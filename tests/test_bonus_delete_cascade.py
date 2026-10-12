"""Bonus: cascade-delete a synthetic customer without breaking the ledger."""
from __future__ import annotations

import json

from agent import ledger
from agent.privacy import delete_customer_cascade


def test_delete_customer_cascades_embedded_links_and_keeps_ledger_valid(tmp_path):
    customers_path = tmp_path / "customers.json"
    customers_path.write_text(json.dumps([
        {"customer_id": "SYN-1", "email": "synthetic@example.invalid",
         "related_tickets": [901, 902]},
        {"customer_id": "SYN-2", "email": "other@example.invalid",
         "related_tickets": [903]},
    ]), encoding="utf-8")
    ledger_path = tmp_path / "ledger.jsonl"
    ledger.append({
        "ts": "2026-10-12T00:00:00Z", "agent_id": "bonus-test",
        "run_id": "delete-cascade", "tool": "read_customer",
        "args_hash": "a" * 64, "classification": "restricted",
        "decision": "allow", "reason": "synthetic fixture for delete test",
    }, ledger_path)
    ledger_before = ledger_path.read_bytes()

    assert delete_customer_cascade("SYN-1", customers_path) is True
    remaining = json.loads(customers_path.read_text(encoding="utf-8"))
    assert remaining == [{"customer_id": "SYN-2", "email": "other@example.invalid",
                          "related_tickets": [903]}]
    assert "synthetic@example.invalid" not in customers_path.read_text(encoding="utf-8")
    assert ledger_path.read_bytes() == ledger_before
    assert ledger.verify(ledger_path) is True
    assert delete_customer_cascade("SYN-1", customers_path) is False
