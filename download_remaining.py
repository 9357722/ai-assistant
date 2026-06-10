import urllib.request, os, hashlib, time, pymysql
from db_config import get_pymysql_config

conn = pymysql.connect(**get_pymysql_config())
cur = conn.cursor()
cur.execute("SELECT id, name FROM products WHERE id > 46 ORDER BY id")
products = cur.fetchall()
cur.close()
conn.close()

folder = 'D:/python/AI_Projects/static/products'
existing = set(os.listdir(folder))

count = 0
for pid, name in products:
    filename = f'product_{pid}.jpg'
    if filename in existing:
        continue
    seed = int(hashlib.md5(name.encode()).hexdigest()[:8], 16) % 10000
    filepath = os.path.join(folder, filename)
    url = f'https://picsum.photos/seed/{seed}/400/400'
    try:
        urllib.request.urlretrieve(url, filepath)
        count += 1
        if count % 20 == 0:
            print(f'Downloaded {count}...')
    except:
        pass
    time.sleep(0.05)

print(f'Done. New: {count}, Total: {len(os.listdir(folder))}')
