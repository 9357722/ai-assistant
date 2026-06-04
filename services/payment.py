"""
支付服务模块
提供模拟支付、支付状态查询、退款等功能
"""
import time
import hashlib
import json
from typing import Optional, Dict, Any
from datetime import datetime

import aiomysql

import config


class PaymentService:
    """支付服务"""

    # 支付状态
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"

    def __init__(self, pool: aiomysql.Pool):
        self.pool = pool

    async def create_payment(
        self,
        order_id: int,
        user_id: int,
        amount: float,
        payment_method: str = "alipay"
    ) -> Dict[str, Any]:
        """
        创建支付

        Args:
            order_id: 订单ID
            user_id: 用户ID
            amount: 支付金额
            payment_method: 支付方式 (alipay, wechat)

        Returns:
            支付信息
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 验证订单
                await cur.execute(
                    "SELECT * FROM orders WHERE id = %s AND user_id = %s",
                    (order_id, user_id)
                )
                order = await cur.fetchone()

                if not order:
                    raise ValueError("订单不存在")

                if order["status"] != "pending":
                    raise ValueError(f"订单状态为 {order['status']}，无法支付")

                if float(order["total_amount"]) != amount:
                    raise ValueError("支付金额与订单金额不匹配")

                # 生成支付单号
                payment_no = self._generate_payment_no()

                # 模拟支付处理（实际项目中调用支付宝/微信API）
                payment_result = await self._process_payment(
                    payment_no=payment_no,
                    amount=amount,
                    payment_method=payment_method,
                )

                # 更新订单状态
                if payment_result["status"] == self.SUCCESS:
                    await cur.execute(
                        """UPDATE orders
                           SET status = 'paid', pay_amount = %s, paid_at = NOW()
                           WHERE id = %s""",
                        (amount, order_id)
                    )
                    await conn.commit()

                return {
                    "payment_no": payment_no,
                    "order_no": order["order_no"],
                    "amount": amount,
                    "payment_method": payment_method,
                    "status": payment_result["status"],
                    "message": payment_result["message"],
                    "paid_at": datetime.now().isoformat() if payment_result["status"] == self.SUCCESS else None,
                }

    async def query_payment_status(
        self,
        payment_no: str,
        user_id: int
    ) -> Dict[str, Any]:
        """
        查询支付状态

        Args:
            payment_no: 支付单号
            user_id: 用户ID

        Returns:
            支付状态信息
        """
        # 模拟查询（实际项目中查询支付平台）
        return {
            "payment_no": payment_no,
            "status": self.SUCCESS,
            "message": "支付成功",
        }

    async def refund(
        self,
        order_id: int,
        user_id: int,
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        退款

        Args:
            order_id: 订单ID
            user_id: 用户ID
            reason: 退款原因

        Returns:
            退款结果
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 验证订单
                await cur.execute(
                    "SELECT * FROM orders WHERE id = %s AND user_id = %s",
                    (order_id, user_id)
                )
                order = await cur.fetchone()

                if not order:
                    raise ValueError("订单不存在")

                if order["status"] not in ["paid", "shipped"]:
                    raise ValueError(f"订单状态为 {order['status']}，无法退款")

                # 模拟退款处理
                refund_no = f"REF{int(time.time() * 1000)}"

                # 恢复库存
                await cur.execute(
                    "SELECT * FROM order_items WHERE order_id = %s",
                    (order_id,)
                )
                items = await cur.fetchall()

                for item in items:
                    await cur.execute(
                        "UPDATE products SET stock = stock + %s, sales = sales - %s WHERE id = %s",
                        (item["quantity"], item["quantity"], item["product_id"])
                    )

                # 更新订单状态
                await cur.execute(
                    "UPDATE orders SET status = 'cancelled' WHERE id = %s",
                    (order_id,)
                )

                await conn.commit()

                return {
                    "refund_no": refund_no,
                    "order_no": order["order_no"],
                    "amount": float(order["total_amount"]),
                    "status": "success",
                    "message": "退款成功",
                    "reason": reason,
                }

    async def _process_payment(
        self,
        payment_no: str,
        amount: float,
        payment_method: str
    ) -> Dict[str, Any]:
        """
        处理支付（模拟）

        实际项目中，这里会调用支付宝/微信的支付API
        """
        # 模拟支付延迟
        import asyncio
        await asyncio.sleep(0.1)

        # 模拟支付成功（实际项目中根据回调更新状态）
        return {
            "status": self.SUCCESS,
            "message": "支付成功",
            "transaction_id": f"TXN{int(time.time() * 1000)}",
        }

    def _generate_payment_no(self) -> str:
        """生成支付单号（UUID，不可预测）"""
        import uuid
        return f"PAY{uuid.uuid4().hex[:16].upper()}"

    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """
        生成签名（模拟）

        实际项目中使用支付宝/微信的签名算法
        """
        # 排序参数
        sorted_params = sorted(params.items())
        sign_string = "&".join([f"{k}={v}" for k, v in sorted_params])

        # 使用 HMAC-SHA256 签名
        import hmac
        import hashlib
        sign = hmac.new(
            config.SECRET_KEY.encode(),
            sign_string.encode(),
            hashlib.sha256
        ).hexdigest()

        return sign


class AlipayMock:
    """支付宝模拟"""

    @staticmethod
    async def create_trade(
        out_trade_no: str,
        total_amount: float,
        subject: str
    ) -> Dict[str, Any]:
        """创建交易（模拟）"""
        return {
            "trade_no": f"ALI{int(time.time() * 1000)}",
            "out_trade_no": out_trade_no,
            "total_amount": total_amount,
            "subject": subject,
            "status": "TRADE_SUCCESS",
            "gmt_payment": datetime.now().isoformat(),
        }

    @staticmethod
    async def query_trade(out_trade_no: str) -> Dict[str, Any]:
        """查询交易（模拟）"""
        return {
            "trade_no": f"ALI{int(time.time() * 1000)}",
            "out_trade_no": out_trade_no,
            "status": "TRADE_SUCCESS",
        }

    @staticmethod
    async def refund_trade(
        out_trade_no: str,
        refund_amount: float,
        refund_reason: str
    ) -> Dict[str, Any]:
        """退款（模拟）"""
        return {
            "trade_no": f"ALI{int(time.time() * 1000)}",
            "out_trade_no": out_trade_no,
            "refund_fee": refund_amount,
            "status": "REFUND_SUCCESS",
        }


class WechatPayMock:
    """微信支付模拟"""

    @staticmethod
    async def create_order(
        out_trade_no: str,
        total_fee: int,
        body: str
    ) -> Dict[str, Any]:
        """创建订单（模拟）"""
        return {
            "prepay_id": f"WX{int(time.time() * 1000)}",
            "out_trade_no": out_trade_no,
            "total_fee": total_fee,
            "body": body,
        }

    @staticmethod
    async def query_order(out_trade_no: str) -> Dict[str, Any]:
        """查询订单（模拟）"""
        return {
            "out_trade_no": out_trade_no,
            "trade_state": "SUCCESS",
            "total_fee": 0,
        }

    @staticmethod
    async def refund_order(
        out_trade_no: str,
        refund_fee: int,
        refund_desc: str
    ) -> Dict[str, Any]:
        """退款（模拟）"""
        return {
            "out_trade_no": out_trade_no,
            "refund_fee": refund_fee,
            "status": "SUCCESS",
        }
