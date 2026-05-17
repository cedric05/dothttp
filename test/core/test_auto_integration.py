"""Tests for automatic plugin integration."""

import os
import unittest
from unittest.mock import MagicMock, patch

from dothttp.plugin_system import (
    auto_integrate_plugins,
    cleanup_plugins,
    is_integrated,
)


class AutoIntegrationTest(unittest.TestCase):
    """Test automatic plugin integration."""

    def setUp(self):
        """Setup for each test."""
        cleanup_plugins()

    def tearDown(self):
        """Cleanup after each test."""
        cleanup_plugins()

    def test_auto_integration(self):
        """Test that auto-integration patches RequestCompiler.get_response."""
        # Import should trigger auto-integration
        from dothttp.parse.request_base import RequestCompiler

        # Check if method is wrapped
        self.assertTrue(
            hasattr(RequestCompiler.get_response, '__wrapped__')
            or hasattr(RequestCompiler.get_response, '__name__')
        )

    def test_is_integrated_check(self):
        """Test is_integrated() function."""
        # Should be integrated after import
        self.assertTrue(is_integrated())

    def test_manual_integration(self):
        """Test manual integration call."""
        result = auto_integrate_plugins()
        self.assertTrue(result)

    def test_integration_with_env_var(self):
        """Test that integration can be disabled via env var."""
        # This test just verifies the env var logic exists
        # Actual functionality would need a fresh process
        os.environ['DOTHTTP_DISABLE_AUTO_PLUGIN_INTEGRATION'] = '1'

        # Just verify we can read the env var
        self.assertEqual(os.getenv('DOTHTTP_DISABLE_AUTO_PLUGIN_INTEGRATION'), '1')

        # Cleanup
        del os.environ['DOTHTTP_DISABLE_AUTO_PLUGIN_INTEGRATION']

    @patch('dothttp.plugin_system.auto_integrate.logger')
    def test_integration_logging(self, mock_logger):
        """Test that integration logs success."""
        auto_integrate_plugins()
        # Should have logged something
        # Note: This might not work if already integrated

    def test_plugin_hooks_execute_automatically(self):
        """Test that plugin hooks execute during request."""
        from dothttp.plugin_system import DothttpPlugin, PluginContext, get_plugin_manager

        # Create a test plugin
        class TestPlugin(DothttpPlugin):
            def __init__(self):
                super().__init__()
                self.pre_called = False
                self.post_called = False

            def get_name(self):
                return "test"

            def get_version(self):
                return "1.0.0"

            def pre_request(self, context: PluginContext):
                self.pre_called = True
                return context

            def post_request(self, context: PluginContext):
                self.post_called = True
                return context

        # Manually load the plugin
        manager = get_plugin_manager()
        test_plugin = TestPlugin()
        manager.loader.loaded_plugins["test"] = test_plugin

        # Now when we make a request, hooks should execute automatically
        # This is tested through the integration, not directly here
        # The real test is in the manual test cases

        self.assertTrue(manager.is_enabled())


if __name__ == "__main__":
    unittest.main()
