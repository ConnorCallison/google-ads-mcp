# Google Ads MCP

A local, write-capable MCP server for managing Google Ads accounts through the official
Google Ads API Python client.

This intentionally exposes write operations, but every write supports `dry_run`, validates basic
policy, and writes a JSONL audit record.

## What It Can Do

- List accessible Google Ads customers.
- Run arbitrary GAQL queries.
- Resolve place names to Google Ads geo-target IDs.
- Generate keyword ideas with historical search volume, competition, and bid ranges.
- Forecast proposed Search impressions, clicks, CPC, cost, and conversions without creating a campaign.
- Inspect campaign budgets.
- Set campaign budget amounts.
- Pause, enable, or remove campaigns.
- Mark an exact conversion action as primary or secondary for bidding.
- Set account-default goal biddability for an exact conversion category/origin pair.
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
  --client-id YOUR_CLIENT_ID
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
uv run google-ads-mcp-cli generate-refresh-token --client-id ...
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

## Keyword Planning

Use `suggest_geo_targets` to resolve names such as `Humboldt County, California` to Google geo
target IDs. `generate_keyword_ideas` accepts keyword seeds, a page URL, or both, plus optional
language and geo-target IDs. `generate_keyword_forecast` models a proposed Search ad group and
returns Google's non-guaranteed traffic and cost forecast without creating campaign resources.

Keyword planning calls are more tightly rate-limited than normal reporting calls. Cache results and
rerun them only when the keyword set, targeting, bid strategy, budget, or forecast period changes.

## Conversion Goal Controls

Use `search_google_ads` to inspect the conversion action IDs and existing customer goals before
calling either write tool. The two goal controls require an explicit customer ID and default to
`dry_run=true`, which sends a Google Ads `validate_only` mutation and records it in the audit log.

```json
{
  "tool": "set_conversion_action_primary_for_goal",
  "arguments": {
    "customer_id": "1234567890",
    "conversion_action_id": "9876543210",
    "primary_for_goal": false
  }
}
```

`conversion_action_id` must be the exact digits-only ID. Setting `primary_for_goal=false` makes
that action non-biddable for customer and campaign goals, but Google Ads custom conversion goals
can still bid on it. Setting it to true does not make the action biddable by itself; the matching
customer or campaign goal must also be biddable.

```json
{
  "tool": "set_customer_conversion_goal_biddable",
  "arguments": {
    "customer_id": "1234567890",
    "category": "PURCHASE",
    "origin": "WEBSITE",
    "biddable": true
  }
}
```

`category` and `origin` are exact, case-sensitive Google Ads enum names exposed by the MCP tool
schema. Customer conversion goals are automatically created by Google Ads and can only be updated,
not created or removed. The request customer must be the account's conversion customer. A
customer-goal update changes the account default only; campaigns with campaign-level goal
overrides are unaffected.

Official references: [conversion goal overview](https://developers.google.com/google-ads/api/docs/conversions/goals/overview),
[customer goals](https://developers.google.com/google-ads/api/docs/conversions/goals/customer-goals),
and [`ConversionAction.primary_for_goal`](https://developers.google.com/google-ads/api/reference/rpc/v24/ConversionAction#primary_for_goal).

## Development

```bash
uv run pytest
uv run ruff check .
```

## Notes

This project uses the official Google Ads API client library instead of a browser automation layer.
That is the right primitive for a trusted operator because it gives typed operations,
`validate_only`, resource names, partial failure support, and structured API errors.
