# 安全策略

## 支持的版本

这是一个模板仓库。安全修复会应用到 `master` 分支。Fork 维护者负责及时更新自己的 Fork。

## 报告漏洞

对于安全漏洞，**请不要**公开创建 GitHub Issue。

请通过 [GitHub Security Advisories](../../security/advisories/new) 私下报告，或直接通过电子邮件联系维护者。报告中请包含：

- 漏洞描述及其潜在影响
- 漏洞复现步骤
- 建议采取的缓解措施

我们将在 48 小时内确认收到报告；对于已确认的漏洞，将在 7 天内提供修复方案或缓解计划。

## 使用此模板时的安全注意事项

**部署到生产环境前：**

- 设置强随机性的 `JWT_SECRET_KEY`（长度至少 32 个字符）
- 轮换所有密钥——不要使用 `.env.example` 中的值
- 设置 `DEBUG=false`
- 将 `ALLOWED_ORIGINS` 限制为实际的前端域名
- 如果不希望将对话数据发送到 Langfuse，请设置 `LANGFUSE_TRACING_ENABLED=false`
- 使用按环境区分的 `.env` 文件——绝不要将密钥提交到 git

**模板内置的安全措施：**

- 使用 bcrypt 对密码进行哈希处理（绝不以明文存储）
- JWT 令牌包含用于保证唯一性的 `jti` 声明
- 所有用户输入在使用前都会经过清理
- 对身份认证和聊天接口进行限流
- 通过 `detect-secrets` pre-commit hook 检测密钥
- 已配置 CORS（生产环境中应限制 `ALLOWED_ORIGINS`）
