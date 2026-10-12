# Checkpoint 1 — Baseline

1. Agent chưa có identity riêng cho mỗi run: `_naive_loop()` trong `agent/loop.py:27` chỉ nhận message và LLM, không tạo `agent_id`, `run_id` hay kiểm tra principal, và dù `run_once()` nhận `principal_id` thì nhánh baseline tại dòng 74 cũng không truyền thông tin này vào.

2. Chưa có policy quyết định ai được phép gọi `http_post`: khi tìm thấy chỉ thị injection và đọc được customer, `_naive_loop()` gọi thẳng tool tại `agent/loop.py:44`, còn `http_post()` trong `agent/tools.py:76–84` chỉ kiểm tra đích gửi thuộc localhost rồi POST dữ liệu, không kiểm tra quyền của người dùng hay mức độ nhạy cảm của record.

3. Bằng chứng dữ liệu đã tới sink nằm trong `reports/sink.log`, vì `Handler.do_POST()` trong `sink/sink.py:42–47` ghi đường dẫn và body của request vào file này.
