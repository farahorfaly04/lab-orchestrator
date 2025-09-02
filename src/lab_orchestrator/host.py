"""Main orchestrator host application."""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from importlib import import_module
from pathlib import Path
import importlib.util
import sys
import os

from lab_orchestrator.plugin_api import OrchestratorPlugin, PluginContext
from lab_orchestrator.services.mqtt import SharedMQTT
from lab_orchestrator.services.registry import Registry
from lab_orchestrator.services.scheduler import Scheduler
from lab_orchestrator.services.events import ack, now_iso
from lab_orchestrator import config


app = FastAPI(title="Lab Platform Orchestrator")

# Setup UI
templates_dir = Path(__file__).parent / "ui" / "templates"
static_dir = Path(__file__).parent / "ui" / "static"

templates = Jinja2Templates(directory=str(templates_dir))
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Core services
mqtt = SharedMQTT(**config.MQTT)
registry = Registry()
scheduler = Scheduler()

_plugins: dict[str, OrchestratorPlugin] = {}


def _load_class(path: str):
    """Load a class from a module path."""
    mod, cls = path.split(":")
    m = import_module(mod)
    return getattr(m, cls)


def _load_feature_plugins():
    """Dynamically load plugins from features/ directory."""
    # Look for features in the main repo
    features_dir = Path(__file__).resolve().parents[4] / "features"
    if not features_dir.exists():
        return
    
    for plugin_dir in features_dir.glob("plugins/*/"):
        manifest_file = plugin_dir / "manifest.yaml"
        if not manifest_file.exists():
            continue
            
        try:
            import yaml
            with open(manifest_file) as f:
                manifest = yaml.safe_load(f)
            
            # Add plugin directory to Python path
            if str(plugin_dir) not in sys.path:
                sys.path.insert(0, str(plugin_dir))
            
            plugin_config = {
                "module": manifest.get("name"),
                "path": manifest.get("plugin_class"),
                "settings": manifest.get("settings", {})
            }
            config.PLUGINS.append(plugin_config)
        except Exception as e:
            print(f"Failed to load plugin from {plugin_dir}: {e}")


def load_plugins():
    """Load all configured plugins."""
    _load_feature_plugins()
    
    for p in config.PLUGINS:
        try:
            Cls = _load_class(p["path"])  # type: ignore
            ctx = PluginContext(
                mqtt=mqtt, 
                registry=registry, 
                scheduler=scheduler, 
                settings=p.get("settings", {})
            )
            inst: OrchestratorPlugin = Cls(ctx)
            _plugins[inst.module_name] = inst
            mqtt.subscribe(inst.mqtt_topic_filters(), inst.handle_mqtt)
            
            # Setup API routes
            router = inst.api_router()
            if router:
                app.include_router(
                    router, 
                    prefix=f"/api/{inst.module_name}", 
                    tags=[inst.module_name]
                )
            
            # Setup UI routes
            ui = inst.ui_mount()
            if ui:
                path = ui["path"]
                title = ui["title"]
                tpl = ui["template"]

                @app.get(path, response_class=HTMLResponse)
                async def ui_page(request: Request, _title=title, _tpl=tpl):
                    return templates.TemplateResponse(
                        _tpl, 
                        {
                            "request": request, 
                            "title": _title, 
                            "module": path.split("/")[-1], 
                            "plugins": list(_plugins.keys())
                        }
                    )
            
            inst.start()
            print(f"Loaded plugin: {inst.module_name}")
        except Exception as e:
            print(f"Failed to load plugin {p}: {e}")


@app.on_event("startup")
def on_start():
    """Application startup handler."""
    # Subscribe device meta/status to build registry
    def _dev_cb(topic, payload):
        did = payload.get("device_id")
        if not did:
            return
        d = registry.devices.get(did, {})
        d.update(payload)
        registry.devices[did] = d
        # Publish registry snapshot (retained)
        snap = registry.snapshot()
        snap["ts"] = now_iso()
        snap["modules"] = list(_plugins.keys())
        mqtt.publish_json("/lab/orchestrator/registry", snap, qos=1, retain=True)

    # Subscribe to device updates
    mqtt.subscribe(["/lab/device/+/meta", "/lab/device/+/status"], _dev_cb)
    load_plugins()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "plugins": list(_plugins.keys())}
    )


@app.get("/api/registry", response_class=JSONResponse)
async def api_registry():
    """Get registry snapshot."""
    snap = registry.snapshot()
    snap["ts"] = now_iso()
    snap["modules"] = list(_plugins.keys())
    return JSONResponse(content=snap)


@app.delete("/api/registry/devices/{device_id}")
async def delete_device(device_id: str):
    """Remove a device from the registry."""
    if device_id not in registry.devices:
        raise HTTPException(status_code=404, detail="unknown device")
    
    # Clear retained meta/status from broker so the device does not reappear
    mqtt.publish_raw(f"/lab/device/{device_id}/meta", payload=None, qos=1, retain=True)
    mqtt.publish_raw(f"/lab/device/{device_id}/status", payload=None, qos=1, retain=True)
    
    # Remove from registry and publish snapshot
    try:
        del registry.devices[device_id]
    except Exception:
        pass
    
    snap = registry.snapshot()
    snap["ts"] = now_iso()
    snap["modules"] = list(_plugins.keys())
    mqtt.publish_json("/lab/orchestrator/registry", snap, qos=1, retain=True)
    return {"ok": True, "removed": device_id}


@app.get("/ui/devices", response_class=HTMLResponse)
async def devices_page(request: Request):
    """Devices management page."""
    return templates.TemplateResponse(
        "devices.html", 
        {
            "request": request, 
            "title": "Devices", 
            "plugins": list(_plugins.keys())
        }
    )


def main():
    """Main entry point."""
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
