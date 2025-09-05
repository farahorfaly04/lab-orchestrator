"""Request deduplication using in-memory cache."""

import time
import threading
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass
from collections import OrderedDict


@dataclass
class RequestRecord:
    """Record of a processed request."""
    req_id: str
    timestamp: float
    device_id: str
    action: str
    result: Optional[Dict[str, Any]] = None
    processing: bool = False


class RequestDeduplicator:
    """Thread-safe request deduplication cache."""
    
    def __init__(self, ttl_seconds: int = 300, max_size: int = 10000):
        """
        Initialize deduplicator.
        
        Args:
            ttl_seconds: Time-to-live for cached requests
            max_size: Maximum number of requests to cache
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: OrderedDict[str, RequestRecord] = OrderedDict()
        self._processing: Set[str] = set()
        self._lock = threading.RLock()
    
    def is_duplicate(self, req_id: str, device_id: str, action: str) -> tuple[bool, Optional[RequestRecord]]:
        """
        Check if request is a duplicate.
        
        Returns:
            (is_duplicate, existing_record)
        """
        with self._lock:
            self._cleanup_expired()
            
            if req_id in self._cache:
                record = self._cache[req_id]
                
                # Move to end (LRU)
                self._cache.move_to_end(req_id)
                
                # Check if it's the same request
                if record.device_id == device_id and record.action == action:
                    return True, record
                else:
                    # Same req_id but different request - this is suspicious
                    # Log warning but allow it
                    return False, None
            
            return False, None
    
    def mark_processing(self, req_id: str, device_id: str, action: str) -> bool:
        """
        Mark request as currently processing.
        
        Returns:
            True if successfully marked, False if already processing
        """
        with self._lock:
            # Check if already processing
            if req_id in self._processing:
                return False
            
            # Add to processing set
            self._processing.add(req_id)
            
            # Add to cache as processing
            record = RequestRecord(
                req_id=req_id,
                timestamp=time.time(),
                device_id=device_id,
                action=action,
                processing=True
            )
            
            self._cache[req_id] = record
            self._enforce_max_size()
            
            return True
    
    def mark_completed(self, req_id: str, result: Dict[str, Any] = None):
        """Mark request as completed with result."""
        with self._lock:
            # Remove from processing set
            self._processing.discard(req_id)
            
            # Update cache record
            if req_id in self._cache:
                record = self._cache[req_id]
                record.processing = False
                record.result = result or {}
                record.timestamp = time.time()  # Update timestamp
                
                # Move to end (LRU)
                self._cache.move_to_end(req_id)
    
    def mark_failed(self, req_id: str, error: str):
        """Mark request as failed."""
        with self._lock:
            # Remove from processing set
            self._processing.discard(req_id)
            
            # Update cache record
            if req_id in self._cache:
                record = self._cache[req_id]
                record.processing = False
                record.result = {"error": error, "success": False}
                record.timestamp = time.time()
                
                # Move to end (LRU)
                self._cache.move_to_end(req_id)
    
    def get_result(self, req_id: str) -> Optional[Dict[str, Any]]:
        """Get cached result for request."""
        with self._lock:
            if req_id in self._cache:
                record = self._cache[req_id]
                if not record.processing and record.result is not None:
                    # Move to end (LRU)
                    self._cache.move_to_end(req_id)
                    return record.result
            return None
    
    def is_processing(self, req_id: str) -> bool:
        """Check if request is currently processing."""
        with self._lock:
            return req_id in self._processing
    
    def _cleanup_expired(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = []
        
        for req_id, record in self._cache.items():
            if current_time - record.timestamp > self.ttl_seconds:
                expired_keys.append(req_id)
            else:
                # Since OrderedDict maintains insertion order,
                # we can break early as newer entries follow
                break
        
        for key in expired_keys:
            self._cache.pop(key, None)
            self._processing.discard(key)
    
    def _enforce_max_size(self):
        """Enforce maximum cache size by removing oldest entries."""
        while len(self._cache) > self.max_size:
            # Remove oldest entry
            oldest_key = next(iter(self._cache))
            self._cache.pop(oldest_key)
            self._processing.discard(oldest_key)
    
    def clear(self):
        """Clear all cached requests."""
        with self._lock:
            self._cache.clear()
            self._processing.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            current_time = time.time()
            processing_count = len(self._processing)
            completed_count = len([r for r in self._cache.values() if not r.processing])
            expired_count = len([r for r in self._cache.values() 
                               if current_time - r.timestamp > self.ttl_seconds])
            
            return {
                "total_cached": len(self._cache),
                "processing": processing_count,
                "completed": completed_count,
                "expired": expired_count,
                "cache_hit_potential": completed_count,
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds
            }


# Global deduplicator instance
_global_deduplicator = RequestDeduplicator()


def is_duplicate_request(req_id: str, device_id: str, action: str) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if request is duplicate using global deduplicator.
    
    Returns:
        (is_duplicate, cached_result_if_available)
    """
    is_dup, record = _global_deduplicator.is_duplicate(req_id, device_id, action)
    
    if is_dup and record:
        if record.processing:
            # Request is currently processing
            return True, {"status": "processing", "message": "Request is currently being processed"}
        elif record.result:
            # Request completed, return cached result
            return True, record.result
    
    return False, None


def mark_request_processing(req_id: str, device_id: str, action: str) -> bool:
    """Mark request as currently processing."""
    return _global_deduplicator.mark_processing(req_id, device_id, action)


def mark_request_completed(req_id: str, result: Dict[str, Any] = None):
    """Mark request as completed."""
    _global_deduplicator.mark_completed(req_id, result)


def mark_request_failed(req_id: str, error: str):
    """Mark request as failed."""
    _global_deduplicator.mark_failed(req_id, error)


def get_deduplication_stats() -> Dict[str, Any]:
    """Get deduplication statistics."""
    return _global_deduplicator.stats()


def clear_deduplication_cache():
    """Clear deduplication cache."""
    _global_deduplicator.clear()


# Decorator for automatic request deduplication
def deduplicate_requests(extract_req_info: callable = None):
    """
    Decorator to automatically deduplicate requests.
    
    Args:
        extract_req_info: Function to extract (req_id, device_id, action) from function args
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract request info
            if extract_req_info:
                try:
                    req_id, device_id, action = extract_req_info(*args, **kwargs)
                except Exception:
                    # If extraction fails, proceed without deduplication
                    return func(*args, **kwargs)
            else:
                # Default extraction for common patterns
                if len(args) >= 3:
                    req_id, device_id, action = args[0], args[1], args[2]
                else:
                    # Can't extract, proceed without deduplication
                    return func(*args, **kwargs)
            
            # Check for duplicate
            is_dup, cached_result = is_duplicate_request(req_id, device_id, action)
            if is_dup and cached_result:
                return cached_result
            
            # Mark as processing
            if not mark_request_processing(req_id, device_id, action):
                # Already processing
                return {"status": "processing", "message": "Request is currently being processed"}
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Mark as completed
                mark_request_completed(req_id, result)
                
                return result
                
            except Exception as e:
                # Mark as failed
                mark_request_failed(req_id, str(e))
                raise
        
        return wrapper
    return decorator
