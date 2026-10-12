# Bonus evidence

## OPA / Rego — policy port

Em chuyển các điều kiện chính của `agent.policy.check()` sang `bonus/opa/policy.rego`, giữ `data/principals.json` làm registry mô phỏng. `tests/test_bonus_opa.py` gọi OPA CLI thật, không thay engine bằng mock. `opa check --strict bonus/opa/policy.rego` thành công; cả 5 trường hợp đều pass: tìm kiếm hợp lệ, DPO đọc customer hợp lệ, restricted egress bị deny, quyền hết hạn bị deny và delegated scope không vượt parent scope.

Binary OPA 1.21.2 được tải từ nguồn chính thức, kiểm SHA-256 với sidecar chính thức rồi mới chạy. Không thêm dependency/model vào repo.

## MCP rug pull — local stdio

`bonus/mcp_rug_pull/server.py` chạy local qua stdio và thực hiện handshake MCP JSON-RPC, sau đó trả tool `lookup_ticket` với mô tả/schema ban đầu rồi đổi mô tả/schema ở lần `tools/list` tiếp theo. Client trong `demo.py` so fingerprint, phát hiện thay đổi và deny trước `tools/call`. `tests/test_bonus_mcp_rug_pull.py` pass; trace `reports/bonus-mcp-rug-pull.jsonl` cho thấy chỉ có initialize và hai lần list, không có tool call. Không dùng mạng hay server bên ngoài.

## Delete cascade — ledger giữ nguyên

`agent/privacy.py` xóa record customer cùng các liên kết `related_tickets` nằm trong record và thay file atomically. Test chỉ dùng store synthetic tạm: xác nhận record/PII mục tiêu biến mất, record khác còn nguyên, ledger không bị sửa và `ledger.verify()` vẫn thành công. Test pass; không xóa dữ liệu trong `data/customers.json` thật của bài lab.

## Kiểm tra tổng hợp

`python -m pytest tests/ -q -p no:cacheprovider` với OPA được trỏ qua `OPA_BIN`; kết quả **40 passed**. Ba bonus có test riêng. GLiNER không được cài hoặc chạy theo phạm vi đã thống nhất.
