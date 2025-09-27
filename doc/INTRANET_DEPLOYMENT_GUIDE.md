# 内网部署优化指南

## 概述

本文档提供了在内网环境中部署CollabTrans的优化建议，解决CDN依赖和样式加载问题。

## 已修复的问题

### 1. CDN依赖问题

**问题描述：**
- 内网环境无法访问外部CDN
- 导致Bootstrap等资源加载失败
- 出现 "Loading failed for the script with source" 错误

**修复内容：**
- ✅ 修复了 `login.html` 中的Bootstrap CDN引用
- ✅ 修复了 `json.html` 中的renderjson CDN引用
- ✅ 所有资源现在都使用本地文件

**修复前：**
```html
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
```

**修复后：**
```html
<link href="/static/bootstrap.css" rel="stylesheet">
<script src="/static/bootstrap.bundle.min.js"></script>
```

### 2. 样式表加载时机优化

**问题描述：**
- "Layout was forced before the page was fully loaded"
- 可能导致页面闪烁（FOUC - Flash of Unstyled Content）

**解决方案：**
- ✅ 确保样式表在HTML头部正确加载
- ✅ 使用 `DOMContentLoaded` 事件确保DOM完全加载后再执行JavaScript
- ✅ 所有关键样式都在 `<head>` 中预加载

## 内网部署检查清单

### 1. 静态资源检查

确保以下文件存在于 `/static/` 目录：
- ✅ `bootstrap.css` - Bootstrap样式表
- ✅ `bootstrap.bundle.min.js` - Bootstrap JavaScript
- ✅ `bootstrap-icons.css` - Bootstrap图标
- ✅ `renderjson.min.js` - JSON渲染库
- ✅ `katex.css` 和 `katex.js` - 数学公式渲染
- ✅ `mermaid.js` - 图表渲染
- ✅ `papaparse.min.js` - CSV解析

### 2. 网络配置

**防火墙设置：**
- 确保应用端口（默认8010）可访问
- 如果使用HTTPS，确保443端口开放
- 确保Redis端口（默认6379）可访问

**代理配置：**
- 如果使用反向代理，确保静态文件路径正确
- 检查 `/static/` 和 `/i18n/` 路径的代理配置

### 3. 性能优化

**静态文件缓存：**
```python
# 在app.py中已配置
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/i18n", StaticFiles(directory=I18N_DIR), name="i18n")
```

**浏览器缓存：**
- 静态资源设置了适当的缓存头
- 使用版本号或时间戳避免缓存问题

### 4. 认证配置

**内网认证：**
- 确保认证中间件正确配置
- 检查豁免路径：`/static/`, `/i18n/`, `/login`, `/docs`
- 验证LDAP配置（如果使用）

## 故障排除

### 1. 资源加载失败

**症状：**
```
Loading failed for the <script> with source "https://cdn.jsdelivr.net/..."
```

**解决方案：**
1. 检查是否还有CDN引用未修复
2. 验证静态文件路径是否正确
3. 检查文件权限和网络连接

### 2. 样式表加载问题

**症状：**
```
Layout was forced before the page was fully loaded
```

**解决方案：**
1. 确保样式表在 `<head>` 中正确加载
2. 检查CSS文件是否存在且可访问
3. 验证浏览器缓存设置

### 3. 国际化文件加载失败

**症状：**
```
Failed to load i18n data: Error: Failed to load i18n data
```

**解决方案：**
1. 检查 `/i18n/` 路径是否正确配置
2. 验证认证中间件豁免设置
3. 确认i18n文件存在且格式正确

## 部署验证

### 1. 功能测试

- [ ] 主页正常加载
- [ ] 登录页面正常显示
- [ ] 文件上传功能正常
- [ ] 翻译功能正常
- [ ] 设置页面正常
- [ ] 国际化切换正常

### 2. 性能测试

- [ ] 页面加载速度正常
- [ ] 静态资源加载无错误
- [ ] 无FOUC（页面闪烁）现象
- [ ] 控制台无错误信息

### 3. 网络测试

```bash
# 测试静态资源访问
curl -I http://your-server:8010/static/bootstrap.css
curl -I http://your-server:8010/i18n/i18nData.json

# 测试应用启动
curl -I http://your-server:8010/
```

## 最佳实践

### 1. 资源管理

- 定期检查静态资源完整性
- 使用版本控制管理静态文件
- 考虑使用CDN镜像（如果有内网CDN）

### 2. 监控和日志

- 监控静态资源加载时间
- 记录404错误和加载失败
- 设置资源加载超时告警

### 3. 安全考虑

- 确保静态文件路径安全
- 验证文件上传和下载权限
- 定期更新依赖库版本

## 总结

通过以上修复和优化，CollabTrans现在完全支持内网部署：

- ✅ **无外部依赖** - 所有资源都使用本地文件
- ✅ **快速加载** - 优化了资源加载顺序
- ✅ **稳定运行** - 解决了样式表加载时机问题
- ✅ **完整功能** - 所有功能在内网环境下正常工作

内网部署不再需要担心CDN访问问题，应用可以完全离线运行。
