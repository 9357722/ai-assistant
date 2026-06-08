# 🛒 惠购商城

> 基于 FastAPI + LangChain + DeepSeek 的智能电商平台，支持 AI 比价、商品管理、购物车、订单支付、商家后台等功能。

## 🚀 在线体验

- **商城首页**：[http://120.55.95.8:8000/](http://120.55.95.8:8000/)
- **API 文档**：[http://120.55.95.8:8000/docs](http://120.55.95.8:8000/docs)

## 🧠 核心功能

### 用户端
- ✅ **商品浏览**：分类筛选、搜索、商品详情展示
- ✅ **购物车**：添加商品、数量调整、批量结算
- ✅ **订单管理**：下单、模拟支付（支付宝/微信）、取消订单
- ✅ **收货地址**：多地址管理、默认地址设置
- ✅ **AI 比价**：智能查询多平台价格，输出购买建议

### 商家端
- ✅ **商品管理**：商品 CRUD、上下架、库存管理
- ✅ **图片上传**：商品图片本地存储
- ✅ **订单处理**：查看订单、发货操作

### 技术特性
- ✅ **Agent 自主决策**：AI 自主调用数据库查询、联网搜索、计算器
- ✅ **多角色协作**：查价 Agent + 分析 Agent 分工合作
- ✅ **WebSocket 实时通知**：订单状态变更实时推送
- ✅ **Redis 缓存**：热门商品、会话缓存加速（MD5 哈希 key）
- ✅ **JWT 鉴权**：Token 认证 + 密码 bcrypt 加密
- ✅ **安全防护**：XSS 防护、输入验证、敏感信息脱敏日志

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI (异步) |
| **AI 引擎** | LangChain + DeepSeek-V4-Flash |
| **关系数据库** | MySQL 8.0 |
| **缓存** | Redis |
| **容器化** | Docker + Docker Compose |
| **CI/CD** | GitHub Actions 自动部署 |
| **云服务** | 阿里云 ECS |

## 📁 项目结构

```
├── api_server.py          # FastAPI 主服务入口
├── routes/
│   ├── product.py         # 商品接口
│   ├── order.py           # 订单接口（含支付）
│   ├── cart.py            # 购物车接口
│   ├── merchant.py        # 商家后台接口
│   └── user.py            # 用户认证接口
├── services/
│   ├── payment.py         # 支付服务（支付宝/微信模拟）
│   ├── cache.py           # Redis 缓存服务
│   └── websocket_manager.py  # WebSocket 实时通知
├── models/                # 数据模型定义
├── static/                # 前端静态页面
│   ├── index.html         # 商城首页
│   ├── product.html       # 商品详情
│   ├── cart.html          # 购物车
│   ├── orders.html        # 订单管理
│   ├── merchant.html      # 商家后台
│   └── user.html          # 用户中心
├── docker-compose.yml     # Docker 编排
├── Dockerfile             # 镜像构建
├── requirements.txt       # Python 依赖
└── init.sql               # 数据库初始化
```

## 📡 API 接口

### 商品接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/products` | GET | 商品列表（支持分类筛选） |
| `/api/products/{id}` | GET | 商品详情 |

**请求示例**：
```bash
# 获取商品列表
curl http://localhost:8000/api/products?page=1&page_size=10&category_id=1

# 获取商品详情
curl http://localhost:8000/api/products/1
```

**响应示例**：
```json
{
  "total": 100,
  "page": 1,
  "page_size": 10,
  "items": [
    {
      "id": 1,
      "name": "iPhone 17 Pro",
      "price": 7999.00,
      "platform": "京东",
      "stock": 50,
      "sales": 12,
      "main_image": "/static/products/iPhone_17_Pro.jpg"
    }
  ]
}
```

### 用户认证

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/user/register` | POST | 用户注册 |
| `/api/user/login` | POST | 用户登录 |

**登录请求示例**：
```bash
curl -X POST http://localhost:8000/api/user/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "123456"}'
```

**登录响应示例**：
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "testuser",
    "role": "user"
  }
}
```

### 购物车接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/cart` | GET | 获取购物车 |
| `/api/cart` | POST | 添加商品到购物车 |
| `/api/cart/{id}` | PUT | 更新购物车项 |
| `/api/cart/{id}` | DELETE | 删除购物车项 |

### 订单接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/orders` | GET | 订单列表 |
| `/api/orders` | POST | 创建订单 |
| `/api/orders/{id}` | GET | 订单详情 |
| `/api/orders/{id}/pay` | POST | 模拟支付 |
| `/api/orders/{id}/cancel` | POST | 取消订单 |

**创建订单请求示例**：
```bash
curl -X POST http://localhost:8000/api/orders \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "address_id": 1,
    "cart_item_ids": [1, 2, 3],
    "remark": "请尽快发货"
  }'
```

### 商家接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/merchant/products` | GET | 商家商品列表 |
| `/api/merchant/products` | POST | 创建商品 |
| `/api/merchant/orders` | GET | 商家订单列表 |

### AI 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/ai/recommendations` | GET | 个性化推荐 |
| `/api/ai/chat` | POST | AI 客服对话 |
| `/api/ai/chat/stream` | POST | AI 客服流式对话 |

### 监控接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/metrics` | GET | Prometheus 指标 |
| `/api/user/login` | POST | 用户登录 |
| `/api/user/register` | POST | 用户注册 |

## 👤 关于作者

**技能**：Python / FastAPI / LangChain / Docker / MySQL / Redis / CI-CD

**求职方向**：AI 应用开发工程师 / 后端开发工程师
