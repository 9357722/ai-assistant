# AI 智能商品比价助手

## 项目概述
基于 FastAPI + LangChain + DeepSeek 的 AI 智能商品比价助手，支持 RAG 检索增强、Agent 工具调用、多轮对话记忆。

## 技术栈
- **后端**: FastAPI + LangChain + DeepSeek-V4-Flash
- **前端**: chat.html (HTML/JS)
- **数据库**: MySQL 8.0 (product_db)
- **向量库**: ChromaDB
- **记忆**: LangGraph MemorySaver + ChatSession
- **容器化**: Docker + Docker Compose

## 核心文件
- `agent_tools.py` — Agent 工具定义（商品查询、计算器、联网搜索）
- `api_server.py` — FastAPI 主服务
- `chat.html` — 前端聊天页面（位于 D:\python\chat.html）
- `docker-compose.yml` — 容器编排
- `init.sql` — 数据库初始化脚本
- `requirements.txt` — Python 依赖

## API 端点
- `POST /chat/stream` — 流式对话
- `POST /agent` — Agent 模式（工具调用）
- `POST /compare` — 商品对比
- `POST /recommend` — 智能推荐
- `POST /clear` — 清空对话

## 部署信息
- **ECS**: 120.55.95.8 (阿里云)
- **API**: http://120.55.95.8:8000
- **前端**: http://120.55.95.8:8080/chat.html
- **Lobe Chat**: http://120.55.95.8:3210

## 开发命令
```bash
# 启动开发环境
cd D:\python\AI_Projects
docker compose up -d

# 重新构建
docker build -t ai-assistant:slim .
docker compose down && docker compose up -d

# 测试 API
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-agent-key-001" \
  -d '{"question":"华为手机多少钱"}'
```

## 编码规范
- Python: 使用 async/await 异步编程
- 前端: 原生 HTML/JS，使用 fetch + ReadableStream 流式处理
- 数据库: aiomysql 异步驱动
- 环境变量: API Key 必须通过 os.getenv() 读取，禁止硬编码
