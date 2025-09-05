"""Dead letter queue implementation for failed MQTT messages."""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from .services.mqtt import SharedMQTT
from .db import db_manager, db_session


class FailureReason(str, Enum):
    """Reasons for message failures."""
    VALIDATION_ERROR = "validation_error"
    DEVICE_UNREACHABLE = "device_unreachable"
    MODULE_ERROR = "module_error"
    TIMEOUT = "timeout"
    PROCESSING_ERROR = "processing_error"
    RETRY_EXHAUSTED = "retry_exhausted"
    SCHEMA_VIOLATION = "schema_violation"
    RESOURCE_LOCKED = "resource_locked"
    UNKNOWN_DEVICE = "unknown_device"
    UNKNOWN_MODULE = "unknown_module"


@dataclass
class DeadLetterMessage:
    """Dead letter message record."""
    id: str
    original_topic: str
    payload: Dict[str, Any]
    failure_reason: FailureReason
    error_message: str
    device_id: Optional[str]
    module_name: Optional[str]
    req_id: Optional[str]
    retry_count: int
    first_failed_at: str
    last_failed_at: str
    metadata: Dict[str, Any]


class DeadLetterQueue:
    """Dead letter queue for failed MQTT messages."""
    
    def __init__(self, mqtt_client: SharedMQTT, max_retries: int = 3):
        self.mqtt = mqtt_client
        self.max_retries = max_retries
        self._setup_dlq_topics()
    
    def _setup_dlq_topics(self):
        """Setup dead letter queue MQTT topics."""
        # Subscribe to DLQ management commands
        self.mqtt.subscribe(["/lab/dlq/cmd"], self._handle_dlq_command)
    
    def send_to_dlq(
        self,
        original_topic: str,
        payload: Dict[str, Any],
        failure_reason: FailureReason,
        error_message: str,
        device_id: Optional[str] = None,
        module_name: Optional[str] = None,
        req_id: Optional[str] = None,
        retry_count: int = 0,
        metadata: Dict[str, Any] = None
    ):
        """Send failed message to dead letter queue."""
        import uuid
        
        # Create DLQ message
        dlq_message = DeadLetterMessage(
            id=str(uuid.uuid4()),
            original_topic=original_topic,
            payload=payload,
            failure_reason=failure_reason,
            error_message=error_message,
            device_id=device_id,
            module_name=module_name,
            req_id=req_id or payload.get("req_id"),
            retry_count=retry_count,
            first_failed_at=datetime.utcnow().isoformat() + 'Z',
            last_failed_at=datetime.utcnow().isoformat() + 'Z',
            metadata=metadata or {}
        )
        
        # Determine DLQ topic
        if device_id and module_name:
            dlq_topic = f"/lab/dlq/{device_id}/{module_name}"
        elif device_id:
            dlq_topic = f"/lab/dlq/{device_id}/device"
        else:
            dlq_topic = "/lab/dlq/orchestrator"
        
        # Publish to DLQ topic
        dlq_payload = asdict(dlq_message)
        self.mqtt.publish_json(dlq_topic, dlq_payload, qos=1, retain=False)
        
        # Store in database for persistence
        self._store_dlq_message(dlq_message)
        
        # Log the failure
        import logging
        logger = logging.getLogger("dead_letter")
        logger.warning(
            f"Message sent to DLQ: {failure_reason.value}",
            extra={
                "dlq_id": dlq_message.id,
                "original_topic": original_topic,
                "failure_reason": failure_reason.value,
                "error_message": error_message,
                "device_id": device_id,
                "module_name": module_name,
                "req_id": req_id,
                "retry_count": retry_count
            }
        )
    
    def _store_dlq_message(self, message: DeadLetterMessage):
        """Store DLQ message in database."""
        try:
            with db_session() as session:
                # Create a simple DLQ table entry
                # This would require a DLQ table in the database schema
                pass  # Implementation would depend on database schema
        except Exception as e:
            import logging
            logger = logging.getLogger("dead_letter")
            logger.error(f"Failed to store DLQ message in database: {e}")
    
    def retry_message(self, dlq_id: str) -> bool:
        """Retry a message from the dead letter queue."""
        try:
            # Retrieve message from database
            dlq_message = self._get_dlq_message(dlq_id)
            if not dlq_message:
                return False
            
            # Check retry count
            if dlq_message.retry_count >= self.max_retries:
                import logging
                logger = logging.getLogger("dead_letter")
                logger.warning(
                    f"DLQ message {dlq_id} exceeded max retries ({self.max_retries})",
                    extra={"dlq_id": dlq_id, "retry_count": dlq_message.retry_count}
                )
                return False
            
            # Republish original message
            self.mqtt.publish_json(
                dlq_message.original_topic,
                dlq_message.payload,
                qos=1,
                retain=False
            )
            
            # Update retry count
            dlq_message.retry_count += 1
            dlq_message.last_failed_at = datetime.utcnow().isoformat() + 'Z'
            
            # Update in database
            self._update_dlq_message(dlq_message)
            
            import logging
            logger = logging.getLogger("dead_letter")
            logger.info(
                f"Retried DLQ message {dlq_id}",
                extra={
                    "dlq_id": dlq_id,
                    "retry_count": dlq_message.retry_count,
                    "original_topic": dlq_message.original_topic
                }
            )
            
            return True
            
        except Exception as e:
            import logging
            logger = logging.getLogger("dead_letter")
            logger.error(f"Failed to retry DLQ message {dlq_id}: {e}")
            return False
    
    def get_dlq_messages(
        self,
        device_id: Optional[str] = None,
        module_name: Optional[str] = None,
        failure_reason: Optional[FailureReason] = None,
        limit: int = 100
    ) -> List[DeadLetterMessage]:
        """Get messages from dead letter queue with filtering."""
        try:
            # This would query the database for DLQ messages
            # Implementation depends on database schema
            return []  # Placeholder
        except Exception as e:
            import logging
            logger = logging.getLogger("dead_letter")
            logger.error(f"Failed to retrieve DLQ messages: {e}")
            return []
    
    def purge_old_messages(self, older_than_days: int = 7):
        """Purge old messages from dead letter queue."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            
            # Delete from database
            with db_session() as session:
                # This would delete old DLQ messages
                # Implementation depends on database schema
                pass
            
            import logging
            logger = logging.getLogger("dead_letter")
            logger.info(f"Purged DLQ messages older than {older_than_days} days")
            
        except Exception as e:
            import logging
            logger = logging.getLogger("dead_letter")
            logger.error(f"Failed to purge old DLQ messages: {e}")
    
    def get_dlq_stats(self) -> Dict[str, Any]:
        """Get dead letter queue statistics."""
        try:
            # This would query database for statistics
            return {
                "total_messages": 0,
                "by_failure_reason": {},
                "by_device": {},
                "by_module": {},
                "oldest_message": None,
                "newest_message": None
            }
        except Exception as e:
            import logging
            logger = logging.getLogger("dead_letter")
            logger.error(f"Failed to get DLQ stats: {e}")
            return {}
    
    def _get_dlq_message(self, dlq_id: str) -> Optional[DeadLetterMessage]:
        """Get DLQ message by ID from database."""
        try:
            # Query database for DLQ message
            # Implementation depends on database schema
            return None  # Placeholder
        except Exception:
            return None
    
    def _update_dlq_message(self, message: DeadLetterMessage):
        """Update DLQ message in database."""
        try:
            # Update database record
            # Implementation depends on database schema
            pass
        except Exception as e:
            import logging
            logger = logging.getLogger("dead_letter")
            logger.error(f"Failed to update DLQ message: {e}")
    
    def _handle_dlq_command(self, topic: str, payload: Dict[str, Any]):
        """Handle DLQ management commands."""
        try:
            action = payload.get("action")
            
            if action == "retry":
                dlq_id = payload.get("dlq_id")
                if dlq_id:
                    success = self.retry_message(dlq_id)
                    response = {"action": "retry", "dlq_id": dlq_id, "success": success}
                else:
                    response = {"action": "retry", "error": "Missing dlq_id"}
            
            elif action == "purge":
                days = payload.get("older_than_days", 7)
                self.purge_old_messages(days)
                response = {"action": "purge", "success": True}
            
            elif action == "stats":
                stats = self.get_dlq_stats()
                response = {"action": "stats", "stats": stats}
            
            elif action == "list":
                filters = payload.get("filters", {})
                messages = self.get_dlq_messages(**filters)
                response = {
                    "action": "list",
                    "messages": [asdict(msg) for msg in messages],
                    "count": len(messages)
                }
            
            else:
                response = {"error": f"Unknown action: {action}"}
            
            # Send response
            response["req_id"] = payload.get("req_id", "")
            response["ts"] = datetime.utcnow().isoformat() + 'Z'
            
            self.mqtt.publish_json("/lab/dlq/response", response, qos=1, retain=False)
            
        except Exception as e:
            import logging
            logger = logging.getLogger("dead_letter")
            logger.error(f"Failed to handle DLQ command: {e}")
            
            error_response = {
                "error": str(e),
                "req_id": payload.get("req_id", ""),
                "ts": datetime.utcnow().isoformat() + 'Z'
            }
            self.mqtt.publish_json("/lab/dlq/response", error_response, qos=1, retain=False)


# Convenience functions for sending messages to DLQ
def send_validation_error_to_dlq(
    mqtt: SharedMQTT,
    dlq: DeadLetterQueue,
    topic: str,
    payload: Dict[str, Any],
    error: str,
    device_id: str = None,
    module_name: str = None
):
    """Send validation error to DLQ."""
    dlq.send_to_dlq(
        original_topic=topic,
        payload=payload,
        failure_reason=FailureReason.VALIDATION_ERROR,
        error_message=error,
        device_id=device_id,
        module_name=module_name
    )


def send_timeout_to_dlq(
    mqtt: SharedMQTT,
    dlq: DeadLetterQueue,
    topic: str,
    payload: Dict[str, Any],
    timeout_seconds: float,
    device_id: str = None,
    module_name: str = None
):
    """Send timeout error to DLQ."""
    dlq.send_to_dlq(
        original_topic=topic,
        payload=payload,
        failure_reason=FailureReason.TIMEOUT,
        error_message=f"Command timed out after {timeout_seconds} seconds",
        device_id=device_id,
        module_name=module_name
    )


def send_device_unreachable_to_dlq(
    mqtt: SharedMQTT,
    dlq: DeadLetterQueue,
    topic: str,
    payload: Dict[str, Any],
    device_id: str,
    module_name: str = None
):
    """Send device unreachable error to DLQ."""
    dlq.send_to_dlq(
        original_topic=topic,
        payload=payload,
        failure_reason=FailureReason.DEVICE_UNREACHABLE,
        error_message=f"Device {device_id} is unreachable",
        device_id=device_id,
        module_name=module_name
    )
