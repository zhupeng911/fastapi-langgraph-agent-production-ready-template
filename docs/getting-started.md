# 快速开始

## 前置条件

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)：`pip install uv`
- Docker + Docker Compose（本地开发推荐）
- OpenAI API 密钥
- Langfuse 账户（可选；设置 `LANGFUSE_TRACING_ENABLED=false` 可跳过）

## 方案 A：Docker（推荐）

这是最快的启动方式.一条命令即可启动 API 和带 pgvector 的 PostgreSQL.

```bash
git clone <repo-url> my-agent
cd my-agent

# 复制并填写环境文件
cp .env.example .env.development
# 必填：OPENAI_API_KEY、JWT_SECRET_KEY
# 可选：LANGFUSE_* 密钥（或设置 LANGFUSE_TRACING_ENABLED=false）

make install       # 安装 Python 依赖和 pre-commit 钩子
make docker-up     # 启动 API（端口 8000）和 PostgreSQL
make docker-migrate # 在 app 容器中运行 Alembic 迁移
```

打开 [http://localhost:8000/docs](http://localhost:8000/docs).

## 方案 B：本地 Python

```bash
git clone <repo-url> my-agent
cd my-agent

cp .env.example .env.development
# 填写：OPENAI_API_KEY、JWT_SECRET_KEY、POSTGRES_*（指向你的数据库）

make install       # 安装依赖和 pre-commit 钩子
make migrate       # 通过 Alembic 创建表
make dev           # 在端口 8000 启动带热重载的服务
```

## 第一个 API 请求

### 1. 注册用户

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "Secret123!", "username": "you"}'  # pragma: allowlist secret
```

返回 `user_id` 和 JWT 令牌.

### 2. 创建会话

```bash
curl -X POST http://localhost:8000/api/v1/auth/session \
  -H "Authorization: Bearer <token from step 1>"
```

返回 `session_id` 和作用域为当前会话的 JWT.

### 3. 聊天

```bash
curl -X POST http://localhost:8000/api/v1/chatbot/chat \
  -H "Authorization: Bearer <session token>" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

也可以使用流式接口获取实时响应：

```bash
curl -X POST http://localhost:8000/api/v1/chatbot/chat/stream \
  -H "Authorization: Bearer <session token>" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

## 自定义 Agent

以下是最常见的修改位置：

| 修改内容 | 位置 |
|---|---|
| Agent 个性与指令 | `app/core/prompts/system.md` |
| 可用工具 | `app/core/langgraph/tools.py` |
| LLM 模型和回退顺序 | `app/services/llm.py` → `LLMRegistry.LLMS` |
| 记忆集合名称 | `.env` 中的 `LONG_TERM_MEMORY_COLLECTION_NAME` |

## 运行 pre-commit 钩子

钩子会在 `git commit` 时自动运行，也可以手动执行：

```bash
make pre-commit
```

钩子包括：行尾空格检查、YAML/TOML/JSON 校验、密钥检测，以及 ruff 检查和格式化.

## 故障排查

**启动时数据库连接错误**

确保 PostgreSQL 正在运行，并且 `.env` 中的 `POSTGRES_*` 配置正确.使用 Docker 时，`make docker-up` 会处理该问题，包括运行迁移.

**`could not translate host name "db"`**

`POSTGRES_HOST=db` 只在 Docker 网络内部有效，因为它是 Compose 服务名称.如果在宿主机上运行命令（例如本地 Python 流程中的 `make migrate` 或 `make dev`），请将 `POSTGRES_HOST` 设置为 `localhost`；数据库端口已通过 `docker-compose.yml` 发布到宿主机.容器内部则保持设置为 `db`.

**`detect-secrets` 阻止提交**

如果确认是误报，请在被标记行末尾添加 `# pragma: allowlist secret`.

**Langfuse 错误**

开发期间可以在 `.env` 中设置 `LANGFUSE_TRACING_ENABLED=false`，完全禁用跟踪.
