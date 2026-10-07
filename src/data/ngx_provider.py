"""Small client for the official NGX market-data API.

Access is deliberately opt-in. The API requires an NGX access token and the
operator must confirm that their agreement permits the intended app/tester use.
"""

from __future__ import annotations

import json
import os
import time
from datetime import date, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


NGX_API_ROOT = "https://marketdataapiv3.ngxgroup.com/v3/api/price"
SOURCE_NAME = "NGX Market Data API"


class MarketDataProviderError(RuntimeError):
    """A provider error with secrets and request URLs removed."""


def market_data_use_approved() -> bool:
    return os.getenv("NGX_MARKET_DATA_USE_APPROVED", "false").strip().lower() == "true"


def _access_token() -> str:
    token = os.getenv("NGX_DATA_API_TOKEN", "").strip()
    if not token:
        raise MarketDataProviderError("NGX_DATA_API_TOKEN is not configured")
    if not market_data_use_approved():
        raise MarketDataProviderError(
            "NGX market-data use is disabled until the applicable use agreement is approved"
        )
    return token


def _fetch_json(endpoint: str, params: dict[str, str]) -> Any:
    query = dict(params)
    query["_t"] = _access_token()
    url = f"{NGX_API_ROOT}/{endpoint}.json?{urlencode(query)}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "HybStockAdvisor/2"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=20) as response:
                if response.status < 200 or response.status >= 300:
                    if response.status in (429, 500, 502, 503, 504) and attempt < 2:
                        time.sleep(0.25 * (2**attempt))
                        continue
                    raise MarketDataProviderError(
                        f"NGX market-data request failed ({response.status})"
                    )
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(0.25 * (2**attempt))
                continue
            raise MarketDataProviderError(
                f"NGX market-data request failed ({exc.code})"
            ) from None
        except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            if attempt < 2:
                time.sleep(0.25 * (2**attempt))
                continue
            raise MarketDataProviderError(
                f"NGX market-data request could not be completed: {type(exc).__name__}"
            ) from None
    raise MarketDataProviderError("NGX market-data request could not be completed")


def _records(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "Data", "result", "Result", "prices", "Prices"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return candidate
    raise MarketDataProviderError("NGX market-data response did not contain a record list")


def _value(record: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in record:
            return record[name]
    lower_names = {name.lower() for name in names}
    for key, value in record.items():
        if key.lower() in lower_names:
            return value
    return None


def _parse_trade_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        normalized = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized).date()
        except ValueError:
            for fmt in ("%d/%m/%Y", "%Y%m%d"):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    pass
    raise MarketDataProviderError("NGX market-data response contains an invalid trade date")


def _normalize_record(record: Any) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    asset = str(_value(record, "Asset", "AssetClass", "MarketType") or "EQUITY").upper()
    if asset != "EQUITY":
        return None
    symbol = str(_value(record, "Symbol", "Ticker", "SecurityCode") or "").strip().upper()
    if not symbol:
        return None
    try:
        trade_date = _parse_trade_date(_value(record, "TradeDate", "Date", "date"))
        close = float(_value(record, "Close", "ClosingPrice", "ClosePrice"))
        open_price = _value(record, "Open", "OpeningPrice", "OpenPrice")
        high = _value(record, "High", "HighPrice")
        low = _value(record, "Low", "LowPrice")
        volume = _value(record, "Volume", "TradedVolume")
    except (TypeError, ValueError) as exc:
        raise MarketDataProviderError("NGX market-data response contains invalid price fields") from exc
    if close <= 0:
        return None
    return {
        "exchange": "NGX",
        "symbol": symbol,
        "trade_date": trade_date,
        "currency": "NGN",
        "open": float(open_price) if open_price is not None else None,
        "high": float(high) if high is not None else None,
        "low": float(low) if low is not None else None,
        "close": close,
        "volume": float(volume) if volume is not None else None,
        "source": SOURCE_NAME,
        "source_as_of": datetime.combine(trade_date, datetime.min.time()),
        "provider_verified": True,
    }


def fetch_end_of_day() -> list[dict[str, Any]]:
    """Fetch the official end-of-day equity snapshot for all NGX symbols."""
    payload = _fetch_json("pricesEOD", {"a": "EQUITY"})
    normalized = [_normalize_record(record) for record in _records(payload)]
    bars = [bar for bar in normalized if bar is not None]
    if not bars:
        raise MarketDataProviderError("NGX returned no valid end-of-day equity prices")
    return bars


def fetch_history(symbol: str, start_date: date, end_date: date) -> list[dict[str, Any]]:
    """Fetch official daily OHLCV history for a single NGX security."""
    symbol = symbol.strip().upper()
    if not symbol or len(symbol) > 30:
        raise ValueError("symbol must contain 1 to 30 characters")
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
    payload = _fetch_json(
        "interdayprices",
        {"s": symbol, "f": start_date.isoformat(), "t": end_date.isoformat()},
    )
    normalized = []
    for record in _records(payload):
        if isinstance(record, (list, tuple)) and len(record) >= 5:
            # Some API versions expose interday rows as [date, open, high, low, close, volume].
            record = {
                "Symbol": symbol,
                "TradeDate": record[0],
                "Open": record[1],
                "High": record[2],
                "Low": record[3],
                "Close": record[4],
                "Volume": record[5] if len(record) > 5 else None,
                "Asset": "EQUITY",
            }
        elif isinstance(record, dict):
            record = dict(record)
            record.setdefault("Symbol", symbol)
            record.setdefault("Asset", "EQUITY")
        bar = _normalize_record(record)
        if bar and start_date <= bar["trade_date"] <= end_date and bar["symbol"] == symbol:
            normalized.append(bar)
    return normalized
