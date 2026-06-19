# 合同管理系统 — 运行手册

## 本地安装与启动

### 1. 环境准备

项目复用共享 Conda 环境：
```bash
# 激活共享环境
conda activate ~/外部需求/.conda/codingagent

# 若环境不存在，创建并安装依赖
conda create -p ~/外部需求/.conda/codingagent python=3.11 -y
conda activate ~/外部需求/.conda/codingagent
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 按需修改（默认值即可用于本地开发）
```

环境变量说明：

| 变量 | 默认值 | 说明 |
|---|---|---|
| DATABASE_URL | sqlite:///./contract_mgmt.db | SQLite 数据库文件路径 |
| UPLOAD_DIR | ./uploads | 附件存储目录（自动创建） |
| SECRET_KEY | change-me-in-production | Session 签名密钥 |
| SESSION_TTL_HOURS | 24 | Session 过期时间 |
| MAX_UPLOAD_SIZE_MB | 10 | 附件上传大小上限 |
| BASE_PATH | /projects/contract-mgmt | 应用部署路径前缀 |
| APP_VERSION | 0.0.1 | 当前版本号（静态资源版本令牌） |
| LOG_LEVEL | INFO | 日志级别 |

### 3. 初始化数据库

```bash
python scripts/init_db.py
```

这将：
- 创建 SQLite 数据库文件
- 执行建表 DDL
- 插入演示账号和示例合同

### 4. 启动开发服务器

```bash
# 方式一：使用 run.py
python run.py

# 方式二：直接使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 访问应用

- 主页：http://localhost:8000/projects/contract-mgmt/
- 登录页：http://localhost:8000/projects/contract-mgmt/login
- API 文档：http://localhost:8000/docs

### 演示账号

| 用户名 | 密码 | 角色 |
|---|---|---|
| admin | admin123 | 管理员（全部权限） |
| user | user123 | 普通用户（合同管理，无用户管理） |

---

## 测试

### 运行全部测试

```bash
pytest tests/ -v --tb=short
```

预期输出：**45 passed**

### 测试架构

- 每测试使用独立 SQLite 临时文件数据库（UUID 命名）
- 自动创建表结构和演示账号
- 测试后自动清理（drop_all + 删除临时文件）
- `app` fixture 创建 FastAPI 应用，`client`/`admin_client`/`user_client` 提供不同认证状态的 TestClient

### 测试文件

| 文件 | 测试数 | 覆盖范围 |
|---|---|---|
| tests/test_auth.py | 9 | 登录/登出/会话/禁用用户 |
| tests/test_users.py | 10 | 用户 CRUD/角色权限/密码修改 |
| tests/test_contracts.py | 15 | 合同 CRUD/状态流转/搜索/筛选/权限 |
| tests/test_attachments.py | 11 | 附件上传/类型校验/下载/删除/权限 |

---

## 健康检查

```bash
curl http://localhost:8000/projects/contract-mgmt/healthz
# → {"status":"ok","version":"0.0.1"}
```

---

## Base Path

所有路由和静态资源统一位于 `/projects/contract-mgmt/` 前缀下：

- API：`/projects/contract-mgmt/api/auth/login`
- 页面：`/projects/contract-mgmt/contracts`
- 静态资源：`/projects/contract-mgmt/static/css/style.css?v=0.0.1`

不得假设应用部署在 `/` 根路径。

---

## 缓存策略

### HTML 文档

所有 `text/html` 响应由 `CacheControlMiddleware` (ASGI 中间件) 自动添加以下 HTTP 响应头：

```
Cache-Control: no-cache, no-store, must-revalidate
Pragma: no-cache
Expires: 0
```

**注意**：这是真实的 HTTP 响应头，非 `<meta>` 标签。浏览器验收要求服务器下发的 HTTP 头包含 `Cache-Control: no-cache`。

### 静态资源

所有 CSS/JS 引用携带版本令牌：
```html
<link rel="stylesheet" href="/projects/contract-mgmt/static/css/style.css?v=0.0.1">
<script src="/projects/contract-mgmt/static/js/app.js?v=0.0.1"></script>
```

版本令牌随 `APP_VERSION` 递增，每个交付版本自动触发缓存失效。

---

## 部署步骤

### Aliyun 部署

目标服务器：`aliyun-cowork` (120.24.117.67)

```bash
# 1. SSH 到服务器
ssh aliyun-cowork

# 2. 拉取代码
cd /srv/codingagent/contract-mgmt
git pull origin iteration/0.0.1

# 3. 安装依赖（如需要）
conda activate ~/外部需求/.conda/codingagent
pip install -r requirements.txt

# 4. 初始化数据库（如首次部署）
python scripts/init_db.py

# 5. 重启服务
sudo systemctl restart codingagent-contract-mgmt
```

### systemd 服务配置

服务文件：`/etc/systemd/system/codingagent-contract-mgmt.service`

```
[Unit]
Description=Contract Management System
After=network.target

[Service]
Type=simple
User=codingagent
WorkingDirectory=/srv/codingagent/contract-mgmt
ExecStart=/home/codingagent/外部需求/.conda/codingagent/bin/uvicorn app.main:app --host 127.0.0.1 --port 19050
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Nginx 配置

```
location /projects/contract-mgmt/ {
    proxy_pass http://127.0.0.1:19050;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

---

## 日志查看

```bash
# systemd 日志
sudo journalctl -u codingagent-contract-mgmt -f

# uvicorn 日志（直接运行时）
# 控制台标准输出，包含请求日志和异常堆栈
```

日志级别可通过 `.env` 中的 `LOG_LEVEL` 调整（DEBUG/INFO/WARNING/ERROR）。

---

## 常见故障与恢复

### 1. 端口被占用

```bash
# 查找占用进程
lsof -ti:19050
# 终止进程
kill $(lsof -ti:19050)
```

### 2. 数据库文件权限问题

```bash
# 检查数据库文件
ls -la contract_mgmt.db
# 确保 uvicorn 进程用户有读写权限
chmod 644 contract_mgmt.db
```

### 3. uploads 目录权限问题

```bash
# 创建 uploads 目录
mkdir -p uploads
chmod 755 uploads
```

### 4. 数据库重置

```bash
# 删除旧数据库并重新初始化
rm -f contract_mgmt.db
python scripts/init_db.py
```

### 5. 回滚到精确 Tag

```bash
git checkout <tag>
sudo systemctl restart codingagent-contract-mgmt
```

---

## API 快速参考

```bash
# 登录（保存 session cookie）
curl -c cookies.txt -X POST http://localhost:8000/projects/contract-mgmt/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 获取当前用户
curl -b cookies.txt http://localhost:8000/projects/contract-mgmt/api/auth/me

# 合同列表
curl -b cookies.txt http://localhost:8000/projects/contract-mgmt/api/contracts/

# 创建合同
curl -b cookies.txt -X POST http://localhost:8000/projects/contract-mgmt/api/contracts/ \
  -H "Content-Type: application/json" \
  -d '{"title":"测试合同","contract_no":"HT-001","parties":[{"name":"甲","role":"甲方"},{"name":"乙","role":"乙方"}],"amount":100000}'

# 上传附件
curl -b cookies.txt -X POST http://localhost:8000/projects/contract-mgmt/api/contracts/1/attachments \
  -F "file=@document.pdf;type=application/pdf"

# 状态流转
curl -b cookies.txt -X POST http://localhost:8000/projects/contract-mgmt/api/contracts/1/status \
  -H "Content-Type: application/json" \
  -d '{"status":"pending_review","reason":"请审批"}'

# 健康检查
curl http://localhost:8000/projects/contract-mgmt/healthz
```
