"""Prometheus metrics for Lab Platform orchestrator."""

import time
from functools import wraps
from typing import Dict, Any, Optional

from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST


# Create a custom registry for better control
REGISTRY = CollectorRegistry()

# System info
SYSTEM_INFO = Info(
    'lab_platform_info',
    'Lab Platform system information',
    registry=REGISTRY
)

# HTTP metrics
HTTP_REQUESTS_TOTAL = Counter(
    'lab_platform_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY
)

HTTP_REQUEST_DURATION = Histogram(
    'lab_platform_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY
)

# MQTT metrics
MQTT_MESSAGES_TOTAL = Counter(
    'lab_platform_mqtt_messages_total',
    'Total MQTT messages',
    ['direction', 'topic_pattern'],
    registry=REGISTRY
)

MQTT_MESSAGE_SIZE_BYTES = Histogram(
    'lab_platform_mqtt_message_size_bytes',
    'MQTT message size in bytes',
    ['direction'],
    buckets=[10, 50, 100, 500, 1000, 5000, 10000, 50000],
    registry=REGISTRY
)

MQTT_PUBLISH_DURATION = Histogram(
    'lab_platform_mqtt_publish_duration_seconds',
    'MQTT publish duration in seconds',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=REGISTRY
)

# Command metrics
COMMANDS_TOTAL = Counter(
    'lab_platform_commands_total',
    'Total commands processed',
    ['device_id', 'module', 'action', 'status'],
    registry=REGISTRY
)

COMMAND_DURATION = Histogram(
    'lab_platform_command_duration_seconds',
    'Command execution duration in seconds',
    ['device_id', 'module', 'action'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    registry=REGISTRY
)

COMMAND_FAILURES_TOTAL = Counter(
    'lab_platform_command_failures_total',
    'Total command failures',
    ['device_id', 'module', 'action', 'error_type'],
    registry=REGISTRY
)

# Device metrics
DEVICES_CONNECTED = Gauge(
    'lab_platform_devices_connected',
    'Number of connected devices',
    registry=REGISTRY
)

DEVICES_ONLINE = Gauge(
    'lab_platform_devices_online',
    'Number of online devices',
    registry=REGISTRY
)

MODULES_LOADED = Gauge(
    'lab_platform_modules_loaded_total',
    'Total number of loaded modules',
    ['device_id', 'module'],
    registry=REGISTRY
)

# Plugin metrics
PLUGINS_LOADED = Gauge(
    'lab_platform_plugins_loaded',
    'Number of loaded plugins',
    registry=REGISTRY
)

# Database metrics
DATABASE_OPERATIONS_TOTAL = Counter(
    'lab_platform_database_operations_total',
    'Total database operations',
    ['operation', 'table', 'status'],
    registry=REGISTRY
)

DATABASE_OPERATION_DURATION = Histogram(
    'lab_platform_database_operation_duration_seconds',
    'Database operation duration in seconds',
    ['operation', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=REGISTRY
)

# Resource metrics
RESOURCE_LOCKS_ACTIVE = Gauge(
    'lab_platform_resource_locks_active',
    'Number of active resource locks',
    registry=REGISTRY
)

SCHEDULED_TASKS_ACTIVE = Gauge(
    'lab_platform_scheduled_tasks_active',
    'Number of active scheduled tasks',
    registry=REGISTRY
)


class MetricsCollector:
    """Metrics collection and management."""
    
    def __init__(self):
        self.registry = REGISTRY
        self._initialize_system_info()
    
    def _initialize_system_info(self):
        """Initialize system information metrics."""
        import platform
        import sys
        from lab_orchestrator import __version__ if hasattr(__import__('lab_orchestrator'), '__version__') else '0.1.0'
        
        SYSTEM_INFO.info({
            'version': '0.1.0',  # Replace with actual version
            'python_version': sys.version.split()[0],
            'platform': platform.system(),
            'architecture': platform.machine()
        })
    
    def track_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Track HTTP request metrics."""
        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        HTTP_REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def track_mqtt_message(self, direction: str, topic: str, size_bytes: int, duration: float = None):
        """Track MQTT message metrics."""
        # Simplify topic to pattern
        topic_pattern = self._simplify_topic(topic)
        
        MQTT_MESSAGES_TOTAL.labels(
            direction=direction,
            topic_pattern=topic_pattern
        ).inc()
        
        MQTT_MESSAGE_SIZE_BYTES.labels(direction=direction).observe(size_bytes)
        
        if duration is not None and direction == 'publish':
            MQTT_PUBLISH_DURATION.observe(duration)
    
    def track_command(self, device_id: str, module: str, action: str, 
                     status: str, duration: float = None, error_type: str = None):
        """Track command execution metrics."""
        COMMANDS_TOTAL.labels(
            device_id=device_id,
            module=module,
            action=action,
            status=status
        ).inc()
        
        if duration is not None:
            COMMAND_DURATION.labels(
                device_id=device_id,
                module=module,
                action=action
            ).observe(duration)
        
        if status == 'failed' and error_type:
            COMMAND_FAILURES_TOTAL.labels(
                device_id=device_id,
                module=module,
                action=action,
                error_type=error_type
            ).inc()
    
    def track_database_operation(self, operation: str, table: str, status: str, duration: float):
        """Track database operation metrics."""
        DATABASE_OPERATIONS_TOTAL.labels(
            operation=operation,
            table=table,
            status=status
        ).inc()
        
        DATABASE_OPERATION_DURATION.labels(
            operation=operation,
            table=table
        ).observe(duration)
    
    def update_device_counts(self, connected: int, online: int):
        """Update device count metrics."""
        DEVICES_CONNECTED.set(connected)
        DEVICES_ONLINE.set(online)
    
    def update_module_status(self, device_id: str, module: str, loaded: bool):
        """Update module status metrics."""
        if loaded:
            MODULES_LOADED.labels(device_id=device_id, module=module).set(1)
        else:
            MODULES_LOADED.labels(device_id=device_id, module=module).set(0)
    
    def update_plugin_count(self, count: int):
        """Update plugin count metrics."""
        PLUGINS_LOADED.set(count)
    
    def update_resource_locks(self, count: int):
        """Update resource lock count."""
        RESOURCE_LOCKS_ACTIVE.set(count)
    
    def update_scheduled_tasks(self, count: int):
        """Update scheduled task count."""
        SCHEDULED_TASKS_ACTIVE.set(count)
    
    def _simplify_topic(self, topic: str) -> str:
        """Simplify MQTT topic to reduce cardinality."""
        parts = topic.split('/')
        
        if len(parts) >= 3 and parts[1] == 'lab':
            if parts[2] == 'device' and len(parts) >= 4:
                # /lab/device/{device_id}/... -> /lab/device/+/...
                return '/'.join([parts[0], parts[1], parts[2], '+'] + parts[4:])
            elif parts[2] == 'orchestrator':
                # Keep orchestrator topics as-is
                return topic
        
        return topic
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry).decode('utf-8')
    
    def get_content_type(self) -> str:
        """Get metrics content type."""
        return CONTENT_TYPE_LATEST


# Global metrics collector
metrics = MetricsCollector()


# Decorators for automatic metrics collection
def track_http_metrics(endpoint: str):
    """Decorator to track HTTP request metrics."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(request, *args, **kwargs):
            start_time = time.time()
            status_code = 200
            
            try:
                response = await func(request, *args, **kwargs)
                if hasattr(response, 'status_code'):
                    status_code = response.status_code
                return response
            except Exception as e:
                status_code = getattr(e, 'status_code', 500)
                raise
            finally:
                duration = time.time() - start_time
                method = request.method if hasattr(request, 'method') else 'GET'
                metrics.track_http_request(method, endpoint, status_code, duration)
        
        @wraps(func)
        def sync_wrapper(request, *args, **kwargs):
            start_time = time.time()
            status_code = 200
            
            try:
                response = func(request, *args, **kwargs)
                if hasattr(response, 'status_code'):
                    status_code = response.status_code
                return response
            except Exception as e:
                status_code = getattr(e, 'status_code', 500)
                raise
            finally:
                duration = time.time() - start_time
                method = request.method if hasattr(request, 'method') else 'GET'
                metrics.track_http_request(method, endpoint, status_code, duration)
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def track_database_metrics(operation: str, table: str):
    """Decorator to track database operation metrics."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                status = 'error'
                raise
            finally:
                duration = time.time() - start_time
                metrics.track_database_operation(operation, table, status, duration)
        
        return wrapper
    return decorator


def track_command_metrics(device_id: str, module: str, action: str):
    """Decorator to track command execution metrics."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'
            error_type = None
            
            try:
                result = func(*args, **kwargs)
                # Assume result is (success, error, details) tuple
                if isinstance(result, tuple) and len(result) >= 2:
                    success, error = result[0], result[1]
                    if not success:
                        status = 'failed'
                        error_type = type(error).__name__ if error else 'unknown'
                return result
            except Exception as e:
                status = 'error'
                error_type = type(e).__name__
                raise
            finally:
                duration = time.time() - start_time
                metrics.track_command(device_id, module, action, status, duration, error_type)
        
        return wrapper
    return decorator
