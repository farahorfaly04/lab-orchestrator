"""Configuration for the Lab Orchestrator."""

import os
from pathlib import Path

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    # Support .env placed in various locations
    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent.parent.parent / ".env",  # infra/.env when running from repo
        here.parent.parent / ".env",                # orchestrator/.env
        Path.cwd() / ".env",                        # current working directory
    ]
    for env_path in candidates:
        if env_path.exists():
            load_dotenv(env_path)
            break
except Exception:
    pass

def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)

# MQTT Configuration
MQTT = {
    "host": _env("MQTT_HOST", "localhost"),
    "port": int(os.getenv("MQTT_PORT", "1883")),
    "username": _env("MQTT_USERNAME", "mqtt"),
    "password": _env("MQTT_PASSWORD", "public"),
}

# Plugin Configuration - will be loaded dynamically from features/
PLUGINS = []
