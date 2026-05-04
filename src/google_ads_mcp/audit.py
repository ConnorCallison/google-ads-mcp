from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class AuditRecord:
    id: str
    timestamp: str
    tool: str
    customer_id: str
    dry_run: bool
    request: dict[str, Any]
    response: dict[str, Any] | None = None
    error: str | None = None


class AuditLogger:
    def __init__(self, audit_dir: Path) -> None:
        self.audit_dir = audit_dir

    def write(
        self,
        *,
        tool: str,
        customer_id: str,
        dry_run: bool,
        request: dict[str, Any],
        response: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> AuditRecord:
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        record = AuditRecord(
            id=str(uuid4()),
            timestamp=datetime.now(UTC).isoformat(),
            tool=tool,
            customer_id=customer_id,
            dry_run=dry_run,
            request=request,
            response=response,
            error=error,
        )
        path = self.audit_dir / f"{datetime.now(UTC).date().isoformat()}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return record
