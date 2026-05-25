# -*- coding: utf-8 -*-
import os
import asyncio
import aiomysql
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool

# ===== 工具一：商品价格查询（异步版） =====
@tool
async def search_product_price(query: str) -> str:
    """查询商品价格。输入商品名称，从MySQL数据库返回各平台价格信息。"""
    conn = await aiomysql.connect(
        host='host.docker.internal',
        user='root',
        password='108045',
        db='product_db',
        charset='utf8mb4',
        use_unicode=True
    )
    
    keywords = [query[i:i+2] for i in range(len(query)-1)]
    if not keywords:
        keywords = [query]
    
    like_conditions = " OR ".join(["name LIKE %s"] * len(keywords))
    sql = f"SELECT name, price, platform FROM products WHERE {like_conditions}"
    params = tuple(f"%{k}%" for k in keywords)
    
    async with conn.cursor() as cursor:
        await cursor.execute(sql, params)
        rows = await cursor.fetchall()
    
    conn.close()
    
    if not rows:
        return "未找到该商品的价格信息"
    
    results = []
    for name, price, platform in rows:
        results.append(f"{name} {platform}{price}元")
    return "、".join(results)

# ===== 工具二：计算器 =====
@tool
async def calculator(expression: str) -> str:
    """执行数学计算。输入数学表达式，返回计算结果。"""
    try:
        result = eval(expression)
        return f"计算结果：{expression} = {result}"
    except Exception as e:
        return f"计算出错：{e}"

# ===== 工具三：联网搜索（异步版） =====
@tool
async def web_search(query: str) -> str:
    """联网搜索最新信息。输入搜索关键词，返回搜索结果摘要。"""
    conn = await aiomysql.connect(
        host='host.docker.internal',
        user='root',
        password='108045',
        db='product_db',
        charset='utf8mb4',
        use_unicode=True
    )
    
    async with conn.cursor() as cursor:
        await cursor.execute(
            "SELECT content FROM market_news WHERE keyword LIKE %s",
            (f"%{query}%",)
        )
        rows = await cursor.fetchall()
    
    conn.close()
    
    if not rows:
        return f"搜索结果：关于“{query}”暂无具体数据。"
    return f"搜索结果：\n- {rows[0][0]}"

# ===== 初始化模型 =====
agent_model = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    extra_body={"thinking": {"type": "disabled"}},
    http_async_client=None,
)

# ===== 创建记忆管理器 =====
memory = MemorySaver()

# ===== 创建 Agent =====
agent = create_agent(
    model=agent_model,
    tools=[search_product_price, calculator, web_search],
    checkpointer=memory,
)