# Configuration Guide

Complete guide to configuring AgentForge-AI for your environment.

## Quick Setup

```bash
# Generate default config
agentforge init

# Edit the config file
notepad %USERPROFILE%\.agentforge\config.yml     # Windows
nano ~/.agentforge/config.yml                     # macOS / Linux
```

## Full Configuration File

```yaml
# ── LLM Provider ────────────────────────────────────────
llm:
  provider: groq                    # 'openai' or 'groq'
  model: llama-3.3-70b-versatile    # model name for your provider
  api_key: ''                       # your API key

# ── MCP Server Connections ──────────────────────────────
mcp_servers:
  github_token: ''                  # GitHub PAT (required)
  github_owner: ''                  # GitHub username
  github_repo: ''                   # target repository
  notion_token: ''                  # Notion integration secret (optional)
  notion_page_id: ''                # Notion page ID for reports (optional)
  slack_token: ''                   # Slack bot token (optional)
  slack_channel: general            # Slack channel for alerts

# ── Behavior ────────────────────────────────────────────
auto_approve: false                 # skip approval prompts
confidence_threshold: 0.8           # min confidence for agent routing
max_iterations: 10                  # max subtasks per run
standup_lookback_hours: 24          # GitHub activity lookback window
```

---

## LLM Provider Setup

### Option A: Groq (Free Tier Available)

1. Sign up at [console.groq.com](https://console.groq.com/)
2. Create an API key
3. Configure:

```yaml
llm:
  provider: groq
  model: llama-3.3-70b-versatile    # fast, free tier
  api_key: 'gsk_...'
```

**Available Groq models:** `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768`

### Option B: OpenAI

1. Get an API key from [platform.openai.com](https://platform.openai.com/)
2. Configure:

```yaml
llm:
  provider: openai
  model: gpt-4o                     # or gpt-4o-mini for lower cost
  api_key: 'sk-...'
```

**Available OpenAI models:** `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`

> **Note:** The API key for OpenAI can also be set via the `OPENAI_API_KEY` environment variable (LangChain default behavior).

---

## GitHub Setup

A GitHub Personal Access Token is **required** for all agent workflows.

### Create a Token

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **"Generate new token (fine-grained)"**
3. Select the target repository
4. Grant permissions:
   - **Issues**: Read and Write
   - **Metadata**: Read-only
5. Copy the token

### Configure

```yaml
mcp_servers:
  github_token: 'github_pat_...'
  github_owner: 'YourUsername'       # or organization name
  github_repo: 'your-repo'          # repository name (without owner)
```

---

## Notion Setup (Optional)

Notion integration allows TriageAgent and StandupAgent to create report pages.

### Create an Integration

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **"New integration"**
3. Name it "AgentForge" and submit
4. Copy the **Internal Integration Secret**

### Share a Page

1. Open the Notion page where you want reports
2. Click **"..."** → **"Add connections"** → Select "AgentForge"
3. Copy the **page ID** from the URL: `notion.so/Your-Page-{page_id}`

### Configure

```yaml
mcp_servers:
  notion_token: 'ntn_...'
  notion_page_id: 'abc123...'       # 32-char hex ID from page URL
```

> If Notion is not configured, agents will skip report creation (non-fatal).

---

## Slack Setup (Optional)

Slack integration allows agents to post alerts and standups.

### Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"** → **"From scratch"**
3. Under **OAuth & Permissions**, add Bot Token Scopes:
   - `chat:write` — Send messages
   - `channels:read` — List channels (for `agentforge server`)
4. **Install to Workspace** and copy the **Bot User OAuth Token**

### Invite the Bot

In Slack, invite the bot to your channel:
```
/invite @AgentForge
```

### Configure

```yaml
mcp_servers:
  slack_token: 'xoxb-...'
  slack_channel: engineering        # channel name without '#'
```

> If Slack is not configured, agents will skip alerts (non-fatal).

---

## Behavior Settings

### `auto_approve`

When `true`, bypasses all approval prompts for destructive operations. Use only in trusted, automated environments.

```yaml
auto_approve: false    # default: require human approval
```

### `confidence_threshold`

Minimum LLM confidence (0.0–1.0) for agent routing. Below this, the orchestrator falls back to keyword matching.

```yaml
confidence_threshold: 0.8    # default
```

- Lower values = trust LLM more, fewer fallbacks
- Higher values = more conservative, more keyword routing

### `max_iterations`

Maximum number of subtasks the orchestrator will generate per run.

```yaml
max_iterations: 10    # default
```

### `standup_lookback_hours`

How far back (in hours) the StandupAgent fetches GitHub activity.

```yaml
standup_lookback_hours: 24    # default: last 24 hours
```

---

## Verify Configuration

After configuring, check that all servers are properly set up:

```bash
agentforge server
```

Expected output:
```
  GitHub       ✅ configured
  Notion       ✅ configured
  Slack        ✅ configured
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `agentforge: command not found` | Run `pip install agentforge-ai` or `pip install -e .` |
| Config not loading | Ensure file is at `~/.agentforge/config.yml` (not `.yaml`) |
| GitHub 401 errors | Verify token has correct scopes and hasn't expired |
| Notion page not found | Ensure the integration is connected to the target page |
| Slack `channel_not_found` | Invite the bot to the channel with `/invite @BotName` |
| LLM timeout | Check API key validity; try switching providers |
