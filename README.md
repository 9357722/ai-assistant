# 惠购商城 — AI 智能电商导购平台

> 基于 FastAPI + DeepSeek 的 AI 电商平台，核心能力为 **Agent 自主决策** 与 **混合智能搜索**。

## 在线体验

| 入口 | 地址 |
|------|------|
| 商城首页 | http://120.55.95.8:8000/ |
| AI 客服 | http://120.55.95.8:8000/chat.html |
| 商家后台 | http://120.55.95.8:8000/merchant.html |
| API 文档 | http://120.55.95.8:8000/docs |

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                      前端层                              │
│   index.html │ product.html │ cart.html │ chat.html      │
│   merchant.html │ orders.html │ user.html                │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP / WebSocket
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 FastAPI (api_server.py)                   │
│  ┌────────────────────────────────────────────────────┐ │
│  │                  路由层 (routes/)                    │ │
│  │  user │ product │ cart │ order │ ai │ admin         │ │
│  │  merchant │ multimodal                              │ │
│  └────────────────────────┬───────────────────────────┘ │
│                           ▼                              │
│  ┌────────────────────────────────────────────────────┐ │
│  │                  服务层 (services/)                   │ │
│  │  ai_customer_service │ hybrid_search                │ │
│  │  recommendation │ merchant_agent                    │ │
│  │  cache(Redis) │ websocket_manager                   │ │
│  └────────────────────────┬───────────────────────────┘ │
│                           ▼                              │
│  ┌────────────────────────────────────────────────────┐ │
│  │                  数据层                              │ │
│  │  MySQL(商品/订单) │ Redis(缓存/限流)                │ │
│  │  ChromaDB(向量)   │ DeepSeek API(AI)               │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 核心 AI 能力

### 1. Agent 自主决策（ReAct 模式）

AI 客服基于 ReAct 循环构建，LLM 自主判断何时调用工具、调哪个工具，支持多轮推理：

```
用户: "小米14和iPhone16哪个便宜？"
  → Agent 调用 search_product_price 查询两款商品
  → Agent 调用 calculator 计算差价
  → Agent 整合结果，生成对比建议
```

支持 10+ 工具：商品查询、多平台比价、订单操作、优惠券查询、尺码推荐、评价分析等。

### 2. 混合搜索引擎

四棒搜索流水线，结合规则召回与语义召回：

```
用户输入 → 意图识别 → 同音纠错 → 混合召回 → 精排打分 → 分页返回
```

- **意图提取**：从自然语言中提取商品类别、品牌、价格区间等结构化意图
- **同音纠错**："苹裹手机" → "苹果手机"，"蓝压耳机" → "蓝牙耳机"
- **规则召回**：MySQL FULLTEXT 索引 + 条件过滤（主要）
- **向量召回**：ChromaDB 语义相似度匹配（补充）
- **精排打分**：多维度加权排序

### 3. 多 Agent 协作

Orchestrator + 子 Agent 三层协作架构：

```
Orchestrator（总调度）
  ├── SearchAgent（商品搜索）
  └── CompareAgent（价格对比）
```

Orchestrator 负责任务拆解与结果整合，子 Agent 各司其职，支持复杂多步骤查询。

### 4. RAG 知识增强

基于 ChromaDB 的商品知识库，为 AI 客服提供精准上下文：

- 商品信息 Embedding 向量化存储
- 余弦相似度检索相关商品
- 检索结果注入 Prompt，减少大模型幻觉

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI（全异步） |
| AI 引擎 | DeepSeek-V4-Flash + Function Calling |
| 向量库 | ChromaDB |
| 关系数据库 | MySQL 8.0 + aiomysql 异步连接池 |
| 缓存 | Redis（缓存 + 滑动窗口限流） |
| 实时通信 | WebSocket（订单状态推送） |
| 容器化 | Docker + Docker Compose |
| CI/CD | GitHub Actions 自动部署 |
| 云服务 | 阿里云 ECS |

## 项目结构

```
├── api_server.py              # FastAPI 主服务入口 + 生命周期管理
├── config.py                  # 配置管理（环境变量）
├── auth.py                    # JWT 认证 + 密码哈希
├── db.py                      # MySQL 异步连接池（aiomysql）
├── agent_tools.py             # Agent 工具定义（ReAct 模式）
├── init.sql                   # 数据库初始化脚本
│
├── routes/                    # 路由层
│   ├── user.py                #   用户注册/登录/地址管理
│   ├── product.py             #   商品 CRUD + 搜索
│   ├── cart.py                #   购物车
│   ├── order.py               #   订单（创建/支付/取消/发货）
│   ├── ai.py                  #   AI 客服 + 推荐
│   ├── admin.py               #   管理员后台
│   ├── merchant.py            #   商家后台 + Agent 助手
│   └── multimodal.py          #   多模态（图像识别/生成）
│
├── services/                  # 服务层
│   ├── ai_customer_service.py #   AI 客服核心（工具调用 + 多轮记忆）
│   ├── hybrid_search.py       #   混合搜索引擎（规则 + 向量）
│   ├── intent_extractor.py    #   意图识别
│   ├── typo_fixer.py          #   同音纠错
│   ├── recommendation.py      #   推荐引擎
│   ├── merchant_agent.py      #   商家智能助手
│   ├── cache.py               #   Redis 缓存（优雅降级）
│   └── websocket_manager.py   #   WebSocket 连接管理
│
├── ai/                        # AI 模块
│   ├── agents/                #   多 Agent 协作
│   ├── tools/                 #   Agent 工具集
│   ├── memory/                #   对话记忆管理
│   └── workflows/             #   工作流编排
│
├── static/                    # 前端页面
│   ├── index.html             #   商城首页
│   ├── chat.html              #   AI 客服对话
│   ├── product.html           #   商品详情
│   ├── cart.html              #   购物车
│   ├── orders.html            #   订单管理
│   ├── merchant.html          #   商家后台
│   └── common.js              #   公共工具函数
│
├── docker-compose.yml         # Docker 编排
├── Dockerfile                 # 镜像构建
└── requirements.txt           # Python 依赖
```

## 快速启动

```bash
# 克隆项目
git clone https://github.com/9357722/ai-assistant.git
cd ai-assistant

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DeepSeek API Key、MySQL/Redis 连接信息

# Docker 一键启动
docker compose up -d

# 访问
# 商城首页: http://localhost:8000/
# API 文档: http://localhost:8000/docs
```

## 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| Agent 工具调用 | ReAct 循环 + JSON 文本 | 兼容所有 LLM，不依赖原生 Function Calling |
| 搜索策略 | 规则召回为主 + 向量召回补充 | 规则召回精确，向量召回处理语义模糊查询 |
| 缓存降级 | Redis 不可用时返回 None | 部分组件故障不影响核心功能 |
| 登录限流 | Redis 滑动窗口 + 内存降级 | 防暴力破解，Redis 挂了仍能限流 |
| 密码存储 | bcrypt（cost=12） | 工业界标准，抗彩虹表攻击 |

## 作者

**伍雯靓** · AI 应用开发工程师

- GitHub: [@9357722](https://github.com/9357722)
- 求职方向: AI 应用开发 / Agent 开发 / 后端开发
