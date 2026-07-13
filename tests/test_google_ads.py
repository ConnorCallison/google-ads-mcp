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


class _FakeKeywordIdeasRequest:
    def __init__(self) -> None:
        self.customer_id = ""
        self.language = ""
        self.geo_target_constants: list[str] = []
        self.include_adult_keywords = False
        self.keyword_plan_network = None
        self.page_size = 0
        self.keyword_and_url_seed = SimpleNamespace(keywords=[], url="")
        self.keyword_seed = SimpleNamespace(keywords=[])
        self.url_seed = SimpleNamespace(url="")


class _FakeGeoRequest:
    def __init__(self) -> None:
        self.locale = ""
        self.country_code = ""
        self.location_names = SimpleNamespace(names=[])


class _FakeGeoSuggestion:
    @classmethod
    def to_dict(cls, instance: Any, **kwargs: Any) -> dict[str, Any]:
        assert kwargs == {
            "preserving_proto_field_name": False,
            "use_integers_for_enums": False,
        }
        return {
            "searchTerm": instance.search_term,
            "geoTargetConstant": {"resourceName": instance.resource_name},
        }

    def __init__(self) -> None:
        self.search_term = "Humboldt County, California"
        self.resource_name = "geoTargetConstants/21137"


class _FakeForecastRequest:
    def __init__(self) -> None:
        self.customer_id = ""
        self.currency_code = ""
        self.forecast_period = SimpleNamespace(start_date="", end_date="")
        self.campaign = SimpleNamespace(
            language_constants=[],
            geo_modifiers=[],
            keyword_plan_network=None,
            negative_keywords=[],
            ad_groups=[],
            bidding_strategy=SimpleNamespace(
                manual_cpc_bidding_strategy=SimpleNamespace(
                    daily_budget_micros=0,
                    max_cpc_bid_micros=0,
                ),
                maximize_clicks_bidding_strategy=SimpleNamespace(
                    daily_target_spend_micros=0,
                    max_cpc_bid_ceiling_micros=0,
                ),
                maximize_conversions_bidding_strategy=SimpleNamespace(
                    daily_target_spend_micros=0,
                ),
            ),
        )


class _FakeForecastMetrics:
    @classmethod
    def to_dict(cls, instance: Any, **kwargs: Any) -> dict[str, Any]:
        assert kwargs == {
            "preserving_proto_field_name": False,
            "use_integers_for_enums": False,
        }
        return {
            "impressions": instance.impressions,
            "clicks": instance.clicks,
            "costMicros": instance.cost_micros,
        }

    def __init__(self) -> None:
        self.impressions = 1200.0
        self.clicks = 84.0
        self.cost_micros = 25_000_000


class _FakeKeywordPlanService:
    def __init__(self) -> None:
        self.idea_request = None
        self.forecast_request = None
        self.geo_request = None

    def generate_keyword_ideas(self, *, request: Any) -> list[Any]:
        self.idea_request = request
        return []

    def generate_keyword_forecast_metrics(self, *, request: Any) -> Any:
        self.forecast_request = request
        return SimpleNamespace(campaign_forecast_metrics=_FakeForecastMetrics())

    def suggest_geo_target_constants(self, *, request: Any) -> Any:
        self.geo_request = request
        return SimpleNamespace(geo_target_constant_suggestions=[_FakeGeoSuggestion()])


class _FakePlanningClient:
    def __init__(self) -> None:
        self.service = _FakeKeywordPlanService()
        self.enums = SimpleNamespace(
            KeywordPlanNetworkEnum=SimpleNamespace(
                GOOGLE_SEARCH="GOOGLE_SEARCH",
                GOOGLE_SEARCH_AND_PARTNERS="GOOGLE_SEARCH_AND_PARTNERS",
            ),
            KeywordMatchTypeEnum=SimpleNamespace(
                BROAD="BROAD",
                PHRASE="PHRASE",
                EXACT="EXACT",
            ),
        )

    def get_service(self, name: str) -> _FakeKeywordPlanService:
        assert name in {"KeywordPlanIdeaService", "GeoTargetConstantService"}
        return self.service

    def get_type(self, name: str) -> Any:
        if name == "SuggestGeoTargetConstantsRequest":
            return _FakeGeoRequest()
        if name == "GenerateKeywordIdeasRequest":
            return _FakeKeywordIdeasRequest()
        if name == "GenerateKeywordForecastMetricsRequest":
            return _FakeForecastRequest()
        if name == "CriterionBidModifier":
            return SimpleNamespace(geo_target_constant="", bid_modifier=0.0)
        if name == "ForecastAdGroup":
            return SimpleNamespace(
                max_cpc_bid_micros=0,
                biddable_keywords=[],
                negative_keywords=[],
            )
        if name == "BiddableKeyword":
            return SimpleNamespace(
                keyword=SimpleNamespace(text="", match_type=None),
                max_cpc_bid_micros=0,
            )
        if name == "KeywordInfo":
            return SimpleNamespace(text="", match_type=None)
        raise AssertionError(f"Unexpected type request: {name}")


def test_suggest_geo_targets_resolves_hyperlocal_place_names():
    gateway = GoogleAdsGateway(settings=None)  # type: ignore[arg-type]
    fake_client = _FakePlanningClient()
    gateway.__dict__["client"] = fake_client

    result = gateway.suggest_geo_targets(
        query="Humboldt County, California",
        country_code="us",
        locale="en",
    )

    request = fake_client.service.geo_request
    assert request.country_code == "US"
    assert request.location_names.names == ["Humboldt County, California"]
    assert result == [
        {
            "searchTerm": "Humboldt County, California",
            "geoTargetConstant": {"resourceName": "geoTargetConstants/21137"},
        }
    ]


def test_generate_keyword_ideas_builds_scoped_keyword_and_url_request():
    gateway = GoogleAdsGateway(settings=None)  # type: ignore[arg-type]
    fake_client = _FakePlanningClient()
    gateway.__dict__["client"] = fake_client

    result = gateway.generate_keyword_ideas(
        customer_id="5703884860",
        keywords=["event ticketing", " event ticketing ", "box office software"],
        page_url="https://example.com/ticketing",
        location_ids=["21137"],
        language_id="1000",
        network="GOOGLE_SEARCH",
        include_adult_keywords=False,
        limit=100,
    )

    request = fake_client.service.idea_request
    assert result == []
    assert request.customer_id == "5703884860"
    assert request.language == "languageConstants/1000"
    assert request.geo_target_constants == ["geoTargetConstants/21137"]
    assert request.keyword_and_url_seed.keywords == [
        "event ticketing",
        "box office software",
    ]
    assert request.keyword_and_url_seed.url == "https://example.com/ticketing"
    assert request.keyword_plan_network == "GOOGLE_SEARCH"


def test_generate_keyword_forecast_builds_non_mutating_campaign_model():
    gateway = GoogleAdsGateway(settings=None)  # type: ignore[arg-type]
    fake_client = _FakePlanningClient()
    gateway.__dict__["client"] = fake_client

    result = gateway.generate_keyword_forecast(
        customer_id="5703884860",
        keywords=["event ticketing software", "sell event tickets"],
        location_ids=["21137"],
        language_id="1000",
        match_type="PHRASE",
        network="GOOGLE_SEARCH",
        bidding_strategy="MAXIMIZE_CLICKS",
        daily_budget_micros=5_000_000,
        max_cpc_bid_micros=2_000_000,
        start_date="2030-01-01",
        end_date="2030-01-30",
        currency_code="usd",
        negative_keywords=["jobs"],
    )

    request = fake_client.service.forecast_request
    campaign = request.campaign
    assert request.customer_id == "5703884860"
    assert request.currency_code == "USD"
    assert campaign.language_constants == ["languageConstants/1000"]
    assert campaign.geo_modifiers[0].geo_target_constant == "geoTargetConstants/21137"
    assert (
        campaign.bidding_strategy.maximize_clicks_bidding_strategy.daily_target_spend_micros
        == 5_000_000
    )
    assert [keyword.keyword.text for keyword in campaign.ad_groups[0].biddable_keywords] == [
        "event ticketing software",
        "sell event tickets",
    ]
    assert campaign.negative_keywords[0].text == "jobs"
    assert result["metrics"] == {
        "impressions": 1200.0,
        "clicks": 84.0,
        "costMicros": 25_000_000,
    }
