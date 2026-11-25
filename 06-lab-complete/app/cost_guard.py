"""
Cost guard (tiêu chí 8).

Yêu cầu:
  • Cộng dồn chi phí LLM (tính theo token) vào Redis
  • Tổng chi phí vượt DAILY_BUDGET_USD (hoặc MONTHLY_BUDGET_USD) → HTTP 402
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from .config import settings
from .redis_client import r


# $0.00015 and $0.00060 per 1,000 tokens, in integer billionths of a dollar.
NANODOLLARS_PER_USD = 1_000_000_000
INPUT_PRICE = 150
OUTPUT_PRICE = 600

RESERVE = """
local cost = tonumber(ARGV[1])
for index, key in ipairs(KEYS) do
    local spent = tonumber(redis.call('GET', key) or '0')
    if spent + cost > tonumber(ARGV[index * 2]) then
        return 0
    end
end
for index, key in ipairs(KEYS) do
    redis.call('INCRBY', key, ARGV[1])
    redis.call('EXPIREAT', key, ARGV[index * 2 + 1])
end
return 1
"""
REFUND = """
for _, key in ipairs(KEYS) do
    if redis.call('EXISTS', key) == 1 then
        redis.call('DECRBY', key, ARGV[1])
    end
end
return 1
"""
reserve = r.register_script(RESERVE)
refund = r.register_script(REFUND)


@dataclass(frozen=True)
class Reservation:
    keys: list[str]
    amount: int


def check_budget(input_tokens: int, max_output_tokens: int) -> Reservation:
    """Reserve the maximum cost atomically before calling the mock LLM."""
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today.replace(day=1)
    next_month = (month_start + timedelta(days=32)).replace(day=1)
    windows = (
        ("day", today, today + timedelta(days=1), settings.daily_budget_usd),
        ("month", month_start, next_month, settings.monthly_budget_usd),
    )

    amount = input_tokens * INPUT_PRICE + max_output_tokens * OUTPUT_PRICE
    keys = []
    arguments = [amount]
    for period, start, end, budget in windows:
        if budget is None:
            continue
        keys.append(f"day14:part6:cost:{{budget}}:{period}:{start:%Y-%m-%d}")
        # Keep the old key briefly so requests that span midnight can settle.
        arguments.extend([int(budget * NANODOLLARS_PER_USD), int(end.timestamp()) + 60])
    if not reserve(keys=keys, args=arguments):
        raise HTTPException(status_code=402, detail="LLM budget exceeded")
    return Reservation(keys, amount)


def record_cost(reservation: Reservation, input_tokens: int, output_tokens: int) -> float:
    amount = input_tokens * INPUT_PRICE + output_tokens * OUTPUT_PRICE
    change = reservation.amount - amount
    if change:
        refund(keys=reservation.keys, args=[change])
    return amount / NANODOLLARS_PER_USD
