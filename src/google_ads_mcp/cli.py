from __future__ import annotations

import argparse
import getpass
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from google_ads_mcp.config import Settings
from google_ads_mcp.google_ads import GoogleAdsGateway

GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"


def _print_json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def check_config(settings: Settings) -> int:
    payload = {
        "google_ads_yaml_path": str(settings.google_ads_yaml_path),
        "google_ads_yaml_exists": settings.google_ads_yaml_path.exists(),
        "login_customer_id": settings.login_customer_id,
        "default_customer_id": settings.default_customer_id,
        "audit_dir": str(settings.audit_dir),
        "default_dry_run": settings.default_dry_run,
        "allowed_customer_ids": sorted(settings.allowed_customer_ids),
        "max_budget_change_pct": settings.max_budget_change_pct,
    }
    _print_json(payload)
    return 0 if settings.google_ads_yaml_path.exists() else 1


def list_customers(settings: Settings) -> int:
    _print_json(GoogleAdsGateway(settings).list_accessible_customers())
    return 0


def run_gaql(settings: Settings, *, customer_id: str | None, query: str, limit: int) -> int:
    gateway = GoogleAdsGateway(settings)
    resolved_customer_id = settings.customer_id(customer_id)
    _print_json(gateway.search(customer_id=resolved_customer_id, query=query, limit=limit))
    return 0


def generate_refresh_token(*, client_id: str, client_secret: str) -> int:
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        },
        scopes=[GOOGLE_ADS_SCOPE],
    )
    credentials = flow.run_local_server(
        port=0,
        authorization_prompt_message="Open this URL to authorize Google Ads access: {url}",
        success_message="Authorization complete. You can close this browser tab.",
        open_browser=True,
        access_type="offline",
        prompt="consent",
    )
    _print_json({"refresh_token": credentials.refresh_token})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Google Ads MCP helper CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check-config", help="Show resolved local config without calling Google")
    subparsers.add_parser("list-customers", help="Call Google Ads and list accessible customers")

    gaql = subparsers.add_parser("gaql", help="Run a GAQL query")
    gaql.add_argument("--customer-id", help="Customer ID, digits or dashed format")
    gaql.add_argument("--query", help="GAQL query text")
    gaql.add_argument("--file", type=Path, help="Path to a .gaql query file")
    gaql.add_argument("--limit", type=int, default=100)

    refresh = subparsers.add_parser(
        "generate-refresh-token",
        help="Open a browser OAuth flow and print a Google Ads refresh token",
    )
    refresh.add_argument("--client-id", required=True)
    refresh.add_argument("--client-secret", help="OAuth client secret. Omit to enter it securely.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = Settings.from_env()

    if args.command == "check-config":
        raise SystemExit(check_config(settings))
    if args.command == "list-customers":
        raise SystemExit(list_customers(settings))
    if args.command == "gaql":
        if bool(args.query) == bool(args.file):
            parser.error("Provide exactly one of --query or --file")
        query = args.query if args.query else args.file.read_text(encoding="utf-8")
        raise SystemExit(
            run_gaql(settings, customer_id=args.customer_id, query=query, limit=args.limit)
        )
    if args.command == "generate-refresh-token":
        client_secret = args.client_secret or getpass.getpass("OAuth client secret: ")
        raise SystemExit(
            generate_refresh_token(client_id=args.client_id, client_secret=client_secret)
        )

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
