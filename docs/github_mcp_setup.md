# GitHub MCP Setup

This repository defines a project-scoped Codex MCP server for GitHub in
`.codex/config.toml`.

## Authentication

Set a GitHub token in the local environment before starting Codex:

```powershell
$env:GITHUB_MCP_PAT = "<your-github-token>"
```

Do not commit tokens to this repository. The project config references only the
environment variable name.

## Server

The configured server uses GitHub's hosted MCP endpoint:

```toml
[mcp_servers.github]
url = "https://api.githubcopilot.com/mcp/"
bearer_token_env_var = "GITHUB_MCP_PAT"
```

## Verification

After restarting Codex or opening a new trusted session, check `/mcp` and confirm
the `github` server is listed. Keep tool approval prompts enabled for GitHub
actions that create or modify issues, pull requests, comments, branches, or
workflow state.

