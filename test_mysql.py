import pymysql

# 连接数据库
conn = pymysql.connect(
    host='localhost',
    user='root',
    password='108045',
    database='product_db',
    charset='utf8mb4'
)

# 创建游标
cursor = conn.cursor()

# 查询所有商品
cursor.execute("SELECT * FROM products")
rows = cursor.fetchall()

for row in rows:
    print(row)

# 关闭
cursor.close()
conn.close()