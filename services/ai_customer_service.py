"""
AI 客服服务
提供智能客服对话、订单查询、商品咨询、比价、优惠券等功能
"""
import json
import os
import re
import time
from typing import List, Optional, Dict, Any, AsyncGenerator
from collections import defaultdict

import aiomysql
from openai import AsyncOpenAI

import config

# 对话历史存储（用户ID → 消息列表）
_chat_history: Dict[int, List[dict]] = defaultdict(list)
_MAX_HISTORY = 20
_HISTORY_EXPIRE = 3600
_chat_timestamps: Dict[int, float] = {}

# 降价提醒存储（商品ID → [{user_id, target_price}]）
_price_alerts: Dict[int, List[dict]] = defaultdict(list)


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

    def _get_history(self, user_id: int) -> List[dict]:
        """获取用户的对话历史"""
        now = time.time()
        if user_id in _chat_timestamps:
            if now - _chat_timestamps[user_id] > _HISTORY_EXPIRE:
                _chat_history[user_id] = []
        _chat_timestamps[user_id] = now
        return _chat_history[user_id]

    def _save_message(self, user_id: int, role: str, content: str):
        """保存一条消息到历史"""
        history = _chat_history[user_id]
        history.append({"role": role, "content": content})
        if len(history) > _MAX_HISTORY:
            _chat_history[user_id] = history[-_MAX_HISTORY:]

    def clear_history(self, user_id: int):
        """清除用户的对话历史"""
        _chat_history[user_id] = []
        _chat_timestamps.pop(user_id, None)

    async def chat(
        self,
        user_id: int,
        message: str,
        history: List[Dict[str, str]] = None
    ) -> str:
        """AI 客服对话"""
        context = await self._get_user_context(user_id)
        messages = [{"role": "system", "content": self.system_prompt}]

        if context:
            messages.append({
                "role": "system",
                "content": f"用户信息：{json.dumps(context, ensure_ascii=False)}"
            })

        stored_history = self._get_history(user_id)
        if stored_history:
            messages.extend(stored_history)
        elif history:
            messages.extend(history[-5:])

        messages.append({"role": "user", "content": message})

        # 多工具链式调用：同时执行多个工具
        tool_responses = await self._check_and_call_tools_multi(user_id, message)
        if tool_responses:
            messages.append({
                "role": "system",
                "content": f"工具查询结果：\n" + "\n".join(tool_responses)
            })

        try:
            if not config.DEEPSEEK_API_KEY:
                return "AI 服务未配置，请联系管理员"

            client = AsyncOpenAI(api_key=config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
            response = await client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=messages,
                max_tokens=800,
                temperature=0.7,
            )
            reply = response.choices[0].message.content

            self._save_message(user_id, "user", message)
            self._save_message(user_id, "assistant", reply)

            return reply

        except Exception as e:
            return "抱歉，AI 服务暂时不可用，请稍后再试。"

    async def chat_stream(
        self,
        user_id: int,
        message: str,
        history: List[Dict[str, str]] = None
    ) -> AsyncGenerator[str, None]:
        """AI 客服流式对话"""
        context = await self._get_user_context(user_id)
        messages = [{"role": "system", "content": self.system_prompt}]
        if context:
            messages.append({
                "role": "system",
                "content": f"用户信息：{json.dumps(context, ensure_ascii=False)}"
            })

        stored_history = self._get_history(user_id)
        if stored_history:
            messages.extend(stored_history)
        elif history:
            messages.extend(history[-5:])

        messages.append({"role": "user", "content": message})

        tool_responses = await self._check_and_call_tools_multi(user_id, message)
        if tool_responses:
            messages.append({
                "role": "system",
                "content": f"工具查询结果：\n" + "\n".join(tool_responses)
            })

        if not config.DEEPSEEK_API_KEY:
            yield "AI 服务未配置，请联系管理员"
            return

        client = AsyncOpenAI(api_key=config.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        full_reply = ""
        try:
            stream = await client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=messages,
                max_tokens=800,
                temperature=0.7,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_reply += token
                    yield token

            self._save_message(user_id, "user", message)
            self._save_message(user_id, "assistant", full_reply)

        except Exception as e:
            yield f"\n\nAI 服务出错：{str(e)}"

    async def _get_user_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户上下文信息"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(
                    "SELECT username, email FROM users WHERE id = %s",
                    (user_id,)
                )
                user = await cur.fetchone()
                if not user:
                    return None

                await cur.execute("""
                    SELECT order_no, status, total_amount, created_at
                    FROM orders WHERE user_id = %s
                    ORDER BY created_at DESC LIMIT 3
                """, (user_id,))
                recent_orders = await cur.fetchall()

                await cur.execute(
                    "SELECT COUNT(*) as count FROM cart_items WHERE user_id = %s",
                    (user_id,)
                )
                cart_count = (await cur.fetchone())["count"]

                return {
                    "username": user["username"],
                    "recent_orders": [
                        {"order_no": o["order_no"], "status": o["status"], "amount": float(o["total_amount"])}
                        for o in recent_orders
                    ],
                    "cart_count": cart_count,
                }

    # ============ 多工具链式调用 ============

    async def _check_and_call_tools_multi(self, user_id: int, message: str) -> List[str]:
        """同时调用多个工具，返回所有结果"""
        message_lower = message.lower()
        results = []

        # 比价
        if any(kw in message_lower for kw in ["比价", "对比价格", "哪个平台便宜", "哪里便宜", "跨平台"]):
            r = await self._compare_prices(message)
            if r:
                results.append(r)

        # 降价提醒
        if any(kw in message_lower for kw in ["降价提醒", "降价通知", "目标价", "监控价格"]):
            r = await self._set_price_alert(user_id, message)
            if r:
                results.append(r)

        # 优惠券
        if any(kw in message_lower for kw in ["优惠券", "优惠", "券", "折扣", "满减"]):
            r = await self._find_coupons(user_id, message)
            if r:
                results.append(r)

        # 评价分析
        if any(kw in message_lower for kw in ["评价", "评论", "买家说", "口碑", "怎么样"]):
            r = await self._analyze_reviews(message)
            if r:
                results.append(r)

        # 尺码推荐
        if any(kw in message_lower for kw in ["尺码", "多大", "尺寸", "买多大", "推荐尺码"]):
            r = await self._recommend_size(user_id, message)
            if r:
                results.append(r)

        # 订单查询
        if any(kw in message_lower for kw in ["订单", "物流", "发货", "快递"]):
            r = await self._query_orders(user_id)
            if r:
                results.append(r)

        # 商品查询
        if any(kw in message_lower for kw in ["价格", "多少钱", "有没有", "推荐"]):
            keywords = self._extract_product_keywords(message)
            if keywords:
                r = await self._query_products(keywords)
                if r:
                    results.append(r)

        # 退换货
        if any(kw in message_lower for kw in ["退货", "换货", "退款", "退换"]):
            results.append("退换货政策：\n1. 7天无理由退换货\n2. 商品质量问题可免费退换\n3. 请保持商品原包装完好\n4. 请联系客服获取退换货地址")

        return results

    # ============ 工具：商品比价 ============

    async def _compare_prices(self, message: str) -> Optional[str]:
        """跨平台商品比价"""
        keywords = self._extract_product_keywords(message)
        if not keywords:
            return None

        keyword = keywords[0]
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT name, price, platform, stock, sales
                    FROM products
                    WHERE name LIKE %s AND status = 'on_sale'
                    ORDER BY price ASC
                """, (f"%{keyword}%",))
                products = await cur.fetchall()

        if not products:
            return f"未找到与'{keyword}'相关的商品进行比价"

        # 按平台分组
        platforms = {}
        for p in products:
            platform = p['platform'] or '未知'
            if platform not in platforms:
                platforms[platform] = []
            platforms[platform].append(p)

        result = f"**{keyword} 跨平台比价**：\n\n"
        prices = []
        for platform, items in platforms.items():
            cheapest = min(items, key=lambda x: float(x['price']))
            prices.append(float(cheapest['price']))
            stock_status = "有货" if cheapest['stock'] > 0 else "缺货"
            result += f"- {platform}：¥{cheapest['price']} ({stock_status}, 已售{cheapest['sales']}件)\n"

        if len(prices) > 1:
            cheapest_platform = min(platforms.items(), key=lambda x: min(float(p['price']) for p in x[1]))[0]
            most_expensive = max(prices)
            cheapest = min(prices)
            savings = most_expensive - cheapest
            result += f"\n**推荐**：{cheapest_platform} 最便宜，比最高价便宜 ¥{savings:.2f}"

        return result

    # ============ 工具：降价提醒 ============

    async def _set_price_alert(self, user_id: int, message: str) -> Optional[str]:
        """设置降价提醒"""
        # 提取商品名和目标价格
        price_match = re.search(r'(\d+(?:\.\d+)?)', message)
        target_price = float(price_match.group(1)) if price_match else None

        keywords = self._extract_product_keywords(message)
        if not keywords:
            return "请告诉我您想监控哪个商品的价格？例如：「监控iPhone的降价，目标价5000」"

        keyword = keywords[0]

        # 查找商品
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT id, name, price FROM products
                    WHERE name LIKE %s AND status = 'on_sale' LIMIT 1
                """, (f"%{keyword}%",))
                product = await cur.fetchone()

        if not product:
            return f"未找到'{keyword}'相关商品"

        if target_price is None:
            target_price = float(product['price']) * 0.8  # 默认为目标价的80%

        # 保存提醒
        _price_alerts[product['id']].append({
            "user_id": user_id,
            "target_price": target_price,
            "current_price": float(product['price']),
            "created_at": time.time(),
        })

        return (f"已设置降价提醒：\n"
                f"- 商品：{product['name']}\n"
                f"- 当前价格：¥{product['price']}\n"
                f"- 目标价格：¥{target_price}\n"
                f"- 降价后会通知您！")

    # ============ 工具：优惠券发现 ============

    async def _find_coupons(self, user_id: int, message: str) -> Optional[str]:
        """查找可用优惠券"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 查询所有有效优惠券
                await cur.execute("""
                    SELECT c.*, m.shop_name
                    FROM coupons c
                    LEFT JOIN merchants m ON c.merchant_id = m.id
                    WHERE c.is_active = TRUE
                    AND (c.end_date IS NULL OR c.end_date >= CURDATE())
                    AND (c.max_uses = 0 OR c.used_count < c.max_uses)
                    ORDER BY c.value DESC
                    LIMIT 10
                """)
                coupons = await cur.fetchall()

                # 查询用户已领取的优惠券
                await cur.execute("""
                    SELECT coupon_id FROM user_coupons WHERE user_id = %s
                """, (user_id,))
                claimed = {row['coupon_id'] for row in await cur.fetchall()}

        if not coupons:
            return "暂时没有可用的优惠券，稍后再来看看吧！"

        result = "🎁 **可用优惠券**：\n\n"
        for c in coupons:
            claimed_status = "已领取" if c['id'] in claimed else "未领取"
            if c['type'] == 'fixed':
                discount = f"减¥{c['value']}"
            else:
                discount = f"{c['value']}%off"
            min_amount = f"满¥{c['min_amount']}可用" if c.get('min_amount') else "无门槛"
            shop = c.get('shop_name') or '平台'
            result += f"- [{shop}] {c['name']}: {discount} ({min_amount}) [{claimed_status}]\n"

        return result

    # ============ 工具：评价分析 ============

    async def _analyze_reviews(self, message: str) -> Optional[str]:
        """分析商品评价"""
        keywords = self._extract_product_keywords(message)
        if not keywords:
            return None

        keyword = keywords[0]
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 查找商品
                await cur.execute("""
                    SELECT id, name FROM products WHERE name LIKE %s AND status = 'on_sale' LIMIT 1
                """, (f"%{keyword}%",))
                product = await cur.fetchone()

                if not product:
                    return f"未找到'{keyword}'相关商品"

                # 获取评价
                await cur.execute("""
                    SELECT pr.rating, pr.content, u.username
                    FROM product_reviews pr
                    JOIN users u ON pr.user_id = u.id
                    WHERE pr.product_id = %s
                    ORDER BY pr.created_at DESC
                    LIMIT 20
                """, (product['id'],))
                reviews = await cur.fetchall()

        if not reviews:
            return f"'{product['name']}'暂时还没有评价"

        # 统计
        total = len(reviews)
        avg_rating = sum(r['rating'] for r in reviews) / total
        rating_dist = {i: 0 for i in range(1, 6)}
        for r in reviews:
            rating_dist[r['rating']] = rating_dist.get(r['rating'], 0) + 1

        result = f"**{product['name']} 评价分析**（共{total}条）：\n\n"
        result += f"- 平均评分：{'⭐' * round(avg_rating)} {avg_rating:.1f}/5\n"
        result += f"- 5星: {rating_dist.get(5, 0)}条 | 4星: {rating_dist.get(4, 0)}条 | 3星: {rating_dist.get(3, 0)}条\n\n"

        # 正面/负面评价
        positive = [r for r in reviews if r['rating'] >= 4]
        negative = [r for r in reviews if r['rating'] <= 2]

        if positive:
            result += "**好评摘录**：\n"
            for r in positive[:3]:
                result += f"- {r['username']}：{r['content'][:50]}...\n"

        if negative:
            result += "\n**差评摘录**：\n"
            for r in negative[:2]:
                result += f"- {r['username']}：{r['content'][:50]}...\n"

        return result

    # ============ 工具：尺码推荐 ============

    async def _recommend_size(self, user_id: int, message: str) -> Optional[str]:
        """根据用户信息推荐尺码"""
        # 简单的尺码推荐逻辑
        size_chart = {
            "T恤": {"XS": "身高155以下", "S": "身高155-160", "M": "身高160-170", "L": "身高170-180", "XL": "身高180以上"},
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
