# 记忆管理系统实现说明

## 概述

本系统为 AI 智能电商导购平台实现了完整的记忆管理方案，包括工作记忆、长期记忆和用户画像管理。

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                 记忆管理系统架构                          │
├─────────────────────────────────────────────────────────┤
│  用户交互层                                              │
│  - AI 客服对话                                           │
│  - 商品推荐                                              │
│  - 订单查询                                              │
├─────────────────────────────────────────────────────────┤
│  工作记忆层（Redis）                                      │
│  - 当前会话上下文                                         │
│  - 实时对话状态                                          │
│  - 24小时自动过期                                         │
├─────────────────────────────────────────────────────────┤
│  记忆提取层                                              │
│  - AI 自动识别重要信息                                    │
│  - 实体识别（用户、商品、订单）                            │
│  - 关系提取（偏好、行为模式）                              │
├─────────────────────────────────────────────────────────┤
│  长期记忆池（MySQL）                                      │
│  - 用户画像存储                                          │
│  - 行为模式存储                                          │
│  - 偏好信息存储                                          │
├─────────────────────────────────────────────────────────┤
│  记忆管理策略                                            │
│  - 压缩：精简冗余信息                                     │
│  - 丢弃：移除过时信息                                     │
│  - 选择：保留关键信息                                     │
└─────────────────────────────────────────────────────────┘
```

## 文件结构

```
AI_Projects/
├── services/
│   ├── memory_manager.py     # 记忆管理器核心模块
│   ├── redis_client.py       # Redis 连接管理
│   └── ai_customer_service.py # AI 客服（已集成记忆）
├── routes/
│   └── memory.py             # 记忆管理 API 路由
├── memory_config.py          # 记忆管理配置
├── init.sql                  # 数据库表（已添加记忆相关表）
└── test_memory.py            # 测试脚本
```

## 数据库表

### 1. user_profiles（用户画像表）
- 用户基本信息（昵称、性别、年龄段）
- 偏好信息（颜色、类别、价格区间、品牌）
- 购买行为（订单数、平均金额、购买频率）

### 2. memory_logs（记忆日志表）
- 记忆操作记录
- 置信度评分
- 来源和操作类型

### 3. user_memory_vectors（用户记忆向量表）
- 长期记忆存储
- 记忆类型分类
- 元数据

## API 接口

### 1. 获取用户记忆画像
```
GET /api/memory/profile
Authorization: Bearer <token>
```

### 2. 获取记忆列表
```
GET /api/memory/list?memory_type=preference&limit=20
Authorization: Bearer <token>
```

### 3. 搜索记忆
```
POST /api/memory/search
Authorization: Bearer <token>
Content-Type: application/json

{
    "query": "用户喜欢什么颜色",
    "limit": 5
}
```

### 4. 清除记忆
```
DELETE /api/memory/clear
Authorization: Bearer <token>
```

### 5. 记忆统计
```
GET /api/memory/stats
Authorization: Bearer <token>
```

## 工作流程

### 1. 对话记忆处理
```python
# 用户发送消息时
1. 获取工作记忆（Redis）
2. 获取用户画像和长期记忆
3. 构建上下文发送给 AI
4. AI 生成回复
5. 保存到对话历史（MySQL）
6. 提取记忆（使用 AI）
7. 更新用户偏好
8. 保存长期记忆
```

### 2. 记忆提取
- 使用 DeepSeek 模型分析对话
- 提取用户偏好（颜色、类别、品牌、价格区间）
- 提取行为意图（搜索、比较、购买）
- 生成记忆摘要

### 3. 记忆管理策略
- **压缩**：合并相似记忆，去除重复
- **衰减**：删除过期记忆（默认30天）
- **置信度**：只保留高置信度记忆

## 配置说明

在 `memory_config.py` 中可以调整以下参数：

```python
# 工作记忆
WORKING_MEMORY_TTL = 86400  # 24小时
MAX_WORKING_MEMORY = 50     # 最大条数

# 长期记忆
CONFIDENCE_THRESHOLD = 0.6  # 置信度阈值
DECAY_DAYS = 30            # 衰减天数

# 记忆提取
MEMORY_EXTRACTION_MODEL = "deepseek-chat"
```

## 使用示例

### 1. 启动服务
```bash
cd D:\python\AI_Projects
docker compose up -d
```

### 2. 执行数据库迁移
```bash
# 如果是新数据库，执行 init.sql
mysql -u root -p product_db < init.sql
```

### 3. 测试记忆系统
```bash
python test_memory.py
```

### 4. API 调用示例
```python
import httpx

# 获取记忆画像
response = httpx.get(
    "http://localhost:8000/api/memory/profile",
    headers={"Authorization": "Bearer <token>"}
)
print(response.json())
```

## 集成到 AI 客服

记忆系统已自动集成到 AI 客服服务中：

1. **自动记忆提取**：每次对话后自动提取重要信息
2. **上下文增强**：AI 回复时自动加载相关记忆
3. **偏好学习**：自动更新用户画像
4. **会话连续性**：通过工作记忆保持会话上下文

## 注意事项

1. **Redis 依赖**：确保 Redis 服务已启动
2. **数据库迁移**：新表已添加到 init.sql
3. **API Key**：需要配置 DeepSeek API Key
4. **性能考虑**：大量记忆时建议定期压缩

## 后续优化

1. 引入向量数据库（ChromaDB）进行语义搜索
2. 实现更复杂的记忆压缩算法
3. 添加记忆可视化界面
4. 支持记忆导出和导入
