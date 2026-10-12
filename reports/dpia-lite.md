# DPIA-lite — Checkpoint 5

1. **Dữ liệu và phân loại:** corpus chứa ticket và chỉ thị injection; customer store tổng hợp có customer ID, CCCD, số điện thoại, STK và email. Bài lab xem hồ sơ customer là `restricted`. Dữ liệu trong repo đều là synthetic.

2. **Mục đích và principal:** em chạy câu hỏi “Tổng hợp các ticket còn mở tuần này” để kiểm tra tổng hợp ticket và khả năng ngăn rò rỉ. Run sau containment dùng principal `dpo` mô phỏng. Cấu hình principal nằm trong `data/principals.json`; đây không phải xác thực người dùng thật.

3. **Luồng dữ liệu và nơi đi:** Run A tìm tài liệu trong `corpus/`, redact PII trong text trước khi tổng hợp và chỉ chuyển ticket ID dạng số lấy từ filename. Run B dùng ticket ID để tìm customer qua `related_tickets`, sau đó gọi `read_customer` khi policy cho phép. Egress dự kiến tới sink lab `http://127.0.0.1:10024/reconcile`; policy deny trước khi request được gửi. Sau lượt replay, `reports/attack-after.log` là 0 byte và `reports/sink.log` rỗng.

4. **Bằng chứng và giới hạn:** em chạy `python -m pytest tests/ -q`; 33 test pass. Sau đó em reset sink lần nữa, chạy CLI với `--mock --as dpo` trên cùng query, kiểm tra sink rỗng, lưu sink log thành `attack-after.log`, rồi xác minh ledger. `reports/ledger.jsonl:24` ghi `http_post` bị deny với reason và `on_behalf_of=dpo`; toàn bộ 24 dòng có reason và hash chain verify thành công. `reports/attack-before.log` ghi lần tấn công baseline với dữ liệu synthetic.

Mock chỉ mô phỏng nhận diện chỉ thị theo marker; kết quả không khẳng định model thật sẽ có cùng hành vi. Dữ liệu là synthetic, principal là fixture, sink là localhost; đây không phải đánh giá DPIA pháp lý hay bằng chứng triển khai production.
