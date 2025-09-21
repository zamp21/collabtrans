# Test Directory

这个目录包含了各种测试脚本和调试工具。

## 测试脚本分类

### 1. AI Platform 相关测试
- `test_ai_platform.html` - AI Platform模块功能测试
- `test_ai_platform_loading.py` - AI Platform加载功能测试
- `test_api_key_display.html` - API Key显示和masked检测测试
- `verify_settings_ai_platform.py` - Settings页面AI Platform功能验证

### 2. 密码切换功能测试
- `test_password_toggle.html` - 密码显示/隐藏切换按钮测试

### 3. 调试工具
- `debug_ui_display.html` - Settings页面UI显示调试工具
- `debug_settings_ai_platform.html` - Settings页面AI Platform调试工具
- `check_settings_content.html` - Settings页面内容检查工具

### 4. LDAP 相关测试
- `test_ldap_groups.py` - LDAP组查询测试
- `test_group_query.py` - 组查询功能测试
- `test_ldap_ui.js` - LDAP UI测试脚本
- `debug_ldap_ui.html` - LDAP UI调试工具

### 5. 国际化测试
- `test_settings_i18n.py` - Settings页面国际化测试
- `analyze_settings_i18n.py` - Settings国际化分析脚本
- `compare_i18n_data.py` - 国际化数据比较脚本
- `compare_i18n.py` - 国际化比较工具
- `fix_i18n_data.py` - 国际化数据修复脚本

### 6. 性能测试
- `test_token_performance.py` - Token性能测试

## 文档
- `settings_auth_migration_summary.md` - Settings页面AUTH配置迁移总结
- `ai_platform_loading_fix_summary.md` - AI Platform加载问题修复总结

## 使用方法

### HTML测试页面
直接在浏览器中访问：
```
http://localhost:8000/test/[文件名]
```

### Python测试脚本
```bash
cd test
python [脚本名].py
```

### JavaScript测试脚本
在浏览器控制台中运行或通过HTML页面加载。

## 注意事项

1. 运行测试前确保服务器正在运行
2. 某些测试需要管理员权限
3. 测试脚本可能会修改配置，请谨慎使用
4. 建议在测试环境中运行这些脚本
