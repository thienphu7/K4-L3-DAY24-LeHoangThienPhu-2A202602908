"""Checkpoint 3c/3d — on-behalf-of authorization and trifecta split.

Đọc CHECKPOINTS.md (§3c) trước khi viết code. Tóm tắt yêu cầu:

Tách 1 yêu cầu người dùng thành ít nhất 2 run riêng biệt — KHÔNG run nào
được cầm cả 3 chân của trifecta cùng lúc:

    Run A: gọi search_docs (untrusted content).
           KHÔNG gọi read_customer. KHÔNG gọi http_post.
    Run B: gọi read_customer (private data).
           CHỈ nhận input là TYPED, ĐÃ SANITIZE từ Run A — ví dụ
           list[int] ticket id trích từ TÊN FILE (vd "ticket-007.md" -> 7),
           KHÔNG BAO GIỜ nhận nguyên văn text của document. free text của
           attacker không được đi xa hơn Run A.

Mọi lần gọi tool (allow HAY deny) phải:
  1. Đi qua `agent.policy.check()` TRƯỚC KHI tool thật sự chạy.
  2. Được ghi vào ledger qua `agent.ledger.append()` — cả khi deny.
Nếu policy deny, KHÔNG được gọi tool đó.

--- Gợi ý kiến trúc (không bắt buộc theo đúng, nhưng đủ để làm trong 13') ---

data/customers.json có field `related_tickets: list[int]` cho mỗi khách
hàng — đây là NGUỒN TIN CẬY để map ticket_id -> customer_id, KHÔNG map qua
customer_id mà attacker nhúng trong nội dung document. Cụ thể:

    Run A: search_docs(message) -> lấy list[int] ticket_id từ TÊN FILE của
           các doc khớp (vd "ticket-999.md" -> 999). Cũng chạy
           llm.find_injection() trên text để log lại (KHÔNG dùng
           customer_id mà nó trả về).
    Run B: với mỗi ticket_id nhận từ Run A, tìm customer nào trong
           customers.json có ticket_id trong related_tickets, rồi
           read_customer(customer_id) đó — không phải customer_id lấy từ
           text tự do.

Vì sao cách này chống được một chỉ thị viết không dấu / lookalike: filter
chuỗi thô sẽ luôn có thể bị né bằng cách viết lại chỉ thị, nhưng nếu Run B
không bao giờ ĐỌC free text để quyết định gọi ai, thì việc né filter chuỗi
trở nên vô nghĩa — đây là containment (kiến trúc), khác với mitigation
(bộ lọc). Sinh viên NÊN thử filter chuỗi trước, rồi tự phá nó bằng
một bản viết lại không dấu của lure, trước khi chuyển sang cách này.

Interface bắt buộc (agent/loop.py import và gọi hàm này nếu tồn tại):

    handle(message: str, llm, log_dir: pathlib.Path | None = None,
           principal_id: str = "support_l1") -> str
        `llm` cung cấp:
            llm.find_injection(text: str) -> InjectedInstruction | None
            llm.summarize(docs: list[dict]) -> str
        `log_dir` là thư mục chứa ledger.jsonl (mặc định: reports/).
        Mỗi tool call truyền principal_id, requested_tool, agent_scopes,
        parent_scopes và expires_at vào PolicyContext; ledger ghi
        on_behalf_of = principal_id, agent_id, run_id, expires_at.
        Principal chỉ được tra trong data/principals.json. Run B không
        được đọc customer cho support_l1; dpo vẫn đọc được khách hợp lệ.
        Trả về câu trả lời cuối cùng hiển thị cho người dùng — hành vi
        quan sát được từ ngoài (CLI) không đổi so với trước khi contain,
        chỉ có sink log và ledger là khác.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from agent import ledger, pii, policy, tools

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
DEFAULT_LEDGER_PATH = REPORTS_DIR / "ledger.jsonl"


ROOT_SCOPES = ("search_docs", "read_customer")
TICKET_FILENAME = re.compile(r"ticket-([0-9]+)(?:b)?\.md")


@dataclass(frozen=True)
class RunContext:
    principal_id: str
    agent_id: str
    run_id: str
    scopes: tuple[str, ...]
    parent_scopes: tuple[str, ...]
    expires_at: str
    ledger_path: Path


def _args_hash(args: dict) -> str:
    encoded = json.dumps(args, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _gate(run: RunContext, tool: str, args: dict, classification: str,
          purpose: str, egress: bool = False) -> bool:
    context = policy.PolicyContext(
        data_classification=classification,
        request_purpose=purpose,
        agent_owner=run.agent_id,
        delegation_depth=1,
        egress_enabled=egress,
        principal_id=run.principal_id,
        requested_tool=tool,
        agent_scopes=run.scopes,
        parent_scopes=run.parent_scopes,
        expires_at=run.expires_at,
    )
    allowed, reason = policy.check(context)
    if not isinstance(reason, str) or not reason.strip():
        raise RuntimeError("policy returned an empty reason")
    ledger.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "on_behalf_of": run.principal_id,
        "agent_id": run.agent_id,
        "run_id": run.run_id,
        "expires_at": run.expires_at,
        "tool": tool,
        "args_hash": _args_hash(args),
        "classification": classification,
        "decision": "allow" if allowed else "deny",
        "reason": reason,
    }, run.ledger_path)
    return allowed


def _run_a(message: str, llm, run: RunContext) -> tuple[list[int], str]:
    if not _gate(run, "search_docs", {"query": message}, "internal", "summarize-tickets"):
        return [], "Không được phép tìm kiếm ticket."
    docs = tools.search_docs(message)
    # Inspection stays in Run A. Attacker-selected IDs and URLs are discarded.
    llm.find_injection("\n\n".join(doc["text"] for doc in docs))
    sanitized_docs = [{"id": doc["id"], "text": pii.redact(doc["text"])} for doc in docs]
    ticket_ids = set()
    for doc in sanitized_docs:
        match = TICKET_FILENAME.fullmatch(doc["id"])
        if match:
            ticket_ids.add(int(match.group(1)))
    return sorted(ticket_ids), llm.summarize(sanitized_docs)


def _run_b(ticket_ids: list[int], run: RunContext) -> None:
    if not ticket_ids:
        return
    if any(type(ticket_id) is not int for ticket_id in ticket_ids):
        raise ValueError("Run B only accepts integer ticket IDs")
    # The mapping is stored beside private records: authorize before opening it.
    if not _gate(run, "read_customer", {"ticket_ids": ticket_ids, "phase": "trusted-mapping"},
                 "restricted", "support-reply"):
        return
    customers = json.loads(tools.CUSTOMERS_FILE.read_text(encoding="utf-8"))
    selected_tickets = set(ticket_ids)
    customer_ids = sorted({
        record["customer_id"] for record in customers
        if selected_tickets.intersection(record.get("related_tickets", []))
    })
    del customers
    records = []
    for customer_id in customer_ids:
        if _gate(run, "read_customer", {"customer_id": customer_id}, "restricted", "support-reply"):
            records.append(tools.read_customer(customer_id))
    if records:
        url = "http://127.0.0.1:10024/reconcile"
        body = {"records": records}
        if _gate(run, "http_post", {"url": url, "body": body}, "restricted", "support-reply", egress=True):
            tools.http_post(url, body)


def handle(message: str, llm, log_dir: Path | None = None,
           principal_id: str = "support_l1") -> str:
    ledger_path = Path(log_dir) / "ledger.jsonl" if log_dir is not None else DEFAULT_LEDGER_PATH
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    run_a = RunContext(
        principal_id=principal_id,
        agent_id="lab24-agent/run-a",
        run_id=str(uuid4()),
        scopes=("search_docs",),
        parent_scopes=ROOT_SCOPES,
        expires_at=expires_at,
        ledger_path=ledger_path,
    )
    run_b = RunContext(
        principal_id=principal_id,
        agent_id="lab24-agent/run-b",
        run_id=str(uuid4()),
        scopes=("read_customer",),
        parent_scopes=ROOT_SCOPES,
        expires_at=expires_at,
        ledger_path=ledger_path,
    )
    ticket_ids, summary = _run_a(message, llm, run_a)
    _run_b(ticket_ids, run_b)
    return summary
