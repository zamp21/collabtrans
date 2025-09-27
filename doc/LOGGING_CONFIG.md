# 日志配置管理

## 概述

系统现在支持通过配置文件来管理日志级别和其他日志相关设置，无需修改代码即可调整日志行为。

## 配置文件

日志配置位于 `global_config.json` 文件中的 `logging` 部分：

```json
{
  "logging": {
    "level": "INFO",
    "console_enabled": true,
    "file_enabled": true,
    "max_file_size_mb": 10,
    "backup_count": 7
  }
}
```

### 配置项说明

- **level**: 日志级别，可选值：`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **console_enabled**: 是否启用控制台输出
- **file_enabled**: 是否启用文件输出
- **max_file_size_mb**: 日志文件最大大小（MB）
- **backup_count**: 保留的备份文件数量

## 管理工具

使用 `manage_logging.py` 工具可以方便地管理日志配置：

### 基本用法

```bash
# 显示当前配置
python3 manage_logging.py --show

# 设置日志级别
python3 manage_logging.py --level DEBUG
python3 manage_logging.py --level INFO
python3 manage_logging.py --level WARNING
python3 manage_logging.py --level ERROR
python3 manage_logging.py --level CRITICAL

# 控制台输出
python3 manage_logging.py --console on   # 启用控制台输出
python3 manage_logging.py --console off  # 禁用控制台输出

# 文件输出
python3 manage_logging.py --file on      # 启用文件输出
python3 manage_logging.py --file off     # 禁用文件输出

# 文件大小设置
python3 manage_logging.py --max-size 20  # 设置最大文件大小为20MB

# 备份文件数量
python3 manage_logging.py --backup-count 10  # 设置备份文件数量为10
```

### 组合使用

```bash
# 同时设置多个选项
python3 manage_logging.py --level DEBUG --console on --file on --max-size 20
```

## 日志级别说明

- **DEBUG**: 最详细的日志，包括AI交互的详细信息
- **INFO**: 一般信息日志，推荐用于生产环境
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误信息

## 应用场景

### 开发调试
```bash
python3 manage_logging.py --level DEBUG
```
启用DEBUG级别可以看到AI交互的详细日志，便于调试翻译问题。

### 生产环境
```bash
python3 manage_logging.py --level INFO
```
使用INFO级别，减少日志输出，提高性能。

### 问题排查
```bash
python3 manage_logging.py --level WARNING
```
只显示警告和错误信息，快速定位问题。

## 注意事项

1. **重启生效**: 修改配置后需要重启服务才能生效
2. **配置文件**: 配置保存在 `global_config.json` 中
3. **权限**: 确保有写入配置文件的权限
4. **备份**: 建议在修改配置前备份原配置文件

## 故障排除

### 配置不生效
1. 检查配置文件格式是否正确（JSON格式）
2. 确认服务已重启
3. 检查文件权限

### 工具无法运行
1. 确认Python环境正确
2. 检查依赖模块是否安装
3. 确认在正确的目录下运行

### 日志文件过大
1. 调整 `max_file_size_mb` 参数
2. 减少 `backup_count` 数量
3. 提高日志级别（如从DEBUG改为INFO）
