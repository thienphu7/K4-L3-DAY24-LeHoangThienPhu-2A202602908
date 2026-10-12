"""Invoke the actual OPA CLI against the lab's trusted principal registry."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POLICY = Path(__file__).with_name("policy.rego")


def evaluate(context: dict, opa_binary: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="opa-lab24-") as temporary:
        data_path = Path(temporary) / "principals.json"
        data_path.write_text(json.dumps({"principals": json.loads(
            (ROOT / "data" / "principals.json").read_text(encoding="utf-8"))}),
            encoding="utf-8")
        completed = subprocess.run(
            [opa_binary, "eval", "--format=json", "--data", str(POLICY),
             "--data", str(data_path), "--input", "/dev/stdin",
             "data.lab24.authz.result"],
            input=json.dumps(context), capture_output=True, text=True, check=True,
        )
    document = json.loads(completed.stdout)
    return document["result"][0]["expressions"][0]["value"]
