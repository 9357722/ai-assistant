"""从京东搜索下载真实商品图片"""
import os
import re
import json
import time
import hashlib
import requests
from urllib.parse import quote

# 项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, 'static', 'products')

# 确保目录存在
os.makedirs(IMAGES_DIR, exist_ok=True)

# 去重后的商品列表
PRODUCTS = [
    # 手机
    "iPhone 17 Pro",
    "华为Mate 70 Pro",
    "红米K80",
    "小米14",
    "小米17",
    # 耳机
    "蓝牙耳机 Pro",
    "蓝牙耳机 Lite",
    "蓝牙音箱",
    # 电脑
    "MacBook Pro 16",
    "联想小新Pro 16",
    "华为MateBook 14",
    # 平板
    "iPad Pro 12.9",
    "iPad Air",
    "华为MatePad Pro",
    # 智能手表
    "Apple Watch Series 9",
    "华为Watch GT4",
    # 相机
    "索尼A7M4",
    "佳能R6二代",
    # 服装
    "优衣库圆领T恤",
    "Levi's 501牛仔裤",
    "阿迪达斯三叶草卫衣",
    # 鞋靴
    "Nike Air Max 运动鞋",
    # 美妆
    "兰蔻小黑瓶精华",
    "雅诗兰黛眼霜",
    "完美日记口红",
    # 食品
    "农夫山泉矿泉水24瓶",
    "三只松鼠坚果礼盒",
    "良品铺子零食大礼包",
    # 家居
    "南极人四件套",
    # 家电
    "小米空气净化器",
    "美的电饭煲",
    "格力空调",
    "戴森吹风机",
    # 运动
    "Keep瑜伽垫",
    "李宁运动短裤",
    # 母婴
    "babycare奶瓶",
    "好奇纸尿裤",
    # 图书
    "活着",
    "三体全集",
]

# 搜索关键词映射（优化搜索结果）
SEARCH_KEYWORDS = {
    "iPhone 17 Pro": "iPhone 17 Pro 手机",
    "华为Mate 70 Pro": "华为Mate70 Pro 手机",
    "红米K80": "红米K80 手机",
    "小米14": "小米14 手机",
    "小米17": "小米17 手机",
    "蓝牙耳机 Pro": "蓝牙耳机 降噪",
    "蓝牙耳机 Lite": "蓝牙耳机 轻量",
    "蓝牙音箱": "蓝牙音箱 便携",
    "MacBook Pro 16": "MacBook Pro 16寸 笔记本",
    "联想小新Pro 16": "联想小新Pro16 笔记本",
    "华为MateBook 14": "华为MateBook14 笔记本",
    "iPad Pro 12.9": "iPad Pro 12.9 平板",
    "iPad Air": "iPad Air 平板",
    "华为MatePad Pro": "华为MatePad Pro 平板",
    "Apple Watch Series 9": "Apple Watch Series 9 手表",
    "华为Watch GT4": "华为Watch GT4 手表",
    "索尼A7M4": "索尼A7M4 相机",
    "佳能R6二代": "佳能R6 II 相机",
    "优衣库圆领T恤": "优衣库 圆领T恤 男",
    "Levi's 501牛仔裤": "Levi's 501 牛仔裤 男",
    "阿迪达斯三叶草卫衣": "阿迪达斯 三叶草 卫衣 男",
    "Nike Air Max 运动鞋": "Nike Air Max 运动鞋 男",
    "兰蔻小黑瓶精华": "兰蔻小黑瓶精华液",
    "雅诗兰黛眼霜": "雅诗兰黛眼霜",
    "完美日记口红": "完美日记口红",
    "农夫山泉矿泉水24瓶": "农夫山泉矿泉水 24瓶 整箱",
    "三只松鼠坚果礼盒": "三只松鼠坚果礼盒",
    "良品铺子零食大礼包": "良品铺子零食大礼包",
    "南极人四件套": "南极人四件套 纯棉",
    "小米空气净化器": "小米空气净化器",
    "美的电饭煲": "美的电饭煲",
    "格力空调": "格力空调 挂机",
    "戴森吹风机": "戴森吹风机",
    "Keep瑜伽垫": "Keep瑜伽垫 加厚",
    "李宁运动短裤": "李宁运动短裤 男",
    "babycare奶瓶": "babycare奶瓶 宽口径",
    "好奇纸尿裤": "好奇纸尿裤 皇室",
    "活着": "活着 余华 小说",
    "三体全集": "三体全集 刘慈欣",
}

# Headers 模拟浏览器
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://www.jd.com/',
}


def get_jd_search_url(keyword):
    """获取京东搜索URL"""
    return f"https://search.jd.com/Search?keyword={quote(keyword)}&enc=utf-8"


def extract_jd_image_url(html_content):
    """从京东搜索结果页提取商品图片URL"""
    # 匹配京东商品图片
    patterns = [
        r'data-lazy-img="([^"]+)"',
        r'data-origin="([^"]+)"',
        r'"imageUrl":"([^"]+)"',
        r'<img[^>]+src="(https://img\d+\.360buyimg\.com/[^"]+)"',
        r'(https://img\d+\.360buyimg\.com/[^"\'>\s]+\.jpg)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html_content)
        if matches:
            # 过滤掉小图标和非商品图
            for url in matches:
                if 'n1/' in url or 'n0/' in url:
                    # 确保是完整URL
                    if url.startswith('//'):
                        url = 'https:' + url
                    elif not url.startswith('http'):
                        continue
                    # 过滤掉明显不是商品图的
                    if 'avatar' not in url and 'icon' not in url and 'logo' not in url:
                        return url
    return None


def download_image(url, product_name):
    """下载图片并保存"""
    try:
        # 生成文件名（基于商品名的hash）
        safe_name = re.sub(r'[^\w一-龥]', '_', product_name)
        file_name = f"{safe_name}.jpg"
        file_path = os.path.join(IMAGES_DIR, file_name)

        # 如果文件已存在，跳过
        if os.path.exists(file_path) and os.path.getsize(file_path) > 1000:
            print(f"  [跳过] {file_name} 已存在")
            return file_name

        # 下载图片
        response = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        response.raise_for_status()

        # 检查是否是有效图片
        content_type = response.headers.get('Content-Type', '')
        if 'image' not in content_type and len(response.content) < 1000:
            print(f"  [失败] 不是有效图片: {content_type}")
            return None

        # 保存文件
        with open(file_path, 'wb') as f:
            f.write(response.content)

        print(f"  [成功] {file_name} ({len(response.content)} bytes)")
        return file_name

    except Exception as e:
        print(f"  [失败] {e}")
        return None


def search_and_download():
    """搜索并下载所有商品图片"""
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()
    session.headers.update(HEADERS)

    results = {}

    for i, product in enumerate(PRODUCTS):
        print(f"\n[{i+1}/{len(PRODUCTS)}] 搜索: {product}")

        keyword = SEARCH_KEYWORDS.get(product, product)

        try:
            # 搜索京东
            url = get_jd_search_url(keyword)
            response = session.get(url, timeout=10, verify=False)

            # 提取图片URL
            image_url = extract_jd_image_url(response.text)

            if image_url:
                print(f"  找到图片: {image_url[:60]}...")
                file_name = download_image(image_url, product)
                if file_name:
                    results[product] = f"/static/products/{file_name}"
            else:
                print(f"  [警告] 未找到图片，尝试使用备用方案...")
                # 备用：使用 picsum 生成唯一图片
                seed = hashlib.md5(product.encode()).hexdigest()[:8]
                results[product] = f"https://picsum.photos/seed/{seed}/400/400"

        except Exception as e:
            print(f"  [错误] {e}")
            # 备用
            seed = hashlib.md5(product.encode()).hexdigest()[:8]
            results[product] = f"https://picsum.photos/seed/{seed}/400/400"

        # 礼貌延迟
        time.sleep(1)

    return results


def update_database(results):
    """更新数据库中的图片路径"""
    import pymysql

    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='108045',
        database='product_db',
        charset='utf8mb4'
    )
    cursor = conn.cursor()

    updated = 0
    for product_name, image_path in results.items():
        # 更新所有匹配的商品（处理重复）
        cursor.execute(
            "UPDATE products SET main_image = %s WHERE name = %s",
            (image_path, product_name)
        )
        if cursor.rowcount > 0:
            print(f"更新数据库: {product_name} -> {image_path}")
            updated += cursor.rowcount

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n共更新 {updated} 条商品图片记录")


if __name__ == "__main__":
    print("=" * 50)
    print("开始下载商品图片...")
    print("=" * 50)

    results = search_and_download()

    print("\n" + "=" * 50)
    print("更新数据库...")
    print("=" * 50)

    update_database(results)

    print("\n" + "=" * 50)
    print("完成！")
    print("=" * 50)
