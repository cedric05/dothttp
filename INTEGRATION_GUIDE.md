# Plugin Integration Guide

This guide explains how to integrate the plugin system into dothttp's request execution code.

## Overview

The plugin system allows external Python code to hook into the request/response lifecycle even when dothttp is running as a PyInstaller frozen binary.

## Integration Steps

### 1. Import Plugin Manager

At the top of your request execution file (e.g., `dothttp/parse/request_base.py`):

```python
from dothttp.plugin_system import get_plugin_manager
```

### 2. Modify Request Execution

Integrate plugin hooks into the `get_response()` method:

#### Before (current code):

```python
def get_response(self):
    session = self.get_session()
    request = self.get_request()
    session.cookies = request._cookies
    
    # ... certificate setup ...
    
    try:
        resp: Response = session.send(
            request,
            cert=cert,
            verify=not self.httpdef.allow_insecure,
            proxies=self.httpdef.proxy,
        )
    except SSLError as e:
        # ... error handling ...
```

#### After (with plugins):

```python
def get_response(self):
    session = self.get_session()
    request = self.get_request()
    session.cookies = request._cookies
    
    # Get plugin manager
    plugin_manager = get_plugin_manager()
    
    # Execute pre-request hooks
    if plugin_manager.is_enabled():
        request = plugin_manager.execute_pre_request(
            request,
            properties=self.property_util.properties if self.property_util else {}
        )
    
    # ... certificate setup ...
    
    try:
        resp: Response = session.send(
            request,
            cert=cert,
            verify=not self.httpdef.allow_insecure,
            proxies=self.httpdef.proxy,
        )
        
        # Execute post-request hooks
        if plugin_manager.is_enabled():
            resp = plugin_manager.execute_post_request(
                request,
                resp,
                properties=self.property_util.properties if self.property_util else {}
            )
        
        return resp
        
    except SSLError as e:
        # Execute error hooks
        if plugin_manager.is_enabled():
            e = plugin_manager.execute_on_error(
                request,
                e,
                properties=self.property_util.properties if self.property_util else {}
            )
        raise
```

### 3. Cleanup on Exit

In your main entry point (e.g., `dothttp/__main__.py`):

```python
from dothttp.plugin_system import cleanup_plugins
import atexit

def main():
    # Register cleanup handler
    atexit.register(cleanup_plugins)
    
    # ... rest of main ...

if __name__ == "__main__":
    main()
```

## Complete Example

Here's a complete integration example for `request_base.py`:

```python
# At the top of the file
from dothttp.plugin_system import get_plugin_manager

class HttpDef:
    # ... existing code ...
    
    def get_response(self):
        """Execute HTTP request with plugin support."""
        session = self.get_session()
        request = self.get_request()
        session.cookies = request._cookies
        
        # Get plugin manager (lazy initialization)
        plugin_manager = get_plugin_manager()
        
        # PRE-REQUEST HOOK: Allow plugins to modify request
        if plugin_manager.is_enabled():
            try:
                request = plugin_manager.execute_pre_request(
                    request,
                    properties=self.property_util.properties if self.property_util else {}
                )
            except Exception as plugin_error:
                request_logger.error(f"Plugin pre-request hook failed: {plugin_error}")
                # Continue execution even if plugin fails
        
        # Setup certificates
        if self.httpdef.p12:
            session.mount(
                request.url,
                Pkcs12Adapter(
                    pkcs12_filename=self.httpdef.p12[0],
                    pkcs12_password=self.httpdef.p12[1],
                ),
            )
        
        # Execute the request
        try:
            if self.httpdef.certificate:
                cert = tuple(self.httpdef.certificate)
            else:
                cert = None
                
            resp: Response = session.send(
                request,
                cert=cert,
                verify=not self.httpdef.allow_insecure,
                proxies=self.httpdef.proxy,
            )
            
            # POST-REQUEST HOOK: Allow plugins to process response
            if plugin_manager.is_enabled():
                try:
                    resp = plugin_manager.execute_post_request(
                        request,
                        resp,
                        properties=self.property_util.properties if self.property_util else {}
                    )
                except Exception as plugin_error:
                    request_logger.error(f"Plugin post-request hook failed: {plugin_error}")
                    # Continue execution even if plugin fails
            
            return resp
            
        except UnicodeEncodeError:
            # Handle unicode encoding issues
            request.prepare_body(request.body.encode("utf-8"), files=None)
            resp: Response = session.send(
                request,
                cert=self.httpdef.certificate,
                verify=not self.httpdef.allow_insecure,
            )
            
            # POST-REQUEST HOOK for retry
            if plugin_manager.is_enabled():
                try:
                    resp = plugin_manager.execute_post_request(
                        request,
                        resp,
                        properties=self.property_util.properties if self.property_util else {}
                    )
                except Exception as plugin_error:
                    request_logger.error(f"Plugin post-request hook failed: {plugin_error}")
            
            return resp
            
        except SSLError as e:
            # ERROR HOOK: Allow plugins to handle errors
            if plugin_manager.is_enabled():
                try:
                    e = plugin_manager.execute_on_error(
                        request,
                        e,
                        properties=self.property_util.properties if self.property_util else {}
                    )
                except Exception as plugin_error:
                    request_logger.error(f"Plugin error hook failed: {plugin_error}")
            
            # Re-raise the error after plugin processing
            raise DothttpUnSignedCertException() from e
            
        except Exception as e:
            # ERROR HOOK: Generic error handling
            if plugin_manager.is_enabled():
                try:
                    e = plugin_manager.execute_on_error(
                        request,
                        e,
                        properties=self.property_util.properties if self.property_util else {}
                    )
                except Exception as plugin_error:
                    request_logger.error(f"Plugin error hook failed: {plugin_error}")
            raise
```

## Performance Considerations

1. **Lazy Loading**: Plugins are loaded only once when `get_plugin_manager()` is first called
2. **Check if Enabled**: Use `plugin_manager.is_enabled()` to skip plugin execution if no plugins are loaded
3. **Exception Handling**: Wrap plugin calls in try/except to prevent plugin errors from breaking requests
4. **Minimal Overhead**: If no plugins are enabled, overhead is just one if-check per request

## Testing with Plugins

### Manual Testing

1. Create a test plugin in `~/.config/dothttp-plugins/plugins/test/`:

```python
# plugin.py
from dothttp.plugin_system import DothttpPlugin, PluginContext

class TestPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "test"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def pre_request(self, context: PluginContext) -> PluginContext:
        print(f"[TEST] Sending {context.request.method} {context.request.url}")
        return context
    
    def post_request(self, context: PluginContext) -> PluginContext:
        print(f"[TEST] Got {context.response.status_code}")
        return context
```

2. Enable it in `~/.config/dothttp-plugins/enabled.json`:

```json
{
  "plugins": {
    "test": {
      "enabled": true
    }
  }
}
```

3. Run dothttp and verify plugin output appears

### Unit Testing

Add tests in `test/core/test_plugins.py`:

```python
import unittest
from unittest.mock import MagicMock, patch
from dothttp.plugin_system import get_plugin_manager, cleanup_plugins

class PluginIntegrationTest(unittest.TestCase):
    def tearDown(self):
        cleanup_plugins()
    
    def test_plugin_execution(self):
        # Test plugin loading and execution
        manager = get_plugin_manager()
        # ... test logic ...
```

## PyInstaller Configuration

No special PyInstaller configuration is needed! The plugin system:

1. Uses the Python interpreter included in the frozen binary
2. Loads plugins from external directories at runtime
3. Dynamically modifies `sys.path` to include plugin paths
4. Supports plugins with their own virtual environments

The frozen binary can import and execute external Python code without issues.

## Troubleshooting Integration

### Plugins Not Loading

Check logs by adding at the start of `get_response()`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Impact

Measure plugin overhead:

```python
import time

start = time.time()
plugin_manager = get_plugin_manager()
print(f"Plugin init: {time.time() - start:.4f}s")

start = time.time()
request = plugin_manager.execute_pre_request(request, {})
print(f"Pre-request hooks: {time.time() - start:.4f}s")
```

### Import Errors

If plugins fail to import their dependencies, ensure:
1. Plugin has a `.venv/` directory with dependencies installed
2. Dependencies are in `.venv/lib/pythonX.Y/site-packages/`
3. Check logs for `sys.path` contents

## CLI Integration

Add a command to list/manage plugins in `dothttp/__main__.py`:

```python
def handle_plugins_command(args):
    """Handle plugin-related commands."""
    from dothttp.plugin_system import get_plugin_manager
    
    manager = get_plugin_manager()
    
    if args.plugin_action == "list":
        plugins = manager.get_loaded_plugin_names()
        if plugins:
            print("Loaded plugins:")
            for name in plugins:
                plugin = manager.loader.loaded_plugins[name]
                print(f"  - {name} (v{plugin.get_version()}): {plugin.get_description()}")
        else:
            print("No plugins loaded")
    
    elif args.plugin_action == "reload":
        manager.reload_plugins()
        print("Plugins reloaded")

# Add to argument parser
parser.add_argument(
    '--plugins',
    dest='plugin_action',
    choices=['list', 'reload'],
    help='Plugin management commands'
)
```

## Summary

The plugin system is designed to be:
- **Non-intrusive**: Minimal changes to existing code
- **Safe**: Plugins can't break request execution
- **Fast**: No overhead when no plugins are enabled
- **Flexible**: Works with PyInstaller frozen binaries
- **Easy to test**: Standard Python imports and execution

Key integration points:
1. Import `get_plugin_manager()`
2. Call `execute_pre_request()` before sending request
3. Call `execute_post_request()` after receiving response
4. Call `execute_on_error()` in exception handlers
5. Call `cleanup_plugins()` on exit
