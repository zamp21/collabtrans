# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def reset_admin_password_if_recovery_enabled() -> bool:
    """
    Reset admin password to default if password recovery is enabled in configuration.
    
    Returns:
        bool: True if password was reset, False otherwise
    """
    try:
        # Load local configuration
        from ..config.local_config import LocalConfig
        local_config = LocalConfig.load_from_file()
        
        # Check if password recovery is enabled
        if not local_config.security.password_recovery:
            logger.debug("Password recovery is disabled")
            return False
        
        logger.info("Password recovery is enabled, resetting admin password...")
        
        # Load users data
        users_file = Path("local_users.json")
        if not users_file.exists():
            logger.error("local_users.json not found")
            return False
        
        with open(users_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check if admin user exists
        if 'admin' not in data.get('users', {}):
            logger.error("Admin user not found in local_users.json")
            return False
        
        # Generate new password hash for "Changeme" (skip validation for default password)
        from .password_manager import password_manager
        new_password = "Changeme"
        new_hash = password_manager.hash_password(new_password, skip_validation=True)
        
        # Update admin password
        data['users']['admin']['password_hash'] = new_hash
        
        # Save updated users data
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Admin password reset successfully to: {new_password}")
        
        # Disable password recovery after successful reset
        local_config.security.password_recovery = False
        local_config.save_to_file()
        logger.info("Password recovery disabled after successful reset")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to reset admin password: {e}")
        return False


def enable_password_recovery() -> bool:
    """
    Enable password recovery in configuration.
    
    Returns:
        bool: True if enabled successfully, False otherwise
    """
    try:
        from ..config.local_config import LocalConfig
        local_config = LocalConfig.load_from_file()
        local_config.security.password_recovery = True
        local_config.save_to_file()
        logger.info("Password recovery enabled in configuration")
        return True
    except Exception as e:
        logger.error(f"Failed to enable password recovery: {e}")
        return False


def disable_password_recovery() -> bool:
    """
    Disable password recovery in configuration.
    
    Returns:
        bool: True if disabled successfully, False otherwise
    """
    try:
        from ..config.local_config import LocalConfig
        local_config = LocalConfig.load_from_file()
        local_config.security.password_recovery = False
        local_config.save_to_file()
        logger.info("Password recovery disabled in configuration")
        return True
    except Exception as e:
        logger.error(f"Failed to disable password recovery: {e}")
        return False
