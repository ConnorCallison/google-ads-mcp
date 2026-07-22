from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from google.ads.googleads.client import GoogleAdsClient

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


class _FakeUpdateMask:
    def __init__(self) -> None:
        self.paths: list[str] = []

    def CopyFrom(self, value: Any) -> None:
        self.paths = list(value.paths)


class _FakeConversionActionService:
    def __init__(self) -> None:
        self.request = None

    def conversion_action_path(self, customer_id: str, conversion_action_id: str) -> str:
        return f"customers/{customer_id}/conversionActions/{conversion_action_id}"

    def mutate_conversion_actions(self, *, request: Any) -> Any:
        self.request = request
        return SimpleNamespace(
            results=[SimpleNamespace(resource_name=request.operations[0].update.resource_name)]
        )


class _FakeConversionActionClient:
    def __init__(self) -> None:
        self.service = _FakeConversionActionService()

    def get_service(self, name: str) -> _FakeConversionActionService:
        assert name == "ConversionActionService"
        return self.service

    def get_type(self, name: str) -> Any:
        if name == "ConversionActionOperation":
            return SimpleNamespace(
                update=SimpleNamespace(resource_name="", primary_for_goal=None),
                update_mask=_FakeUpdateMask(),
            )
        if name == "MutateConversionActionsRequest":
            return SimpleNamespace(customer_id="", operations=[], validate_only=False)
        raise AssertionError(f"Unexpected type request: {name}")


def test_set_conversion_action_primary_for_goal_uses_exact_id_and_validate_only():
    gateway = GoogleAdsGateway(settings=None)  # type: ignore[arg-type]
    fake_client = _FakeConversionActionClient()
    gateway.__dict__["client"] = fake_client

    result = gateway.set_conversion_action_primary_for_goal(
        customer_id="5703884860",
        conversion_action_id="7268783163",
        primary_for_goal=False,
        dry_run=True,
    )

    request = fake_client.service.request
    operation = request.operations[0]
    assert request.customer_id == "5703884860"
    assert request.validate_only is True
    assert operation.update.resource_name == (
        "customers/5703884860/conversionActions/7268783163"
    )
    assert operation.update.primary_for_goal is False
    assert operation.update_mask.paths == ["primary_for_goal"]
    assert result == {
        "resource_names": ["customers/5703884860/conversionActions/7268783163"],
        "resource_name": "customers/5703884860/conversionActions/7268783163",
        "conversion_action_id": "7268783163",
        "primary_for_goal": False,
        "validate_only": True,
    }


def test_set_conversion_action_primary_for_goal_rejects_non_exact_id():
    gateway = GoogleAdsGateway(settings=None)  # type: ignore[arg-type]
    fake_client = _FakeConversionActionClient()
    gateway.__dict__["client"] = fake_client

    try:
        gateway.set_conversion_action_primary_for_goal(
            customer_id="5703884860",
            conversion_action_id="7-268-783-163",
            primary_for_goal=True,
            dry_run=True,
        )
    except ValueError as exc:
        assert "ASCII digits only" in str(exc)
    else:
        raise AssertionError("non-exact conversion action ID was accepted")
    assert fake_client.service.request is None


class _FakeCustomerConversionGoalService:
    def __init__(self) -> None:
        self.request = None

    def customer_conversion_goal_path(
        self,
        customer_id: str,
        category: str,
        origin: str,
    ) -> str:
        return f"customers/{customer_id}/customerConversionGoals/{category}~{origin}"

    def mutate_customer_conversion_goals(self, *, request: Any) -> Any:
        self.request = request
        return SimpleNamespace(
            results=[SimpleNamespace(resource_name=request.operations[0].update.resource_name)]
        )


class _FakeCustomerConversionGoalClient:
    def __init__(self) -> None:
        self.service = _FakeCustomerConversionGoalService()

    def get_service(self, name: str) -> _FakeCustomerConversionGoalService:
        assert name == "CustomerConversionGoalService"
        return self.service

    def get_type(self, name: str) -> Any:
        if name == "CustomerConversionGoalOperation":
            return SimpleNamespace(
                update=SimpleNamespace(resource_name="", biddable=None),
                update_mask=_FakeUpdateMask(),
            )
        if name == "MutateCustomerConversionGoalsRequest":
            return SimpleNamespace(customer_id="", operations=[], validate_only=False)
        raise AssertionError(f"Unexpected type request: {name}")


def test_set_customer_conversion_goal_biddable_uses_exact_enums_and_validate_only():
    gateway = GoogleAdsGateway(settings=None)  # type: ignore[arg-type]
    fake_client = _FakeCustomerConversionGoalClient()
    gateway.__dict__["client"] = fake_client

    result = gateway.set_customer_conversion_goal_biddable(
        customer_id="5703884860",
        category="PURCHASE",
        origin="WEBSITE",
        biddable=True,
        dry_run=True,
    )

    request = fake_client.service.request
    operation = request.operations[0]
    assert request.customer_id == "5703884860"
    assert request.validate_only is True
    assert operation.update.resource_name == (
        "customers/5703884860/customerConversionGoals/PURCHASE~WEBSITE"
    )
    assert operation.update.biddable is True
    assert operation.update_mask.paths == ["biddable"]
    assert result == {
        "resource_names": [
            "customers/5703884860/customerConversionGoals/PURCHASE~WEBSITE"
        ],
        "resource_name": (
            "customers/5703884860/customerConversionGoals/PURCHASE~WEBSITE"
        ),
        "category": "PURCHASE",
        "origin": "WEBSITE",
        "biddable": True,
        "validate_only": True,
    }


def test_set_customer_conversion_goal_biddable_rejects_non_exact_enums():
    gateway = GoogleAdsGateway(settings=None)  # type: ignore[arg-type]
    fake_client = _FakeCustomerConversionGoalClient()
    gateway.__dict__["client"] = fake_client

    for category, origin in [("purchase", "WEBSITE"), ("PURCHASE", "web")]:
        try:
            gateway.set_customer_conversion_goal_biddable(
                customer_id="5703884860",
                category=category,  # type: ignore[arg-type]
                origin=origin,  # type: ignore[arg-type]
                biddable=False,
                dry_run=True,
            )
        except ValueError as exc:
            assert "exact Google Ads enum name" in str(exc)
        else:
            raise AssertionError("non-exact conversion goal enum was accepted")
    assert fake_client.service.request is None


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
            geo_target_constants=[],
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
        if name == "ForecastAdGroup":
            return SimpleNamespace(keywords=[])
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
        negative_keywords=[],
    )

    request = fake_client.service.forecast_request
    campaign = request.campaign
    assert request.customer_id == "5703884860"
    assert request.currency_code == "USD"
    assert campaign.language_constants == ["languageConstants/1000"]
    assert campaign.geo_target_constants == ["geoTargetConstants/21137"]
    assert (
        campaign.bidding_strategy.maximize_clicks_bidding_strategy.daily_target_spend_micros
        == 5_000_000
    )
    assert [keyword.text for keyword in campaign.ad_groups[0].keywords] == [
        "event ticketing software",
        "sell event tickets",
    ]
    assert result["network"] == "GOOGLE_SEARCH"
    assert result["metrics"] == {
        "impressions": 1200.0,
        "clicks": 84.0,
        "costMicros": 25_000_000,
    }


def test_generate_keyword_forecast_matches_installed_google_ads_schema():
    google_client = GoogleAdsClient(
        credentials=None,
        developer_token="test",
        use_proto_plus=True,
    )
    service = _FakeKeywordPlanService()

    def generate_keyword_forecast_metrics(*, request: Any) -> Any:
        service.forecast_request = request
        return SimpleNamespace(
            campaign_forecast_metrics=google_client.get_type("KeywordForecastMetrics")
        )

    service.generate_keyword_forecast_metrics = generate_keyword_forecast_metrics
    schema_client = SimpleNamespace(
        enums=google_client.enums,
        get_type=google_client.get_type,
        get_service=lambda name: service,
    )
    gateway = GoogleAdsGateway(settings=None)  # type: ignore[arg-type]
    gateway.__dict__["client"] = schema_client

    result = gateway.generate_keyword_forecast(
        customer_id="5703884860",
        keywords=["event ticketing software"],
        location_ids=["21137"],
        language_id="1000",
        match_type="PHRASE",
        network="GOOGLE_SEARCH",
        bidding_strategy="MAXIMIZE_CLICKS",
        daily_budget_micros=5_000_000,
        max_cpc_bid_micros=2_000_000,
        start_date="2030-01-01",
        end_date="2030-01-30",
        currency_code="USD",
        negative_keywords=[],
    )

    request = service.forecast_request
    assert request.campaign.geo_target_constants == ["geoTargetConstants/21137"]
    assert request.campaign.language_constants == ["languageConstants/1000"]
    assert request.campaign.ad_groups[0].keywords[0].text == "event ticketing software"
    assert result["network"] == "GOOGLE_SEARCH"


def test_generate_keyword_forecast_rejects_unsupported_v24_inputs():
    gateway = GoogleAdsGateway(settings=None)  # type: ignore[arg-type]
    fake_client = _FakePlanningClient()
    gateway.__dict__["client"] = fake_client

    common = {
        "customer_id": "5703884860",
        "keywords": ["event ticketing software"],
        "location_ids": ["21137"],
        "language_id": "1000",
        "match_type": "PHRASE",
        "bidding_strategy": "MAXIMIZE_CLICKS",
        "daily_budget_micros": 5_000_000,
        "max_cpc_bid_micros": None,
        "start_date": "2030-01-01",
        "end_date": "2030-01-30",
        "currency_code": "USD",
    }

    try:
        gateway.generate_keyword_forecast(
            **common,
            network="GOOGLE_SEARCH_AND_PARTNERS",
            negative_keywords=[],
        )
    except ValueError as exc:
        assert "GOOGLE_SEARCH only" in str(exc)
    else:
        raise AssertionError("unsupported forecast network was accepted")

    try:
        gateway.generate_keyword_forecast(
            **common,
            network="GOOGLE_SEARCH",
            negative_keywords=["jobs"],
        )
    except ValueError as exc:
        assert "negative_keywords are not supported" in str(exc)
    else:
        raise AssertionError("unsupported forecast negative keywords were accepted")
