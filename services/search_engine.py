# -*- coding: utf-8 -*-
"""
四棒搜索引擎
第1棒：意图解析与查询改写（LLM）
第2棒：多路召回（MySQL文本 + 分类 + 向量）
第3棒：精排打分（规则引擎）
第4棒：重排调整（多样性 + 业务规则）
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

import aiomysql
from openai import AsyncOpenAI

import config

logger = logging.getLogger(__name__)

# ============ 同义词/纠错词典 ============
CATEGORY_SYNONYMS = {
    "手机": ["手机", "智能手机", "移动电话", "phone"],
    "电脑": ["电脑", "笔记本", "笔记本电脑", "laptop", "PC"],
    "平板": ["平板", "平板电脑", "pad", "tablet"],
    "耳机": ["耳机", "耳麦", "headphone", "耳塞"],
    "智能手表": ["手表", "智能手表", "手环", "watch"],
    "相机": ["相机", "摄像机", "单反", "微单", "camera"],
    "服装": ["服装", "衣服", "T恤", "衬衫", "裤子"],
    "鞋靴": ["鞋", "鞋子", "运动鞋", "靴子"],
    "箱包": ["包", "箱包", "背包", "手提包"],
    "美妆": ["美妆", "化妆品", "口红", "护肤", "面膜"],
    "食品": ["食品", "零食", "坚果", "饮料"],
    "家居": ["家居", "家具", "家纺"],
    "家电": ["家电", "电器", "空调", "冰箱", "洗衣机"],
    "母婴": ["母婴", "婴儿", "宝宝", "奶粉"],
    "运动": ["运动", "健身", "户外"],
    "图书": ["图书", "书", "书籍"],
}

# 品牌关键词 + 别名映射
BRAND_KEYWORDS = [
    "苹果", "apple", "华为", "huawei", "小米", "xiaomi", "红米", "redmi",
    "三星", "samsung", "oppo", "vivo", "荣耀", "honor", "一加", "oneplus",
    "索尼", "sony", "佳能", "canon", "尼康", "nikon", "戴尔", "dell",
    "联想", "lenovo", "thinkpad", "惠普", "hp", "兰蔻", "lancome",
    "雅诗兰黛", "三只松鼠", "良品铺子", "格力", "美的", "海尔",
    "耐克", "nike", "阿迪达斯", "adidas", "优衣库", "李宁",
]

# 品牌名 → 商品名中可能出现的关键词
BRAND_NAME_MAP = {
    "苹果": ["iphone", "apple", "airpods", "macbook", "ipad"],
    "华为": ["华为", "huawei", "mate", "p60", "p70", "nova"],
    "小米": ["小米", "xiaomi", "redmi", "红米"],
    "红米": ["红米", "redmi"],
    "三星": ["三星", "samsung", "galaxy"],
    "索尼": ["索尼", "sony"],
    "佳能": ["佳能", "canon"],
}


class SearchEngine:
    """四棒搜索引擎"""

    def __init__(self, pool: aiomysql.Pool):
        self.pool = pool

    # ================================================================
    # 第1棒：意图解析与查询改写
    # ================================================================

    async def parse_intent(self, query: str) -> Dict[str, Any]:
        """
        用 LLM 解析用户搜索意图，返回结构化信息。

        返回:
            {
                "original_query": "三千左右的手机",
                "keywords": ["手机"],
                "category": "手机",
                "brand": null,
                "price_min": 2500,
                "price_max": 3500,
                "attributes": ["三千左右"],
                "corrected_query": "三千左右的手机",
                "intent": "search"  # search | compare | recommend
            }
        """
        # 先用规则快速提取
        intent = self._rule_based_parse(query)

        # 再用 LLM 增强（纠错、语义扩展）
        try:
            llm_result = await self._llm_parse(query)
            if llm_result:
                # LLM 结果优先，但保留规则提取的价格区间（LLM 可能不准）
                if intent.get("price_min") and not llm_result.get("price_min"):
                    llm_result["price_min"] = intent["price_min"]
                    llm_result["price_max"] = intent["price_max"]
                return llm_result
        except Exception as e:
            logger.warning(f"LLM intent parsing failed, using rule-based: {e}")

        return intent

    def _rule_based_parse(self, query: str) -> Dict[str, Any]:
        """基于规则的快速意图解析"""
        intent = {
            "original_query": query,
            "keywords": [],
            "category": None,
            "brand": None,
            "price_min": None,
            "price_max": None,
            "attributes": [],
            "corrected_query": query,
            "intent": "search",
        }

        # 1. 提取价格区间（支持中文数字和阿拉伯数字）
        cn_num_map = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "百": 100, "千": 1000, "万": 10000}

        def parse_cn_number(s):
            """解析中文数字，如 '三千' → 3000, '五千' → 5000"""
            total = 0
            current = 0
            for ch in s:
                if ch in cn_num_map:
                    val = cn_num_map[ch]
                    if val >= 1000:
                        current = max(current, 1) * val
                        total += current
                        current = 0
                    elif val >= 10:
                        current = max(current, 1) * val
                    else:
                        current = current * 10 + val
            total += current
            return total if total > 0 else None

        price_patterns = [
            # 中文数字: 三千左右、五千以内
            (r'([一二两三四五六七八九十百千万]+)\s*[块元]?\s*[以之]?\s*[上下左右内]?',
             lambda m: (parse_cn_number(m.group(1)) * 0.7, parse_cn_number(m.group(1)) * 1.3) if parse_cn_number(m.group(1)) else None),
            # 阿拉伯数字: 3000左右、5000以内
            (r'(\d+)\s*[块元]?\s*[以之]?\s*[上下左右内]',
             lambda m: (float(m.group(1)) * 0.7, float(m.group(1)) * 1.3)),
            (r'[低于少于小于]\s*(\d+)\s*[块元]?', lambda m: (0, float(m.group(1)))),
            (r'[高于大于超过]\s*(\d+)\s*[块元]?', lambda m: (float(m.group(1)), 999999)),
            (r'(\d+)\s*[-到至]\s*(\d+)\s*[块元]?', lambda m: (float(m.group(1)), float(m.group(2)))),
        ]
        for pattern, extractor in price_patterns:
            m = re.search(pattern, query)
            if m:
                low, high = extractor(m)
                intent["price_min"] = low
                intent["price_max"] = high
                intent["attributes"].append(m.group())
                break

        # 2. 提取分类
        for cat_name, synonyms in CATEGORY_SYNONYMS.items():
            for syn in synonyms:
                if syn in query:
                    intent["category"] = cat_name
                    intent["keywords"].append(cat_name)
                    break
            if intent["category"]:
                break

        # 3. 提取品牌
        query_lower = query.lower()
        for brand in BRAND_KEYWORDS:
            if brand in query_lower:
                intent["brand"] = brand
                intent["keywords"].append(brand)
                break

        # 4. 兜底：如果没有提取到关键词，用整个查询
        if not intent["keywords"]:
            intent["keywords"] = [query]

        return intent

    async def _llm_parse(self, query: str) -> Optional[Dict[str, Any]]:
        """用 DeepSeek LLM 解析搜索意图"""
        if not config.DEEPSEEK_API_KEY:
            return None

        client = AsyncOpenAI(api_key=config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

        prompt = f"""你是电商搜索意图解析器。分析用户搜索词，返回JSON格式结果。

用户搜索: "{query}"

可选分类: 手机、电脑、平板、耳机、智能手表、相机、服装、鞋靴、箱包、美妆、食品、家居、家电、母婴、运动、图书

请返回以下JSON（不要其他内容）:
{{
    "corrected_query": "纠错后的搜索词（如果没错误就原样返回）",
    "keywords": ["提取的核心搜索关键词"],
    "category": "匹配的分类名或null",
    "brand": "品牌名或null",
    "price_min": null,
    "price_max": null,
    "attributes": ["属性词如颜色、尺寸等"],
    "intent": "search或compare或recommend"
}}

只返回JSON，不要其他文字。"""

        response = await client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0,
        )

        content = response.choices[0].message.content.strip()
        # 提取 JSON（兼容 markdown code block）
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            result["original_query"] = query
            if "keywords" not in result:
                result["keywords"] = [query]
            return result

        return None

    # ================================================================
    # 第2棒：多路召回
    # ================================================================

    async def multi_recall(self, intent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        多路并发召回候选商品。

        三路召回：
        1. 文本召回：匹配商品名 + 描述
        2. 分类召回：匹配分类下的商品
        3. 品牌召回：匹配品牌关键词
        """
        candidates = {}  # 用 dict 去重，key=product_id

        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # --- 路径1: 文本召回 ---
                for kw in intent.get("keywords", []):
                    await cur.execute("""
                        SELECT p.*, c.name as category_name
                        FROM products p
                        LEFT JOIN categories c ON p.category_id = c.id
                        WHERE p.status = 'on_sale'
                          AND (p.name LIKE %s OR p.description LIKE %s)
                        ORDER BY p.sales DESC
                        LIMIT 20
                    """, (f"%{kw}%", f"%{kw}%"))
                    for row in await cur.fetchall():
                        pid = row["id"]
                        if pid not in candidates:
                            row["_recall_source"] = "text"
                            row["_match_score"] = 0
                            candidates[pid] = row
                        candidates[pid]["_match_score"] += 3  # 文本命中加分

                # --- 路径2: 分类召回 ---
                if intent.get("category"):
                    cat_name = intent["category"]
                    # 用同义词扩展
                    synonyms = CATEGORY_SYNONYMS.get(cat_name, [cat_name])
                    for syn in synonyms:
                        await cur.execute("""
                            SELECT p.*, c.name as category_name
                            FROM products p
                            JOIN categories c ON p.category_id = c.id
                            WHERE p.status = 'on_sale'
                              AND c.name = %s
                            ORDER BY p.sales DESC
                            LIMIT 20
                        """, (syn,))
                        for row in await cur.fetchall():
                            pid = row["id"]
                            if pid not in candidates:
                                row["_recall_source"] = "category"
                                row["_match_score"] = 0
                                candidates[pid] = row
                            candidates[pid]["_match_score"] += 2  # 分类命中加分

                # --- 路径3: 品牌召回 ---
                if intent.get("brand"):
                    brand = intent["brand"]
                    await cur.execute("""
                        SELECT p.*, c.name as category_name
                        FROM products p
                        LEFT JOIN categories c ON p.category_id = c.id
                        WHERE p.status = 'on_sale'
                          AND p.name LIKE %s
                        ORDER BY p.sales DESC
                        LIMIT 20
                    """, (f"%{brand}%",))
                    for row in await cur.fetchall():
                        pid = row["id"]
                        if pid not in candidates:
                            row["_recall_source"] = "brand"
                            row["_match_score"] = 0
                            candidates[pid] = row
                        candidates[pid]["_match_score"] += 2  # 品牌命中加分

        return list(candidates.values())

    # ================================================================
    # 第3棒：精排打分
    # ================================================================

    def score_products(self, products: List[Dict], intent: Dict) -> List[Dict]:
        """
        对召回商品进行精排打分。

        打分维度：
        - 关键词相关性（召回时的基础分）
        - 价格匹配度（越接近目标区间越高）
        - 销量热度
        - 评分
        - 库存状态
        """
        for p in products:
            score = p.get("_match_score", 0)

            # 1. 价格匹配度（权重最高）
            price = float(p.get("price", 0))
            if intent.get("price_min") is not None and intent.get("price_max") is not None:
                p_min, p_max = intent["price_min"], intent["price_max"]
                if p_min <= price <= p_max:
                    score += 10  # 价格在区间内，高分
                elif price < p_min:
                    gap = (p_min - price) / p_max if p_max else 0
                    score += max(0, 5 - gap * 10)
                else:
                    gap = (price - p_max) / p_max if p_max else 0
                    score += max(0, 5 - gap * 10)

            # 2. 销量热度（归一化到0-3分）
            sales = p.get("sales", 0) or 0
            if sales > 100:
                score += 3
            elif sales > 50:
                score += 2
            elif sales > 10:
                score += 1

            # 3. 评分（0-2分）
            rating = p.get("rating")
            if rating is not None:
                score += min(2, float(rating) / 2.5)

            # 4. 库存惩罚
            stock = p.get("stock", 0) or 0
            if stock <= 0:
                score -= 10  # 缺货大幅降权

            p["_final_score"] = round(score, 2)

        return sorted(products, key=lambda x: x.get("_final_score", 0), reverse=True)

    # ================================================================
    # 第4棒：重排调整
    # ================================================================

    def rerank(self, products: List[Dict], limit: int = 20) -> List[Dict]:
        """
        重排：多样性打散 + 清理内部字段。

        - 同平台最多展示 N 个，避免全是一个平台
        - 清理内部打分字段
        """
        if not products:
            return []

        # 多样性打散：同平台最多连续出现2个
        result = []
        platform_count = {}
        MAX_SAME_PLATFORM = 4

        for p in products:
            platform = p.get("platform", "unknown")
            count = platform_count.get(platform, 0)
            if count < MAX_SAME_PLATFORM:
                result.append(p)
                platform_count[platform] = count + 1
            if len(result) >= limit:
                break

        # 如果打散后不够，把剩余的补回来
        if len(result) < limit:
            for p in products:
                if p not in result:
                    result.append(p)
                if len(result) >= limit:
                    break

        # 清理内部字段
        for p in result:
            p.pop("_recall_source", None)
            p.pop("_match_score", None)
            p.pop("_final_score", None)

        return result

    # ================================================================
    # 主入口：四棒串联
    # ================================================================

    async def search(self, query: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        完整的四棒搜索流程。

        Args:
            query: 用户搜索词
            page: 页码
            page_size: 每页数量

        Returns:
            {
                "intent": {...},         # 解析后的意图
                "total": 42,
                "page": 1,
                "page_size": 20,
                "items": [...]
            }
        """
        # 第1棒：意图解析
        intent = await self.parse_intent(query)
        logger.info(f"Search intent: {json.dumps(intent, ensure_ascii=False)}")

        # 第2棒：多路召回
        candidates = await self.multi_recall(intent)
        logger.info(f"Recalled {len(candidates)} candidates")

        # 第3棒：精排打分
        scored = self.score_products(candidates, intent)
        logger.info(f"Scored {len(scored)} products, top score: {scored[0]['_final_score'] if scored else 0}")

        # 品牌过滤：如果指定了品牌，优先只保留品牌匹配的商品
        if intent.get("brand"):
            brand = intent["brand"].lower()
            # 获取品牌的所有可能名称（含别名）
            brand_aliases = BRAND_NAME_MAP.get(brand, [brand])
            brand_aliases_lower = [a.lower() for a in brand_aliases]

            def matches_brand(product_name):
                name_lower = product_name.lower()
                return any(alias in name_lower for alias in brand_aliases_lower)

            brand_matched = [p for p in scored if matches_brand(p.get("name", ""))]
            if brand_matched:
                scored = brand_matched
                scored.sort(key=lambda x: x.get("_final_score", 0), reverse=True)
            else:
                for p in scored:
                    p["_final_score"] -= 20
                scored.sort(key=lambda x: x.get("_final_score", 0), reverse=True)

        # 第4棒：重排调整
        total = len(scored)
        start = (page - 1) * page_size
        end = start + page_size
        reranked = self.rerank(scored[start:end], limit=page_size)

        # 构建分页后的完整结果（需要对全量 scored 做重排再分页）
        all_reranked = self.rerank(scored, limit=total)
        paginated = all_reranked[start:end]

        return {
            "intent": {
                "original_query": intent.get("original_query", query),
                "corrected_query": intent.get("corrected_query", query),
                "category": intent.get("category"),
                "brand": intent.get("brand"),
                "price_range": {
                    "min": intent.get("price_min"),
                    "max": intent.get("price_max"),
                } if intent.get("price_min") is not None else None,
            },
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": paginated,
        }
