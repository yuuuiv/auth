# Auth(-live)

🔐 轻量级、自托管的统一认证网关。一行配置即可为你的任意应用接入 **GitHub / Google / Microsoft / Web3 钱包 / 邮箱验证码** 等多种登录方式，返回标准 JWT，开箱即用。

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/yuuuiv/auth)

---

## 目录

- [功能特性](#功能特性)
- [认证流程](#认证流程)
- [快速开始](#快速开始)
  - [接入你的应用](#接入你的应用)
  - [前端路由](#前端路由)
- [API 文档](#api-文档)
  - [认证接口](#认证接口)
  - [邮箱接口](#邮箱接口)
  - [用户接口](#用户接口)
  - [临时邮箱桥接接口](#临时邮箱桥接接口)
  - [系统接口](#系统接口)
- [部署](#部署)
  - [Vercel 部署](#vercel-部署)
  - [Docker 部署](#docker-部署)
- [配置参考](#配置参考)
- [技术栈](#技术栈)
- [致谢](#致谢)

---

## 功能特性

| 类别 | 支持项 |
|------|--------|
| 🔗 **OAuth 登录** | GitHub / Google / Microsoft / Web3 (MetaMask) |
| ✉️ **邮箱登录** | SMTP 验证码注册 & 登录，支持密码重置 |
| 🛡️ **人机验证** | Cloudflare Turnstile |
| 🔑 **Token 交换** | OAuth Code → JWT，支持多 App 租户隔离 |
| 💾 **多后端存储** | SQLite / Supabase / Redis / Upstash KV / 内存缓存 |
| 📮 **临时邮箱桥接** | 统一账户同步到 Temp Mail Worker，代理邮箱管理 |
| 🌗 **前端主题** | 亮色 / 暗色主题自适应 |
| 🚀 **部署方式** | Vercel Serverless / Docker Compose 一键部署 |

---

## 认证流程

```mermaid
sequenceDiagram
    participant User
    participant ClientApp as 你的应用
    participant AwslAuth as Awsl Auth
    participant Provider as 登录提供商

    User->>ClientApp: 点击登录
    ClientApp->>AwslAuth: 重定向到 Awsl Auth 登录页
    User->>AwslAuth: 选择登录方式
    AwslAuth->>Provider: 重定向到提供商登录页
    User->>Provider: 完成登录授权
    Provider->>AwslAuth: 回调返回授权码
    AwslAuth->>Provider: 换取用户信息
    AwslAuth->>ClientApp: 重定向回你的应用 (携带 code)
    ClientApp->>AwslAuth: POST /api/token 用 code 换 JWT
    AwslAuth->>ClientApp: 校验 code 并返回 JWT
    ClientApp->>User: 登录成功
```

---

## 快速开始

### 接入你的应用

1. 在 `.env` 或环境变量中配置 `app_id`、`app_secret`、`redirect_url`。

2. 将用户重定向到 Awsl Auth 登录页：

   ```
   https://your-auth-domain.com/login?app_id=你的app_id
   ```

3. 用户完成登录后，会被重定向回你的 `redirect_url`，并携带 `code` 参数：

   ```
   https://your-app.com/callback?code=<authorization_code>
   ```

4. 后端用 `code` 换取 JWT：

   ```js
   const { jwt } = await fetch("https://your-auth-domain.com/api/token", {
       method: "POST",
       headers: { "Content-Type": "application/json" },
       body: JSON.stringify({
           app_id: "demo",
           app_secret: "demo_secret",
           code: code,
       })
   }).then(res => res.json());
   ```

5. 使用 JWT：

   - 不要把 `app_secret` 放进浏览器，也不要在浏览器自行解码或验证 JWT。
   - 携带 JWT 请求用户信息接口：

   ```js
   const user = await fetch(`/api/info?app_id=${app_id}`, {
       headers: {
           'Authorization': `Bearer ${jwt}`,
           'Content-Type': 'application/json',
       }
   }).then(res => res.json());
   ```

### 前端路由

内置前端页面路由：

| 路由 | 说明 |
|------|------|
| `/login` | 登录页（默认首页），展示邮箱登录 + OAuth 按钮 |
| `/register` | 邮箱注册页（验证码 + Turnstile 人机验证） |
| `/reset_pass` | 密码重置页 |
| `/callback/:loginType` | OAuth 回调处理页 |
| `/user` | 登录后用户信息页 |
| `/demo` | 兼容旧版 `/demo` 路由 |

---

## API 文档

### 认证接口

#### `GET /api/settings`

获取当前启用的登录方式及配置。

**响应：**

```json
{
    "enabled_smtp": true,
    "enabled_github": true,
    "enabled_google": false,
    "enabled_ms": false,
    "enabled_web3": true,
    "cf_turnstile_site_key": "1x00000000000000000000AA",
    "temp_mail_bridge_enabled": true
}
```

#### `GET /api/login`

获取第三方登录跳转 URL。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `login_type` | `string` | 登录类型：`github` / `google` / `ms` / `web3` |
| `redirect_url` | `string` | 可选，OAuth 完成后的回调地址 |

#### `POST /api/oauth`

OAuth / Web3 回调处理，返回临时授权码。

**请求体：**

```json
{
    "app_id": "demo",
    "login_type": "github",
    "code": "github_oauth_code",
    "redirect_url": "https://myapp.com/callback"
}
```

**响应：**

```json
{
    "redirect_url": "https://myapp.com/callback",
    "code": "临时授权码"
}
```

#### `POST /api/token`

用临时授权码换取 JWT。

**请求体：**

```json
{
    "app_id": "demo",
    "app_secret": "demo_secret",
    "code": "临时授权码"
}
```

**响应：**

```json
{
    "jwt": "eyJhbGciOiJIUzI1NiIs..."
}
```

---

### 邮箱接口

#### `POST /api/email/login`

邮箱密码登录。

**请求体：**

```json
{
    "email": "user@example.com",
    "password": "your_password"
}
```

#### `POST /api/email/verify_code`

发送邮箱验证码（需先通过 Turnstile 人机验证）。

**请求体：**

```json
{
    "email": "user@example.com",
    "cf_token": "turnstile_token"
}
```

#### `POST /api/email/register`

验证码注册 / 重置密码。

**请求体：**

```json
{
    "email": "user@example.com",
    "password": "your_password",
    "code": "123456"
}
```

---

### 用户接口

#### `GET /api/info`

通过 JWT 获取当前用户信息（需 `Authorization: Bearer <jwt>` 请求头）。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `app_id` | `string` | App ID |

**响应：**

```json
{
    "login_type": "github",
    "user_name": "octocat",
    "user_email": "octocat@github.com",
    "web3_account": null,
    "expire_at": 1720000000.0
}
```

---

### 临时邮箱桥接接口

> 需要配置 `temp_mail_api_base` 和 `temp_mail_admin_auth` 环境变量。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/temp-mail/sync_user` | 同步当前用户到 Temp Mail Worker |
| `GET` | `/api/temp-mail/addresses` | 获取绑定邮箱列表 |
| `POST` | `/api/temp-mail/addresses` | 创建绑定邮箱 |
| `DELETE` | `/api/temp-mail/addresses` | 删除绑定邮箱 |
| `GET` | `/api/temp-mail/mails` | 获取邮箱邮件列表 |
| `GET` | `/api/temp-mail/sendbox` | 获取发件箱列表 |
| `GET` | `/api/temp-mail/addresses/jwt` | 获取邮箱 JWT |
| `POST` | `/api/temp-mail/addresses/bind_jwt` | 绑定已验证邮箱 JWT |
| `GET` | `/api/temp-mail/addresses/forwarding_rules` | 获取转发规则 |
| `POST` | `/api/temp-mail/addresses/forwarding_rules` | 保存转发规则 |

> 以上接口均需携带 `Authorization: Bearer <jwt>` 及 `app_id` 查询参数。

---

### 系统接口

#### `GET /api/health_check`

健康检查端点，返回 `200 OK`。

### NeoFantasy 会话接口

站点集成应优先使用以下接口。它们由 Auth 统一创建账号、验证密码并签发带 `iss`/`aud` 的 JWT，同时设置 HttpOnly Cookie；`access_token` 仅用于不能共享子域 Cookie 的开发回退，不应放入 URL。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/session/verify-code` | 校验 Turnstile 并发送注册验证码 |
| `POST` | `/api/session/register` | 使用邮箱、密码和验证码创建账号并登录 |
| `POST` | `/api/session/login` | 邮箱密码登录 |
| `GET` | `/api/session/me` | 获取当前会话用户和角色 |
| `POST` | `/api/session/logout` | 清除会话 Cookie |
| `POST` | `/api/session/oauth-exchange` | 将现有 OAuth provider code 换成中心会话 |

生产环境请将 `auth_cookie_domain` 配置为 `.neofantasy.online`，使 `auth.neofantasy.online` 签发的 HttpOnly Cookie 能被 `api.neofantasy.online` 使用。

---

## 部署

### Vercel 部署

点击上方 **Deploy with Vercel** 按钮一键部署，或手动配置：

项目结构使用 Vercel 多构建：

- `main.py` → Python Serverless Function（处理 `/api/*`）
- `frontend/` → Static Build（Vite + React）

**环境变量配置：** 参见下方 [配置参考](#配置参考)。

### Docker 部署

```bash
git clone https://github.com/yuuuiv/auth.git
cd auth
# 编辑环境变量（可选，也可直接在 docker-compose.yml 中修改）
cp .env.example .env
docker compose up -d
```

服务默认监听 `http://localhost:8000`。

`docker-compose.yml` 已内置 Redis 依赖，无需额外配置。

---

## 配置参考

### 完整环境变量列表

```dotenv
# ========== 调试模式 ==========
debug=false

# ========== CORS ==========
cors_allow_origins=http://localhost:5173,https://你的前端域名

# ========== 数据库 (可选) ==========
enabled_db=false
db_client_type=supabase_rest          # 可选: sqlite3 / supabase_rest
supabase_api_url=
supabase_api_key=                     # 推荐使用 service_role key
sqlite_db_url=sqlite:///db.sqlite3

# ========== 缓存客户端 ==========
cache_client_type=upstash             # 可选: memory / redis / upstash
redis_url=redis://localhost:6379/0
upstash_api_url=
upstash_api_token=

# ========== 临时邮箱桥接 (可选) ==========
temp_mail_api_base=https://你的-temp-mail-worker
temp_mail_admin_auth=                 # Worker 管理员密码，仅放后端
temp_mail_user_max_address_count=50   # 统一账户默认可绑定邮箱上限；更高值可由管理员在控制台调整
temp_mail_account_send_balance=10     # 临时邮箱首次绑定统一账户时设置的发信额度

# ========== SMTP 邮箱服务 ==========
enabled_smtp=false
smtp_url=smtps://username:passwd@smtp.example.com:465   # 隐式 SSL（推荐）
# smtp_url=smtp://username:passwd@smtp.example.com:587  # STARTTLS
verify_code_expire_seconds=120
email_rate_limit_timewindow_seconds=60
email_rate_limit_max_requests=60

# ========== Cloudflare Turnstile ==========
cf_turnstile_site_key=
cf_turnstile_secret_key=

# ========== OAuth 第三方登录 ==========
github_client_id=
github_client_secret=
google_client_id=
google_client_secret=
ms_client_id=
ms_client_secret=
enabled_web3_client=true

# ========== App 多租户配置 ==========
app_settings__0__app_id=demo
app_settings__0__app_secret=demo_secret
app_settings__0__redirect_url=
app_settings__0__token_expire_days=30

app_settings__1__app_id=app2
app_settings__1__app_secret=app_secret2
app_settings__1__redirect_url=http://localhost:5000/callback
app_settings__1__token_expire_days=30
```

### 缓存客户端选择

| 客户端 | 适用场景 |
|--------|----------|
| `memory` | 本地开发 / 单实例测试 |
| `redis` | Docker 部署 / 多实例生产环境 |
| `upstash` | Vercel Serverless（无状态，推荐） |

### 数据库客户端选择

| 客户端 | 适用场景 |
|--------|----------|
| `sqlite3` | Docker 单机部署，数据持久化到本地卷 |
| `supabase_rest` | Vercel / 云端部署，使用 Supabase REST API |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI (Python 3) |
| **前端框架** | React 19 + TypeScript + Vite |
| **UI 组件** | shadcn/ui + Tailwind CSS |
| **认证** | PyJWT (HS256) |
| **数据库** | SQLAlchemy (SQLite) / Supabase REST |
| **缓存** | Redis / Upstash KV / 内存 |
| **部署** | Vercel Serverless / Docker |

---

## 致谢

本项目基于 [dreamhunter2333/awsl-auth](https://github.com/dreamhunter2333/awsl-auth) 二次开发
