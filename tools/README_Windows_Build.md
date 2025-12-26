# Windows 安装包构建指南

本项目提供了多种 Windows 安装包构建方案，从简单的可执行文件到专业的安装器。

## 构建方案

### 1. 简单打包（推荐快速测试）

生成包含配置文件的文件夹，可直接运行：

```powershell
# 构建轻量版和全量版
.\tools\build_win.ps1

# 只构建轻量版
.\tools\build_win.ps1 --lite

# 只构建全量版
.\tools\build_win.ps1 --full
```

**输出位置**: `build\win\collabtrans-lite-<version>\` 和 `build\win\collabtrans-full-<version>\`

**包含内容**:
- 可执行文件 (`bin\` 目录)
- 配置文件模板 (`config\` 目录)
- 启动脚本 (`collabtrans.bat`, `collabtrans-full.bat`)
- 安装/卸载脚本 (`install.bat`, `uninstall.bat`)
- 说明文档 (`README.txt`)

### 2. 专业安装器（推荐发布）

生成 Windows 安装包 (.exe)，支持安装向导、快捷方式、卸载程序：

```powershell
# 构建安装器（需要先安装 Inno Setup）
.\tools\build_win_installer.ps1

# 只构建轻量版安装器
.\tools\build_win_installer.ps1 --lite

# 只构建全量版安装器
.\tools\build_win_installer.ps1 --full
```

**前置要求**: 安装 [Inno Setup](https://jrsoftware.org/isinfo.php)

**输出位置**: `build\installer\CollabTrans-<version>-Windows-Installer.exe`

## Windows 配置路径适配

### 配置文件位置

- **Linux**: `/etc/collabtrans/`
- **Windows**: `C:\Users\Public\collabtrans\`

### 自动配置生成

安装包会自动：

1. **创建配置目录**: `C:\Users\Public\collabtrans\`
2. **复制模板文件**:
   - `global_config.json` → 全局配置
   - `local_secrets.json.template` → `local_secrets.json` (API 密钥)
   - `app_config.json.template` → `app_config.json` (应用配置)
3. **设置环境变量**:
   - `COLLABTRANS_CONFIG_PATH` = `C:\Users\Public\collabtrans`
   - `DOCUTRANSLATE_PORT` = `8020`

### 启动脚本功能

Windows 启动脚本 (`collabtrans.bat`, `collabtrans-full.bat`) 会：

1. 检查配置目录是否存在，不存在则创建
2. 检查配置文件是否存在，不存在则从模板复制
3. 设置环境变量
4. 启动应用程序

## 使用说明

### 简单打包使用

1. 运行 `install.bat` (需要管理员权限)
2. 应用程序安装到 `C:\Program Files\CollabTrans`
3. 配置文件创建到 `C:\Users\Public\collabtrans`
4. 桌面和开始菜单快捷方式自动创建

### 专业安装器使用

1. 运行生成的 `.exe` 安装器
2. 跟随安装向导，可选择配置目录位置
3. 安装完成后可通过开始菜单或桌面快捷方式启动

## 开发说明

### 文件结构

```
tools/
├── build_win.ps1              # 简单打包脚本
├── build_win_installer.ps1    # 专业安装器构建脚本
├── collabtrans_installer.iss  # Inno Setup 安装器脚本
└── windows/
    ├── collabtrans.bat        # 轻量版启动脚本
    └── collabtrans-full.bat   # 全量版启动脚本
```

### 自定义配置

如需修改配置路径或添加其他功能，可编辑：

- **启动脚本**: `tools\windows\*.bat`
- **安装器脚本**: `tools\collabtrans_installer.iss`
- **构建脚本**: `tools\build_win*.ps1`

## 故障排除

### 常见问题

1. **PyInstaller 构建失败**
   - 确保关闭所有 Python 进程: `taskkill /F /IM python.exe`
   - 检查虚拟环境是否正确激活

2. **图标文件缺失**
   - 已自动处理，会回退到 `favicon.ico` 或跳过图标

3. **Inno Setup 未找到**
   - 安装 Inno Setup 或使用简单打包方案
   - 或指定路径: `.\tools\build_win_installer.ps1 -InnoSetupPath "C:\Path\To\ISCC.exe"`

4. **配置文件未生成**
   - 确保启动脚本有写入权限
   - 检查 `C:\Users\Public\collabtrans` 目录权限

### 调试模式

在启动脚本中添加 `pause` 命令可查看详细输出：

```batch
echo Debug information...
pause
```

## 下一步计划

1. **代码路径适配**: 修改应用程序代码，支持 Windows 配置路径
2. **服务安装**: 添加 Windows 服务安装选项
3. **自动更新**: 集成自动更新机制
4. **多语言支持**: 完善安装器多语言界面
