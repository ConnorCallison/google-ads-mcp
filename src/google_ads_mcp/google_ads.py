from __future__ import annotations

from functools import cached_property
from typing import Any

from google.ads.googleads.client import GoogleAdsClient
from google.protobuf import field_mask_pb2

from google_ads_mcp.config import Settings
from google_ads_mcp.policy import validate_budget_change, validate_limit


def _serialize_google_ads_row(row: Any) -> dict[str, Any]:
    return GoogleAdsClient.serialize(row)


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

        response = service.mutate_campaign_budgets(
            customer_id=customer_id,
            operations=[operation],
            validate_only=dry_run,
        )
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

        response = service.mutate_campaigns(
            customer_id=customer_id,
            operations=[operation],
            validate_only=dry_run,
        )
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

        response = criterion_service.mutate_campaign_criteria(
            customer_id=customer_id,
            operations=[operation],
            validate_only=dry_run,
        )
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
        service = self.client.get_service("RecommendationService")
        operation = self.client.get_type("ApplyRecommendationOperation")
        operation.resource_name = service.recommendation_path(customer_id, recommendation_id)
        response = service.apply_recommendation(
            customer_id=customer_id,
            operations=[operation],
            partial_failure=False,
            validate_only=dry_run,
        )
        return {
            "resource_names": [result.resource_name for result in response.results],
            "recommendation_id": recommendation_id,
            "validate_only": dry_run,
        }
