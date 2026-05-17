"""
Example dothttp plugin that demonstrates all available hooks.

This is a reference implementation showing how to create a plugin.
Copy this to ~/.config/dothttp-plugins/plugins/example/ to use it.
"""

import json
import time
from pathlib import Path

from dothttp.plugin_system import DothttpPlugin, PluginContext


class ExamplePlugin(DothttpPlugin):
    """Example plugin demonstrating all hooks and features."""

    def get_name(self) -> str:
        return "example-plugin"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Example plugin showing all available hooks"

    def initialize(self, config: dict) -> None:
        """Initialize the plugin with user configuration."""
        self.enabled_hooks = config.get("hooks", ["pre", "post", "error"])
        self.log_file = config.get("log_file", "/tmp/dothttp-example.log")
        self.add_timestamp = config.get("add_timestamp", True)

        print(f"[ExamplePlugin] Initialized with hooks: {self.enabled_hooks}")
        print(f"[ExamplePlugin] Logging to: {self.log_file}")

        # Ensure log file directory exists
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)

    def pre_request(self, context: PluginContext) -> PluginContext:
        """Called before the HTTP request is sent."""
        if "pre" not in self.enabled_hooks:
            return context

        print(f"[ExamplePlugin] PRE-REQUEST: {context.request.method} {context.request.url}")

        # Store start time for timing
        context.metadata["example_start_time"] = time.time()

        # Example: Add custom header
        if self.add_timestamp:
            context.request.headers["X-Request-Timestamp"] = str(int(time.time()))

        # Example: Log request details
        self._log({
            "hook": "pre_request",
            "method": context.request.method,
            "url": context.request.url,
            "headers": dict(context.request.headers),
        })

        # Example: Access properties from http file
        if context.properties:
            print(f"[ExamplePlugin] Properties: {context.properties}")

        return context

    def post_request(self, context: PluginContext) -> PluginContext:
        """Called after receiving the HTTP response."""
        if "post" not in self.enabled_hooks:
            return context

        status = context.response.status_code
        print(f"[ExamplePlugin] POST-REQUEST: {status} {context.response.reason}")

        # Calculate request duration
        if "example_start_time" in context.metadata:
            duration = time.time() - context.metadata["example_start_time"]
            print(f"[ExamplePlugin] Request took {duration:.2f}s")

        # Example: Log response details
        self._log({
            "hook": "post_request",
            "status_code": status,
            "reason": context.response.reason,
            "headers": dict(context.response.headers),
            "body_length": len(context.response.content),
            "duration": duration if "example_start_time" in context.metadata else None,
        })

        # Example: Validate response
        if status >= 400:
            print(f"[ExamplePlugin] ⚠️  Request failed with {status}")

        return context

    def on_error(self, context: PluginContext) -> PluginContext:
        """Called when an error occurs during request execution."""
        if "error" not in self.enabled_hooks:
            return context

        print(f"[ExamplePlugin] ERROR: {type(context.error).__name__}: {context.error}")

        # Log error details
        self._log({
            "hook": "on_error",
            "error_type": type(context.error).__name__,
            "error_message": str(context.error),
            "request_url": context.request.url if context.request else None,
        })

        return context

    def cleanup(self) -> None:
        """Called when the plugin is unloaded."""
        print("[ExamplePlugin] Cleaning up...")
        # Close any open resources, connections, etc.

    def _log(self, data: dict) -> None:
        """Helper method to log data to file."""
        try:
            with open(self.log_file, "a") as f:
                log_entry = {
                    "timestamp": time.time(),
                    **data
                }
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"[ExamplePlugin] Failed to write log: {e}")


# Alternative way to export the plugin
def get_plugin():
    """Factory function to create plugin instance."""
    return ExamplePlugin()
