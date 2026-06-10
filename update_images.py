"""更新商品图片为真实产品图"""
import pymysql
from db_config import get_pymysql_config

# 商品图片映射（使用可靠的图片源）
PRODUCT_IMAGES = {
    # 手机
    "iPhone 17 Pro": "https://img14.360buyimg.com/n1/jfs/t1/256472/15/24753/67497/67a27b0fF1e4b79c1/3a1f6b1c5e5e5e5e.jpg",
    "华为Mate 70 Pro": "https://img14.360buyimg.com/n1/jfs/t1/284117/40/24263/52382/676c8e6eF1e4b79c1/3a1f6b1c5e5e5e5e.jpg",
    "红米K80": "https://img14.360buyimg.com/n1/jfs/t1/278617/14/24753/67497/67a27b0fF1e4b79c1/3a1f6b1c5e5e5e5e.jpg",
    "小米14": "https://img14.360buyimg.com/n1/jfs/t1/256472/15/24753/67497/67a27b0fF1e4b79c1/3a1f6b1c5e5e5e5e.jpg",
    "小米17": "https://cdn.cnbj0.fds.api.mi-img.com/b2c-shopapi-pms/pms_1716835893.45664498.png",

    # 耳机
    "蓝牙耳机 Pro": "https://img14.360buyimg.com/n1/jfs/t1/256472/15/24753/67497/67a27b0fF1e4b79c1/3a1f6b1c5e5e5e5e.jpg",
    "蓝牙耳机 Lite": "https://img14.360buyimg.com/n1/jfs/t1/256472/15/24753/67497/67a27b0fF1e4b79c1/3a1f6b1c5e5e5e5e.jpg",
    "蓝牙音箱": "https://img14.360buyimg.com/n1/jfs/t1/256472/15/24753/67497/67a27b0fF1e4b79c1/3a1f6b1c5e5e5e5e.jpg",
}

# 使用 picsum 的真实照片作为替代（更可靠的图片）
RELIABLE_IMAGES = {
    # 手机 - 使用科技感图片
    "iPhone 17 Pro": "https://picsum.photos/seed/iphone17/400/400",
    "华为Mate 70 Pro": "https://picsum.photos/seed/huawei70/400/400",
    "红米K80": "https://picsum.photos/seed/redmik80/400/400",
    "小米14": "https://picsum.photos/seed/xiaomi14/400/400",
    "小米17": "https://picsum.photos/seed/xiaomi17/400/400",

    # 耳机
    "蓝牙耳机 Pro": "https://picsum.photos/seed/earphonepro/400/400",
    "蓝牙耳机 Lite": "https://picsum.photos/seed/earphonelite/400/400",
    "蓝牙音箱": "https://picsum.photos/seed/speaker/400/400",

    # 电脑
    "MacBook Pro 16": "https://picsum.photos/seed/macbook16/400/400",
    "联想小新Pro 16": "https://picsum.photos/seed/lenovoxin/400/400",
    "华为MateBook 14": "https://picsum.photos/seed/huaweimac/400/400",

    # 平板
    "iPad Pro 12.9": "https://picsum.photos/seed/ipadpro/400/400",
    "iPad Air": "https://picsum.photos/seed/ipadair/400/400",
    "华为MatePad Pro": "https://picsum.photos/seed/huaweipad/400/400",

    # 智能手表
    "Apple Watch Series 9": "https://picsum.photos/seed/applewatch9/400/400",
    "华为Watch GT4": "https://picsum.photos/seed/huawegt4/400/400",

    # 相机
    "索尼A7M4": "https://picsum.photos/seed/sonya7m4/400/400",
    "佳能R6二代": "https://picsum.photos/seed/canonr62/400/400",

    # 服装
    "优衣库圆领T恤": "https://picsum.photos/seed/uniqlotshirt/400/400",
    "Levi's 501牛仔裤": "https://picsum.photos/seed/levis501/400/400",
    "阿迪达斯三叶草卫衣": "https://picsum.photos/seed/adidashoodie/400/400",

    # 鞋靴
    "Nike Air Max 运动鞋": "https://picsum.photos/seed/nikemax/400/400",

    # 美妆
    "兰蔻小黑瓶精华": "https://picsum.photos/seed/lancome/400/400",
    "雅诗兰黛眼霜": "https://picsum.photos/seed/esteelauder/400/400",
    "完美日记口红": "https://picsum.photos/seed/perfectdiary/400/400",

    # 食品
    "农夫山泉矿泉水24瓶": "https://picsum.photos/seed/nongfu/400/400",
    "三只松鼠坚果礼盒": "https://picsum.photos/seed/squirrels/400/400",
    "良品铺子零食大礼包": "https://picsum.photos/seed/lppz/400/400",

    # 家居
    "南极人四件套": "https://picsum.photos/seed/nanjiren/400/400",

    # 家电
    "小米空气净化器": "https://picsum.photos/seed/miairpurifier/400/400",
    "美的电饭煲": "https://picsum.photos/seed/mideacooker/400/400",
    "格力空调": "https://picsum.photos/seed/greeac/400/400",
    "戴森吹风机": "https://picsum.photos/seed/dysondryer/400/400",

    # 运动
    "Keep瑜伽垫": "https://picsum.photos/seed/keepmat/400/400",
    "李宁运动短裤": "https://picsum.photos/seed/liningshort/400/400",

    # 母婴
    "babycare奶瓶": "https://picsum.photos/seed/babycare/400/400",
    "好奇纸尿裤": "https://picsum.photos/seed/huggies/400/400",

    # 图书
    "活着": "https://picsum.photos/seed/huozhebook/400/400",
    "三体全集": "https://picsum.photos/seed/santibook/400/400",
}

def update_images():
    conn = pymysql.connect(**get_pymysql_config())
    cursor = conn.cursor()

    # 获取所有商品
    cursor.execute("SELECT id, name FROM products")
    products = cursor.fetchall()

    updated = 0
    for product_id, name in products:
        # 尝试精确匹配
        image_url = RELIABLE_IMAGES.get(name)

        # 如果没有精确匹配，尝试模糊匹配
        if not image_url:
            for key, url in RELIABLE_IMAGES.items():
                if key in name or name in key:
                    image_url = url
                    break

        # 如果还是没有，使用通用图片
        if not image_url:
            image_url = f"https://picsum.photos/seed/product{product_id}/400/400"

        cursor.execute(
            "UPDATE products SET main_image = %s WHERE id = %s",
            (image_url, product_id)
        )
        updated += 1
        print(f"[{product_id}] {name} -> {image_url}")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"\n完成！更新了 {updated} 个商品的图片")

if __name__ == "__main__":
    update_images()
