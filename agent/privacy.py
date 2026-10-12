"""Small, auditable cascade deletion helper for the synthetic lab store."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def delete_customer_cascade(customer_id: str, customers_path: Path) -> bool:
    """Delete a customer record and its embedded related-ticket links.

    The source store is atomically replaced. The append-only audit ledger is
    deliberately not modified: it contains argument hashes, not raw PII, and
    remains independently verifiable after the data deletion.
    """
    path = Path(customers_path)
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("customer store must be a JSON list")
    remaining = [row for row in records if row.get("customer_id") != customer_id]
    if len(remaining) == len(records):
        return False

    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(remaining, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return True
