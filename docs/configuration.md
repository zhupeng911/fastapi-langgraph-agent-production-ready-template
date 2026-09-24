# 配置

所有配置都来自环境变量.使用 `.env.development`、`.env.staging` 或 `.env.production`，应用会根据 `APP_ENV` 变量加载对应文件.

复制 `.env.example` 开始配置：

```bash
cp .env.example .env.development
```

---

## 应用配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_ENV` | `development` | 运行环境：`development`、`staging`、`production`、`test` |
| `PROJECT_NAME` | `FastAPI LangGraph Template` | 在 API 文档和日志中显示的项目名称 |
| `VERSION` | `1.0.0` | API 版本 |
| `DEBUG` | `false` | 启用调试日志和性能分析中间件 |
| `API_V1_STR` | `/api/v1` | API 前缀 |
| `ALLOWED_ORIGINS` | `*` | 以逗号分隔的 CORS 来源列表 |

---

## LLM 配置

| 变量 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | — | 是 | OpenAI API 密钥 |
| `DEFAULT_LLM_MODEL` | `gpt-5-mini` | 否 | 初始模型，回退顺序参见 [LLM 服务](llm-service.md) |
| `DEFAULT_LLM_TEMPERATURE` | `0.2` | 否 | 聊天补全的 temperature |
| `MAX_TOKENS` | `2000` | 否 | 每次 LLM 响应的最大令牌数 |
| `MAX_LLM_CALL_RETRIES` | `3` | 否 | 每个模型切换到回退模型前的重试次数 |
| `LLM_TOTAL_TIMEOUT` | `60` | 否 | 整个回退循环的最大耗时，单位为秒 |
| `SESSION_NAMING_ENABLED` | `true` | 否 | 是否使用 LLM 后台任务，根据用户第一条消息自动生成会话标题 |

---

## 长期记忆

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LONG_TERM_MEMORY_COLLECTION_NAME` | `longterm_memory` | pgvector 集合名称 |
| `LONG_TERM_MEMORY_MODEL` | `gpt-5-nano` | mem0 用于提取记忆的 LLM |
| `LONG_TERM_MEMORY_EMBEDDER_MODEL` | `text-embedding-3-small` | 用于语义搜索的嵌入模型 |

---

## 数据库

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `POSTGRES_HOST` | `localhost` | PostgreSQL 主机 |
| `POSTGRES_PORT` | `5432` | PostgreSQL 端口 |
| `POSTGRES_DB` | `food_order_db` | 数据库名称 |
| `POSTGRES_USER` | `postgres` | 数据库用户 |
| `POSTGRES_PASSWORD` | `postgres` | 数据库密码 |
| `POSTGRES_POOL_SIZE` | `20` | SQLAlchemy 连接池大小 |
| `POSTGRES_MAX_OVERFLOW` | `10` | 超出连接池大小的最大溢出连接数 |

---

## 认证

| 变量 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `JWT_SECRET_KEY` | — | 是 | 用于签名 JWT 的密钥，生产环境应使用长度足够长的随机字符串 |
| `JWT_ALGORITHM` | `HS256` | 否 | JWT 签名算法 |
| `JWT_ACCESS_TOKEN_EXPIRE_DAYS` | `30` | 否 | 令牌有效期，单位为天 |

---

## 缓存（Valkey/Redis，可选）

设置 `VALKEY_HOST` 后，应用会使用 Valkey/Redis 进行记忆搜索缓存和限流.未设置时回退到内存 TTL 缓存，该缓存不会在多个实例之间共享.

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VALKEY_HOST` | ``（禁用） | Valkey/Redis 主机，留空则使用内存回退 |
| `VALKEY_PORT` | `6379` | 端口 |
| `VALKEY_DB` | `0` | 数据库索引 |
| `VALKEY_PASSWORD` | `` | 密码（需要时设置） |
| `VALKEY_MAX_CONNECTIONS` | `20` | 连接池大小 |
| `CACHE_TTL_SECONDS` | `60` | 记忆搜索结果的缓存 TTL |

---

## 可观测性（Langfuse）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LANGFUSE_TRACING_ENABLED` | `true` | 设置为 `false` 可完全禁用跟踪 |
| `LANGFUSE_PUBLIC_KEY` | — | Langfuse 项目公钥 |
| `LANGFUSE_SECRET_KEY` | — | Langfuse 项目私钥 |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Langfuse 地址，可使用自托管或云端地址 |

---

## 限流

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `RATE_LIMIT_DEFAULT` | `200 per day, 50 per hour` | 回退限制 |
| `RATE_LIMIT_CHAT` | `30 per minute` | POST /chat |
| `RATE_LIMIT_CHAT_STREAM` | `20 per minute` | POST /chat/stream |
| `RATE_LIMIT_MESSAGES` | `50 per minute` | GET/DELETE /messages |
| `RATE_LIMIT_LOGIN` | `20 per minute` | POST /auth/login |
| `RATE_LIMIT_REGISTER` | `10 per hour` | POST /auth/register |

配置 Valkey 后，限流状态会在所有应用实例之间共享；未配置时，限流仅在当前进程内生效.

---

## 性能分析（仅调试模式）

仅在 `DEBUG=true` 时启用.系统会分析每个请求，并在请求耗时超过阈值时保存 JSON 报告.

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `PROFILING_DIR` | `/tmp/fastapi_profiles` | 性能分析 JSON 文件目录 |
| `PROFILING_THRESHOLD_SECONDS` | `2.0` | 触发保存报告的最小耗时，设置为 `0` 可分析每个请求 |

---

## 日志

| 变量 | 默认值（开发） | 默认值（生产） | 说明 |
| --- | --- | --- | --- |
| `LOG_LEVEL` | `DEBUG` | `WARNING` | 日志级别 |
| `LOG_FORMAT` | `console` | `json` | `console` 表示彩色开发日志，`json` 表示结构化生产日志 |
