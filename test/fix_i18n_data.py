import json
import os

# 文件路径
file_path = "collabtrans/i18n/i18nData.json"

# 读取JSON文件
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 检查并添加缺失的键
    missing_keys = {
        'mineruTokenPlaceholder': 'Required when using Mineru engine',
        'saveLdapConfigBtn': 'Save LDAP Config'
    }
    
    updated = False
    for key, value in missing_keys.items():
        if key not in data['en']:
            data['en'][key] = value
            updated = True
            print(f"✅ 添加缺失的英文键 '{key}': '{value}'")
    
    # 如果有更新，保存文件
    if updated:
        # 先备份文件
        backup_path = f"{file_path}.backup"
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 再保存更新后的文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ i18nData.json 文件已更新并备份到 {backup_path}")
    else:
        print("✅ 英文部分已经包含所有需要的键，无需更新")
    
    # 再次验证
    zh_keys = set(data.get('zh', {}).keys())
    en_keys = set(data.get('en', {}).keys())
    zh_missing = en_keys - zh_keys
    en_missing = zh_keys - en_keys
    
    print(f"\n=== 修复后验证结果 ===")
    print(f"总键数量: 中文 {len(zh_keys)}, 英文 {len(en_keys)}")
    if not zh_missing and not en_missing:
        print("✅ 所有键现在完全对应，没有缺失或多余的项！")
    
# 错误处理
except FileNotFoundError:
    print(f"错误: 找不到文件 {file_path}")
except json.JSONDecodeError:
    print(f"错误: JSON格式无效")
except Exception as e:
    print(f"错误: {str(e)}")