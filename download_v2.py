import urllib.request, os, hashlib, time, pymysql
from db_config import get_pymysql_config

# 获取数据库中的商品
conn = pymysql.connect(**get_pymysql_config())
cur = conn.cursor()
cur.execute("SELECT id, name, category_id FROM products WHERE id > 46 ORDER BY id")
products = cur.fetchall()
cur.close()
conn.close()

folder = 'D:/python/AI_Projects/static/products'
os.makedirs(folder, exist_ok=True)

# 下载图片
count = 0
mapping = []
for pid, name, cat_id in products:
    # 用商品名生成唯一种子
    seed = int(hashlib.md5(name.encode()).hexdigest()[:8], 16) % 10000
    filename = f'product_{pid}.jpg'
    filepath = os.path.join(folder, filename)
    url = f'https://picsum.photos/seed/{seed}/400/400'

    try:
        urllib.request.urlretrieve(url, filepath)
        count += 1
        mapping.append((pid, name, filename))
        if count % 50 == 0:
            print(f'Downloaded {count}/{len(products)}...')
    except Exception as e:
        print(f'Failed: {name} - {e}')
    time.sleep(0.05)

# 保存映射到文件
with open('D:/python/AI_Projects/image_mapping.txt', 'w', encoding='utf-8') as f:
    for pid, name, filename in mapping:
        f.write(f'{pid}|{name}|{filename}\n')

print(f'Done. Downloaded {count} images. Mapping saved.')
