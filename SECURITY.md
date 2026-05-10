# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Current |

## Reporting a Vulnerability

If you discover a security vulnerability in AgentForge-AI, please report it responsibly.

### How to Report

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Email the maintainer directly at the email listed on the [GitHub profile](https://github.com/OmRajput17)
3. Include a detailed description of the vulnerability
4. Include steps to reproduce (if applicable)

### What to Expect

- **Acknowledgment** within 48 hours
- **Assessment** within 1 week
- **Fix** released as a patch version

## Security Best Practices

When using AgentForge-AI:

### API Keys

- **Never** commit API keys to version control
- Store all secrets in `~/.agentforge/config.yml` (excluded from repos by default)
- Use environment variables or secret managers in production
- Rotate API keys regularly

### GitHub Tokens

- Use **fine-grained** Personal Access Tokens with minimal required scopes
- Required scopes for full functionality:
  - `repo` — Issue read/write, label management
  - `read:user` — User activity feed

### Slack Tokens

- Use a **bot token** (starts with `xoxb-`) rather than user tokens
- Required scopes: `chat:write`, `channels:read`

### Notion Tokens

- Create a dedicated **integration** for AgentForge
- Only share the specific pages the integration needs access to

### Auto-Approve Mode

- The `auto_approve: true` setting bypasses all approval gates
- **Only use in trusted, automated environments** (CI/CD pipelines with controlled inputs)
- Keep `auto_approve: false` (default) for interactive use

## Dependency Security

AgentForge-AI uses well-maintained dependencies:

| Dependency | Security Notes |
|-----------|----------------|
| `httpx` | TLS-verified HTTPS by default |
| `pydantic` | Input validation and sanitization |
| `tenacity` | Prevents unbounded retries |
| `langchain` | Follows LangChain security guidelines |

We recommend running `pip audit` periodically to check for known vulnerabilities in dependencies.
