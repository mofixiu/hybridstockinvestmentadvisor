"""Short-lived client for the Investo NGX EOD API.

Raw provider responses are cached in process memory for five minutes only. This
module deliberately does not write Investo price history to local files or the
market-data database; the free API terms permit transient caching, not a
permanent mirror of the raw feed.
"""

from __future__ import annotations

import copy
import json
import os
import threading
import time
from datetime import date, datetime, time as datetime_time, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


API_ROOT = "https://investo.ng/api/v1"
SOURCE_NAME = "Investo — investo.ng"
CACHE_TTL_SECONDS = 300
_cache: dict[tuple[str, tuple[tuple[str, str], ...]], tuple[float, Any]] = {}
_cache_lock = threading.Lock()


class InvestoProviderError(RuntimeError):
    """Sanitized provider error that never includes the API key or request URL."""


def is_configured() -> bool:
    return bool(os.getenv("INVESTO_API", "").strip() or os.getenv("INVESTO_API_KEY", "").strip())


def _api_key() -> str:
    key = (os.getenv("INVESTO_API", "") or os.getenv("INVESTO_API_KEY", "")).strip()
    if not key:
        raise InvestoProviderError("INVESTO_API is not configured")
    return key


def _request_json(path: str, params: dict[str, str] | None = None) -> tuple[Any, dict[str, Any]]:
    query = tuple(sorted((str(k), str(v)) for k, v in (params or {}).items()))
    cache_key = (path, query)
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached is not None and cached[0] > now:
            payload = copy.deepcopy(cached[1])
            return _unwrap(payload)
        if cached is not None:
            _cache.pop(cache_key, None)

    url = f"{API_ROOT}/{path}"
    if query:
        url += "?" + urlencode(query)
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {_api_key()}",
            "User-Agent": "HybStockAdvisor/2",
        },
    )

    for attempt in range(3):
        try:
            with urlopen(request, timeout=20) as response:
                if response.status < 200 or response.status >= 300:
                    if response.status in (429, 500, 502, 503, 504) and attempt < 2:
                        time.sleep(0.25 * (2**attempt))
                        continue
                    raise InvestoProviderError(
                        f"Investo request failed with HTTP {response.status}"
                    )
                payload = json.loads(response.read().decode("utf-8"))
                data, meta = _unwrap(payload)
                with _cache_lock:
                    _cache[cache_key] = (time.monotonic() + CACHE_TTL_SECONDS, copy.deepcopy(payload))
                return data, meta
        except HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(0.25 * (2**attempt))
                continue
            raise InvestoProviderError(
                f"Investo request failed with HTTP {exc.code}"
            ) from None
        except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            if attempt < 2:
                time.sleep(0.25 * (2**attempt))
                continue
            raise InvestoProviderError(
                f"Investo request could not be completed: {type(exc).__name__}"
            ) from None
    raise InvestoProviderError("Investo request could not be completed")


def _unwrap(payload: Any) -> tuple[Any, dict[str, Any]]:
    if not isinstance(payload, dict) or payload.get("ok") is False:
        raise InvestoProviderError("Investo returned an unsuccessful response")
    data = payload.get("data")
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    if data is None:
        raise InvestoProviderError("Investo response did not contain data")
    return data, meta


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        normalized = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized).date()
        except ValueError:
            pass
    raise InvestoProviderError("Investo response contained an invalid trade date")


def _parse_timestamp(value: Any, fallback: date) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            parsed = datetime.combine(fallback, datetime_time.min)
    else:
        parsed = datetime.combine(fallback, datetime_time.min)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _normalize_bar(symbol: str, record: Any, generated_at: Any) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    trade_date = _parse_date(record.get("date") or record.get("trade_date"))
    close = _optional_float(record.get("close", record.get("price")))
    if close is None or close <= 0:
        return None
    return {
        "exchange": "NGX",
        "symbol": str(record.get("symbol") or symbol).strip().upper(),
        "trade_date": trade_date,
        "currency": "NGN",
        "open": _optional_float(record.get("open")),
        "high": _optional_float(record.get("high")),
        "low": _optional_float(record.get("low")),
        "close": close,
        "volume": _optional_float(record.get("volume")),
        "source": SOURCE_NAME,
        "source_as_of": _parse_timestamp(generated_at, trade_date),
        "provider_verified": True,
    }


def fetch_stocks() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch the current NGX equity list and its latest close data."""
    data, meta = _request_json("stocks")
    if not isinstance(data, list):
        raise InvestoProviderError("Investo stock response was not a list")
    result = []
    generated_at = meta.get("generated_at")
    for item in data:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or "").strip().upper()
        trade_date_value = item.get("trade_date") or item.get("date")
        price = _optional_float(item.get("price", item.get("close")))
        if not symbol or price is None or price <= 0 or not trade_date_value:
            continue
        trade_date = _parse_date(trade_date_value)
        previous = _optional_float(item.get("previous_close"))
        change = _optional_float(item.get("change_percent"))
        if change is None:
            change = ((price - previous) / previous * 100) if previous else 0.0
        result.append(
            {
                "symbol": symbol,
                "name": str(item.get("name") or symbol),
                "market_cap": _optional_float(item.get("market_cap")),
                "price": price,
                "change_pct": change,
                "currency": "NGN",
                "exchange": "NGX",
                "trade_date": trade_date,
                "as_of": _parse_timestamp(generated_at, trade_date),
                "source": SOURCE_NAME,
                "stale": False,
            }
        )
    return result, meta


def fetch_history(symbol: str, start_date: date) -> list[dict[str, Any]]:
    """Fetch EOD history into memory; callers must not persist raw rows."""
    normalized = symbol.strip().upper()
    if not normalized or len(normalized) > 30:
        raise ValueError("symbol must contain 1 to 30 characters")
    data, meta = _request_json(
        f"prices/{quote(normalized, safe='')}", {"from": start_date.isoformat()}
    )
    records = data if isinstance(data, list) else [data]
    bars = [_normalize_bar(normalized, row, meta.get("generated_at")) for row in records]
    result = [bar for bar in bars if bar is not None and bar["trade_date"] >= start_date]
    result.sort(key=lambda bar: bar["trade_date"])
    return result


def fetch_asi_history(start_date: date) -> list[dict[str, Any]]:
    """Fetch the NGX All-Share Index history for in-memory research evaluation."""
    data, _meta = _request_json(
        "indices/asi/history", {"from": start_date.isoformat()}
    )
    if not isinstance(data, list):
        raise InvestoProviderError("Investo index history response was not a list")
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        day = _parse_date(item.get("date"))
        close = _optional_float(item.get("close"))
        if close is not None and close > 0:
            result.append({"date": day, "close": close})
    result.sort(key=lambda item: item["date"])
    return result
