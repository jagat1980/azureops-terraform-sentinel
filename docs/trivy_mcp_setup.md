# Trivy MCP Setup

This repository defines a project-scoped Codex MCP server for Trivy in
`.codex/config.toml`.

## Tools

- `scan_image`: returns raw Trivy JSON from either a live `trivy image` run or a
  repository-local payload file.
- `analyze_image`: runs the AzureOps container remediation pipeline using the
  Trivy-style payload and writes the local audit report.

## Requirements

- The project must be trusted by Codex so `.codex/config.toml` is loaded.
- `C:\tmp\uv-checkov\uv.exe` must exist. This thread installed it while setting
  up Checkov.
- For live image scans, install the `trivy` executable on the host. Without it,
  use `payload_path` for offline validation.

## Verification

After restarting Codex or opening a new trusted session, check `/mcp` and confirm
the `trivy` server is listed. Then call `trivy.analyze_image` with:

```json
{
  "image_uri": "azureops-app:latest",
  "payload_path": "payloads/trivy_container_openssl_cve.json"
}
```

