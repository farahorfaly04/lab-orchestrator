"""Retry mechanisms with jittered exponential backoff."""

import asyncio
import functools
import logging
import random
import time
from typing import Callable, Any, Optional, Type, Tuple, Union, List


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""
    
    def __init__(self, message: str, last_exception: Exception, attempt_count: int):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempt_count = attempt_count


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        jitter_factor: float = 0.1,
        retriable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        non_retriable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.jitter_factor = jitter_factor
        self.retriable_exceptions = retriable_exceptions or (Exception,)
        self.non_retriable_exceptions = non_retriable_exceptions or ()
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            jitter_range = delay * self.jitter_factor
            jitter = random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay + jitter)
        
        return delay
    
    def is_retriable_exception(self, exception: Exception) -> bool:
        """Check if exception should trigger a retry."""
        # First check non-retriable exceptions
        if isinstance(exception, self.non_retriable_exceptions):
            return False
        
        # Then check retriable exceptions
        return isinstance(exception, self.retriable_exceptions)


# Default retry configurations for different use cases
MQTT_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=0.5,
    max_delay=30.0,
    retriable_exceptions=(ConnectionError, TimeoutError, OSError),
    non_retriable_exceptions=(ValueError, TypeError)
)

DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    retriable_exceptions=(Exception,),  # Most DB errors are retriable
    non_retriable_exceptions=(ValueError, TypeError)
)

SUBPROCESS_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
    retriable_exceptions=(OSError, subprocess.SubprocessError) if 'subprocess' in globals() else (OSError,),
    non_retriable_exceptions=(ValueError, TypeError, FileNotFoundError)
)

SERIAL_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    max_delay=15.0,
    retriable_exceptions=(OSError, ConnectionError),
    non_retriable_exceptions=(ValueError, TypeError)
)


def retry_sync(config: RetryConfig = None, logger: logging.Logger = None):
    """Decorator for synchronous retry functionality."""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    # Log successful retry
                    if attempt > 1 and logger:
                        logger.info(
                            f"Function {func.__name__} succeeded on attempt {attempt}",
                            extra={"attempt": attempt, "function": func.__name__}
                        )
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if exception is retriable
                    if not config.is_retriable_exception(e):
                        if logger:
                            logger.warning(
                                f"Non-retriable exception in {func.__name__}: {e}",
                                extra={"function": func.__name__, "exception": str(e)}
                            )
                        raise e
                    
                    # Don't delay after last attempt
                    if attempt < config.max_attempts:
                        delay = config.calculate_delay(attempt)
                        
                        if logger:
                            logger.warning(
                                f"Attempt {attempt} failed for {func.__name__}: {e}. Retrying in {delay:.2f}s",
                                extra={
                                    "attempt": attempt,
                                    "function": func.__name__,
                                    "delay": delay,
                                    "exception": str(e)
                                }
                            )
                        
                        time.sleep(delay)
                    else:
                        if logger:
                            logger.error(
                                f"All {config.max_attempts} attempts failed for {func.__name__}",
                                extra={
                                    "function": func.__name__,
                                    "max_attempts": config.max_attempts,
                                    "final_exception": str(e)
                                }
                            )
            
            # All attempts exhausted
            raise RetryError(
                f"Function {func.__name__} failed after {config.max_attempts} attempts",
                last_exception,
                config.max_attempts
            )
        
        return wrapper
    return decorator


def retry_async(config: RetryConfig = None, logger: logging.Logger = None):
    """Decorator for asynchronous retry functionality."""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    result = await func(*args, **kwargs)
                    
                    # Log successful retry
                    if attempt > 1 and logger:
                        logger.info(
                            f"Function {func.__name__} succeeded on attempt {attempt}",
                            extra={"attempt": attempt, "function": func.__name__}
                        )
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if exception is retriable
                    if not config.is_retriable_exception(e):
                        if logger:
                            logger.warning(
                                f"Non-retriable exception in {func.__name__}: {e}",
                                extra={"function": func.__name__, "exception": str(e)}
                            )
                        raise e
                    
                    # Don't delay after last attempt
                    if attempt < config.max_attempts:
                        delay = config.calculate_delay(attempt)
                        
                        if logger:
                            logger.warning(
                                f"Attempt {attempt} failed for {func.__name__}: {e}. Retrying in {delay:.2f}s",
                                extra={
                                    "attempt": attempt,
                                    "function": func.__name__,
                                    "delay": delay,
                                    "exception": str(e)
                                }
                            )
                        
                        await asyncio.sleep(delay)
                    else:
                        if logger:
                            logger.error(
                                f"All {config.max_attempts} attempts failed for {func.__name__}",
                                extra={
                                    "function": func.__name__,
                                    "max_attempts": config.max_attempts,
                                    "final_exception": str(e)
                                }
                            )
            
            # All attempts exhausted
            raise RetryError(
                f"Function {func.__name__} failed after {config.max_attempts} attempts",
                last_exception,
                config.max_attempts
            )
        
        return wrapper
    return decorator


class RetryableOperation:
    """Context manager for retryable operations."""
    
    def __init__(self, config: RetryConfig = None, logger: logging.Logger = None, operation_name: str = "operation"):
        self.config = config or RetryConfig()
        self.logger = logger
        self.operation_name = operation_name
        self.attempt = 0
        self.last_exception = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Success
            if self.attempt > 1 and self.logger:
                self.logger.info(
                    f"Operation {self.operation_name} succeeded on attempt {self.attempt}",
                    extra={"attempt": self.attempt, "operation": self.operation_name}
                )
            return False
        
        # Exception occurred
        self.last_exception = exc_val
        
        # Check if retriable
        if not self.config.is_retriable_exception(exc_val):
            if self.logger:
                self.logger.warning(
                    f"Non-retriable exception in {self.operation_name}: {exc_val}",
                    extra={"operation": self.operation_name, "exception": str(exc_val)}
                )
            return False  # Re-raise
        
        # Check if we should retry
        if self.attempt < self.config.max_attempts:
            delay = self.config.calculate_delay(self.attempt)
            
            if self.logger:
                self.logger.warning(
                    f"Attempt {self.attempt} failed for {self.operation_name}: {exc_val}. Retrying in {delay:.2f}s",
                    extra={
                        "attempt": self.attempt,
                        "operation": self.operation_name,
                        "delay": delay,
                        "exception": str(exc_val)
                    }
                )
            
            time.sleep(delay)
            return True  # Suppress exception and retry
        else:
            # All attempts exhausted
            if self.logger:
                self.logger.error(
                    f"All {self.config.max_attempts} attempts failed for {self.operation_name}",
                    extra={
                        "operation": self.operation_name,
                        "max_attempts": self.config.max_attempts,
                        "final_exception": str(exc_val)
                    }
                )
            
            # Replace with RetryError
            raise RetryError(
                f"Operation {self.operation_name} failed after {self.config.max_attempts} attempts",
                exc_val,
                self.config.max_attempts
            )
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        for attempt in range(1, self.config.max_attempts + 1):
            self.attempt = attempt
            
            with self:
                return func(*args, **kwargs)


# Convenience functions
def retry_mqtt_operation(func: Callable, *args, logger: logging.Logger = None, **kwargs) -> Any:
    """Retry MQTT operation with appropriate configuration."""
    operation = RetryableOperation(MQTT_RETRY_CONFIG, logger, f"mqtt_{func.__name__}")
    return operation.execute(func, *args, **kwargs)


def retry_database_operation(func: Callable, *args, logger: logging.Logger = None, **kwargs) -> Any:
    """Retry database operation with appropriate configuration."""
    operation = RetryableOperation(DATABASE_RETRY_CONFIG, logger, f"db_{func.__name__}")
    return operation.execute(func, *args, **kwargs)


def retry_subprocess_operation(func: Callable, *args, logger: logging.Logger = None, **kwargs) -> Any:
    """Retry subprocess operation with appropriate configuration."""
    operation = RetryableOperation(SUBPROCESS_RETRY_CONFIG, logger, f"subprocess_{func.__name__}")
    return operation.execute(func, *args, **kwargs)


def retry_serial_operation(func: Callable, *args, logger: logging.Logger = None, **kwargs) -> Any:
    """Retry serial operation with appropriate configuration."""
    operation = RetryableOperation(SERIAL_RETRY_CONFIG, logger, f"serial_{func.__name__}")
    return operation.execute(func, *args, **kwargs)
