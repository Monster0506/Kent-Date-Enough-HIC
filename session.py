import hashlib
import hmac
import os

_SECRET = os.environ.get("KDE_SECRET", "SECRET SECRET")


def make_session_cookie(user_id: int) -> str:
    payload = str(user_id)
    sig = hmac.new(_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def read_session_cookie(cookie: str | None) -> int | None:
    if not cookie:
        return None
    try:
        payload, sig = cookie.rsplit(".", 1)
        expected = hmac.new(
            _SECRET.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        return int(payload)
    except Exception:
        return None


def get_session(req) -> int | None:
    raw = req.header("cookie", "")
    for part in (raw or "").split(";"):
        part = part.strip()
        if part.startswith("session="):
            return read_session_cookie(part[len("session=") :])
    return None


def set_session_header(user_id: int) -> tuple[str, str]:
    value = make_session_cookie(user_id)
    return ("Set-Cookie", f"session={value}; HttpOnly; SameSite=Lax; Path=/")


def clear_session_header() -> tuple[str, str]:
    return ("Set-Cookie", "session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0")
