# -*- coding: utf-8 -*-
import sys, io, os, json, uuid, pymysql
from typing import List, Optional
import time
from fastapi import Header, HTTPException, Request
from collections import defaultdict

# 强制使用 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from fastapi import FastAPI,Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from langchain_openai import ChatOpenAI
import requests
from utils import calc_electricity, input_int, ai_chat, generate_price_comparison, ChatSession, init_vector_db
from recommend import recommend_phone, compare_products, generate_product_comparison

# ================== 系统提示词 ==================
SYSTEM_PROMPT = """
### 角色 ###
你是一位专为编程初学者服务的助教，擅长用生活中常见的比喻来解释晦涩的技术概念。
### 任务 ###
用户会输入一个编程术语，你需要用比喻的方式解释它。
### 约束 ###
- 解释必须包含一个生活化的比喻
- 总字数不超过150字
- 语气亲切幽默
"""
COMPARE_PROMPT = """
### 角色 ###
你是一个专业、细致但表达简洁的商品对比顾问。
### 任务 ###
用户给出两个商品名称，你需要生成一份**清晰易读**的对比报告。
### 输出要求（必须严格遵守） ###
1. **开篇引言**：用1-2句话概括两款产品的核心定位差异（例如“A主打性价比，B主打高端体验”）。
2. **核心参数对比表**：必须用 Markdown 表格呈现，包含以下四列：
   | 对比维度 | 商品A | 商品B | 差异简评 |
3. **选购建议**：用2-3句话分别说明“什么样的人适合选A”、“什么样的人适合选B”，给出具体场景建议。
4. **表格维度选择**：选取4-6个最关键且差异明显的维度（如价格、核心性能、续航、特色功能、适用人群等）。
### 风格约束 ###
- 语言简洁，避免长篇大论，每个部分点到为止，要最核心的参数。
- 表格内每格内容不超过50字，差异简评必须直接点明优劣。
"""

# ================== 全局客户端初始化 ==================
# --- 加载环境变量 ---
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
SILICONFLOW_KEY = os.getenv("SILICONFLOW_API_KEY")

if not DEEPSEEK_KEY:
    raise ValueError("❌ 环境变量 DEEPSEEK_API_KEY 未设置！")
if not SILICONFLOW_KEY:
    print("⚠️ 警告：环境变量 SILICONFLOW_API_KEY 未设置，RAG功能可能无法使用。")

# --- 客户端实例化（注意：所有参数都必须用关键字传递）---
client = openai.OpenAI(
    api_key=DEEPSEEK_KEY,
    base_url="https://api.deepseek.com"
)

langchain_model = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key=DEEPSEEK_KEY,
    base_url="https://api.deepseek.com",
    extra_body={"thinking": {"type": "disabled"}},
    http_async_client=None,
)

# 初始化向量数据库
vector_collection = None
if SILICONFLOW_KEY:
    try:
        vector_collection = init_vector_db(api_key=SILICONFLOW_KEY)
    except Exception as e:
        print(f"⚠️ 向量数据库初始化失败: {e}")

# 初始化聊天会话
chat_session = ChatSession(system_prompt=SYSTEM_PROMPT, model=langchain_model)

# ================== FastAPI 应用 ==================
class UTF8JSONResponse(JSONResponse):
    def render(self, content: any) -> bytes:
        return json.dumps(content, ensure_ascii=False).encode('utf-8')

app = FastAPI(title="商品比价 AI 助手", default_response_class=UTF8JSONResponse)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
# ================== API 鉴权配置 ==================
# 有效的 API Key 列表（实际项目中存数据库或环境变量）
VALID_API_KEYS = {"sk-agent-key-001", "sk-agent-key-002"}

def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """验证请求头中的 API Key"""
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="无效的 API Key，请检查 X-API-Key 请求头")
    return x_api_key

# ================== 请求限流 ==================
# 每个 API Key 每分钟最多 30 次请求
rate_limit_store = defaultdict(list)

def check_rate_limit(api_key: str, max_requests: int = 30, window: int = 60):
    """检查请求频率是否超限"""
    now = time.time()
    # 清除过期记录
    rate_limit_store[api_key] = [
        t for t in rate_limit_store[api_key] if now - t < window
    ]
    if len(rate_limit_store[api_key]) >= max_requests:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    rate_limit_store[api_key].append(now)
# ================== 数据模型 ==================
class ChatRequest(BaseModel):
    question: str
    use_rag: bool = False

class PriceCompareRequest(BaseModel):
    product_name: str

class RecommendRequest(BaseModel):
    budget: int
    prefer_huawei: bool

class CompareRequest(BaseModel):
    query: str

class AddProductRequest(BaseModel):
    content: str

class AddProductDBRequest(BaseModel):
    name: str
    price: float
    platform: str

class UpdatePriceRequest(BaseModel):
    product_id: int
    new_price: float

class DeleteProductRequest(BaseModel):
    product_id: int

# ================== 业务接口 ==================
@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        question = request.question
        search_results = None
        if vector_collection:
            search_results = vector_collection.query(query_texts=[question], n_results=3)
            retrieved_docs = search_results['documents'][0]
        else:
            retrieved_docs = []

        if retrieved_docs:
            context = "\n".join([f"- {doc}" for doc in retrieved_docs])
            enhanced_question = f"【商品信息】\n{context}\n\n【用户问题】\n{question}\n\n如果商品信息中有相关数据，请直接引用。"
        else:
            enhanced_question = question
            
        result = chat_session.ask(enhanced_question)
        return {"question": question, "answer": result}
    except Exception as e:
        return {"error": str(e)}

@app.post("/recommend")
async def recommend(request: RecommendRequest):
    result = recommend_phone(request.budget, request.prefer_huawei)
    return {"recommendation": result}

@app.post("/compare_price")
async def compare_price(request: PriceCompareRequest):
    try:
        result = generate_price_comparison(client, request.product_name)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}

@app.post("/compare")
async def compare_products_endpoint(request: CompareRequest):
    try:
        result = generate_product_comparison(client, request.query)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}

@app.post("/clear")
async def clear_history():
    chat_session.clear()
    return {"message": "对话历史已清空"}

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    question = request.question
    final_question = question
    if request.use_rag and vector_collection:
        search_results = vector_collection.query(query_texts=[question], n_results=3)
        retrieved_docs = search_results['documents'][0]
        if retrieved_docs:
            context = "\n".join([f"- {doc}" for doc in retrieved_docs])
            final_question = f"【商品信息】\n{context}\n\n【用户问题】\n{question}\n\n要求：如果对比多个商品，请用表格呈现。"

    async def generate():
        for chunk in chat_session.ask_stream(final_question):
            yield chunk
    return StreamingResponse(generate(), media_type="text/plain")

@app.post("/add_product")
async def add_product(request: AddProductRequest):
    if not vector_collection:
        return {"error": "向量数据库未初始化"}
    vector_collection.add(documents=[request.content], ids=[str(uuid.uuid4())])
    return {"message": f"已添加：{request.content[:50]}..."}

@app.post("/add_product_db")
async def add_product_db(request: AddProductDBRequest):
    conn = pymysql.connect(host='localhost', user='root', password='108045', database='product_db', charset='utf8mb4')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO products (name, price, platform) VALUES (%s, %s, %s)", (request.name, request.price, request.platform))
    conn.commit()
    cursor.close(); conn.close()
    return {"message": "商品添加成功", "id": cursor.lastrowid}

@app.put("/update_price")
async def update_price(request: UpdatePriceRequest):
    conn = pymysql.connect(host='localhost', user='root', password='108045', database='product_db', charset='utf8mb4')
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET price=%s WHERE id=%s", (request.new_price, request.product_id))
    conn.commit()
    affected = cursor.rowcount
    cursor.close(); conn.close()
    return {"error": "未找到"} if affected == 0 else {"message": f"影响{affected}行"}

@app.delete("/delete_product")
async def delete_product(request: DeleteProductRequest):
    conn = pymysql.connect(host='localhost', user='root', password='108045', database='product_db', charset='utf8mb4')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id=%s", (request.product_id,))
    conn.commit()
    affected = cursor.rowcount
    cursor.close(); conn.close()
    return {"error": "未找到"} if affected == 0 else {"message": f"影响{affected}行"}

# ================== Agent 接口 ==================
from agent_tools import agent as agent_executor

@app.post("/agent")
async def agent_chat(request: ChatRequest, api_key: str = Depends(verify_api_key)):
    try:
        check_rate_limit(api_key)
        config = {"configurable": {"thread_id": "agent-session-001"}}
        result = await agent_executor.ainvoke(  # ← 异步调用
            {"messages": [
                {"role": "system", "content": "你是商品比价助手。用户询问商品价格时，请先调用 search_product_price 工具查询。用户询问市场行情时，请调用 web_search 工具。不要直接回答，先用工具查。"},
                {"role": "user", "content": request.question}
            ]},
            config=config
        )
        answer = result["messages"][-1].content
        return {"question": request.question, "answer": answer}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)