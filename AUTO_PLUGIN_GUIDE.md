# Automatic Plugin System

Plugins are now **automatically loaded and integrated** - no manual code changes needed!

## How It Works

### Automatic Integration

Plugins are automatically integrated into dothttp through:

1. **Import-time integration** - When `dothttp` or `dotextensions` is imported
2. **Auto-patching** - `HttpDef.get_response()` is automatically wrapped with plugin hooks
3. **Lazy loading** - Plugins load only when first needed

```python
# This happens automatically - no action needed!
from dothttp.plugin_system import ensure_integrated
ensure_integrated()  # Auto-patches request execution
```

### Where Integration Happens

- `dothttp/__main__.py` - CLI entry point
- `dotextensions/__init__.py` - Extension server
- `dothttp/plugin_system/__init__.py` - Plugin module itself

## CLI Commands

### List Plugins

```bash
# List all loaded plugins
dothttp plugin list

# Show detailed information
dothttp plugin list -v
```

Example output:
```
Loaded Plugins (2):

  ✓ hello (v1.0.0)
  ✓ request-logger (v1.0.0)

Available but not enabled (1):
  ○ auth-helper

Enable in ~/.config/dothttp-plugins/enabled.json
```

### Create a Plugin

```bash
# Create from basic template
dothttp plugin create my-plugin

# Create from logger template
dothttp plugin create my-logger --template logger

# Create from auth template
dothttp plugin create my-auth --template auth
```

Templates available:
- `basic` - Simple pre/post request hooks
- `logger` - File-based request/response logging
- `auth` - Automatic authentication header injection

### Enable/Disable Plugins

```bash
# Enable a plugin
dothttp plugin enable my-plugin

# Disable a plugin
dothttp plugin disable my-plugin
```

### Show Plugin Info

```bash
dothttp plugin info my-plugin
```

Example output:
```
Plugin: my-plugin
Version: 1.0.0
Description: Custom request logger
Path: ~/.config/dothttp-plugins/plugins/my-plugin

Hooks (2):
  - pre_request
  - post_request

Dependencies:
  - requests==2.31.0
  - python-json-logger==2.0.7

Virtual environment: ~/.config/dothttp-plugins/plugins/my-plugin/.venv
```

### Install Plugin Dependencies

```bash
# Create venv and install requirements.txt
dothttp plugin install my-plugin
```

This will:
1. Create `.venv/` in the plugin directory
2. Install all packages from `requirements.txt`
3. Plugin dependencies are isolated from dothttp

## Quick Start Examples

### Example 1: Simple Logger

```bash
# Create plugin
dothttp plugin create simple-logger

# It creates ~/.config/dothttp-plugins/plugins/simple-logger/plugin.py:
```

```python
from dothttp.plugin_system import DothttpPlugin, PluginContext

class SimpleLoggerPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "simple-logger"

    def get_version(self) -> str:
        return "1.0.0"

    def pre_request(self, context: PluginContext) -> PluginContext:
        print(f"→ {context.request.method} {context.request.url}")
        return context

    def post_request(self, context: PluginContext) -> PluginContext:
        print(f"← {context.response.status_code}")
        return context
```

```bash
# Enable it
dothttp plugin enable simple-logger

# Test it
dothttp test.http
# Output:
# → GET https://httpbin.org/get
# ← 200
```

### Example 2: Request Timer

```bash
dothttp plugin create request-timer
```

Edit `~/.config/dothttp-plugins/plugins/request-timer/plugin.py`:

```python
import time
from dothttp.plugin_system import DothttpPlugin, PluginContext

class RequestTimerPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "request-timer"

    def get_version(self) -> str:
        return "1.0.0"

    def pre_request(self, context: PluginContext) -> PluginContext:
        context.metadata["start_time"] = time.time()
        return context

    def post_request(self, context: PluginContext) -> PluginContext:
        elapsed = time.time() - context.metadata["start_time"]
        print(f"⏱️  Request took {elapsed:.2f}s")
        return context
```

```bash
dothttp plugin enable request-timer
dothttp test.http
# Output:
# ⏱️  Request took 0.34s
```

### Example 3: Auth Header Injector

```bash
dothttp plugin create auth-injector --template auth
dothttp plugin enable auth-injector
```

Configure in `~/.config/dothttp-plugins/enabled.json`:

```json
{
  "plugins": {
    "auth-injector": {
      "enabled": true,
      "config": {
        "token_env": "MY_API_TOKEN",
        "header_name": "Authorization",
        "header_format": "Bearer {token}"
      }
    }
  }
}
```

```bash
export MY_API_TOKEN="your-token-here"
dothttp test.http
# Authorization header automatically added!
```

### Example 4: Plugin with Dependencies

```bash
# Create plugin
dothttp plugin create json-logger

# Add dependencies
cd ~/.config/dothttp-plugins/plugins/json-logger
echo "python-json-logger==2.0.7" >> requirements.txt

# Install dependencies
dothttp plugin install json-logger
```

Edit `plugin.py`:

```python
from pythonjsonlogger import jsonlogger
import logging
from dothttp.plugin_system import DothttpPlugin, PluginContext

class JsonLoggerPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "json-logger"

    def get_version(self) -> str:
        return "1.0.0"

    def initialize(self, config: dict) -> None:
        handler = logging.FileHandler('/tmp/requests.log')
        formatter = jsonlogger.JsonFormatter()
        handler.setFormatter(formatter)
        self.logger = logging.getLogger('requests')
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def post_request(self, context: PluginContext) -> PluginContext:
        self.logger.info("request", extra={
            "url": context.request.url,
            "status": context.response.status_code
        })
        return context
```

```bash
dothttp plugin enable json-logger
dothttp test.http
cat /tmp/requests.log
# {"url": "https://httpbin.org/get", "status": 200, "message": "request"}
```

## How Auto-Loading Works Internally

### 1. Import-Time Hook

When you run `dothttp`, the plugin system is imported:

```python
# In dothttp/__main__.py
from dothttp.plugin_system import ensure_integrated

ensure_integrated()  # Happens automatically
```

### 2. Monkey-Patching

The `auto_integrate_plugins()` function patches `HttpDef.get_response()`:

```python
# Original method
def get_response(self):
    session = self.get_session()
    request = self.get_request()
    resp = session.send(request, ...)
    return resp

# Patched method (automatic)
def get_response_with_plugins(self):
    plugin_manager = get_plugin_manager()
    session = self.get_session()
    request = self.get_request()

    # PRE-REQUEST HOOK (automatic)
    if plugin_manager.is_enabled():
        request = plugin_manager.execute_pre_request(request, properties={})

    resp = session.send(request, ...)

    # POST-REQUEST HOOK (automatic)
    if plugin_manager.is_enabled():
        resp = plugin_manager.execute_post_request(request, resp, properties={})

    return resp
```

### 3. Plugin Discovery

Plugins are discovered from `~/.config/dothttp-plugins/enabled.json`:

```json
{
  "plugins": {
    "my-plugin": {
      "enabled": true,
      "config": {
        "key": "value"
      }
    }
  }
}
```

### 4. Lazy Loading

Plugins load on first request, not at import time:

1. `dothttp` command runs
2. `ensure_integrated()` patches methods (fast, no I/O)
3. First request triggers `get_plugin_manager()`
4. Plugins load from disk (one-time cost)
5. Subsequent requests use cached plugins (fast)

## Disabling Auto-Integration

If you need to disable automatic integration:

```bash
export DOTHTTP_DISABLE_AUTO_PLUGIN_INTEGRATION=1
dothttp test.http
```

Or in Python:

```python
import os
os.environ['DOTHTTP_DISABLE_AUTO_PLUGIN_INTEGRATION'] = '1'

import dothttp
# Plugins won't auto-integrate
```

## Testing with Frozen Binary

The auto-integration works perfectly with PyInstaller:

```bash
# Build frozen binary
pyinstaller dothttp.spec

# Create plugin
./dist/dothttp plugin create test-plugin
./dist/dothttp plugin enable test-plugin

# Plugin works with frozen binary!
./dist/dothttp test.http
```

The frozen binary can still:
- Load external Python modules
- Modify sys.path at runtime
- Import from plugin directories
- Use plugin virtual environments

## Troubleshooting Auto-Loading

### Plugins Not Loading

1. Check if auto-integration is enabled:
```python
from dothttp.plugin_system import is_integrated
print(is_integrated())  # Should be True
```

2. Check if plugins are loaded:
```bash
dothttp plugin list
```

3. Enable debug logging:
```bash
dothttp --debug test.http
```

### Plugin Errors

Plugin errors are logged but don't break requests:

```python
# In your plugin
def pre_request(self, context):
    try:
        # Your code
        pass
    except Exception as e:
        import logging
        logging.error(f"Plugin error: {e}")
        # Execution continues
    return context
```

### Performance

Auto-integration has minimal overhead:

- Import-time patching: ~5ms (one-time)
- First request plugin load: ~50-100ms (one-time)
- Per-request overhead: ~1-5ms
- Zero overhead if no plugins enabled

## Advanced: Manual Integration (Optional)

If you prefer manual control, disable auto-integration and do it yourself:

```python
import os
os.environ['DOTHTTP_DISABLE_AUTO_PLUGIN_INTEGRATION'] = '1'

from dothttp.plugin_system import get_plugin_manager

# Manually call plugin hooks
plugin_manager = get_plugin_manager()

# Before request
request = plugin_manager.execute_pre_request(request, properties={})

# After response
response = plugin_manager.execute_post_request(request, response, properties={})

# On error
try:
    # ... send request ...
except Exception as e:
    e = plugin_manager.execute_on_error(request, e, properties={})
    raise
```

## Summary

✅ **Automatic**: Plugins load and integrate automatically  
✅ **CLI Commands**: Create, enable, disable, info, install  
✅ **Templates**: Basic, logger, auth templates  
✅ **Dependencies**: Per-plugin virtual environments  
✅ **Safe**: Plugin errors don't break requests  
✅ **Fast**: Lazy loading, minimal overhead  
✅ **PyInstaller**: Works with frozen binaries  

No manual integration needed - just create a plugin and enable it!

```bash
# Three commands to get started
dothttp plugin create my-plugin
dothttp plugin enable my-plugin
dothttp test.http  # Plugin runs automatically!
```
