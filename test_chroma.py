# test_chroma.py —— 使用极其免费且效果好的中文 Embedding 服务
import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from openai import OpenAI # 完全兼容官方openai库

class SiliconFlowEmbedding(EmbeddingFunction):
    def __init__(self):
        # 填入刚才复制的硅基流动 API Key (通常 src 开头)
        self.client = OpenAI(
            api_key="sk-pqgblebbhnjisdsywfoqhqszcdxcjojxfzmxaccorqqhnmee",
            base_url="https://api.siliconflow.cn/v1"
        )

    def __call__(self, input: Documents) -> Embeddings:
        response = self.client.embeddings.create(
            model="BAAI/bge-large-zh-v1.5",  # 线上高性能免费中文模型
            input=input
        )
        return [item.embedding for item in response.data]

# 清理旧库，重建新库
import os, shutil
if os.path.exists("./my_vectordb"):
    shutil.rmtree("./my_vectordb")

client = chromadb.PersistentClient(path="./my_vectordb")
collection = client.create_collection(
    name="products_silicon",
    embedding_function=SiliconFlowEmbedding()
)

documents = [
    "iPhone 15 128GB 黑色 京东价格5999元",
    "华为Mate60 256GB 银色 淘宝价格6499元",
    "红米K90 512GB 白色 拼多多价格2999元"
]
collection.add(documents=documents, ids=["doc_1", "doc_2", "doc_3"])
print("✅ 数据存入成功！（使用硅基流动）\n")

query = "苹果手机价格"
results = collection.query(query_texts=[query], n_results=2)
print(f"用户查询：{query}")
print(f"最相关结果：{results['documents'][0]}")