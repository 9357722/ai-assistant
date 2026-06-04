# -*- coding: utf-8 -*-
"""CrewAI 多 Agent 协作：查价 + 分析"""

import os
import asyncio
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_openai import ChatOpenAI

# 导入原始异步工具函数
from agent_tools import search_product_price, web_search

# 使用 CrewAI 的 @tool 装饰器包装同步函数
@tool("search_product_price")
def price_tool(query: str) -> str:
    """查询商品在各平台的价格，输入商品名称，返回价格信息"""
    return asyncio.run(search_product_price.ainvoke({"query": query}))

@tool("web_search")
def search_tool(query: str) -> str:
    """联网搜索最新市场行情，输入搜索关键词"""
    return asyncio.run(web_search.ainvoke({"query": query}))

# ===== 查价 Agent =====
price_searcher = Agent(
    role="商品价格查询员",
    goal="根据用户的问题，从数据库中查询所有相关商品的价格",
    backstory="你是一个经验丰富的电商比价助手，擅长快速准确地从数据库中检索商品信息。",
    tools=[price_tool, search_tool],
    verbose=True,
    allow_delegation=False,
)

# ===== 分析 Agent =====
price_analyst = Agent(
    role="价格分析师",
    goal="对比各平台价格，分析性价比，给出明确的购买建议",
    backstory="你是一个精明的消费顾问，擅长从多个平台的价格数据中找出最划算的选项。",
    tools=[],
    verbose=True,
    allow_delegation=False,
)

# ===== 任务1：查价 =====
search_task = Task(
    description="根据用户输入 {question}，查询所有相关商品在各平台的价格。",
    expected_output="各平台商品价格列表，包含商品名称、平台、价格。",
    agent=price_searcher,
)

# ===== 任务2：分析 =====
analyze_task = Task(
    description="根据查到的价格数据，进行对比分析，给出购买建议（哪个平台最便宜、性价比如何）。",
    expected_output="包含价格对比、性价比分析和最终购买建议的完整报告。",
    agent=price_analyst,
)

# ===== 配置 LLM（使用 DeepSeek） =====
deepseek_llm = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    extra_body={"thinking": {"type": "disabled"}},
)

# ===== 组建团队 =====
price_crew = Crew(
    agents=[price_searcher, price_analyst],
    tasks=[search_task, analyze_task],
    process=Process.sequential,
    verbose=True,
    llm=deepseek_llm,
)

async def run_price_analysis(question: str) -> str:
    """供 api_server.py 调用的入口函数"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: price_crew.kickoff(inputs={"question": question})
    )
    return result