from __future__ import annotations

from datetime import date, timedelta
from functools import cached_property
from typing import Any

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import field_mask_pb2

from google_ads_mcp.config import Settings
from google_ads_mcp.policy import validate_budget_change, validate_limit


def _serialize_google_ads_row(row: Any) -> dict[str, Any]:
    return type(row).to_dict(
        row,
        preserving_proto_field_name=False,
        use_integers_for_enums=False,
    )


def _serialize_google_ads_message(message: Any) -> dict[str, Any]:
    return type(message).to_dict(
        message,
        preserving_proto_field_name=False,
        use_integers_for_enums=False,
    )


def _clean_keywords(keywords: list[str], *, maximum: int) -> list[str]:
    cleaned = list(dict.fromkeys(keyword.strip() for keyword in keywords if keyword.strip()))
    if not cleaned:
        raise ValueError("at least one non-empty keyword is required")
    if len(cleaned) > maximum:
        raise ValueError(f"at most {maximum} keywords are allowed")
    return cleaned


def _resource_id(value: str, *, field: str) -> str:
    cleaned = value.strip().replace("-", "")
    if not cleaned.isdigit():
        raise ValueError(f"{field} must contain digits only")
    return cleaned


def _raise_clear_planning_access_error(exc: GoogleAdsException) -> None:
    if any("DEVELOPER_TOKEN_NOT_APPROVED" in str(error) for error in exc.failure.errors):
        raise RuntimeError(
            "Google Ads keyword planning requires Basic or Standard developer-token access. "
            "The configured token currently has Explorer access; apply for Basic Access in the "
            "Google Ads manager account API Center."
        ) from exc
    raise exc


class GoogleAdsGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @cached_property
    def client(self) -> GoogleAdsClient:
        if not self.settings.google_ads_yaml_path.exists():
            msg = f"Google Ads config not found at {self.settings.google_ads_yaml_path}"
            raise FileNotFoundError(msg)
        client = GoogleAdsClient.load_from_storage(str(self.settings.google_ads_yaml_path))
        if self.settings.login_customer_id:
            client.login_customer_id = self.settings.login_customer_id
        return client

    def list_accessible_customers(self) -> list[str]:
        service = self.client.get_service("CustomerService")
        response = service.list_accessible_customers()
        return list(response.resource_names)

    def search(self, *, customer_id: str, query: str, limit: int = 100) -> list[dict[str, Any]]:
        limit = validate_limit(limit)
        service = self.client.get_service("GoogleAdsService")
        rows: list[dict[str, Any]] = []
        stream = service.search_stream(customer_id=customer_id, query=query)
        for batch in stream:
            for row in batch.results:
                rows.append(_serialize_google_ads_row(row))
                if len(rows) >= limit:
                    return rows
        return rows

    def suggest_geo_targets(
        self,
        *,
        query: str,
        country_code: str,
        locale: str,
    ) -> list[dict[str, Any]]:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("query is required")
        cleaned_country = country_code.strip().upper()
        if len(cleaned_country) != 2 or not cleaned_country.isalpha():
            raise ValueError("country_code must be a two-letter ISO country code")

        request = self.client.get_type("SuggestGeoTargetConstantsRequest")
        request.locale = locale.strip() or "en"
        request.country_code = cleaned_country
        request.location_names.names.append(cleaned_query)
        service = self.client.get_service("GeoTargetConstantService")
        response = service.suggest_geo_target_constants(request=request)
        return [
            _serialize_google_ads_message(suggestion)
            for suggestion in response.geo_target_constant_suggestions
        ]

    def generate_keyword_ideas(
        self,
        *,
        customer_id: str,
        keywords: list[str],
        page_url: str | None,
        location_ids: list[str],
        language_id: str,
        network: str,
        include_adult_keywords: bool,
        limit: int,
    ) -> list[dict[str, Any]]:
        if not keywords and not (page_url and page_url.strip()):
            raise ValueError("keywords, page_url, or both are required")
        cleaned_keywords = _clean_keywords(keywords, maximum=20) if keywords else []
        cleaned_url = page_url.strip() if page_url else None
        cleaned_locations = [
            _resource_id(location_id, field="location_id") for location_id in location_ids
        ]
        cleaned_language = _resource_id(language_id, field="language_id")
        resolved_limit = validate_limit(limit)

        normalized_network = network.upper()
        if normalized_network not in {"GOOGLE_SEARCH", "GOOGLE_SEARCH_AND_PARTNERS"}:
            raise ValueError("network must be GOOGLE_SEARCH or GOOGLE_SEARCH_AND_PARTNERS")

        request = self.client.get_type("GenerateKeywordIdeasRequest")
        request.customer_id = customer_id
        request.language = f"languageConstants/{cleaned_language}"
        request.geo_target_constants.extend(
            f"geoTargetConstants/{location_id}" for location_id in cleaned_locations
        )
        request.include_adult_keywords = include_adult_keywords
        request.keyword_plan_network = getattr(
            self.client.enums.KeywordPlanNetworkEnum, normalized_network
        )
        request.page_size = resolved_limit

        if cleaned_keywords and cleaned_url:
            request.keyword_and_url_seed.keywords.extend(cleaned_keywords)
            request.keyword_and_url_seed.url = cleaned_url
        elif cleaned_keywords:
            request.keyword_seed.keywords.extend(cleaned_keywords)
        else:
            request.url_seed.url = cleaned_url

        service = self.client.get_service("KeywordPlanIdeaService")
        try:
            response = service.generate_keyword_ideas(request=request)
        except GoogleAdsException as exc:
            _raise_clear_planning_access_error(exc)
        ideas: list[dict[str, Any]] = []
        for idea in response:
            ideas.append(_serialize_google_ads_message(idea))
            if len(ideas) >= resolved_limit:
                break
        return ideas

    def generate_keyword_forecast(
        self,
        *,
        customer_id: str,
        keywords: list[str],
        location_ids: list[str],
        language_id: str,
        match_type: str,
        network: str,
        bidding_strategy: str,
        daily_budget_micros: int,
        max_cpc_bid_micros: int | None,
        start_date: str | None,
        end_date: str | None,
        currency_code: str,
        negative_keywords: list[str],
    ) -> dict[str, Any]:
        cleaned_keywords = _clean_keywords(keywords, maximum=200)
        cleaned_negatives = (
            _clean_keywords(negative_keywords, maximum=200) if negative_keywords else []
        )
        cleaned_locations = [
            _resource_id(location_id, field="location_id") for location_id in location_ids
        ]
        cleaned_language = _resource_id(language_id, field="language_id")
        if daily_budget_micros <= 0:
            raise ValueError("daily_budget_micros must be positive")
        if max_cpc_bid_micros is not None and max_cpc_bid_micros <= 0:
            raise ValueError("max_cpc_bid_micros must be positive when provided")

        normalized_match_type = match_type.upper()
        if normalized_match_type not in {"BROAD", "PHRASE", "EXACT"}:
            raise ValueError("match_type must be BROAD, PHRASE, or EXACT")
        normalized_network = network.upper()
        if normalized_network != "GOOGLE_SEARCH":
            raise ValueError(
                "Google Ads forecast requests support GOOGLE_SEARCH only; "
                "the current API no longer exposes a forecast network field"
            )
        if cleaned_negatives:
            raise ValueError(
                "negative_keywords are not supported by the current Google Ads forecast API"
            )
        normalized_strategy = bidding_strategy.upper()
        if normalized_strategy not in {"MANUAL_CPC", "MAXIMIZE_CLICKS", "MAXIMIZE_CONVERSIONS"}:
            raise ValueError(
                "bidding_strategy must be MANUAL_CPC, MAXIMIZE_CLICKS, or MAXIMIZE_CONVERSIONS"
            )
        if normalized_strategy == "MANUAL_CPC" and max_cpc_bid_micros is None:
            raise ValueError("max_cpc_bid_micros is required for MANUAL_CPC forecasts")

        tomorrow = date.today() + timedelta(days=1)
        resolved_start = date.fromisoformat(start_date) if start_date else tomorrow
        resolved_end = (
            date.fromisoformat(end_date) if end_date else resolved_start + timedelta(days=29)
        )
        if resolved_start < tomorrow:
            raise ValueError("start_date must be tomorrow or later")
        if resolved_end < resolved_start:
            raise ValueError("end_date must be on or after start_date")

        request = self.client.get_type("GenerateKeywordForecastMetricsRequest")
        request.customer_id = customer_id
        request.currency_code = currency_code.strip().upper()
        request.forecast_period.start_date = resolved_start.isoformat()
        request.forecast_period.end_date = resolved_end.isoformat()

        campaign = request.campaign
        campaign.language_constants.append(f"languageConstants/{cleaned_language}")
        campaign.geo_target_constants.extend(
            f"geoTargetConstants/{location_id}" for location_id in cleaned_locations
        )

        strategy = campaign.bidding_strategy
        if normalized_strategy == "MANUAL_CPC":
            strategy.manual_cpc_bidding_strategy.daily_budget_micros = daily_budget_micros
            strategy.manual_cpc_bidding_strategy.max_cpc_bid_micros = max_cpc_bid_micros
        elif normalized_strategy == "MAXIMIZE_CLICKS":
            strategy.maximize_clicks_bidding_strategy.daily_target_spend_micros = (
                daily_budget_micros
            )
            if max_cpc_bid_micros is not None:
                strategy.maximize_clicks_bidding_strategy.max_cpc_bid_ceiling_micros = (
                    max_cpc_bid_micros
                )
        else:
            strategy.maximize_conversions_bidding_strategy.daily_target_spend_micros = (
                daily_budget_micros
            )

        ad_group = self.client.get_type("ForecastAdGroup")
        for keyword_text in cleaned_keywords:
            keyword = self.client.get_type("KeywordInfo")
            keyword.text = keyword_text
            keyword.match_type = getattr(
                self.client.enums.KeywordMatchTypeEnum, normalized_match_type
            )
            ad_group.keywords.append(keyword)
        campaign.ad_groups.append(ad_group)

        service = self.client.get_service("KeywordPlanIdeaService")
        try:
            response = service.generate_keyword_forecast_metrics(request=request)
        except GoogleAdsException as exc:
            _raise_clear_planning_access_error(exc)
        return {
            "forecastPeriod": {
                "startDate": resolved_start.isoformat(),
                "endDate": resolved_end.isoformat(),
            },
            "currencyCode": request.currency_code,
            "network": normalized_network,
            "biddingStrategy": normalized_strategy,
            "keywordCount": len(cleaned_keywords),
            "metrics": _serialize_google_ads_message(response.campaign_forecast_metrics),
        }

    def get_campaign_budget(self, *, customer_id: str, budget_id: str) -> dict[str, Any] | None:
        resource_name = self.client.get_service("CampaignBudgetService").campaign_budget_path(
            customer_id, budget_id
        )
        query = f"""
            SELECT
              campaign_budget.id,
              campaign_budget.name,
              campaign_budget.amount_micros,
              campaign_budget.delivery_method,
              campaign_budget.status
            FROM campaign_budget
            WHERE campaign_budget.resource_name = '{resource_name}'
            LIMIT 1
        """
        rows = self.search(customer_id=customer_id, query=query, limit=1)
        return rows[0].get("campaignBudget") if rows else None

    def set_campaign_budget(
        self,
        *,
        customer_id: str,
        budget_id: str,
        amount_micros: int,
        dry_run: bool,
    ) -> dict[str, Any]:
        existing = self.get_campaign_budget(customer_id=customer_id, budget_id=budget_id)
        current_amount = existing.get("amountMicros") if existing else None
        validate_budget_change(
            current_amount_micros=int(current_amount) if current_amount is not None else None,
            new_amount_micros=amount_micros,
            max_change_pct=self.settings.max_budget_change_pct,
        )

        service = self.client.get_service("CampaignBudgetService")
        operation = self.client.get_type("CampaignBudgetOperation")
        operation.update.resource_name = service.campaign_budget_path(customer_id, budget_id)
        operation.update.amount_micros = amount_micros
        operation.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["amount_micros"]))

        request = self.client.get_type("MutateCampaignBudgetsRequest")
        request.customer_id = customer_id
        request.operations.append(operation)
        request.validate_only = dry_run
        response = service.mutate_campaign_budgets(request=request)
        return {
            "resource_names": [result.resource_name for result in response.results],
            "previous_amount_micros": current_amount,
            "new_amount_micros": amount_micros,
            "validate_only": dry_run,
        }

    def set_campaign_status(
        self,
        *,
        customer_id: str,
        campaign_id: str,
        status: str,
        dry_run: bool,
    ) -> dict[str, Any]:
        normalized = status.upper()
        if normalized not in {"ENABLED", "PAUSED", "REMOVED"}:
            raise ValueError("status must be ENABLED, PAUSED, or REMOVED")

        service = self.client.get_service("CampaignService")
        operation = self.client.get_type("CampaignOperation")
        operation.update.resource_name = service.campaign_path(customer_id, campaign_id)
        operation.update.status = getattr(self.client.enums.CampaignStatusEnum, normalized)
        operation.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["status"]))

        request = self.client.get_type("MutateCampaignsRequest")
        request.customer_id = customer_id
        request.operations.append(operation)
        request.validate_only = dry_run
        response = service.mutate_campaigns(request=request)
        return {
            "resource_names": [result.resource_name for result in response.results],
            "status": normalized,
            "validate_only": dry_run,
        }

    def add_campaign_negative_keyword(
        self,
        *,
        customer_id: str,
        campaign_id: str,
        keyword_text: str,
        match_type: str,
        dry_run: bool,
    ) -> dict[str, Any]:
        normalized_match_type = match_type.upper()
        if normalized_match_type not in {"BROAD", "PHRASE", "EXACT"}:
            raise ValueError("match_type must be BROAD, PHRASE, or EXACT")
        if not keyword_text.strip():
            raise ValueError("keyword_text is required")

        campaign_service = self.client.get_service("CampaignService")
        criterion_service = self.client.get_service("CampaignCriterionService")
        operation = self.client.get_type("CampaignCriterionOperation")
        criterion = operation.create
        criterion.campaign = campaign_service.campaign_path(customer_id, campaign_id)
        criterion.negative = True
        criterion.keyword.text = keyword_text.strip()
        criterion.keyword.match_type = getattr(
            self.client.enums.KeywordMatchTypeEnum, normalized_match_type
        )

        request = self.client.get_type("MutateCampaignCriteriaRequest")
        request.customer_id = customer_id
        request.operations.append(operation)
        request.validate_only = dry_run
        response = criterion_service.mutate_campaign_criteria(request=request)
        return {
            "resource_names": [result.resource_name for result in response.results],
            "keyword_text": keyword_text.strip(),
            "match_type": normalized_match_type,
            "validate_only": dry_run,
        }

    def apply_recommendation(
        self,
        *,
        customer_id: str,
        recommendation_id: str,
        dry_run: bool,
    ) -> dict[str, Any]:
        if dry_run:
            return {
                "resource_names": [],
                "recommendation_id": recommendation_id,
                "validate_only": True,
            }

        service = self.client.get_service("RecommendationService")
        operation = self.client.get_type("ApplyRecommendationOperation")
        operation.resource_name = service.recommendation_path(customer_id, recommendation_id)
        request = self.client.get_type("ApplyRecommendationRequest")
        request.customer_id = customer_id
        request.operations.append(operation)
        request.partial_failure = False
        response = service.apply_recommendation(request=request)
        return {
            "resource_names": [result.resource_name for result in response.results],
            "recommendation_id": recommendation_id,
            "validate_only": False,
        }
