from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

AuditStatus = Literal["started", "succeeded", "failed"]


@dataclass(frozen=True)
class AuditRecord:
    id: str
    timestamp: str
    status: AuditStatus
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
        status: AuditStatus,
        audit_id: str | None = None,
        response: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> AuditRecord:
        if status == "started":
            if audit_id is not None:
                raise ValueError("started audit records must allocate their own audit ID")
            if response is not None or error is not None:
                raise ValueError("started audit records cannot contain a response or error")
            resolved_audit_id = str(uuid4())
        else:
            if not audit_id:
                raise ValueError("terminal audit records require the started audit ID")
            resolved_audit_id = audit_id
        if status == "succeeded" and error is not None:
            raise ValueError("succeeded audit records cannot contain an error")
        if status == "failed" and error is None:
            raise ValueError("failed audit records require an error")

        self.audit_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(UTC)
        record = AuditRecord(
            id=resolved_audit_id,
            timestamp=now.isoformat(),
            status=status,
            tool=tool,
            customer_id=customer_id,
            dry_run=dry_run,
            request=request,
            response=response,
            error=error,
        )
        path = self.audit_dir / f"{now.date().isoformat()}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return record
