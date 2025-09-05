"""Pydantic models for API and data validation."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
from uuid import UUID


# Base models
class TimestampedModel(BaseModel):
    """Base model with timestamp fields."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Device models
class DeviceCapabilities(BaseModel):
    """Device module capabilities."""
    viewer: bool = False
    recorder: bool = False
    serial_control: bool = False
    custom_commands: Dict[str, Any] = Field(default_factory=dict)


class DeviceMetadata(BaseModel):
    """Device metadata from registration."""
    device_id: str = Field(..., min_length=1, max_length=255)
    modules: List[str] = Field(default_factory=list)
    capabilities: Dict[str, DeviceCapabilities] = Field(default_factory=dict)
    labels: List[str] = Field(default_factory=list)
    version: str = Field(default="unknown")
    online: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('device_id')
    def validate_device_id(cls, v):
        if not v or not v.strip():
            raise ValueError('device_id cannot be empty')
        return v.strip()


class DeviceStatus(BaseModel):
    """Device status information."""
    device_id: str
    online: bool
    last_seen: datetime
    modules: List[str] = Field(default_factory=list)
    uptime_seconds: Optional[int] = None


class ModuleState(BaseModel):
    """Module state information."""
    state: str = "idle"
    online: bool = True
    fields: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Command models
class CommandEnvelope(BaseModel):
    """MQTT command envelope."""
    req_id: str = Field(..., min_length=1)
    actor: str = Field(..., regex=r'^(api|orchestrator|user|host:.+)$')
    ts: str = Field(...)  # ISO timestamp
    action: str = Field(..., min_length=1)
    params: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('ts')
    def validate_timestamp(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError('Invalid timestamp format')


class CommandAck(BaseModel):
    """Command acknowledgment."""
    req_id: str
    success: bool
    action: str
    actor: str
    code: str = "OK"
    error: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    ts: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + 'Z')


class CommandRecord(BaseModel):
    """Command execution record."""
    id: UUID
    req_id: str
    device_id: str
    module_name: Optional[str]
    actor: str
    action: str
    params: Dict[str, Any]
    status: str  # dispatched, acked, failed, timeout
    dispatched_at: datetime
    acked_at: Optional[datetime]
    success: Optional[bool]
    error_message: Optional[str]
    response_details: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[int]


# Event models
class SystemEvent(BaseModel):
    """System event record."""
    event_type: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    device_id: Optional[str] = None
    module_name: Optional[str] = None
    actor: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Schedule models
class ScheduleCommand(BaseModel):
    """Command to execute in a schedule."""
    device_id: str
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)


class ScheduleDefinition(BaseModel):
    """Scheduled task definition."""
    name: str = Field(..., min_length=1, max_length=255)
    device_id: Optional[str] = None
    module_name: Optional[str] = None
    actor: str = "scheduler"
    schedule_type: str = Field(..., regex=r'^(once|cron)$')
    schedule_expr: str = Field(..., min_length=1)  # ISO timestamp or cron
    commands: List[ScheduleCommand] = Field(..., min_items=1)
    active: bool = True
    
    @validator('schedule_expr')
    def validate_schedule_expr(cls, v, values):
        schedule_type = values.get('schedule_type')
        
        if schedule_type == 'once':
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('Invalid timestamp format for once schedule')
        elif schedule_type == 'cron':
            parts = v.split()
            if len(parts) != 5:
                raise ValueError('Cron expression must have 5 parts')
        
        return v


# API Request/Response models
class NDIStartRequest(BaseModel):
    """NDI start viewer request."""
    device_id: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)


class NDIStopRequest(BaseModel):
    """NDI stop viewer request."""
    device_id: str = Field(..., min_length=1)


class NDIRecordStartRequest(BaseModel):
    """NDI start recording request."""
    device_id: str = Field(..., min_length=1)
    source: Optional[str] = None
    output_path: Optional[str] = None


class ProjectorPowerRequest(BaseModel):
    """Projector power control request."""
    device_id: str = Field(..., min_length=1)
    power: str = Field(..., regex=r'^(on|off)$')


class ProjectorInputRequest(BaseModel):
    """Projector input selection request."""
    device_id: str = Field(..., min_length=1)
    input: str = Field(..., regex=r'^(HDMI1|HDMI2)$')


class ProjectorAdjustRequest(BaseModel):
    """Projector image adjustment request."""
    device_id: str = Field(..., min_length=1)
    adjustment: str = Field(..., regex=r'^(H-IMAGE-SHIFT|V-IMAGE-SHIFT|H-KEYSTONE|V-KEYSTONE)$')
    value: int = Field(..., ge=-100, le=100)
    
    @validator('value')
    def validate_adjustment_range(cls, v, values):
        adjustment = values.get('adjustment')
        
        if adjustment in ['H-KEYSTONE', 'V-KEYSTONE']:
            if not (-40 <= v <= 40):
                raise ValueError('Keystone value must be between -40 and 40')
        elif adjustment in ['H-IMAGE-SHIFT', 'V-IMAGE-SHIFT']:
            if not (-100 <= v <= 100):
                raise ValueError('Image shift value must be between -100 and 100')
        
        return v


# Response models
class APIResponse(BaseModel):
    """Standard API response."""
    ok: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DeviceListResponse(BaseModel):
    """Device list API response."""
    devices: Dict[str, DeviceMetadata]
    count: int
    online_count: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NDISourcesResponse(BaseModel):
    """NDI sources discovery response."""
    sources: List[str]
    count: int
    discovery_error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CommandDispatchResponse(BaseModel):
    """Command dispatch response."""
    ok: bool = True
    dispatched: bool = True
    device_id: str
    action: str
    req_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
