#!/usr/bin/env python3
"""
测试Settings页面及其子页面的国际化完整性
"""

import os
import re
import json

def test_i18n_data_completeness():
    """测试i18nData.json的完整性"""
    print("检查i18nData.json的完整性...")
    print("=" * 50)
    
    i18n_file = "collabtrans/static/i18nData.json"
    if not os.path.exists(i18n_file):
        print("❌ i18nData.json文件不存在")
        return False
    
    with open(i18n_file, 'r', encoding='utf-8') as f:
        i18n_data = json.load(f)
    
    # 检查中英文键的一致性
    zh_keys = set(i18n_data.get('zh', {}).keys())
    en_keys = set(i18n_data.get('en', {}).keys())
    
    missing_in_en = zh_keys - en_keys
    missing_in_zh = en_keys - zh_keys
    
    if missing_in_en:
        print(f"❌ 英文翻译缺失的键: {missing_in_en}")
    else:
        print("✅ 英文翻译完整")
    
    if missing_in_zh:
        print(f"❌ 中文翻译缺失的键: {missing_in_zh}")
    else:
        print("✅ 中文翻译完整")
    
    # 检查Settings相关的键
    settings_keys = [
        'saveGeneralSettingsBtn', 'generalSettingsSaved', 'saveFailed',
        'saveAiPlatformSettingsBtn', 'testConnectionBtn', 'aiPlatformSettingsSaved',
        'saveApiKeyFailed', 'testingAiPlatformConnection', 'aiPlatformConnectionTestSuccess',
        'testFailed', 'testException', 'saveEngineSettingsBtn', 'engineSettingsSaved',
        'saveLoginSettingsBtn', 'loginSettingsSaved', 'generateTestCmdLabel',
        'testLdapConnectionLabel', 'testLdapConnectionTitle', 'usernameWithoutDomainLabel',
        'passwordLabel', 'closeBtn', 'startTestBtn', 'saveWebSettingsBtn',
        'webSettingsSaved', 'uploadSuccess', 'uploadFailed', 'copyFailed'
    ]
    
    missing_settings_keys = []
    for key in settings_keys:
        if key not in zh_keys or key not in en_keys:
            missing_settings_keys.append(key)
    
    if missing_settings_keys:
        print(f"❌ Settings相关键缺失: {missing_settings_keys}")
    else:
        print("✅ Settings相关键完整")
    
    return len(missing_in_en) == 0 and len(missing_in_zh) == 0 and len(missing_settings_keys) == 0

def test_js_files_i18n():
    """测试JavaScript文件中的国际化使用"""
    print("\n检查JavaScript文件中的国际化使用...")
    print("=" * 50)
    
    js_files = [
        "collabtrans/static/settings/general.js",
        "collabtrans/static/settings/ai-platforms.js", 
        "collabtrans/static/settings/parsing-engines.js",
        "collabtrans/static/settings/login-settings.js",
        "collabtrans/static/settings/web-settings.js"
    ]
    
    all_good = True
    
    for js_file in js_files:
        if not os.path.exists(js_file):
            print(f"❌ {js_file} 文件不存在")
            all_good = False
            continue
            
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否还有硬编码的中文文本
        chinese_pattern = r'[\u4e00-\u9fff]+'
        chinese_matches = re.findall(chinese_pattern, content)
        
        # 过滤掉注释中的中文
        filtered_matches = []
        for match in chinese_matches:
            # 检查是否在注释中
            lines = content.split('\n')
            for line in lines:
                if match in line and not line.strip().startswith('//'):
                    filtered_matches.append(match)
                    break
        
        if filtered_matches:
            print(f"❌ {js_file} 中仍有硬编码中文: {set(filtered_matches)}")
            all_good = False
        else:
            print(f"✅ {js_file} 国际化完成")
    
    return all_good

def test_html_files_i18n():
    """测试HTML文件中的国际化使用"""
    print("\n检查HTML文件中的国际化使用...")
    print("=" * 50)
    
    html_files = [
        "collabtrans/static/settings/general.html",
        "collabtrans/static/settings/ai-platforms.html",
        "collabtrans/static/settings/parsing-engines.html", 
        "collabtrans/static/settings/login-settings.html",
        "collabtrans/static/settings/web-settings.html"
    ]
    
    all_good = True
    
    for html_file in html_files:
        if not os.path.exists(html_file):
            print(f"❌ {html_file} 文件不存在")
            all_good = False
            continue
            
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有未国际化的placeholder
        placeholder_pattern = r'placeholder="[^"]*[\u4e00-\u9fff][^"]*"'
        placeholder_matches = re.findall(placeholder_pattern, content)
        
        if placeholder_matches:
            print(f"❌ {html_file} 中有未国际化的中文placeholder: {placeholder_matches}")
            all_good = False
        else:
            print(f"✅ {html_file} placeholder国际化完成")
        
        # 检查是否有未国际化的文本内容
        text_pattern = r'>[^<]*[\u4e00-\u9fff][^<]*<'
        text_matches = re.findall(text_pattern, content)
        
        # 过滤掉已经有data-i18n属性的元素
        filtered_text_matches = []
        for match in text_matches:
            # 检查这个文本是否在已经有data-i18n的元素中
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if match.strip() in line:
                    # 检查前面的行是否有data-i18n
                    has_i18n = False
                    for j in range(max(0, i-3), i+1):
                        if 'data-i18n=' in lines[j]:
                            has_i18n = True
                            break
                    if not has_i18n:
                        filtered_text_matches.append(match.strip())
                    break
        
        if filtered_text_matches:
            print(f"❌ {html_file} 中有未国际化的中文文本: {filtered_text_matches}")
            all_good = False
        else:
            print(f"✅ {html_file} 文本国际化完成")
    
    return all_good

def test_settings_core_i18n():
    """测试settings-core.js的国际化功能"""
    print("\n检查settings-core.js的国际化功能...")
    print("=" * 50)
    
    core_file = "collabtrans/static/settings/settings-core.js"
    if not os.path.exists(core_file):
        print("❌ settings-core.js文件不存在")
        return False
    
    with open(core_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键功能是否存在
    required_functions = [
        'getText',
        'setLanguage', 
        'initLanguageSync',
        'loadI18nData'
    ]
    
    missing_functions = []
    for func in required_functions:
        if f'function {func}' not in content and f'const {func}' not in content:
            missing_functions.append(func)
    
    if missing_functions:
        print(f"❌ 缺失关键函数: {missing_functions}")
        return False
    else:
        print("✅ 关键国际化函数完整")
    
    # 检查语言同步机制
    sync_mechanisms = [
        'languageChanged',
        'storage',
        'setInterval'
    ]
    
    missing_sync = []
    for mechanism in sync_mechanisms:
        if mechanism not in content:
            missing_sync.append(mechanism)
    
    if missing_sync:
        print(f"❌ 缺失语言同步机制: {missing_sync}")
        return False
    else:
        print("✅ 语言同步机制完整")
    
    return True

def main():
    """主测试函数"""
    print("开始测试Settings页面国际化完整性...")
    print("=" * 60)
    
    test1 = test_i18n_data_completeness()
    test2 = test_js_files_i18n()
    test3 = test_html_files_i18n()
    test4 = test_settings_core_i18n()
    
    print("\n" + "=" * 60)
    if test1 and test2 and test3 and test4:
        print("🎉 Settings页面国际化完成！")
        print("\n主要改进:")
        print("✅ 所有JavaScript文件中的硬编码中文文本已国际化")
        print("✅ 所有HTML文件中的placeholder和文本已国际化")
        print("✅ i18nData.json包含完整的中英文翻译")
        print("✅ settings-core.js包含完整的国际化功能")
        print("✅ 实现了跨页面语言同步机制")
        print("\n现在Settings页面完全支持中英文切换，所有文本都会根据语言设置自动更新！")
    else:
        print("❌ Settings页面国际化未完全完成，请检查上述问题")

if __name__ == "__main__":
    main()
