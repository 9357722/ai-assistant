# -*- coding: utf-8 -*-
# agent_tools.py —— Agent 工具集
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool

# ===== 工具一：商品价格查询（调用你的 ChromaDB 向量库） =====
# 这里先用模拟数据，后续可以替换为真实的向量检索
@tool
def search_product_price(query: str) -> str:
    """查询商品价格。输入商品名称（如'西瓜手机'），返回各平台价格信息。"""
    database = {
        "西瓜手机": "西瓜手机 X500 京东价格999元",
        "冬瓜平板": "冬瓜平板 Y200 京东1599元、淘宝1549元、拼多多1499元",
        "草莓耳机": "草莓耳机 E300 京东1299元、淘宝1249元、拼多多1199元",
        "小米14": "小米14 Ultra 京东价格6999元，淘宝价格6899元，拼多多价格6599元",
    }
    for key, value in database.items():
        if key in query:
            return value
    return "未找到该商品的价格信息"

# ===== 工具二：计算器 =====
@tool
def calculator(expression: str) -> str:
    """执行数学计算。输入数学表达式（如'999*2+1599'），返回计算结果。"""
    try:
        result = eval(expression)
        return f"计算结果：{expression} = {result}"
    except Exception as e:
        return f"计算出错：{e}"

# ===== 工具三：联网搜索（可选，填入你的 API Key） =====
@tool
def web_search(query: str) -> str:
    """联网搜索最新信息。输入搜索关键词，返回搜索结果摘要。"""
    # 如果没有 API Key，可以先用模拟数据
    mock_results = {
        "手机行情": "2026年5月：华为Mate 70 Pro均价6999元，iPhone 17 Pro均价7999元，红米K80均价2499元。",
    }
    for key, value in mock_results.items():
        if key in query:
            return f"搜索结果：\n- {value}"
    return f"搜索结果：关于“{query}”暂无具体数据，建议前往电商平台查看。"

# ===== 初始化模型 =====
agent_model = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key="sk-fb21f48146f9455d87b1ba30593a15e7",
    base_url="https://api.deepseek.com",
    extra_body={"thinking": {"type": "disabled"}}
)

# ===== 创建记忆管理器 =====
memory = MemorySaver()

# ===== 创建 Agent =====
agent = create_agent(
    model=agent_model,
    tools=[search_product_price, calculator, web_search],
    checkpointer=memory,
)