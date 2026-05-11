# batch_add_products.py —— 一次性批量导入商品数据
import uuid
from utils import init_vector_db

# 你的硅基流动 API Key
API_KEY = "sk-pqgblebbhnjisdsywfoqhqszcdxcjojxfzmxaccorqqhnmee"

collection = init_vector_db(api_key=API_KEY)

products = [
    "冬瓜平板 Y200 128GB 银色 京东价格1599元，淘宝价格1549元，拼多多价格1499元",
    "菠萝手表 W500 黑色 京东价格899元，拼多多价格849元",
    "草莓耳机 E300 白色 京东价格1299元，淘宝价格1249元，拼多多价格1199元",
    "西瓜手机 X500 256GB 红色 京东价格999元",
    "芒果音箱 M100 灰色 淘宝价格699元，拼多多价格659元"
]

collection.add(
    documents=products,
    ids=[str(uuid.uuid4()) for _ in products]
)

print(f"✅ 已成功导入 {len(products)} 条商品数据！")