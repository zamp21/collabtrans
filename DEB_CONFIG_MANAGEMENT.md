# CollabTrans DEB包配置文件管理

## 概述

DEB安装包现在会将配置文件安装到`/etc/collabtrans`目录下，应用启动时会优先使用系统配置文件。

## 配置文件优先级

### 1. 全局配置文件 (global_config.json)
优先级顺序：
1. `/etc/collabtrans/global_config.json` (系统配置)
2. `可执行程序目录/global_config.json` (打包的配置)
3. `./global_config.json` (本地配置)

### 2. 敏感配置文件 (local_secrets.json)
优先级顺序：
1. `/etc/collabtrans/local_secrets.json` (系统配置)
2. `可执行程序目录/local_secrets.json` (打包的配置)
3. `./local_secrets.json` (本地配置)

### 3. 模板文件 (local_secrets.json.template)
优先级顺序：
1. `/etc/collabtrans/local_secrets.json.template` (系统模板)
2. `可执行程序目录/local_secrets.json.template` (打包的模板)
3. `./local_secrets.json.template` (本地模板)

### 配置文件加载逻辑
- 如果`/etc/collabtrans`目录存在，优先使用系统配置
- 如果`/etc/collabtrans`目录不存在，则使用可执行程序目录下的配置文件
- 如果都不存在，使用当前目录下的配置文件
- 如果都不存在，使用空配置

## DEB包安装的文件

### 系统配置文件目录: `/etc/collabtrans/`
- `global_config.json` - 全局配置文件
- `local_secrets.json.template` - 敏感配置模板文件

### 应用目录: `/opt/collabtrans/`
- `CollabTrans-*-linux` - 主程序
- `setup_secrets.py` - 敏感配置初始化脚本
- `setup_first_deploy.py` - 首次部署设置脚本

## 配置文件管理工具

### 1. 配置文件管理脚本
```bash
# 检查配置文件状态
python3 manage_config_files.py check

# 将本地配置文件复制到系统目录
sudo python3 manage_config_files.py copy-to-system

# 从系统目录复制配置文件到本地
python3 manage_config_files.py copy-from-system

# 从模板创建系统配置文件
sudo python3 manage_config_files.py create-secrets
```

### 2. 首次部署设置脚本
```bash
# 在 /opt/collabtrans 目录下运行
python3 setup_first_deploy.py
```

### 3. 敏感配置初始化脚本
```bash
# 在 /opt/collabtrans 目录下运行
python3 setup_secrets.py
```

## 部署流程

### 1. 安装DEB包
```bash
sudo dpkg -i collabtrans-*_amd64.deb
```

### 2. 配置系统配置文件
```bash
# 方法1: 使用管理脚本
sudo python3 /opt/collabtrans/manage_config_files.py copy-to-system

# 方法2: 手动复制
sudo cp global_config.json /etc/collabtrans/
sudo cp local_secrets.json.template /etc/collabtrans/
```

### 3. 创建敏感配置文件
```bash
# 方法1: 使用管理脚本
sudo python3 /opt/collabtrans/manage_config_files.py create-secrets

# 方法2: 使用初始化脚本
cd /opt/collabtrans
sudo python3 setup_secrets.py
```

### 4. 编辑敏感配置
```bash
sudo nano /etc/collabtrans/local_secrets.json
```

### 5. 启动服务
```bash
sudo systemctl start collabtrans
sudo systemctl enable collabtrans
```

## 配置文件结构

### 系统配置文件目录
```
/etc/collabtrans/
├── global_config.json              # 全局配置
├── local_secrets.json.template     # 敏感配置模板
└── local_secrets.json              # 敏感配置（需要手动创建）
```

### 应用目录
```
/opt/collabtrans/
├── CollabTrans-*-linux             # 主程序
├── setup_secrets.py                # 敏感配置初始化脚本
└── setup_first_deploy.py           # 首次部署设置脚本
```

## 安全考虑

1. **文件权限**: 系统配置文件设置为644权限，只有root可写
2. **敏感信息**: `local_secrets.json`包含API密钥等敏感信息，需要妥善保管
3. **备份**: 建议定期备份`/etc/collabtrans/`目录下的配置文件

## 故障排除

### 1. 配置文件不存在
```bash
# 检查配置文件状态
python3 /opt/collabtrans/manage_config_files.py check
```

### 2. 权限问题
```bash
# 确保配置文件权限正确
sudo chmod 644 /etc/collabtrans/*.json
sudo chown root:root /etc/collabtrans/*.json
```

### 3. 配置文件格式错误
```bash
# 验证JSON格式
python3 -m json.tool /etc/collabtrans/global_config.json
python3 -m json.tool /etc/collabtrans/local_secrets.json
```

## 版本对比

| 版本 | 配置文件位置 | 特点 |
|------|-------------|------|
| **Lite** | `/etc/collabtrans/` | 基础功能，系统配置优先 |
| **Balance** | `/etc/collabtrans/` | 平衡功能，系统配置优先 |
| **Full** | `/etc/collabtrans/` | 完整功能，系统配置优先 |

所有版本都支持系统配置文件优先的机制，确保生产环境的一致性和安全性。
