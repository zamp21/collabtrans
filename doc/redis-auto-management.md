# Redis自动管理功能

## 概述

CollabTrans现在支持自动启动和管理本地Redis服务，无需用户手动安装和配置Redis环境变量。

## 功能特性

### ✅ 自动启动Redis
- 应用启动时自动检测并启动本地Redis服务
- 支持Windows、Linux、macOS多平台
- 无需手动配置环境变量

### ✅ 智能降级
- 优先使用本地Redis服务
- 如果本地Redis不可用，自动尝试连接外部Redis
- 如果Redis完全不可用，会话管理功能会优雅降级

### ✅ 自动清理
- 应用退出时自动关闭Redis服务
- 支持信号处理和优雅关闭

## 目录结构

```
collabtrans/
├── 3rdParty/
│   └── windows/
│       └── Redis-x64-3.0.504/          # Windows Redis安装包
│           ├── redis-server.exe         # Redis服务器
│           ├── redis-cli.exe            # Redis客户端
│           └── redis.windows.conf       # Redis配置文件
├── collabtrans/
│   └── utils/
│       └── redis_manager.py             # Redis管理器
└── ...
```

## 平台支持

### Windows
- 自动检测 `3rdParty/windows/Redis-x64-3.0.504/redis-server.exe`
- 使用 `redis.windows.conf` 配置文件启动

### Linux
- 自动检测 `/usr/bin/redis-server`
- 使用系统安装的Redis

### macOS
- 自动检测 `/usr/local/bin/redis-server` 或 `/opt/homebrew/bin/redis-server`
- 支持Homebrew安装的Redis

## 使用方法

### 1. 自动模式（推荐）
无需任何配置，应用会自动启动本地Redis：

```bash
# 启动CollabTrans
.venv\Scripts\python.exe -m collabtrans.cli -i
```

启动日志会显示：
```
🚀 正在启动本地Redis服务: D:\workspace\collabtrans\3rdParty\windows\Redis-x64-3.0.504\redis-server.exe
✅ Redis服务启动成功
✅ 使用本地Redis服务进行会话管理
```

### 2. 外部Redis模式
如果您想使用外部Redis服务，只需确保外部Redis正在运行，应用会自动检测并连接。

## 配置说明

### Redis配置
Redis使用以下默认配置：
- **端口**: 6379
- **主机**: 127.0.0.1
- **数据库**: 0
- **密码**: 无

### 会话配置
- **会话过期时间**: 7天
- **登录尝试限制**: 5次失败后锁定5分钟
- **Cookie名称**: collabtrans_session

## 故障排除

### 问题1：Redis启动失败
**症状**: 看到 "❌ Redis服务启动失败" 错误

**解决方案**:
1. 检查 `3rdParty/windows/Redis-x64-3.0.504/` 目录是否存在
2. 确认 `redis-server.exe` 文件存在且可执行
3. 检查端口6379是否被其他程序占用

### 问题2：Redis连接超时
**症状**: 看到 "⏳ 等待Redis启动..." 但最终超时

**解决方案**:
1. 手动启动Redis测试：
   ```bash
   cd 3rdParty\windows\Redis-x64-3.0.504
   redis-server.exe redis.windows.conf
   ```
2. 检查防火墙设置
3. 确认没有其他Redis实例在运行

### 问题3：会话功能不可用
**症状**: 登录后立即退出或会话丢失

**解决方案**:
1. 检查Redis服务是否正常运行：
   ```bash
   redis-cli ping
   # 应该返回: PONG
   ```
2. 查看应用日志中的Redis相关错误信息
3. 重启应用和Redis服务

## 技术实现

### Redis管理器 (`redis_manager.py`)
- `LocalRedisManager`: 管理Redis进程生命周期
- `get_redis_client()`: 获取Redis客户端连接
- 自动进程管理和信号处理

### 会话管理器 (`session_manager.py`)
- 优先使用本地Redis管理器
- 降级到外部Redis连接
- 优雅处理Redis不可用的情况

## 性能优化

### 连接池
Redis客户端使用连接池，提高并发性能。

### 超时设置
- 连接超时: 2秒
- 操作超时: 2秒
- 避免长时间阻塞

### 错误处理
所有Redis操作都有异常处理，确保应用稳定性。

## 安全考虑

### 本地Redis
- 默认只监听127.0.0.1，不对外暴露
- 无密码保护（仅本地访问）

### 生产环境
- 建议使用外部Redis服务
- 配置密码和网络访问控制
- 使用TLS加密连接

## 更新日志

### v1.4.3
- ✅ 添加自动Redis管理功能
- ✅ 支持多平台Redis检测
- ✅ 实现优雅降级机制
- ✅ 添加自动清理功能
