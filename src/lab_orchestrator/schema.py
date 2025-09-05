"""Pydantic schema validation for MQTT messages and API requests."""

from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class ActorType(str, Enum):
    """Valid actor types."""
    API = "api"
    ORCHESTRATOR = "orchestrator"
    USER = "user"
    HOST_PREFIX = "host:"


class ActionType(str, Enum):
    """Common action types."""
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    STATUS = "status"
    CONFIGURE = "configure"
    SET_INPUT = "set_input"
    RECORD_START = "record_start"
    RECORD_STOP = "record_stop"
    POWER_ON = "power_on"
    POWER_OFF = "power_off"
    NAVIGATE = "navigate"
    ADJUST_IMAGE = "adjust_image"


class CommandStatus(str, Enum):
    """Command execution status."""
    DISPATCHED = "dispatched"
    ACKED = "acked"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ResponseCode(str, Enum):
    """Response codes for acknowledgments."""
    OK = "OK"
    BAD_JSON = "BAD_JSON"
    BAD_REQUEST = "BAD_REQUEST"
    DEVICE_ERROR = "DEVICE_ERROR"
    MODULE_ERROR = "MODULE_ERROR"
    EXCEPTION = "EXCEPTION"
    TIMEOUT = "TIMEOUT"
    DISPATCHED = "DISPATCHED"
    SCHEDULED = "SCHEDULED"
    IN_USE = "IN_USE"
    NOT_OWNER = "NOT_OWNER"
    BAD_ACTION = "BAD_ACTION"


class MQTTCommandEnvelope(BaseModel):
    """Strict MQTT command envelope schema."""
    req_id: str = Field(..., min_length=1, max_length=255, description="Unique request identifier")
    actor: str = Field(..., min_length=1, max_length=100, description="Actor initiating the command")
    ts: str = Field(..., description="ISO 8601 timestamp")
    action: str = Field(..., min_length=1, max_length=100, description="Command action")
    params: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")
    
    @validator('actor')
    def validate_actor(cls, v):
        """Validate actor format."""
        if v in [ActorType.API, ActorType.ORCHESTRATOR, ActorType.USER]:
            return v
        elif v.startswith(ActorType.HOST_PREFIX):
            return v
        else:
            raise ValueError(f"Invalid actor: {v}. Must be one of: api, orchestrator, user, or host:*")
    
    @validator('ts')
    def validate_timestamp(cls, v):
        """Validate ISO 8601 timestamp."""
        try:
            # Try to parse the timestamp
            if v.endswith('Z'):
                datetime.fromisoformat(v[:-1] + '+00:00')
            else:
                datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {v}. Must be ISO 8601.")
    
    @validator('action')
    def validate_action(cls, v):
        """Validate action is not empty."""
        if not v.strip():
            raise ValueError("Action cannot be empty")
        return v.strip()
    
    @validator('params')
    def validate_params_size(cls, v):
        """Validate params size to prevent oversized messages."""
        import json
        try:
            serialized = json.dumps(v)
            if len(serialized.encode('utf-8')) > 64 * 1024:  # 64KB limit
                raise ValueError("Params too large (>64KB)")
            return v
        except (TypeError, ValueError) as e:
            if "too large" in str(e):
                raise e
            raise ValueError("Params must be JSON serializable")


class MQTTAckEnvelope(BaseModel):
    """Strict MQTT acknowledgment envelope schema."""
    req_id: str = Field(..., min_length=1, max_length=255)
    success: bool = Field(...)
    action: str = Field(..., min_length=1, max_length=100)
    actor: str = Field(..., min_length=1, max_length=100)
    code: ResponseCode = Field(default=ResponseCode.OK)
    error: Optional[str] = Field(None, max_length=1000)
    details: Dict[str, Any] = Field(default_factory=dict)
    ts: str = Field(..., description="ISO 8601 timestamp")
    
    @validator('ts')
    def validate_timestamp(cls, v):
        """Validate ISO 8601 timestamp."""
        try:
            if v.endswith('Z'):
                datetime.fromisoformat(v[:-1] + '+00:00')
            else:
                datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {v}")
    
    @validator('details')
    def validate_details_size(cls, v):
        """Validate details size."""
        import json
        try:
            serialized = json.dumps(v)
            if len(serialized.encode('utf-8')) > 32 * 1024:  # 32KB limit
                raise ValueError("Details too large (>32KB)")
            return v
        except (TypeError, ValueError) as e:
            if "too large" in str(e):
                raise e
            raise ValueError("Details must be JSON serializable")


class DeviceMetaEnvelope(BaseModel):
    """Device metadata envelope schema."""
    device_id: str = Field(..., min_length=1, max_length=255)
    modules: List[str] = Field(default_factory=list)
    capabilities: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    labels: List[str] = Field(default_factory=list, max_items=20)
    version: str = Field(default="unknown", max_length=100)
    ts: str = Field(..., description="ISO 8601 timestamp")
    
    @validator('device_id')
    def validate_device_id(cls, v):
        """Validate device ID format."""
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Device ID can only contain alphanumeric characters, hyphens, and underscores")
        return v
    
    @validator('modules')
    def validate_modules(cls, v):
        """Validate module names."""
        import re
        for module in v:
            if not re.match(r'^[a-zA-Z0-9_]+$', module):
                raise ValueError(f"Invalid module name: {module}")
        return v
    
    @validator('labels')
    def validate_labels(cls, v):
        """Validate labels."""
        for label in v:
            if len(label) > 50:
                raise ValueError("Label too long (>50 characters)")
        return v


class DeviceStatusEnvelope(BaseModel):
    """Device status envelope schema."""
    online: bool = Field(...)
    device_id: str = Field(..., min_length=1, max_length=255)
    ts: str = Field(..., description="ISO 8601 timestamp")
    uptime_seconds: Optional[float] = Field(None, ge=0)
    memory_usage: Optional[Dict[str, Any]] = Field(None)
    
    @validator('ts')
    def validate_timestamp(cls, v):
        """Validate timestamp."""
        try:
            if v.endswith('Z'):
                datetime.fromisoformat(v[:-1] + '+00:00')
            else:
                datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {v}")


class ModuleStatusEnvelope(BaseModel):
    """Module status envelope schema."""
    state: str = Field(..., min_length=1, max_length=50)
    online: bool = Field(default=True)
    ts: str = Field(..., description="ISO 8601 timestamp")
    fields: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('fields')
    def validate_fields_size(cls, v):
        """Validate fields size."""
        import json
        try:
            serialized = json.dumps(v)
            if len(serialized.encode('utf-8')) > 16 * 1024:  # 16KB limit
                raise ValueError("Fields too large (>16KB)")
            return v
        except (TypeError, ValueError) as e:
            if "too large" in str(e):
                raise e
            raise ValueError("Fields must be JSON serializable")


# NDI-specific schemas
class NDICommandParams(BaseModel):
    """NDI command parameters schema."""
    device_id: str = Field(..., min_length=1, max_length=255)
    source: Optional[str] = Field(None, max_length=500)
    output_path: Optional[str] = Field(None, max_length=1000)
    
    @validator('source')
    def validate_source(cls, v):
        """Validate NDI source format."""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Source cannot be empty string")
        return v


# Projector-specific schemas
class ProjectorCommandParams(BaseModel):
    """Projector command parameters schema."""
    device_id: str = Field(..., min_length=1, max_length=255)
    input: Optional[str] = Field(None, regex=r'^(HDMI1|HDMI2)$')
    ratio: Optional[str] = Field(None, regex=r'^(4:3|16:9)$')
    direction: Optional[str] = Field(None, regex=r'^(UP|DOWN|LEFT|RIGHT|ENTER|MENU|BACK)$')
    adjustment: Optional[str] = Field(None, regex=r'^(H-IMAGE-SHIFT|V-IMAGE-SHIFT|H-KEYSTONE|V-KEYSTONE)$')
    value: Optional[int] = Field(None, ge=-100, le=100)
    command: Optional[str] = Field(None, max_length=200)  # Raw command
    
    @validator('value')
    def validate_adjustment_value(cls, v, values):
        """Validate adjustment value ranges."""
        if v is None:
            return v
        
        adjustment = values.get('adjustment')
        if adjustment in ['H-KEYSTONE', 'V-KEYSTONE']:
            if not (-40 <= v <= 40):
                raise ValueError('Keystone value must be between -40 and 40')
        elif adjustment in ['H-IMAGE-SHIFT', 'V-IMAGE-SHIFT']:
            if not (-100 <= v <= 100):
                raise ValueError('Image shift value must be between -100 and 100')
        
        return v


# Schedule schemas
class ScheduleCommandSchema(BaseModel):
    """Schedule command schema."""
    device_id: str = Field(..., min_length=1, max_length=255)
    action: str = Field(..., min_length=1, max_length=100)
    params: Dict[str, Any] = Field(default_factory=dict)


class ScheduleSchema(BaseModel):
    """Schedule definition schema."""
    name: str = Field(..., min_length=1, max_length=255)
    device_id: Optional[str] = Field(None, max_length=255)
    module_name: Optional[str] = Field(None, max_length=100)
    actor: str = Field(default="scheduler", max_length=100)
    schedule_type: str = Field(..., regex=r'^(once|cron)$')
    schedule_expr: str = Field(..., min_length=1, max_length=255)
    commands: List[ScheduleCommandSchema] = Field(..., min_items=1, max_items=50)
    active: bool = Field(default=True)
    
    @validator('schedule_expr')
    def validate_schedule_expression(cls, v, values):
        """Validate schedule expression format."""
        schedule_type = values.get('schedule_type')
        
        if schedule_type == 'once':
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('Invalid timestamp format for once schedule')
        elif schedule_type == 'cron':
            parts = v.split()
            if len(parts) != 5:
                raise ValueError('Cron expression must have 5 parts (minute hour day month weekday)')
            
            # Basic validation of cron parts
            for i, part in enumerate(parts):
                if part == '*':
                    continue
                if ',' in part:
                    # Multiple values
                    for val in part.split(','):
                        if not val.isdigit():
                            raise ValueError(f'Invalid cron value: {val}')
                elif '/' in part:
                    # Step values
                    base, step = part.split('/', 1)
                    if base != '*' and not base.isdigit():
                        raise ValueError(f'Invalid cron step base: {base}')
                    if not step.isdigit():
                        raise ValueError(f'Invalid cron step: {step}')
                elif '-' in part:
                    # Range values
                    start, end = part.split('-', 1)
                    if not start.isdigit() or not end.isdigit():
                        raise ValueError(f'Invalid cron range: {part}')
                elif not part.isdigit():
                    raise ValueError(f'Invalid cron value: {part}')
        
        return v


# Validation functions
def validate_mqtt_command(payload: Dict[str, Any]) -> MQTTCommandEnvelope:
    """Validate and parse MQTT command envelope."""
    return MQTTCommandEnvelope(**payload)


def validate_mqtt_ack(payload: Dict[str, Any]) -> MQTTAckEnvelope:
    """Validate and parse MQTT acknowledgment envelope."""
    return MQTTAckEnvelope(**payload)


def validate_device_meta(payload: Dict[str, Any]) -> DeviceMetaEnvelope:
    """Validate and parse device metadata envelope."""
    return DeviceMetaEnvelope(**payload)


def validate_device_status(payload: Dict[str, Any]) -> DeviceStatusEnvelope:
    """Validate and parse device status envelope."""
    return DeviceStatusEnvelope(**payload)


def validate_module_status(payload: Dict[str, Any]) -> ModuleStatusEnvelope:
    """Validate and parse module status envelope."""
    return ModuleStatusEnvelope(**payload)


def validate_ndi_params(params: Dict[str, Any]) -> NDICommandParams:
    """Validate NDI command parameters."""
    return NDICommandParams(**params)


def validate_projector_params(params: Dict[str, Any]) -> ProjectorCommandParams:
    """Validate projector command parameters."""
    return ProjectorCommandParams(**params)


def validate_schedule(schedule_data: Dict[str, Any]) -> ScheduleSchema:
    """Validate schedule definition."""
    return ScheduleSchema(**schedule_data)
