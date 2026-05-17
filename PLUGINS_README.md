# Dothttp Plugin System

**Extend dothttp with custom functionality - no code changes required!**

## Quick Start (30 seconds)

```bash
# 1. Create a plugin
dothttp plugin create my-logger

# 2. Enable it
dothttp plugin enable my-logger

# 3. Use dothttp - plugin runs automatically!
dothttp test.http
```

That's it! Your plugin is now running on every request.

## What Are Plugins?

Plugins let you hook into dothttp's request/response lifecycle to:

- 🔐 Add authentication headers automatically
- 📝 Log requests and responses
- ⏱️ Measure request timing
- ✅ Validate responses
- 🔄 Retry failed requests
- 📊 Collect metrics
- 🎨 And anything else you can imagine!

## Why Use Plugins?

✅ **Automatic** - No manual integration needed  
✅ **Isolated** - Each plugin has its own dependencies  
✅ **Safe** - Plugin errors don't break requests  
✅ **Fast** - Minimal overhead (1-5ms per request)  
✅ **Shareable** - Distribute plugins to your team  
✅ **PyInstaller Compatible** - Works with frozen binaries  

## How It Works

When you enable a plugin, dothttp automatically:

1. Loads the plugin from `~/.config/dothttp-plugins/plugins/`
2. Calls `pre_request()` before sending requests
3. Calls `post_request()` after receiving responses
4. Calls `on_error()` if something goes wrong

**You don't need to modify any dothttp code!**

## CLI Commands

### List Plugins

```bash
# Show all plugins
dothttp plugin list

# Show detailed info
dothttp plugin list -v
```

### Create Plugin

```bash
# Create from basic template
dothttp plugin create my-plugin

# Create from logger template
dothttp plugin create my-logger --template logger

# Create from auth template
dothttp plugin create my-auth --template auth
```

### Enable/Disable

```bash
# Enable a plugin
dothttp plugin enable my-plugin

# Disable a plugin
dothttp plugin disable my-plugin
```

### Show Info

```bash
# Show plugin details
dothttp plugin info my-plugin
```

### Install Dependencies

```bash
# Install plugin's dependencies into its own virtualenv
dothttp plugin install my-plugin
```

## Creating a Plugin

### Basic Structure

Every plugin needs:

1. A directory: `~/.config/dothttp-plugins/plugins/<plugin-name>/`
2. A Python file: `plugin.py` (or `__init__.py`)
3. A class that inherits from `DothttpPlugin`

### Minimal Example

```python
# ~/.config/dothttp-plugins/plugins/hello/plugin.py
from dothttp.plugin_system import DothttpPlugin, PluginContext

class HelloPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "hello"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def pre_request(self, context: PluginContext) -> PluginContext:
        print(f"🚀 Sending request to: {context.request.url}")
        return context
    
    def post_request(self, context: PluginContext) -> PluginContext:
        print(f"✅ Got response: {context.response.status_code}")
        return context
```

Enable and use:

```bash
dothttp plugin enable hello
dothttp test.http
# Output:
# 🚀 Sending request to: https://httpbin.org/get
# ✅ Got response: 200
```

## Example Plugins

### 1. Request Timer

Measure how long requests take:

```python
import time
from dothttp.plugin_system import DothttpPlugin, PluginContext

class TimerPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "timer"
    
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

### 2. Auth Header Injector

Automatically add authentication:

```python
import os
from dothttp.plugin_system import DothttpPlugin, PluginContext

class AuthPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "auth"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def pre_request(self, context: PluginContext) -> PluginContext:
        token = os.getenv("API_TOKEN")
        if token:
            context.request.headers["Authorization"] = f"Bearer {token}"
        return context
```

```bash
export API_TOKEN="your-token"
dothttp plugin enable auth
dothttp test.http  # Authorization header added automatically!
```

### 3. Response Validator

Validate responses and log failures:

```python
from dothttp.plugin_system import DothttpPlugin, PluginContext

class ValidatorPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "validator"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def post_request(self, context: PluginContext) -> PluginContext:
        if context.response.status_code >= 400:
            print(f"⚠️  Request failed!")
            print(f"   Status: {context.response.status_code}")
            print(f"   URL: {context.request.url}")
            print(f"   Response: {context.response.text[:200]}")
        return context
```

### 4. Request Logger

Log all requests to a file:

```python
import json
from pathlib import Path
from dothttp.plugin_system import DothttpPlugin, PluginContext

class LoggerPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "logger"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def initialize(self, config: dict) -> None:
        self.log_file = config.get("log_file", "/tmp/requests.log")
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
    
    def post_request(self, context: PluginContext) -> PluginContext:
        entry = {
            "url": context.request.url,
            "method": context.request.method,
            "status": context.response.status_code,
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return context
```

Configure in `~/.config/dothttp-plugins/enabled.json`:

```json
{
  "plugins": {
    "logger": {
      "enabled": true,
      "config": {
        "log_file": "/tmp/my-requests.log"
      }
    }
  }
}
```

## Using External Libraries

Plugins can use external Python libraries!

### Create Plugin with Dependencies

```bash
# 1. Create plugin
dothttp plugin create advanced-logger

# 2. Add dependencies
cd ~/.config/dothttp-plugins/plugins/advanced-logger
echo "python-json-logger==2.0.7" >> requirements.txt

# 3. Install dependencies (creates .venv)
dothttp plugin install advanced-logger
```

### Use External Library

```python
# plugin.py
from pythonjsonlogger import jsonlogger  # External library!
import logging
from dothttp.plugin_system import DothttpPlugin, PluginContext

class AdvancedLoggerPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "advanced-logger"
    
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

Each plugin's dependencies are isolated in its own `.venv/`!

## Plugin API Reference

### DothttpPlugin Base Class

```python
class DothttpPlugin(ABC):
    # Required methods
    def get_name(self) -> str: ...
    def get_version(self) -> str: ...
    
    # Optional methods
    def get_description(self) -> str: ...
    def get_hooks(self) -> list[PluginHook]: ...
    def initialize(self, config: dict) -> None: ...
    def cleanup(self) -> None: ...
    
    # Hook methods (implement what you need)
    def pre_request(self, context: PluginContext) -> PluginContext: ...
    def post_request(self, context: PluginContext) -> PluginContext: ...
    def on_error(self, context: PluginContext) -> PluginContext: ...
```

### PluginContext

```python
@dataclass
class PluginContext:
    request: PreparedRequest       # The HTTP request
    response: Optional[Response]   # The response (if available)
    error: Optional[Exception]     # The error (if any)
    properties: Dict[str, Any]     # Properties from .http file
    config: Dict[str, Any]         # Plugin configuration
    metadata: Dict[str, Any]       # Share data between hooks
```

## Configuration

Plugins are configured in `~/.config/dothttp-plugins/enabled.json`:

```json
{
  "plugins": {
    "my-plugin": {
      "enabled": true,
      "config": {
        "setting1": "value1",
        "setting2": 42
      }
    },
    "another-plugin": {
      "enabled": false
    }
  }
}
```

Access config in your plugin:

```python
def initialize(self, config: dict) -> None:
    self.setting1 = config.get("setting1", "default")
    self.setting2 = config.get("setting2", 0)
```

## Directory Structure

```
~/.config/dothttp-plugins/
├── enabled.json              # Plugin configuration
└── plugins/
    ├── my-logger/
    │   ├── plugin.py        # Plugin code
    │   ├── requirements.txt # Dependencies (optional)
    │   └── .venv/          # Virtual environment (optional)
    ├── auth-helper/
    │   └── plugin.py
    └── timer/
        └── plugin.py
```

## Templates

Create plugins from templates:

### Basic Template

```bash
dothttp plugin create my-plugin --template basic
```

Creates a plugin with pre_request and post_request hooks.

### Logger Template

```bash
dothttp plugin create my-logger --template logger
```

Creates a file-based request/response logger.

### Auth Template

```bash
dothttp plugin create my-auth --template auth
```

Creates an authentication header injector.

## Troubleshooting

### Plugin Not Loading?

```bash
# Check if plugins are loaded
dothttp plugin list

# Enable debug logging
dothttp --debug test.http

# Check if plugin is enabled
cat ~/.config/dothttp-plugins/enabled.json
```

### Dependencies Not Found?

```bash
# Install dependencies
dothttp plugin install my-plugin

# Verify .venv exists
ls ~/.config/dothttp-plugins/plugins/my-plugin/.venv/
```

### Plugin Errors?

Plugin errors are logged but don't break requests. Check logs with `--debug`.

## Advanced: Sharing Plugins

### As a Git Repository

```bash
# Publish
cd ~/.config/dothttp-plugins/plugins/my-plugin
git init
git add .
git commit -m "Initial commit"
git push origin main

# Install
cd ~/.config/dothttp-plugins/plugins/
git clone https://github.com/user/dothttp-plugin-name.git
cd dothttp-plugin-name
dothttp plugin install dothttp-plugin-name
dothttp plugin enable dothttp-plugin-name
```

### As a Zip File

```bash
# Create
cd ~/.config/dothttp-plugins/plugins/
zip -r my-plugin.zip my-plugin/

# Install
unzip my-plugin.zip -d ~/.config/dothttp-plugins/plugins/
dothttp plugin install my-plugin
dothttp plugin enable my-plugin
```

## Best Practices

1. **Keep plugins lightweight** - Don't slow down requests
2. **Handle errors gracefully** - Use try/except
3. **Document configuration** - Explain config options
4. **Version your plugins** - Use semantic versioning
5. **Test with frozen binaries** - Ensure PyInstaller compatibility
6. **Clean up resources** - Implement cleanup() if needed

## More Information

- **Full API Guide**: See `PLUGIN_GUIDE.md`
- **Auto-Loading Details**: See `AUTO_PLUGIN_GUIDE.md`
- **Quick Start**: See `PLUGIN_QUICKSTART.md`
- **Technical Details**: See `PLUGIN_SUMMARY.md`

## Examples

Check out `examples/example-plugin/` for a complete reference implementation.

## Getting Help

- Check debug logs: `dothttp --debug test.http`
- List plugins: `dothttp plugin list -v`
- Read the guides in the docs folder

## Summary

Creating plugins is easy:

```bash
# 1. Create
dothttp plugin create my-plugin

# 2. Edit
nano ~/.config/dothttp-plugins/plugins/my-plugin/plugin.py

# 3. Enable
dothttp plugin enable my-plugin

# 4. Use
dothttp test.http  # Plugin runs automatically!
```

**That's it! No code changes, no configuration complexity, just works!** 🎉
