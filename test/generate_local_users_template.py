#!/usr/bin/env python3
"""
Generate local_users.json.template file
Generate local_users.json.template file
"""

import json
import os
import sys
from typing import Dict, Any, List

def create_template_structure() -> Dict[str, Any]:
    """Create template structure"""
    return {
        "users": [
            {
                "username": "admin",
                "password_hash": "{{ADMIN_PASSWORD_HASH}}",
                "role": "super_admin",
                "created_at": "{{TIMESTAMP}}",
                "last_login": None,
                "is_active": True
            },
            {
                "username": "app_admin",
                "password_hash": "{{APP_ADMIN_PASSWORD_HASH}}",
                "role": "local_admin",
                "created_at": "{{TIMESTAMP}}",
                "last_login": None,
                "is_active": True
            },
            {
                "username": "user1",
                "password_hash": "{{USER1_PASSWORD_HASH}}",
                "role": "local_user",
                "created_at": "{{TIMESTAMP}}",
                "last_login": None,
                "is_active": True
            }
        ],
        "metadata": {
            "version": "1.0",
            "created_at": "{{TIMESTAMP}}",
            "description": "Local users configuration template",
            "default_passwords": {
                "admin": "admin123",
                "app_admin": "appadmin123",
                "user1": "user123"
            }
        }
    }

def create_initialization_script() -> str:
    """Create initialization script content"""
    return '''#!/usr/bin/env python3
"""
Initialize local user data
Initialize local user data
"""

import json
import os
import sys
import hashlib
import hmac
import time
from datetime import datetime

def hash_password(password: str, salt: str = None) -> str:
    """Hash password"""
    if salt is None:
        salt = os.urandom(32).hex()
    
    # Use HMAC-SHA256 for password hashing
    password_hash = hmac.new(
        salt.encode('utf-8'),
        password.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"{salt}:{password_hash}"

def initialize_local_users():
    """Initialize local user data"""
    template_file = "local_users.json.template"
    output_file = "local_users.json"
    
    if not os.path.exists(template_file):
        print(f"❌ Template file does not exist: {template_file}")
        return False
    
    # Read template
    with open(template_file, 'r', encoding='utf-8') as f:
        template_data = json.load(f)
    
    # Generate timestamp
    timestamp = datetime.now().isoformat()
    
    # Process user data
    for user in template_data["users"]:
        username = user["username"]
        
        # Get default password
        default_password = template_data["metadata"]["default_passwords"].get(username, "password123")
        
        # Generate password hash
        password_hash = hash_password(default_password)
        
        # Replace template variables
        user["password_hash"] = password_hash
        user["created_at"] = timestamp
    
    # Update metadata
    template_data["metadata"]["created_at"] = timestamp
    
    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(template_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Local user data initialization completed: {output_file}")
    print("📋 Default user accounts:")
    for username, password in template_data["metadata"]["default_passwords"].items():
        print(f"  - Username: {username}, Password: {password}")
    
    return True

if __name__ == "__main__":
    if initialize_local_users():
        print("🎉 Initialization successful!")
        sys.exit(0)
    else:
        print("❌ Initialization failed!")
        sys.exit(1)
'''

def create_readme() -> str:
    """Create README content"""
    return '''# 本地用户管理工具
# Local User Management Tools

## 文件说明
## File Description

- `local_users.json.template`: 本地用户配置模板
- `init_local_users.py`: 初始化脚本
- `local_users.json`: 生成的用户配置文件（不提交到Git）

## 使用方法
## Usage

### 1. 生成模板文件
### 1. Generate template file

```bash
python tools/generate_local_users_template.py
```

### 2. 初始化用户数据
### 2. Initialize user data

```bash
python init_local_users.py
```

### 3. 默认用户账户
### 3. Default user accounts

- **admin** / admin123 (超级管理员)
- **app_admin** / appadmin123 (应用管理员)
- **user1** / user123 (普通用户)

## 安全注意事项
## Security Notes

1. 生产环境中请修改默认密码
2. `local_users.json` 文件包含敏感信息，不要提交到版本控制
3. 定期备份用户数据
4. 使用强密码策略

## 角色说明
## Role Description

- **super_admin**: 超级管理员，拥有所有权限
- **local_admin**: 本地管理员，可以管理用户和设置
- **local_user**: 普通用户，基本使用权限
'''

def main():
    """Main function"""
    print("🔧 Generating local user management tools...")
    print("=" * 50)
    
    # Get project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Create template file
    template_data = create_template_structure()
    template_file = os.path.join(project_root, "local_users.json.template")
    
    with open(template_file, 'w', encoding='utf-8') as f:
        json.dump(template_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Template file generated: {template_file}")
    
    # Create initialization script
    init_script = create_initialization_script()
    init_file = os.path.join(project_root, "init_local_users.py")
    
    with open(init_file, 'w', encoding='utf-8') as f:
        f.write(init_script)
    
    # Set execution permissions
    os.chmod(init_file, 0o755)
    print(f"✅ Initialization script generated: {init_file}")
    
    # Create README
    readme_content = create_readme()
    readme_file = os.path.join(project_root, "LOCAL_USERS_README.md")
    
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ README file generated: {readme_file}")
    
    print("\n🎉 Local user management tools generation completed!")
    print("\n📋 Next steps:")
    print("1. Run python init_local_users.py to initialize user data")
    print("2. Check LOCAL_USERS_README.md for detailed instructions")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
