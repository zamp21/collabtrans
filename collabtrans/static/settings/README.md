# Settings 模块化重构

## 概述

Settings页面已重构为模块化设计，通过左侧导航切换不同设置模块，使界面更加简洁和易于维护。

## 文件结构

```
collabtrans/static/
├── settings.html                    # 主设置页面
└── settings/
    ├── README.md                    # 本文档
    ├── settings-core.js             # 核心JavaScript功能
    ├── general.html                 # General设置HTML
    ├── general.js                   # General设置JavaScript
    ├── ai-platforms.html            # AI平台设置HTML
    ├── ai-platforms.js              # AI平台设置JavaScript
    ├── parsing-engines.html         # 解析引擎设置HTML
    ├── parsing-engines.js           # 解析引擎设置JavaScript
    ├── login-settings.html          # 登录设置HTML
    ├── login-settings.js            # 登录设置JavaScript
    ├── web-settings.html            # Web设置HTML
    └── web-settings.js              # Web设置JavaScript
```

## 核心特性

### 1. 模块化设计
- 每个设置模块独立为HTML和JS文件
- 便于维护和扩展
- 代码职责清晰分离

### 2. 左侧导航切换
- 点击左侧导航链接切换不同设置模块
- 只有当前激活的模块显示内容
- 界面更加简洁

### 3. 简洁的标题设计
- 去掉了所有子模块标题中的"设置"字样
- 导航和内容标题更加简洁明了
- 提升用户体验

### 4. 跨页面语言同步
- 与主页使用相同的i18nData.json文件
- 实现与主页一致的语言检测和切换机制
- 支持localStorage和后端配置同步
- **实时语言同步**：主页切换语言时Settings页面立即更新
- 多重同步机制：自定义事件 + localStorage事件 + 定期轮询
- 支持跨标签页/窗口的语言同步

### 5. 按需加载
- 只有访问对应模块时才加载其内容
- 提高页面加载性能
- 减少初始页面大小

### 6. 统一管理
- 核心功能统一在`settings-core.js`中管理
- 国际化、导航、通知等功能共享
- 避免代码重复

## 模块说明

### General
- **文件**: `general.html`, `general.js`
- **功能**: 系统基本设置，如默认语言等
- **API**: `saveGeneralSettings()`

### AI 平台
- **文件**: `ai-platforms.html`, `ai-platforms.js`
- **功能**: AI翻译平台配置，API密钥管理等
- **API**: `saveAiPlatformConfig()`, `testAiPlatform()`

### Parsing Engine
- **文件**: `parsing-engines.html`, `parsing-engines.js`
- **功能**: 文档解析引擎配置
- **API**: `saveParsingEngineConfig()`

### 登录
- **文件**: `login-settings.html`, `login-settings.js`
- **功能**: LDAP认证配置和测试
- **API**: `saveLoginSettings()`, `testLdapConnectivity()`

### Web
- **文件**: `web-settings.html`, `web-settings.js`
- **功能**: HTTPS证书配置和测试
- **API**: `saveWebSettings()`

## 核心API

### SettingsCore 对象
```javascript
window.SettingsCore = {
  getText,                    // 国际化文本获取
  setLanguage,               // 语言设置（与主页同步）
  showNotification,          // 通知显示
  initTogglePasswordButtons, // 密码显示切换
  loadedModules              // 已加载模块集合
}
```

### 跨页面语言同步实现
- **数据源**: `/static/i18nData.json`（与主页共享）
- **语言检测优先级**: 
  1. localStorage中的`ui_language`设置
  2. 后端配置的`default_language`
  3. 浏览器语言检测
- **同步机制**: 
  - 主页切换语言时触发`languageChanged`自定义事件
  - Settings页面监听自定义事件和storage变化
  - 定期轮询作为备用机制（每2秒检查一次）
- **实时更新**: 主页切换语言，Settings页面立即同步更新UI
- **跨窗口支持**: 支持多个标签页/窗口之间的语言同步

### 模块加载
```javascript
// 加载指定模块内容
await loadModuleContent('general');

// 检查模块是否已加载
if (loadedModules.has('general')) {
  // 模块已加载
}
```

### 保存所有设置
```javascript
// 保存所有已加载模块的设置
await saveAllSettings();
```

## 开发指南

### 添加新模块

1. 在`settings/`目录下创建新的HTML和JS文件
2. 在`settings.html`中添加导航链接
3. 在`settings-core.js`的`saveAllSettings`函数中添加保存逻辑
4. 确保JS文件导出对应的保存函数到全局作用域

### 模块文件规范

#### HTML文件
- 只包含该模块的HTML内容
- 不包含`<html>`, `<head>`, `<body>`等标签
- 使用Bootstrap样式类

#### JavaScript文件
- 包含模块的初始化和事件绑定
- 导出保存函数到全局作用域: `window.saveModuleName = saveFunction`
- 使用`window.SettingsCore`访问核心功能

### 样式规范
- 使用Bootstrap 5样式
- 保持与现有设计一致
- 响应式设计

## 优势

1. **可维护性**: 每个模块独立，便于维护和调试
2. **可扩展性**: 添加新模块只需创建对应文件
3. **性能优化**: 按需加载，减少初始加载时间
4. **用户体验**: 界面简洁，导航清晰
5. **代码复用**: 核心功能统一管理，避免重复代码

## 兼容性

- 保持与原有API的完全兼容
- 所有原有功能正常工作
- 向后兼容，不影响现有配置
