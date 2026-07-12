from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from google_ads_mcp.google_ads import GoogleAdsGateway, _serialize_google_ads_row


class _FakeGoogleAdsRow:
    @classmethod
    def to_dict(cls, instance: Any, **kwargs: Any) -> dict[str, Any]:
        assert instance is not None
        assert kwargs == {
            "preserving_proto_field_name": False,
            "use_integers_for_enums": False,
        }
        return {"campaignBudget": {"amountMicros": "1000000"}}


def test_serialize_google_ads_row_uses_proto_plus_conversion():
    row = _FakeGoogleAdsRow()

    assert _serialize_google_ads_row(row) == {"campaignBudget": {"amountMicros": "1000000"}}


class _FakeCampaignService:
    def __init__(self) -> None:
        self.request = None

    def campaign_path(self, customer_id: str, campaign_id: str) -> str:
        return f"customers/{customer_id}/campaigns/{campaign_id}"

    def mutate_campaigns(self, *, request: Any) -> Any:
        self.request = request
        return SimpleNamespace(results=[])


class _FakeGoogleAdsClient:
    def __init__(self) -> None:
        self.service = _FakeCampaignService()
        self.enums = SimpleNamespace(CampaignStatusEnum=SimpleNamespace(PAUSED="PAUSED"))

    def get_service(self, name: str) -> _FakeCampaignService:
        assert name == "CampaignService"
        return self.service

    def get_type(self, name: str) -> Any:
        if name == "CampaignOperation":
            return SimpleNamespace(
                update=SimpleNamespace(
                    resource_name="",
                    status=None,
                ),
                update_mask=SimpleNamespace(CopyFrom=lambda value: None),
            )
        if name == "MutateCampaignsRequest":
            return SimpleNamespace(customer_id="", operations=[], validate_only=False)
        raise AssertionError(f"Unexpected type request: {name}")


def test_set_campaign_status_uses_validate_only_request():
    gateway = GoogleAdsGateway(settings=None)  # type: ignore[arg-type]
    fake_client = _FakeGoogleAdsClient()
    gateway.__dict__["client"] = fake_client

    result = gateway.set_campaign_status(
        customer_id="5703884860",
        campaign_id="21650918079",
        status="PAUSED",
        dry_run=True,
    )

    assert fake_client.service.request.customer_id == "5703884860"
    assert fake_client.service.request.validate_only is True
    assert len(fake_client.service.request.operations) == 1
    assert result == {
        "resource_names": [],
        "status": "PAUSED",
        "validate_only": True,
    }


def test_apply_recommendation_dry_run_does_not_call_google():
    gateway = GoogleAdsGateway(settings=None)  # type: ignore[arg-type]

    assert gateway.apply_recommendation(
        customer_id="5703884860",
        recommendation_id="example",
        dry_run=True,
    ) == {
        "resource_names": [],
        "recommendation_id": "example",
        "validate_only": True,
    }
