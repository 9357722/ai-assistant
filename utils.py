from langchain_openai import ChatOpenAI
import config

# utils.py —— 工具函数模块

def input_int(prompt="请输入一个整数："):
    """输入校验：反复提示直到用户输入合法整数，返回该整数"""
    while True:
        try:
            num = int(input(prompt))
            return num
        except ValueError:
            print("输入无效，请输入整数！")


def calc_electricity(degree):
    """传入用电度数，返回电费"""
    l1, l2 = 2880, 4800
    p1, p2, p3 = 0.4883, 0.5383, 0.7883

    if degree <= l1:
        return degree * p1
    elif degree <= l2:
        return l1 * p1 + (degree - l1) * p2
    else:
        return l1 * p1 + (l2 - l1) * p2 + (degree - l2) * p3


# 只有直接运行 utils.py 时才测试
if __name__ == "__main__":
    print("测试 input_int：")
    num = input_int("随便输入一个整数：")
    print(f"你输入的是：{num}")

    print("\n测试 calc_electricity：")
    print(f"3000 度电费：{calc_electricity(3000):.2f} 元")

# ===== AI 聊天核心逻辑 =====
def ai_chat(client, user_question, system_prompt):
    """调用 AI 接口，返回回复文本"""
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question}
        ]
    )
    return response.choices[0].message.content


# ===== 价格对比核心逻辑 =====
def generate_price_comparison(client, product_name):
    """为指定商品生成模拟价格数据，并调用 AI 生成对比表格"""
    import random

    # 生成模拟价格数据
    base_price = random.randint(3000, 8000)
    jd_price = base_price
    tb_price = int(base_price * random.uniform(0.95, 1.05))
    pdd_price = int(base_price * random.uniform(0.85, 0.95))

    # 构建提示词
    price_data = f"""
    商品名称：{product_name}
    京东价格：{jd_price}元
    淘宝价格：{tb_price}元
    拼多多价格：{pdd_price}元
    """

    prompt = f"""### 角色 ###
你是一个专业购物助手，擅长分析各电商平台价格。

### 任务 ###
根据以下价格数据，生成价格对比表格。

### 价格数据 ###
{price_data}

### 输出要求 ###
1. 生成包含「平台」、「价格」、「一句话点评」三列的 Markdown 表格
2. 表格下方给出一句话购买建议
3. 价格数字必须精确到个位数"""

    result = ai_chat(client, f"请帮我对比{product_name}的价格", prompt)
    return result

# ===== 对话记忆模块 =====

class ChatSession:
    """管理一次完整的对话会话，自动维护上下文"""

    def __init__(self, system_prompt="你是一个有帮助的AI助手", model=None):
        self.system_prompt = system_prompt
        self.history = []

        # 如果没有传入 model，则创建一个默认的 LangChain 模型对象
        if model is None:
            self.model = ChatOpenAI(
                model="deepseek-v4-flash",
                api_key=config.DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com"
            )
        else:
            self.model = model

    def ask(self, user_message):
        self.history.append({"role": "user", "content": user_message})
        full_messages = [{"role": "system", "content": self.system_prompt}] + self.history
        response = self.model.invoke(full_messages)
        ai_reply = response.content
        self.history.append({"role": "assistant", "content": ai_reply})
        return ai_reply

    def ask_stream(self, user_message):
        self.history.append({"role": "user", "content": user_message})
        full_messages = [{"role": "system", "content": self.system_prompt}] + self.history
        collected_content = ""
        for chunk in self.model.stream(full_messages):
            if chunk.content:
                collected_content += chunk.content
                yield chunk.content
        self.history.append({"role": "assistant", "content": collected_content})

    def clear(self):
        """清空对话历史，但保留系统提示词"""
        self.history = []

    def get_history(self):
        """返回当前完整对话记录"""
        return self.history

# ===== RAG 向量数据库模块 =====
import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from openai import OpenAI

class SiliconFlowEmbedding(EmbeddingFunction):
    """硅基流动 Embedding 函数"""
    def __init__(self, api_key=None, base_url="https://api.siliconflow.cn/v1"):
        self.client = OpenAI(
            api_key=api_key or config.SILICONFLOW_API_KEY,
            base_url=base_url
        )

    def __call__(self, input: Documents) -> Embeddings:
        response = self.client.embeddings.create(
            model="BAAI/bge-large-zh-v1.5",
            input=input
        )
        return [item.embedding for item in response.data]
def init_vector_db(api_key, db_path="./my_vectordb", collection_name="products"):
    """
    初始化 ChromaDB 向量数据库，返回 collection 对象。
    api_key: 硅基流动的 API Key
    db_path: 数据库文件夹路径
    collection_name: 集合名称
    """
    embedding_func = SiliconFlowEmbedding(api_key=api_key)
    chroma_client = chromadb.PersistentClient(path=db_path)

    # 如果集合已存在则直接获取，否则创建新集合
    try:
        collection = chroma_client.get_collection(
            name=collection_name,
            embedding_function=embedding_func
        )
    except Exception:
        collection = chroma_client.create_collection(
            name=collection_name,
            embedding_function=embedding_func
        )
    return collection