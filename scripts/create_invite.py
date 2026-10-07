"""Create a one-use account invitation without exposing stored credentials."""

import argparse
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from src.api.database import InviteToken, SessionLocal


def create_invite(expires_in_days: int) -> str:
    if expires_in_days < 1 or expires_in_days > 30:
        raise ValueError("expires_in_days must be between 1 and 30")
    code = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=expires_in_days)
    db = SessionLocal()
    try:
        db.add(InviteToken(token_hash=token_hash, expires_at=expires_at))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expires-in-days", type=int, default=7)
    args = parser.parse_args()
    print(create_invite(args.expires_in_days))
