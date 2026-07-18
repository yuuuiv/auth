# Neofantasy Live Auth

轻量级、自托管的统一认证服务，为 Neofantasy Live 提供邮箱密码、邮箱验证码、Google 和 GitHub 登录，并签发统一 JWT 会话。

## 功能

| 类别 | 支持项 |
|------|--------|
| OAuth 登录 | Google / GitHub / Microsoft / Web3 |
| 邮箱登录 | SMTP 验证码注册、密码登录、密码重置 |
| 会话安全 | HttpOnly Cookie、Bearer fallback、JWT issuer/audience 校验 |
| 人机验证 | Cloudflare Turnstile |
| 存储 | SQLite / Supabase / Redis / Upstash |
| 部署 | Vercel Serverless / Docker |

## Neofantasy Live 会话接口

站点集成应优先使用这些接口。服务统一创建账号、验证密码并签发带 `iss`/`aud` 的 JWT，同时设置 HttpOnly Cookie。`access_token` 仅用于不能共享子域 Cookie 的开发回退，不应放入 URL。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/session/verify-code` | 校验 Turnstile 并发送注册验证码 |
| `POST` | `/api/session/register` | 使用邮箱、密码和验证码创建账号并登录 |
| `POST` | `/api/session/login` | 邮箱密码登录 |
| `GET` | `/api/session/me` | 获取当前会话用户和角色 |
| `POST` | `/api/session/logout` | 清除会话 Cookie |
| `POST` | `/api/session/oauth-callback` | 完成 Google/GitHub 回调并签发中心会话 |
| `POST` | `/api/session/oauth-exchange` | 兼容旧应用 OAuth code 并换成中心会话 |

生产环境请将 `auth_cookie_domain` 配置为 `.neofantasy.online`，使 `auth.neofantasy.online` 签发的 HttpOnly Cookie 能被 `api.neofantasy.online` 使用。

## OAuth 登录

前端登录页会根据 `GET /api/settings` 返回的 `enabled_google`、`enabled_github` 显示按钮。

Google 和 GitHub OAuth 应用的回调地址分别设置为：

```text
https://auth.neofantasy.online/callback/google
https://auth.neofantasy.online/callback/github
```

仅在后端环境变量中配置：

```dotenv
google_client_id=<Google OAuth client ID>
google_client_secret=<Google OAuth client secret>
github_client_id=<GitHub OAuth client ID>
github_client_secret=<GitHub OAuth client secret>
```

站内回调会调用 `/api/session/oauth-callback`，由 Auth 服务取得提供商用户信息、创建或关联中心账号，然后签发 `nf_session`。client secret 不会进入浏览器，也不要求 Neofantasy Live 使用旧的 `app_settings` 才能登录。

## 旧应用 OAuth 接口

旧的多租户应用接口仍保留：

- `GET /api/login?login_type=github|google&redirect_url=...`：获取第三方登录跳转地址。
- `POST /api/oauth`：处理第三方回调并返回临时授权码。
- `POST /api/token`：使用服务端保存的 `app_secret` 将授权码换成 JWT。

旧应用的 `app_secret` 只能存储在后端，不能放进浏览器或前端代码中。

## 配置参考

```dotenv
# 基础
debug=false
cors_allow_origins=http://localhost:5173,https://live.neofantasy.online

# 数据库
enabled_db=true
db_client_type=supabase_rest
supabase_api_url=https://<project>.supabase.co
supabase_api_key=<Supabase service_role key>

# 缓存
cache_client_type=upstash
upstash_api_url=<Upstash REST URL>
upstash_api_token=<Upstash REST token>

# SMTP
enabled_smtp=true
smtp_url=smtps://<username>:<password>@<smtp-host>:465
verify_code_expire_seconds=300
email_rate_limit_timewindow_seconds=60
email_rate_limit_max_requests=60

# Turnstile（可选）
cf_turnstile_site_key=<可选>
cf_turnstile_secret_key=<可选>

# OAuth（可选）
google_client_id=<可选>
google_client_secret=<可选>
github_client_id=<可选>
github_client_secret=<可选>

# Neofantasy Live 中心会话
auth_jwt_secret=<与 neofantasy-api 完全相同的随机长密钥>
auth_token_expire_days=7
auth_cookie_name=nf_session
auth_cookie_domain=.neofantasy.online
auth_issuer=neofantasy-auth
auth_audience=neofantasy
admin_emails=<管理员邮箱，多个邮箱用逗号分隔>
```

所有 service key、SMTP 密码、OAuth secret 和 JWT secret 都必须配置在部署平台的环境变量中，不能提交到仓库。若凭据曾经出现在公开日志、文档或 Git 历史中，应立即轮换。

## 本地运行

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

前端：

```bash
cd frontend
pnpm install
pnpm dev
```

## 部署

Vercel 部署时，将 `main.py` 作为 Python Serverless Function，并将 `frontend/` 构建为 Vite 静态资源。完整的 NeoFantasy Live、Supabase、权限审核和域名配置步骤见仓库根目录的 `DEPLOYMENT_GUIDE.md`。

## 相关接口

旧版兼容接口仍包括：

- `GET /api/settings`
- `GET /api/health_check`
- `GET /api/info`
- `POST /api/email/login`
- `POST /api/email/verify_code`
- `POST /api/email/register`

临时邮箱桥接接口仍以 `/api/temp-mail/*` 提供，但它与 Neofantasy Live 的中心会话和播放权限是两个独立功能。
