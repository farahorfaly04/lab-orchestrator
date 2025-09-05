# Plugin Template Standardization Guide

This guide explains the standardized plugin template system for the Lab Platform UI.

## Overview

All plugin UIs now follow a consistent design pattern using a base template system that ensures:
- **Consistent visual design** across all plugins
- **Standardized functionality** (device selection, status display, activity logging)
- **Reusable JavaScript framework** for common operations
- **Easy customization** for plugin-specific features

## Template Structure

### 1. Base Template (`plugin_base.html`)

The foundation template that provides:
- **Standard page header** with plugin title and description
- **Summary cards** showing device statistics
- **Device selection panel** with refresh functionality
- **Device status panel** with loading states
- **Activity log** with auto-refresh and clear functionality
- **Quick actions** for common operations
- **JavaScript framework** (`StandardPlugin` class)

### 2. Plugin-Specific Templates

Individual plugins extend the base template and customize:
- **Plugin configuration** via `plugin_config` variable
- **Custom controls** in the `plugin_controls` block
- **JavaScript implementation** extending `StandardPlugin` class

### 3. Generic Shell Template (`plugin_shell.html`)

A fallback template for plugins without custom implementations that provides:
- **Generic interface** with placeholder functionality
- **Developer guidance** for creating custom templates
- **Basic plugin structure** ready for customization

## Creating a New Plugin Template

### Step 1: Create Plugin Template File

Create a new template file: `your_plugin_standard.html`

```html
{% extends "plugin_base.html" %}

{% set plugin_config = {
    'title': 'Your Plugin Name',
    'icon': '🔧',
    'description': 'Description of your plugin functionality',
    'device_type': 'Your Device Type',
    'api_endpoint': 'your_api_endpoint',
    'active_label': 'Active Status Label'
} %}

{% block plugin_controls %}
<!-- Your custom controls here -->
<div class="row mt-3">
    <div class="col-md-12">
        <div class="card">
            <div class="card-header">
                <h5>🎛️ Custom Controls</h5>
            </div>
            <div class="card-body">
                <!-- Plugin-specific UI elements -->
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block plugin_scripts %}
// Your Plugin Implementation
class YourPlugin extends StandardPlugin {
    constructor() {
        super({
            title: 'Your Plugin Name',
            api_endpoint: 'your_api_endpoint'
        });
    }
    
    setupPluginEventListeners() {
        // Add your custom event listeners
    }
    
    // Override methods as needed
    async startDevice() {
        // Implement start functionality
    }
}

// Initialize your plugin
const yourPlugin = new YourPlugin();
{% endblock %}
```

### Step 2: Configure Plugin Settings

The `plugin_config` object controls the plugin appearance:

- **`title`**: Display name in the header
- **`icon`**: Emoji icon for the plugin
- **`description`**: Subtitle description
- **`device_type`**: Label for device selection dropdown
- **`api_endpoint`**: API endpoint prefix for device operations
- **`active_label`**: Label for the "active" summary card

### Step 3: Implement Custom Controls

Use the `plugin_controls` block to add your specific UI elements:

```html
{% block plugin_controls %}
<div class="row mt-3">
    <!-- Your control panels here -->
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5>🎛️ Control Panel</h5>
            </div>
            <div class="card-body">
                <!-- Controls -->
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### Step 4: Extend JavaScript Class

Create a class extending `StandardPlugin`:

```javascript
class YourPlugin extends StandardPlugin {
    constructor() {
        super({
            title: 'Your Plugin Name',
            api_endpoint: 'your_api_endpoint'
        });
    }
    
    setupPluginEventListeners() {
        // Add event listeners for your custom controls
        document.getElementById('yourButton').addEventListener('click', () => {
            this.yourCustomMethod();
        });
    }
    
    // Override standard methods
    async startDevice() {
        // Custom start implementation
    }
    
    async stopDevice() {
        // Custom stop implementation
    }
    
    // Add custom methods
    async yourCustomMethod() {
        // Custom functionality
    }
}
```

## Standard Features Available

### Device Management
- `loadDevices()` - Load and display available devices
- `updateDeviceStatus()` - Update selected device status
- `renderDeviceStatus(device)` - Override to customize status display

### Activity Logging
- `logActivity(message, type)` - Log messages ('info', 'success', 'warning', 'error')
- `clearLog()` - Clear activity log
- Auto-refresh functionality with toggle

### Summary Cards
- Automatic device count updates
- Online/offline status tracking
- Custom "active" count (override `getActiveDeviceCount()`)
- Status indicator updates

### Standard API Methods
- `getStatus()` - Get device status
- `startDevice()` - Start device (override for custom behavior)
- `restartDevice()` - Restart device (override for custom behavior)
- `stopDevice()` - Stop device (override for custom behavior)

## CSS Classes Available

### Card Styles
- `.card` - Standard card container
- `.card-header` - Card header with gradient background
- `.card-body` - Card content area

### Button Styles
- `.btn.shadow-hover` - Buttons with hover effects
- `.btn-primary`, `.btn-success`, `.btn-warning`, `.btn-danger` - Colored buttons
- `.btn-outline-*` - Outline button variants

### Status Indicators
- `.badge.badge-success` - Green status badge
- `.badge.badge-danger` - Red status badge
- `.badge.badge-info` - Blue status badge
- `.status-online`, `.status-offline` - Status with icons

### Layout Classes
- `.device-status-row` - Status display rows
- `.activity-log` - Activity log container
- `.quick-actions` - Quick actions button container

## Examples

See the following implementations:
- `ndi_standard.html` - Complex plugin with multiple control panels
- `projector_standard.html` - Plugin with navigation grid and controls
- `plugin_shell.html` - Generic template for new plugins

## Migration Guide

To migrate existing plugins:

1. **Create new standardized template** following the structure above
2. **Move custom controls** to the `plugin_controls` block
3. **Refactor JavaScript** to extend `StandardPlugin` class
4. **Update API calls** to use standard methods where possible
5. **Test functionality** to ensure all features work correctly

## Benefits

- **Consistent user experience** across all plugins
- **Reduced development time** for new plugins
- **Standardized functionality** (logging, device management, status display)
- **Easy maintenance** and updates
- **Professional appearance** with modern UI components
- **Responsive design** that works on all devices
