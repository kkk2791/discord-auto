import re
import hashlib
from datetime import datetime, timezone


def mask_token(token: str, visible: int = 8) -> str:
    if len(token) <= visible * 2:
        return "*" * len(token)
    return token[:visible] + "*" * (len(token) - visible * 2) + token[-visible:]


def validate_discord_token(token: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9._-]{50,100}$", token))


def generate_id_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def format_datetime(dt: datetime | None) -> str:
    if dt is None:
        return "N/A"
    local = dt.astimezone()
    return local.strftime("%Y-%m-%d %H:%M:%S")


def truncate_str(s: str, max_len: int = 100) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."
