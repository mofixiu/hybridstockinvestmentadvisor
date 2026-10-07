"""HybStockAdvisor API: authenticated accounts and verified market research."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Optional

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google import genai
from google.genai import types
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.api.database import (
    InviteToken,
    MarketDailyBar,
    PasswordReset,
    PaperSignal,
    Portfolio,
    User,
    Watchlist,
    get_db,
)
from src.api.market_data import (
    NGX_TIMEZONE,
    bar_as_dict,
    is_stale,
    latest_bar,
    market_data_enabled,
    market_data_source,
    market_summary,
    published_signal,
    release_approval,
    recent_bars,
    signal_as_dict,
)
from src.api.schemas import (
    ForecastResponse,
    InsightsResponse,
    MarketSummaryResponse,
)

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

app = FastAPI(
    title="HybStockAdvisor API",
    description="Authenticated research API for NGX daily market data",
    version="2.0.0",
)

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
    if origin.strip()
]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _registration_allowlist() -> set[str]:
    configured = {
        email.strip().lower()
        for email in os.getenv("INVITED_USER_EMAILS", "").split(",")
        if email.strip()
    }
    owner_email = os.getenv("INVESTO_PERSONAL_OWNER_EMAIL", "").strip().lower()
    if owner_email:
        configured.add(owner_email)
    return configured


def _market_data_allowed_for_user(user: User) -> bool:
    """The free Investo tier is restricted to the owner's personal project."""
    if os.getenv("INVESTO_API", "").strip() or os.getenv("INVESTO_API_KEY", "").strip():
        owner_email = os.getenv("INVESTO_PERSONAL_OWNER_EMAIL", "").strip().lower()
        return bool(owner_email) and user.email.strip().lower() == owner_email
    return market_data_enabled()


def create_access_token(user: User) -> str:
    if len(JWT_SECRET_KEY) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured on this server",
        )
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "user_id": user.id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not JWT_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub"]},
        )
        user_id = int(payload["user_id"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Session is invalid or expired") from None
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Account is no longer available")
    # Release the database connection after the short authentication lookup.
    # The route may make slower provider or AI calls before it needs the DB again.
    db.commit()
    return user


def _require_exchange(exchange: str) -> str:
    normalized = exchange.strip().upper()
    if normalized != "NGX":
        raise HTTPException(status_code=404, detail="This exchange is not available yet")
    return normalized


class UserCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    invite_code: Optional[str] = Field(default=None, min_length=20, max_length=128)


class UserLogin(BaseModel):
    identifier: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=128)


class PortfolioCreate(BaseModel):
    # Kept optional for old clients. The authenticated user remains authoritative.
    user_id: Optional[int] = None
    ticker: str = Field(min_length=1, max_length=30)
    quantity: float = Field(gt=0)
    average_buy_price: float = Field(gt=0)


class WatchlistCreate(BaseModel):
    user_id: Optional[int] = None
    ticker: str = Field(min_length=1, max_length=30)


class RemoveItemRequest(BaseModel):
    user_id: Optional[int] = None
    ticker: str = Field(min_length=1, max_length=30)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResetPasswordRequest(BaseModel):
    reset_token: str = Field(min_length=20, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ChatMessage(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    current_ticker: Optional[str] = Field(default=None, max_length=30)


@app.get("/")
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "market_data_configured": market_data_enabled(),
    }


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    email = str(user.email).strip().lower()
    username = user.username.strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="Username already taken")

    invitation = None
    invite_code = (user.invite_code or "").strip()
    if invite_code:
        invitation = (
            db.query(InviteToken)
            .filter(InviteToken.token_hash == _hash(invite_code))
            .with_for_update()
            .first()
        )
        if (
            invitation is None
            or invitation.used_at is not None
            or invitation.expires_at <= _utc_now_naive()
        ):
            raise HTTPException(status_code=403, detail="Invitation code is invalid or expired")
    elif email not in _registration_allowlist():
        raise HTTPException(status_code=403, detail="Registration is by invitation only")

    created = User(
        first_name=user.first_name.strip(),
        last_name=user.last_name.strip(),
        username=username,
        email=email,
        password_hash=pwd_context.hash(user.password),
    )
    if invitation is not None:
        invitation.used_at = _utc_now_naive()
    db.add(created)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Account could not be created") from None
    db.refresh(created)
    return {
        "status": "success",
        "message": "Account created successfully",
        "data": {"user_id": created.id, "username": created.username},
    }


@app.post("/api/auth/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    identifier = user.identifier.strip()
    db_user = (
        db.query(User)
        .filter(or_(User.email == identifier.lower(), User.username == identifier))
        .first()
    )
    if not db_user or not pwd_context.verify(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username/email or password")
    return {
        "status": "success",
        "message": "Login successful",
        "token": create_access_token(db_user),
        "user_data": {
            "id": db_user.id,
            "first_name": db_user.first_name,
            "last_name": db_user.last_name,
            "username": db_user.username,
            "email": db_user.email,
        },
    }


@app.get("/api/summary", response_model=MarketSummaryResponse)
def get_market_summary(
    exchange: str = Query(default="NGX", min_length=3, max_length=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _market_data_allowed_for_user(current_user):
        return {
            "status": "success",
            "data": [],
            "meta": {
                "data_available": False,
                "reason": "market_data_not_enabled_for_this_account",
                "exchange": _require_exchange(exchange),
                "as_of": None,
                "stale": True,
            },
        }
    return market_summary(db, _require_exchange(exchange))


@app.get("/api/forecast/{ticker}", response_model=ForecastResponse)
def get_forecast(
    ticker: str,
    exchange: str = Query(default="NGX", min_length=3, max_length=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exchange = _require_exchange(exchange)
    normalized_ticker = ticker.strip().upper()
    if len(normalized_ticker) > 30 or not normalized_ticker:
        raise HTTPException(status_code=422, detail="Invalid stock symbol")
    allowed = _market_data_allowed_for_user(current_user)
    bars = recent_bars(db, normalized_ticker, limit=120, exchange=exchange) if allowed else []
    latest = bars[-1] if bars else None
    signal_row = published_signal(db, normalized_ticker, exchange, latest)
    signal = signal_as_dict(signal_row, latest, release_approval(db, signal_row))
    return {
        "status": "success",
        "data": [bar_as_dict(bar) for bar in bars],
        "meta": {
            "data_available": bool(bars),
            "exchange": exchange,
            "symbol": normalized_ticker,
            "currency": latest.currency if latest else "NGN",
            "as_of": latest.source_as_of.isoformat() if latest else None,
            "source": latest.source if latest else None,
            "stale": is_stale(latest.trade_date) if latest else True,
        },
        "signal": signal,
    }


@app.get("/api/insights/{ticker}", response_model=InsightsResponse)
def get_insights(
    ticker: str,
    exchange: str = Query(default="NGX", min_length=3, max_length=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exchange = _require_exchange(exchange)
    normalized_ticker = ticker.strip().upper()
    current = (
        latest_bar(db, normalized_ticker, exchange)
        if _market_data_allowed_for_user(current_user)
        else None
    )
    signal_row = published_signal(db, normalized_ticker, exchange, current)
    signal = signal_as_dict(signal_row, current, release_approval(db, signal_row))
    if current is None:
        explanation = "Verified NGX closing data is not available yet. No stock signal is being shown."
    elif is_stale(current.trade_date):
        explanation = "The latest verified closing data is stale. No stock signal is being shown."
    elif signal["available"]:
        explanation = (
            "A reviewed research signal is available for the stated horizon. "
            "It is uncertain and is not a personalized instruction to trade."
        )
    else:
        explanation = (
            "Verified closing data is available, but no model signal has passed review. "
            "This page provides market context only."
        )
    return {
        "status": "success",
        "data": {
            "ticker": normalized_ticker,
            "exchange": exchange,
            "currency": current.currency if current else "NGN",
            "price": float(current.close) if current else None,
            "data_as_of": current.source_as_of.isoformat() if current else None,
            "data_source": current.source if current else None,
            "data_stale": is_stale(current.trade_date) if current else True,
            "recommendation": signal["direction"],
            "signal": signal,
            "ai_confidence": signal.get("probability_positive"),
            "market_stability": None,
            "public_sentiment": None,
            "safety_index": None,
            "rsi_impact": None,
            "ema_impact": None,
            "evidence": signal["evidence"],
            "explanation": explanation,
        },
    }


@app.post("/api/portfolio/add")
def add_to_portfolio(
    item: PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if item.user_id is not None and item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    ticker = item.ticker.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,29}", ticker):
        raise HTTPException(status_code=422, detail="Enter a valid NGX symbol")
    if db.query(Portfolio).filter_by(user_id=current_user.id, ticker=ticker).first():
        raise HTTPException(status_code=409, detail="Stock is already in your portfolio")
    db.add(
        Portfolio(
            user_id=current_user.id,
            ticker=ticker,
            quantity=item.quantity,
            average_buy_price=item.average_buy_price,
        )
    )
    db.commit()
    return {"status": "success"}


@app.delete("/api/portfolio/remove")
def remove_from_portfolio(
    item: RemoveItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if item.user_id is not None and item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    row = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == current_user.id, Portfolio.ticker == item.ticker.upper())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Stock not found in portfolio")
    db.delete(row)
    db.commit()
    return {"status": "success"}


@app.post("/api/watchlist/add")
def add_to_watchlist(
    item: WatchlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if item.user_id is not None and item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    ticker = item.ticker.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,29}", ticker):
        raise HTTPException(status_code=422, detail="Enter a valid NGX symbol")
    if db.query(Watchlist).filter_by(user_id=current_user.id, ticker=ticker).first():
        return {"status": "error", "detail": "Already in watchlist"}
    db.add(Watchlist(user_id=current_user.id, ticker=ticker))
    db.commit()
    return {"status": "success"}


@app.delete("/api/watchlist/remove")
def remove_from_watchlist(
    item: RemoveItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if item.user_id is not None and item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    row = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == current_user.id, Watchlist.ticker == item.ticker.upper())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Stock not found in watchlist")
    db.delete(row)
    db.commit()
    return {"status": "success"}


def _asset_market_values(
    db: Session, ticker: str, *, allow_market_data: bool = True
) -> tuple[float | None, float | None, list[float], str | None, str | None, str | None, bool]:
    if not allow_market_data or not market_data_enabled():
        return None, None, [], None, None, None, True
    bars = recent_bars(db, ticker, limit=7)
    if not bars:
        return None, None, [], None, None, None, True
    price = float(bars[-1].close)
    previous = float(bars[-2].close) if len(bars) > 1 else price
    change = ((price - previous) / previous) * 100 if previous else 0.0
    return (
        price,
        change,
        [float(bar.close) for bar in bars],
        bars[-1].currency,
        bars[-1].source_as_of.isoformat(),
        bars[-1].source,
        is_stale(bars[-1].trade_date),
    )


@app.get("/api/user/{user_id}/assets")
def get_user_assets(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this data")
    portfolio_rows = db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()
    watchlist_rows = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).all()
    # These rows are fully loaded (expire_on_commit=False). Release the DB
    # connection before making one or more potentially slow market-data calls.
    db.commit()
    portfolio = []
    watchlist = []
    allow_market_data = _market_data_allowed_for_user(current_user)
    for row in portfolio_rows:
        price, change, spark, currency, as_of, source, stale = _asset_market_values(
            db, row.ticker, allow_market_data=allow_market_data
        )
        portfolio.append(
            {
                "id": row.id,
                "ticker": row.ticker,
                "quantity": float(row.quantity),
                "avg_buy_price": float(row.average_buy_price),
                "live_price": price,
                "change_pct": change,
                "spark_data": spark,
                "currency": currency or "NGN",
                "exchange": "NGX",
                "as_of": as_of,
                "source": source,
                "stale": stale,
            }
        )
    for row in watchlist_rows:
        price, change, spark, currency, as_of, source, stale = _asset_market_values(
            db, row.ticker, allow_market_data=allow_market_data
        )
        watchlist.append(
            {
                "id": row.id,
                "ticker": row.ticker,
                "live_price": price,
                "change_pct": change,
                "spark_data": spark,
                "currency": currency or "NGN",
                "exchange": "NGX",
                "as_of": as_of,
                "source": source,
                "stale": stale,
            }
        )
    return {
        "status": "success",
        "data": {
            "portfolio": portfolio,
            "watchlist": watchlist,
            "meta": {
                "market_data_available": allow_market_data and market_data_enabled(),
                "source": market_data_source() if allow_market_data else None,
            },
        },
    }


def _chat_context(
    db: Session, user: User, ticker: str | None, *, allow_market_data: bool = True
) -> str:
    owned = db.query(Portfolio).filter(Portfolio.user_id == user.id).all()
    watched = db.query(Watchlist).filter(Watchlist.user_id == user.id).all()
    symbols = {row.ticker.upper() for row in owned}
    symbols.update(row.ticker.upper() for row in watched)
    if ticker:
        symbols.add(ticker.strip().upper())
    if not allow_market_data or not market_data_enabled():
        return "Verified market data is not configured. Do not claim current prices or signals."
    lines = []
    for symbol in sorted(symbols):
        bar = latest_bar(db, symbol)
        if bar is None:
            lines.append(f"{symbol}: no verified market data is available.")
            continue
        lines.append(
            f"{symbol}: NGN {float(bar.close):.4f}, closing date {bar.trade_date.isoformat()}, "
            f"source {bar.source}, as of {bar.source_as_of.isoformat()}, stale={is_stale(bar.trade_date)}."
        )
        signal = published_signal(db, symbol, current_bar=bar)
        if signal and signal.validation_status == "published" and not is_stale(bar.trade_date):
            lines.append(
                f"{symbol} reviewed research signal: {signal.direction}, "
                f"{signal.horizon_sessions} trading days, model {signal.model_version}."
            )
        else:
            lines.append(f"{symbol}: no reviewed directional signal is available.")
    return "\n".join(lines) if lines else "No current stock context was selected."


@app.post("/api/chat")
def ai_chat(
    request: ChatMessage,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="The research assistant is not configured")
    context = _chat_context(
        db,
        current_user,
        request.current_ticker,
        allow_market_data=_market_data_allowed_for_user(current_user),
    )
    system_prompt = f"""
You are Lexi, a calm research companion for HybStockAdvisor.
The user's name is {current_user.first_name}. Use it naturally, not on every reply.
Use only the verified app data below for current prices, dates, or published signals:
{context}

Rules:
- Never invent prices, metrics, news, recommendations, or claims that data is live.
- Say when data is missing or stale and state the data date when using a price.
- A published signal is uncertain research, not a personalized instruction or a promise.
- Do not tell the user to buy, sell, or place a trade. Explain evidence and risks neutrally.
- If asked about general finance, label the answer as general information, not current market data.
- Keep the answer concise and readable.
"""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=request.text,
            config=types.GenerateContentConfig(system_instruction=system_prompt),
        )
    except Exception:
        raise HTTPException(status_code=502, detail="The research assistant is temporarily unavailable") from None
    if not response.text:
        raise HTTPException(status_code=502, detail="The research assistant returned an empty response")
    return {"status": "success", "reply": response.text}


def _smtp_configured() -> bool:
    return all(
        os.getenv(name)
        for name in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "EMAIL_FROM")
    )


def _send_password_reset_email(email: str, first_name: str, otp: str) -> None:
    message = EmailMessage()
    message["Subject"] = "HybStockAdvisor password reset"
    message["From"] = os.environ["EMAIL_FROM"]
    message["To"] = email
    message.set_content(
        f"Hello {first_name},\n\nYour password reset code is {otp}. "
        "It expires in 15 minutes. If you did not request this, ignore this email."
    )
    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        if os.getenv("SMTP_STARTTLS", "true").lower() == "true":
            smtp.starttls()
        smtp.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(message)


@app.post("/api/auth/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    if not _smtp_configured():
        raise HTTPException(status_code=503, detail="Password reset email is not configured")
    user = db.query(User).filter(User.email == str(request.email).lower()).first()
    if user is None:
        return {"status": "success", "message": "If the account exists, a reset code was sent"}
    otp = f"{secrets.randbelow(1_000_000):06d}"
    reset = db.query(PasswordReset).filter(PasswordReset.email == user.email).first()
    if reset is None:
        reset = PasswordReset(
            email=user.email,
            otp="000000",  # legacy column retained; the real code is stored as a digest.
            otp_hash=_hash(otp),
            failed_attempts=0,
            reset_token=None,
            expires_at=_utc_now_naive() + timedelta(minutes=15),
        )
        db.add(reset)
    else:
        reset.otp = "000000"
        reset.otp_hash = _hash(otp)
        reset.failed_attempts = 0
        reset.reset_token = None
        reset.expires_at = _utc_now_naive() + timedelta(minutes=15)
    try:
        _send_password_reset_email(user.email, user.first_name, otp)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=502, detail="Could not send the password reset email") from None
    return {"status": "success", "message": "If the account exists, a reset code was sent"}


@app.post("/api/auth/verify-reset-otp")
def verify_otp(request: VerifyOtpRequest, db: Session = Depends(get_db)):
    email = str(request.email).lower()
    reset = db.query(PasswordReset).filter(PasswordReset.email == email).with_for_update().first()
    if reset is None:
        raise HTTPException(status_code=400, detail="Reset code is invalid or expired")
    if reset.expires_at <= _utc_now_naive() or reset.failed_attempts >= 5:
        db.delete(reset)
        db.commit()
        raise HTTPException(status_code=400, detail="Reset code is invalid or expired")
    otp_matches = (
        hmac.compare_digest(reset.otp_hash, _hash(request.otp))
        if reset.otp_hash
        else hmac.compare_digest(reset.otp, request.otp)
    )
    if not otp_matches:
        reset.failed_attempts = (reset.failed_attempts or 0) + 1
        db.commit()
        raise HTTPException(status_code=400, detail="Reset code is invalid or expired")
    reset_token = secrets.token_urlsafe(32)
    reset.reset_token = _hash(reset_token)
    db.commit()
    return {"status": "success", "reset_token": reset_token}


@app.post("/api/auth/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    reset = db.query(PasswordReset).filter(
        PasswordReset.reset_token == _hash(request.reset_token)
    ).first()
    if reset is None or reset.expires_at <= _utc_now_naive():
        raise HTTPException(status_code=400, detail="Reset session is invalid or expired")
    user = db.query(User).filter(User.email == reset.email).first()
    if user is None:
        db.delete(reset)
        db.commit()
        raise HTTPException(status_code=400, detail="Reset session is invalid or expired")
    user.password_hash = pwd_context.hash(request.new_password)
    db.delete(reset)
    db.commit()
    return {"status": "success", "message": "Password has been reset successfully"}
