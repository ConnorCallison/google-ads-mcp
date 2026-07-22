from __future__ import annotations

from google_ads_mcp.mcp_server import mcp


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
