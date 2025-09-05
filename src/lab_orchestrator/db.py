"""Database layer for Lab Platform orchestrator."""

import os
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import create_engine, Column, String, DateTime, Text, Boolean, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid


# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/labdb")
engine = create_engine(DATABASE_URL, echo=os.getenv("SQL_DEBUG", "").lower() == "true")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Models
class Device(Base):
    """Device registry table."""
    __tablename__ = "devices"
    
    device_id = Column(String(255), primary_key=True, index=True)
    modules = Column(JSON, default=list)  # List of module names
    capabilities = Column(JSON, default=dict)  # Module capabilities
    labels = Column(JSON, default=list)  # Device labels
    version = Column(String(100))
    last_seen = Column(DateTime, default=datetime.utcnow, index=True)
    online = Column(Boolean, default=True, index=True)
    metadata = Column(JSON, default=dict)  # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ModuleStatus(Base):
    """Module status snapshots."""
    __tablename__ = "module_status"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(255), index=True, nullable=False)
    module_name = Column(String(100), index=True, nullable=False)
    state = Column(String(50), index=True)
    fields = Column(JSON, default=dict)  # Module-specific fields
    online = Column(Boolean, default=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class Heartbeat(Base):
    """Device heartbeat records."""
    __tablename__ = "heartbeats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(255), index=True, nullable=False)
    online = Column(Boolean, default=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    metadata = Column(JSON, default=dict)  # Additional heartbeat data


class Command(Base):
    """Command dispatch and status log."""
    __tablename__ = "commands"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    req_id = Column(String(255), unique=True, index=True, nullable=False)
    device_id = Column(String(255), index=True, nullable=False)
    module_name = Column(String(100), index=True)
    actor = Column(String(100), index=True)  # Who initiated the command
    action = Column(String(100), index=True, nullable=False)
    params = Column(JSON, default=dict)
    
    # Status tracking
    status = Column(String(50), default="dispatched", index=True)  # dispatched, acked, failed, timeout
    dispatched_at = Column(DateTime, default=datetime.utcnow, index=True)
    acked_at = Column(DateTime, index=True)
    success = Column(Boolean, index=True)
    error_message = Column(Text)
    response_details = Column(JSON, default=dict)
    
    # Timing
    duration_ms = Column(Integer)  # Time from dispatch to ack


class Event(Base):
    """Audit log for system events."""
    __tablename__ = "events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), index=True, nullable=False)  # device_connected, command_executed, etc.
    device_id = Column(String(255), index=True)
    module_name = Column(String(100), index=True)
    actor = Column(String(100), index=True)
    description = Column(Text)
    metadata = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class Schedule(Base):
    """Scheduled tasks."""
    __tablename__ = "schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), index=True)
    device_id = Column(String(255), index=True)
    module_name = Column(String(100), index=True)
    actor = Column(String(100), index=True)
    
    # Schedule definition
    schedule_type = Column(String(50), index=True)  # once, cron
    schedule_expr = Column(String(255))  # cron expression or ISO timestamp
    commands = Column(JSON, default=list)  # List of commands to execute
    
    # Status
    active = Column(Boolean, default=True, index=True)
    last_run = Column(DateTime, index=True)
    next_run = Column(DateTime, index=True)
    run_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Database Access Layer
class DatabaseManager:
    """Database access layer for Lab Platform."""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    def create_tables(self):
        """Create all tables."""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all tables (for testing)."""
        Base.metadata.drop_all(bind=self.engine)
    
    # Device management
    def upsert_device(self, device_data: Dict[str, Any]) -> Device:
        """Insert or update device record."""
        with self.get_session() as session:
            device = session.query(Device).filter_by(device_id=device_data["device_id"]).first()
            
            if device:
                # Update existing
                for key, value in device_data.items():
                    if hasattr(device, key):
                        setattr(device, key, value)
                device.updated_at = datetime.utcnow()
            else:
                # Create new
                device = Device(**device_data)
                session.add(device)
            
            session.commit()
            session.refresh(device)
            return device
    
    def get_device(self, device_id: str) -> Optional[Device]:
        """Get device by ID."""
        with self.get_session() as session:
            return session.query(Device).filter_by(device_id=device_id).first()
    
    def get_all_devices(self, online_only: bool = False) -> List[Device]:
        """Get all devices."""
        with self.get_session() as session:
            query = session.query(Device)
            if online_only:
                query = query.filter_by(online=True)
            return query.all()
    
    # Module status
    def record_module_status(self, device_id: str, module_name: str, status_data: Dict[str, Any]) -> ModuleStatus:
        """Record module status snapshot."""
        with self.get_session() as session:
            status = ModuleStatus(
                device_id=device_id,
                module_name=module_name,
                state=status_data.get("state", "unknown"),
                fields=status_data.get("fields", {}),
                online=status_data.get("online", True)
            )
            session.add(status)
            session.commit()
            session.refresh(status)
            return status
    
    def get_latest_module_status(self, device_id: str, module_name: str) -> Optional[ModuleStatus]:
        """Get latest status for a module."""
        with self.get_session() as session:
            return session.query(ModuleStatus).filter_by(
                device_id=device_id,
                module_name=module_name
            ).order_by(ModuleStatus.timestamp.desc()).first()
    
    # Heartbeats
    def record_heartbeat(self, device_id: str, online: bool = True, metadata: Dict[str, Any] = None) -> Heartbeat:
        """Record device heartbeat."""
        with self.get_session() as session:
            heartbeat = Heartbeat(
                device_id=device_id,
                online=online,
                metadata=metadata or {}
            )
            session.add(heartbeat)
            session.commit()
            session.refresh(heartbeat)
            return heartbeat
    
    # Command tracking
    def record_command_dispatch(self, req_id: str, device_id: str, module_name: str,
                              actor: str, action: str, params: Dict[str, Any]) -> Command:
        """Record command dispatch."""
        with self.get_session() as session:
            command = Command(
                req_id=req_id,
                device_id=device_id,
                module_name=module_name,
                actor=actor,
                action=action,
                params=params,
                status="dispatched"
            )
            session.add(command)
            session.commit()
            session.refresh(command)
            return command
    
    def record_command_ack(self, req_id: str, success: bool, error_message: str = None,
                          response_details: Dict[str, Any] = None) -> Optional[Command]:
        """Record command acknowledgment."""
        with self.get_session() as session:
            command = session.query(Command).filter_by(req_id=req_id).first()
            if not command:
                return None
            
            command.status = "acked" if success else "failed"
            command.acked_at = datetime.utcnow()
            command.success = success
            command.error_message = error_message
            command.response_details = response_details or {}
            
            if command.dispatched_at:
                duration = datetime.utcnow() - command.dispatched_at
                command.duration_ms = int(duration.total_seconds() * 1000)
            
            session.commit()
            session.refresh(command)
            return command
    
    # Events
    def record_event(self, event_type: str, description: str, device_id: str = None,
                    module_name: str = None, actor: str = None, metadata: Dict[str, Any] = None) -> Event:
        """Record system event."""
        with self.get_session() as session:
            event = Event(
                event_type=event_type,
                device_id=device_id,
                module_name=module_name,
                actor=actor,
                description=description,
                metadata=metadata or {}
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            return event
    
    # Cleanup
    def cleanup_old_records(self, days: int = 30):
        """Clean up old records to prevent database bloat."""
        cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = cutoff - datetime.timedelta(days=days)
        
        with self.get_session() as session:
            # Clean up old heartbeats (keep only latest per device per day)
            session.query(Heartbeat).filter(Heartbeat.timestamp < cutoff).delete()
            
            # Clean up old module status (keep only latest per module per day)
            session.query(ModuleStatus).filter(ModuleStatus.timestamp < cutoff).delete()
            
            # Clean up old events (keep audit trail but limit size)
            session.query(Event).filter(Event.timestamp < cutoff).delete()
            
            # Don't delete commands - they're important for debugging
            
            session.commit()


# Global database manager instance
db_manager = DatabaseManager()


# Context manager for database sessions
class db_session:
    """Context manager for database sessions."""
    
    def __enter__(self) -> Session:
        self.session = db_manager.get_session()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()
