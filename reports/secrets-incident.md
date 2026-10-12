# Secret giả trong lịch sử Git — Checkpoint 4

## Quét lịch sử

Em dùng Gitleaks v8.30.1 với cấu hình `.gitleaks.toml` và chạy:

```bash
gitleaks git --config .gitleaks.toml --redact --verbose .
```

Scanner báo đúng một finding: rule `lab24-synthetic-token`, file `lab-fake-secret.txt`, dòng 1, commit `1bdd849922156c868a5ee9293d68f5b72e242d2c`. Exit status là 1 vì có finding. Giá trị token đã được redacted và không được chép vào báo cáo. Đây là token giả, vô hiệu, được cài sẵn trong lịch sử cho bài lab; finding này là bằng chứng checkpoint chứ không phải credential thật.

## Quét working tree hiện tại

Em chạy:

```bash
gitleaks dir --config .gitleaks.toml .
```

Kết quả: scanner quét khoảng 149.95 KB, không tìm thấy leak và trả exit status 0.

## Dependency và hook

Em sinh `requirements.lock` từ `requirements.txt` bằng pip-tools 7.6.2 và `--generate-hashes`. Lock ghim 10 package, mỗi package có SHA-256. Sau đó em cài vào thư mục kiểm tra tạm bằng:

```bash
python -m pip install --require-hashes --target <thư-mục-tạm> -r requirements.lock
```

Cài đặt thành công. Em thêm hook `gitleaks-system` từ repository chính thức, pin `rev: v8.30.1`, đặt `pass_filenames: false`, rồi chạy `pre-commit run --all-files`. Hook hoàn tất với kết quả Passed.

## Cách xử lý nếu đây là secret thật

Nếu giá trị trong finding là credential thật, cần thu hồi hoặc rotate ngay và kiểm tra nơi credential đã được dùng. Xóa file khỏi HEAD không xóa các commit cũ, nên giá trị vẫn có thể được tìm trong Git history. Pin dependency và thêm hook giúp phát hiện hoặc ngăn một số lần lộ tiếp theo, nhưng không làm credential đã lộ mất hiệu lực.
