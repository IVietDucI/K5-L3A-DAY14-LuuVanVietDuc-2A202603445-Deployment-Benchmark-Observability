# Day 14 — Deployment

## Nền tảng

Railway. Service agent build từ Dockerfile của `06-lab-complete/`. Service Redis nằm cùng project và dùng kết nối nội bộ. `railway.toml` cấu hình kiểm tra `/health` và Dockerfile đọc `PORT` do nền tảng cấp.

Public URL: https://agent-production-0bccc7b8.up.railway.app

Railway báo deployment `SUCCESS` của service `agent`. Kết quả kiểm thử local được ghi trong [MISSION_ANSWERS.md](MISSION_ANSWERS.md).

## Biến môi trường

| Biến | Cách cấp |
|---|---|
| `AGENT_API_KEY` | Secret của service agent. |
| `REDIS_URL` | Tham chiếu biến kết nối nội bộ từ service Redis. |
| `ENVIRONMENT` | `production`. |
| `PORT` | Railway cấp, mặc định Dockerfile dùng `8000` khi chạy local. |
| `RATE_LIMIT_PER_MINUTE` | Mặc định `10`. |
| `MONTHLY_BUDGET_USD` | Mặc định `10` cho chi phí mô phỏng LLM. |

## Smoke test

Trong Bash, đặt `BASE` bằng URL của agent và nhập key với `read -rsp 'Agent API key: ' AGENT_API_KEY`.

```bash
curl -sS -o /dev/null -w 'health %{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w 'ready %{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w 'ask without key %{http_code}\n' "$BASE/ask" \
  -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w 'ask with key %{http_code}\n' "$BASE/ask" \
  -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" \
  -d '{"question":"Hello"}'
```

## Kết quả kiểm thử công khai

Đo lúc 22:20:35 (GMT+7), ngày 25/11/2026.

| Kiểm tra | HTTP |
|---|---:|
| `GET /health` | 200 |
| `GET /ready` | 200 |
| `POST /ask` thiếu API key | 401 |
| `POST /ask` có API key | 200 |
| `POST /ask` có API key, câu hỏi chỉ chứa khoảng trắng | 422 |

[Dashboard Railway](screenshots/dashboard.png) · [Ảnh phản hồi health của agent public](screenshots/running.png) · [Ảnh kết quả smoke test](screenshots/test.png)
