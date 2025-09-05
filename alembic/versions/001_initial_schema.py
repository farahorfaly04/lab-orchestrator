"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create initial schema."""
    
    # Devices table
    op.create_table('devices',
        sa.Column('device_id', sa.String(255), primary_key=True),
        sa.Column('modules', JSON, nullable=True),
        sa.Column('capabilities', JSON, nullable=True),
        sa.Column('labels', JSON, nullable=True),
        sa.Column('version', sa.String(100), nullable=True),
        sa.Column('last_seen', sa.DateTime, nullable=True),
        sa.Column('online', sa.Boolean, nullable=True),
        sa.Column('metadata', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True)
    )
    op.create_index('ix_devices_device_id', 'devices', ['device_id'])
    op.create_index('ix_devices_last_seen', 'devices', ['last_seen'])
    op.create_index('ix_devices_online', 'devices', ['online'])
    
    # Module status table
    op.create_table('module_status',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('device_id', sa.String(255), nullable=False),
        sa.Column('module_name', sa.String(100), nullable=False),
        sa.Column('state', sa.String(50), nullable=True),
        sa.Column('fields', JSON, nullable=True),
        sa.Column('online', sa.Boolean, nullable=True),
        sa.Column('timestamp', sa.DateTime, nullable=True)
    )
    op.create_index('ix_module_status_device_id', 'module_status', ['device_id'])
    op.create_index('ix_module_status_module_name', 'module_status', ['module_name'])
    op.create_index('ix_module_status_state', 'module_status', ['state'])
    op.create_index('ix_module_status_timestamp', 'module_status', ['timestamp'])
    
    # Heartbeats table
    op.create_table('heartbeats',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('device_id', sa.String(255), nullable=False),
        sa.Column('online', sa.Boolean, nullable=True),
        sa.Column('timestamp', sa.DateTime, nullable=True),
        sa.Column('metadata', JSON, nullable=True)
    )
    op.create_index('ix_heartbeats_device_id', 'heartbeats', ['device_id'])
    op.create_index('ix_heartbeats_online', 'heartbeats', ['online'])
    op.create_index('ix_heartbeats_timestamp', 'heartbeats', ['timestamp'])
    
    # Commands table
    op.create_table('commands',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('req_id', sa.String(255), nullable=False),
        sa.Column('device_id', sa.String(255), nullable=False),
        sa.Column('module_name', sa.String(100), nullable=True),
        sa.Column('actor', sa.String(100), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('params', JSON, nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('dispatched_at', sa.DateTime, nullable=True),
        sa.Column('acked_at', sa.DateTime, nullable=True),
        sa.Column('success', sa.Boolean, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('response_details', JSON, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True)
    )
    op.create_index('ix_commands_req_id', 'commands', ['req_id'], unique=True)
    op.create_index('ix_commands_device_id', 'commands', ['device_id'])
    op.create_index('ix_commands_module_name', 'commands', ['module_name'])
    op.create_index('ix_commands_actor', 'commands', ['actor'])
    op.create_index('ix_commands_action', 'commands', ['action'])
    op.create_index('ix_commands_status', 'commands', ['status'])
    op.create_index('ix_commands_dispatched_at', 'commands', ['dispatched_at'])
    op.create_index('ix_commands_success', 'commands', ['success'])
    
    # Events table
    op.create_table('events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('device_id', sa.String(255), nullable=True),
        sa.Column('module_name', sa.String(100), nullable=True),
        sa.Column('actor', sa.String(100), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('metadata', JSON, nullable=True),
        sa.Column('timestamp', sa.DateTime, nullable=True)
    )
    op.create_index('ix_events_event_type', 'events', ['event_type'])
    op.create_index('ix_events_device_id', 'events', ['device_id'])
    op.create_index('ix_events_module_name', 'events', ['module_name'])
    op.create_index('ix_events_actor', 'events', ['actor'])
    op.create_index('ix_events_timestamp', 'events', ['timestamp'])
    
    # Schedules table
    op.create_table('schedules',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('device_id', sa.String(255), nullable=True),
        sa.Column('module_name', sa.String(100), nullable=True),
        sa.Column('actor', sa.String(100), nullable=True),
        sa.Column('schedule_type', sa.String(50), nullable=True),
        sa.Column('schedule_expr', sa.String(255), nullable=True),
        sa.Column('commands', JSON, nullable=True),
        sa.Column('active', sa.Boolean, nullable=True),
        sa.Column('last_run', sa.DateTime, nullable=True),
        sa.Column('next_run', sa.DateTime, nullable=True),
        sa.Column('run_count', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True)
    )
    op.create_index('ix_schedules_name', 'schedules', ['name'])
    op.create_index('ix_schedules_device_id', 'schedules', ['device_id'])
    op.create_index('ix_schedules_module_name', 'schedules', ['module_name'])
    op.create_index('ix_schedules_actor', 'schedules', ['actor'])
    op.create_index('ix_schedules_schedule_type', 'schedules', ['schedule_type'])
    op.create_index('ix_schedules_active', 'schedules', ['active'])
    op.create_index('ix_schedules_last_run', 'schedules', ['last_run'])
    op.create_index('ix_schedules_next_run', 'schedules', ['next_run'])


def downgrade():
    """Drop all tables."""
    op.drop_table('schedules')
    op.drop_table('events')
    op.drop_table('commands')
    op.drop_table('heartbeats')
    op.drop_table('module_status')
    op.drop_table('devices')
