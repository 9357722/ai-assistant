# v审查报告

审查时间：2026-06-09  
项目路径：D:\python\AI_Projects  
审查范围：FastAPI 后端、静态前端、Docker/Compose、CI/CD、数据库 schema、测试脚本、Git 仓库卫生。  
审查方式：静态代码审查 + Docker 运行态验证。未改业务代码。

## 总体结论

当前项目功能面较完整，用户、购物车、订单、商品、商家后台、AI 模块都有成型实现；旧 Docker 容器当前可运行，`/health` 和商品列表接口可用。

但项目还不能作为“可复现、可安全部署”的状态交付。主要风险集中在：密钥泄露、Docker 从零构建失败、运行镜像与本地源码漂移、生产默认 JWT 密钥、依赖清单不完整、商家输入校验不足、Docker 构建会漏静态图片、CI/CD 触发策略危险。

## 运行态验证结果

| 项目 | 结果 | 说明 |
|---|---:|---|
| Docker 可用性 | 通过 | Docker 29.4.2，Compose v5.1.3 |
| `docker compose up --build -d` | 失败 | 构建卡在 `Dockerfile:4` 的 `apt-get update && apt-get install curl`，Debian 源连接/索引失败 |
| 旧容器状态 | 通过 | `ai-assistant` 容器已存在并处于 healthy |
| `/health` | 通过 | 返回 `status=ok`，数据库 connected |
| `/api/products?page_size=2` | 通过 | 返回商品数据，总数 569 |
| `/` 首页 | 通过 | HTTP 200 |
| `/docs` | 通过 | HTTP 200，API 文档公开可访问 |
| `/metrics` | 失败/漂移 | 当前源码有 `/metrics`，但运行旧容器返回 404 |
| 商品图片静态资源 | 旧容器通过 | `/static/products/product_586.jpg` 返回 200；但当前 `.dockerignore` 从零构建会排除 jpg |

### 关键运行态发现

1. 运行容器不是当前源码构建结果。  
   容器内 `/app/api_server.py` SHA256 与本地 `api_server.py` SHA256 不一致；容器无 `/metrics` 路由，而本地源码有。

2. 当前旧镜像里依赖存在，但 `requirements.txt` 不完整。  
   容器里能找到 `aiofiles`、`email_validator`、`aiomysql`、`redis`，但本地依赖清单缺 `aiofiles` 和 `email-validator`。

3. 容器环境变量中暴露了真实数据库密码和 API Key。  
   `docker inspect ai-assistant` 可直接看到敏感环境变量。报告不记录密钥值，但这些凭据应按泄露处理并轮换。

## 高危问题

### 1. 密钥和数据库密码暴露

证据：
- Docker 容器环境变量包含数据库密码、DeepSeek/OpenAI/SiliconFlow 等 API Key。
- 多个脚本硬编码 MySQL root 密码：`add_products.py:3`、`import_products.py:5`、`download_v2.py:4`、`test_admin.py:14`、`test_ai.py:14`、`test_cart_order.py:13`、`test_product.py:14`、`test_user_auth.py:15` 等。
- `CLAUDE.md:48`、阶段总结文档中出现示例 API Key 形式，容易误导复制到真实配置。

影响：
- 任何能访问 Docker 主机或仓库的人都可能获取凭据。
- 若这些值曾推送到远端，应视作已泄露。

建议：
- 立即轮换数据库密码和所有已暴露 API Key。
- 脚本统一改为读取环境变量，不写死 root 密码。
- 使用最小权限数据库账号，不使用 root。
- 生产密钥改用服务器 secret 管理，不直接长期放在 compose 环境变量里。

### 2. JWT 默认密钥可能被生产误用

证据：
- `config.py:16-23`：`SECRET_KEY` 缺失时开发环境会使用固定默认密钥。
- `docker-compose.yml:12` 传 `SECRET_KEY`，但没有设置 `ENV=production` 强制校验。
- 当前运行容器使用的是开发风格密钥配置。

影响：
- 如果生产部署漏配密钥，JWT 可被伪造，用户/管理员身份都可能被绕过。

建议：
- 生产环境始终设置 `ENV=production`。
- 启动时无条件要求 `SECRET_KEY` 满足长度和随机性要求。
- 删除可预测默认密钥，或仅在本地测试入口显式启用。

### 3. 当前源码从零 Docker 构建失败

证据：
- `docker compose up --build -d` 失败在 `Dockerfile:4`：`apt-get update && apt-get install curl`。
- CI 部署流程 `.github/workflows/deploy.yml:27` 使用 `docker compose build --no-cache`，线上会触发同类风险。

影响：
- 旧容器能跑不代表新提交能部署。
- 一旦服务器清理镜像或 CI 重新构建，服务可能无法恢复。

建议：
- 固定基础镜像 digest 或使用稳定 Debian 版本。
- 配置可靠镜像源/apt 源，或去掉 curl 依赖，改用 Python healthcheck。
- 在 CI 里先 build/test，再部署，不要只在远端服务器上构建。

### 4. 运行镜像与本地源码漂移

证据：
- 本地 `api_server.py` SHA256 与容器内 `/app/api_server.py` 不一致。
- 本地源码有 `/metrics`，旧容器没有。
- 旧容器依赖存在，但 `requirements.txt` 缺依赖。

影响：
- 当前运行结果不能证明当前源码可运行。
- 排查线上问题时会出现“代码看起来有，服务却没有”的错觉。

建议：
- 每次发布记录 Git commit、镜像 digest、构建时间。
- 服务启动时暴露 `/version`，返回 commit SHA 和镜像版本。
- CI 构建镜像后推送，再由服务器拉取指定镜像，不在服务器现场构建未知状态。

## 中高危问题

### 5. Refresh Token 逻辑允许过期 Token 无限续期

证据：
- `auth.py:64-75` 的 `decode_token_allow_expired` 关闭 `verify_exp`。
- `routes/user.py:215` 刷新接口只要签名有效、用户存在，就能签发新 Token。

影响：
- 被窃取的旧 Token 长期可用。
- 无法有效撤销会话。

建议：
- 区分 access token 和 refresh token。
- refresh token 设置单独过期时间、撤销表、token version。
- 密码修改、用户禁用、登出时使旧 refresh token 失效。

### 6. WebSocket JWT 放在 URL 路径中

证据：
- `api_server.py:193`：`/ws/{token}`。
- `static/ws.js:22`：前端把 localStorage token 拼进 ws URL。
- `api_server.py:123` 会记录请求 path，代理和浏览器历史也可能记录 URL。

影响：
- JWT 容易进入日志、代理、浏览器记录和错误追踪系统。

建议：
- 改为短期一次性 WebSocket ticket。
- 或使用 HttpOnly/Secure/SameSite Cookie 做鉴权。
- 日志中明确脱敏 token、Authorization、API Key。

### 7. 依赖清单不完整，当前源码新环境可能启动失败

证据：
- `api_server.py:348` 使用 `aiofiles`，`requirements.txt` 未声明。
- `models/user.py:8` 使用 `EmailStr`，需要 `email-validator`，`requirements.txt` 未声明。
- 本机系统 Python 导入失败缺 `redis`，项目 `ai_env` 导入失败缺 `aiomysql`，说明本地环境也不可复现。

建议：
- 补充 `aiofiles`、`email-validator`。
- 用 `pip-tools`、`uv lock` 或 Poetry 固化依赖。
- CI 中执行 `pip install -r requirements.txt && python -c "import api_server"`。

### 8. 商家商品接口缺少后端输入约束

证据：
- `routes/merchant.py:33-39` 的 `ProductCreate`：`price: float`、`stock: Optional[int] = 100`，无 `gt/ge`。
- `routes/merchant.py:155` 使用 `data: dict` 更新商品，无 Pydantic schema。
- `services/merchant_service.py:120` 直接把 price/stock 写入 products。
- `init.sql:8`、`init.sql:14` 无 price/stock 的 `CHECK` 约束。

影响：
- 商家可以提交负价格、负库存、异常状态，影响订单金额和库存逻辑。

建议：
- 商家商品创建/更新复用 `models.product.ProductCreate/ProductUpdate`。
- DB 层增加 `CHECK (price > 0)`、`CHECK (stock >= 0)`。
- 所有 `data: dict` 改成明确的请求模型。

### 9. Docker 构建会漏掉商品图片

证据：
- `.dockerignore:26-27` 排除 `*.png`、`*.jpg`。
- 商品图片位于 `static/products/*.jpg`。
- `.gitignore` 对 static/products 做了例外，但 `.dockerignore` 没有。

影响：
- 旧容器图片可访问；从当前源码重新构建后，商品图大概率 404。

建议：
- `.dockerignore` 增加：
  - `!static/products/`
  - `!static/products/*.jpg`
  - `!static/products/*.png`
  - `!static/products/*.jpeg`
- 或把商品图片放到对象存储/CDN，不打入镜像。

### 10. CI/CD 会在 PR 上直接部署

证据：
- `.github/workflows/deploy.yml:3-7` 同时监听 `push main` 和 `pull_request main`。
- Job 名为 deploy，并直接 SSH 到 ECS 执行部署。

影响：
- Pull request 事件也可能触发部署逻辑，风险过高。

建议：
- PR 只运行 lint/test/build，不部署。
- 部署只允许 `push main` 或手动 `workflow_dispatch`。
- 使用环境保护、审批和并发锁。

### 11. CI 回滚逻辑基本不可用

证据：
- `.github/workflows/deploy.yml:41` 读取 `/tmp/rollback_info.txt`。
- 工作流中没有写入该文件。
- 因此失败时 `PREV_COMMIT` 大概率是 `none`，不会真正回滚。

建议：
- 部署前记录当前 commit 和镜像 tag。
- 回滚应拉取上一版镜像，而不是在服务器上 `git reset --hard`。

## 中危问题

### 12. 当前源码 `/health` 可能泄露数据库错误细节

证据：
- `api_server.py:163`：健康检查失败时返回 `database: str(e)`。

影响：
- 公开环境中可能暴露数据库主机、账号、网络错误、驱动细节。

建议：
- 对外只返回 `database: unavailable`。
- 详细错误只写服务端日志。

### 13. 慢查询日志可能记录敏感参数

证据：
- `db.py:27-28` 会记录 SQL 片段和 params。

影响：
- 地址、手机号、备注、搜索内容等可能进入日志。

建议：
- 对手机号、地址、token、password、api_key 等字段做脱敏。
- 慢查询日志记录 query hash、耗时、调用点，避免完整 params。

### 14. 前端存在 XSS 风险点

证据：
- 大量使用 `innerHTML`：`static/product.html:681`、`static/product.html:757`、`static/cart.html:366`、`static/merchant.html:1317`、`static/orders.html:439` 等。
- 部分字段有 `escapeHTML`，但不是全覆盖。例如商品详情中的 `platform`、`category_name`，图片 URL 属性等。
- Token 存储在 localStorage：`static/common.js:36`、`static/user.html:833`、`static/ws.js:14`。

影响：
- 一旦商品名、平台、图片 URL、订单字段被注入恶意内容，可能读取 localStorage 中的 JWT。

建议：
- 默认用 `textContent` 和 DOM API 创建元素。
- 对 URL 字段做白名单校验，只允许 `/static/products/` 或可信 CDN。
- Token 迁移到 HttpOnly Cookie，降低 XSS 后果。

### 15. 商家订单状态机与数据库枚举不一致

证据：
- `services/merchant_service.py:199` 允许 `shipped -> returned`。
- `init.sql:114` 的订单状态 ENUM 没有 `returned`。

影响：
- 按 schema 新建数据库后，退货状态更新会失败。
- 业务层和数据库层状态定义分裂。

建议：
- 统一订单状态枚举。
- 把状态机抽到单一模块，数据库迁移同步更新。
- 给状态流转写自动化测试。

### 16. 支付/退款逻辑状态命名不一致

证据：
- `services/payment.py:23` 定义 `REFUNDED = "refunded"`。
- `services/payment.py:167` 退款后实际把订单状态改成 `cancelled`。
- `init.sql:114` 没有 `refunded`。

影响：
- 财务语义不清：取消、退款、退货混在一起。

建议：
- 拆分订单状态和退款状态。
- 增加 refund_records/payment_records 表。

### 17. API 文档公开暴露

证据：
- 运行态 `/docs` 返回 200。

影响：
- 公网部署时会暴露内部管理、Agent、商家接口结构。

建议：
- 生产环境关闭 `/docs`、`/redoc`、`/openapi.json`，或加 IP 白名单/鉴权。

### 18. 测试不可复现，且依赖真实数据库

证据：
- `test_admin.py`、`test_ai.py`、`test_cart_order.py`、`test_product.py` 等直接连接 localhost MySQL。
- 多个测试脚本硬编码数据库密码。
- 不是标准 pytest 隔离测试，缺少 fixtures、测试库迁移和清理。

影响：
- CI 难以运行。
- 测试可能污染真实/开发数据库。

建议：
- 引入 pytest + pytest-asyncio。
- 使用独立 test database，通过迁移初始化。
- 测试凭据读取环境变量。
- 对订单创建/库存扣减/状态流转做集成测试。

## 低危/工程质量问题

### 19. Git 跟踪了构建产物和第三方依赖

证据：
- `git ls-files node_modules`：387 个文件被跟踪。
- `git ls-files __pycache__`：4 个文件被跟踪。
- `.gitignore` 有 `__pycache__/`，但没有 `node_modules/`。

建议：
- 增加 `node_modules/` 到 `.gitignore`。
- 执行 `git rm -r --cached node_modules __pycache__`。

### 20. 项目目录有大量本地归档和截图

证据：
- 根目录存在多个数百 MB tar/zip 和大量截图。
- 这些归档未被 Git 跟踪，是好事，但会干扰本地维护。

建议：
- 移到 `artifacts/` 或项目外目录。
- 保持源码仓库只放源码、必要静态资源和文档。

### 21. Docker Compose 只定义 api，不定义 MySQL/Redis

证据：
- `docker-compose.yml` 通过 `host.docker.internal` 连接宿主机 MySQL/Redis。

影响：
- 新机器无法一键启动完整系统。

建议：
- 开发 compose 增加 mysql/redis 服务。
- 生产 compose 明确外部托管服务和健康检查。

## 优先修复路线

### P0：先止血

1. 轮换所有已暴露的数据库密码和 API Key。
2. 删除/替换脚本里的硬编码密码。
3. 生产禁用默认 JWT 密钥，设置 `ENV=production`。
4. 修复 Docker 从零构建失败。
5. 补齐 `requirements.txt`：`aiofiles`、`email-validator`。

### P1：保证可部署可回滚

1. 修复 `.dockerignore`，确保静态商品图不会被排除。
2. CI 改为：PR 只测试，main 才部署。
3. 部署改为构建镜像 -> 推送 registry -> 服务器拉指定 tag。
4. 加 `/version` 显示 commit SHA 和镜像版本。
5. 修复回滚逻辑，不依赖不存在的 `/tmp/rollback_info.txt`。

### P2：补业务安全和测试

1. 商家商品/优惠券/订单更新接口全部改成 Pydantic schema。
2. 统一订单状态枚举，修复 returned/refunded/cancelled 语义。
3. WebSocket 鉴权从 URL token 改成 ticket/cookie。
4. 前端减少 `innerHTML`，统一 DOM API 和 URL 白名单。
5. 建立 pytest 集成测试，覆盖登录、下单、支付、取消、商家发货。

## 建议验收标准

- `docker compose build --no-cache` 可以稳定通过。
- 新构建镜像启动后 `/health`、`/api/products`、`/static/products/*.jpg` 均通过。
- 当前源码构建镜像后 `/metrics` 行为与源码一致。
- `python -c "import api_server"` 在干净虚拟环境中通过。
- Git 中不再跟踪 `node_modules`、`__pycache__`、密钥文件。
- Secret 扫描无真实密钥命中。
- PR 不再触发部署。
