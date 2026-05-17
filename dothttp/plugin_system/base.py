"""Base classes for dothttp plugins."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from requests import PreparedRequest, Response


class PluginHook(Enum):
    """Plugin execution hooks."""
    PRE_REQUEST = "pre_request"
    POST_REQUEST = "post_request"
    ON_ERROR = "on_error"


@dataclass
class PluginContext:
    """Context passed to plugin hooks.

    Attributes:
        request: The prepared HTTP request
        response: The HTTP response (only available in post_request and on_error)
        error: The exception that occurred (only in on_error)
        properties: User-defined properties from the http file
        config: Plugin configuration from plugin metadata
        metadata: Additional metadata about the request
    """
    request: PreparedRequest
    response: Optional[Response] = None
    error: Optional[Exception] = None
    properties: Dict[str, Any] = None
    config: Dict[str, Any] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
        if self.config is None:
            self.config = {}
        if self.metadata is None:
            self.metadata = {}


class DothttpPlugin(ABC):
    """Base class for all dothttp plugins.

    Plugins should inherit from this class and implement the hooks they need.
    All hooks are optional - only implement what you need.

    Example:
        class MyLoggerPlugin(DothttpPlugin):
            def get_name(self) -> str:
                return "my-logger"

            def get_version(self) -> str:
                return "1.0.0"

            def pre_request(self, context: PluginContext) -> PluginContext:
                print(f"Making request to {context.request.url}")
                return context

            def post_request(self, context: PluginContext) -> PluginContext:
                print(f"Got response: {context.response.status_code}")
                return context
    """

    @abstractmethod
    def get_name(self) -> str:
        """Return the plugin name.

        Returns:
            Unique identifier for this plugin
        """
        pass

    @abstractmethod
    def get_version(self) -> str:
        """Return the plugin version.

        Returns:
            Version string (e.g., "1.0.0")
        """
        pass

    def get_description(self) -> str:
        """Return a brief description of the plugin.

        Returns:
            Human-readable description
        """
        return ""

    def get_hooks(self) -> list[PluginHook]:
        """Return list of hooks this plugin implements.

        By default, inspects which methods are overridden.
        Override if you want explicit control.

        Returns:
            List of PluginHook values
        """
        hooks = []
        if type(self).pre_request != DothttpPlugin.pre_request:
            hooks.append(PluginHook.PRE_REQUEST)
        if type(self).post_request != DothttpPlugin.post_request:
            hooks.append(PluginHook.POST_REQUEST)
        if type(self).on_error != DothttpPlugin.on_error:
            hooks.append(PluginHook.ON_ERROR)
        return hooks

    def pre_request(self, context: PluginContext) -> PluginContext:
        """Called before the HTTP request is sent.

        Plugins can modify the request, add headers, log, etc.
        Must return the context (potentially modified).

        Args:
            context: The plugin context with request information

        Returns:
            Modified or unmodified context

        Raises:
            Exception: Any exception raised will cancel the request
        """
        return context

    def post_request(self, context: PluginContext) -> PluginContext:
        """Called after receiving the HTTP response.

        Plugins can inspect/modify the response, log, extract data, etc.
        Must return the context (potentially modified).

        Args:
            context: The plugin context with request and response

        Returns:
            Modified or unmodified context
        """
        return context

    def on_error(self, context: PluginContext) -> PluginContext:
        """Called when an error occurs during request execution.

        Plugins can handle errors, log them, retry, etc.

        Args:
            context: The plugin context with request and error information

        Returns:
            Modified or unmodified context
        """
        return context

    def initialize(self, config: Dict[str, Any]) -> None:
        """Called once when the plugin is loaded.

        Use this to perform any setup, validate configuration, etc.

        Args:
            config: Plugin configuration from enabled.json

        Raises:
            Exception: If initialization fails
        """
        pass

    def cleanup(self) -> None:
        """Called when the plugin is unloaded or dothttp exits.

        Use this to clean up resources, close connections, etc.
        """
        pass
