# Dothttp Plugin System

Dothttp supports a plugin system that allows you to extend its functionality with custom pre-request and post-request hooks.

## Plugin Directory Structure

Plugins are stored in `~/.config/dothttp-plugins/`:

```
~/.config/dothttp-plugins/
├── plugins/
│   ├── my-logger/
│   │   ├── __init__.py          # or plugin.py
│   │   ├── requirements.txt     # Optional
│   │   └── .venv/              # Optional: plugin's own virtualenv
│   └── auth-helper/
│       └── plugin.py
└── enabled.json                 # Plugin configuration
```

## Creating a Plugin

### 1. Create Plugin Directory

```bash
mkdir -p ~/.config/dothttp-plugins/plugins/my-logger
cd ~/.config/dothttp-plugins/plugins/my-logger
```

### 2. Create Plugin Code

Create either `__init__.py` or `plugin.py`:

```python
# plugin.py or __init__.py
from dothttp.plugin_system import DothttpPlugin, PluginContext

class MyLoggerPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "my-logger"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_description(self) -> str:
        return "Logs all HTTP requests and responses"
    
    def initialize(self, config: dict) -> None:
        """Called once when plugin loads."""
        self.log_file = config.get("log_file", "/tmp/dothttp.log")
        print(f"MyLogger initialized, logging to {self.log_file}")
    
    def pre_request(self, context: PluginContext) -> PluginContext:
        """Called before sending the request."""
        print(f"→ {context.request.method} {context.request.url}")
        
        # You can modify the request
        context.request.headers["X-My-Plugin"] = "active"
        
        return context
    
    def post_request(self, context: PluginContext) -> PluginContext:
        """Called after receiving the response."""
        print(f"← {context.response.status_code} {context.response.reason}")
        
        # Log response details
        with open(self.log_file, "a") as f:
            f.write(f"{context.request.url} -> {context.response.status_code}\n")
        
        return context
    
    def on_error(self, context: PluginContext) -> PluginContext:
        """Called when an error occurs."""
        print(f"✗ Error: {context.error}")
        return context

# Alternative: export via function
def get_plugin():
    return MyLoggerPlugin()
```

### 3. Add Plugin Dependencies (Optional)

If your plugin needs external dependencies:

```bash
cd ~/.config/dothttp-plugins/plugins/my-logger

# Create a virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install requests beautifulsoup4

# Save requirements
pip freeze > requirements.txt
```

Dothttp will automatically add the plugin's `.venv/lib/pythonX.Y/site-packages` to `sys.path`.

### 4. Enable the Plugin

Edit `~/.config/dothttp-plugins/enabled.json`:

```json
{
  "plugins": {
    "my-logger": {
      "enabled": true,
      "config": {
        "log_file": "/tmp/dothttp-requests.log"
      }
    }
  }
}
```

## Plugin API Reference

### DothttpPlugin Base Class

All plugins must inherit from `DothttpPlugin` and implement at least `get_name()` and `get_version()`.

#### Required Methods

- `get_name() -> str`: Return unique plugin identifier
- `get_version() -> str`: Return version string (e.g., "1.0.0")

#### Optional Methods

- `get_description() -> str`: Return human-readable description
- `get_hooks() -> list[PluginHook]`: Return list of hooks (auto-detected by default)
- `initialize(config: dict) -> None`: Called once during plugin load
- `cleanup() -> None`: Called when plugin unloads
- `pre_request(context: PluginContext) -> PluginContext`: Before request
- `post_request(context: PluginContext) -> PluginContext`: After response
- `on_error(context: PluginContext) -> PluginContext`: On error

### PluginContext

The context object passed to hook methods:

```python
@dataclass
class PluginContext:
    request: PreparedRequest      # The HTTP request
    response: Optional[Response]  # The HTTP response (if available)
    error: Optional[Exception]    # The error (if any)
    properties: Dict[str, Any]    # Properties from the http file
    config: Dict[str, Any]        # Plugin config from enabled.json
    metadata: Dict[str, Any]      # Additional metadata
```

You can modify the context and must return it from hook methods.

## Example Plugins

### Timing Plugin

```python
import time
from dothttp.plugin_system import DothttpPlugin, PluginContext

class TimingPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "request-timer"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def pre_request(self, context: PluginContext) -> PluginContext:
        context.metadata["start_time"] = time.time()
        return context
    
    def post_request(self, context: PluginContext) -> PluginContext:
        elapsed = time.time() - context.metadata["start_time"]
        print(f"Request took {elapsed:.2f}s")
        return context
```

### Auth Token Injector

```python
import os
from dothttp.plugin_system import DothttpPlugin, PluginContext

class AuthPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "auth-injector"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def pre_request(self, context: PluginContext) -> PluginContext:
        # Add auth token from environment
        token = os.getenv("API_TOKEN")
        if token:
            context.request.headers["Authorization"] = f"Bearer {token}"
        return context
```

### Response Validator

```python
from dothttp.plugin_system import DothttpPlugin, PluginContext

class ValidatorPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "response-validator"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def post_request(self, context: PluginContext) -> PluginContext:
        # Validate response
        if context.response.status_code >= 400:
            print(f"⚠️  Warning: Request failed with {context.response.status_code}")
            print(f"Response: {context.response.text[:200]}")
        return context
```

## Plugin with External Dependencies

```python
# plugin.py
from dothttp.plugin_system import DothttpPlugin, PluginContext
from bs4 import BeautifulSoup  # External dependency

class HtmlParserPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "html-parser"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def post_request(self, context: PluginContext) -> PluginContext:
        if 'text/html' in context.response.headers.get('Content-Type', ''):
            soup = BeautifulSoup(context.response.text, 'html.parser')
            title = soup.title.string if soup.title else "No title"
            print(f"Page title: {title}")
        return context
```

```bash
# Setup
cd ~/.config/dothttp-plugins/plugins/html-parser
python -m venv .venv
source .venv/bin/activate
pip install beautifulsoup4 lxml
pip freeze > requirements.txt
```

## PyInstaller Compatibility

The plugin system works with PyInstaller frozen binaries because:

1. PyInstaller includes the Python interpreter
2. Plugins are loaded from external directories at runtime
3. Each plugin can have its own virtual environment
4. `sys.path` is dynamically modified to include plugin directories

The frozen dothttp binary can import and execute external Python code without any special configuration.

## Troubleshooting

### Plugin Not Loading

1. Check `~/.config/dothttp-plugins/enabled.json` exists and plugin is enabled
2. Verify plugin directory exists: `~/.config/dothttp-plugins/plugins/your-plugin/`
3. Check logs for error messages
4. Ensure plugin has `__init__.py` or `plugin.py`
5. Verify plugin class inherits from `DothttpPlugin`

### Import Errors

1. If plugin uses external libraries, create a `.venv` in the plugin directory
2. Install dependencies: `pip install -r requirements.txt`
3. Ensure `.venv/lib/pythonX.Y/site-packages` exists and contains the packages

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Advanced: Plugin Packaging

You can distribute plugins as zip files or git repos:

```bash
# Install from zip
unzip my-plugin.zip -d ~/.config/dothttp-plugins/plugins/

# Install from git
cd ~/.config/dothttp-plugins/plugins/
git clone https://github.com/user/dothttp-plugin-name.git
cd dothttp-plugin-name
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Best Practices

1. **Keep plugins lightweight** - Don't slow down request execution
2. **Handle errors gracefully** - Use try/except to avoid breaking requests
3. **Document configuration** - Explain what config options do
4. **Version your plugins** - Use semantic versioning
5. **Test with PyInstaller** - Ensure plugins work with frozen binary
6. **Avoid global state** - Use instance variables, not globals
7. **Clean up resources** - Implement `cleanup()` for file handles, connections, etc.
