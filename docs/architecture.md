# 合同管理系统 — 架构文档

## 系统目标与边界

合同管理系统（contract-mgmt）提供企业合同的全生命周期管理，包括合同创建、编辑、状态流转、附件管理和审计追踪。

### 功能边界
- **包含**：用户名密码登录、用户管理（admin）、合同 CRUD、5 状态流转、PDF/DOC/DOCX 附件上传下载（≤10MB）、审计日志
- **不包含**：OAuth/OIDC、电子签名、多租户、邮件通知、移动端适配、批量导入导出

---

## 技术栈与选择理由

| 层级 | 技术 | 理由 |
|---|---|---|
| 后端框架 | Python FastAPI 0.137 | 高性能异步框架，原生 OpenAPI 文档生成 |
| ORM | SQLAlchemy 2.0 ORM | Mapped/mapped_column 声明式模型，Session 管理 |
| 数据库 | SQLite (文件存储) | 零配置、单文件、备份简单；演示规模完全够用 |
| 模板引擎 | Jinja2 3.1 (服务端渲染) | 无需前端构建工具链，Session Cookie 天然适配 SSR |
| 认证 | Starlette SessionMiddleware | HttpOnly signed cookie (itsdangerous)，防 XSS |
| 密码哈希 | passlib[bcrypt] (bcrypt 4.3) | 行业标准，自动 salt |
| 数据校验 | Pydantic v2 + pydantic-settings | 请求体/响应体自动校验，环境变量加载 |
| 测试 | pytest 9.1 + FastAPI TestClient | 每测试独立 SQLite 数据库 |

---

## 项目结构

```
contract-mgmt/
├── app/
│   ├── main.py              # FastAPI 应用入口，lifespan，中间件注册，路由组装
│   ├── config.py            # pydantic-settings BaseSettings，8 个环境变量
│   ├── database.py          # SQLAlchemy engine + SessionLocal + Base + get_db
│   ├── dependencies.py      # get_current_user / require_admin FastAPI Depends
│   ├── models/              # ORM 模型 (4 张表)
│   │   ├── user.py          # User: id, username, password_hash, display_name, role, is_active...
│   │   ├── contract.py      # Contract: id, title, contract_no, parties, amount, status...
│   │   ├── attachment.py    # Attachment: id, contract_id(FK), filename, file_size, mime_type...
│   │   └── audit_log.py     # AuditLog: id, user_id, action, target_type, target_id, detail(JSON)
│   ├── schemas/             # Pydantic 请求/响应模型
│   │   ├── auth.py          # LoginRequest
│   │   ├── user.py          # UserCreate/UserUpdate/UserResponse/PasswordChange
│   │   ├── contract.py      # ContractCreate/ContractUpdate/StatusChange + PartyItem
│   │   └── attachment.py    # AttachmentResponse
│   ├── services/            # 业务逻辑层
│   │   ├── audit.py         # write_audit — 统一审计日志入口
│   │   ├── auth.py          # hash_password/verify_password/authenticate_user
│   │   ├── user.py          # CRUD + toggle_status + change_password + reset_password
│   │   ├── contract.py      # CRUD + 状态流转校验 + search/filter/pagination
│   │   └── attachment.py    # 上传(UUID重命名)/下载/删除 + 类型/大小校验
│   ├── routers/             # API 路由 + 页面路由
│   │   ├── auth.py          # POST /api/auth/login, /logout, GET /me
│   │   ├── users.py         # CRUD /api/users/* (admin)
│   │   ├── contracts.py     # CRUD /api/contracts/* + status
│   │   ├── attachments.py   # upload / download / delete
│   │   └── pages.py         # Jinja2 页面路由 (9 条)
│   ├── templates/           # Jinja2 模板
│   │   ├── base.html        # 全局布局 (导航栏 + flash 消息 + 模态框)
│   │   ├── login.html       # 登录卡片
│   │   ├── users/           # list.html, form.html
│   │   └── contracts/       # list.html, form.html, detail.html
│   ├── static/              # 静态资源
│   │   ├── css/style.css    # 蓝白商务风格，CSS 自定义属性，5 色状态标签
│   │   └── js/app.js        # 模态确认、文件上传预览、动态表单行、fetch 提交
│   └── middleware/
│       └── cache_control.py # ASGI 中间件：text/html 添加 Cache-Control: no-cache
├── migrations/              # SQL 迁移脚本（文档/手动执行备用）
│   ├── 001_initial_schema.sql
│   └── 002_seed_data.sql
├── scripts/
│   └── init_db.py           # 数据库初始化工具
├── tests/
│   ├── conftest.py          # pytest fixtures (独立 SQLite 数据库)
│   ├── test_auth.py         # 9 tests
│   ├── test_users.py        # 10 tests
│   ├── test_contracts.py    # 15 tests
│   └── test_attachments.py  # 11 tests
├── uploads/                 # 附件存储目录 (运行时创建)
├── requirements.txt         # Python 依赖清单
├── .env.example             # 环境变量模板
├── .gitignore
├── run.py                   # uvicorn 开发启动脚本
└── docs/                    # 文档
```

---

## 数据库设计

### 表关系

```
users (1) ────< contracts (N)       (created_by FK)
users (1) ────< attachments (N)     (uploaded_by FK)
users (1) ────< audit_logs (N)      (user_id FK)
contracts (1) ────< attachments (N)  (contract_id FK, ON DELETE CASCADE)
```

### users — 用户表

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK AUTOINCREMENT | |
| username | TEXT | UNIQUE NOT NULL | 3-50 字符 |
| password_hash | TEXT | NOT NULL | bcrypt $2b$12$ |
| display_name | TEXT | NOT NULL | 显示名称 |
| role | TEXT | NOT NULL, CHECK(admin/user) | 角色 |
| is_active | INTEGER | NOT NULL DEFAULT 1 | 1=启用, 0=禁用 |
| created_at | TEXT | NOT NULL DEFAULT datetime('now') | ISO 8601 |
| updated_at | TEXT | NOT NULL DEFAULT datetime('now') | |

### contracts — 合同表

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK AUTOINCREMENT | |
| title | TEXT | NOT NULL | 合同标题 |
| contract_no | TEXT | UNIQUE NOT NULL | 合同编号 |
| parties | TEXT | NOT NULL | JSON 数组 `[{name, role}]`, ≥2 方 |
| amount | REAL | NOT NULL | 合同金额 |
| status | TEXT | NOT NULL DEFAULT draft | CHECK 5 种状态 |
| sign_date | TEXT | NULL | YYYY-MM-DD |
| expiry_date | TEXT | NULL | YYYY-MM-DD |
| content | TEXT | NULL | 合同正文 |
| created_by | INTEGER | NOT NULL FK→users.id | |
| created_at | TEXT | NOT NULL DEFAULT datetime('now') | |
| updated_at | TEXT | NOT NULL DEFAULT datetime('now') | |

### attachments — 附件表

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK AUTOINCREMENT | |
| contract_id | INTEGER | NOT NULL FK→contracts.id ON DELETE CASCADE | |
| filename | TEXT | NOT NULL | UUID hex + 原始扩展名 |
| original_name | TEXT | NOT NULL | 用户上传时的文件名 |
| file_size | INTEGER | NOT NULL | 字节数 |
| mime_type | TEXT | NOT NULL | application/pdf 等 |
| uploaded_by | INTEGER | NOT NULL FK→users.id | |
| created_at | TEXT | NOT NULL DEFAULT datetime('now') | |

### audit_logs — 审计日志表

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | INTEGER | PK AUTOINCREMENT | |
| user_id | INTEGER | FK→users.id (nullable) | 操作人 |
| action | TEXT | NOT NULL | 如 contract_create |
| target_type | TEXT | NULL | user/contract/attachment |
| target_id | INTEGER | NULL | 目标实体 ID |
| detail | TEXT | NULL | JSON 格式操作详情 |
| ip_address | TEXT | NULL | 客户端 IP (登录/登出) |
| created_at | TEXT | NOT NULL DEFAULT datetime('now') | |

---

## API 设计

所有 API 端点前缀：`/projects/contract-mgmt/api`

### Auth (3 端点)

| Method | Path | Auth | 说明 |
|---|---|---|---|
| POST | /auth/login | 无 | 用户名+密码 → session cookie |
| POST | /auth/logout | 登录 | 清除 session |
| GET | /auth/me | 登录 | 当前用户信息 |

### Users (6 端点)

| Method | Path | Auth | 说明 |
|---|---|---|---|
| GET | /users/ | admin | 用户列表 |
| POST | /users/ | admin | 创建用户 |
| GET | /users/{id} | admin | 获取用户 |
| PUT | /users/{id} | admin | 编辑用户 |
| PUT | /users/{id}/status | admin | 启用/禁用切换 |
| PUT | /users/me/password | 登录 | 修改自己密码 |

### Contracts (6 端点)

| Method | Path | Auth | 说明 |
|---|---|---|---|
| GET | /contracts/ | 登录 | 列表 (?search=&status=&page=&page_size=) |
| POST | /contracts/ | 登录 | 创建 (status=draft) |
| GET | /contracts/{id} | 登录 | 详情 (含附件+allowed_transitions) |
| PUT | /contracts/{id} | 登录 | 编辑 (仅 draft/pending_review) |
| DELETE | /contracts/{id} | 登录 | 删除 (admin 或 draft 创建者) |
| POST | /contracts/{id}/status | 登录 | 状态变更 {status, reason} |

### Attachments (4 端点)

| Method | Path | Auth | 说明 |
|---|---|---|---|
| POST | /contracts/{id}/attachments | 登录 | 上传 (multipart/form-data) |
| GET | /contracts/{id}/attachments | 登录 | 附件列表 |
| GET | /attachments/{id}/download | 登录 | 下载 (FileResponse) |
| DELETE | /attachments/{id} | 登录 | 删除 (admin 或上传者) |

---

## 前端页面

| 路由 | 模板 | Auth | 说明 |
|---|---|---|---|
| GET / | → 重定向 /contracts | | |
| GET /login | login.html | 无 | 登录页面 |
| GET /contracts | contracts/list.html | 登录 | 搜索+筛选+分页 |
| GET /contracts/new | contracts/form.html | 登录 | 新建合同 |
| GET /contracts/{id} | contracts/detail.html | 登录 | 详情+附件+状态操作+审计 |
| GET /contracts/{id}/edit | contracts/form.html | 登录 | 编辑 (不可编辑状态自动重定向) |
| GET /users | users/list.html | admin | 用户列表 |
| GET /users/new | users/form.html | admin | 新建用户 |
| GET /users/{id}/edit | users/form.html | admin | 编辑用户 |

---

## 认证方案

```
┌─────────┐    POST /api/auth/login     ┌──────────────┐
│ Browser │ ──────────────────────────→ │  FastAPI     │
│         │    {username, password}      │              │
│         │ ←────────────────────────── │  bcrypt.verify()
│         │   Set-Cookie: session_id=   │  session["user_id"] = user.id
│         │   {user: ..., message}      │              │
└─────────┘                             └──────────────┘

后续请求:
  Cookie: session_id=xxx  →  SessionMiddleware 解密  →  get_current_user()
                                                          ├─ user_id → DB query
                                                          ├─ is_active check → 403
                                                          └─ role check → 403 (require_admin)
```

- **机制**：Starlette SessionMiddleware，signed cookie (itsdangerous)
- **Cookie**：httponly, same_site=lax, path=/projects/contract-mgmt/
- **密码**：bcrypt cost 12，passlib 库
- **Session TTL**：24 小时 (SESSION_TTL_HOURS)

---

## 附件存储方案

```
上传流程:
  Browser → multipart/form-data POST
    → validate_attachment()  (扩展名 .pdf/.doc/.docx + MIME 类型)
    → validate_file_size()   (≤10MB = 10,485,760 bytes)
    → uuid4().hex + ext      (a1b2c3d4...pdf)
    → open(uploads/{uuid}, "wb").write(content)
    → INSERT INTO attachments

下载流程:
  Browser → GET /api/attachments/{id}/download
    → DB lookup (权限校验)
    → FileResponse(uploads/{filename}, filename=original_name)

删除流程:
  DELETE → 权限检查 (admin 或上传者)
    → os.remove(uploads/{filename})
    → DELETE FROM attachments
    → 审计日志
```

- **存储路径**：`uploads/`（可配置）
- **安全**：upload 目录不通过静态文件服务暴露，仅通过认证 API 端点下载

---

## 合同状态机

```
                    ┌──────────┐
                    │   draft  │
                    └────┬─────┘
               ┌─────────┼─────────┐
               ▼         │         ▼
        ┌──────────┐    │    ┌────────────┐
        │ pending_ │    │    │ terminated │
        │ review   │    │    └────────────┘
        └────┬─────┘    │
             │          │
        ┌────▼─────┐    │
        │  active  │────┘
        └────┬─────┘
             │
        ┌────▼─────┐
        │ expired  │
        └──────────┘
```

| 当前状态 | 可转换目标 | 操作语义 |
|---|---|---|
| draft | pending_review | 提交审批 |
| draft | terminated | 终止合同 |
| pending_review | active | 审批通过 |
| pending_review | draft | 退回修改 |
| active | expired | 到期 |
| active | terminated | 终止合同 |
| expired | — | 终态 |
| terminated | — | 终态 |

---

## 审计日志动作

| 模块 | 动作 | 触发位置 |
|---|---|---|
| Auth | auth_login, auth_logout | routers/auth.py |
| User | user_create, user_update, user_toggle_status, password_change, user_reset_password | services/user.py |
| Contract | contract_create, contract_update, contract_delete, contract_status_change | services/contract.py |
| Attachment | attachment_upload, attachment_delete | services/attachment.py |

---

## 测试策略

- **框架**：pytest 9.1 + FastAPI TestClient
- **数据库隔离**：每测试独立 SQLite 临时文件 (UUID 命名)，测试后 drop_all + dispose + os.remove
- **会话管理**：独立 TestClient 实例 (app fixture + client/admin_client/user_client)
- **测试覆盖**：45 个测试，覆盖 Auth(9) + User(10) + Contract(15) + Attachment(11)

运行命令：
```bash
pytest tests/ -v --tb=short
```

---

## 部署拓扑

```
Aliyun ECS (120.24.117.67)
│
├── Nginx (反向代理)
│   └── /projects/contract-mgmt/ → http://127.0.0.1:19050
│
├── systemd: codingagent-contract-mgmt.service
│   └── uvicorn app.main:app --host 127.0.0.1 --port 19050
│
├── Conda 环境: ~/外部需求/.conda/codingagent (Python 3.11)
│
├── 部署路径: /srv/codingagent/contract-mgmt/
│
└── 静态资源: ?v=0.0.1 版本令牌 + Cache-Control: no-cache 响应头
```

---

## 安全边界

| 措施 | 说明 |
|---|---|
| 会话认证 | HttpOnly signed cookie，防 XSS 窃取 |
| CSRF | same_site=lax |
| 密码存储 | bcrypt cost 12，不可逆 |
| SQL 注入 | SQLAlchemy ORM 参数化查询 |
| 附件下载 | 仅认证 API 端点，不暴露静态文件 |
| 附件类型 | 扩展名白名单 + MIME 类型双重校验 |
| 附件大小 | 10MB 上限，上传前后双重检查 |
| 密码泄露 | 所有 API 响应通过 Pydantic 序列化，绝不含 password_hash |

---

## 已知技术债

- `db.query(Model).get(id)` 使用 SQLAlchemy 1.x 遗留 API，应迁移至 `db.get(Model, id)` (2.0 style)
- passlib 1.7.4 与 bcrypt 4.3 的 `__about__` 兼容警告（不影响功能）
- 无前端错误页面（用户不存在/合同不存在时渲染登录页显示错误信息）

---

## 关联 ADR 与最近变更

- iteration/0.0.1: 完整合同管理系统实现
- 参见 evidence/claude/technical_plan_0.0.1.json 详细技术方案
- 参见 evidence/claude/tasks_0.0.1.json 任务拆解
