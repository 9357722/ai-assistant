"""
商品服务层
处理商品相关的业务逻辑
"""
import json
from typing import Optional, List, Tuple

import aiomysql

import config
from models.product import (
    ProductCreate,
    ProductUpdate,
    ProductQuery,
    ProductResponse,
    ProductListResponse,
    ReviewCreate,
    ReviewResponse,
    ReviewListResponse,
)


class ProductService:
    """商品服务"""

    def __init__(self, pool: aiomysql.Pool):
        self.pool = pool

    async def get_products(self, query: ProductQuery) -> ProductListResponse:
        """
        获取商品列表（支持筛选、排序、分页）

        Args:
            query: 查询参数

        Returns:
            商品列表响应
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 构建 WHERE 条件
                conditions = []
                params = []

                if query.keyword:
                    conditions.append("(p.name LIKE %s OR p.description LIKE %s)")
                    params.extend([f"%{query.keyword}%", f"%{query.keyword}%"])

                if query.category_id:
                    conditions.append("p.category_id = %s")
                    params.append(query.category_id)

                if query.min_price is not None:
                    conditions.append("p.price >= %s")
                    params.append(query.min_price)

                if query.max_price is not None:
                    conditions.append("p.price <= %s")
                    params.append(query.max_price)

                if query.platform:
                    conditions.append("p.platform = %s")
                    params.append(query.platform)

                if query.status:
                    conditions.append("p.status = %s")
                    params.append(query.status)
                else:
                    conditions.append("p.status = 'on_sale'")

                where_clause = " AND ".join(conditions) if conditions else "1=1"

                # 排序
                valid_sort_fields = ["created_at", "price", "sales", "name"]
                valid_sort_orders = {"asc": "ASC", "desc": "DESC"}
                sort_by = query.sort_by if query.sort_by in valid_sort_fields else "created_at"
                sort_order = valid_sort_orders.get(query.sort_order.lower(), "DESC")

                # 获取总数
                count_sql = f"SELECT COUNT(*) as total FROM products p WHERE {where_clause}"
                await cur.execute(count_sql, params)
                total = (await cur.fetchone())["total"]

                # 获取分页数据
                offset = (query.page - 1) * query.page_size
                data_sql = f"""
                    SELECT p.*, c.name as category_name,
                           COALESCE(AVG(r.rating), 0) as rating,
                           COUNT(DISTINCT r.id) as review_count
                    FROM products p
                    LEFT JOIN categories c ON p.category_id = c.id
                    LEFT JOIN product_reviews r ON p.id = r.product_id
                    WHERE {where_clause}
                    GROUP BY p.id
                    ORDER BY p.{sort_by} {sort_order}
                    LIMIT %s OFFSET %s
                """
                params.extend([query.page_size, offset])
                await cur.execute(data_sql, params)
                products = await cur.fetchall()

                # 处理 JSON 字段
                items = []
                for product in products:
                    if product.get("images") and isinstance(product["images"], str):
                        product["images"] = json.loads(product["images"])
                    product["rating"] = round(float(product["rating"]), 1) if product["rating"] else None
                    items.append(ProductResponse(**product))

                return ProductListResponse(
                    total=total,
                    page=query.page,
                    page_size=query.page_size,
                    items=items,
                )

    async def get_product_by_id(self, product_id: int) -> Optional[ProductResponse]:
        """
        根据ID获取商品详情

        Args:
            product_id: 商品ID

        Returns:
            商品响应或None
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                sql = """
                    SELECT p.*, c.name as category_name,
                           COALESCE(AVG(r.rating), 0) as rating,
                           COUNT(DISTINCT r.id) as review_count
                    FROM products p
                    LEFT JOIN categories c ON p.category_id = c.id
                    LEFT JOIN product_reviews r ON p.id = r.product_id
                    WHERE p.id = %s
                    GROUP BY p.id
                """
                await cur.execute(sql, (product_id,))
                product = await cur.fetchone()

                if not product:
                    return None

                if product.get("images") and isinstance(product["images"], str):
                    product["images"] = json.loads(product["images"])
                product["rating"] = round(float(product["rating"]), 1) if product["rating"] else None

                return ProductResponse(**product)

    async def create_product(self, product_data: ProductCreate) -> ProductResponse:
        """
        创建商品

        Args:
            product_data: 商品数据

        Returns:
            创建的商品响应
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                images_json = json.dumps(product_data.images) if product_data.images else None

                sql = """
                    INSERT INTO products (name, price, platform, category_id, description, main_image, images, stock, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                await cur.execute(sql, (
                    product_data.name,
                    product_data.price,
                    product_data.platform,
                    product_data.category_id,
                    product_data.description,
                    product_data.main_image,
                    images_json,
                    product_data.stock,
                    product_data.status,
                ))
                await conn.commit()

                product_id = cur.lastrowid
                return await self.get_product_by_id(product_id)

    async def update_product(self, product_id: int, product_data: ProductUpdate) -> Optional[ProductResponse]:
        """
        更新商品

        Args:
            product_id: 商品ID
            product_data: 更新数据

        Returns:
            更新后的商品响应或None
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
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
                    return await self.get_product_by_id(product_id)

                update_values.append(product_id)
                sql = f"UPDATE products SET {', '.join(update_fields)} WHERE id = %s"
                await cur.execute(sql, update_values)
                await conn.commit()

                if cur.rowcount == 0:
                    return None

                return await self.get_product_by_id(product_id)

    async def delete_product(self, product_id: int) -> bool:
        """
        删除商品（软删除，设置状态为 off_sale）

        Args:
            product_id: 商品ID

        Returns:
            是否成功
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE products SET status = 'off_sale' WHERE id = %s",
                    (product_id,)
                )
                await conn.commit()
                return cur.rowcount > 0

    async def get_categories(self) -> List[dict]:
        """
        获取分类列表（树形结构）

        Returns:
            分类列表
        """
        async with self.pool.acquire() as conn:
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

    async def get_product_reviews(
        self, product_id: int, page: int = 1, page_size: int = 20
    ) -> ReviewListResponse:
        """
        获取商品评价

        Args:
            product_id: 商品ID
            page: 页码
            page_size: 每页数量

        Returns:
            评价列表响应
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 获取总数和平均评分
                await cur.execute(
                    "SELECT COUNT(*) as total, COALESCE(AVG(rating), 0) as avg_rating FROM product_reviews WHERE product_id = %s",
                    (product_id,)
                )
                stats = await cur.fetchone()
                total = stats["total"]
                avg_rating = round(float(stats["avg_rating"]), 1)

                # 获取评价列表
                offset = (page - 1) * page_size
                sql = """
                    SELECT r.*, u.username
                    FROM product_reviews r
                    LEFT JOIN users u ON r.user_id = u.id
                    WHERE r.product_id = %s
                    ORDER BY r.created_at DESC
                    LIMIT %s OFFSET %s
                """
                await cur.execute(sql, (product_id, page_size, offset))
                reviews = await cur.fetchall()

                items = []
                for review in reviews:
                    if review.get("images") and isinstance(review["images"], str):
                        review["images"] = json.loads(review["images"])
                    items.append(ReviewResponse(**review))

                return ReviewListResponse(
                    total=total,
                    page=page,
                    page_size=page_size,
                    average_rating=avg_rating,
                    items=items,
                )

    async def create_review(
        self, product_id: int, user_id: int, review_data: ReviewCreate
    ) -> ReviewResponse:
        """
        创建评价

        Args:
            product_id: 商品ID
            user_id: 用户ID
            review_data: 评价数据

        Returns:
            创建的评价响应
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # 检查商品是否存在
                await cur.execute("SELECT id FROM products WHERE id = %s", (product_id,))
                if not await cur.fetchone():
                    raise ValueError("商品不存在")

                # 检查是否已评价
                await cur.execute(
                    "SELECT id FROM product_reviews WHERE product_id = %s AND user_id = %s",
                    (product_id, user_id)
                )
                if await cur.fetchone():
                    raise ValueError("您已评价过该商品")

                # 创建评价
                images_json = json.dumps(review_data.images) if review_data.images else None
                await cur.execute(
                    "INSERT INTO product_reviews (product_id, user_id, rating, content, images) VALUES (%s, %s, %s, %s, %s)",
                    (product_id, user_id, review_data.rating, review_data.content, images_json)
                )
                await conn.commit()

                review_id = cur.lastrowid

                # 返回创建的评价
                await cur.execute(
                    "SELECT r.*, u.username FROM product_reviews r LEFT JOIN users u ON r.user_id = u.id WHERE r.id = %s",
                    (review_id,)
                )
                review = await cur.fetchone()
                if review.get("images") and isinstance(review["images"], str):
                    review["images"] = json.loads(review["images"])

                return ReviewResponse(**review)

    async def search_products_with_vector(
        self, keyword: str, vector_collection, n_results: int = 10
    ) -> List[ProductResponse]:
        """
        结合向量搜索的商品搜索

        Args:
            keyword: 搜索关键词
            vector_collection: 向量数据库集合
            n_results: 返回结果数量

        Returns:
            商品列表
        """
        results = []

        # 先尝试向量搜索
        if vector_collection:
            try:
                search_results = vector_collection.query(
                    query_texts=[keyword],
                    n_results=n_results
                )
                if search_results and search_results["documents"]:
                    # 从向量搜索结果中提取商品信息
                    for doc in search_results["documents"][0]:
                        # 尝试从文档中解析商品名称
                        if "：" in doc:
                            product_name = doc.split("：")[0].strip()
                        else:
                            product_name = doc[:50]

                        # 在数据库中查找匹配的商品
                        async with self.pool.acquire() as conn:
                            async with conn.cursor(aiomysql.DictCursor) as cur:
                                await cur.execute(
                                    "SELECT * FROM products WHERE name LIKE %s AND status = 'on_sale' LIMIT 1",
                                    (f"%{product_name}%",)
                                )
                                product = await cur.fetchone()
                                if product:
                                    results.append(ProductResponse(**product))
            except Exception as e:
                print(f"向量搜索失败: {e}")

        # 如果向量搜索结果不足，补充关键词搜索
        if len(results) < n_results:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    remaining = n_results - len(results)
                    await cur.execute(
                        "SELECT * FROM products WHERE (name LIKE %s OR description LIKE %s) AND status = 'on_sale' LIMIT %s",
                        (f"%{keyword}%", f"%{keyword}%", remaining)
                    )
                    products = await cur.fetchall()
                    for product in products:
                        if product["id"] not in [r.id for r in results]:
                            results.append(ProductResponse(**product))

        return results[:n_results]
