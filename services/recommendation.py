"""
推荐引擎服务
基于用户行为、商品向量相似度、协同过滤等算法提供个性化推荐
"""
import json
from typing import List, Optional, Dict, Any

import aiomysql
from openai import OpenAI

import config


class RecommendationEngine:
    """推荐引擎"""

    def __init__(self, pool: aiomysql.Pool, vector_collection=None):
        self.pool = pool
        self.vector_collection = vector_collection

    async def get_personalized_recommendations(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取个性化推荐

        综合以下因素：
        1. 用户浏览/购买历史
        2. 商品向量相似度
        3. 热门商品
        4. 协同过滤（相似用户喜欢的商品）

        Args:
            user_id: 用户ID
            limit: 推荐数量

        Returns:
            推荐商品列表
        """
        recommendations = []

        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 1. 基于用户购买历史的推荐
                history_recs = await self._recommend_by_history(cur, user_id, limit // 2)
                recommendations.extend(history_recs)

                # 2. 基于热门商品的推荐
                hot_recs = await self._recommend_by_popularity(cur, limit // 2)
                recommendations.extend(hot_recs)

                # 3. 基于向量相似度的推荐（如果有向量数据库）
                if self.vector_collection:
                    vector_recs = await self._recommend_by_vector(cur, user_id, limit // 2)
                    recommendations.extend(vector_recs)

                # 去重并排序
                seen_ids = set()
                unique_recs = []
                for rec in recommendations:
                    if rec["id"] not in seen_ids:
                        seen_ids.add(rec["id"])
                        unique_recs.append(rec)

                return unique_recs[:limit]

    async def _recommend_by_history(
        self,
        cursor,
        user_id: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """基于用户购买历史推荐"""
        # 获取用户购买过的商品分类
        await cursor.execute("""
            SELECT DISTINCT p.category_id
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            JOIN products p ON oi.product_id = p.id
            WHERE o.user_id = %s AND o.status IN ('paid', 'completed')
        """, (user_id,))
        categories = await cursor.fetchall()

        if not categories:
            return []

        # 推荐同分类的其他商品
        category_ids = [c["category_id"] for c in categories if c["category_id"]]
        if not category_ids:
            return []

        placeholders = ",".join(["%s"] * len(category_ids))
        await cursor.execute(f"""
            SELECT p.*, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.category_id IN ({placeholders})
            AND p.status = 'on_sale'
            AND p.id NOT IN (
                SELECT oi.product_id FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE o.user_id = %s
            )
            ORDER BY p.sales DESC, p.created_at DESC
            LIMIT %s
        """, category_ids + [user_id, limit])

        products = await cursor.fetchall()
        return [self._format_product(p, "history", "根据您的购买历史推荐") for p in products]

    async def _recommend_by_popularity(
        self,
        cursor,
        limit: int
    ) -> List[Dict[str, Any]]:
        """基于热门商品推荐"""
        await cursor.execute("""
            SELECT p.*, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.status = 'on_sale'
            ORDER BY p.sales DESC, p.created_at DESC
            LIMIT %s
        """, (limit,))

        products = await cursor.fetchall()
        return [self._format_product(p, "hot", "热门商品") for p in products]

    async def _recommend_by_vector(
        self,
        cursor,
        user_id: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """基于向量相似度推荐"""
        if not self.vector_collection:
            return []

        # 获取用户最近购买的商品
        await cursor.execute("""
            SELECT p.name
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            JOIN products p ON oi.product_id = p.id
            WHERE o.user_id = %s
            ORDER BY o.created_at DESC
            LIMIT 3
        """, (user_id,))
        recent_products = await cursor.fetchall()

        if not recent_products:
            return []

        # 使用向量搜索相似商品
        query_text = " ".join([p["name"] for p in recent_products])
        try:
            results = self.vector_collection.query(
                query_texts=[query_text],
                n_results=limit
            )

            if not results or not results["documents"]:
                return []

            # 从向量结果中提取商品名称
            similar_names = []
            for doc in results["documents"][0]:
                if "：" in doc:
                    name = doc.split("：")[0].strip()
                else:
                    name = doc[:30]
                similar_names.append(name)

            # 查询数据库中的商品
            recommendations = []
            for name in similar_names[:limit]:
                await cursor.execute("""
                    SELECT p.*, c.name as category_name
                    FROM products p
                    LEFT JOIN categories c ON p.category_id = c.id
                    WHERE p.name LIKE %s AND p.status = 'on_sale'
                    LIMIT 1
                """, (f"%{name}%",))
                product = await cursor.fetchone()
                if product:
                    recommendations.append(
                        self._format_product(product, "vector", "相似商品推荐")
                    )

            return recommendations

        except Exception as e:
            print(f"向量推荐失败: {e}")
            return []

    def _format_product(
        self,
        product: Dict[str, Any],
        source: str,
        reason: str
    ) -> Dict[str, Any]:
        """格式化推荐商品"""
        return {
            "id": product["id"],
            "name": product["name"],
            "price": float(product["price"]),
            "platform": product["platform"],
            "category_name": product.get("category_name"),
            "main_image": product.get("main_image"),
            "sales": product.get("sales", 0),
            "rating": product.get("rating"),
            "source": source,
            "reason": reason,
        }

    async def get_recommendation_by_budget(
        self,
        budget: float,
        category: Optional[str] = None,
        prefer_brand: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        基于预算的推荐

        Args:
            budget: 预算金额
            category: 商品分类
            prefer_brand: 偏好品牌
            limit: 推荐数量

        Returns:
            推荐商品列表
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 构建查询条件
                conditions = ["p.status = 'on_sale'", "p.price <= %s"]
                params = [budget]

                if category:
                    conditions.append("c.name = %s")
                    params.append(category)

                if prefer_brand:
                    conditions.append("p.name LIKE %s")
                    params.append(f"%{prefer_brand}%")

                where_clause = " AND ".join(conditions)

                await cur.execute(f"""
                    SELECT p.*, c.name as category_name
                    FROM products p
                    LEFT JOIN categories c ON p.category_id = c.id
                    WHERE {where_clause}
                    ORDER BY p.price DESC, p.sales DESC
                    LIMIT %s
                """, params + [limit])

                products = await cur.fetchall()
                return [
                    self._format_product(p, "budget", f"¥{budget}预算内推荐")
                    for p in products
                ]

    async def get_similar_products(
        self,
        product_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        获取相似商品推荐

        Args:
            product_id: 商品ID
            limit: 推荐数量

        Returns:
            相似商品列表
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 获取当前商品信息
                await cur.execute("""
                    SELECT p.*, c.name as category_name
                    FROM products p
                    LEFT JOIN categories c ON p.category_id = c.id
                    WHERE p.id = %s
                """, (product_id,))
                product = await cur.fetchone()

                if not product:
                    return []

                # 基于分类和价格区间推荐
                price_range = float(product["price"]) * 0.3  # 30% 价格浮动
                min_price = float(product["price"]) - price_range
                max_price = float(product["price"]) + price_range

                await cur.execute("""
                    SELECT p.*, c.name as category_name
                    FROM products p
                    LEFT JOIN categories c ON p.category_id = c.id
                    WHERE p.id != %s
                    AND p.status = 'on_sale'
                    AND p.category_id = %s
                    AND p.price BETWEEN %s AND %s
                    ORDER BY p.sales DESC
                    LIMIT %s
                """, (product_id, product["category_id"], min_price, max_price, limit))

                products = await cur.fetchall()

                # 如果同分类结果不足，补充其他分类
                if len(products) < limit:
                    remaining = limit - len(products)
                    await cur.execute("""
                        SELECT p.*, c.name as category_name
                        FROM products p
                        LEFT JOIN categories c ON p.category_id = c.id
                        WHERE p.id != %s
                        AND p.status = 'on_sale'
                        AND p.price BETWEEN %s AND %s
                        ORDER BY p.sales DESC
                        LIMIT %s
                    """, (product_id, min_price, max_price, remaining))

                    other_products = await cur.fetchall()
                    products.extend(other_products)

                return [
                    self._format_product(p, "similar", "相似商品")
                    for p in products[:limit]
                ]

    async def generate_ai_recommendation(
        self,
        user_query: str,
        budget: Optional[float] = None
    ) -> str:
        """
        使用 AI 生成推荐文案

        Args:
            user_query: 用户需求描述
            budget: 预算

        Returns:
            AI 生成的推荐文案
        """
        # 获取相关商品
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                conditions = ["p.status = 'on_sale'"]
                params = []

                if budget:
                    conditions.append("p.price <= %s")
                    params.append(budget)

                where_clause = " AND ".join(conditions)
                await cur.execute(f"""
                    SELECT p.name, p.price, p.platform, p.sales
                    FROM products p
                    WHERE {where_clause}
                    ORDER BY p.sales DESC
                    LIMIT 10
                """, params)

                products = await cur.fetchall()

        if not products:
            return "暂无符合条件的商品推荐"

        # 生成推荐文案
        product_list = "\n".join([
            f"- {p['name']}: ¥{p['price']} ({p['platform']}, 销量{p['sales']})"
            for p in products
        ])

        try:
            import os
            deepseek_key = os.getenv("DEEPSEEK_API_KEY")
            if not deepseek_key:
                return "AI 服务未配置"

            client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")
            response = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[
                    {"role": "system", "content": """你是专业的电商导购助手。根据用户需求和商品列表，给出个性化推荐。
要求：
1. 推荐3-5款最合适的商品
2. 说明推荐理由
3. 给出购买建议
4. 语气亲切专业"""},
                    {"role": "user", "content": f"用户需求: {user_query}\n预算: {'¥' + str(budget) if budget else '不限'}\n\n可选商品:\n{product_list}"}
                ],
                max_tokens=500,
            )
            return response.choices[0].message.content

        except Exception as e:
            return f"AI 推荐生成失败: {str(e)}"
