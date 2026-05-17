"""Integration point for plugins into dothttp request execution."""

import logging
from typing import Optional

from requests import PreparedRequest, Response

from .base import PluginContext, PluginHook
from .loader import PluginLoader

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages plugin lifecycle for dothttp execution.

    This is a singleton that handles loading plugins once and
    executing hooks during request/response lifecycle.
    """

    _instance: Optional['PluginManager'] = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the plugin manager (only once)."""
        if not PluginManager._initialized:
            self.loader = PluginLoader()
            self._load_plugins()
            PluginManager._initialized = True

    def _load_plugins(self):
        """Load all enabled plugins."""
        try:
            self.loader.load_all_plugins()
        except Exception as e:
            logger.error(f"Failed to load plugins: {e}", exc_info=True)

    def execute_pre_request(
        self,
        request: PreparedRequest,
        properties: dict = None,
    ) -> PreparedRequest:
        """Execute pre-request hooks for all plugins.

        Args:
            request: The prepared HTTP request
            properties: User properties from the http file

        Returns:
            Modified request (if any plugin modified it)
        """
        if not self.loader.loaded_plugins:
            return request

        context = PluginContext(
            request=request,
            properties=properties or {},
        )

        try:
            context = self.loader.execute_hook(PluginHook.PRE_REQUEST, context)
            return context.request
        except Exception as e:
            logger.error(f"Error in pre_request hooks: {e}", exc_info=True)
            return request

    def execute_post_request(
        self,
        request: PreparedRequest,
        response: Response,
        properties: dict = None,
    ) -> Response:
        """Execute post-request hooks for all plugins.

        Args:
            request: The HTTP request that was sent
            response: The HTTP response received
            properties: User properties from the http file

        Returns:
            Modified response (if any plugin modified it)
        """
        if not self.loader.loaded_plugins:
            return response

        context = PluginContext(
            request=request,
            response=response,
            properties=properties or {},
        )

        try:
            context = self.loader.execute_hook(PluginHook.POST_REQUEST, context)
            return context.response
        except Exception as e:
            logger.error(f"Error in post_request hooks: {e}", exc_info=True)
            return response

    def execute_on_error(
        self,
        request: PreparedRequest,
        error: Exception,
        properties: dict = None,
    ) -> Exception:
        """Execute error hooks for all plugins.

        Args:
            request: The HTTP request that was attempted
            error: The exception that occurred
            properties: User properties from the http file

        Returns:
            Modified error (if any plugin modified it)
        """
        if not self.loader.loaded_plugins:
            return error

        context = PluginContext(
            request=request,
            error=error,
            properties=properties or {},
        )

        try:
            context = self.loader.execute_hook(PluginHook.ON_ERROR, context)
            return context.error
        except Exception as e:
            logger.error(f"Error in on_error hooks: {e}", exc_info=True)
            return error

    def cleanup(self):
        """Cleanup all plugins."""
        if self.loader:
            self.loader.cleanup()

    def reload_plugins(self):
        """Reload all plugins (useful for development)."""
        self.cleanup()
        PluginManager._initialized = False
        self._load_plugins()

    def get_loaded_plugin_names(self) -> list[str]:
        """Get names of all loaded plugins.

        Returns:
            List of plugin names
        """
        return list(self.loader.get_loaded_plugins().keys())

    def is_enabled(self) -> bool:
        """Check if any plugins are loaded.

        Returns:
            True if at least one plugin is loaded
        """
        return len(self.loader.loaded_plugins) > 0


# Global instance - created lazily
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance.

    Returns:
        PluginManager singleton instance
    """
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


def cleanup_plugins():
    """Cleanup the global plugin manager."""
    global _plugin_manager
    if _plugin_manager:
        _plugin_manager.cleanup()
        _plugin_manager = None
