# -*- coding: utf-8 -*-
"""
WebSocket 连接管理器
支持用户级别的实时消息推送（订单状态变更、库存预警、促销通知等）
"""
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """管理 WebSocket 连接，支持按用户 ID 广播"""

    def __init__(self):
        # user_id -> set of WebSocket connections
        self._connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """接受并注册一个 WebSocket 连接"""
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(websocket)
        logger.info(f"WebSocket connected: user_id={user_id}, total={self.count()}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        """移除一个 WebSocket 连接"""
        if user_id in self._connections:
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info(f"WebSocket disconnected: user_id={user_id}, remaining={self.count()}")

    def count(self) -> int:
        """当前总连接数"""
        return sum(len(conns) for conns in self._connections.values())

    async def send_to_user(self, user_id: int, message: dict):
        """向指定用户的所有连接发送消息"""
        if user_id not in self._connections:
            return
        dead = []
        for ws in self._connections[user_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[user_id].discard(ws)

    async def broadcast(self, message: dict):
        """向所有连接广播消息"""
        dead_users = []
        for user_id, conns in self._connections.items():
            dead = []
            for ws in conns:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                conns.discard(ws)
            if not conns:
                dead_users.append(user_id)
        for uid in dead_users:
            del self._connections[uid]

    # ---- 便捷方法 ----

    async def notify_order_status(self, user_id: int, order_no: str, status: str, message: str = ""):
        """推送订单状态变更通知"""
        await self.send_to_user(user_id, {
            "type": "order_status",
            "order_no": order_no,
            "status": status,
            "message": message,
        })

    async def notify_stock_alert(self, user_id: int, product_name: str, stock: int):
        """推送库存预警"""
        await self.send_to_user(user_id, {
            "type": "stock_alert",
            "product_name": product_name,
            "stock": stock,
            "message": f"您关注的「{product_name}」库存仅剩 {stock} 件",
        })

    async def notify_promotion(self, user_id: int, title: str, content: str):
        """推送促销通知"""
        await self.send_to_user(user_id, {
            "type": "promotion",
            "title": title,
            "content": content,
        })


# 全局单例
ws_manager = ConnectionManager()
