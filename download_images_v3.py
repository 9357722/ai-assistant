"""从可靠来源下载商品图片 v3"""
import os
import re
import time
import hashlib
import requests
from urllib.parse import quote
from db_config import get_pymysql_config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, 'static', 'products')
os.makedirs(IMAGES_DIR, exist_ok=True)

# 可靠的商品图片URL映射
# 来源：Unsplash (免费可商用), Pixabay, 以及一些开放的产品图
PRODUCT_IMAGES = {
    # 手机 - 使用高质量手机相关图片
    "iPhone 17 Pro": "https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=600&h=600&fit=crop",
    "华为Mate 70 Pro": "https://images.unsplash.com/photo-1616348436168-de43ad0db179?w=600&h=600&fit=crop",
    "红米K80": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&h=600&fit=crop",
    "小米14": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&h=600&fit=crop",
    "小米17": "https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=600&h=600&fit=crop",

    # 耳机
    "蓝牙耳机 Pro": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&h=600&fit=crop",
    "蓝牙耳机 Lite": "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=600&h=600&fit=crop",
    "蓝牙音箱": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&h=600&fit=crop",

    # 电脑
    "MacBook Pro 16": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&h=600&fit=crop",
    "联想小新Pro 16": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&h=600&fit=crop",
    "华为MateBook 14": "https://images.unsplash.com/photo-1484788984921-03950022c9ef?w=600&h=600&fit=crop",

    # 平板
    "iPad Pro 12.9": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&h=600&fit=crop",
    "iPad Air": "https://images.unsplash.com/photo-1585790050230-5dd28404ccb9?w=600&h=600&fit=crop",
    "华为MatePad Pro": "https://images.unsplash.com/photo-1561154464-82e9adf32764?w=600&h=600&fit=crop",

    # 智能手表
    "Apple Watch Series 9": "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=600&h=600&fit=crop",
    "华为Watch GT4": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&h=600&fit=crop",

    # 相机
    "索尼A7M4": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=600&h=600&fit=crop",
    "佳能R6二代": "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=600&h=600&fit=crop",

    # 服装
    "优衣库圆领T恤": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600&h=600&fit=crop",
    "Levi's 501牛仔裤": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=600&h=600&fit=crop",
    "阿迪达斯三叶草卫衣": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=600&h=600&fit=crop",

    # 鞋靴
    "Nike Air Max 运动鞋": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&h=600&fit=crop",

    # 美妆
    "兰蔻小黑瓶精华": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=600&h=600&fit=crop",
    "雅诗兰黛眼霜": "https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?w=600&h=600&fit=crop",
    "完美日记口红": "https://images.unsplash.com/photo-1586495777744-4413f21062fa?w=600&h=600&fit=crop",

    # 食品
    "农夫山泉矿泉水24瓶": "https://images.unsplash.com/photo-1523362628745-0c100fc988a6?w=600&h=600&fit=crop",
    "三只松鼠坚果礼盒": "https://images.unsplash.com/photo-1599599810769-bcde5a160d32?w=600&h=600&fit=crop",
    "良品铺子零食大礼包": "https://images.unsplash.com/photo-1621939514649-280e2ee25f60?w=600&h=600&fit=crop",

    # 家居
    "南极人四件套": "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=600&h=600&fit=crop",

    # 家电
    "小米空气净化器": "https://images.unsplash.com/photo-1585771724684-38269d6639fd?w=600&h=600&fit=crop",
    "美的电饭煲": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=600&h=600&fit=crop",
    "格力空调": "https://images.unsplash.com/photo-1585338107529-13afc5f02586?w=600&h=600&fit=crop",
    "戴森吹风机": "https://images.unsplash.com/photo-1522338242992-e1a54571a7d8?w=600&h=600&fit=crop",

    # 运动
    "Keep瑜伽垫": "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=600&h=600&fit=crop",
    "李宁运动短裤": "https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=600&h=600&fit=crop",

    # 母婴
    "babycare奶瓶": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=600&h=600&fit=crop",
    "好奇纸尿裤": "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=600&h=600&fit=crop",

    # 图书
    "活着": "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=600&h=600&fit=crop",
    "三体全集": "https://images.unsplash.com/photo-1532012197267-da84d127e765?w=600&h=600&fit=crop",
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'image/*,*/*',
}


def download_image(url, product_name):
    """下载图片"""
    try:
        safe_name = re.sub(r'[^\w一-龥]', '_', product_name)
        file_name = f"{safe_name}.jpg"
        file_path = os.path.join(IMAGES_DIR, file_name)

        # 已存在则跳过
        if os.path.exists(file_path) and os.path.getsize(file_path) > 5000:
            print(f"  [跳过] {file_name} 已存在 ({os.path.getsize(file_path)//1024}KB)")
            return file_name

        resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        resp.raise_for_status()

        with open(file_path, 'wb') as f:
            f.write(resp.content)

        size = os.path.getsize(file_path)
        print(f"  [OK] {file_name} ({size//1024}KB)")
        return file_name

    except Exception as e:
        print(f"  [FAIL] {e}")
        return None


def update_database(results):
    """更新数据库"""
    import pymysql

    conn = pymysql.connect(**get_pymysql_config())
    cursor = conn.cursor()

    updated = 0
    for product, image_path in results.items():
        cursor.execute("UPDATE products SET main_image = %s WHERE name = %s", (image_path, product))
        updated += cursor.rowcount
        print(f"  DB: {product} -> {image_path}")

    conn.commit()
    cursor.close()
    conn.close()
    return updated


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()

    print("=" * 50)
    print("下载商品图片 v3 (Unsplash)")
    print("=" * 50)

    results = {}
    total = len(PRODUCT_IMAGES)

    for i, (product, url) in enumerate(PRODUCT_IMAGES.items()):
        print(f"\n[{i+1}/{total}] {product}")
        fname = download_image(url, product)
        if fname:
            results[product] = f"/static/products/{fname}"
        else:
            # 备用：使用 picsum
            seed = hashlib.md5(product.encode()).hexdigest()[:8]
            results[product] = f"https://picsum.photos/seed/{seed}/400/400"
            print(f"  使用备用图片")

    print("\n" + "=" * 50)
    print("更新数据库...")
    count = update_database(results)
    print(f"\n完成！更新了 {count} 条记录")
