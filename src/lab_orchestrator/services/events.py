"""Event handling utilities."""

from datetime import datetime, timezone


def now_iso():
    """Return current timestamp in ISO format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ack(req_id: str, ok: bool, code: str = "OK", error: str = None, details=None):
    """Create a standardized acknowledgment message."""
    return {
        "v": 1, 
        "req_id": req_id, 
        "ok": ok, 
        "code": code, 
        "error": error, 
        "details": details or {}, 
        "ts": now_iso()
    }
