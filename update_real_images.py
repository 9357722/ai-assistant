"""用 Unsplash 搜索API更新商品图片"""
import pymysql

# 使用 Unsplash 的搜索图片（允许热链接）
PRODUCT_IMAGES = {
    # 手机
    "iPhone 17 Pro": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=400&h=400&fit=crop",
    "华为Mate 70 Pro": "https://images.unsplash.com/photo-1616348436168-de43ad0db179?w=400&h=400&fit=crop",
    "红米K80": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop",
    "小米14": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400&h=400&fit=crop",
    "小米17": "https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=400&h=400&fit=crop",

    # 耳机
    "蓝牙耳机 Pro": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop",
    "蓝牙耳机 Lite": "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=400&h=400&fit=crop",
    "蓝牙音箱": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400&h=400&fit=crop",

    # 电脑
    "MacBook Pro 16": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=400&fit=crop",
    "联想小新Pro 16": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400&h=400&fit=crop",
    "华为MateBook 14": "https://images.unsplash.com/photo-1484788984921-03950022c9ef?w=400&h=400&fit=crop",

    # 平板
    "iPad Pro 12.9": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop",
    "iPad Air": "https://images.unsplash.com/photo-1585790050230-5dd28404ccb9?w=400&h=400&fit=crop",
    "华为MatePad Pro": "https://images.unsplash.com/photo-1561154464-82e9adf32764?w=400&h=400&fit=crop",

    # 智能手表
    "Apple Watch Series 9": "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop",
    "华为Watch GT4": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&h=400&fit=crop",

    # 相机
    "索尼A7M4": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400&h=400&fit=crop",
    "佳能R6二代": "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=400&h=400&fit=crop",

    # 服装
    "优衣库圆领T恤": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop",
    "Levi's 501牛仔裤": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=400&h=400&fit=crop",
    "阿迪达斯三叶草卫衣": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=400&h=400&fit=crop",

    # 鞋靴
    "Nike Air Max 运动鞋": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop",

    # 美妆
    "兰蔻小黑瓶精华": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=400&h=400&fit=crop",
    "雅诗兰黛眼霜": "https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=400&h=400&fit=crop",
    "完美日记口红": "https://images.unsplash.com/photo-1586495777744-4413f21062fa?w=400&h=400&fit=crop",

    # 食品
    "农夫山泉矿泉水24瓶": "https://images.unsplash.com/photo-1523362628745-0c100fc988a6?w=400&h=400&fit=crop",
    "三只松鼠坚果礼盒": "https://images.unsplash.com/photo-1599599810769-bcde5a160d32?w=400&h=400&fit=crop",
    "良品铺子零食大礼包": "https://images.unsplash.com/photo-1621939514649-280e2ee25f60?w=400&h=400&fit=crop",

    # 家居
    "南极人四件套": "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=400&h=400&fit=crop",

    # 家电
    "小米空气净化器": "https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=400&h=400&fit=crop",
    "美的电饭煲": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=400&fit=crop",
    "格力空调": "https://images.unsplash.com/photo-1585338107529-13afc5f02586?w=400&h=400&fit=crop",
    "戴森吹风机": "https://images.unsplash.com/photo-1522338242992-e1a54571a7d8?w=400&h=400&fit=crop",

    # 运动
    "Keep瑜伽垫": "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=400&h=400&fit=crop",
    "李宁运动短裤": "https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=400&h=400&fit=crop",

    # 母婴
    "babycare奶瓶": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=400&h=400&fit=crop",
    "好奇纸尿裤": "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=400&h=400&fit=crop",

    # 图书
    "活着": "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400&h=400&fit=crop",
    "三体全集": "https://images.unsplash.com/photo-1532012197267-da84d127e765?w=400&h=400&fit=crop",
}

def update_images():
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='108045',
        database='product_db',
        charset='utf8mb4'
    )
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM products")
    products = cursor.fetchall()

    updated = 0
    for product_id, name in products:
        image_url = PRODUCT_IMAGES.get(name)

        if not image_url:
            # 尝试模糊匹配
            for key, url in PRODUCT_IMAGES.items():
                if key in name or name in key:
                    image_url = url
                    break

        if not image_url:
            # 根据分类使用默认图片
            cursor.execute("SELECT category_name FROM products WHERE id = %s", (product_id,))
            result = cursor.fetchone()
            category = result[0] if result else ""

            category_defaults = {
                "手机": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400&h=400&fit=crop",
                "耳机": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&h=400&fit=crop",
                "电脑": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400&h=400&fit=crop",
                "平板": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop",
                "智能手表": "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=400&h=400&fit=crop",
                "相机": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400&h=400&fit=crop",
                "服装": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop",
                "鞋靴": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop",
                "箱包": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&h=400&fit=crop",
                "美妆": "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400&h=400&fit=crop",
                "食品": "https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?w=400&h=400&fit=crop",
                "家居": "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=400&h=400&fit=crop",
                "家电": "https://images.unsplash.com/photo-1585338107529-13afc5f02586?w=400&h=400&fit=crop",
                "母婴": "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=400&h=400&fit=crop",
                "运动": "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=400&h=400&fit=crop",
                "图书": "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400&h=400&fit=crop",
            }
            image_url = category_defaults.get(category, "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&h=400&fit=crop")

        cursor.execute("UPDATE products SET main_image = %s WHERE id = %s", (image_url, product_id))
        updated += 1
        print(f"[{product_id}] {name} -> {image_url[:60]}...")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"\n完成！更新了 {updated} 个商品")

if __name__ == "__main__":
    update_images()
