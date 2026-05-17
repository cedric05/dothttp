"""CLI commands for plugin management."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .integration import get_plugin_manager
from .loader import PluginLoader


def list_plugins(verbose: bool = False):
    """
    List all plugins (loaded and available).

    Args:
        verbose: Show detailed information
    """
    plugin_manager = get_plugin_manager()
    loader = plugin_manager.loader

    loaded = loader.get_loaded_plugins()

    if not loaded:
        print("No plugins loaded.")
        print(f"\nPlugin directory: {loader.plugins_path}")
        print("Create plugins in ~/.config/dothttp-plugins/plugins/")
        return

    print(f"Loaded Plugins ({len(loaded)}):\n")

    for name, plugin in loaded.items():
        hooks = [h.value for h in plugin.get_hooks()]
        print(f"  ✓ {plugin.get_name()} (v{plugin.get_version()})")

        if verbose:
            desc = plugin.get_description()
            if desc:
                print(f"    Description: {desc}")
            print(f"    Hooks: {', '.join(hooks)}")
            print(f"    Path: {loader.plugins_path / name}")
            print()

    # Show available but not loaded
    if loader.plugins_path.exists():
        all_dirs = [d for d in loader.plugins_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
        not_loaded = [d.name for d in all_dirs if d.name not in loaded]

        if not_loaded:
            print(f"\nAvailable but not enabled ({len(not_loaded)}):")
            for name in not_loaded:
                print(f"  ○ {name}")
            print("\nEnable in ~/.config/dothttp-plugins/enabled.json")


def show_plugin_info(plugin_name: str):
    """
    Show detailed information about a specific plugin.

    Args:
        plugin_name: Name of the plugin
    """
    plugin_manager = get_plugin_manager()
    loader = plugin_manager.loader

    if plugin_name not in loader.loaded_plugins:
        print(f"Plugin '{plugin_name}' is not loaded.")
        plugin_path = loader.plugins_path / plugin_name
        if plugin_path.exists():
            print(f"Plugin directory exists at: {plugin_path}")
            print("Enable it in ~/.config/dothttp-plugins/enabled.json")
        return

    plugin = loader.loaded_plugins[plugin_name]
    plugin_path = loader.plugins_path / plugin_name

    print(f"Plugin: {plugin.get_name()}")
    print(f"Version: {plugin.get_version()}")
    desc = plugin.get_description()
    if desc:
        print(f"Description: {desc}")
    print(f"Path: {plugin_path}")

    hooks = plugin.get_hooks()
    print(f"\nHooks ({len(hooks)}):")
    for hook in hooks:
        print(f"  - {hook.value}")

    # Check for requirements
    requirements_file = plugin_path / "requirements.txt"
    if requirements_file.exists():
        print(f"\nDependencies:")
        with open(requirements_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    print(f"  - {line}")

    # Check for venv
    venv_path = plugin_path / ".venv"
    if venv_path.exists():
        print(f"\nVirtual environment: {venv_path}")


def create_plugin(plugin_name: str, template: str = "basic"):
    """
    Create a new plugin from a template.

    Args:
        plugin_name: Name for the new plugin
        template: Template to use (basic, logger, auth)
    """
    loader = PluginLoader()
    plugin_path = loader.plugins_path / plugin_name

    if plugin_path.exists():
        print(f"Plugin '{plugin_name}' already exists at: {plugin_path}")
        return False

    # Create plugin directory
    plugin_path.mkdir(parents=True)

    # Get template content
    templates = {
        "basic": """from dothttp.plugin_system import DothttpPlugin, PluginContext


class {class_name}(DothttpPlugin):
    def get_name(self) -> str:
        return "{plugin_name}"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Description of {plugin_name}"

    def pre_request(self, context: PluginContext) -> PluginContext:
        # Modify request before sending
        print(f"→ {{context.request.method}} {{context.request.url}}")
        return context

    def post_request(self, context: PluginContext) -> PluginContext:
        # Process response
        print(f"← {{context.response.status_code}}")
        return context
""",
        "logger": """import logging
from pathlib import Path
from dothttp.plugin_system import DothttpPlugin, PluginContext


class {class_name}(DothttpPlugin):
    def get_name(self) -> str:
        return "{plugin_name}"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Logs requests and responses to file"

    def initialize(self, config: dict) -> None:
        self.log_file = config.get("log_file", "/tmp/dothttp.log")
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)

    def pre_request(self, context: PluginContext) -> PluginContext:
        with open(self.log_file, "a") as f:
            f.write(f"→ {{context.request.method}} {{context.request.url}}\\n")
        return context

    def post_request(self, context: PluginContext) -> PluginContext:
        with open(self.log_file, "a") as f:
            f.write(f"← {{context.response.status_code}}\\n")
        return context
""",
        "auth": """import os
from dothttp.plugin_system import DothttpPlugin, PluginContext


class {class_name}(DothttpPlugin):
    def get_name(self) -> str:
        return "{plugin_name}"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Automatically adds authentication headers"

    def initialize(self, config: dict) -> None:
        self.token_env = config.get("token_env", "API_TOKEN")
        self.header_name = config.get("header_name", "Authorization")
        self.header_format = config.get("header_format", "Bearer {token}")

    def pre_request(self, context: PluginContext) -> PluginContext:
        token = os.getenv(self.token_env)
        if token:
            header_value = self.header_format.format(token=token)
            context.request.headers[self.header_name] = header_value
        return context
"""
    }

    if template not in templates:
        print(f"Unknown template: {template}")
        print(f"Available templates: {', '.join(templates.keys())}")
        return False

    # Generate class name
    class_name = ''.join(word.capitalize() for word in plugin_name.split('-')) + 'Plugin'

    # Write plugin file
    content = templates[template].format(
        plugin_name=plugin_name,
        class_name=class_name
    )
    (plugin_path / "plugin.py").write_text(content)

    print(f"✓ Created plugin: {plugin_path}")
    print(f"  - plugin.py (template: {template})")

    # Create empty requirements.txt
    (plugin_path / "requirements.txt").write_text("# Add dependencies here\n")
    print(f"  - requirements.txt")

    print(f"\nNext steps:")
    print(f"  1. Edit {plugin_path}/plugin.py")
    print(f"  2. Enable in ~/.config/dothttp-plugins/enabled.json:")
    print(f'     {{"plugins": {{"{plugin_name}": {{"enabled": true}}}}}}')

    return True


def enable_plugin(plugin_name: str):
    """
    Enable a plugin in the configuration.

    Args:
        plugin_name: Name of the plugin to enable
    """
    loader = PluginLoader()

    # Check if plugin exists
    plugin_path = loader.plugins_path / plugin_name
    if not plugin_path.exists():
        print(f"Plugin '{plugin_name}' not found at: {plugin_path}")
        return False

    # Load current config
    if loader.config_path.exists():
        with open(loader.config_path, 'r') as f:
            config = json.load(f)
    else:
        config = {"plugins": {}}

    # Enable plugin
    if "plugins" not in config:
        config["plugins"] = {}

    config["plugins"][plugin_name] = {
        "enabled": True
    }

    # Save config
    with open(loader.config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"✓ Enabled plugin: {plugin_name}")
    print(f"  Config: {loader.config_path}")
    print(f"\nRestart dothttp for changes to take effect.")

    return True


def disable_plugin(plugin_name: str):
    """
    Disable a plugin in the configuration.

    Args:
        plugin_name: Name of the plugin to disable
    """
    loader = PluginLoader()

    if not loader.config_path.exists():
        print("No plugin configuration found.")
        return False

    # Load current config
    with open(loader.config_path, 'r') as f:
        config = json.load(f)

    # Disable plugin
    if "plugins" in config and plugin_name in config["plugins"]:
        config["plugins"][plugin_name]["enabled"] = False

        # Save config
        with open(loader.config_path, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"✓ Disabled plugin: {plugin_name}")
        print(f"\nRestart dothttp for changes to take effect.")
        return True
    else:
        print(f"Plugin '{plugin_name}' is not configured.")
        return False


def install_plugin_dependencies(plugin_name: str):
    """
    Install dependencies for a plugin.

    Args:
        plugin_name: Name of the plugin
    """
    loader = PluginLoader()
    plugin_path = loader.plugins_path / plugin_name

    if not plugin_path.exists():
        print(f"Plugin '{plugin_name}' not found.")
        return False

    requirements_file = plugin_path / "requirements.txt"
    if not requirements_file.exists():
        print(f"No requirements.txt found for plugin '{plugin_name}'.")
        return False

    # Create venv if it doesn't exist
    venv_path = plugin_path / ".venv"
    if not venv_path.exists():
        print(f"Creating virtual environment at {venv_path}...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)

    # Determine pip path
    if sys.platform == "win32":
        pip_path = venv_path / "Scripts" / "pip"
    else:
        pip_path = venv_path / "bin" / "pip"

    # Install dependencies
    print(f"Installing dependencies from {requirements_file}...")
    subprocess.run([
        str(pip_path), "install", "-r", str(requirements_file)
    ], check=True)

    print(f"✓ Dependencies installed for '{plugin_name}'")
    return True


def run_cli(args):
    """
    Run the plugin CLI command.

    Args:
        args: Parsed command-line arguments
    """
    command = args.plugin_command

    if command == "list":
        list_plugins(verbose=args.verbose)

    elif command == "info":
        if not args.plugin_name:
            print("Error: --name required for 'info' command")
            sys.exit(1)
        show_plugin_info(args.plugin_name)

    elif command == "create":
        if not args.plugin_name:
            print("Error: --name required for 'create' command")
            sys.exit(1)
        template = getattr(args, 'template', 'basic')
        create_plugin(args.plugin_name, template)

    elif command == "enable":
        if not args.plugin_name:
            print("Error: --name required for 'enable' command")
            sys.exit(1)
        enable_plugin(args.plugin_name)

    elif command == "disable":
        if not args.plugin_name:
            print("Error: --name required for 'disable' command")
            sys.exit(1)
        disable_plugin(args.plugin_name)

    elif command == "install":
        if not args.plugin_name:
            print("Error: --name required for 'install' command")
            sys.exit(1)
        install_plugin_dependencies(args.plugin_name)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
