from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import requests
import json

# 初始化 FastAPI
app = FastAPI(title="我的第一个 AI API")

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

# 定义请求体的格式
class ChatRequest(BaseModel):
    question: str
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
    """接收用户问题，返回 AI 解释"""
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request.question}
        ]
    )
    ai_reply = response.choices[0].message.content
    return {"question": request.question, "answer": ai_reply}

@app.get("/")
# ========== 新增：商品推荐接口 ==========
class RecommendRequest(BaseModel):
    budget: int
    prefer_huawei: bool

@app.post("/recommend")
async def recommend(request: RecommendRequest):
    """根据预算和品牌偏好推荐手机"""
    budget = request.budget
    prefer_huawei = request.prefer_huawei
    
    if budget >= 6000 and prefer_huawei:
        result = "推荐：华为 Mate 60 Pro"
    elif budget >= 6000 and not prefer_huawei:
        result = "推荐：iPhone 15 Pro"
    elif 3000 <= budget < 6000:
        result = "推荐：红米 K90 或 荣耀 100"
    else:
        result = "推荐：红米 Note 13 或 荣耀 X50"
    
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
    """获取各平台价格（当前为模拟数据），并生成对比表格"""
    product_name = request.product_name
    
    # 1. 【模拟数据】生成各平台的随机价格
    import random
    base_price = random.randint(3000, 8000)  # 生成一个3000-8000的基数
    jd_price = base_price
    tb_price = int(base_price * random.uniform(0.95, 1.05))  # 价格上下浮动5%
    pdd_price = int(base_price * random.uniform(0.85, 0.95)) # 拼多多通常便宜一些
    
    # 2. 构建给AI的提示词（Prompt）
    price_data = f"""
    商品名称：{product_name}
    京东价格：{jd_price}元
    淘宝价格：{tb_price}元
    拼多多价格：{pdd_price}元
    """
    
    COMPARE_PRICE_PROMPT = f"""
    ### 角色 ###
    你是一个专业的购物助手，擅长分析各电商平台的价格并给出建议。
    
    ### 任务 ###
    根据以下各平台的价格数据，生成一个清晰的价格对比表格。
    
    ### 价格数据 ###
    {price_data}
    
    ### 输出要求 ###
    1. 必须生成一个包含「平台」、「价格」、「一句话点评」三列的Markdown表格。
    2. 在表格下方，用一句话给出最终的购买建议。
    3. 如果某个平台的价格缺失，请在表格中注明“暂未获取到”。
    """
    
    # 3. 调用大模型生成对比表格
    try:
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": COMPARE_PRICE_PROMPT},
                {"role": "user", "content": f"请帮我对比{product_name}的价格"}
            ]
        )
        result = response.choices[0].message.content
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
async def compare_products(request: CompareRequest):
    """接收商品对比请求，返回 AI 生成的对比表格和建议"""
    try:
        # 调用大模型生成对比内容
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": COMPARE_PROMPT},
                {"role": "user", "content": request.query}
            ]
        )
        result = response.choices[0].message.content
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}