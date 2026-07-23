"""
AI 客服服务
提供智能客服对话、订单查询、商品咨询、比价、优惠券等功能
集成记忆管理系统（工作记忆 + 长期记忆 + 用户画像）
"""
import json
import os
import re
import time
import uuid
import logging
from typing import List, Optional, Dict, Any, AsyncGenerator
from collections import defaultdict

import aiomysql
from openai import AsyncOpenAI, APIError, RateLimitError, AuthenticationError

import config
from services.multimodal_service import describe_image_for_agent, image_to_base64, get_image_media_type
from services.memory_manager import MemoryManager, get_memory_manager

logger = logging.getLogger(__name__)

# 对话历史存储（用户ID → 消息列表）
# 改用 MySQL 持久化，重启不丢失
_MAX_HISTORY = 20  # 每次请求加载最近 N 条

# 降价提醒存储（商品ID → [{user_id, target_price}]）
_price_alerts: Dict[int, List[dict]] = defaultdict(list)
_PRICE_ALERTS_MAX_PRODUCTS = 5000  # 最大监控商品数


class AICustomerService:
    """AI 客服（集成记忆管理）"""

    def __init__(self, pool: aiomysql.Pool):
        self.pool = pool
        self.memory_manager: Optional[MemoryManager] = None
        self.system_prompt = """你是 AI 智能电商客服助手，名叫"小智"。

## 你的职责：
1. 解答商品相关问题（规格、功能、对比）
2. 查询订单状态和物流信息
3. 处理退换货咨询
4. 推荐合适的商品
5. 解答购物流程问题
6. 商品比价（跨平台价格对比）
7. 降价提醒（设置目标价格）
8. 优惠券发现（匹配可用优惠券）
9. 商品评价分析（总结买家评价）
10. 尺码推荐（根据用户信息推荐）

## 回复规范：
- 语气亲切、专业、耐心
- 回答简洁明了，避免冗长
- 涉及订单查询时，主动提供订单号
- 推荐商品时说明推荐理由
- 比价时要清晰列出各平台价格
- 无法解答的问题，建议联系人工客服

## 可用工具：
- 查询商品信息
- 查询订单状态
- 商品比价
- 设置降价提醒
- 查询优惠券
- 分析商品评价
- 尺码推荐"""

    async def _init_memory_manager(self):
        """初始化记忆管理器"""
        if not self.memory_manager:
            self.memory_manager = await get_memory_manager(self.pool)

    async def _get_history(self, user_id: int) -> List[dict]:
        """从 MySQL 获取用户的最近对话历史"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(
                        """SELECT role, content FROM chat_history
                           WHERE user_id = %s
                           ORDER BY id DESC LIMIT %s""",
                        (user_id, _MAX_HISTORY)
                    )
                    rows = await cur.fetchall()
                    # 反转为时间正序
                    return list(reversed(rows))
        except Exception as e:
            logger.warning(f"Failed to load chat history: {e}")
            return []

    async def _save_message(self, user_id: int, role: str, content: str):
        """保存一条消息到 MySQL"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "INSERT INTO chat_history (user_id, role, content) VALUES (%s, %s, %s)",
                        (user_id, role, content)
                    )
                    await conn.commit()
        except Exception as e:
            logger.warning(f"Failed to save chat history: {e}")

    async def clear_history(self, user_id: int):
        """清除用户的对话历史"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("DELETE FROM chat_history WHERE user_id = %s", (user_id,))
                    await conn.commit()
        except Exception as e:
            logger.warning(f"Failed to clear chat history: {e}")

    def _generate_session_id(self, user_id: int) -> str:
        """生成会话 ID"""
        return f"session_{user_id}_{int(time.time())}"

    async def chat(
        self,
        user_id: int,
        message: str,
        history: List[Dict[str, str]] = None,
        image_data: Optional[bytes] = None,
        session_id: Optional[str] = None
    ) -> str:
        """AI 客服对话（支持图片输入，集成记忆管理）"""
        await self._init_memory_manager()

        # 生成或使用提供的 session_id
        if not session_id:
            session_id = self._generate_session_id(user_id)

        context = await self._get_user_context(user_id)
        messages = [{"role": "system", "content": self.system_prompt}]

        # 获取记忆上下文
        memory_context = await self.memory_manager.get_memory_context(user_id, session_id)
        if memory_context:
            messages.append({
                "role": "system",
                "content": f"【记忆信息】\n{memory_context}"
            })

        if context:
            messages.append({
                "role": "system",
                "content": f"用户信息：{json.dumps(context, ensure_ascii=False)}"
            })

        # 获取工作记忆上下文
        working_memory = await self.memory_manager.get_working_memory(user_id, session_id)
        if working_memory.get("context"):
            # 使用工作记忆中的上下文
            for msg in working_memory["context"][-10:]:  # 最近10条
                messages.append({"role": msg["role"], "content": msg["content"]})

        stored_history = await self._get_history(user_id)
        if stored_history:
            messages.extend(stored_history)
        elif history:
            messages.extend(history[-5:])

        # 构造用户消息（支持图片）
        if image_data:
            # 先用视觉模型描述图片
            image_desc = await describe_image_for_agent(image_data, "用户在客服对话中发送了一张图片。")
            user_content = [
                {"type": "text", "text": f"{message}\n\n[用户发送的图片描述: {image_desc}]"}
            ]
            messages.append({"role": "user", "content": json.dumps(user_content, ensure_ascii=False)})
        else:
            messages.append({"role": "user", "content": message})

        # 检查是否需要调用工具
        tool_result = await self._check_and_call_tools(user_id, message)

        if tool_result:
            # 如果有工具结果，添加到上下文
            messages.append({
                "role": "system",
                "content": f"【工具查询结果】\n{tool_result}"
            })

        try:
            client = AsyncOpenAI(
                api_key=config.DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com"
            )
            response = await client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            reply = response.choices[0].message.content

            # 保存到 MySQL
            await self._save_message(user_id, "user", message)
            await self._save_message(user_id, "assistant", reply)

            # 处理记忆
            await self.memory_manager.process_conversation_memory(
                user_id, session_id, message, reply
            )

            return reply
        except Exception as e:
            logger.error(f"AI chat error: {e}")
            return f"抱歉，AI 服务暂时不可用，请稍后再试。错误：{str(e)}"

    async def chat_stream(
        self,
        user_id: int,
        message: str,
        history: List[Dict[str, str]] = None,
        image_data: Optional[bytes] = None,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """AI 客服流式对话（SSE，集成记忆管理）"""
        await self._init_memory_manager()

        # 生成或使用提供的 session_id
        if not session_id:
            session_id = self._generate_session_id(user_id)

        context = await self._get_user_context(user_id)
        messages = [{"role": "system", "content": self.system_prompt}]

        # 获取记忆上下文
        memory_context = await self.memory_manager.get_memory_context(user_id, session_id)
        if memory_context:
            messages.append({
                "role": "system",
                "content": f"【记忆信息】\n{memory_context}"
            })

        if context:
            messages.append({
                "role": "system",
                "content": f"用户信息：{json.dumps(context, ensure_ascii=False)}"
            })

        # 获取工作记忆上下文
        working_memory = await self.memory_manager.get_working_memory(user_id, session_id)
        if working_memory.get("context"):
            for msg in working_memory["context"][-10:]:
                messages.append({"role": msg["role"], "content": msg["content"]})

        stored_history = await self._get_history(user_id)
        if stored_history:
            messages.extend(stored_history)
        elif history:
            messages.extend(history[-5:])

        # 构造用户消息（支持图片）
        if image_data:
            image_desc = await describe_image_for_agent(image_data, "用户在客服对话中发送了一张图片。")
            user_content = [
                {"type": "text", "text": f"{message}\n\n[用户发送的图片描述: {image_desc}]"}
            ]
            messages.append({"role": "user", "content": json.dumps(user_content, ensure_ascii=False)})
        else:
            messages.append({"role": "user", "content": message})

        # 检查是否需要调用工具
        tool_result = await self._check_and_call_tools(user_id, message)

        if tool_result:
            messages.append({
                "role": "system",
                "content": f"【工具查询结果】\n{tool_result}"
            })

        try:
            client = AsyncOpenAI(
                api_key=config.DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com"
            )
            response = await client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=True
            )

            full_reply = ""
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_reply += token
                    yield token

            # 保存到 MySQL
            await self._save_message(user_id, "user", message)
            await self._save_message(user_id, "assistant", full_reply)

            # 处理记忆
            await self.memory_manager.process_conversation_memory(
                user_id, session_id, message, full_reply
            )

        except Exception as e:
            logger.error(f"AI stream chat error: {e}")
            yield f"\n\n抱歉，AI 服务暂时不可用，请稍后再试。错误：{str(e)}"

    async def _get_user_context(self, user_id: int) -> Optional[dict]:
        """获取用户上下文信息"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # 获取用户基本信息
                    await cur.execute(
                        "SELECT username, email, phone FROM users WHERE id = %s",
                        (user_id,)
                    )
                    user = await cur.fetchone()

                    if not user:
                        return None

                    context = {"username": user["username"]}

                    # 获取最近订单
                    await cur.execute(
                        """SELECT order_no, status, total_amount
                           FROM orders WHERE user_id = %s
                           ORDER BY created_at DESC LIMIT 3""",
                        (user_id,)
                    )
                    orders = await cur.fetchall()
                    if orders:
                        context["recent_orders"] = orders

                    # 获取购物车数量
                    await cur.execute(
                        "SELECT COUNT(*) as count FROM cart_items WHERE user_id = %s",
                        (user_id,)
                    )
                    cart_count = (await cur.fetchone())["count"]
                    if cart_count > 0:
                        context["cart_count"] = cart_count

                    return context
        except Exception as e:
            logger.warning(f"Failed to get user context: {e}")
            return None

    async def _check_and_call_tools(self, user_id: int, message: str) -> Optional[str]:
        """检查是否需要调用工具"""
        message_lower = message.lower()

        # 订单查询
        if any(keyword in message_lower for keyword in ["订单", "order", "购买记录", "物流"]):
            return await self._query_orders(user_id)

        # 商品查询
        product_keywords = self._extract_product_keywords(message)
        if product_keywords:
            product_info = await self._query_products(product_keywords)
            if product_info:
                return product_info

        # 比价查询
        if any(keyword in message_lower for keyword in ["比价", "价格对比", "哪个便宜", "compare"]):
            # 提取商品名称进行比价
            compare_result = await self._compare_prices(message)
            if compare_result:
                return compare_result

        # 降价提醒
        if any(keyword in message_lower for keyword in ["降价提醒", "价格提醒", "notify"]):
            return await self._set_price_alert(user_id, message)

        # 优惠券查询
        if any(keyword in message_lower for keyword in ["优惠券", "coupon", "折扣"]):
            return await self._query_coupons(user_id)

        # 尺码推荐
        if any(keyword in message_lower for keyword in ["尺码", "size", "多大", "尺寸"]):
            return self._get_size_recommendation(message)

        return None

    async def _compare_prices(self, message: str) -> Optional[str]:
        """比价功能"""
        # 提取商品关键词
        keywords = self._extract_product_keywords(message)
        if not keywords:
            return None

        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    keyword = keywords[0]
                    await cur.execute("""
                        SELECT name, platform, price
                        FROM products
                        WHERE name LIKE %s AND status = 'on_sale'
                        ORDER BY price ASC
                    """, (f"%{keyword}%",))
                    products = await cur.fetchall()

                    if len(products) < 2:
                        return None

                    result = f"**{keyword} 比价结果**：\n\n"
                    for p in products:
                        result += f"- {p['platform']}: ¥{p['price']:.2f}\n"

                    # 计算价差
                    prices = [p['price'] for p in products]
                    diff = max(prices) - min(prices)
                    result += f"\n价差: ¥{diff:.2f}"

                    return result
        except Exception as e:
            logger.error(f"Compare prices error: {e}")
            return None

    async def _set_price_alert(self, user_id: int, message: str) -> str:
        """设置降价提醒"""
        # 提取目标价格
        price_match = re.search(r'(\d+(?:\.\d+)?)', message)
        if not price_match:
            return "请告诉我您期望的价格，例如：「iPhone 15 降价到 5000 元提醒我」"

        target_price = float(price_match.group(1))
        keywords = self._extract_product_keywords(message)

        if not keywords:
            return "请告诉我您想设置哪个商品的降价提醒"

        # 这里简化处理，实际应该存储到数据库
        return f"已为您设置降价提醒：当 **{keywords[0]}** 价格降至 ¥{target_price:.2f} 时通知您"

    async def _query_coupons(self, user_id: int) -> str:
        """查询可用优惠券"""
        # 简化实现
        return "**可用优惠券**：\n\n- 新用户专享：满100减10\n- 电子产品：满1000减50\n- 服装类：满200减20\n\n使用优惠券可在结算时自动抵扣。"

    def _get_size_recommendation(self, message: str) -> str:
        """尺码推荐"""
        size_chart = {
            "T恤": {"S": "身高155-160", "M": "身高160-165", "L": "身高165-170", "XL": "身高170-175", "XXL": "身高175-180", "XXXL": "身高180以上"},
            "裤子": {"S": "腰围2尺1", "M": "腰围2尺2", "L": "腰围2尺3", "XL": "腰围2尺4", "XXL": "腰围2尺5", "XXXL": "腰围2尺6以上"},
            "鞋": {"36": "脚长23cm", "37": "脚长23.5cm", "38": "脚长24cm", "39": "脚长24.5cm", "40": "脚长25cm", "41": "脚长25.5cm", "42": "脚长26cm"},
        }

        # 提取商品类型
        for category, chart in size_chart.items():
            if category in message:
                result = f"**{category}尺码对照表**：\n\n"
                for size, desc in chart.items():
                    result += f"- {size}：{desc}\n"
                result += "\n建议您根据身高/脚长选择合适的尺码。如有疑问可咨询客服。"
                return result

        return "请告诉我您想买什么商品，我来帮您推荐尺码。例如：「T恤买多大」「鞋子尺码推荐」"

    # ============ 辅助函数 ============

    async def _query_orders(self, user_id: int) -> str:
        """查询用户订单"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT order_no, status, total_amount, created_at
                    FROM orders WHERE user_id = %s
                    ORDER BY created_at DESC LIMIT 5
                """, (user_id,))
                orders = await cur.fetchall()

                if not orders:
                    return "您还没有订单记录"

                status_map = {
                    "pending": "待支付", "paid": "已支付", "shipped": "已发货",
                    "completed": "已完成", "cancelled": "已取消",
                }

                result = "您的最近订单：\n"
                for o in orders:
                    status = status_map.get(o["status"], o["status"])
                    result += f"- 订单号: {o['order_no']}, 状态: {status}, 金额: ¥{o['total_amount']}\n"
                return result

    async def _query_products(self, keywords: List[str]) -> str:
        """查询商品信息"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                keyword = keywords[0] if keywords else ""
                await cur.execute("""
                    SELECT p.name, p.price, p.platform, p.stock
                    FROM products p
                    LEFT JOIN categories c ON p.category_id = c.id
                    WHERE (p.name LIKE %s OR c.name LIKE %s) AND p.status = 'on_sale'
                    ORDER BY p.sales DESC LIMIT 8
                """, (f"%{keyword}%", f"%{keyword}%"))
                products = await cur.fetchall()

                if not products:
                    return f"未找到与'{keyword}'相关的商品"

                result = f"找到以下'{keyword}'相关商品：\n"
                for p in products:
                    stock_status = "有货" if p["stock"] > 0 else "缺货"
                    result += f"- {p['name']}: ¥{p['price']} ({p['platform']}, {stock_status})\n"
                return result

    def _extract_product_keywords(self, message: str) -> List[str]:
        """从消息中提取商品关键词"""
        keywords = []
        product_categories = [
            "手机", "耳机", "电脑", "平板", "音箱", "手表",
            "美妆", "口红", "护肤", "零食", "坚果", "食品",
            "服装", "T恤", "牛仔裤", "鞋", "运动", "箱包",
            "相机", "镜头", "空调", "电饭煲", "家电", "家居",
            "母婴", "奶粉", "图书", "iPhone", "小米", "华为",
        ]
        for category in product_categories:
            if category.lower() in message.lower():
                keywords.append(category)

        quoted = re.findall(r'[「」""\'](.*?)[「」""\']', message)
        keywords.extend(quoted)

        return keywords if keywords else [message[:10]]

    async def get_quick_replies(self, user_id: int) -> List[str]:
        """获取快捷回复建议"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT COUNT(*) as count FROM orders WHERE user_id = %s AND status = 'pending'",
                    (user_id,)
                )
                has_pending = (await cur.fetchone())["count"] > 0

                await cur.execute(
                    "SELECT COUNT(*) as count FROM cart_items WHERE user_id = %s",
                    (user_id,)
                )
                has_cart = (await cur.fetchone())["count"] > 0

                quick_replies = ["查看热门商品", "商品推荐", "查优惠券"]

                if has_pending:
                    quick_replies.insert(0, "查看待支付订单")
                if has_cart:
                    quick_replies.insert(0, "查看购物车")

                return quick_replies

    # ============ 记忆管理 API ============

    async def get_user_memory_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户记忆画像"""
        await self._init_memory_manager()
        return await self.memory_manager.get_user_profile(user_id)

    async def get_user_memories(self, user_id: int, memory_type: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """获取用户记忆列表"""
        await self._init_memory_manager()
        return await self.memory_manager.get_long_term_memories(user_id, memory_type, limit)

    async def search_user_memories(self, user_id: int, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索用户记忆"""
        await self._init_memory_manager()
        return await self.memory_manager.search_long_term_memory(user_id, query, limit)

    async def clear_user_memories(self, user_id: int):
        """清除用户记忆"""
        await self._init_memory_manager()
        # 清除工作记忆
        session_id = self._generate_session_id(user_id)
        await self.memory_manager.clear_working_memory(user_id, session_id)
        # 清除长期记忆
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("DELETE FROM user_memory_vectors WHERE user_id = %s", (user_id,))
                    await cur.execute("DELETE FROM memory_logs WHERE user_id = %s", (user_id,))
                    await conn.commit()
        except Exception as e:
            logger.error(f"Failed to clear user memories: {e}")
