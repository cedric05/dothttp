"""
Dotextensions module.

Automatically loads and integrates dothttp plugins.
"""

# Auto-load plugins when dotextensions is imported
try:
    from dothttp.plugin_system import ensure_integrated
    ensure_integrated()
except ImportError:
    # Plugin system not available
    pass
