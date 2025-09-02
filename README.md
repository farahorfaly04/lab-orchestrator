# Lab Platform Orchestrator

Central coordination service for the Lab Platform. This FastAPI application manages device registry, plugin system, and provides web UI for monitoring and control.

## Features

- **Device Registry**: Track and manage connected devices
- **Plugin System**: Extensible functionality via plugins
- **Web UI**: Dashboard for monitoring and control
- **REST API**: Programmatic access to platform features
- **MQTT Communication**: Real-time device communication
- **Resource Locking**: Prevent device conflicts
- **Task Scheduling**: Automated command execution

## Installation

```bash
pip install -e .
```

## Usage

### As a Package
```bash
lab-orchestrator
```

### Development
```bash
uvicorn lab_orchestrator.host:app --reload
```

### Docker
```bash
docker build -t lab-orchestrator .
docker run -p 8000:8000 lab-orchestrator
```

## Configuration

Set environment variables:
- `MQTT_HOST`: MQTT broker hostname
- `MQTT_PORT`: MQTT broker port (default: 1883)
- `MQTT_USERNAME`: MQTT username
- `MQTT_PASSWORD`: MQTT password
- `HOST`: Bind host (default: 0.0.0.0)
- `PORT`: Bind port (default: 8000)

## API Endpoints

- `GET /`: Main dashboard
- `GET /api/registry`: Device registry
- `DELETE /api/registry/devices/{device_id}`: Remove device
- `GET /ui/devices`: Device management UI

## Plugin Development

Extend `OrchestratorPlugin` class:

```python
from lab_orchestrator.plugin_api import OrchestratorPlugin

class MyPlugin(OrchestratorPlugin):
    module_name = "my_plugin"
    
    def mqtt_topic_filters(self):
        return [f"/lab/orchestrator/{self.module_name}/cmd"]
    
    def handle_mqtt(self, topic, payload):
        # Handle MQTT messages
        pass
```

## Architecture

- **FastAPI**: Web framework
- **MQTT**: Device communication
- **Plugin System**: Dynamic feature loading
- **Jinja2**: Template rendering
- **APScheduler**: Task scheduling
