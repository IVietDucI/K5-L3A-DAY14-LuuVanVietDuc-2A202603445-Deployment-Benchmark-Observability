# Day 14 — Mission Answers

## Part 1 — Localhost vs Production

### Exercise 1.1

Trong [app develop](01-localhost-vs-production/develop/app.py) có các vấn đề sau.

1. Dòng 17–18 đặt key và DSN trong source. Khi commit, cả lịch sử Git cũng giữ giá trị đó.
2. Dòng 33–38 in câu hỏi, key và câu trả lời ra log. Production cần log có cấu trúc, giới hạn trường dữ liệu và loại secret.
3. Dòng 21 cố định cờ debug. Việc bật dòng log chi tiết nên điều khiển bằng cấu hình môi trường.
4. Dòng 41–42 cho thấy thiếu endpoint health check. Orchestrator cần một tín hiệu để phân biệt process sống với process treo.
5. Dòng 51–52 lắng nghe trên loopback và cố định port 8000. Container cần nhận traffic trên địa chỉ có thể truy cập và dùng port được cấp.
6. Dòng 53 bật tự tải lại code. Mỗi lần phát hiện thay đổi, worker có thể bị thay thế ngoài quy trình deploy.
7. Không có lifespan hooks để khởi tạo và dọn tài nguyên theo vòng đời của app.

### Exercise 1.2–1.3

Trên WSL2, dùng cổng loopback 18000 để chạy các bản mẫu lần lượt. Bản develop nhận câu hỏi qua query, trả HTTP 200 và câu trả lời mô phỏng về Docker. Bản production nhận JSON, trả HTTP 200 ở `/ask`, `/health` và `/ready`. `/health` báo `environment=staging`, đúng với giá trị đã truyền lúc chạy.

| Thành phần | Develop | Production | Tác dụng |
|---|---|---|---|
| Cấu hình | Key, địa chỉ và port cố định | `Settings` nhận biến môi trường | Cùng image có thể chạy giữa các môi trường. |
| API | Query parameter | Body JSON với lỗi 422 khi thiếu câu hỏi | Dễ mở rộng schema đầu vào và trả lỗi rõ ràng. |
| Probe | Chỉ có route nghiệp vụ | `/health` báo process sống, `/ready` báo app sẵn sàng | Route traffic đúng thời điểm và chẩn đoán lỗi khởi động. |
| Logging | `print` kèm thông tin thô | Log sự kiện, metadata và độ dài nội dung | Có thể lọc log theo sự kiện mà giảm lộ dữ liệu. |
| Shutdown | Cấu hình cho vòng lặp sửa code local | Uvicorn và lifespan cho cleanup | Cho request đang xử lý thời gian hoàn tất. |

## Part 2 — Docker

### Exercise 2.1

1. Image develop dùng base `python:3.11`.
2. `WORKDIR /app` đặt thư mục làm việc trong container và làm gốc cho các đường dẫn tương đối tiếp theo.
3. Copy `requirements.txt` trước, cài dependencies, rồi copy source. Khi chỉ sửa source, tầng cài dependencies còn có thể dùng cache.
4. `ENTRYPOINT` xác định chương trình mặc định để chạy. `CMD` xác định lệnh mặc định khi có thể thay thế hoặc truyền tham số mặc định cho `ENTRYPOINT`.

### Exercise 2.2–2.4

Builder cài công cụ build và Python dependencies. Runtime bắt đầu từ base slim, chép các package đã cài cùng source và chạy bằng user thường. Phần giảm kích thước đến từ việc loại hệ thống build và chọn base gọn.

```text
Máy local → Nginx → FastAPI agent
                      ├── Redis
                      └── Qdrant
```

Hai cấu hình Redis và Qdrant đi theo DNS nội bộ Compose. Compose dùng health check để chờ hai dependency trước khi khởi động agent. Bản demo chỉ gọi mock LLM trong đường đi `/ask`.

| Image | Số byte từ `docker image inspect` | Kích thước `docker image ls` |
|---|---:|---:|
| `k5-day14-docker:develop` | 1667788101 | 1.67 GB |
| `k5-day14-docker:advanced` | 239815569 | 240 MB |

Image advanced giảm **85.62%** so với develop, tính theo byte. Container develop nhận `POST /ask?question=What%20is%20Docker%3F` và trả 200. Stack có đủ agent, Redis, Qdrant và Nginx. Qua Nginx ở cổng loopback `18080`, `GET /health` trả 200 với `status=ok` và `POST /ask` có JSON trả 200 với câu trả lời mock. Cổng host được đổi trong cấu hình chạy local của bài để tránh va chạm với dịch vụ khác.

## Part 3 — Cloud Deployment

### Exercise 3.1

Kết quả deploy và smoke test nằm trong [DEPLOYMENT.md](DEPLOYMENT.md).

### Exercise 3.2

Trong ví dụ ở `03-cloud-deployment/`, Railway dùng TOML cho cấu hình build và deploy của một service, với `startCommand`, `healthcheckPath` và restart policy. Render dùng Blueprint YAML để khai báo nhiều tài nguyên, gồm web service và Redis, cùng region, lệnh build/start, health check và cách cấp biến môi trường. `sync: false` yêu cầu điền secret khi cấu hình dịch vụ, còn `generateValue: true` yêu cầu nền tảng tự sinh giá trị. Với Part 6, Railway dùng Dockerfile đã chấm thử và biến môi trường của service để nối Redis.

### Exercise 3.3

1. Cloud Build cài dependencies và chạy pytest trước khi build.
2. Docker build image với tag theo commit SHA và tag `latest`, rồi push image lên registry.
3. Bước deploy dùng image gắn SHA để tạo revision Cloud Run ở `asia-southeast1` và lấy secret từ Secret Manager.
4. `service.yaml` mô tả tài nguyên, concurrency, autoscaling và hai probe chờ startup và kiểm tra liveness.

## Part 4 — API Security

### Exercise 4.1–4.3

Kết quả `curl -i` trên agent mẫu loopback với body JSON. Header mang API key và JWT được bỏ khỏi phần trích.

```http
HTTP/1.1 401 Unauthorized
content-type: application/json

{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}

HTTP/1.1 200 OK
content-type: application/json

{"question":"What is Docker?","answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}

HTTP/1.1 429 Too Many Requests
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
retry-after: 59
content-type: application/json

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```

- Bản develop dùng dependency `verify_api_key`. Thiếu key nhận 401 và thử key đúng nhận 200. Có thể xoay key qua biến môi trường và rollout lại service, sau đó cập nhật client.
- Bản production cấp JWT tại `POST /auth/token`. Sau khi đăng nhập bằng user demo trong lab, gửi token Bearer cho `/ask`. Server xác minh chữ ký và thời hạn trước khi lấy role từ token.
- Bản mẫu đếm timestamp theo user bằng cửa sổ trượt trong bộ nhớ. Tài khoản student nhận 200 ở 10 request đầu. Request 11 nhận 429 sau khi cửa sổ đầy. Role admin sử dụng limiter riêng với 100 request/phút trong cấu hình mẫu.

### Exercise 4.4

Rate limit hạn chế lưu lượng. Cost guard giới hạn tiền dựa trên số token đầu vào và đầu ra. Một thiết kế cho nhiều worker là tính phí dự kiến trước, đặt trước số tiền đó bằng thao tác Redis nguyên tử trên key theo kỳ UTC, rồi quyết toán theo token thực tế. Nếu đã hết ngân sách, từ chối với HTTP 402 trước khi gọi mock LLM. Part 6 áp dụng cơ chế này cho ngân sách toàn service. Nếu thêm ngân sách theo user, key Redis cần kèm định danh user đã được xác thực.

## Part 5 — Scaling & Reliability

### Exercise 5.1–5.3

- Khi agent mẫu đang chạy, `/health` trả 200 với `status=ok` và `/ready` trả 200 với `ready=true`. Liveness dùng cho việc phát hiện process chết. Readiness cho load balancer biết lúc nào có thể chuyển traffic.
- Gửi `POST /ask` theo query, rồi gửi SIGTERM cho process trong WSL2. Request trả 200 và log có `Graceful shutdown initiated`, `Shutdown complete` và tín hiệu 15.
- Khi nhiều instance phục vụ cùng session, Redis cho mọi instance đọc và ghi cùng key lịch sử. Lưu state mỗi instance trong RAM khiến request đi sang instance khác không thấy lịch sử cũ.

### Exercise 5.4–5.5

Chạy project Compose `k5-day14-scaling` với ba agent, một Redis và Nginx. Dùng cổng loopback `28081` và chạy cùng logic của `test_stateless.py` với URL local này. Năm request đi qua ba instance. Sau request cuối, đọc lại cùng session và thấy đủ **10 message**, gồm năm câu hỏi và năm câu trả lời.

```text
Total requests: 5
Instances used: {'instance-def7e0', 'instance-db7b22', 'instance-269351'}
Total messages: 10
```

Nginx phân phối request đến ba agent. Từng instance là stateless đối với session vì tất cả truy cập cùng Redis. Bài kiểm này xác minh lịch sử qua nhiều instance trong cùng một session.

## Part 6 — Production readiness

Chạy `python check_production_ready.py` trong Ubuntu 24.04 WSL2 với Docker Engine 29.9.3. Script đo image **247 MB** và Docker stop **1,0 giây**, exit code **0**. Khi Redis ngắt kết nối, `/health` vẫn 200 và `/ready` trả 503. Rate limit tiếp tục trả 429 sau khi khởi động lại agent. Ngân sách kiểm thử nhỏ dẫn đến 402 ở request đầu.

```text
📋 Checklist Deliverable
   ✅ Dockerfile (multi-stage, < 500 MB)
   ✅ docker-compose.yml (agent + redis)
   ✅ .dockerignore
   ✅ Health check endpoint (GET /health)
   ✅ Readiness endpoint (GET /ready)
   ✅ API Key authentication
   ✅ Rate limiting
   ✅ Cost guard
   ✅ Config từ environment variables
   ✅ Structured logging
   ✅ Graceful shutdown
   ✅ Public URL ready (Railway / Render config)
Result: 12/12 tiêu chí đạt · 41/41 checks passed
🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
```

## Tự chấm theo RUBRIC.md

| Hạng mục | Điểm tự chấm | Bằng chứng |
|---|---:|---|
| Part 1 | 8/8 | Anti-pattern, HTTP 200 và bảng develop/production. |
| Part 2 | 8/8 | Hai image đã build, số byte thật và test qua Nginx. |
| Part 3 | 8/8 | Railway public, so sánh Render và mô tả Cloud Run. |
| Part 4 | 8/8 | API key và JWT, output 401/200/429, thiết kế cost guard. |
| Part 5 | 8/8 | Probes, SIGTERM và history 10 message qua ba replica. |
| Part 6 | 60/60 | PASS 12/12, 41/41 phép kiểm, URL và ảnh deploy. |
| Part 7 | 20/20 | 10 JSON, hai CSV, Grafana, hai trace cùng log và hai alert firing. |
| **Tổng** | **120/120** | **Quy đổi 100/100, điểm tự chấm.** |

## AI log

- Yêu cầu AI đối chiếu README, giáo trình PDF và rubric K5, rồi lập kế hoạch, triển khai và tự kiểm bài lab trong repo.
- Codex viết các phần TODO của Part 6 và chạy script chấm gốc trong WSL2. Codex chạy các ví dụ để lấy mã HTTP và thực hiện eval trước và sau khi cập nhật knowledge base. Benchmark và ảnh dùng kết quả thiết bị chạy lab.
- Có thể tái kiểm bằng các lệnh trong `CHECKPOINTS.md`, file JSON/CSV đã nộp và URL ghi trong `DEPLOYMENT.md` sau khi xác nhận deploy.
