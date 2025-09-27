import json
import os

# 文件路径
file_path = "collabtrans/i18n/i18nSettings.json"

# 读取JSON文件
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 获取中文和英文部分
    zh_keys = set(data.get('zh', {}).keys())
    en_keys = set(data.get('en', {}).keys())
    
    # 检查缺失的键
    zh_missing = en_keys - zh_keys
    en_missing = zh_keys - en_keys
    
    # 输出结果
    print(f"=== i18nSettings.json 中英文键对比结果 ===")
    print(f"总键数量: 中文 {len(zh_keys)}, 英文 {len(en_keys)}")
    
    if not zh_missing and not en_missing:
        print("✅ 所有键完全对应，没有缺失或多余的项！")
    else:
        if zh_missing:
            print(f"❌ 中文部分缺失 {len(zh_missing)} 个键:")
            for key in sorted(zh_missing):
                print(f"  - {key}")
        
        if en_missing:
            print(f"❌ 英文部分缺失 {len(en_missing)} 个键:")
            for key in sorted(en_missing):
                print(f"  - {key}")
    
    print("==================================")
    
# 错误处理
except FileNotFoundError:
    print(f"错误: 找不到文件 {file_path}")
except json.JSONDecodeError:
    print(f"错误: JSON格式无效")
except Exception as e:
    print(f"错误: {str(e)}")