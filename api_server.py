# -*- coding: utf-8 -*-
import sys
import io
# 强制使用UTF-8，这是最根本的解决方法
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from fastapi import FastAPI
from starlette.responses import JSONResponse
import json
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from langchain_openai import ChatOpenAI
import requests
import json
from recommend import recommend_phone, compare_products
from utils import calc_electricity, input_int
from utils import calc_electricity, input_int, ai_chat, generate_price_comparison,ChatSession,init_vector_db
from recommend import recommend_phone, compare_products, generate_product_comparison
from utils import ai_chat, generate_price_comparison
from fastapi.responses import StreamingResponse


# 原 client 保留（其他接口可能还在用）
client = openai.OpenAI(
    api_key="sk-fb21f48146f9455d87b1ba30593a15e7",
    base_url="https://api.deepseek.com"
)

# 新建 LangChain 模型对象
langchain_model = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key="sk-fb21f48146f9455d87b1ba30593a15e7",
    base_url="https://api.deepseek.com"
)

# 初始化向量数据库（使用硅基流动 API Key）
SILICONFLOW_API_KEY = "sk-pqgblebbhnjisdsywfoqhqszcdxcjojxfzmxaccorqqhnmee"
vector_collection = init_vector_db(api_key=SILICONFLOW_API_KEY)
# 初始化 FastAPI
class UTF8JSONResponse(JSONResponse):
    def render(self, content: any) -> bytes:
        return json.dumps(content, ensure_ascii=False).encode('utf-8')

app = FastAPI(
    title="我的第一个 AI API",
    default_response_class=UTF8JSONResponse
)

# 添加 CORS 中间件（解决跨域问题）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 DeepSeek 客户端
client = openai.OpenAI(
    api_key="sk-ef1bcf1c1c0b4deebbaf4a83cbcc0dd0",
    base_url="https://api.deepseek.com"
)

# 系统提示词（定义 AI 的角色和回答风格）
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
#创建带记忆的聊天会话(全局单例)
chat_session = ChatSession(system_prompt=SYSTEM_PROMPT, model=langchain_model)

# 定义请求体的格式
class ChatRequest(BaseModel):
    question: str
    use_rag: bool = False    # ← 这一行必须有
# 用于价格对比的请求体
class PriceCompareRequest(BaseModel):
    product_name: str # 用户要搜索的商品名称
# 系统提示词
SYSTEM_PROMPT = """
### 角色###
你是一位动物与自然栏目的主持人，擅长用专业的术语以及优美的词汇描述大自然的万千景象。

### 任务 ###
用户会输入一些动植物，你需要用自身的词汇描述它。

### 约束 ###
- 解释必须包含动植物的各种生活习性
- 总字数不超过150字
- 语气亲切幽默
"""


@app.post("/chat")
async def chat(request: ChatRequest):
    """接收用户问题，先检索知识库再回答"""
    try:
        question = request.question
        
        # 1. 从向量数据库检索相关商品信息
        search_results = vector_collection.query(query_texts=[question], n_results=3)
        retrieved_docs = search_results['documents'][0]
        
        # 2. 构建增强提示词：把检索到的数据作为上下文传给 AI
        if retrieved_docs:
            context = "\n".join([f"- {doc}" for doc in retrieved_docs])
            enhanced_question = f"""请根据以下商品信息，准确回答用户问题。

【商品信息】
{context}

【用户问题】
{question}

如果商品信息中有相关数据，请直接引用并给出具体价格和平台。如果商品信息中没有相关数据，请如实告知暂无该商品信息。"""
        else:
            enhanced_question = question
        
        # 3. 调用 AI 生成回答
        result = chat_session.ask(enhanced_question)
        return {"question": question, "answer": result}
    except Exception as e:
        return {"error": str(e)}
# ========== 新增：商品推荐接口 ==========
class RecommendRequest(BaseModel):
    budget: int
    prefer_huawei: bool

@app.post("/recommend")
async def recommend(request: RecommendRequest):
    """根据预算和品牌偏好推荐手机"""
    result = recommend_phone(request.budget, request.prefer_huawei)
    return {"recommendation": result}
async def root():
    return {"message": "AI API 服务已启动！访问 /docs 查看接口文档"}
# ========== 新增：价格对比功能（模拟数据版） ==========
from typing import List, Optional
import json

class PriceCompareRequest(BaseModel):
    product_name: str  # 用户要搜索的商品名称

@app.post("/compare_price")
async def compare_price(request: PriceCompareRequest):
    """获取各平台价格并生成对比表格"""
    try:
        result = generate_price_comparison(client, request.product_name)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}
# ========== 新增：商品对比功能 ==========
from typing import List, Optional
import json

class CompareRequest(BaseModel):
    query: str  # 用户输入的商品对比请求

# 用于对比的系统提示词
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
- 整体回答长度控制在合理范围内（表格行数×8行以内）。
"""

@app.post("/compare")
async def compare_products_endpoint(request: CompareRequest):
    """接收商品对比请求，返回 AI 生成的对比表格和建议"""
    try:
        result = generate_product_comparison(client, request.query)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}

@app.post("/clear")
async def clear_history():
    """清空当前对话历史"""
    chat_session.clear()
    return {"message": "对话历史已清空"}


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天接口：根据 use_rag 参数决定是否先检索知识库"""
    
    # 构建最终要发给AI的消息
    question = request.question
    
    if request.use_rag:
        # RAG增强模式：先检索向量数据库
        search_results = vector_collection.query(query_texts=[question], n_results=3)
        retrieved_docs = search_results['documents'][0]
        
        if retrieved_docs:
            context = "\n".join([f"- {doc}" for doc in retrieved_docs])
            final_question = f"""请根据以下商品信息，准确回答用户问题。

【商品信息】
{context}

【用户问题】
{question}

要求：
1. 如果对比多个商品，请用 Markdown 表格列出每个商品的【商品名称、平台、价格】，并给出购买建议。
2. 如果是单个商品，直接给出各平台价格，也用简洁的表格呈现。
3. 如果商品信息中没有相关数据，请如实告知暂无该商品信息。"""
        else:
            final_question = question
    else:
        # 普通模式：直接对话
        final_question = question
    
    async def generate():
        for chunk in chat_session.ask_stream(final_question):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")
class AddProductRequest(BaseModel):
    content: str
@app.post("/add_product")
async def add_product(request: AddProductRequest):
    """动态向向量数据库中添加一条商品信息"""
    try:
        import uuid
        vector_collection.add(
            documents=[request.content],
            ids=[str(uuid.uuid4())]
        )
        return {"message": f"已添加商品信息：{request.content[:50]}..."}
    except Exception as e:
        return {"error": str(e)}


# ===== 新增 Agent 接口 =====
from agent_tools import agent as agent_executor

@app.post("/agent")
async def agent_chat(request: ChatRequest):
    """Agent 模式：让 AI 自主调用工具完成任务"""
    try:
        # 使用 thread_id 隔离不同用户的记忆
        config = {"configurable": {"thread_id": "agent-session-001"}}
        
        result = agent_executor.invoke(
            {"messages": [
                {"role": "system", "content": "你是一个专业的商品比价助手，可查询价格、计算、联网搜索。"},
                {"role": "user", "content": request.question}
            ]},
            config=config
        )
        # 提取最终回复
        answer = result["messages"][-1].content
        return {"question": request.question, "answer": answer}
    except Exception as e:
        return {"error": str(e)}