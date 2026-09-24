# FastAPI LangGraph Agent 模板

一个用于使用 FastAPI 和 LangGraph 构建 AI Agent 后端的生产级模板。它处理有状态对话、长期记忆、工具调用、可观测性、限流和身份认证等复杂部分，让你可以专注于 Agent 逻辑。

**面向需要可靠基础设施的 AI 工程师**，而不是一个教程项目。

---

## 由 Atlas Cloud 驱动——可直接替换的 LangGraph Agent LLM 后端

<div align="center">
  <a href="https://www.atlascloud.ai/?utm_source=github&utm_medium=link&utm_campaign=fastapi-langgraph-agent-production-ready-template">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/atlas-cloud-logo-dark.png"/>
      <img src="docs/atlas-cloud-logo.png" alt="Atlas Cloud" width="200"/>
    </picture>
  </a>
</div>

[**Atlas Cloud**](https://www.atlascloud.ai/?utm_source=github&utm_medium=link&utm_campaign=fastapi-langgraph-agent-production-ready-template) 提供与 **OpenAI 兼容的 LLM API**，可以无缝集成到这个 FastAPI + LangGraph 模板中，无需修改 Agent 图代码。只需替换 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY`，即可通过统一端点使用 **DeepSeek、Qwen、GLM、Kimi、MiniMax、Gemini、Claude、GPT** 等模型。

此模板中的 `LLMRegistry` 使用 `langchain_openai.ChatOpenAI`；Atlas Cloud 在接口层面兼容，因此无需改动任何 LangGraph 逻辑，即可立即访问 130 多个精选模型。

### 快速配置

**步骤 1——获取免费的 API 密钥：** [atlascloud.ai/console/coding-plan](https://www.atlascloud.ai/console/coding-plan)

**步骤 2——更新 `.env.development`：**

```env
OPENAI_API_KEY=<your-atlascloud-key>
OPENAI_BASE_URL=https://api.atlascloud.ai/v1
DEFAULT_LLM_MODEL=deepseek-ai/deepseek-v4-pro
```

**步骤 3——或者直接在代码中使用：**

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="deepseek-ai/deepseek-v4-pro",
    openai_api_base="https://api.atlascloud.ai/v1",
    openai_api_key="<your-atlascloud-key>",
    max_tokens=512,  # reasoning model requires max_tokens >= 512
)
```

在 LangGraph Agent 中所有使用 `ChatOpenAI` 的位置都可以直接替换使用，包括 `LLMRegistry`、循环回退服务和 mem0 长期记忆。

<details>
<summary>📋 模型目录——当前精选模型（共 136 个可用模型）</summary>

| Model ID | Provider |
|---|---|
| `openai/gpt-5.6-luna` | OpenAI |
| `openai/gpt-5.6-sol` | OpenAI |
| `openai/gpt-5.6-terra` | OpenAI |
| `openai/gpt-5.5` | OpenAI |
| `openai/gpt-5.4` | OpenAI |
| `openai/gpt-5.4-mini` | OpenAI |
| `openai/gpt-5.4-nano` | OpenAI |
| `openai/gpt-5.3-codex` | OpenAI |
| `openai/gpt-5.2` | OpenAI |
| `anthropic/claude-opus-5` | Anthropic |
| `anthropic/claude-sonnet-5` | Anthropic |
| `anthropic/claude-opus-4.8` | Anthropic |
| `anthropic/claude-sonnet-4.6` | Anthropic |
| `anthropic/claude-haiku-4.5-20251001` | Anthropic |
| `google/gemini-3.5-flash` | Google |
| `google/gemini-3.1-pro-preview` | Google |
| `google/gemini-3.1-flash-lite` | Google |
| `google/gemini-2.5-pro` | Google |
| `deepseek-ai/deepseek-v4-pro` | DeepSeek |
| `deepseek-ai/deepseek-v4-flash` | DeepSeek |
| `qwen/qwen3.8-max` | Alibaba Qwen |
| `qwen/qwen3.7-plus` | Alibaba Qwen |
| `qwen/qwen3.5-plus` | Alibaba Qwen |
| `moonshotai/kimi-k3` | Moonshot AI |
| `moonshotai/kimi-k2.7-code` | Moonshot AI |
| `zai-org/glm-5.2` | Zhipu AI |
| `zai-org/glm-5.1` | Zhipu AI |
| `zai-org/glm-5` | Zhipu AI |
| `minimaxai/minimax-m3` | MiniMax |
| `minimaxai/minimax-m2.7` | MiniMax |
| `xai/grok-4.6` | xAI |
| `xai/grok-4.5` | xAI |
| `bytedance/doubao-seed-2.1-pro-260628` | ByteDance |
| `xiaomi/mimo-v2.5-pro` | Xiaomi |
| `tencent/hy3` | Tencent |

[查看实时模型列表 →](https://www.atlascloud.ai/?utm_source=github&utm_medium=link&utm_campaign=fastapi-langgraph-agent-production-ready-template)

</details>

---

## 功能概览

- **LangGraph** 有状态 Agent，支持检查点、工具调用和人在回路
- 通过 mem0 + pgvector 实现的**长期记忆**——按用户进行语义搜索，并由缓存提供支持
- **LLM 服务**支持循环模型回退、指数退避重试和总超时预算
- 所有 LLM 调用均支持 **Langfuse** 追踪；提供 Prometheus 指标和 Grafana 仪表板
- 支持带会话管理的 **JWT 身份认证**；通过 slowapi 实现限流
- 支持 **Alembic** 数据库迁移；可选 Valkey/Redis 缓存层
- 每行日志都包含请求、会话和用户上下文的**结构化日志**

## 快速开始

```bash
git clone <repo-url> my-agent && cd my-agent
cp .env.example .env.development   # fill in your keys
make install
make docker-up                     # starts API + PostgreSQL
```

打开 [http://localhost:8000/docs](http://localhost:8000/docs) 查看交互式 API 文档。

> 如需在不使用 Docker 的情况下进行本地开发，请参阅 [docs/getting-started.md](docs/getting-started.md)。

## 文档

| 指南 | 内容 |
|---|---|
| [快速开始](docs/getting-started.md) | 前置条件、本地配置、首次 API 调用 |
| [架构](docs/architecture.md) | 系统设计、请求流程、组件图 |
| [配置](docs/configuration.md) | 所有带默认值的环境变量 |
| [身份认证](docs/authentication.md) | JWT 流程、会话、接口参考 |
| [数据库与迁移](docs/database.md) | 数据库结构、Alembic 迁移、pgvector |
| [LLM 服务](docs/llm-service.md) | 模型、重试、回退、超时预算 |
| [记忆](docs/memory.md) | mem0 长期记忆、缓存层 |
| [可观测性](docs/observability.md) | Langfuse、结构化日志、Prometheus、性能分析 |
| [评估](docs/evaluation.md) | 评估框架、自定义指标、报告 |
| [Docker](docs/docker.md) | Docker、Compose、完整监控栈 |

## 项目结构

```
app/
  api/v1/          # Route handlers
  core/
    langgraph/     # Agent graph + tools
    prompts/       # System prompt template
    cache.py       # Valkey/Redis + in-memory fallback
    config.py      # Settings
    middleware.py  # Metrics, logging context, profiling
    limiter.py     # Rate limiting
  models/          # SQLModel ORM models
  schemas/         # Pydantic request/response schemas
  services/        # LLM, database, memory services
alembic/           # Database migrations
evals/             # LLM evaluation framework
```

## 贡献

欢迎提交 PR。请先阅读 [docs/getting-started.md](docs/getting-started.md) 配置开发环境，然后遵循 [AGENTS.md](AGENTS.md) 中的编码规范。

请私下报告安全问题，详见 [SECURITY.md](SECURITY.md)。

## 许可证

详见 [LICENSE](LICENSE)。

## 常见问题

### 通用问题

**这个模板是什么？**
这是一个基于 FastAPI + LangGraph 构建的 AI Agent 后端生产级基础模板。它集成了通常需要手动组装的组件，包括有状态对话、长期记忆、工具调用、可观测性、限流和 JWT 身份认证。

**它与基础 LangGraph 配置有什么不同？**
基础 LangGraph 快速入门只实现了“Agent 在本地运行”。此模板额外提供 Alembic 迁移、mem0 + pgvector 长期记忆、Langfuse 追踪、Prometheus + Grafana 仪表板、JWT 会话、slowapi 限流、带请求级上下文的结构化日志，以及循环回退 LLM 服务，涵盖了通常需要单独构建的生产环境能力。

### 安装与配置

**必须使用 Docker 吗？**
推荐使用，但不是必须的。`make docker-up` 会同时启动 API 和 PostgreSQL。仅进行本地配置时，请参阅 [docs/getting-started.md](docs/getting-started.md)。

**支持哪些 LLM 提供商？**
目前通过 `app/services/llm/registry.py` 中的 `LLMRegistry` 仅支持 **OpenAI**。计划通过 LangChain 的 `init_chat_model` 支持多提供商（Anthropic、Google、OpenRouter），详见 [#51](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template/issues/51)。请通过 `.env.development` 中的 `DEFAULT_LLM_MODEL` 配置模型。

**如何配置长期记忆？**
长期记忆采用自托管方式：mem0 在进程内运行，并通过 pgvector 持久化到现有 PostgreSQL 中，不需要单独的 mem0 云账号或 API 密钥。你只需要一个可用的 `OPENAI_API_KEY`（用于事实提取和向量嵌入），并启用 pgvector 扩展。详情请参阅 [docs/memory.md](docs/memory.md)。

### 开发

**如何添加自定义工具？**
在 `app/core/langgraph/tools/` 中添加一个使用 LangChain `@tool` 装饰的函数，并将其注册到该包导出的 `tools` 列表中。Agent 下次启动时会自动加载，无需修改图结构。

**LLM 服务如何处理故障？**
分为两层：(1) 通过 `tenacity` 实现每次调用的指数退避重试；(2) **循环回退**——如果当前模型耗尽重试次数，服务会切换到 `LLMRegistry` 中的下一个模型并继续处理。总超时预算会限制整个调用的耗时，从而控制延迟。详见 [docs/llm-service.md](docs/llm-service.md)。

**不使用 Langfuse 可以吗？**
可以。将 `LANGFUSE_TRACING_ENABLED=false`（或不配置 Langfuse 相关密钥）即可。Agent 无需修改即可运行，结构化日志仍会记录请求、会话和用户上下文。

### 故障排查

**API 无法启动**
- 确认 PostgreSQL 正在运行（`make docker-up` 会与 API 一起启动 PostgreSQL）
- 确认 `.env.development` 存在——从 `.env.example` 复制并填写必需的配置项
- 执行迁移：`make migrate`

**记忆或语义搜索没有返回结果**
- 确认 PostgreSQL 实例已启用 `pgvector` 扩展
- 确认 `OPENAI_API_KEY` 有效（mem0 会调用 OpenAI 进行事实提取和向量嵌入）
- 检查 `.env.development` 中是否设置了 `LONG_TERM_MEMORY_MODEL` 和 `LONG_TERM_MEMORY_EMBEDDER_MODEL`

**限流过于严格**
限制定义在 `app/core/limiter.py`（slowapi）中。可以在该文件中调整各路由装饰器或默认限流值。相关环境变量请参阅 [docs/configuration.md](docs/configuration.md)。
