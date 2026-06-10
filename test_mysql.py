import pymysql
from db_config import get_pymysql_config

# 连接数据库
conn = pymysql.connect(**get_pymysql_config())

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
