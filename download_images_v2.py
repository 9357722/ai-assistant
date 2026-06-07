"""从搜索引擎下载真实商品图片"""
import os
import re
import time
import hashlib
import requests
from urllib.parse import quote, urljoin

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, 'static', 'products')
os.makedirs(IMAGES_DIR, exist_ok=True)

# 商品列表（去重）
PRODUCTS = {
    # 手机
    "iPhone 17 Pro": "iPhone 17 Pro 官方图片",
    "华为Mate 70 Pro": "华为Mate70 Pro 官方图片",
    "红米K80": "红米K80 官方图片",
    "小米14": "小米14 官方图片",
    "小米17": "小米17 官方图片",
    # 耳机
    "蓝牙耳机 Pro": "头戴式蓝牙耳机 降噪",
    "蓝牙耳机 Lite": "真无线蓝牙耳机",
    "蓝牙音箱": "便携蓝牙音箱",
    # 电脑
    "MacBook Pro 16": "MacBook Pro 16寸",
    "联想小新Pro 16": "联想小新Pro16",
    "华为MateBook 14": "华为MateBook14",
    # 平板
    "iPad Pro 12.9": "iPad Pro 12.9",
    "iPad Air": "iPad Air",
    "华为MatePad Pro": "华为MatePad Pro",
    # 手表
    "Apple Watch Series 9": "Apple Watch Series 9",
    "华为Watch GT4": "华为Watch GT4",
    # 相机
    "索尼A7M4": "索尼A7M4 相机",
    "佳能R6二代": "佳能EOS R6 Mark II",
    # 服装
    "优衣库圆领T恤": "优衣库 圆领T恤",
    "Levi's 501牛仔裤": "Levi's 501 牛仔裤",
    "阿迪达斯三叶草卫衣": "阿迪达斯 三叶草 卫衣",
    # 鞋
    "Nike Air Max 运动鞋": "Nike Air Max 运动鞋",
    # 美妆
    "兰蔻小黑瓶精华": "兰蔻小黑瓶精华液",
    "雅诗兰黛眼霜": "雅诗兰黛眼霜",
    "完美日记口红": "完美日记口红",
    # 食品
    "农夫山泉矿泉水24瓶": "农夫山泉矿泉水 整箱",
    "三只松鼠坚果礼盒": "三只松鼠坚果礼盒",
    "良品铺子零食大礼包": "良品铺子零食礼包",
    # 家居
    "南极人四件套": "南极人四件套 纯棉",
    # 家电
    "小米空气净化器": "小米空气净化器",
    "美的电饭煲": "美的电饭煲",
    "格力空调": "格力空调",
    "戴森吹风机": "戴森吹风机",
    # 运动
    "Keep瑜伽垫": "Keep瑜伽垫",
    "李宁运动短裤": "李宁运动短裤",
    # 母婴
    "babycare奶瓶": "babycare奶瓶",
    "好奇纸尿裤": "好奇纸尿裤",
    # 图书
    "活着": "活着 余华 书籍封面",
    "三体全集": "三体全集 刘慈欣 书籍封面",
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# 预定义的真实商品图片URL（从官方渠道收集）
OFFICIAL_IMAGES = {
    # 手机
    "iPhone 17 Pro": [
        "https://store.storeimages.cdn-apple.com/1/as-images.apple.com/is/iphone-17-pro-hero-desert-202509?wid=800&hei=800&fmt=jpeg&qlt=90",
        "https://fdn2.gsmarena.com/vv/pics/apple/apple-iphone-16-pro-1.jpg",
    ],
    "华为Mate 70 Pro": [
        "https://consumer.huawei.com/content/dam/huawei-cbg-site/common/mkt/pdp/phones/mate70-pro/img/design/mate70-pro-design-color1.png",
    ],
    "小米14": [
        "https://cdn.cnbj0.fds.api.mi-img.com/b2c-shopapi-pms/pms_1697632614.71524284.png",
    ],
    "小米17": [
        "https://cdn.cnbj0.fds.api.mi-img.com/b2c-shopapi-pms/pms_1716835893.45664498.png",
    ],
    # ... 可以继续添加
}


def search_bing_images(keyword, count=5):
    """从Bing搜索图片"""
    url = f"https://www.bing.com/images/search?q={quote(keyword)}&form=HDRSC3&first=1"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        # 提取图片URL
        pattern = r'murl":"(https?://[^"]+\.(jpg|jpeg|png|webp))"'
        matches = re.findall(pattern, resp.text)
        return [m[0] for m in matches[:count]]
    except:
        return []


def search_sogou_images(keyword):
    """从搜狗搜索图片"""
    url = f"https://pic.sogou.com/pics?query={quote(keyword)}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        pattern = r'"oriPicUrl":"(https?://[^"]+)"'
        matches = re.findall(pattern, resp.text)
        return matches[:3]
    except:
        return []


def download_image(url, product_name, index=0):
    """下载图片"""
    try:
        safe_name = re.sub(r'[^\w一-龥]', '_', product_name)
        file_name = f"{safe_name}_{index}.jpg" if index > 0 else f"{safe_name}.jpg"
        file_path = os.path.join(IMAGES_DIR, file_name)

        if os.path.exists(file_path) and os.path.getsize(file_path) > 5000:
            print(f"  [跳过] 已存在: {file_name}")
            return file_name

        resp = requests.get(url, headers=HEADERS, timeout=15, verify=False, stream=True)
        resp.raise_for_status()

        content_type = resp.headers.get('Content-Type', '')
        if 'image' not in content_type and 'octet-stream' not in content_type:
            return None

        with open(file_path, 'wb') as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)

        size = os.path.getsize(file_path)
        if size < 1000:
            os.remove(file_path)
            return None

        print(f"  [OK] {file_name} ({size//1024}KB)")
        return file_name

    except Exception as e:
        print(f"  [FAIL] {e}")
        return None


def main():
    import urllib3
    urllib3.disable_warnings()

    results = {}
    total = len(PRODUCTS)

    for i, (product, keyword) in enumerate(PRODUCTS.items()):
        print(f"\n[{i+1}/{total}] {product}")

        # 1. 尝试官方图片
        if product in OFFICIAL_IMAGES:
            for url in OFFICIAL_IMAGES[product]:
                fname = download_image(url, product)
                if fname:
                    results[product] = f"/static/products/{fname}"
                    break
            if product in results:
                continue

        # 2. 搜索Bing
        print(f"  搜索Bing: {keyword}")
        image_urls = search_bing_images(keyword)

        # 3. 搜索搜狗
        if not image_urls:
            print(f"  搜索搜狗: {keyword}")
            image_urls = search_sogou_images(keyword)

        # 4. 下载第一个有效图片
        for url in image_urls:
            fname = download_image(url, product)
            if fname:
                results[product] = f"/static/products/{fname}"
                break

        # 5. 如果都失败，用分类默认图
        if product not in results:
            print(f"  使用分类默认图")
            results[product] = f"https://picsum.photos/seed/{hashlib.md5(product.encode()).hexdigest()[:8]}/400/400"

        time.sleep(0.5)

    return results


def update_database(results):
    """更新数据库"""
    import pymysql

    conn = pymysql.connect(
        host='localhost', user='root', password='108045',
        database='product_db', charset='utf8mb4'
    )
    cursor = conn.cursor()

    updated = 0
    for product, image_path in results.items():
        cursor.execute("UPDATE products SET main_image = %s WHERE name = %s", (image_path, product))
        updated += cursor.rowcount

    conn.commit()
    cursor.close()
    conn.close()
    return updated


if __name__ == "__main__":
    print("=" * 50)
    print("下载真实商品图片 v2")
    print("=" * 50)

    results = main()

    print("\n" + "=" * 50)
    print("更新数据库...")
    count = update_database(results)
    print(f"更新了 {count} 条记录")

    # 保存映射表
    import json
    with open(os.path.join(BASE_DIR, 'image_mapping.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("映射表已保存到 image_mapping.json")
