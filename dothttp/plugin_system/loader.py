"""Plugin loader for dothttp.

This module handles loading plugins from the user's plugin directory,
even when running as a PyInstaller frozen executable.
"""

import importlib.util
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .base import DothttpPlugin, PluginContext, PluginHook

logger = logging.getLogger(__name__)


class PluginLoader:
    """Loads and manages dothttp plugins from ~/.config/dothttp-plugins/."""

    def __init__(self, plugin_dir: Optional[Path] = None):
        """Initialize the plugin loader.

        Args:
            plugin_dir: Custom plugin directory path. If None, uses default.
        """
        if plugin_dir is None:
            plugin_dir = Path.home() / ".config" / "dothttp-plugins"

        self.plugin_dir = plugin_dir
        self.plugins_path = plugin_dir / "plugins"
        self.config_path = plugin_dir / "enabled.json"
        self.loaded_plugins: Dict[str, DothttpPlugin] = {}
        self._enabled_config: Dict[str, Dict] = {}

        # Ensure plugin directory exists
        self.plugins_path.mkdir(parents=True, exist_ok=True)

    def load_all_plugins(self) -> None:
        """Load all enabled plugins from the plugin directory."""
        # Load configuration
        self._load_config()

        if not self._enabled_config:
            logger.info("No plugins enabled")
            return

        for plugin_name, config in self._enabled_config.items():
            if config.get("enabled", True):
                try:
                    self._load_plugin(plugin_name, config)
                except Exception as e:
                    logger.error(f"Failed to load plugin '{plugin_name}': {e}", exc_info=True)

        logger.info(f"Loaded {len(self.loaded_plugins)} plugin(s)")

    def _load_config(self) -> None:
        """Load the enabled plugins configuration."""
        if not self.config_path.exists():
            logger.info(f"No config file found at {self.config_path}")
            self._create_default_config()
            return

        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
                self._enabled_config = config.get("plugins", {})
        except Exception as e:
            logger.error(f"Failed to load plugin config: {e}")
            self._enabled_config = {}

    def _create_default_config(self) -> None:
        """Create a default configuration file."""
        default_config = {
            "plugins": {
                # Example:
                # "my-logger": {
                #     "enabled": true,
                #     "config": {
                #         "log_level": "INFO"
                #     }
                # }
            }
        }
        try:
            with open(self.config_path, "w") as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"Created default config at {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to create default config: {e}")

    def _load_plugin(self, plugin_name: str, config: Dict) -> None:
        """Load a single plugin.

        Args:
            plugin_name: Name of the plugin directory
            config: Plugin configuration from enabled.json
        """
        plugin_path = self.plugins_path / plugin_name

        if not plugin_path.exists() or not plugin_path.is_dir():
            logger.warning(f"Plugin directory not found: {plugin_path}")
            return

        # Check for plugin's own virtual environment
        venv_path = plugin_path / ".venv"
        if venv_path.exists():
            self._add_venv_to_path(venv_path)

        # Add plugin directory to sys.path so it can be imported
        plugin_path_str = str(plugin_path)
        if plugin_path_str not in sys.path:
            sys.path.insert(0, plugin_path_str)

        try:
            # Import the plugin module
            # First try __init__.py, then plugin.py
            init_file = plugin_path / "__init__.py"
            plugin_file = plugin_path / "plugin.py"

            if init_file.exists():
                spec = importlib.util.spec_from_file_location(
                    f"dothttp_plugin_{plugin_name}",
                    init_file
                )
            elif plugin_file.exists():
                spec = importlib.util.spec_from_file_location(
                    f"dothttp_plugin_{plugin_name}",
                    plugin_file
                )
            else:
                raise ImportError(f"No __init__.py or plugin.py found in {plugin_path}")

            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load spec for plugin {plugin_name}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            # Find the plugin class (should inherit from DothttpPlugin)
            plugin_instance = self._find_plugin_class(module, plugin_name)

            if plugin_instance is None:
                raise ValueError(f"No DothttpPlugin subclass found in {plugin_name}")

            # Initialize the plugin
            plugin_config = config.get("config", {})
            plugin_instance.initialize(plugin_config)

            # Store the loaded plugin
            self.loaded_plugins[plugin_name] = plugin_instance
            logger.info(
                f"Loaded plugin: {plugin_instance.get_name()} "
                f"v{plugin_instance.get_version()} "
                f"(hooks: {[h.value for h in plugin_instance.get_hooks()]})"
            )

        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}", exc_info=True)
            raise

    def _add_venv_to_path(self, venv_path: Path) -> None:
        """Add a virtual environment's site-packages to sys.path.

        Args:
            venv_path: Path to the .venv directory
        """
        # Determine the site-packages path based on OS
        if sys.platform == "win32":
            site_packages = venv_path / "Lib" / "site-packages"
        else:
            # Find the pythonX.Y directory
            lib_path = venv_path / "lib"
            if lib_path.exists():
                python_dirs = [d for d in lib_path.iterdir() if d.name.startswith("python")]
                if python_dirs:
                    site_packages = python_dirs[0] / "site-packages"
                else:
                    logger.warning(f"Could not find python directory in {lib_path}")
                    return
            else:
                logger.warning(f"Virtual environment lib directory not found: {lib_path}")
                return

        if site_packages.exists():
            site_packages_str = str(site_packages)
            if site_packages_str not in sys.path:
                sys.path.insert(0, site_packages_str)
                logger.debug(f"Added to sys.path: {site_packages}")
        else:
            logger.warning(f"Site-packages directory not found: {site_packages}")

    def _find_plugin_class(self, module, plugin_name: str) -> Optional[DothttpPlugin]:
        """Find and instantiate a DothttpPlugin subclass in the module.

        Args:
            module: The loaded plugin module
            plugin_name: Name of the plugin (for error messages)

        Returns:
            Instantiated plugin or None
        """
        # Look for a class that inherits from DothttpPlugin
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, DothttpPlugin)
                and attr is not DothttpPlugin
            ):
                return attr()

        # Also check if module has a get_plugin() function
        if hasattr(module, "get_plugin"):
            plugin = module.get_plugin()
            if isinstance(plugin, DothttpPlugin):
                return plugin

        return None

    def execute_hook(
        self, hook: PluginHook, context: PluginContext
    ) -> PluginContext:
        """Execute a specific hook for all loaded plugins.

        Args:
            hook: The hook to execute
            context: The plugin context

        Returns:
            Modified context after all plugins have processed it
        """
        for plugin_name, plugin in self.loaded_plugins.items():
            if hook not in plugin.get_hooks():
                continue

            try:
                if hook == PluginHook.PRE_REQUEST:
                    context = plugin.pre_request(context)
                elif hook == PluginHook.POST_REQUEST:
                    context = plugin.post_request(context)
                elif hook == PluginHook.ON_ERROR:
                    context = plugin.on_error(context)
            except Exception as e:
                logger.error(
                    f"Plugin '{plugin_name}' failed at {hook.value}: {e}",
                    exc_info=True
                )
                # Don't let one plugin break the entire chain
                # but you might want to make this configurable

        return context

    def cleanup(self) -> None:
        """Clean up all loaded plugins."""
        for plugin_name, plugin in self.loaded_plugins.items():
            try:
                plugin.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up plugin '{plugin_name}': {e}")

        self.loaded_plugins.clear()

    def get_loaded_plugins(self) -> Dict[str, DothttpPlugin]:
        """Get all loaded plugins.

        Returns:
            Dictionary mapping plugin names to plugin instances
        """
        return self.loaded_plugins.copy()

    def is_plugin_loaded(self, plugin_name: str) -> bool:
        """Check if a plugin is loaded.

        Args:
            plugin_name: Name of the plugin

        Returns:
            True if loaded, False otherwise
        """
        return plugin_name in self.loaded_plugins
