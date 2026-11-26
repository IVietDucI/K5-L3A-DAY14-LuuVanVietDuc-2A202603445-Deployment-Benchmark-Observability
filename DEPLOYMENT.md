# Day 14 — Deployment

## Nền tảng

Agent được build từ Dockerfile trong `06-lab-complete/` và triển khai trên Railway. Redis nằm cùng project và kết nối qua mạng nội bộ. `railway.toml` dùng `/health` làm health check. Railway ghi nhận deployment `SUCCESS` trong lần chạy ngày 25/11/2026. [URL công khai](https://agent-production-0bccc7b8.up.railway.app) · [Kết quả kiểm thử local](MISSION_ANSWERS.md)

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

Các lệnh sau chạy trong Bash. API key được nhập từ terminal.

```bash
BASE='https://agent-production-0bccc7b8.up.railway.app'
read -rsp 'Agent API key: ' AGENT_API_KEY
printf '\n'

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
