# Example Dothttp Plugin

This is a reference implementation demonstrating all plugin features.

## Installation

```bash
# Copy to plugin directory
cp -r examples/example-plugin ~/.config/dothttp-plugins/plugins/example

# Enable in config
cat >> ~/.config/dothttp-plugins/enabled.json << 'EOF'
{
  "plugins": {
    "example": {
      "enabled": true,
      "config": {
        "hooks": ["pre", "post", "error"],
        "log_file": "/tmp/dothttp-example.log",
        "add_timestamp": true
      }
    }
  }
}
EOF
```

## Configuration Options

- `hooks`: List of hooks to enable (`["pre", "post", "error"]`)
- `log_file`: Path to log file (default: `/tmp/dothttp-example.log`)
- `add_timestamp`: Add timestamp header to requests (default: `true`)

## What It Does

- **Pre-request**: Logs request details, adds timestamp header
- **Post-request**: Logs response details, calculates request duration
- **On-error**: Logs error information
