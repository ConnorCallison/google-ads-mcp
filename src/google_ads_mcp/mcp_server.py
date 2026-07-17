from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from google_ads_mcp.audit import AuditLogger
from google_ads_mcp.config import Settings
from google_ads_mcp.google_ads import GoogleAdsGateway

mcp = FastMCP("Google Ads MCP")
settings = Settings.from_env()
gateway = GoogleAdsGateway(settings)
audit = AuditLogger(settings.audit_dir)


def _dry_run(value: bool | None) -> bool:
    return settings.default_dry_run if value is None else value


def _recorded_write(
    *,
    tool: str,
    customer_id: str,
    dry_run: bool,
    request: dict[str, Any],
    action,
) -> dict[str, Any]:
    try:
        response = action()
    except Exception as exc:
        record = audit.write(
            tool=tool,
            customer_id=customer_id,
            dry_run=dry_run,
            request=request,
            error=str(exc),
        )
        raise RuntimeError(f"{exc} (audit_id={record.id})") from exc
    record = audit.write(
        tool=tool,
        customer_id=customer_id,
        dry_run=dry_run,
        request=request,
        response=response,
    )
    return {"audit_id": record.id, **response}


@mcp.tool()
def list_accessible_customers() -> list[str]:
    """List Google Ads customer resource names available to the configured OAuth user."""
    return gateway.list_accessible_customers()


@mcp.tool()
def search_google_ads(
    customer_id: str | None,
    query: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Run a GAQL query and return serialized Google Ads rows."""
    resolved_customer_id = settings.customer_id(customer_id)
    return gateway.search(customer_id=resolved_customer_id, query=query, limit=limit)


@mcp.tool()
def suggest_geo_targets(
    query: str,
    country_code: str = "US",
    locale: str = "en",
) -> list[dict[str, Any]]:
    """Resolve a place name to Google Ads geo-target IDs for hyperlocal planning."""
    return gateway.suggest_geo_targets(
        query=query,
        country_code=country_code,
        locale=locale,
    )


@mcp.tool()
def generate_keyword_ideas(
    customer_id: str | None,
    keywords: list[str] | None = None,
    page_url: str | None = None,
    location_ids: list[str] | None = None,
    language_id: str = "1000",
    network: str = "GOOGLE_SEARCH",
    include_adult_keywords: bool = False,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Generate Google Search keyword ideas with historical volume and bid metrics."""
    resolved_customer_id = settings.customer_id(customer_id)
    return gateway.generate_keyword_ideas(
        customer_id=resolved_customer_id,
        keywords=keywords or [],
        page_url=page_url,
        location_ids=location_ids or [],
        language_id=language_id,
        network=network,
        include_adult_keywords=include_adult_keywords,
        limit=limit,
    )


@mcp.tool()
def generate_keyword_forecast(
    customer_id: str | None,
    keywords: list[str],
    daily_budget_micros: int,
    location_ids: list[str] | None = None,
    language_id: str = "1000",
    match_type: str = "EXACT",
    network: str = "GOOGLE_SEARCH",
    bidding_strategy: str = "MAXIMIZE_CLICKS",
    max_cpc_bid_micros: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    currency_code: str = "USD",
    negative_keywords: list[str] | None = None,
) -> dict[str, Any]:
    """Forecast Google Search impressions, clicks, CPC, cost, and optional conversions.

    The current Google Ads forecast API supports Google Search only and does not expose
    negative-keyword inputs. Passing either an alternate network or negative keywords
    returns a clear validation error rather than silently changing the forecast.
    """
    resolved_customer_id = settings.customer_id(customer_id)
    return gateway.generate_keyword_forecast(
        customer_id=resolved_customer_id,
        keywords=keywords,
        location_ids=location_ids or [],
        language_id=language_id,
        match_type=match_type,
        network=network,
        bidding_strategy=bidding_strategy,
        daily_budget_micros=daily_budget_micros,
        max_cpc_bid_micros=max_cpc_bid_micros,
        start_date=start_date,
        end_date=end_date,
        currency_code=currency_code,
        negative_keywords=negative_keywords or [],
    )


@mcp.tool()
def get_campaign_budget(customer_id: str | None, budget_id: str) -> dict[str, Any] | None:
    """Fetch a campaign budget by numeric campaign budget ID."""
    resolved_customer_id = settings.customer_id(customer_id)
    return gateway.get_campaign_budget(customer_id=resolved_customer_id, budget_id=budget_id)


@mcp.tool()
def set_campaign_budget(
    customer_id: str | None,
    budget_id: str,
    amount_micros: int,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    """Set a campaign budget amount in micros. Pass dry_run=false to perform the write."""
    resolved_customer_id = settings.customer_id(customer_id)
    resolved_dry_run = _dry_run(dry_run)
    request = {
        "budget_id": budget_id,
        "amount_micros": amount_micros,
    }
    return _recorded_write(
        tool="set_campaign_budget",
        customer_id=resolved_customer_id,
        dry_run=resolved_dry_run,
        request=request,
        action=lambda: gateway.set_campaign_budget(
            customer_id=resolved_customer_id,
            budget_id=budget_id,
            amount_micros=amount_micros,
            dry_run=resolved_dry_run,
        ),
    )


@mcp.tool()
def set_campaign_status(
    customer_id: str | None,
    campaign_id: str,
    status: str,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    """Set a campaign status to ENABLED, PAUSED, or REMOVED."""
    resolved_customer_id = settings.customer_id(customer_id)
    resolved_dry_run = _dry_run(dry_run)
    request = {
        "campaign_id": campaign_id,
        "status": status,
    }
    return _recorded_write(
        tool="set_campaign_status",
        customer_id=resolved_customer_id,
        dry_run=resolved_dry_run,
        request=request,
        action=lambda: gateway.set_campaign_status(
            customer_id=resolved_customer_id,
            campaign_id=campaign_id,
            status=status,
            dry_run=resolved_dry_run,
        ),
    )


@mcp.tool()
def add_campaign_negative_keyword(
    customer_id: str | None,
    campaign_id: str,
    keyword_text: str,
    match_type: str = "EXACT",
    dry_run: bool | None = None,
) -> dict[str, Any]:
    """Add a campaign-level negative keyword with BROAD, PHRASE, or EXACT match."""
    resolved_customer_id = settings.customer_id(customer_id)
    resolved_dry_run = _dry_run(dry_run)
    request = {
        "campaign_id": campaign_id,
        "keyword_text": keyword_text,
        "match_type": match_type,
    }
    return _recorded_write(
        tool="add_campaign_negative_keyword",
        customer_id=resolved_customer_id,
        dry_run=resolved_dry_run,
        request=request,
        action=lambda: gateway.add_campaign_negative_keyword(
            customer_id=resolved_customer_id,
            campaign_id=campaign_id,
            keyword_text=keyword_text,
            match_type=match_type,
            dry_run=resolved_dry_run,
        ),
    )


@mcp.tool()
def apply_recommendation(
    customer_id: str | None,
    recommendation_id: str,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    """Apply a Google Ads recommendation by numeric recommendation ID."""
    resolved_customer_id = settings.customer_id(customer_id)
    resolved_dry_run = _dry_run(dry_run)
    request = {"recommendation_id": recommendation_id}
    return _recorded_write(
        tool="apply_recommendation",
        customer_id=resolved_customer_id,
        dry_run=resolved_dry_run,
        request=request,
        action=lambda: gateway.apply_recommendation(
            customer_id=resolved_customer_id,
            recommendation_id=recommendation_id,
            dry_run=resolved_dry_run,
        ),
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
