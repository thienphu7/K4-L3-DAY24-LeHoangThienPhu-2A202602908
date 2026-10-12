"""Bonus: parity checks against the real OPA CLI (not a Python policy mock)."""
from __future__ import annotations

import os
import shutil

import pytest

from bonus.opa.evaluate import evaluate


OPA = os.environ.get("OPA_BIN") or shutil.which("opa")
pytestmark = pytest.mark.skipif(not OPA, reason="OPA binary is not installed")


def _context(**overrides):
    context = {
        "data_classification": "internal", "request_purpose": "summarize-tickets",
        "agent_owner": "lab24-agent/run-a", "delegation_depth": 0,
        "egress_enabled": False, "principal_id": "support_l1",
        "requested_tool": "search_docs",
        "agent_scopes": ["search_docs", "read_customer", "http_post"],
        "parent_scopes": [], "expires_at": "2099-01-01T00:00:00Z",
    }
    context.update(overrides)
    return context


def test_opa_allows_valid_scoped_search():
    result = evaluate(_context(), OPA)
    assert result["allow"] is True and result["reason"]


def test_opa_keeps_dpo_read_customer_functionality():
    result = evaluate(_context(principal_id="dpo", request_purpose="support-reply",
                               requested_tool="read_customer"), OPA)
    assert result["allow"] is True and result["reason"]


def test_opa_denies_restricted_egress_even_for_dpo():
    result = evaluate(_context(data_classification="restricted", egress_enabled=True,
                               request_purpose="support-reply", principal_id="dpo",
                               requested_tool="http_post"), OPA)
    assert result["allow"] is False
    assert "restricted data cannot leave through egress" in result["reason"]


def test_opa_denies_expired_authorization():
    result = evaluate(_context(expires_at="2000-01-01T00:00:00Z"), OPA)
    assert result["allow"] is False
    assert "expired or invalid" in result["reason"]


def test_opa_denies_tool_outside_parent_scope():
    result = evaluate(_context(principal_id="dpo", request_purpose="support-reply",
                               requested_tool="read_customer", delegation_depth=1,
                               parent_scopes=["search_docs"]), OPA)
    assert result["allow"] is False
    assert "tool outside effective delegated scopes" in result["reason"]
