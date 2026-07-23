from __future__ import annotations

import pytest

from google_ads_mcp.config import Settings


def test_customer_id_normalizes_dashes(tmp_path):
    settings = Settings(
        google_ads_yaml_path=tmp_path / "google-ads.yaml",
        login_customer_id=None,
        default_customer_id=None,
        audit_dir=tmp_path / "audit",
        default_dry_run=True,
        allowed_customer_ids=set(),
        max_budget_change_pct=30,
    )

    assert settings.customer_id("123-456-7890") == "1234567890"


def test_empty_allowlist_preserves_reads_but_denies_writes(tmp_path):
    settings = Settings(
        google_ads_yaml_path=tmp_path / "google-ads.yaml",
        login_customer_id=None,
        default_customer_id=None,
        audit_dir=tmp_path / "audit",
        default_dry_run=True,
        allowed_customer_ids=set(),
        max_budget_change_pct=30,
    )

    assert settings.customer_id("123-456-7890") == "1234567890"
    with pytest.raises(ValueError, match="writes require a non-empty"):
        settings.write_customer_id("123-456-7890")


def test_customer_id_allowlist(tmp_path):
    settings = Settings(
        google_ads_yaml_path=tmp_path / "google-ads.yaml",
        login_customer_id=None,
        default_customer_id=None,
        audit_dir=tmp_path / "audit",
        default_dry_run=True,
        allowed_customer_ids={"1112223333"},
        max_budget_change_pct=30,
    )

    assert settings.write_customer_id("111-222-3333") == "1112223333"
    with pytest.raises(ValueError, match="not in GOOGLE_ADS_ALLOWED_CUSTOMER_IDS"):
        settings.write_customer_id("999-888-7777")
