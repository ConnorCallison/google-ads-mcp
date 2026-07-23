from __future__ import annotations

from types import SimpleNamespace

import pytest

from google_ads_mcp import mcp_server
from google_ads_mcp.config import Settings
from google_ads_mcp.mcp_server import mcp


class _FakeAudit:
    def __init__(self, events: list[tuple[str, str, str]], fail_status: str | None = None) -> None:
        self.events = events
        self.fail_status = fail_status

    def write(self, *, status: str, audit_id: str | None = None, **_kwargs):
        resolved_audit_id = audit_id or "audit-123"
        self.events.append(("audit", status, resolved_audit_id))
        if status == self.fail_status:
            raise OSError(f"{status} audit unavailable")
        return SimpleNamespace(id=resolved_audit_id)


def _settings(tmp_path, *, allowed_customer_ids: set[str]) -> Settings:
    return Settings(
        google_ads_yaml_path=tmp_path / "google-ads.yaml",
        login_customer_id=None,
        default_customer_id=None,
        audit_dir=tmp_path / "audit",
        default_dry_run=True,
        allowed_customer_ids=allowed_customer_ids,
        max_budget_change_pct=30,
    )


def test_conversion_goal_tool_schemas_require_explicit_targets_and_default_to_dry_run():
    primary_tool = mcp._tool_manager._tools["set_conversion_action_primary_for_goal"]
    primary_schema = primary_tool.parameters
    assert primary_schema["required"] == [
        "customer_id",
        "conversion_action_id",
        "primary_for_goal",
    ]
    assert primary_schema["properties"]["dry_run"]["default"] is True
    assert primary_schema["properties"]["conversion_action_id"]["pattern"] == "^[0-9]+$"

    goal_tool = mcp._tool_manager._tools["set_customer_conversion_goal_biddable"]
    goal_schema = goal_tool.parameters
    assert goal_schema["required"] == [
        "customer_id",
        "category",
        "origin",
        "biddable",
    ]
    assert goal_schema["properties"]["dry_run"]["default"] is True
    assert "PURCHASE" in goal_schema["properties"]["category"]["enum"]
    assert "UNKNOWN" not in goal_schema["properties"]["category"]["enum"]
    assert goal_schema["properties"]["origin"]["enum"] == [
        "APP",
        "CALL_FROM_ADS",
        "GOOGLE_HOSTED",
        "STORE",
        "WEBSITE",
        "YOUTUBE_HOSTED",
    ]


@pytest.mark.parametrize(
    "write_call",
    [
        lambda: mcp_server.set_campaign_budget("1234567890", "1", 1_000_000),
        lambda: mcp_server.set_campaign_status("1234567890", "1", "PAUSED"),
        lambda: mcp_server.set_conversion_action_primary_for_goal("1234567890", "1", False),
        lambda: mcp_server.set_customer_conversion_goal_biddable(
            "1234567890", "PURCHASE", "WEBSITE", False
        ),
        lambda: mcp_server.add_campaign_negative_keyword("1234567890", "1", "free", "EXACT"),
        lambda: mcp_server.apply_recommendation("1234567890", "1"),
    ],
)
def test_every_write_tool_fails_closed_without_allowlist(monkeypatch, tmp_path, write_call):
    monkeypatch.setattr(
        mcp_server,
        "settings",
        _settings(tmp_path, allowed_customer_ids=set()),
    )

    with pytest.raises(ValueError, match="writes require a non-empty"):
        write_call()


def test_read_tool_remains_available_without_allowlist(monkeypatch, tmp_path):
    monkeypatch.setattr(
        mcp_server,
        "settings",
        _settings(tmp_path, allowed_customer_ids=set()),
    )
    gateway = SimpleNamespace(
        search=lambda **kwargs: [
            {
                "customerId": kwargs["customer_id"],
                "query": kwargs["query"],
                "limit": kwargs["limit"],
            }
        ]
    )
    monkeypatch.setattr(mcp_server, "gateway", gateway)

    assert mcp_server.search_google_ads("123-456-7890", "SELECT customer.id", 1) == [
        {
            "customerId": "1234567890",
            "query": "SELECT customer.id",
            "limit": 1,
        }
    ]


def test_recorded_write_persists_started_before_action_and_reuses_audit_id(monkeypatch):
    events: list[tuple[str, str, str]] = []
    monkeypatch.setattr(mcp_server, "audit", _FakeAudit(events))

    def action():
        events.append(("action", "called", ""))
        return {"resource_names": ["customers/1/example/2"]}

    result = mcp_server._recorded_write(
        tool="example",
        customer_id="1",
        dry_run=False,
        request={"target": "2"},
        action=action,
    )

    assert events == [
        ("audit", "started", "audit-123"),
        ("action", "called", ""),
        ("audit", "succeeded", "audit-123"),
    ]
    assert result == {
        "audit_id": "audit-123",
        "resource_names": ["customers/1/example/2"],
    }


def test_recorded_write_records_terminal_failure_with_started_audit_id(monkeypatch):
    events: list[tuple[str, str, str]] = []
    monkeypatch.setattr(mcp_server, "audit", _FakeAudit(events))

    def action():
        events.append(("action", "called", ""))
        raise ValueError("provider rejected request")

    with pytest.raises(RuntimeError, match=r"provider rejected request \(audit_id=audit-123\)"):
        mcp_server._recorded_write(
            tool="example",
            customer_id="1",
            dry_run=True,
            request={"target": "2"},
            action=action,
        )

    assert events == [
        ("audit", "started", "audit-123"),
        ("action", "called", ""),
        ("audit", "failed", "audit-123"),
    ]


def test_recorded_write_does_not_call_provider_when_started_audit_fails(monkeypatch):
    events: list[tuple[str, str, str]] = []
    monkeypatch.setattr(mcp_server, "audit", _FakeAudit(events, fail_status="started"))

    def action():
        events.append(("action", "called", ""))
        return {}

    with pytest.raises(OSError, match="started audit unavailable"):
        mcp_server._recorded_write(
            tool="example",
            customer_id="1",
            dry_run=False,
            request={"target": "2"},
            action=action,
        )

    assert events == [("audit", "started", "audit-123")]


def test_recorded_write_reports_terminal_audit_failure_after_success(monkeypatch):
    events: list[tuple[str, str, str]] = []
    monkeypatch.setattr(mcp_server, "audit", _FakeAudit(events, fail_status="succeeded"))

    def action():
        events.append(("action", "called", ""))
        return {}

    with pytest.raises(
        RuntimeError,
        match="external action succeeded but terminal audit write failed "
        r"\(audit_id=audit-123\)",
    ):
        mcp_server._recorded_write(
            tool="example",
            customer_id="1",
            dry_run=False,
            request={"target": "2"},
            action=action,
        )

    assert events == [
        ("audit", "started", "audit-123"),
        ("action", "called", ""),
        ("audit", "succeeded", "audit-123"),
    ]
