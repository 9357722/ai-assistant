# -*- coding: utf-8 -*-
import os
import ast
import operator
import asyncio
import aiomysql
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from db import get_pool


# ===== 安全数学表达式求值 =====
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node):
    """递归遍历AST节点，只允许数字和四则运算"""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPERATORS:
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _SAFE_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPERATORS:
        return _SAFE_OPERATORS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("unsupported expression")


# ===== 工具一: 商品价格查询 =====
@tool
async def search_product_price(query: str) -> str:
    """查询商品价格。输入商品名称, 从MySQL数据库返回各平台价格信息。"""
    pool = get_pool()
    async with pool.acquire() as conn:
        keywords = [query[i:i + 2] for i in range(len(query) - 1)]
        if not keywords:
            keywords = [query]

        like_conditions = " OR ".join(["name LIKE %s"] * len(keywords))
        sql = f"SELECT name, price, platform FROM products WHERE {like_conditions}"
        params = tuple(f"%{k}%" for k in keywords)

        async with conn.cursor() as cursor:
            await cursor.execute(sql, params)
            rows = await cursor.fetchall()

    if not rows:
        return "not found"

    results = []
    for name, price, platform in rows:
        results.append(f"{name} {platform}{price}")
    return "、".join(results)


# ===== 工具二: 计算器 =====
@tool
async def calculator(expression: str) -> str:
    """执行数学计算。输入数学表达式, 返回计算结果。支持 + - * / // % **"""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree)
        return f"result: {expression} = {result}"
    except ZeroDivisionError:
        return "error: division by zero"
    except Exception as e:
        return f"error: {e}"


# ===== 工具三: 联网搜索 =====
@tool
async def web_search(query: str) -> str:
    """联网搜索最新信息。输入搜索关键词, 返回搜索结果摘要。"""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT content FROM market_news WHERE keyword LIKE %s",
                (f"%{query}%",)
            )
            rows = await cursor.fetchall()

    if not rows:
        return f"search result: no data for [{query}]"
    return f"search result:\n- {rows[0][0]}"


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
