"""Client-side capability pinning demo against the local MCP server."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SERVER = Path(__file__).with_name("server.py")


def _fingerprint(tool: dict) -> str:
    canonical = json.dumps(tool, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run_demo(trace_path: Path) -> dict:
    trace_path = Path(trace_path)
    trace_path.write_text("", encoding="utf-8")
    env = dict(os.environ, MCP_RUGPULL_TRACE=str(trace_path))
    process = subprocess.Popen([sys.executable, str(SERVER)], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, env=env, bufsize=1)

    def rpc(request_id: int, method: str, params: dict | None = None) -> dict:
        message = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()
        response = json.loads(process.stdout.readline())
        if response.get("id") != request_id or "error" in response:
            raise RuntimeError(f"MCP request failed: {method}")
        return response["result"]

    try:
        rpc(1, "initialize", {"protocolVersion": "2024-11-05",
                               "capabilities": {}, "clientInfo": {"name": "lab", "version": "1"}})
        assert process.stdin is not None
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        process.stdin.flush()
        original = rpc(2, "tools/list")["tools"][0]
        changed = rpc(3, "tools/list")["tools"][0]
        original_hash, changed_hash = _fingerprint(original), _fingerprint(changed)
        decision = "deny_capability_changed" if original_hash != changed_hash else "allow"
        process.stdin.close()
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()

    events = [json.loads(line)["event"] for line in trace_path.read_text(encoding="utf-8").splitlines()]
    return {"scenario": "local MCP tool rug pull", "initial_tool_hash": original_hash,
            "observed_tool_hash": changed_hash, "decision": decision,
            "tool_call_sent": "tools/call" in events, "server_events": events}


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    with tempfile.TemporaryDirectory(prefix="mcp-rugpull-") as temp_dir:
        result = run_demo(Path(temp_dir) / "server-trace.jsonl")
    rendered = json.dumps(result, ensure_ascii=False, sort_keys=True)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
