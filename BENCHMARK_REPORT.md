# Benchmark & Observability Report — Day 14

**Họ tên** Luu Van Viet Duc

**Ngày chạy** 25/11/2026 (GMT+7)

**Môi trường** Windows, Ubuntu 24.04 WSL2, Python 3.12.3, Docker Engine 29.9.3, Compose 5.7.0.

## 1. SLO của agent

| SLI | SLO | Lý do chọn |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Đo trải nghiệm ở phần cuối phân bố latency và dùng ngưỡng mặc định của `load_test.py`. |
| Error rate `/ask` | ≤ 2% | Giới hạn tỷ lệ request thất bại, kể cả khi mock upstream thỉnh thoảng báo 503. |
| Accuracy golden dataset | 100% cho v2 đã sửa và 0 regression | Quality gate cho bộ 23 câu cố định. |

## 2. Benchmark hiệu năng

### 2.1 Concurrency vs latency (agent v2)

Mỗi mức dùng 300 request đến cùng agent local. Percentile tính trên request HTTP 200, còn error rate tính trên toàn bộ request.

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---:|---:|---:|---:|---:|---|
| 1 | 3.64 | 191.5 | 1662.1 | 1709.2 | 1.00% | FAIL |
| 10 | 41.29 | 189.6 | 222.8 | 1695.8 | 0.33% | PASS |
| 50 | 98.75 | 212.6 | 355.4 | 1708.9 | 1.67% | PASS |
| 100 | 64.22 | 694.2 | 2353.6 | 2675.2 | 0.67% | FAIL |

RPS cao nhất ở concurrency 50 trong lần đo này. Khi tăng từ 50 lên 100, throughput giảm và p50 cũng tăng, phù hợp với tình trạng request phải chờ trong hệ thống khi quá nhiều request đồng thời. Số đo này chỉ cho thấy điểm nghẽn xuất hiện ở tải cao. Cần profile hoặc đo riêng tầng client, app và I/O để xác định nguyên nhân. Ở concurrency 1, các request đi tuần tự nên các lần gọi mock chậm cũng kéo dài tổng thời gian.

### 2.2 Tail latency

Giữ 300 request và concurrency 20, khởi động lại v2 giữa các lần đổi biến.

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---:|---:|---:|
| 0 | 189.8 | 217.7 | 226.5 |
| 0.03 | 223.6 | 242.1 | 1690.6 |
| 0.1 | 328.7 | 1680.6 | 1717.3 |

Ở 0.03, p99 tăng từ 226.5 lên 1690.6 ms trong khi avg tăng 33.8 ms. Khi nâng tỷ lệ chậm lên 0.1, cả p95 cũng tăng mạnh. Đặt SLO theo percentile giúp nhận biết đuôi phân bố và giữ error rate làm chỉ số riêng để phản ánh request thất bại.

### 2.3 Metrics ở Exercise 7.1

- `http_requests_total` là Counter. `agent_in_flight_requests` là Gauge. `http_request_duration_seconds` và `agent_question_length_chars` là Histogram.
- Sau một câu hỏi thử, `agent_question_length_chars_count` là 1 và `agent_question_length_chars_sum` là 40, đúng với độ dài đầu vào đã gửi.
- Nhãn route dùng template hoặc `unmatched`. Đưa URL đầy đủ vào nhãn có thể tạo nhiều time series mới từ mỗi URL có tham số hoặc đường dẫn lạ.

## 3. Benchmark chất lượng

| Chỉ số | Agent v1 | Agent v2 trước sửa | Agent v2 sau sửa |
|---|---:|---:|---:|
| Accuracy | 1/23 (4.35%) | 21/23 (91.30%) | 23/23 (100%) |
| Avg tokens/câu | 57.4 | 109.0 | 113.5 |
| Tổng cost (USD) | 0.000408 | 0.000760 | 0.000789 |
| Cost/câu đúng (USD) | 0.00040815 | 0.00003619 | 0.00003430 |
| p95 trong bộ eval (ms) | 179.7 | 215.1 | 218.8 |
| Quality gate | FAIL | PASS | PASS, 0 regression |

| ID | Keyword bị thiếu | Đã sửa |
|---|---|---|
| `security-02` | token, hết hạn, chữ ký | Thêm ngữ cảnh về JWT có chữ ký, thời hạn và sự khác nhau với API key. |
| `scaling-03` | cpu, memory, custom metrics | Thêm ngữ cảnh về Kubernetes HPA và các metric làm đầu vào cho autoscaling. |

V2 dùng nhiều token và tốn thêm thời gian truy xuất, nhưng giảm chi phí trên mỗi câu đúng nhờ tỷ lệ trả lời đúng tăng. Độ trễ trong bảng eval chỉ có 23 mẫu cho mỗi bản. Phần 2 dùng load test riêng để đánh giá hiệu năng.

CI có thể khởi động v2 với `MOCK_ERROR_RATE=0` rồi chạy `run_eval.py --min-accuracy 0.85 --baseline <baseline-từ-main>`. Exit code 1 cho biết accuracy dưới ngưỡng hoặc một câu từng đúng bị sai. Đặt job thành required check để PR chỉ merge khi job thành công. Lần sửa này dùng gate chặt hơn ở `1.0`.

## 4. Observability stack

### 4.1 Dashboard Grafana

Stack dùng loopback riêng để tránh cổng của các lab khác. Nginx ở `28080`, Grafana ở `23000`, Prometheus ở `29090` và Jaeger ở `26686`. Ở bài dashboard, hai replica phục vụ 30 users Locust với ramp-up 5 users/s.

- Truy vấn Prometheus lúc 22:49:13 (GMT+7) cho p95 **295.8 ms** và avg **234.1 ms** đối với `POST /ask`. Khoảng cách **61.7 ms** cho thấy percentile và mức trung bình phản ánh các phần khác nhau của phân bố latency.
- Metrics ở hai agent ghi nhận **3.98 req/s** và **3.44 req/s** tại thời điểm lấy mẫu. Nginx chuyển traffic đến cả hai instance với mức gần nhau.
- Input khoảng **573.6 token/s**, output khoảng **299.8 token/s**. Prompt đầu vào gồm hướng dẫn, câu hỏi và ngữ cảnh retrieval.
- `GET /metrics` qua Nginx trả **404**. Metrics được scrape trực tiếp từ agent trong network Compose.

[Dashboard Grafana khi có tải](screenshots/grafana-dashboard.png)

### 4.2 Thí nghiệm cảnh báo

`promtool test rules` báo `SUCCESS`. Trước lần đo, hai alert ở trạng thái inactive. Từ 23:00:29 (GMT+7), áp dụng đồng thời hai thay đổi trên stack local và tiếp tục 30 users Locust.

| Thay đổi | Alert | Thời gian đến lần đầu quan sát firing | Tín hiệu |
|---|---|---:|---|
| `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` | 96.6 giây | Error rate `/ask` vượt 5%. |
| `MOCK_SLOW_RATE=0.3`, `MOCK_LATENCY_MS=1100` | `AgentHighLatencyP95` | 156.4 giây | p95 `/ask` vượt 1 giây. |

Thời gian đo tính cả lúc tạo lại agent, chờ sample lọt vào cửa sổ `rate` và khoảng giữ điều kiện `for`. Hai alert cùng firing trong [ảnh Prometheus](screenshots/prometheus-alert-firing.png).

Nếu chuyển sang v1, chất lượng có thể giảm trong khi agent vẫn trả 200. Dùng golden dataset làm quality gate trước khi phát hành và theo dõi thêm chất lượng câu trả lời trên một mẫu traffic thật.

### 4.3 Debug bằng trace

**[Trace chậm](screenshots/jaeger-slow-trace.png)** có ID `d7c1cd426c04c953384ff958ba0c7171`, tổng thời gian **2703.04 ms**. Span `chat mock-llm-small` chiếm **2678.27 ms** (99.1% tổng thời gian). Trong request này, chờ LLM chiếm phần lớn latency.

```json
{"ts":"2026-11-25T16:02:44.241652+00:00","level":"INFO","service":"observable-agent","instance":"4d27f12fd32e","event":"llm_call","trace_id":"d7c1cd426c04c953384ff958ba0c7171","span_id":"1c062c0e570df871","request_id":"945da4afbcae","model":"mock-llm-small","agent_version":"v2","input_tokens":95,"output_tokens":55,"cost_usd":4.7e-05,"llm_ms":2678.4}
```

**[Trace lỗi](screenshots/jaeger-error-trace.png)** có ID `4740d1c53c01781aab9e4caae8934eb9`. `POST /ask` trả **503** sau **608.93 ms**. Span `chat mock-llm-small` có event `exception` và kéo dài **576.95 ms**. Hai trace được đối chiếu với dòng log bằng cùng `trace_id`.

```json
{"ts":"2026-11-25T16:04:19.230566+00:00","level":"INFO","service":"observable-agent","instance":"4d27f12fd32e","event":"llm_error","trace_id":"4740d1c53c01781aab9e4caae8934eb9","span_id":"9c18eef14530775d","request_id":"7b21cce12fdf","error":"Upstream LLM error: 503 Service Unavailable (mock)"}
```

## 5. Benchmark scaling

Locust headless chạy 100 users, ramp-up 10 users/s, 2 phút cho mỗi cấu hình. Khi chạy `docker compose run --rm --no-deps locust`, giữ nguyên số replica đã đặt bằng `--scale agent=1` hoặc `--scale agent=3`. Prometheus thấy đúng số agent trước và sau mỗi lượt. Bảng dùng hàng `Aggregated` gồm `/ask` và `/health`.

| Số instance | Requests | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures | Error rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5052 | 39.62 | 230 | 3800 | 7500 | 39 | 0.77% |
| 3 | 6703 | 52.82 | 200 | 1700 | 4600 | 59 | 0.88% |

Throughput tăng khoảng 33% và p95 giảm khoảng 55%. Số user và thời gian nghỉ giữa request giữ nguyên, vì vậy tăng replica không làm RPS tăng gấp ba. p99 vẫn cao trong cả hai lần đo. Để điều tra, xem span LLM chậm trong mục 4 và đối chiếu latency ở tầng Nginx với latency của agent.

[CSV một replica](benchmark-results/scale_1_stats.csv) · [CSV ba replica](benchmark-results/scale_3_stats.csv)

## 6. Kết luận

1. SLO latency theo percentile cho thấy tác động của các request chậm mà mức trung bình có thể che đi.
2. Benchmark chất lượng cần dataset cố định và baseline. Mã HTTP 200 chỉ nói request thành công ở tầng giao thức.
3. Theo dõi RPS, latency, error rate và chi phí cùng lúc để đánh giá tác động của tăng tải hoặc thay model.

Khi đưa agent vào vận hành, theo dõi lỗi và latency tại load balancer, chi phí theo model và tỷ lệ trả lời đúng theo mẫu câu hỏi thực tế.
