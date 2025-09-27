#!/usr/bin/env python3
"""
分析i18nData.json中的Settings相关键，为分离做准备
"""

import json
import os

def analyze_settings_keys():
    """分析Settings相关的国际化键"""
    print("分析Settings相关的国际化键...")
    print("=" * 50)
    
    i18n_file = "collabtrans/i18n/i18nData.json"
    if not os.path.exists(i18n_file):
        print("❌ i18nData.json文件不存在")
        return
    
    with open(i18n_file, 'r', encoding='utf-8') as f:
        i18n_data = json.load(f)
    
    # 定义Settings相关的键模式
    settings_key_patterns = [
        # 通用Settings键
        'settingsTitle', 'homePageBtn', 'languageBtn', 'languageSwitcherTitle',
        
        # General模块
        'saveGeneralSettingsBtn', 'generalSettingsSaved', 'generalTitle', 'generalDescription',
        
        # AI平台模块
        'saveAiPlatformSettingsBtn', 'aiPlatformSettingsSaved', 'aiPlatformTitle', 'aiPlatformDescription',
        'saveApiKeyFailed', 'testingAiPlatformConnection', 'aiPlatformConnectionTestSuccess',
        'platformUrlPlaceholder', 'apiKeyPlaceholder', 'savedApiKeyPlaceholder',
        
        # Parsing Engine模块
        'saveEngineSettingsBtn', 'engineSettingsSaved', 'parsingEngineTitle', 'parsingEngineDescription',
        'saveMineruApiKeyFailed', 'mineruModelVersionPlaceholder', 'mineruApiKeyPlaceholder',
        
        # Login模块
        'saveLoginSettingsBtn', 'loginSettingsSaved', 'loginTitle', 'loginDescription',
        'generateTestCmdLabel', 'testLdapConnectionLabel', 'testLdapConnectionTitle',
        'usernameWithoutDomainLabel', 'passwordLabel', 'closeBtn', 'startTestBtn',
        'enterTestUsernamePrompt', 'ldapTestCmdCopied', 'enterUsernameAndPassword',
        'ldapConnectionTestSuccess', 'ldapConnectionTestFailed',
        'ldapHostPlaceholder', 'ldapPortPlaceholder', 'ldapBaseDnPlaceholder',
        'ldapUserFilterPlaceholder', 'ldapAdminGroupPlaceholder', 'ldapGlossaryGroupPlaceholder',
        'ldapGroupBaseDnPlaceholder', 'ldapTlsCacertfilePlaceholder', 'ldapTestUsernamePlaceholder',
        'ldapTestPasswordPlaceholder', 'ldapProtocolOptionLdap', 'ldapProtocolOptionLdaps',
        'ldapBindDnExample1', 'ldapBindDnExample2', 'ldapUserFilterExample',
        
        # Web模块
        'saveWebSettingsBtn', 'webSettingsSaved', 'webTitle', 'webDescription',
        'webSettingsSaveFailed', 'certUploadSuccess', 'certUploadFailed',
        'certUploadFailedTestCancelled', 'httpsTestSuccess', 'httpsTestFailed',
        'httpsTestException', 'certFileAcceptPlaceholder', 'keyFileAcceptPlaceholder',
        
        # 通用错误和状态
        'saveFailed', 'testFailed', 'testException', 'uploadSuccess', 'uploadFailed',
        'copyFailed', 'unknownError'
    ]
    
    # 获取所有键
    zh_keys = set(i18n_data.get('zh', {}).keys())
    en_keys = set(i18n_data.get('en', {}).keys())
    
    # 找出Settings相关的键
    settings_keys_zh = set()
    settings_keys_en = set()
    
    for key in settings_key_patterns:
        if key in zh_keys:
            settings_keys_zh.add(key)
        if key in en_keys:
            settings_keys_en.add(key)
    
    # 找出可能遗漏的Settings相关键（通过名称模式匹配）
    additional_settings_keys = set()
    for key in zh_keys:
        if any(pattern in key.lower() for pattern in ['settings', 'ldap', 'cert', 'https', 'api', 'platform', 'engine', 'login', 'web']):
            if key not in settings_keys_zh:
                additional_settings_keys.add(key)
    
    print(f"✅ 识别的Settings相关键（中文）: {len(settings_keys_zh)}个")
    print(f"✅ 识别的Settings相关键（英文）: {len(settings_keys_en)}个")
    print(f"✅ 可能遗漏的键: {len(additional_settings_keys)}个")
    
    if additional_settings_keys:
        print(f"可能遗漏的键: {sorted(additional_settings_keys)}")
    
    # 创建Settings i18n数据
    settings_i18n_data = {
        'zh': {key: i18n_data['zh'][key] for key in settings_keys_zh if key in i18n_data['zh']},
        'en': {key: i18n_data['en'][key] for key in settings_keys_en if key in i18n_data['en']}
    }
    
    # 保存到文件
    settings_i18n_file = "collabtrans/i18n/i18nSettings.json"
    os.makedirs(os.path.dirname(settings_i18n_file), exist_ok=True)
    
    with open(settings_i18n_file, 'w', encoding='utf-8') as f:
        json.dump(settings_i18n_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Settings i18n数据已保存到: {settings_i18n_file}")
    print(f"✅ 中文键数量: {len(settings_i18n_data['zh'])}")
    print(f"✅ 英文键数量: {len(settings_i18n_data['en'])}")
    
    # 显示一些示例键
    print("\n示例Settings键:")
    sample_keys = list(settings_keys_zh)[:10]
    for key in sample_keys:
        print(f"  - {key}: {i18n_data['zh'][key]}")
    
    return settings_keys_zh, settings_keys_en, additional_settings_keys

def show_separation_plan():
    """显示分离计划"""
    print("\n" + "=" * 60)
    print("Settings国际化分离计划")
    print("=" * 60)
    
    print("\n1. 文件结构:")
    print("   collabtrans/static/")
    print("   ├── i18nData.json                    # 主页面国际化")
    print("   └── settings/")
    print("       ├── i18nData.json                # Settings页面国际化")
    print("       ├── settings-core.js             # 修改以支持独立i18n")
    print("       └── ...")
    
    print("\n2. 修改步骤:")
    print("   ✅ 创建settings/i18nData.json")
    print("   ⏳ 修改settings-core.js加载逻辑")
    print("   ⏳ 从主i18nData.json移除Settings键")
    print("   ⏳ 测试分离后的功能")
    print("   ⏳ 更新文档")
    
    print("\n3. 优势:")
    print("   - 主i18nData.json文件更小，加载更快")
    print("   - Settings模块独立，便于维护")
    print("   - 减少主页面和Settings页面的耦合")
    print("   - 支持按需加载国际化数据")

if __name__ == "__main__":
    settings_keys_zh, settings_keys_en, additional_keys = analyze_settings_keys()
    show_separation_plan()
    
    print(f"\n📊 统计信息:")
    print(f"   - Settings相关键总数: {len(settings_keys_zh | settings_keys_en)}")
    print(f"   - 可能遗漏的键: {len(additional_keys)}")
    print(f"   - 建议检查遗漏的键是否应该包含在Settings中")
