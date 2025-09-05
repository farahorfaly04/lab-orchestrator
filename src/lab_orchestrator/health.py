"""Health check endpoints for Lab Platform orchestrator."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import HTTPException
from pydantic import BaseModel

from .services.mqtt import SharedMQTT
from .services.registry import Registry
from .db import db_manager


class HealthStatus(BaseModel):
    """Health check status model."""
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime
    checks: Dict[str, Dict[str, Any]]
    uptime_seconds: float
    version: str = "0.1.0"


class HealthChecker:
    """Health check manager for orchestrator services."""
    
    def __init__(self, mqtt: SharedMQTT, registry: Registry):
        self.mqtt = mqtt
        self.registry = registry
        self.start_time = time.time()
    
    async def check_health(self, include_details: bool = True) -> HealthStatus:
        """Perform comprehensive health check."""
        checks = {}
        overall_status = "healthy"
        
        # Check MQTT connection
        mqtt_check = await self._check_mqtt()
        checks["mqtt"] = mqtt_check
        if mqtt_check["status"] != "healthy":
            overall_status = "degraded" if overall_status == "healthy" else "unhealthy"
        
        # Check database connection
        db_check = await self._check_database()
        checks["database"] = db_check
        if db_check["status"] != "healthy":
            overall_status = "degraded" if overall_status == "healthy" else "unhealthy"
        
        # Check device connectivity
        devices_check = await self._check_devices()
        checks["devices"] = devices_check
        if devices_check["status"] != "healthy":
            overall_status = "degraded"  # Device issues are not critical
        
        # Check plugin status
        plugins_check = await self._check_plugins()
        checks["plugins"] = plugins_check
        
        # Check system resources
        if include_details:
            system_check = await self._check_system_resources()
            checks["system"] = system_check
        
        return HealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow(),
            checks=checks,
            uptime_seconds=time.time() - self.start_time
        )
    
    async def check_readiness(self) -> Dict[str, Any]:
        """Check if service is ready to handle requests."""
        ready = True
        details = {}
        
        # Check MQTT connection
        mqtt_ready = self._is_mqtt_ready()
        details["mqtt"] = mqtt_ready
        ready = ready and mqtt_ready
        
        # Check database connection
        db_ready = await self._is_database_ready()
        details["database"] = db_ready
        ready = ready and db_ready
        
        # Check plugins loaded
        plugins_ready = self._are_plugins_ready()
        details["plugins"] = plugins_ready
        ready = ready and plugins_ready
        
        return {
            "ready": ready,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def check_liveness(self) -> Dict[str, Any]:
        """Basic liveness check."""
        return {
            "alive": True,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - self.start_time
        }
    
    async def _check_mqtt(self) -> Dict[str, Any]:
        """Check MQTT broker connectivity."""
        try:
            # Check if MQTT client is connected
            is_connected = self.mqtt.client.is_connected()
            
            if is_connected:
                # Try to publish a test message
                test_topic = "/lab/orchestrator/health/test"
                test_payload = {"test": True, "timestamp": time.time()}
                
                start_time = time.time()
                self.mqtt.publish_json(test_topic, test_payload)
                response_time = (time.time() - start_time) * 1000
                
                return {
                    "status": "healthy",
                    "connected": True,
                    "response_time_ms": response_time,
                    "message": "MQTT broker is accessible"
                }
            else:
                return {
                    "status": "unhealthy",
                    "connected": False,
                    "message": "MQTT client not connected"
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "message": "MQTT broker check failed"
            }
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            start_time = time.time()
            
            # Simple query to check connection
            with db_manager.get_session() as session:
                result = session.execute("SELECT 1").scalar()
                
            response_time = (time.time() - start_time) * 1000
            
            if result == 1:
                return {
                    "status": "healthy",
                    "connected": True,
                    "response_time_ms": response_time,
                    "message": "Database is accessible"
                }
            else:
                return {
                    "status": "unhealthy",
                    "connected": False,
                    "message": "Database query returned unexpected result"
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "message": "Database connection failed"
            }
    
    async def _check_devices(self) -> Dict[str, Any]:
        """Check device connectivity status."""
        try:
            registry_snapshot = self.registry.snapshot()
            devices = registry_snapshot.get("devices", {})
            
            total_devices = len(devices)
            online_devices = sum(1 for d in devices.values() if d.get("online", False))
            
            # Consider healthy if > 50% of devices are online (or no devices registered)
            if total_devices == 0:
                status = "healthy"
                message = "No devices registered"
            elif online_devices / total_devices >= 0.5:
                status = "healthy"
                message = f"{online_devices}/{total_devices} devices online"
            else:
                status = "degraded"
                message = f"Only {online_devices}/{total_devices} devices online"
            
            # Check for stale devices (not seen in last 5 minutes)
            cutoff_time = datetime.utcnow() - timedelta(minutes=5)
            stale_devices = []
            
            for device_id, device_data in devices.items():
                last_seen_str = device_data.get("last_seen")
                if last_seen_str:
                    try:
                        last_seen = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
                        if last_seen < cutoff_time:
                            stale_devices.append(device_id)
                    except (ValueError, AttributeError):
                        pass
            
            return {
                "status": status,
                "total_devices": total_devices,
                "online_devices": online_devices,
                "stale_devices": len(stale_devices),
                "message": message
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "Device status check failed"
            }
    
    async def _check_plugins(self) -> Dict[str, Any]:
        """Check plugin loading status."""
        try:
            # This would need access to the plugin registry from host.py
            # For now, return basic info
            return {
                "status": "healthy",
                "message": "Plugin status check not implemented"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "message": "Plugin status check failed"
            }
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Determine status based on resource usage
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
                status = "unhealthy"
                message = "High resource usage detected"
            elif cpu_percent > 70 or memory_percent > 70 or disk_percent > 80:
                status = "degraded"
                message = "Moderate resource usage"
            else:
                status = "healthy"
                message = "Resource usage is normal"
            
            return {
                "status": status,
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "message": message
            }
            
        except ImportError:
            return {
                "status": "unknown",
                "message": "psutil not available for system resource monitoring"
            }
        except Exception as e:
            return {
                "status": "unknown",
                "error": str(e),
                "message": "System resource check failed"
            }
    
    def _is_mqtt_ready(self) -> bool:
        """Check if MQTT is ready."""
        try:
            return self.mqtt.client.is_connected()
        except:
            return False
    
    async def _is_database_ready(self) -> bool:
        """Check if database is ready."""
        try:
            with db_manager.get_session() as session:
                session.execute("SELECT 1").scalar()
            return True
        except:
            return False
    
    def _are_plugins_ready(self) -> bool:
        """Check if plugins are loaded and ready."""
        # This would need access to plugin state
        # For now, assume ready
        return True


# Startup probe for module loading
class StartupProbe:
    """Startup probe to check module loading progress."""
    
    def __init__(self):
        self.module_load_status = {}
        self.startup_complete = False
        self.startup_errors = []
    
    def mark_module_loading(self, module_name: str):
        """Mark a module as currently loading."""
        self.module_load_status[module_name] = "loading"
    
    def mark_module_loaded(self, module_name: str, success: bool, error: str = None):
        """Mark a module as loaded (successfully or with error)."""
        if success:
            self.module_load_status[module_name] = "loaded"
        else:
            self.module_load_status[module_name] = "failed"
            if error:
                self.startup_errors.append(f"{module_name}: {error}")
    
    def mark_startup_complete(self):
        """Mark startup process as complete."""
        self.startup_complete = True
    
    def get_startup_status(self) -> Dict[str, Any]:
        """Get current startup status."""
        loading_modules = [k for k, v in self.module_load_status.items() if v == "loading"]
        failed_modules = [k for k, v in self.module_load_status.items() if v == "failed"]
        loaded_modules = [k for k, v in self.module_load_status.items() if v == "loaded"]
        
        ready = self.startup_complete and len(loading_modules) == 0 and len(failed_modules) == 0
        
        return {
            "ready": ready,
            "startup_complete": self.startup_complete,
            "modules": {
                "loading": loading_modules,
                "loaded": loaded_modules,
                "failed": failed_modules
            },
            "errors": self.startup_errors
        }


# Global startup probe instance
startup_probe = StartupProbe()
