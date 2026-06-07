# -*- coding: utf-8 -*-
"""
商家智能助手 Agent
功能：
1. 商品智能上传 - 自动生成标题、描述、定价建议
2. 销售数据分析 - 趋势分析、热销排行、库存预警
3. 智能客服 - 回答买家咨询、处理售后
4. 经营建议 - 营销、定价、选品建议
5. 竞品分析 - 分析同类商品定价策略
6. 智能定价 - 根据市场行情自动调价建议
7. 营销文案生成 - 生成商品详情页文案
8. 销量预测 - 预测未来销量趋势
9. 商品捆绑推荐 - 推荐搭配销售组合
10. 客户评价分析 - 分析差评原因，给出改进建议
11. 库存智能补货 - 根据销售速度预测补货时间
"""
import json
import logging
import time
from typing import Dict, Any, List, Optional
from collections import defaultdict
from datetime import datetime, timedelta

import aiomysql
from openai import AsyncOpenAI

import config

logger = logging.getLogger(__name__)

# 商家对话历史存储
_merchant_chat_history: Dict[int, List[dict]] = defaultdict(list)
_MAX_HISTORY = 20
_HISTORY_EXPIRE = 3600
_merchant_chat_timestamps: Dict[int, float] = {}


class MerchantAgent:
    """商家智能助手"""

    def __init__(self, pool: aiomysql.Pool):
        self.pool = pool
        self.client = AsyncOpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )

    def _get_history(self, merchant_id: int) -> List[dict]:
        """获取商家的对话历史"""
        now = time.time()
        if merchant_id in _merchant_chat_timestamps:
            if now - _merchant_chat_timestamps[merchant_id] > _HISTORY_EXPIRE:
                _merchant_chat_history[merchant_id] = []
        _merchant_chat_timestamps[merchant_id] = now
        return _merchant_chat_history[merchant_id]

    def _save_message(self, merchant_id: int, role: str, content: str):
        """保存一条消息到历史"""
        history = _merchant_chat_history[merchant_id]
        history.append({"role": role, "content": content})
        if len(history) > _MAX_HISTORY:
            _merchant_chat_history[merchant_id] = history[-_MAX_HISTORY:]

    def clear_history(self, merchant_id: int):
        """清除商家的对话历史"""
        _merchant_chat_history[merchant_id] = []
        _merchant_chat_timestamps.pop(merchant_id, None)

    async def chat(self, merchant_id: int, message: str, context: List[Dict] = None) -> Dict[str, Any]:
        """与商家Agent对话"""
        merchant_info = await self._get_merchant_info(merchant_id)
        dashboard_data = await self._get_dashboard_data(merchant_id)

        # 获取存储的历史对话
        stored_history = self._get_history(merchant_id)
        if not context and stored_history:
            context = stored_history

        # 多意图识别
        intents = await self._parse_intent(message, merchant_info, dashboard_data, context)

        # 执行所有意图
        results = []
        for intent in intents:
            result = await self._execute_action(merchant_id, intent, message)
            results.append(result)

        # 合并回复
        if len(results) == 1:
            final_result = results[0]
        else:
            combined_reply = "\n\n---\n\n".join([r.get("reply", "") for r in results])
            final_result = {"reply": combined_reply, "action": "multi", "data": [r.get("data") for r in results]}

        # 保存对话
        self._save_message(merchant_id, "user", message)
        self._save_message(merchant_id, "assistant", final_result.get("reply", ""))

        return final_result

    # ============ 商家信息和数据 ============

    async def _get_merchant_info(self, merchant_id: int) -> Dict:
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT * FROM merchants WHERE id = %s", (merchant_id,))
                return await cur.fetchone() or {}

    async def _get_dashboard_data(self, merchant_id: int) -> Dict:
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT COUNT(*) as total_products FROM merchant_products WHERE merchant_id = %s", (merchant_id,))
                products = (await cur.fetchone())['total_products']

                await cur.execute("""
                    SELECT COUNT(DISTINCT o.id) as today_orders, COALESCE(SUM(oi.quantity * oi.price), 0) as today_sales
                    FROM orders o JOIN order_items oi ON o.id = oi.order_id
                    JOIN merchant_products mp ON oi.product_id = mp.product_id
                    WHERE mp.merchant_id = %s AND DATE(o.created_at) = CURDATE()
                """, (merchant_id,))
                today = await cur.fetchone()

                await cur.execute("""
                    SELECT COUNT(DISTINCT o.id) as pending_orders
                    FROM orders o JOIN order_items oi ON o.id = oi.order_id
                    JOIN merchant_products mp ON oi.product_id = mp.product_id
                    WHERE mp.merchant_id = %s AND o.status = 'paid'
                """, (merchant_id,))
                pending = await cur.fetchone()

                await cur.execute("""
                    SELECT p.name, p.price, COALESCE(SUM(oi.quantity), 0) as sales
                    FROM products p JOIN merchant_products mp ON p.id = mp.product_id
                    LEFT JOIN order_items oi ON p.id = oi.product_id
                    WHERE mp.merchant_id = %s GROUP BY p.id ORDER BY sales DESC LIMIT 5
                """, (merchant_id,))
                hot_products = await cur.fetchall()

                await cur.execute("""
                    SELECT p.name, p.stock
                    FROM products p JOIN merchant_products mp ON p.id = mp.product_id
                    WHERE mp.merchant_id = %s AND p.stock < 10 ORDER BY p.stock ASC
                """, (merchant_id,))
                low_stock = await cur.fetchall()

                return {
                    'total_products': products,
                    'today_orders': today['today_orders'],
                    'today_sales': float(today['today_sales']),
                    'pending_orders': pending['pending_orders'],
                    'hot_products': hot_products,
                    'low_stock': low_stock
                }

    # ============ 意图识别（支持多意图） ============

    async def _parse_intent(self, message: str, merchant_info: Dict, dashboard_data: Dict, context: List[Dict] = None) -> List[Dict]:
        """解析用户意图，返回意图列表"""
        system_prompt = f"""你是惠购商城的商家智能助手，帮助商家管理店铺。

当前商家信息：
- 店铺名称：{merchant_info.get('shop_name', '未知')}
- 商品数量：{dashboard_data.get('total_products', 0)}
- 今日订单：{dashboard_data.get('today_orders', 0)}
- 今日销售额：¥{dashboard_data.get('today_sales', 0)}
- 待发货订单：{dashboard_data.get('pending_orders', 0)}

你可以帮助商家：
1. upload_product - 上传商品
2. analytics - 数据分析
3. advice - 经营建议
4. competitor_analysis - 竞品分析
5. smart_pricing - 智能定价
6. marketing_copy - 营销文案生成
7. sales_forecast - 销量预测
8. bundle_recommend - 商品捆绑推荐
9. review_analysis - 客户评价分析
10. inventory_restock - 库存智能补货
11. general_chat - 一般对话

用户可能同时表达多个意图，请分析后返回JSON数组：
[
    {{"intent": "intent_type", "parameters": {{...}}, "reply": "简短回复"}}
]

只返回JSON，不要其他内容。"""

        messages = [{"role": "system", "content": system_prompt}]
        if context:
            messages.extend(context[-5:])
        messages.append({"role": "user", "content": message})

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
            )
            content = response.choices[0].message.content.strip()
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"Intent parsing failed: {e}")

        return [{"intent": "general_chat", "parameters": None, "reply": message}]

    # ============ 执行动作 ============

    async def _execute_action(self, merchant_id: int, intent: Dict, original_message: str) -> Dict:
        action = intent.get('intent', 'general_chat')
        params = intent.get('parameters')

        actions = {
            'upload_product': self._handle_upload_product,
            'analytics': self._handle_analytics,
            'advice': self._handle_advice,
            'competitor_analysis': self._handle_competitor_analysis,
            'smart_pricing': self._handle_smart_pricing,
            'marketing_copy': self._handle_marketing_copy,
            'sales_forecast': self._handle_sales_forecast,
            'bundle_recommend': self._handle_bundle_recommend,
            'review_analysis': self._handle_review_analysis,
            'inventory_restock': self._handle_inventory_restock,
        }

        handler = actions.get(action)
        if handler:
            return await handler(merchant_id, params, original_message)
        return await self._handle_general_chat(original_message, intent.get('reply', ''))

    # ============ 1. 上传商品 ============

    async def _handle_upload_product(self, merchant_id: int, params: Dict, message: str) -> Dict:
        if params and params.get('name'):
            product_info = await self._generate_product_info(params)
            return {
                "reply": f"已为您分析商品信息：\n\n"
                        f"**商品名称**：{product_info['name']}\n"
                        f"**建议价格**：¥{product_info['price']}\n"
                        f"**商品分类**：{product_info['category']}\n"
                        f"**商品描述**：{product_info['description']}\n\n"
                        f"是否确认添加？点击「确认添加」按钮即可上架。",
                "action": "show_product_form",
                "data": product_info
            }
        else:
            return {
                "reply": "请告诉我您要上传的商品信息：\n\n"
                        "1. **商品名称**是什么？\n"
                        "2. **价格**大概多少？\n"
                        "3. 属于哪个**分类**？\n\n"
                        "例如：「上传一款蓝牙耳机，价格199，属于耳机分类」",
                "action": "wait_input",
                "data": None
            }

    async def _generate_product_info(self, params: Dict) -> Dict:
        name = params.get('name', '')
        price = params.get('price', 0)
        category = params.get('category', '')

        prompt = f"""根据以下商品信息，生成完整的商品详情：

商品名：{name}
价格：{price}
分类：{category}

请返回JSON：
{{
    "name": "优化后的商品名称",
    "price": 建议价格,
    "category": "分类名称",
    "description": "商品描述（100字左右）",
    "stock": 建议库存量
}}"""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300, temperature=0.7,
            )
            content = response.choices[0].message.content.strip()
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"Generate product info failed: {e}")

        return {"name": name, "price": price, "category": category, "description": f"优质{name}，品质保证", "stock": 100}

    # ============ 2. 数据分析 ============

    async def _handle_analytics(self, merchant_id: int, params: Dict, message: str) -> Dict:
        analytics_type = params.get('type', 'overview') if params else 'overview'
        data = await self._get_dashboard_data(merchant_id)

        if analytics_type == 'hot_products':
            products = data.get('hot_products', [])
            if products:
                product_list = "\n".join([f"- {p['name']}: 销量{p['sales']}件, ¥{p['price']}" for p in products])
                return {"reply": f"**热销商品 TOP5**：\n\n{product_list}", "action": "show_analytics", "data": data}
            return {"reply": "暂无销售数据！", "action": "show_analytics", "data": data}
        elif analytics_type == 'low_stock':
            low_stock = data.get('low_stock', [])
            if low_stock:
                stock_list = "\n".join([f"- {p['name']}: 仅剩{p['stock']}件" for p in low_stock])
                return {"reply": f"**库存预警**：\n\n{stock_list}\n\n请及时补货！", "action": "show_analytics", "data": data}
            return {"reply": "所有商品库存充足！", "action": "show_analytics", "data": data}
        else:
            return {
                "reply": f"**今日经营概览**：\n\n- 商品总数：{data['total_products']}件\n- 今日订单：{data['today_orders']}笔\n- 今日销售额：¥{data['today_sales']:.2f}\n- 待发货订单：{data['pending_orders']}笔",
                "action": "show_analytics", "data": data
            }

    # ============ 3. 经营建议 ============

    async def _handle_advice(self, merchant_id: int, params: Dict, message: str) -> Dict:
        data = await self._get_dashboard_data(merchant_id)
        prompt = f"""你是电商运营专家，为商家提供经营建议。

店铺数据：商品{data['total_products']}件，今日销售¥{data['today_sales']:.2f}，待发货{data['pending_orders']}笔

用户问题：{message}

请提供具体、可执行的建议（100字以内）。"""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-v4-flash", messages=[{"role": "user", "content": prompt}],
                max_tokens=300, temperature=0.7,
            )
            return {"reply": response.choices[0].message.content.strip(), "action": "show_advice", "data": {"topic": params.get('topic', 'general') if params else 'general'}}
        except Exception as e:
            return {"reply": "抱歉，暂时无法生成建议。", "action": "error", "data": None}

    # ============ 4. 竞品分析 ============

    async def _handle_competitor_analysis(self, merchant_id: int, params: Dict, message: str) -> Dict:
        """分析同类商品定价策略"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 获取商家的商品分类
                await cur.execute("""
                    SELECT DISTINCT p.category_id, c.name as category_name
                    FROM products p
                    JOIN merchant_products mp ON p.id = mp.product_id
                    LEFT JOIN categories c ON p.category_id = c.id
                    WHERE mp.merchant_id = %s
                """, (merchant_id,))
                categories = await cur.fetchall()

                if not categories:
                    return {"reply": "您还没有商品，无法进行竞品分析。", "action": "competitor_analysis", "data": None}

                # 分析每个分类的竞争情况
                results = []
                for cat in categories:
                    cat_id = cat['category_id']
                    cat_name = cat.get('category_name', '未知')

                    # 该分类下所有商家的商品
                    await cur.execute("""
                        SELECT p.name, p.price, p.platform, p.sales, m.shop_name
                        FROM products p
                        JOIN merchant_products mp ON p.id = mp.product_id
                        JOIN merchants m ON mp.merchant_id = m.id
                        WHERE p.category_id = %s AND p.status = 'on_sale'
                        ORDER BY p.sales DESC
                    """, (cat_id,))
                    competitors = await cur.fetchall()

                    # 我的商品
                    await cur.execute("""
                        SELECT p.name, p.price, p.sales
                        FROM products p
                        JOIN merchant_products mp ON p.id = mp.product_id
                        WHERE mp.merchant_id = %s AND p.category_id = %s
                    """, (merchant_id, cat_id))
                    my_products = await cur.fetchall()

                    if competitors and my_products:
                        avg_price = sum(float(c['price']) for c in competitors) / len(competitors)
                        my_avg = sum(float(p['price']) for p in my_products) / len(my_products)
                        results.append({
                            "category": cat_name,
                            "competitor_count": len(competitors),
                            "avg_price": float(avg_price),
                            "my_avg_price": float(my_avg),
                            "price_position": "偏高" if my_avg > avg_price * 1.1 else ("偏低" if my_avg < avg_price * 0.9 else "适中"),
                        })

        if not results:
            return {"reply": "暂无竞品数据。", "action": "competitor_analysis", "data": None}

        reply = "**竞品分析报告**：\n\n"
        for r in results:
            reply += f"**{r['category']}**：{r['competitor_count']}个竞品，市场均价¥{r['avg_price']:.0f}，您的均价¥{r['my_avg_price']:.0f}（{r['price_position']}）\n"

        return {"reply": reply, "action": "competitor_analysis", "data": results}

    # ============ 5. 智能定价 ============

    async def _handle_smart_pricing(self, merchant_id: int, params: Dict, message: str) -> Dict:
        """根据市场行情给出调价建议"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT p.id, p.name, p.price, p.sales, p.category_id
                    FROM products p
                    JOIN merchant_products mp ON p.id = mp.product_id
                    WHERE mp.merchant_id = %s AND p.status = 'on_sale'
                    ORDER BY p.sales DESC LIMIT 10
                """, (merchant_id,))
                my_products = await cur.fetchall()

                if not my_products:
                    return {"reply": "您还没有商品。", "action": "smart_pricing", "data": None}

                pricing_suggestions = []
                for prod in my_products:
                    # 查询同类商品均价
                    await cur.execute("""
                        SELECT AVG(price) as avg_price, MIN(price) as min_price, MAX(price) as max_price
                        FROM products WHERE category_id = %s AND status = 'on_sale' AND id != %s
                    """, (prod['category_id'], prod['id']))
                    market = await cur.fetchone()

                    if market and market['avg_price']:
                        avg = float(market['avg_price'])
                        my_price = float(prod['price'])
                        diff_pct = (my_price - avg) / avg * 100

                        if diff_pct > 15:
                            suggestion = f"建议降价{diff_pct:.0f}%，当前高于市场均价"
                        elif diff_pct < -15:
                            suggestion = f"可以考虑涨价，当前低于市场均价{abs(diff_pct):.0f}%"
                        else:
                            suggestion = "定价合理，无需调整"

                        pricing_suggestions.append({
                            "name": prod['name'],
                            "current_price": my_price,
                            "market_avg": avg,
                            "suggestion": suggestion,
                        })

        if not pricing_suggestions:
            return {"reply": "暂无定价建议数据。", "action": "smart_pricing", "data": None}

        reply = "**智能定价建议**：\n\n"
        for p in pricing_suggestions:
            reply += f"- **{p['name']}**：当前¥{p['current_price']:.0f}，市场均价¥{p['market_avg']:.0f}\n  → {p['suggestion']}\n"

        return {"reply": reply, "action": "smart_pricing", "data": pricing_suggestions}

    # ============ 6. 营销文案生成 ============

    async def _handle_marketing_copy(self, merchant_id: int, params: Dict, message: str) -> Dict:
        """生成商品营销文案"""
        product_name = params.get('name', '') if params else ''

        if not product_name:
            # 提取商品名
            import re
            match = re.search(r'(?:给|为|生成|写)(.+?)(?:的|写|生成)', message)
            if match:
                product_name = match.group(1)

        if not product_name:
            return {"reply": "请告诉我您想为哪个商品生成营销文案？例如：「给蓝牙耳机写详情页文案」", "action": "marketing_copy", "data": None}

        prompt = f"""为以下商品生成营销文案：

商品名称：{product_name}

请生成以下内容：
1. **标题**（15字以内，吸引眼球）
2. **卖点**（3-5个核心卖点，每个一句话）
3. **详情页文案**（200字左右，突出优势）
4. **短视频脚本**（15秒口播文案）

返回JSON格式：{{"title": "", "selling_points": [], "description": "", "video_script": ""}}"""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-v4-flash", messages=[{"role": "user", "content": prompt}],
                max_tokens=500, temperature=0.8,
            )
            content = response.choices[0].message.content.strip()
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                copy_data = json.loads(json_match.group())
                reply = f"**营销文案 - {product_name}**：\n\n"
                reply += f"**标题**：{copy_data.get('title', '')}\n\n"
                reply += f"**卖点**：\n"
                for point in copy_data.get('selling_points', []):
                    reply += f"- {point}\n"
                reply += f"\n**详情页文案**：\n{copy_data.get('description', '')}\n\n"
                reply += f"**短视频脚本**：\n{copy_data.get('video_script', '')}"
                return {"reply": reply, "action": "marketing_copy", "data": copy_data}
        except Exception as e:
            logger.error(f"Marketing copy generation failed: {e}")

        return {"reply": "文案生成失败，请稍后再试。", "action": "error", "data": None}

    # ============ 7. 销量预测 ============

    async def _handle_sales_forecast(self, merchant_id: int, params: Dict, message: str) -> Dict:
        """预测未来销量趋势"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 获取最近30天的销售数据
                await cur.execute("""
                    SELECT DATE(o.created_at) as date, SUM(oi.quantity) as quantity, SUM(oi.quantity * oi.price) as amount
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    JOIN merchant_products mp ON oi.product_id = mp.product_id
                    WHERE mp.merchant_id = %s AND o.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                    GROUP BY DATE(o.created_at)
                    ORDER BY date
                """, (merchant_id,))
                daily_sales = await cur.fetchall()

        if not daily_sales:
            return {"reply": "暂无销售数据，无法进行预测。", "action": "sales_forecast", "data": None}

        # 简单移动平均预测
        total_qty = sum(s['quantity'] for s in daily_sales)
        avg_daily = total_qty / len(daily_sales) if daily_sales else 0
        forecast_7 = avg_daily * 7
        forecast_30 = avg_daily * 30

        # 趋势判断
        if len(daily_sales) >= 7:
            recent_7 = sum(s['quantity'] for s in daily_sales[-7:]) / 7
            prev_7 = sum(s['quantity'] for s in daily_sales[-14:-7]) / 7 if len(daily_sales) >= 14 else recent_7
            trend = "上升" if recent_7 > prev_7 * 1.1 else ("下降" if recent_7 < prev_7 * 0.9 else "平稳")
        else:
            trend = "数据不足"

        reply = f"**销量预测报告**：\n\n"
        reply += f"- 近30天总销量：{total_qty}件\n"
        reply += f"- 日均销量：{avg_daily:.1f}件\n"
        reply += f"- 销售趋势：{trend}\n\n"
        reply += f"**预测**：\n"
        reply += f"- 未来7天预计销售：{forecast_7:.0f}件\n"
        reply += f"- 未来30天预计销售：{forecast_30:.0f}件\n"

        return {"reply": reply, "action": "sales_forecast", "data": {"daily_sales": [dict(s) for s in daily_sales], "forecast_7": forecast_7, "forecast_30": forecast_30}}

    # ============ 8. 商品捆绑推荐 ============

    async def _handle_bundle_recommend(self, merchant_id: int, params: Dict, message: str) -> Dict:
        """推荐搭配销售组合"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 找出一起被购买的商品
                await cur.execute("""
                    SELECT oi1.product_id as p1, oi2.product_id as p2,
                           p1.name as name1, p2.name as name2,
                           COUNT(*) as together_count
                    FROM order_items oi1
                    JOIN order_items oi2 ON oi1.order_id = oi2.order_id AND oi1.product_id < oi2.product_id
                    JOIN products p1 ON oi1.product_id = p1.id
                    JOIN products p2 ON oi2.product_id = p2.id
                    JOIN merchant_products mp1 ON oi1.product_id = mp1.product_id
                    WHERE mp1.merchant_id = %s
                    GROUP BY oi1.product_id, oi2.product_id
                    ORDER BY together_count DESC
                    LIMIT 5
                """, (merchant_id,))
                bundles = await cur.fetchall()

                # 获取商家商品
                await cur.execute("""
                    SELECT p.id, p.name, p.price
                    FROM products p
                    JOIN merchant_products mp ON p.id = mp.product_id
                    WHERE mp.merchant_id = %s AND p.status = 'on_sale'
                """, (merchant_id,))
                products = await cur.fetchall()

        if not bundles:
            # 没有共同购买数据，基于分类推荐
            if len(products) >= 2:
                reply = "**推荐搭配组合**（基于商品分类）：\n\n"
                for i in range(min(3, len(products) - 1)):
                    reply += f"- {products[i]['name']} ¥{products[i]['price']} + {products[i+1]['name']} ¥{products[i+1]['price']}\n"
                reply += "\n建议设置组合优惠价，促进关联销售。"
                return {"reply": reply, "action": "bundle_recommend", "data": products[:5]}

            return {"reply": "商品数量不足，暂无搭配推荐。", "action": "bundle_recommend", "data": None}

        reply = "**热销搭配组合**（基于真实购买数据）：\n\n"
        for b in bundles:
            reply += f"- {b['name1']} + {b['name2']}（共同购买{b['together_count']}次）\n"
        reply += "\n建议为这些组合设置优惠套装价。"

        return {"reply": reply, "action": "bundle_recommend", "data": [dict(b) for b in bundles]}

    # ============ 9. 客户评价分析 ============

    async def _handle_review_analysis(self, merchant_id: int, params: Dict, message: str) -> Dict:
        """分析客户评价，找出差评原因"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT pr.rating, pr.content, p.name, pr.created_at
                    FROM product_reviews pr
                    JOIN products p ON pr.product_id = p.id
                    JOIN merchant_products mp ON p.id = mp.product_id
                    WHERE mp.merchant_id = %s
                    ORDER BY pr.created_at DESC
                    LIMIT 50
                """, (merchant_id,))
                reviews = await cur.fetchall()

        if not reviews:
            return {"reply": "暂无客户评价数据。", "action": "review_analysis", "data": None}

        # 统计
        total = len(reviews)
        avg_rating = sum(r['rating'] for r in reviews) / total
        negative = [r for r in reviews if r['rating'] <= 2]
        positive = [r for r in reviews if r['rating'] >= 4]

        reply = f"**客户评价分析**（共{total}条）：\n\n"
        reply += f"- 平均评分：{'⭐' * round(avg_rating)} {avg_rating:.1f}/5\n"
        reply += f"- 好评率：{len(positive)/total*100:.0f}%\n"
        reply += f"- 差评数：{len(negative)}条\n\n"

        if negative:
            reply += "**差评问题汇总**：\n"
            # 用AI分析差评原因
            negative_texts = "\n".join([f"- {r['name']}: {r['content']}" for r in negative[:10]])
            prompt = f"分析以下电商差评，总结主要问题（3条以内）：\n{negative_texts}"
            try:
                response = await self.client.chat.completions.create(
                    model="deepseek-v4-flash", messages=[{"role": "user", "content": prompt}],
                    max_tokens=200, temperature=0.5,
                )
                reply += response.choices[0].message.content.strip()
            except:
                reply += "- 请查看具体差评内容分析\n"
        else:
            reply += "暂无差评，客户满意度很高！\n"

        return {"reply": reply, "action": "review_analysis", "data": {"total": total, "avg_rating": avg_rating, "negative_count": len(negative)}}

    # ============ 10. 库存智能补货 ============

    async def _handle_inventory_restock(self, merchant_id: int, params: Dict, message: str) -> Dict:
        """根据销售速度预测补货时间"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("""
                    SELECT p.id, p.name, p.stock,
                           COALESCE(SUM(oi.quantity), 0) as total_sold,
                           COUNT(DISTINCT DATE(o.created_at)) as active_days
                    FROM products p
                    JOIN merchant_products mp ON p.id = mp.product_id
                    LEFT JOIN order_items oi ON p.id = oi.product_id
                    LEFT JOIN orders o ON oi.order_id = o.id AND o.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                    WHERE mp.merchant_id = %s AND p.status = 'on_sale'
                    GROUP BY p.id
                    ORDER BY p.stock ASC
                """, (merchant_id,))
                products = await cur.fetchall()

        if not products:
            return {"reply": "暂无商品数据。", "action": "inventory_restock", "data": None}

        restock_list = []
        reply = "**库存智能补货建议**：\n\n"

        for p in products:
            stock = p['stock']
            sold = p['total_sold']
            days = max(p['active_days'], 1)
            daily_sales = sold / days if days > 0 else 0

            if daily_sales > 0:
                days_left = stock / daily_sales
            else:
                days_left = 999 if stock > 0 else 0

            if stock <= 0:
                status = "❌ 已售罄，需紧急补货！"
                restock_urgent = True
            elif days_left < 7:
                status = f"⚠️ 仅剩{days_left:.0f}天库存，建议尽快补货"
                restock_urgent = True
            elif days_left < 14:
                status = f"📊 剩余{days_left:.0f}天库存，可计划补货"
                restock_urgent = False
            else:
                status = f"✅ 库存充足（{days_left:.0f}天）"
                restock_urgent = False

            reply += f"- **{p['name']}**：库存{stock}件，日均销{daily_sales:.1f}件 → {status}\n"

            if restock_urgent:
                restock_list.append({"name": p['name'], "stock": stock, "daily_sales": daily_sales, "days_left": days_left})

        if restock_list:
            reply += f"\n**需紧急补货商品**：{len(restock_list)}件"

        return {"reply": reply, "action": "inventory_restock", "data": restock_list}

    # ============ 一般对话 ============

    async def _handle_general_chat(self, message: str, default_reply: str) -> Dict:
        if default_reply:
            return {"reply": default_reply, "action": "chat", "data": None}

        prompt = f"你是惠购商城的商家智能助手，友好地回答商家的问题。\n\n用户说：{message}\n\n请用简洁友好的语气回答（100字以内）。"

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-v4-flash", messages=[{"role": "user", "content": prompt}],
                max_tokens=200, temperature=0.7,
            )
            return {"reply": response.choices[0].message.content.strip(), "action": "chat", "data": None}
        except Exception as e:
            return {"reply": "有什么可以帮您的吗？", "action": "chat", "data": None}

    # ============ AI识图 ============

    async def generate_product_from_image(self, merchant_id: int, image_url: str) -> Dict:
        return {
            "name": "AI识别商品", "price": 99, "category": "其他",
            "description": "通过AI图片识别生成的商品描述", "stock": 100, "main_image": image_url
        }
