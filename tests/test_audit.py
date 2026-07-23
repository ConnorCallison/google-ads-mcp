from __future__ import annotations

import json

from google_ads_mcp.audit import AuditLogger


def test_audit_lifecycle_reuses_stable_id(tmp_path):
    logger = AuditLogger(tmp_path)
    request = {"target": "2"}

    started = logger.write(
        tool="example",
        customer_id="1",
        dry_run=False,
        request=request,
        status="started",
    )
    succeeded = logger.write(
        tool="example",
        customer_id="1",
        dry_run=False,
        request=request,
        status="succeeded",
        audit_id=started.id,
        response={"resource_names": ["customers/1/example/2"]},
    )

    records = [
        json.loads(line)
        for path in tmp_path.glob("*.jsonl")
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    assert succeeded.id == started.id
    assert [record["status"] for record in records] == ["started", "succeeded"]
    assert {record["id"] for record in records} == {started.id}
