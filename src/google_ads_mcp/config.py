from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _optional_digits(value: str | None) -> str | None:
    if not value:
        return None
    return "".join(ch for ch in value if ch.isdigit())


def _customer_set(value: str | None) -> set[str]:
    if not value:
        return set()
    return {_optional_digits(part) or "" for part in value.split(",") if part.strip()}


@dataclass(frozen=True)
class Settings:
    google_ads_yaml_path: Path
    login_customer_id: str | None
    default_customer_id: str | None
    audit_dir: Path
    default_dry_run: bool
    allowed_customer_ids: set[str]
    max_budget_change_pct: float

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        yaml_path = Path(os.getenv("GOOGLE_ADS_YAML_PATH", "~/google-ads.yaml")).expanduser()
        audit_dir = Path(os.getenv("GOOGLE_ADS_MCP_AUDIT_DIR", "./audit")).expanduser()
        return cls(
            google_ads_yaml_path=yaml_path,
            login_customer_id=_optional_digits(os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID")),
            default_customer_id=_optional_digits(os.getenv("GOOGLE_ADS_DEFAULT_CUSTOMER_ID")),
            audit_dir=audit_dir,
            default_dry_run=_bool(os.getenv("GOOGLE_ADS_MCP_DRY_RUN"), True),
            allowed_customer_ids=_customer_set(os.getenv("GOOGLE_ADS_ALLOWED_CUSTOMER_IDS")),
            max_budget_change_pct=float(os.getenv("GOOGLE_ADS_MAX_BUDGET_CHANGE_PCT", "30")),
        )

    def customer_id(self, customer_id: str | None) -> str:
        resolved = _optional_digits(customer_id) or self.default_customer_id
        if not resolved:
            msg = (
                "customer_id is required; pass it to the tool or set "
                "GOOGLE_ADS_DEFAULT_CUSTOMER_ID"
            )
            raise ValueError(msg)
        if self.allowed_customer_ids and resolved not in self.allowed_customer_ids:
            msg = f"customer_id {resolved} is not in GOOGLE_ADS_ALLOWED_CUSTOMER_IDS"
            raise ValueError(msg)
        return resolved
