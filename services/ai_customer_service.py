"""
AI 客服服务
提供智能客服对话、订单查询、商品咨询等功能
"""
import json
import os
from typing import List, Optional, Dict, Any, AsyncGenerator

import aiomysql
from openai import AsyncOpenAI

import config


class AICustomerService:
    """AI 客服"""

    def __init__(self, pool: aiomysql.Pool):
        self.pool = pool
        self.system_prompt = """你是 AI 智能电商客服助手，名叫"小智"。

## 你的职责：
1. 解答商品相关问题（规格、功能、对比）
2. 查询订单状态和物流信息
3. 处理退换货咨询
4. 推荐合适的商品
5. 解答购物流程问题

## 回复规范：
- 语气亲切、专业、耐心
- 回答简洁明了，避免冗长
- 涉及订单查询时，主动提供订单号
- 推荐商品时说明推荐理由
- 无法解答的问题，建议联系人工客服

## 可用工具：
- 查询商品信息
- 查询订单状态
- 查询用户订单列表
- 推荐商品"""

    async def chat(
        self,
        user_id: int,
        message: str,
        history: List[Dict[str, str]] = None
    ) -> str:
        """
        AI 客服对话

        Args:
            user_id: 用户ID
            message: 用户消息
            history: 对话历史

        Returns:
            AI 回复
        """
        # 获取用户上下文信息
        context = await self._get_user_context(user_id)

        # 构建消息
        messages = [{"role": "system", "content": self.system_prompt}]

        # 添加用户上下文
        if context:
            messages.append({
                "role": "system",
                "content": f"用户信息：{json.dumps(context, ensure_ascii=False)}"
            })

        # 添加对话历史
        if history:
            messages.extend(history[-5:])  # 最近5条对话

        # 添加当前消息
        messages.append({"role": "user", "content": message})

        # 检查是否需要调用工具
        tool_response = await self._check_and_call_tools(user_id, message)
        if tool_response:
            messages.append({
                "role": "system",
                "content": f"工具查询结果：{tool_response}"
            })

        # 调用 AI 生成回复
        try:
            if not config.DEEPSEEK_API_KEY:
                return "AI 服务未配置，请联系管理员"

            client = AsyncOpenAI(api_key=config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
            response = await client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
            )
            return response.choices[0].message.content

        except Exception as e:
            return "抱歉，AI 服务暂时不可用，请稍后再试。"

    async def chat_stream(
        self,
        user_id: int,
        message: str,
        history: List[Dict[str, str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        AI 客服流式对话（yield 每个 token）
        """
        context = await self._get_user_context(user_id)
        messages = [{"role": "system", "content": self.system_prompt}]
        if context:
            messages.append({
                "role": "system",
                "content": f"用户信息：{json.dumps(context, ensure_ascii=False)}"
            })
        if history:
            messages.extend(history[-5:])
        messages.append({"role": "user", "content": message})

        tool_response = await self._check_and_call_tools(user_id, message)
        if tool_response:
            messages.append({
                "role": "system",
                "content": f"工具查询结果：{tool_response}"
            })

        if not config.DEEPSEEK_API_KEY:
            yield "AI 服务未配置，请联系管理员"
            return

        client = AsyncOpenAI(api_key=config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        try:
            stream = await client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\n\nAI 服务出错：{str(e)}"

    async def _get_user_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户上下文信息"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 获取用户基本信息
                await cur.execute(
                    "SELECT username, email FROM users WHERE id = %s",
                    (user_id,)
                )
                user = await cur.fetchone()
                if not user:
                    return None

                # 获取最近订单
                await cur.execute("""
                    SELECT order_no, status, total_amount, created_at
                    FROM orders
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 3
                """, (user_id,))
                recent_orders = await cur.fetchall()

                # 获取购物车商品数
                await cur.execute(
                    "SELECT COUNT(*) as count FROM cart_items WHERE user_id = %s",
                    (user_id,)
                )
                cart_count = (await cur.fetchone())["count"]

                return {
                    "username": user["username"],
                    "recent_orders": [
                        {
                            "order_no": o["order_no"],
                            "status": o["status"],
                            "amount": float(o["total_amount"]),
                        }
                        for o in recent_orders
                    ],
                    "cart_count": cart_count,
                }

    async def _check_and_call_tools(
        self,
        user_id: int,
        message: str
    ) -> Optional[str]:
        """检查是否需要调用工具并执行"""
        message_lower = message.lower()

        # 订单查询
        if any(keyword in message_lower for keyword in ["订单", "物流", "发货", "快递"]):
            return await self._query_orders(user_id)

        # 商品查询
        if any(keyword in message_lower for keyword in ["价格", "多少钱", "有没有", "推荐"]):
            # 提取商品关键词
            keywords = self._extract_product_keywords(message)
            if keywords:
                return await self._query_products(keywords)

        # 退换货
        if any(keyword in message_lower for keyword in ["退货", "换货", "退款", "退换"]):
            return "退换货政策：\n1. 7天无理由退换货\n2. 商品质量问题可免费退换\n3. 请保持商品原包装完好\n4. 请联系客服获取退换货地址"

        return None

    async def _query_orders(self, user_id: int) -> str:
        """查询用户订单"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT order_no, status, total_amount, created_at
                    FROM orders
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (user_id,))
                orders = await cur.fetchall()

                if not orders:
                    return "您还没有订单记录"

                status_map = {
                    "pending": "待支付",
                    "paid": "已支付",
                    "shipped": "已发货",
                    "completed": "已完成",
                    "cancelled": "已取消",
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
                    ORDER BY p.sales DESC
                    LIMIT 8
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
        # 简单的关键词提取
        keywords = []
        product_categories = [
            "手机", "耳机", "电脑", "平板", "音箱", "手表",
            "美妆", "口红", "护肤", "零食", "坚果", "食品",
            "服装", "T恤", "牛仔裤", "鞋", "运动", "箱包",
            "相机", "镜头", "空调", "电饭煲", "家电", "家居",
            "母婴", "奶粉", "纸尿裤", "图书", "书",
        ]

        for category in product_categories:
            if category in message:
                keywords.append(category)

        # 提取引号中的内容
        import re
        quoted = re.findall(r'[「」""\'](.*?)[「」""\']', message)
        keywords.extend(quoted)

        return keywords if keywords else [message[:10]]  # 默认使用前10个字符

    async def get_quick_replies(self, user_id: int) -> List[str]:
        """获取快捷回复建议"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 检查用户是否有待支付订单
                await cur.execute(
                    "SELECT COUNT(*) as count FROM orders WHERE user_id = %s AND status = 'pending'",
                    (user_id,)
                )
                has_pending = (await cur.fetchone())["count"] > 0

                # 检查用户购物车
                await cur.execute(
                    "SELECT COUNT(*) as count FROM cart_items WHERE user_id = %s",
                    (user_id,)
                )
                has_cart = (await cur.fetchone())["count"] > 0

                quick_replies = ["查看热门商品", "商品推荐"]

                if has_pending:
                    quick_replies.insert(0, "查看待支付订单")

                if has_cart:
                    quick_replies.insert(0, "查看购物车")

                return quick_replies
