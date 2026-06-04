# -*- coding: utf-8 -*-
import sys, os, time
import logging
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ================== 日志配置 ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 获取当前脚本所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ================== 注册路由模块 ==================
from routes.user import router as user_router
from routes.product import router as product_router
from routes.cart import router as cart_router
from routes.order import router as order_router
from routes.ai import router as ai_router
from routes.admin import router as admin_router

# ================== FastAPI 应用 ==================
import config
from db import init_pool, close_pool
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    """应用生命周期：启动时初始化连接池，关闭时释放"""
    await init_pool()
    yield
    await close_pool()

app = FastAPI(title="AI 智能电商导购平台", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(user_router)
app.include_router(product_router)
app.include_router(cart_router)
app.include_router(order_router)
app.include_router(ai_router)
app.include_router(admin_router)

# ================== 全局异常处理 ==================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理异常，返回统一格式错误"""
    logger.error(f"Unhandled error: {request.method} {request.url.path} - {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误，请稍后重试"},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """统一 HTTP 异常格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail},
    )

# ================== 请求日志中间件 ==================

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """记录每个请求的方法、路径、耗时"""
    start = time.time()
    response = await call_next(request)
    elapsed = round((time.time() - start) * 1000, 1)
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed}ms)")
    return response

# ================== 健康检查 ==================

@app.get("/health")
async def health_check():
    """健康检查端点（Docker/K8s 探针用）"""
    from db import get_pool
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "error", "database": str(e)})

# 静态文件服务
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# ================== API Key 鉴权（Agent/Crew 端点专用）==================
_valid_api_keys: set = None

def _get_valid_api_keys() -> set:
    """从环境变量加载有效 API Key，逗号分隔"""
    global _valid_api_keys
    if _valid_api_keys is None:
        raw = os.getenv("AGENT_API_KEYS", "")
        _valid_api_keys = {k.strip() for k in raw.split(",") if k.strip()}
        if not _valid_api_keys:
            _valid_api_keys = {"sk-agent-key-001"}  # 开发兜底
    return _valid_api_keys

def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """验证请求头中的 API Key"""
    if x_api_key not in _get_valid_api_keys():
        raise HTTPException(status_code=401, detail="无效的 API Key")
    return x_api_key

# ================== 请求限流 ==================
rate_limit_store = defaultdict(list)

def check_rate_limit(api_key: str, max_requests: int = 30, window: int = 60):
    """检查请求频率是否超限"""
    now = time.time()
    rate_limit_store[api_key] = [t for t in rate_limit_store[api_key] if now - t < window]
    if len(rate_limit_store[api_key]) >= max_requests:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    rate_limit_store[api_key].append(now)

# ================== 数据模型 ==================
class AgentRequest(BaseModel):
    question: str

# ================== Agent 接口（延迟加载避免阻塞） ==================
AGENT_SYSTEM_PROMPT = (
    "你是商品比价助手。用户询问商品价格时，请先调用 search_product_price 工具查询。"
    "用户询问市场行情时，请调用 web_search 工具。不要直接回答，先用工具查。"
)

CREW_SYSTEM_PROMPT = """你现在需要扮演两个角色来完成用户的问题：

【角色1：商品价格查询员】
- 使用 search_product_price 工具查询用户想了解的商品价格
- 把各平台的价格清晰地列出来

【角色2：价格分析师】
- 根据查到的价格数据，对比不同平台的价格差异
- 分析哪个平台最划算
- 给出明确的购买建议

流程要求：
1. 必须先以"查价员"身份调用工具查询
2. 再以"分析师"身份对数据进行分析
3. 最终输出要包含价格对比和购买建议两个部分
"""

@app.post("/agent")
async def agent_chat(request: AgentRequest, api_key: str = Depends(verify_api_key)):
    """单 Agent 模式：比价助手"""
    from agent_tools import agent as agent_executor
    try:
        check_rate_limit(api_key)
        config = {"configurable": {"thread_id": "agent-session-001"}}
        result = await agent_executor.ainvoke(
            {"messages": [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": request.question}
            ]},
            config=config
        )
        answer = result["messages"][-1].content
        return {"question": request.question, "answer": answer}
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"code": 500, "message": "AI 服务暂时不可用"})
async def crew_chat(request: AgentRequest, api_key: str = Depends(verify_api_key)):
    """多角色协作：查价 + 分析（单 Agent Prompt 版）"""
    from agent_tools import agent as agent_executor
    try:
        check_rate_limit(api_key)
        config = {"configurable": {"thread_id": "crew-session-001"}}
        result = await agent_executor.ainvoke(
            {"messages": [
                {"role": "system", "content": CREW_SYSTEM_PROMPT},
                {"role": "user", "content": request.question}
            ]},
            config=config
        )
        answer = result["messages"][-1].content
        return {"question": request.question, "answer": answer}
    except Exception as e:
        logger.error(f"Crew error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"code": 500, "message": "AI 服务暂时不可用"})

# ================== 页面路由（异步文件 I/O） ==================
import aiofiles

@app.get("/", response_class=HTMLResponse)
async def root():
    async with aiofiles.open(os.path.join(BASE_DIR, "static", "index.html"), "r", encoding="utf-8") as f:
        return await f.read()

@app.get("/product.html", response_class=HTMLResponse)
async def product_page():
    async with aiofiles.open(os.path.join(BASE_DIR, "static", "product.html"), "r", encoding="utf-8") as f:
        return await f.read()

@app.get("/cart.html", response_class=HTMLResponse)
async def cart_page():
    async with aiofiles.open(os.path.join(BASE_DIR, "static", "cart.html"), "r", encoding="utf-8") as f:
        return await f.read()

@app.get("/orders.html", response_class=HTMLResponse)
async def orders_page():
    async with aiofiles.open(os.path.join(BASE_DIR, "static", "orders.html"), "r", encoding="utf-8") as f:
        return await f.read()

@app.get("/user.html", response_class=HTMLResponse)
async def user_page():
    async with aiofiles.open(os.path.join(BASE_DIR, "static", "user.html"), "r", encoding="utf-8") as f:
        return await f.read()

@app.get("/chat.html", response_class=HTMLResponse)
async def chat_page():
    async with aiofiles.open(os.path.join(BASE_DIR, "static", "chat.html"), "r", encoding="utf-8") as f:
        return await f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
