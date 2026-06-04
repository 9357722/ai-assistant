"""
管理后台路由模块
提供商品管理、订单管理、用户管理、数据统计等接口
"""
import json
import aiomysql
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

import config
from db import get_pool
from auth import get_current_admin, TokenData
from models.product import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


# ============ 数据库连接 ============

async def get_db():
    """获取全局连接池"""
    return get_pool()


# ============ 请求模型 ============

class OrderStatusUpdate(BaseModel):
    """订单状态更新"""
    status: str = Field(..., description="新状态: shipped, completed")
    tracking_no: Optional[str] = Field(None, description="物流单号")


class UserStatusUpdate(BaseModel):
    """用户状态更新"""
    is_active: bool = Field(..., description="是否启用")


# ============ 数据统计 ============

@router.get("/statistics")
async def get_statistics(
    current_user: TokenData = Depends(get_current_admin),
    pool=Depends(get_db),
):
    """获取数据统计"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 用户统计
            await cur.execute("SELECT COUNT(*) as total FROM users")
            total_users = (await cur.fetchone())["total"]

            await cur.execute("SELECT COUNT(*) as total FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
            new_users_week = (await cur.fetchone())["total"]

            # 商品统计
            await cur.execute("SELECT COUNT(*) as total FROM products WHERE status = 'on_sale'")
            total_products = (await cur.fetchone())["total"]

            # 订单统计
            await cur.execute("SELECT COUNT(*) as total FROM orders")
            total_orders = (await cur.fetchone())["total"]

            await cur.execute("SELECT COUNT(*) as total FROM orders WHERE status = 'pending'")
            pending_orders = (await cur.fetchone())["total"]

            await cur.execute("SELECT COUNT(*) as total FROM orders WHERE status = 'paid'")
            paid_orders = (await cur.fetchone())["total"]

            # 销售额统计
            await cur.execute("""
                SELECT COALESCE(SUM(total_amount), 0) as total
                FROM orders
                WHERE status IN ('paid', 'shipped', 'completed')
            """)
            total_sales = float((await cur.fetchone())["total"])

            await cur.execute("""
                SELECT COALESCE(SUM(total_amount), 0) as total
                FROM orders
                WHERE status IN ('paid', 'shipped', 'completed')
                AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """)
            sales_week = float((await cur.fetchone())["total"])

            # 今日统计
            await cur.execute("""
                SELECT COUNT(*) as orders, COALESCE(SUM(total_amount), 0) as sales
                FROM orders
                WHERE DATE(created_at) = CURDATE()
                AND status IN ('paid', 'shipped', 'completed')
            """)
            today_stats = await cur.fetchone()

            return {
                "users": {
                    "total": total_users,
                    "new_this_week": new_users_week,
                },
                "products": {
                    "total": total_products,
                },
                "orders": {
                    "total": total_orders,
                    "pending": pending_orders,
                    "paid": paid_orders,
                },
                "sales": {
                    "total": total_sales,
                    "this_week": sales_week,
                    "today": float(today_stats["sales"]),
                    "today_orders": today_stats["orders"],
                },
            }


# ============ 商品管理 ============

@router.get("/products")
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    keyword: Optional[str] = Query(None),
    current_user: TokenData = Depends(get_current_admin),
    pool=Depends(get_db),
):
    """获取商品列表（管理员）"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            conditions = []
            params = []

            if status_filter:
                conditions.append("p.status = %s")
                params.append(status_filter)

            if keyword:
                conditions.append("(p.name LIKE %s OR p.description LIKE %s)")
                params.extend([f"%{keyword}%", f"%{keyword}%"])

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 获取总数
            count_sql = f"SELECT COUNT(*) as total FROM products p WHERE {where_clause}"
            await cur.execute(count_sql, params)
            total = (await cur.fetchone())["total"]

            # 获取分页数据
            offset = (page - 1) * page_size
            data_sql = f"""
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE {where_clause}
                ORDER BY p.created_at DESC
                LIMIT %s OFFSET %s
            """
            await cur.execute(data_sql, params + [page_size, offset])
            products = await cur.fetchall()

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": products,
            }


@router.post("/products", status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: TokenData = Depends(get_current_admin),
    pool=Depends(get_db),
):
    """创建商品（管理员）"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            images_json = json.dumps(product_data.images) if product_data.images else None

            await cur.execute(
                """INSERT INTO products (name, price, platform, category_id, description, main_image, images, stock, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    product_data.name,
                    product_data.price,
                    product_data.platform,
                    product_data.category_id,
                    product_data.description,
                    product_data.main_image,
                    images_json,
                    product_data.stock,
                    product_data.status,
                )
            )
            await conn.commit()

            return {"id": cur.lastrowid, "message": "商品创建成功"}


@router.put("/products/{product_id}")
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    current_user: TokenData = Depends(get_current_admin),
    pool=Depends(get_db),
):
    """更新商品（管理员）"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 检查商品是否存在
            await cur.execute("SELECT id FROM products WHERE id = %s", (product_id,))
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="商品不存在")

            # 构建更新语句
            update_fields = []
            update_values = []

            if product_data.name is not None:
                update_fields.append("name = %s")
                update_values.append(product_data.name)

            if product_data.price is not None:
                update_fields.append("price = %s")
                update_values.append(product_data.price)

            if product_data.platform is not None:
                update_fields.append("platform = %s")
                update_values.append(product_data.platform)

            if product_data.category_id is not None:
                update_fields.append("category_id = %s")
                update_values.append(product_data.category_id)

            if product_data.description is not None:
                update_fields.append("description = %s")
                update_values.append(product_data.description)

            if product_data.main_image is not None:
                update_fields.append("main_image = %s")
                update_values.append(product_data.main_image)

            if product_data.images is not None:
                update_fields.append("images = %s")
                update_values.append(json.dumps(product_data.images))

            if product_data.stock is not None:
                update_fields.append("stock = %s")
                update_values.append(product_data.stock)

            if product_data.status is not None:
                update_fields.append("status = %s")
                update_values.append(product_data.status)

            if not update_fields:
                raise HTTPException(status_code=400, detail="没有要更新的内容")

            update_values.append(product_id)
            sql = f"UPDATE products SET {', '.join(update_fields)} WHERE id = %s"
            await cur.execute(sql, update_values)
            await conn.commit()

            return {"message": "商品更新成功"}


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    current_user: TokenData = Depends(get_current_admin),
    pool=Depends(get_db),
):
    """删除商品（管理员，软删除）"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE products SET status = 'off_sale' WHERE id = %s",
                (product_id,)
            )
            await conn.commit()

            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="商品不存在")

            return {"message": "商品已下架"}


# ============ 订单管理 ============

@router.get("/orders")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: TokenData = Depends(get_current_admin),
    pool=Depends(get_db),
):
    """获取订单列表（管理员）"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            conditions = []
            params = []

            if status_filter:
                conditions.append("o.status = %s")
                params.append(status_filter)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 获取总数
            count_sql = f"SELECT COUNT(*) as total FROM orders o WHERE {where_clause}"
            await cur.execute(count_sql, params)
            total = (await cur.fetchone())["total"]

            # 获取订单列表
            offset = (page - 1) * page_size
            order_sql = f"""
                SELECT o.*, u.username
                FROM orders o
                JOIN users u ON o.user_id = u.id
                WHERE {where_clause}
                ORDER BY o.created_at DESC
                LIMIT %s OFFSET %s
            """
            await cur.execute(order_sql, params + [page_size, offset])
            orders = await cur.fetchall()

            # 批量获取订单项（避免 N+1 查询）
            order_ids = [order["id"] for order in orders]
            items_map = {}

            if order_ids:
                ph = ",".join(["%s"] * len(order_ids))
                await cur.execute(f"SELECT * FROM order_items WHERE order_id IN ({ph})", order_ids)
                for item in await cur.fetchall():
                    items_map.setdefault(item["order_id"], []).append(item)

            order_list = []
            for order in orders:
                items = items_map.get(order["id"], [])

                # 解析地址快照
                address_snapshot = order.get("address_snapshot")
                if isinstance(address_snapshot, str):
                    address_snapshot = json.loads(address_snapshot)

                order_list.append({
                    "id": order["id"],
                    "order_no": order["order_no"],
                    "username": order["username"],
                    "total_amount": float(order["total_amount"]),
                    "status": order["status"],
                    "address_snapshot": address_snapshot,
                    "remark": order["remark"],
                    "items": [
                        {
                            "id": item["id"],
                            "product_name": item["product_name"],
                            "price": float(item["price"]),
                            "quantity": item["quantity"],
                        }
                        for item in items
                    ],
                    "created_at": order["created_at"].isoformat() if order["created_at"] else None,
                    "paid_at": order["paid_at"].isoformat() if order["paid_at"] else None,
                })

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": order_list,
            }


@router.put("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    current_user: TokenData = Depends(get_current_admin),
    pool=Depends(get_db),
):
    """更新订单状态（管理员）"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 检查订单是否存在
            await cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
            order = await cur.fetchone()
            if not order:
                raise HTTPException(status_code=404, detail="订单不存在")

            # 验证状态转换
            valid_transitions = {
                "paid": ["shipped"],
                "shipped": ["completed"],
            }

            current_status = order["status"]
            if current_status not in valid_transitions:
                raise HTTPException(
                    status_code=400,
                    detail=f"当前状态 {current_status} 不允许更新"
                )

            if status_data.status not in valid_transitions[current_status]:
                raise HTTPException(
                    status_code=400,
                    detail=f"不允许从 {current_status} 转换到 {status_data.status}"
                )

            # 更新状态
            update_fields = ["status = %s"]
            update_values = [status_data.status]

            if status_data.status == "shipped":
                update_fields.append("shipped_at = NOW()")
            elif status_data.status == "completed":
                update_fields.append("completed_at = NOW()")

            update_values.append(order_id)
            sql = f"UPDATE orders SET {', '.join(update_fields)} WHERE id = %s"
            await cur.execute(sql, update_values)
            await conn.commit()

            return {"message": f"订单状态已更新为 {status_data.status}"}


# ============ 用户管理 ============

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    current_user: TokenData = Depends(get_current_admin),
    pool=Depends(get_db),
):
    """获取用户列表（管理员）"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            conditions = []
            params = []

            if keyword:
                conditions.append("(username LIKE %s OR email LIKE %s OR phone LIKE %s)")
                params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 获取总数
            count_sql = f"SELECT COUNT(*) as total FROM users WHERE {where_clause}"
            await cur.execute(count_sql, params)
            total = (await cur.fetchone())["total"]

            # 获取用户列表
            offset = (page - 1) * page_size
            user_sql = f"""
                SELECT id, username, email, phone, role, is_active, created_at
                FROM users
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            await cur.execute(user_sql, params + [page_size, offset])
            users = await cur.fetchall()

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": users,
            }


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    status_data: UserStatusUpdate,
    current_user: TokenData = Depends(get_current_admin),
    pool=Depends(get_db),
):
    """更新用户状态（管理员）"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # 检查用户是否存在
            await cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="用户不存在")

            # 不能禁用自己
            if user_id == current_user.user_id:
                raise HTTPException(status_code=400, detail="不能禁用自己")

            # 更新状态
            await cur.execute(
                "UPDATE users SET is_active = %s WHERE id = %s",
                (status_data.is_active, user_id)
            )
            await conn.commit()

            return {"message": f"用户状态已更新为 {'启用' if status_data.is_active else '禁用'}"}


# ============ 分类管理 ============

@router.get("/categories")
async def list_categories(
    current_user: TokenData = Depends(get_current_admin),
    pool=Depends(get_db),
):
    """获取分类列表（管理员）"""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM categories ORDER BY sort_order, id")
            categories = await cur.fetchall()

            # 构建树形结构
            category_map = {cat["id"]: cat for cat in categories}
            root_categories = []

            for cat in categories:
                cat["children"] = []
                if cat["parent_id"] is None:
                    root_categories.append(cat)
                else:
                    parent = category_map.get(cat["parent_id"])
                    if parent:
                        parent["children"].append(cat)

            return root_categories


class CategoryCreate(BaseModel):
    """创建分类请求"""
    name: str = Field(..., max_length=50)
    parent_id: Optional[int] = None
    icon: Optional[str] = None
    sort_order: int = 0


@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_user: TokenData = Depends(get_current_admin),
    pool=Depends(get_db),
):
    """创建分类（管理员）"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # 检查父分类是否存在
            if category_data.parent_id:
                await cur.execute("SELECT id FROM categories WHERE id = %s", (category_data.parent_id,))
                if not await cur.fetchone():
                    raise HTTPException(status_code=400, detail="父分类不存在")

            await cur.execute(
                "INSERT INTO categories (name, parent_id, icon, sort_order) VALUES (%s, %s, %s, %s)",
                (category_data.name, category_data.parent_id, category_data.icon, category_data.sort_order)
            )
            await conn.commit()

            return {"id": cur.lastrowid, "message": "分类创建成功"}
