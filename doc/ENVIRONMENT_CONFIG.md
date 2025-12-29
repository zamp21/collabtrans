# Environment Configuration Guide

## Overview

CollabTrans supports two environment modes: **production** and **development**. The environment mode determines where configuration files are loaded from.

## Environment Detection

The application detects the environment mode using the following priority:

1. **`.production` file** in project root - If exists, production mode
2. **`.development` file** in project root - If exists, development mode
3. **`ENV_MODE` environment variable** - Can be set to "production" or "development"
4. **Default** - If none of the above, defaults to development mode

## Configuration File Paths

### Production Environment

When running in production mode, configuration files are loaded from:
- `/etc/collabtrans/`

Configuration files:
- `global_config.json`
- `app_config.json`
- `local_config.json`
- `local_secrets.json`
- `local_secrets.json.template`
- `local_users.json`
- `local_users.json.template`

### Development Environment

When running in development mode, configuration files are loaded from:
- Project root directory (where `.development` or `.production` file is located)

Configuration files:
- `global_config.json`
- `app_config.json`
- `local_config.json`
- `local_secrets.json`
- `local_secrets.json.template`
- `local_users.json`
- `local_users.json.template`

## Setting Up Environment

### For Development

1. Create a `.development` file in the project root:
   ```bash
   touch .development
   ```
   Or the file already exists in the project root.

2. Configuration files will be loaded from the project root directory.

### For Production

1. Create a `.production` file in the project root:
   ```bash
   touch .production
   ```
   Or remove the `.development` file if it exists.

2. Ensure configuration files exist in `/etc/collabtrans/`:
   ```bash
   sudo mkdir -p /etc/collabtrans
   sudo cp global_config.json /etc/collabtrans/
   sudo cp app_config.json /etc/collabtrans/
   sudo cp local_config.json /etc/collabtrans/
   sudo cp local_secrets.json /etc/collabtrans/
   # ... etc
   ```

### Using Environment Variable

You can also set the environment variable `ENV_MODE`:

```bash
# Production mode
export ENV_MODE=production

# Development mode
export ENV_MODE=development
```

## Priority Order

The configuration file loading follows this priority order:

1. **`COLLABTRANS_CONFIG_PATH` environment variable** (cross-platform override)
   - Windows default: `C:\Users\Public\collabtrans`
   - If set, all configs are loaded from this directory

2. **Environment-based path** (production or development)
   - Production: `/etc/collabtrans/`
   - Development: Project root directory

3. **Legacy fallback paths** (for backward compatibility)
   - System directory: `/etc/collabtrans/` (non-Windows)
   - Executable directory (PyInstaller packaged)
   - Current working directory

## Migration Guide

### From Legacy to Environment-Based Configuration

If you're currently using the legacy configuration paths, you can migrate:

1. **Identify your current environment**:
   - If running in production, create `.production` file
   - If running in development, ensure `.development` file exists

2. **Move configuration files**:
   - Production: Copy configs to `/etc/collabtrans/`
   - Development: Keep configs in project root

3. **Test the application**:
   - Verify that configuration files are loaded correctly
   - Check application logs for configuration file paths

## Troubleshooting

### Configuration Not Found

If configuration files are not found:

1. Check environment mode:
   ```python
   from collabtrans.config.env_detector import is_production
   print(f"Production mode: {is_production()}")
   ```

2. Verify file existence:
   ```bash
   # Production
   ls -la /etc/collabtrans/
   
   # Development
   ls -la ./
   ```

3. Check application logs for configuration file paths

### Wrong Configuration Loaded

If the wrong configuration is loaded:

1. Check for `.production` or `.development` file in project root
2. Check `ENV_MODE` environment variable
3. Verify `COLLABTRANS_CONFIG_PATH` is not set (unless intentionally)
4. Review application logs for the actual configuration path used

## Notes

- The environment detection is performed at runtime when configuration files are loaded
- The `.production` and `.development` files are marker files (can be empty)
- Environment variable `ENV_MODE` takes precedence over file markers
- `COLLABTRANS_CONFIG_PATH` environment variable overrides all other paths

