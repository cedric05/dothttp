"""Tests for the plugin system."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from requests import PreparedRequest, Response

from dothttp.plugin_system import (
    DothttpPlugin,
    PluginContext,
    PluginHook,
    PluginLoader,
    cleanup_plugins,
    get_plugin_manager,
)


class MockPlugin(DothttpPlugin):
    """Mock plugin for testing."""

    def __init__(self):
        super().__init__()
        self.pre_request_called = False
        self.post_request_called = False
        self.on_error_called = False

    def get_name(self) -> str:
        return "mock-plugin"

    def get_version(self) -> str:
        return "1.0.0"

    def pre_request(self, context: PluginContext) -> PluginContext:
        self.pre_request_called = True
        context.request.headers["X-Mock-Plugin"] = "active"
        return context

    def post_request(self, context: PluginContext) -> PluginContext:
        self.post_request_called = True
        return context

    def on_error(self, context: PluginContext) -> PluginContext:
        self.on_error_called = True
        return context


class PluginBaseTest(unittest.TestCase):
    """Test the base plugin class."""

    def test_plugin_interface(self):
        """Test that plugin implements required methods."""
        plugin = MockPlugin()
        self.assertEqual(plugin.get_name(), "mock-plugin")
        self.assertEqual(plugin.get_version(), "1.0.0")

    def test_plugin_hooks_detection(self):
        """Test that hooks are automatically detected."""
        plugin = MockPlugin()
        hooks = plugin.get_hooks()
        self.assertIn(PluginHook.PRE_REQUEST, hooks)
        self.assertIn(PluginHook.POST_REQUEST, hooks)
        self.assertIn(PluginHook.ON_ERROR, hooks)

    def test_plugin_context(self):
        """Test plugin context creation."""
        request = MagicMock(spec=PreparedRequest)
        response = MagicMock(spec=Response)

        context = PluginContext(
            request=request,
            response=response,
            properties={"key": "value"},
            config={"setting": "value"},
        )

        self.assertEqual(context.request, request)
        self.assertEqual(context.response, response)
        self.assertEqual(context.properties["key"], "value")
        self.assertEqual(context.config["setting"], "value")


class PluginLoaderTest(unittest.TestCase):
    """Test the plugin loader."""

    def setUp(self):
        """Create a temporary plugin directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.plugin_dir = self.temp_dir / "plugins"
        self.plugin_dir.mkdir(parents=True)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_loader_initialization(self):
        """Test that loader initializes correctly."""
        loader = PluginLoader(plugin_dir=self.temp_dir)
        self.assertEqual(loader.plugin_dir, self.temp_dir)
        self.assertEqual(loader.plugins_path, self.plugin_dir)

    def test_config_creation(self):
        """Test that default config is created."""
        loader = PluginLoader(plugin_dir=self.temp_dir)
        loader.load_all_plugins()

        config_file = self.temp_dir / "enabled.json"
        self.assertTrue(config_file.exists())

        with open(config_file, "r") as f:
            config = json.load(f)
            self.assertIn("plugins", config)

    def test_load_plugin_from_file(self):
        """Test loading a plugin from a Python file."""
        # Create a simple plugin
        plugin_path = self.plugin_dir / "test-plugin"
        plugin_path.mkdir()

        plugin_code = '''
from dothttp.plugin_system import DothttpPlugin, PluginContext

class TestPlugin(DothttpPlugin):
    def get_name(self) -> str:
        return "test-plugin"

    def get_version(self) -> str:
        return "1.0.0"

    def pre_request(self, context: PluginContext) -> PluginContext:
        context.request.headers["X-Test"] = "loaded"
        return context
'''
        (plugin_path / "plugin.py").write_text(plugin_code)

        # Create config
        config = {
            "plugins": {
                "test-plugin": {
                    "enabled": True,
                }
            }
        }
        (self.temp_dir / "enabled.json").write_text(json.dumps(config))

        # Load plugins
        loader = PluginLoader(plugin_dir=self.temp_dir)
        loader.load_all_plugins()

        self.assertIn("test-plugin", loader.loaded_plugins)
        plugin = loader.loaded_plugins["test-plugin"]
        self.assertEqual(plugin.get_name(), "test-plugin")


class PluginManagerTest(unittest.TestCase):
    """Test the plugin manager integration."""

    def tearDown(self):
        """Clean up plugins after each test."""
        cleanup_plugins()

    def test_manager_singleton(self):
        """Test that manager is a singleton."""
        manager1 = get_plugin_manager()
        manager2 = get_plugin_manager()
        self.assertIs(manager1, manager2)

    def test_pre_request_hook(self):
        """Test pre-request hook execution."""
        manager = get_plugin_manager()

        # Mock a loaded plugin
        mock_plugin = MockPlugin()
        manager.loader.loaded_plugins["mock"] = mock_plugin

        request = MagicMock(spec=PreparedRequest)
        request.headers = {}

        result = manager.execute_pre_request(request, properties={})

        self.assertTrue(mock_plugin.pre_request_called)
        self.assertIn("X-Mock-Plugin", result.headers)

    def test_post_request_hook(self):
        """Test post-request hook execution."""
        manager = get_plugin_manager()

        # Mock a loaded plugin
        mock_plugin = MockPlugin()
        manager.loader.loaded_plugins["mock"] = mock_plugin

        request = MagicMock(spec=PreparedRequest)
        response = MagicMock(spec=Response)

        result = manager.execute_post_request(request, response, properties={})

        self.assertTrue(mock_plugin.post_request_called)
        self.assertEqual(result, response)

    def test_error_hook(self):
        """Test error hook execution."""
        manager = get_plugin_manager()

        # Mock a loaded plugin
        mock_plugin = MockPlugin()
        manager.loader.loaded_plugins["mock"] = mock_plugin

        request = MagicMock(spec=PreparedRequest)
        error = Exception("Test error")

        result = manager.execute_on_error(request, error, properties={})

        self.assertTrue(mock_plugin.on_error_called)
        self.assertEqual(result, error)

    def test_plugin_exception_handling(self):
        """Test that plugin exceptions don't break execution."""

        class BrokenPlugin(DothttpPlugin):
            def get_name(self) -> str:
                return "broken"

            def get_version(self) -> str:
                return "1.0.0"

            def pre_request(self, context: PluginContext) -> PluginContext:
                raise ValueError("Plugin error")

        manager = get_plugin_manager()
        manager.loader.loaded_plugins["broken"] = BrokenPlugin()

        request = MagicMock(spec=PreparedRequest)
        request.headers = {}

        # Should not raise, just log the error
        result = manager.execute_pre_request(request)
        self.assertEqual(result, request)


if __name__ == "__main__":
    unittest.main()
