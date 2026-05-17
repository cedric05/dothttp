# Plugin System - Quick Start

## 5-Minute Plugin Setup

### 1. Create Your First Plugin (2 minutes)

```bash
# Create plugin directory
mkdir -p ~/.config/dothttp-plugins/plugins/hello

# Create plugin code
cat > ~/.config/dothttp-plugins/plugins/hello/plugin.py << 'EOF'
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
EOF
```

### 2. Enable the Plugin (1 minute)

```bash
cat > ~/.config/dothttp-plugins/enabled.json << 'EOF'
{
  "plugins": {
    "hello": {
      "enabled": true
    }
  }
}
EOF
```

### 3. Test It (2 minutes)

```bash
# Create a test http file
cat > test.http << 'EOF'
GET https://httpbin.org/get
EOF

# Run dothttp (plugin will print messages)
dothttp test.http
```

Expected output:
```
🚀 Sending request to: https://httpbin.org/get
✅ Got response: 200
```

## Plugin with External Dependencies

### Create Plugin with Dependencies

```bash
# Create plugin directory
mkdir -p ~/.config/dothttp-plugins/plugins/json-logger
cd ~/.config/dothttp-plugins/plugins/json-logger

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install python-json-logger
pip freeze > requirements.txt

# Create plugin code
cat > plugin.py << 'EOF'
import json
import logging
from pythonjsonlogger import jsonlogger
from dothttp.plugin_system import DothttpPlugin, PluginContext

class JsonLoggerPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "json-logger"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def initialize(self, config: dict) -> None:
        # Setup JSON logging
        log_file = config.get("log_file", "/tmp/dothttp.log")
        handler = logging.FileHandler(log_file)
        formatter = jsonlogger.JsonFormatter()
        handler.setFormatter(formatter)
        self.logger = logging.getLogger("dothttp.plugin")
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def post_request(self, context: PluginContext) -> PluginContext:
        self.logger.info("request_completed", extra={
            "url": context.request.url,
            "method": context.request.method,
            "status_code": context.response.status_code,
        })
        return context
EOF
```

### Enable with Configuration

```bash
cat > ~/.config/dothttp-plugins/enabled.json << 'EOF'
{
  "plugins": {
    "json-logger": {
      "enabled": true,
      "config": {
        "log_file": "/tmp/dothttp-requests.log"
      }
    }
  }
}
EOF
```

## Common Plugin Patterns

### Pattern 1: Add Custom Header

```python
def pre_request(self, context: PluginContext) -> PluginContext:
    context.request.headers["X-My-Header"] = "value"
    return context
```

### Pattern 2: Log Response Time

```python
import time

def pre_request(self, context: PluginContext) -> PluginContext:
    context.metadata["start_time"] = time.time()
    return context

def post_request(self, context: PluginContext) -> PluginContext:
    elapsed = time.time() - context.metadata["start_time"]
    print(f"Request took {elapsed:.2f}s")
    return context
```

### Pattern 3: Validate Response

```python
def post_request(self, context: PluginContext) -> PluginContext:
    if context.response.status_code >= 400:
        print(f"⚠️  Warning: Request failed with {context.response.status_code}")
    return context
```

### Pattern 4: Inject Auth Token

```python
import os

def pre_request(self, context: PluginContext) -> PluginContext:
    token = os.getenv("API_TOKEN")
    if token:
        context.request.headers["Authorization"] = f"Bearer {token}"
    return context
```

### Pattern 5: Save Responses

```python
import json
from pathlib import Path

def post_request(self, context: PluginContext) -> PluginContext:
    output_dir = Path("/tmp/responses")
    output_dir.mkdir(exist_ok=True)
    
    filename = f"{context.request.method}_{context.response.status_code}.json"
    filepath = output_dir / filename
    
    with open(filepath, "w") as f:
        json.dump({
            "url": context.request.url,
            "status": context.response.status_code,
            "body": context.response.text,
        }, f, indent=2)
    
    return context
```

## Debugging Plugins

### Enable Debug Logging

Add to your plugin:

```python
import logging

class MyPlugin(DothttpPlugin):
    def initialize(self, config: dict) -> None:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("MyPlugin initialized")
```

### Check Plugin Loading

```python
from dothttp.plugin_system import get_plugin_manager

manager = get_plugin_manager()
print("Loaded plugins:", manager.get_loaded_plugin_names())
```

### Test Plugin Standalone

```python
# test_plugin.py
from unittest.mock import MagicMock
from requests import PreparedRequest
from dothttp.plugin_system import PluginContext
from plugin import MyPlugin

# Create mock request
request = MagicMock(spec=PreparedRequest)
request.url = "https://example.com"
request.method = "GET"
request.headers = {}

# Create context
context = PluginContext(request=request)

# Test plugin
plugin = MyPlugin()
plugin.initialize({})
result = plugin.pre_request(context)

print("Headers:", result.request.headers)
```

## Troubleshooting

### Plugin Not Loading

1. Check path: `~/.config/dothttp-plugins/plugins/YOUR-PLUGIN/`
2. Check file: Must have `plugin.py` or `__init__.py`
3. Check config: `~/.config/dothttp-plugins/enabled.json` must have plugin enabled
4. Check logs: Enable debug logging to see errors

### Import Errors

1. Check `.venv` exists in plugin directory
2. Activate venv and verify: `pip list`
3. Check `site-packages` path exists: `.venv/lib/python3.X/site-packages/`

### Plugin Not Executing

1. Verify hooks are implemented: Override `pre_request`, `post_request`, or `on_error`
2. Check `enabled: true` in config
3. Ensure plugin returns context from hook methods

## Next Steps

- Read [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) for complete API documentation
- See [examples/example-plugin/](examples/example-plugin/) for a full reference implementation
- Check [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) if you're integrating plugins into dothttp code

## Plugin Ideas

- **Request retrier** - Automatically retry failed requests
- **Response cache** - Cache responses to avoid repeated requests
- **Mock server** - Intercept requests and return mock responses
- **Metrics collector** - Collect timing and success metrics
- **Screenshot taker** - Take screenshots of HTML responses
- **Database logger** - Log requests/responses to database
- **Slack notifier** - Send notifications on errors
- **Rate limiter** - Throttle requests to respect API limits
- **Circuit breaker** - Stop requests after consecutive failures
- **Request signing** - Add cryptographic signatures to requests
