# Settings页面AUTH配置迁移总结

## 已完成的修改

### 1. 默认用户配置迁移到General设置 ✅

**文件**: `collabtrans/static/settings/general.html`
- 添加了"超级管理员配置"部分
- 包含默认用户名和密码输入框
- 添加了密码显示/隐藏切换按钮
- 使用国际化属性 `data-i18n`

**文件**: `collabtrans/static/settings/general.js`
- 更新了 `loadGeneralSettings()` 函数，加载默认用户配置
- 更新了 `saveGeneralSettings()` 函数，保存默认用户配置
- 添加了密码切换按钮的初始化
- 修改了API端点从 `/auth/app-config/setting` 到 `/auth/app-config`

### 2. 会话配置和安全配置添加到Login Settings ✅

**文件**: `collabtrans/static/settings/login-settings.html`
- 添加了"会话配置"部分：
  - 会话最大时长（秒）
- 添加了"安全配置"部分：
  - 最大登录尝试次数
  - 登录尝试窗口（秒）
- 所有输入框都有适当的验证（min/max值）
- 使用国际化属性 `data-i18n`

**文件**: `collabtrans/static/settings/login-settings.js`
- 添加了 `loadSessionSecurityConfig()` 函数
- 更新了 `saveLoginSettings()` 函数，同时保存LDAP配置和会话/安全配置
- 在初始化中添加了会话/安全配置的加载
- 添加了新输入框的国际化占位符设置

## 功能对比

### 原主页面AUTH Settings功能：
- ✅ LDAP配置 - 已迁移到Login Settings
- ✅ LDAP测试功能 - 已迁移到Login Settings
- ✅ 默认用户配置 - 已迁移到General Settings（改为超级管理员）
- ✅ 会话配置 - 已迁移到Login Settings
- ✅ 安全配置 - 已迁移到Login Settings
- ❌ 重置配置功能 - 按用户要求暂不实现
- ❌ 完整的AUTH配置保存 - 按用户要求暂不处理

### 当前Settings页面功能：
- **General Settings**: 默认语言 + 超级管理员配置
- **Login Settings**: LDAP配置 + 会话配置 + 安全配置 + LDAP测试功能

## 需要添加的国际化键

以下键需要添加到 `i18nData.json` 或 `i18nSettings.json` 中：

```json
{
  "zh": {
    "superAdminConfigTitle": "超级管理员配置",
    "defaultUsernameLabel": "默认用户名",
    "defaultUsernamePlaceholder": "admin",
    "defaultUsernameHelp": "系统默认管理员的用户名",
    "defaultPasswordLabel": "默认密码",
    "defaultPasswordPlaceholder": "admin123",
    "defaultPasswordHelp": "系统默认管理员的密码",
    "sessionConfigTitle": "会话配置",
    "sessionMaxAgeLabel": "会话最大时长（秒）",
    "sessionMaxAgePlaceholder": "604800",
    "sessionMaxAgeHelp": "会话的最大持续时间，默认 7 天（604800 秒）",
    "securityConfigTitle": "安全配置",
    "maxLoginAttemptsLabel": "最大登录尝试次数",
    "maxLoginAttemptsPlaceholder": "5",
    "maxLoginAttemptsHelp": "在锁定前允许的最大登录尝试次数",
    "loginAttemptWindowLabel": "登录尝试窗口（秒）",
    "loginAttemptWindowPlaceholder": "300",
    "loginAttemptWindowHelp": "登录尝试计数的重置时间窗口"
  },
  "en": {
    "superAdminConfigTitle": "Super Admin Configuration",
    "defaultUsernameLabel": "Default Username",
    "defaultUsernamePlaceholder": "admin",
    "defaultUsernameHelp": "Username for the system default administrator",
    "defaultPasswordLabel": "Default Password",
    "defaultPasswordPlaceholder": "admin123",
    "defaultPasswordHelp": "Password for the system default administrator",
    "sessionConfigTitle": "Session Configuration",
    "sessionMaxAgeLabel": "Session Max Age (seconds)",
    "sessionMaxAgePlaceholder": "604800",
    "sessionMaxAgeHelp": "Maximum duration for sessions, default 7 days (604800 seconds)",
    "securityConfigTitle": "Security Configuration",
    "maxLoginAttemptsLabel": "Max Login Attempts",
    "maxLoginAttemptsPlaceholder": "5",
    "maxLoginAttemptsHelp": "Maximum login attempts allowed before lockout",
    "loginAttemptWindowLabel": "Login Attempt Window (seconds)",
    "loginAttemptWindowPlaceholder": "300",
    "loginAttemptWindowHelp": "Time window for resetting login attempt count"
  }
}
```

## 测试建议

1. **General Settings测试**：
   - 验证默认语言设置功能
   - 验证超级管理员用户名/密码设置功能
   - 验证密码显示/隐藏切换功能

2. **Login Settings测试**：
   - 验证LDAP配置功能
   - 验证会话配置功能
   - 验证安全配置功能
   - 验证LDAP测试功能
   - 验证所有配置的保存功能

3. **国际化测试**：
   - 验证中英文切换
   - 验证所有新增文本的翻译

## 注意事项

1. **API端点**：General Settings现在使用 `/auth/app-config` 而不是 `/auth/app-config/setting`
2. **配置分离**：LDAP配置和会话/安全配置分别保存到不同的API端点
3. **默认值**：所有配置都有合理的默认值
4. **验证**：数字输入框都有适当的min/max验证
5. **用户体验**：密码字段有显示/隐藏切换功能
