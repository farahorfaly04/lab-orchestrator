"""Device registry and locking service."""

import time
from typing import Dict, Any


class Registry:
    """Registry for devices and resource locking."""
    
    def __init__(self):
        self.devices: Dict[str, Any] = {}   # merge from device meta/status
        self.locks: Dict[str, Any] = {}     # key "module:device" -> {holder, exp}

    def lock(self, key: str, holder: str, ttl_s: int) -> bool:
        """Acquire a lock on a resource."""
        exp = time.time() + ttl_s
        cur = self.locks.get(key)
        if cur and cur["exp"] > time.time() and cur["holder"] != holder:
            return False
        self.locks[key] = {"holder": holder, "exp": exp}
        return True

    def release(self, key: str, holder: str) -> bool:
        """Release a lock on a resource."""
        cur = self.locks.get(key)
        if not cur or cur["holder"] != holder:
            return False
        del self.locks[key]
        return True

    def snapshot(self) -> Dict[str, Any]:
        """Get current registry snapshot."""
        return {"devices": self.devices, "locks": self.locks}

    def can_use(self, key: str, actor: str) -> bool:
        """Check if an actor can use a resource."""
        cur = self.locks.get(key)
        if not cur:
            return True
        if cur.get("exp", 0) <= time.time():
            return True
        return cur.get("holder") == actor
