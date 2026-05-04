# Google Ads MCP

A local, write-capable MCP server for managing Google Ads accounts through the official
Google Ads API Python client.

This intentionally exposes write operations, but every write supports `dry_run`, validates basic
policy, and writes a JSONL audit record.

## What It Can Do

- List accessible Google Ads customers.
- Run arbitrary GAQL queries.
- Inspect campaign budgets.
- Set campaign budget amounts.
- Pause, enable, or remove campaigns.
- Add campaign-level negative keywords.
- Apply Google Ads recommendations.

## Setup

```bash
cd ~/code/google-ads-mcp
uv sync
cp .env.example .env
cp google-ads.yaml.example google-ads.yaml
```

Fill in `google-ads.yaml` with your Google Ads API credentials.

Google's official setup guide is here:
https://developers.google.com/google-ads/api/docs/get-started/make-first-call

At minimum you need:

- Google Ads developer token.
- OAuth client ID and client secret.
- OAuth refresh token for the Google user that can access the account.
- Customer ID, digits only.

You can generate the refresh token with:

```bash
uv run google-ads-mcp-cli generate-refresh-token \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET
```

## Run The MCP Server

```bash
cd ~/code/google-ads-mcp
uv run google-ads-mcp
```

For Codex/Claude-style MCP config, use a stdio server command like:

```json
{
  "mcpServers": {
    "google-ads-mcp": {
      "command": "uv",
      "args": ["--directory", "/Users/connor/code/google-ads-mcp", "run", "google-ads-mcp"],
      "env": {
        "GOOGLE_ADS_YAML_PATH": "/Users/connor/code/google-ads-mcp/google-ads.yaml",
        "GOOGLE_ADS_MCP_DRY_RUN": "true"
      }
    }
  }
}
```

## Helper CLI

The MCP server is the main interface. There is also a small CLI for setup checks and quick
queries:

```bash
uv run google-ads-mcp-cli check-config
uv run google-ads-mcp-cli generate-refresh-token --client-id ... --client-secret ...
uv run google-ads-mcp-cli list-customers
uv run google-ads-mcp-cli gaql --customer-id 1234567890 --file examples/campaign_snapshot.gaql
```

## Write Safety

The server is write-capable. The defaults are deliberately reversible:

- `GOOGLE_ADS_MCP_DRY_RUN=true` means writes call Google Ads with `validate_only`.
- Per-tool calls can pass `dry_run=false` to actually mutate the account.
- `GOOGLE_ADS_ALLOWED_CUSTOMER_IDS` can restrict which accounts this server touches.
- `GOOGLE_ADS_MAX_BUDGET_CHANGE_PCT` blocks unexpectedly large budget changes.
- Every write produces an audit record under `audit/YYYY-MM-DD.jsonl`.

## Useful GAQL

Try the included campaign snapshot:

```bash
cat examples/campaign_snapshot.gaql
```

Then call `search_google_ads` with that query.

## Development

```bash
uv run pytest
uv run ruff check .
```

## Notes

This project uses the official Google Ads API client library instead of a browser automation layer.
That is the right primitive for a trusted operator because it gives typed operations,
`validate_only`, resource names, partial failure support, and structured API errors.
