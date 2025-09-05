"""Structured logging system for Lab Platform."""

import json
import logging
import time
import uuid
from contextvars import ContextVar
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

# Context variables for request correlation
request_id_ctx: ContextVar[str] = ContextVar('request_id', default='')
device_id_ctx: ContextVar[str] = ContextVar('device_id', default='')
module_ctx: ContextVar[str] = ContextVar('module', default='')
actor_ctx: ContextVar[str] = ContextVar('actor', default='')


class StructuredFormatter(logging.Formatter):
    """JSON formatter with structured context fields."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime(record.created)),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
            "req_id": request_id_ctx.get(),
            "device_id": device_id_ctx.get(),
            "module": module_ctx.get(),
            "actor": actor_ctx.get(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info', 'exc_text',
                          'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


def setup_logging(
    component: str,
    level: str = "INFO",
    log_file: Optional[Path] = None,
    max_bytes: int = 10_000_000,
    backup_count: int = 5
) -> logging.Logger:
    """Setup structured logging for a component.
    
    Args:
        component: Component name (orchestrator, agent, etc.)
        level: Logging level
        log_file: Optional file path for logging
        max_bytes: Max file size before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(component)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    formatter = StructuredFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    logger.propagate = False
    return logger


def with_context(**context_updates):
    """Decorator to set context variables for the duration of a function call."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tokens = []
            try:
                # Set context variables
                for key, value in context_updates.items():
                    if key == 'request_id':
                        tokens.append(request_id_ctx.set(value))
                    elif key == 'device_id':
                        tokens.append(device_id_ctx.set(value))
                    elif key == 'module':
                        tokens.append(module_ctx.set(value))
                    elif key == 'actor':
                        tokens.append(actor_ctx.set(value))
                
                return func(*args, **kwargs)
            finally:
                # Reset context variables
                for token in tokens:
                    try:
                        token.var.reset(token)
                    except LookupError:
                        pass
        return wrapper
    return decorator


def log_command_execution(action: str, duration_ms: float, result: str, **extra):
    """Log command execution with timing and result."""
    logger = logging.getLogger("command")
    logger.info(
        f"Command executed: {action}",
        extra={
            "action": action,
            "duration_ms": duration_ms,
            "result": result,
            **extra
        }
    )


def log_mqtt_message(direction: str, topic: str, payload_size: int, **extra):
    """Log MQTT message with metadata."""
    logger = logging.getLogger("mqtt")
    logger.debug(
        f"MQTT {direction}: {topic}",
        extra={
            "direction": direction,
            "topic": topic,
            "payload_size": payload_size,
            **extra
        }
    )


def generate_request_id() -> str:
    """Generate a new request ID."""
    return str(uuid.uuid4())


def set_request_context(req_id: str, device_id: str = "", module: str = "", actor: str = ""):
    """Set request context variables."""
    request_id_ctx.set(req_id)
    device_id_ctx.set(device_id)
    module_ctx.set(module)
    actor_ctx.set(actor)


# Middleware for timing operations
class TimingContext:
    """Context manager for timing operations."""
    
    def __init__(self, operation: str, logger: Optional[logging.Logger] = None):
        self.operation = operation
        self.logger = logger or logging.getLogger("timing")
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        result = "error" if exc_type else "success"
        
        self.logger.info(
            f"Operation completed: {self.operation}",
            extra={
                "operation": self.operation,
                "duration_ms": duration_ms,
                "result": result
            }
        )


def timed_operation(operation: str):
    """Decorator for timing operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with TimingContext(operation):
                return func(*args, **kwargs)
        return wrapper
    return decorator
