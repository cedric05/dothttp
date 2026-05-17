"""
Plugin system for dothttp.

This module provides the infrastructure for loading and executing plugins
that can hook into the request/response lifecycle.

Plugins are automatically integrated into request execution.
"""

from .auto_integrate import auto_integrate_plugins, ensure_integrated, is_integrated
from .base import DothttpPlugin, PluginContext, PluginHook
from .integration import PluginManager, cleanup_plugins, get_plugin_manager
from .loader import PluginLoader

__all__ = [
    'DothttpPlugin',
    'PluginContext',
    'PluginHook',
    'PluginLoader',
    'PluginManager',
    'get_plugin_manager',
    'cleanup_plugins',
    'auto_integrate_plugins',
    'ensure_integrated',
    'is_integrated',
]

# Ensure plugins are integrated when this module is imported
ensure_integrated()
