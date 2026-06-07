# -*- coding: utf-8 -*-
"""
商家智能助手 Agent
功能：
1. 商品智能上传 - 自动生成标题、描述、定价建议
2. 销售数据分析 - 趋势分析、热销排行、库存预警
3. 智能客服 - 回答买家咨询、处理售后
4. 经营建议 - 营销、定价、选品建议
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import aiomysql
from openai import AsyncOpenAI

import config

logger = logging.getLogger(__name__)


class MerchantAgent:
    """商家智能助手"""

    def __init__(self, pool: aiomysql.Pool):
        self.pool = pool
        self.client = AsyncOpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )

    async def chat(self, merchant_id: int, message: str, context: List[Dict] = None) -> Dict[str, Any]:
        """
        与商家Agent对话

        Args:
            merchant_id: 商家ID
            message: 用户消息
            context: 对话上下文

        Returns:
            {"reply": "回复内容", "action": "执行的动作", "data": 相关数据}
        """
        # 获取商家信息和数据
        merchant_info = await self._get_merchant_info(merchant_id)
        dashboard_data = await self._get_dashboard_data(merchant_id)

        # 解析用户意图
        intent = await self._parse_intent(message, merchant_info, dashboard_data)

        # 根据意图执行动作
        result = await self._execute_action(merchant_id, intent, message)

        return result

    async def _get_merchant_info(self, merchant_id: int) -> Dict:
        """获取商家信息"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute("SELECT * FROM merchants WHERE id = %s", (merchant_id,))
                return await cur.fetchone() or {}

    async def _get_dashboard_data(self, merchant_id: int) -> Dict:
        """获取仪表板数据"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 商品数量
                await cur.execute("""
                    SELECT COUNT(*) as total_products
                    FROM merchant_products WHERE merchant_id = %s
                """, (merchant_id,))
                products = (await cur.fetchone())['total_products']

                # 今日订单和销售额
                await cur.execute("""
                    SELECT COUNT(DISTINCT o.id) as today_orders,
                           COALESCE(SUM(oi.quantity * oi.price), 0) as today_sales
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    JOIN merchant_products mp ON oi.product_id = mp.product_id
                    WHERE mp.merchant_id = %s AND DATE(o.created_at) = CURDATE()
                """, (merchant_id,))
                today = await cur.fetchone()

                # 待发货订单
                await cur.execute("""
                    SELECT COUNT(DISTINCT o.id) as pending_orders
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    JOIN merchant_products mp ON oi.product_id = mp.product_id
                    WHERE mp.merchant_id = %s AND o.status = 'paid'
                """, (merchant_id,))
                pending = (await cur.fetchone())['pending_orders']

                # 热销商品 TOP5
                await cur.execute("""
                    SELECT p.name, p.price, COALESCE(SUM(oi.quantity), 0) as sales
                    FROM products p
                    JOIN merchant_products mp ON p.id = mp.product_id
                    LEFT JOIN order_items oi ON p.id = oi.product_id
                    WHERE mp.merchant_id = %s
                    GROUP BY p.id
                    ORDER BY sales DESC
                    LIMIT 5
                """, (merchant_id,))
                hot_products = await cur.fetchall()

                # 库存预警（库存 < 10）
                await cur.execute("""
                    SELECT p.name, p.stock
                    FROM products p
                    JOIN merchant_products mp ON p.id = mp.product_id
                    WHERE mp.merchant_id = %s AND p.stock < 10
                    ORDER BY p.stock ASC
                """, (merchant_id,))
                low_stock = await cur.fetchall()

                return {
                    'total_products': products,
                    'today_orders': today['today_orders'],
                    'today_sales': float(today['today_sales']),
                    'pending_orders': pending,
                    'hot_products': hot_products,
                    'low_stock': low_stock
                }

    async def _parse_intent(self, message: str, merchant_info: Dict, dashboard_data: Dict, context: List[Dict] = None) -> Dict:
        """解析用户意图"""
        system_prompt = f"""你是惠购商城的商家智能助手，帮助商家管理店铺。

当前商家信息：
- 店铺名称：{merchant_info.get('shop_name', '未知')}
- 商品数量：{dashboard_data.get('total_products', 0)}
- 今日订单：{dashboard_data.get('today_orders', 0)}
- 今日销售额：¥{dashboard_data.get('today_sales', 0)}
- 待发货订单：{dashboard_data.get('pending_orders', 0)}

你可以帮助商家：
1. 上传商品 - 分析商品信息，生成标题、描述、定价建议
2. 数据分析 - 查看销售趋势、热销商品、库存预警
3. 经营建议 - 提供营销、定价、选品建议
4. 回答问题 - 解答商家运营相关问题

请分析用户的消息，返回JSON格式：
{{
    "intent": "upload_product|analytics|advice|general_chat",
    "parameters": {{
        // 根据intent不同，参数不同
        // upload_product: {{"name": "商品名", "price": 价格, "category": "分类"}}
        // analytics: {{"type": "overview|hot_products|low_stock"}}
        // advice: {{"topic": "pricing|marketing|selection"}}
        // general_chat: null
    }},
    "reply": "你的回复内容（如果需要调用工具，这里可以简短说明）"
}}

只返回JSON，不要其他内容。"""

        messages = [{"role": "system", "content": system_prompt}]
        if context:
            messages.extend(context[-5:])  # 只保留最近5条上下文
        messages.append({"role": "user", "content": message})

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
            )
            content = response.choices[0].message.content.strip()
            # 提取JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"Intent parsing failed: {e}")

        # 降级处理
        return {"intent": "general_chat", "parameters": None, "reply": message}

    async def _execute_action(self, merchant_id: int, intent: Dict, original_message: str) -> Dict:
        """执行意图对应的动作"""
        action = intent.get('intent', 'general_chat')
        params = intent.get('parameters')

        if action == 'upload_product':
            return await self._handle_upload_product(merchant_id, params, original_message)
        elif action == 'analytics':
            return await self._handle_analytics(merchant_id, params)
        elif action == 'advice':
            return await self._handle_advice(merchant_id, params, original_message)
        else:
            return await self._handle_general_chat(original_message, intent.get('reply', ''))

    async def _handle_upload_product(self, merchant_id: int, params: Dict, message: str) -> Dict:
        """处理商品上传"""
        if params and params.get('name'):
            # 有明确的商品信息，生成完整建议
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
            # 没有明确信息，引导用户提供
            return {
                "reply": "请告诉我您要上传的商品信息：\n\n"
                        "1. **商品名称**是什么？\n"
                        "2. **价格**大概多少？\n"
                        "3. 属于哪个**分类**？（手机/电脑/耳机/服装等）\n\n"
                        "例如：「上传一款蓝牙耳机，价格199，属于耳机分类」",
                "action": "wait_input",
                "data": None
            }

    async def _generate_product_info(self, params: Dict) -> Dict:
        """生成商品信息（调用LLM优化）"""
        name = params.get('name', '')
        price = params.get('price', 0)
        category = params.get('category', '')

        prompt = f"""根据以下商品信息，生成完整的商品详情：

商品名：{name}
价格：{price}
分类：{category}

请返回JSON：
{{
    "name": "优化后的商品名称（更吸引人）",
    "price": 建议价格（考虑市场行情）,
    "category": "分类名称",
    "description": "商品描述（100字左右，突出卖点）",
    "stock": 建议库存量
}}"""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7,
            )
            content = response.choices[0].message.content.strip()
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"Generate product info failed: {e}")

        # 降级返回原始信息
        return {
            "name": name,
            "price": price,
            "category": category,
            "description": f"优质{name}，品质保证",
            "stock": 100
        }

    async def _handle_analytics(self, merchant_id: int, params: Dict) -> Dict:
        """处理数据分析"""
        analytics_type = params.get('type', 'overview') if params else 'overview'
        data = await self._get_dashboard_data(merchant_id)

        if analytics_type == 'hot_products':
            products = data.get('hot_products', [])
            if products:
                product_list = "\n".join([
                    f"- {p['name']}: 销量{p['sales']}件, ¥{p['price']}"
                    for p in products
                ])
                return {
                    "reply": f"**热销商品 TOP5**：\n\n{product_list}\n\n"
                            f"建议：热销商品可适当备货，避免缺货影响销量。",
                    "action": "show_analytics",
                    "data": data
                }
            else:
                return {
                    "reply": "暂无销售数据，快去推广您的商品吧！",
                    "action": "show_analytics",
                    "data": data
                }

        elif analytics_type == 'low_stock':
            low_stock = data.get('low_stock', [])
            if low_stock:
                stock_list = "\n".join([
                    f"- {p['name']}: 仅剩{p['stock']}件"
                    for p in low_stock
                ])
                return {
                    "reply": f"**库存预警**：\n\n{stock_list}\n\n"
                            f"建议：请及时补货，避免影响销售。",
                    "action": "show_analytics",
                    "data": data
                }
            else:
                return {
                    "reply": "所有商品库存充足，无需补货！",
                    "action": "show_analytics",
                    "data": data
                }

        else:  # overview
            return {
                "reply": f"**今日经营概览**：\n\n"
                        f"- 商品总数：{data['total_products']}件\n"
                        f"- 今日订单：{data['today_orders']}笔\n"
                        f"- 今日销售额：¥{data['today_sales']:.2f}\n"
                        f"- 待发货订单：{data['pending_orders']}笔\n\n"
                        f"{'有' + str(data['pending_orders']) + '笔订单待发货，请及时处理！' if data['pending_orders'] > 0 else '暂无待发货订单，可以休息一下~'}",
                "action": "show_analytics",
                "data": data
            }

    async def _handle_advice(self, merchant_id: int, params: Dict, message: str) -> Dict:
        """处理经营建议"""
        topic = params.get('topic', 'general') if params else 'general'
        data = await self._get_dashboard_data(merchant_id)

        prompt = f"""你是电商运营专家，为商家提供经营建议。

当前店铺数据：
- 商品数量：{data['total_products']}件
- 今日销售额：¥{data['today_sales']:.2f}
- 待发货订单：{data['pending_orders']}笔
- 热销商品：{json.dumps(data.get('hot_products', []), ensure_ascii=False)}
- 库存预警：{json.dumps(data.get('low_stock', []), ensure_ascii=False)}

用户问题：{message}

请提供具体、可执行的建议（100字以内）。"""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7,
            )
            reply = response.choices[0].message.content.strip()
            return {
                "reply": reply,
                "action": "show_advice",
                "data": {"topic": topic}
            }
        except Exception as e:
            logger.error(f"Generate advice failed: {e}")
            return {
                "reply": "抱歉，暂时无法生成建议，请稍后再试。",
                "action": "error",
                "data": None
            }

    async def _handle_general_chat(self, message: str, default_reply: str) -> Dict:
        """处理一般对话"""
        if default_reply:
            return {
                "reply": default_reply,
                "action": "chat",
                "data": None
            }

        prompt = f"""你是惠购商城的商家智能助手，友好地回答商家的问题。

用户说：{message}

请用简洁友好的语气回答（100字以内）。"""

        try:
            response = await self.client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7,
            )
            reply = response.choices[0].message.content.strip()
            return {
                "reply": reply,
                "action": "chat",
                "data": None
            }
        except Exception as e:
            return {
                "reply": "有什么可以帮您的吗？我可以帮您：\n1. 上传商品\n2. 查看数据分析\n3. 获取经营建议",
                "action": "chat",
                "data": None
            }

    async def generate_product_from_image(self, merchant_id: int, image_url: str) -> Dict:
        """
        从图片生成商品信息（AI识图）

        Args:
            merchant_id: 商家ID
            image_url: 图片URL

        Returns:
            生成的商品信息
        """
        # 这里可以接入多模态模型识别图片
        # 目前返回示例数据
        return {
            "name": "AI识别商品",
            "price": 99,
            "category": "其他",
            "description": "通过AI图片识别生成的商品描述",
            "stock": 100,
            "main_image": image_url
        }
