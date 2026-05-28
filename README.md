# 🛒 AI 智能商品比价助手

> 基于 FastAPI + LangChain + DeepSeek 的智能商品比价 API，支持多平台价格查询、Agent 自主调用工具、多角色协作分析。

## 🚀 在线体验

- **API 文档**：[http://120.55.95.8:8000/docs](http://120.55.95.8:8000/docs)
- **聊天页面**：[http://120.55.95.8:8080/chat.html](http://120.55.95.8:8080/chat.html)

## 🧠 核心功能

- ✅ **智能比价**：输入商品名称，自动查询京东、淘宝、拼多多等平台价格
- ✅ **Agent 自主决策**：AI 自主调用数据库查询工具、联网搜索工具、计算器
- ✅ **多角色协作**：查价 Agent + 分析 Agent 分工合作，输出购买建议
- ✅ **RAG 增强检索**：基于 ChromaDB 向量数据库的商品知识库问答
- ✅ **异步高并发**：全链路 async/await，支持同时处理多个请求
- ✅ **API 安全鉴权**：API Key 验证 + 请求频率限流

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI (异步) |
| **AI 引擎** | LangChain + LangGraph + DeepSeek-V4-Flash |
| **Agent** | 自定义 Tool + MemorySaver 记忆系统 |
| **向量数据库** | ChromaDB |
| **关系数据库** | MySQL 8.0 |
| **容器化** | Docker + Docker Compose |
| **CI/CD** | GitHub Actions 自动部署 |
| **云服务** | 阿里云 ECS (Ubuntu 26.04) + OSS |

## 📁 项目结构
├── api_server.py # FastAPI 主服务（含鉴权、限流、所有接口）
├── agent_tools.py # Agent 工具函数（商品查询、计算器、联网搜索）
├── crew_agent.py # 多 Agent 协作编排
├── utils.py # 工具函数（ChatSession、向量数据库初始化）
├── recommend.py # 商品推荐模块
├── docker-compose.yml # 一键编排 API + MySQL
├── Dockerfile # 镜像构建文件
├── requirements.txt # Python 依赖
├── init.sql # 数据库初始化脚本
├── chat.html # 前端聊天页面
└── .github/workflows/ # CI/CD 自动部署工作流

📡 API 接口
接口	方法	说明
/chat	POST	普通对话
/agent	POST	Agent 模式（自主调用工具）
/crew	POST	多角色协作（查价+分析+建议）
/chat/stream	POST	流式对话
/add_product_db	POST	添加商品到数据库
/update_price	PUT	修改商品价格
/delete_product	DELETE	删除商品

👤 关于作者
技能：Python / FastAPI / LangChain / Docker / MySQL / CI/CD

求职方向：AI 应用开发工程师 / 后端开发工程师