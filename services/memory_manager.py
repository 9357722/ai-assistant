"""
记忆管理服务
实现工作记忆、长期记忆、用户画像管理
"""
import json
import time
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict

import aiomysql
import redis.asyncio as redis
from openai import AsyncOpenAI

import config

logger = logging.getLogger(__name__)

# Redis 键前缀
WORKING_MEMORY_PREFIX = "working_memory:"
USER_PROFILE_PREFIX = "user_profile:"
MEMORY_CACHE_PREFIX = "memory_cache:"

# 默认配置
DEFAULT_WORKING_MEMORY_TTL = 3600 * 24  # 24小时
DEFAULT_MAX_WORKING_MEMORY = 50  # 最大工作记忆条数
DEFAULT_LONG_TERM_MEMORY_LIMIT = 100  # 长期记忆查询限制
DEFAULT_SIMILARITY_THRESHOLD = 0.7  # 相似度阈值
DEFAULT_CONFIDENCE_THRESHOLD = 0.6  # 置信度阈值


class MemoryManager:
    """记忆管理器"""

    def __init__(self, pool: aiomysql.Pool, redis_client: Optional[redis.Redis] = None):
        self.pool = pool
        self.redis = redis_client
        self.openai_client = AsyncOpenAI(api_key=config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    async def _get_redis(self) -> redis.Redis:
        """获取 Redis 连接"""
        if not self.redis:
            self.redis = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                decode_responses=True
            )
        return self.redis

    # ============ 工作记忆（Redis） ============

    async def get_working_memory(self, user_id: int, session_id: str) -> Dict[str, Any]:
        """获取工作记忆"""
        try:
            r = await self._get_redis()
            key = f"{WORKING_MEMORY_PREFIX}{user_id}:{session_id}"
            data = await r.get(key)
            if data:
                return json.loads(data)
            return {
                "session_id": session_id,
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "context": [],
                "state": {
                    "current_intent": None,
                    "extracted_entities": {},
                    "task_progress": {}
                }
            }
        except Exception as e:
            logger.error(f"Failed to get working memory: {e}")
            return {"session_id": session_id, "user_id": user_id, "context": [], "state": {}}

    async def save_working_memory(self, user_id: int, session_id: str, memory: Dict[str, Any]):
        """保存工作记忆"""
        try:
            r = await self._get_redis()
            key = f"{WORKING_MEMORY_PREFIX}{user_id}:{session_id}"
            await r.setex(key, DEFAULT_WORKING_MEMORY_TTL, json.dumps(memory, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Failed to save working memory: {e}")

    async def add_to_working_memory(self, user_id: int, session_id: str, role: str, content: str):
        """添加消息到工作记忆"""
        memory = await self.get_working_memory(user_id, session_id)
        memory["context"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        # 限制大小
        if len(memory["context"]) > DEFAULT_MAX_WORKING_MEMORY:
            memory["context"] = memory["context"][-DEFAULT_MAX_WORKING_MEMORY:]
        await self.save_working_memory(user_id, session_id, memory)

    async def update_working_memory_state(self, user_id: int, session_id: str, state_update: Dict[str, Any]):
        """更新工作记忆状态"""
        memory = await self.get_working_memory(user_id, session_id)
        memory["state"].update(state_update)
        await self.save_working_memory(user_id, session_id, memory)

    async def clear_working_memory(self, user_id: int, session_id: str):
        """清除工作记忆"""
        try:
            r = await self._get_redis()
            key = f"{WORKING_MEMORY_PREFIX}{user_id}:{session_id}"
            await r.delete(key)
        except Exception as e:
            logger.error(f"Failed to clear working memory: {e}")

    # ============ 用户画像 ============

    async def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户画像"""
        try:
            # 先尝试从 Redis 缓存获取
            r = await self._get_redis()
            cache_key = f"{USER_PROFILE_PREFIX}{user_id}"
            cached = await r.get(cache_key)
            if cached:
                return json.loads(cached)

            # 从数据库获取
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("SELECT * FROM user_profiles WHERE user_id = %s", (user_id,))
                    profile = await cur.fetchone()
                    if profile:
                        # 转换 JSON 字段
                        for field in ['favorite_colors', 'favorite_categories', 'price_range', 'brand_preferences']:
                            if profile.get(field) and isinstance(profile[field], str):
                                profile[field] = json.loads(profile[field])
                        # 缓存到 Redis
                        await r.setex(cache_key, 3600, json.dumps(profile, ensure_ascii=False, default=str))
                        return profile
            return None
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return None

    async def save_user_profile(self, user_id: int, profile_data: Dict[str, Any]):
        """保存用户画像"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 准备 JSON 字段
                    json_fields = ['favorite_colors', 'favorite_categories', 'price_range', 'brand_preferences']
                    for field in json_fields:
                        if field in profile_data and isinstance(profile_data[field], (list, dict)):
                            profile_data[field] = json.dumps(profile_data[field], ensure_ascii=False)

                    # 构建更新语句
                    fields = ', '.join([f"{k} = %s" for k in profile_data.keys()])
                    values = list(profile_data.values())
                    values.append(user_id)

                    await cur.execute(
                        f"""INSERT INTO user_profiles (user_id, {', '.join(profile_data.keys())})
                            VALUES (%s, {', '.join(['%s'] * len(profile_data))})
                            ON DUPLICATE KEY UPDATE {fields}""",
                        [user_id] + values
                    )
                    await conn.commit()

                    # 清除缓存
                    r = await self._get_redis()
                    await r.delete(f"{USER_PROFILE_PREFIX}{user_id}")

                    logger.info(f"Saved user profile for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save user profile: {e}")

    async def update_user_preferences(self, user_id: int, preferences: Dict[str, Any]):
        """更新用户偏好"""
        profile = await self.get_user_profile(user_id) or {}
        if "favorite_colors" in preferences:
            colors = profile.get("favorite_colors") or []
            if preferences["favorite_colors"] not in colors:
                colors.append(preferences["favorite_colors"])
                colors = colors[-10:]  # 保留最近10个
                profile["favorite_colors"] = colors
        if "favorite_categories" in preferences:
            categories = profile.get("favorite_categories") or []
            if preferences["favorite_categories"] not in categories:
                categories.append(preferences["favorite_categories"])
                categories = categories[-10:]
                profile["favorite_categories"] = categories
        if "price_range" in preferences:
            profile["price_range"] = preferences["price_range"]
        if "brand_preferences" in preferences:
            brands = profile.get("brand_preferences") or []
            if preferences["brand_preferences"] not in brands:
                brands.append(preferences["brand_preferences"])
                brands = brands[-10:]
                profile["brand_preferences"] = brands

        await self.save_user_profile(user_id, profile)

    # ============ 长期记忆 ============

    async def save_long_term_memory(self, user_id: int, memory_text: str, memory_type: str = "general", metadata: Dict = None):
        """保存长期记忆"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """INSERT INTO user_memory_vectors (user_id, memory_text, memory_type, metadata)
                           VALUES (%s, %s, %s, %s)""",
                        (user_id, memory_text, memory_type, json.dumps(metadata or {}, ensure_ascii=False))
                    )
                    await conn.commit()
                    logger.info(f"Saved long-term memory for user {user_id}: {memory_text[:50]}...")
        except Exception as e:
            logger.error(f"Failed to save long-term memory: {e}")

    async def get_long_term_memories(self, user_id: int, memory_type: str = None, limit: int = DEFAULT_LONG_TERM_MEMORY_LIMIT) -> List[Dict[str, Any]]:
        """获取长期记忆"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    if memory_type:
                        await cur.execute(
                            """SELECT * FROM user_memory_vectors
                               WHERE user_id = %s AND memory_type = %s
                               ORDER BY created_at DESC LIMIT %s""",
                            (user_id, memory_type, limit)
                        )
                    else:
                        await cur.execute(
                            """SELECT * FROM user_memory_vectors
                               WHERE user_id = %s
                               ORDER BY created_at DESC LIMIT %s""",
                            (user_id, limit)
                        )
                    memories = await cur.fetchall()
                    for m in memories:
                        if m.get('metadata') and isinstance(m['metadata'], str):
                            m['metadata'] = json.loads(m['metadata'])
                    return memories
        except Exception as e:
            logger.error(f"Failed to get long-term memories: {e}")
            return []

    async def search_long_term_memory(self, user_id: int, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索长期记忆（基于关键词匹配）"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        """SELECT * FROM user_memory_vectors
                           WHERE user_id = %s AND memory_text LIKE %s
                           ORDER BY created_at DESC LIMIT %s""",
                        (user_id, f"%{query}%", limit)
                    )
                    return await cur.fetchall()
        except Exception as e:
            logger.error(f"Failed to search long-term memory: {e}")
            return []

    # ============ 记忆日志 ============

    async def log_memory_action(self, user_id: int, memory_type: str, content: str, action: str = "create", confidence: float = 0.8, source: str = "auto_extract"):
        """记录记忆操作日志"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """INSERT INTO memory_logs (user_id, memory_type, content, confidence, source, action)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (user_id, memory_type, content, confidence, source, action)
                    )
                    await conn.commit()
        except Exception as e:
            logger.error(f"Failed to log memory action: {e}")

    # ============ 记忆提取 ============

    async def extract_memory_from_conversation(self, user_id: int, user_message: str, assistant_response: str) -> Dict[str, Any]:
        """从对话中提取记忆（使用 AI）"""
        try:
            prompt = f"""分析以下对话，提取用户偏好和重要信息。

用户消息：{user_message}
助手回复：{assistant_response}

请提取以下信息（JSON格式）：
{{
    "preferences": {{
        "favorite_colors": "颜色偏好（如果有）",
        "favorite_categories": "商品类别偏好（如果有）",
        "price_range": {{"min": 最低价格, "max": 最高价格}},
        "brand_preferences": "品牌偏好（如果有）"
    }},
    "behaviors": {{
        "intent": "用户意图（search/compare/buy/ask）",
        "entities": ["提取的实体列表"]
    }},
    "memory_text": "需要记住的关键信息摘要",
    "confidence": 0.8
}}

只提取明确提到的信息，不确定的设为null。"""

            response = await self.openai_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )

            result_text = response.choices[0].message.content
            # 尝试解析 JSON
            try:
                # 提取 JSON 部分
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result
            except:
                pass

            return {"preferences": {}, "behaviors": {}, "memory_text": None, "confidence": 0.5}
        except Exception as e:
            logger.error(f"Failed to extract memory: {e}")
            return {"preferences": {}, "behaviors": {}, "memory_text": None, "confidence": 0.5}

    # ============ 记忆管理策略 ============

    async def compress_memories(self, user_id: int):
        """压缩记忆（合并相似记忆）"""
        try:
            memories = await self.get_long_term_memories(user_id, limit=200)
            if len(memories) < 50:
                return  # 记忆太少，不需要压缩

            # 按类型分组
            by_type = defaultdict(list)
            for m in memories:
                by_type[m.get('memory_type', 'general')].append(m)

            # 对每种类型进行压缩
            for mem_type, type_memories in by_type.items():
                if len(type_memories) < 10:
                    continue

                # 使用 AI 进行记忆压缩
                memory_texts = [m['memory_text'] for m in type_memories[:50]]
                prompt = f"""请将以下用户记忆进行压缩合并，去除重复和过时信息，保留最重要的信息。

记忆列表：
{json.dumps(memory_texts, ensure_ascii=False, indent=2)}

请输出压缩后的记忆列表（JSON数组格式），每个元素是压缩后的记忆文本。"""

                response = await self.openai_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1000
                )

                result_text = response.choices[0].message.content
                try:
                    import re
                    json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
                    if json_match:
                        compressed = json.loads(json_match.group())
                        # 删除旧记忆，保存压缩后的记忆
                        async with self.pool.acquire() as conn:
                            async with conn.cursor() as cur:
                                ids = [m['id'] for m in type_memories]
                                await cur.execute(
                                    f"DELETE FROM user_memory_vectors WHERE id IN ({','.join(['%s'] * len(ids))})",
                                    ids
                                )
                                for text in compressed:
                                    await cur.execute(
                                        """INSERT INTO user_memory_vectors (user_id, memory_text, memory_type)
                                           VALUES (%s, %s, %s)""",
                                        (user_id, text, mem_type)
                                    )
                                await conn.commit()
                        logger.info(f"Compressed memories for user {user_id}, type {mem_type}")
                except Exception as e:
                    logger.error(f"Failed to parse compressed memories: {e}")

        except Exception as e:
            logger.error(f"Failed to compress memories: {e}")

    async def decay_memories(self, user_id: int, days: int = 30):
        """记忆衰减（删除过时记忆）"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "DELETE FROM user_memory_vectors WHERE user_id = %s AND created_at < %s",
                        (user_id, cutoff_date)
                    )
                    deleted = cur.rowcount
                    await conn.commit()
                    if deleted > 0:
                        logger.info(f"Decayed {deleted} old memories for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to decay memories: {e}")

    # ============ 综合记忆操作 ============

    async def process_conversation_memory(self, user_id: int, session_id: str, user_message: str, assistant_response: str):
        """处理对话记忆（完整流程）"""
        # 1. 保存到工作记忆
        await self.add_to_working_memory(user_id, session_id, "user", user_message)
        await self.add_to_working_memory(user_id, session_id, "assistant", assistant_response)

        # 2. 提取记忆
        extracted = await self.extract_memory_from_conversation(user_id, user_message, assistant_response)

        # 3. 更新用户偏好
        if extracted.get("preferences"):
            preferences = {k: v for k, v in extracted["preferences"].items() if v is not None}
            if preferences:
                await self.update_user_preferences(user_id, preferences)

        # 4. 保存长期记忆
        if extracted.get("memory_text") and extracted.get("confidence", 0) >= DEFAULT_CONFIDENCE_THRESHOLD:
            await self.save_long_term_memory(
                user_id,
                extracted["memory_text"],
                memory_type="conversation",
                metadata={"session_id": session_id, "confidence": extracted.get("confidence")}
            )
            await self.log_memory_action(
                user_id,
                "context",
                extracted["memory_text"],
                action="create",
                confidence=extracted.get("confidence", 0.8)
            )

        # 5. 更新工作记忆状态
        if extracted.get("behaviors"):
            await self.update_working_memory_state(user_id, session_id, {
                "current_intent": extracted["behaviors"].get("intent"),
                "extracted_entities": extracted["behaviors"].get("entities", [])
            })

    async def get_memory_context(self, user_id: int, session_id: str = None) -> str:
        """获取记忆上下文（用于 AI 回复）"""
        context_parts = []

        # 1. 用户画像
        profile = await self.get_user_profile(user_id)
        if profile:
            profile_info = []
            if profile.get("favorite_colors"):
                profile_info.append(f"喜欢的颜色: {', '.join(profile['favorite_colors'])}")
            if profile.get("favorite_categories"):
                profile_info.append(f"喜欢的类别: {', '.join(profile['favorite_categories'])}")
            if profile.get("brand_preferences"):
                profile_info.append(f"喜欢的品牌: {', '.join(profile['brand_preferences'])}")
            if profile.get("price_range"):
                pr = profile["price_range"]
                if pr.get("min") or pr.get("max"):
                    profile_info.append(f"预算范围: ¥{pr.get('min', 0)}-{pr.get('max', '不限')}")
            if profile_info:
                context_parts.append("【用户画像】\n" + "\n".join(profile_info))

        # 2. 工作记忆（当前会话上下文）
        if session_id:
            working_memory = await self.get_working_memory(user_id, session_id)
            if working_memory.get("state"):
                state = working_memory["state"]
                if state.get("current_intent"):
                    context_parts.append(f"【当前意图】{state['current_intent']}")
                if state.get("extracted_entities"):
                    context_parts.append(f"【提取实体】{state['extracted_entities']}")

        # 3. 相关长期记忆
        recent_memories = await self.get_long_term_memories(user_id, limit=5)
        if recent_memories:
            memory_texts = [m["memory_text"] for m in recent_memories if m.get("memory_text")]
            if memory_texts:
                context_parts.append("【历史记忆】\n" + "\n".join(memory_texts[:3]))

        return "\n\n".join(context_parts) if context_parts else ""


# 全局记忆管理器实例
_memory_manager: Optional[MemoryManager] = None


async def get_memory_manager(pool: aiomysql.Pool) -> MemoryManager:
    """获取记忆管理器实例"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(pool)
    return _memory_manager
