# Verification — Checkpoint 3

## Môi trường

- Python: 3.12.14

## Checkpoint 3a — PII gate

Lệnh đã chạy: `python -m pytest tests/test_pii.py -v -s -p no:cacheprovider` để kiểm tra cả nhận diện lẫn redact trên bộ `tests/vn_pii_testset.jsonl`. Test so sánh các span dự đoán với nhãn có sẵn và in precision/recall.

Kết quả: gold=118, pred=118, true positive=118; precision=1.000, recall=1.000. Cả 2 test đều pass. Regex ưu tiên email và STK có nhãn trước CCCD/SĐT để hạn chế nhận nhầm cùng một chuỗi số thành nhiều loại. `redact()` thay entity từ cuối văn bản về đầu để các offset còn chính xác.

## Checkpoint 3b — Policy

Lệnh chạy: `python -m pytest tests/test_policy.py -v -p no:cacheprovider`. Bộ test xác nhận `restricted` đi cùng egress luôn bị deny, kể cả principal được phép; các trường hợp public/internal hợp lệ vẫn được allow. Policy kiểm principal từ `data/principals.json`, purpose, scope, parent scope và thời hạn. Mọi kết quả trả về đều có reason.

Kết quả: 4/4 test pass.

## Checkpoint 3c — OBO

Em chạy `python -m pytest tests/test_obo.py -v -p no:cacheprovider`. Ngoài việc kiểm policy trực tiếp, test theo dõi lời gọi `read_customer`: `support_l1` không được đọc hồ sơ, còn `dpo` đọc được khách hợp lệ. Test cũng thử unknown principal, hết hạn và delegated scope vượt quyền cha.

Trong runner, em kiểm tra quyền trước khi mở nguồn mapping khách hàng và kiểm tra lại ngay trước từng lần gọi `read_customer`. Ledger ghi principal đại diện cùng `agent_id`, `run_id` và `expires_at`.

Kết quả: 5/5 test pass. Principal trong lab là cấu hình mô phỏng; kết quả này không chứng minh hệ thống đã xác thực danh tính production.

## Checkpoint 3d — Trifecta split

Lệnh chạy `python -m pytest tests/test_split.py -v -p no:cacheprovider`. Test tạm đặt một lure nhắc `KH-000777`, theo dõi các customer ID mà runner thật sự đọc, rồi xác nhận agent vẫn đọc được khách hợp lệ gắn với ticket. Test fixture cất các lure khác ra ngoài corpus trong lúc chạy và khôi phục chúng sau đó.

Run A tìm tài liệu và chỉ chuyển các ticket ID dạng số lấy từ tên file. Run B map các ID đó qua `related_tickets`; customer ID và URL trong nội dung attacker không được dùng để chọn hồ sơ. Khi có dữ liệu restricted, policy deny egress trước khi `http_post` chạy.

Kết quả: test split pass; `KH-000777` không bị đọc và chức năng đọc khách hợp lệ vẫn hoạt động.

## Checkpoint 3e — Ledger

Lệnh chạy `python -m pytest tests/test_ledger.py -v -p no:cacheprovider`. Test ghi hai entry để kiểm tra `prev_hash` và hash của từng dòng, sửa một dòng cũ mà không tính lại hash rồi gọi `verify()`, và thử entry thiếu reason.

Kết quả: 3/3 test pass. Hash chain phát hiện sửa nội dung còn trong file, nhưng không phát hiện việc cắt dòng cuối hoặc viết lại toàn bộ chuỗi nếu không có mốc tin cậy bên ngoài.

## Kiểm tra tích hợp injection

Chạy `python -m pytest tests/test_injection.py -v -p no:cacheprovider`. Test lần lượt cô lập từng lure và chạy với `support_l1` lẫn `dpo` (4 biến thể × 2 principal). Nó kiểm tra sink không nhận PII, mọi quyết định ledger có reason, và không có lần POST nào thiếu decision allow tương ứng. Mỗi test dùng sink riêng của fixture và tự reset log.

Kết quả: 8/8 trường hợp pass. Đây là test containment; `reports/attack-before.log` từ checkpoint 2 được giữ nguyên. `attack-after.log` và ledger evidence chính thức sẽ được tạo ở checkpoint 5.

## Cách chạy trong môi trường bị giới hạn

Em dùng Python 3.12.14 và các package `requests` 2.34.2, `pytest` 9.1.1 cùng dependency. Test PII chạy trong sandbox và pass. Lượt đầu chạy test tích hợp trong sandbox bị macOS trả `PermissionError` khi fixture bind sink tại `127.0.0.1:10024`; do đó 13 test tích hợp báo lỗi ở bước setup sink, chưa thực thi phần test. Em chạy lại cùng nhóm test với quyền mở sink localhost và thư mục tạm tại `/private/tmp`; lượt đó pass đủ 21/21 test.

Các lệnh chạy tương đương:

```bash
python -m pytest tests/test_pii.py -v -s -p no:cacheprovider
python -m pytest tests/test_policy.py tests/test_obo.py tests/test_split.py \
  tests/test_ledger.py tests/test_injection.py -v -p no:cacheprovider
```

Test ledger dùng đường dẫn tạm; test runner dùng ledger trong `tmp_path`. Các test reset sink trong fixture. Vì vậy những lượt này không ghi đè `reports/ledger.jsonl` hoặc log before đã nộp.

## Những phần chưa chạy

Checkpoint 4 (Gitleaks, pre-commit và dependency hash lock) và checkpoint 5 (full suite, replay tạo `attack-after.log`, compliance mapping, DPIA-lite) chưa thực hiện. Chưa chạy `pre-commit` hoặc Gitleaks trong phần thực hiện checkpoint 3.

## Lỗi còn lại

Lượt test tích hợp đầu tiên bị sandbox chặn bind sink như mô tả ở trên. Sau khi chạy lại trong quyền cho phép localhost, các test thuộc checkpoint 3 đều pass.

## Checkpoint 4 — Supply chain và secrets

Em dùng Gitleaks v8.30.1 trên macOS arm64. Em chạy `gitleaks git --config .gitleaks.toml --redact --verbose .` để quét lịch sử: scanner tìm một finding với rule `lab24-synthetic-token` trong `lab-fake-secret.txt`, commit `1bdd849922156c868a5ee9293d68f5b72e242d2c`; lệnh trả exit status 1 như dự kiến. Giá trị token đã được redacted. Sau đó em chạy `gitleaks dir --config .gitleaks.toml .`; working tree hiện tại sạch, exit status 0.

Em tạo `requirements.lock` bằng pip-tools 7.6.2 với `--generate-hashes`, kiểm tra mỗi package có SHA-256, rồi cài thành công bằng `pip install --require-hashes -r requirements.lock` vào thư mục kiểm tra tạm. Lock chứa 10 package. Em cấu hình hook `gitleaks-system` ở `.pre-commit-config.yaml`, pin `v8.30.1`, đặt `pass_filenames: false`, rồi chạy `pre-commit run --all-files`; hook Passed. Cuối cùng em chạy `python -m pytest tests/test_supply_chain.py -v -p no:cacheprovider`; kết quả: 3/3 test pass.
