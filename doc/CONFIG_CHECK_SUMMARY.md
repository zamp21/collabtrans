# 配置文件环境检测检查总结

## ✅ 已统一处理的配置文件读取

### 1. 核心配置文件（已统一）
- ✅ `global_config.json` - `GlobalConfig.load_from_file()`
- ✅ `app_config.json` - `AppConfig.load_from_file()`
- ✅ `local_config.json` - `LocalConfig.load_from_file()` 和 `AuthConfig.load_from_file()`
- ✅ `local_secrets.json` - `SecretsManager.__init__()` 和 `app.py` 中的 `run_app()`
- ✅ `local_users.json` - `LocalUserStore.__init__()` 和 `UnifiedUserStore.__init__()`

### 2. 模板文件（已统一）
- ✅ `local_secrets.json.template` - `app.py` 中的模板查找逻辑
- ✅ `local_config.json.template` - `AuthConfig.load_from_file()` 中的模板查找逻辑

## ⚠️ 需要修复的保存逻辑

### 1. `AppConfig.save_to_file()`
**位置**: `collabtrans/config/app_config.py:179`
**问题**: 使用了 `get_collabtrans_paths()`，但没有使用环境检测
**建议**: 应该优先使用 `_resolve_app_config_path()` 返回的路径

### 2. `GlobalConfig.save_to_file()`
**位置**: `collabtrans/config/global_config.py:242`
**问题**: 没有使用环境检测，使用的是旧的硬编码路径逻辑
**建议**: 应该使用环境检测，优先保存到环境对应的路径

### 3. `AuthConfig.save_to_file()`
**位置**: `collabtrans/auth/config.py:327`
**问题**: 虽然使用了 `_resolve_auth_config_path()`，但候选路径列表中包含了硬编码的 `/etc/collabtrans`
**建议**: 移除硬编码路径，完全依赖 `_resolve_auth_config_path()`

### 4. `get_collabtrans_paths()`
**位置**: `collabtrans/utils/path_utils.py:79`
**问题**: 没有使用环境检测（`is_production()`），只检查了 `COLLABTRANS_CONFIG_PATH` 环境变量
**影响**: 
- 被 `AppConfig.save_to_file()` 使用
- 被 `GlobalConfig.save_to_file()` 作为后备路径使用
- 返回的配置路径实际上没有被使用（因为各个配置类都有自己的路径解析逻辑）
- 主要用于 `user_profiles`、`prompts`、`glossaries` 等数据目录

**建议**: 
- 对于配置文件路径，应该使用环境检测
- 对于数据目录（user_profiles、prompts、glossaries），可以考虑：
  - 生产环境：`/var/lib/collabtrans/`
  - 开发环境：项目根目录或用户目录

## 📋 其他配置文件

### 用户配置文件（不需要环境检测）
- `user_profiles/{username}_profile.json` - 使用 `get_collabtrans_paths()` 获取路径
- 这些是用户数据，不是系统配置，可以保持当前逻辑

### 其他数据文件（不需要环境检测）
- `prompts/` - 提示词存储
- `glossaries/` - 术语表存储
- 这些是数据文件，不是配置，可以保持当前逻辑

## 🔧 修复建议

### 优先级 1：修复保存逻辑
1. 修改 `AppConfig.save_to_file()` 使用环境检测
2. 修改 `GlobalConfig.save_to_file()` 使用环境检测
3. 修改 `AuthConfig.save_to_file()` 移除硬编码路径

### 优先级 2：优化 `get_collabtrans_paths()`
- 对于配置文件路径，使用环境检测
- 对于数据目录，可以考虑根据环境选择不同路径（可选）

## 📝 总结

**读取逻辑**: ✅ 已全部统一使用环境检测

**保存逻辑**: ⚠️ 部分未统一，需要修复：
- `AppConfig.save_to_file()` - 需要修复
- `GlobalConfig.save_to_file()` - 需要修复
- `AuthConfig.save_to_file()` - 需要优化（移除硬编码）

**数据目录**: ✅ 当前逻辑可以接受（不是配置文件，是用户数据）

