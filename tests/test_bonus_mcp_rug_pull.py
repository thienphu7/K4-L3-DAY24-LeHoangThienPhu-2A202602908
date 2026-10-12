"""Bonus: exercise a local JSON-RPC MCP stdio rug pull and refuse the call."""
from __future__ import annotations

import json

from bonus.mcp_rug_pull.demo import run_demo


def test_client_detects_changed_tool_before_calling_it(tmp_path):
    trace = tmp_path / "server-trace.jsonl"
    result = run_demo(trace)
    assert result["decision"] == "deny_capability_changed"
    assert result["initial_tool_hash"] != result["observed_tool_hash"]
    assert result["tool_call_sent"] is False
    events = [json.loads(line)["event"] for line in trace.read_text(encoding="utf-8").splitlines()]
    assert events == ["initialize", "tools/list", "tools/list"]
