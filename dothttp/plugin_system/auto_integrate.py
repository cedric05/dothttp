"""
Automatic integration of plugins into dothttp.

This module automatically patches the request execution to include plugin hooks
without requiring manual code changes.
"""

import logging
from functools import wraps

from .integration import get_plugin_manager

logger = logging.getLogger(__name__)


def auto_integrate_plugins():
    """
    Automatically integrate plugins into dothttp request execution.

    This function patches the RequestCompiler.get_response() method to automatically
    call plugin hooks without requiring manual integration.

    Should be called once at startup (e.g., in __main__.py or __init__.py).
    """
    try:
        from dothttp.parse.request_base import RequestCompiler

        # Check if already integrated
        if hasattr(RequestCompiler.get_response, '__wrapped__'):
            logger.debug("Plugins already integrated")
            return True

        # Store the original method
        original_get_response = RequestCompiler.get_response

        # Create wrapper with plugin hooks
        @wraps(original_get_response)
        def get_response_with_plugins(self):
            """Wrapped get_response with automatic plugin hook execution."""
            plugin_manager = get_plugin_manager()

            # Get properties for plugin context
            properties = {}
            if hasattr(self, 'property_util') and self.property_util:
                properties = getattr(self.property_util, 'properties', {})

            # Store original session.send for patching
            session = self.get_session()
            original_send = session.send

            def send_with_hooks(request, **kwargs):
                """Wrapped session.send with pre/post hooks."""
                # PRE-REQUEST HOOK
                if plugin_manager.is_enabled():
                    try:
                        request = plugin_manager.execute_pre_request(
                            request,
                            properties=properties
                        )
                    except Exception as e:
                        logger.error(f"Plugin pre-request hook failed: {e}", exc_info=True)

                # Send the request
                try:
                    response = original_send(request, **kwargs)

                    # POST-REQUEST HOOK
                    if plugin_manager.is_enabled():
                        try:
                            response = plugin_manager.execute_post_request(
                                request,
                                response,
                                properties=properties
                            )
                        except Exception as e:
                            logger.error(f"Plugin post-request hook failed: {e}", exc_info=True)

                    return response

                except Exception as error:
                    # ERROR HOOK
                    if plugin_manager.is_enabled():
                        try:
                            error = plugin_manager.execute_on_error(
                                request,
                                error,
                                properties=properties
                            )
                        except Exception as e:
                            logger.error(f"Plugin error hook failed: {e}", exc_info=True)
                    raise

            # Temporarily replace session.send
            session.send = send_with_hooks

            try:
                # Call original get_response
                return original_get_response(self)
            finally:
                # Restore original send
                session.send = original_send

        # Replace the method
        RequestCompiler.get_response = get_response_with_plugins

        logger.info("Plugin system auto-integration successful")
        return True

    except ImportError as e:
        logger.warning(f"Could not auto-integrate plugins: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to auto-integrate plugins: {e}", exc_info=True)
        return False


def is_integrated() -> bool:
    """
    Check if plugins are already integrated.

    Returns:
        True if plugins are integrated, False otherwise
    """
    try:
        from dothttp.parse.request_base import RequestCompiler
        return hasattr(RequestCompiler.get_response, '__wrapped__')
    except:
        return False


# Auto-integrate on module import (can be disabled by setting env var)
import os
if os.getenv('DOTHTTP_DISABLE_AUTO_PLUGIN_INTEGRATION') != '1':
    # Delay integration until first use to avoid import cycles
    _auto_integrated = False

    def ensure_integrated():
        """Ensure plugins are integrated (call on first use)."""
        global _auto_integrated
        if not _auto_integrated:
            auto_integrate_plugins()
            _auto_integrated = True
else:
    def ensure_integrated():
        """No-op when auto-integration is disabled."""
        pass
