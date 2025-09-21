#!/usr/bin/env python3
"""
验证Settings页面AI Platform加载功能
"""

import requests
import json
import sys

def verify_settings_ai_platform():
    """验证Settings页面AI Platform功能"""
    print("=== 验证Settings页面AI Platform功能 ===")
    
    # 测试后端API
    try:
        print("\n1. 测试后端API /auth/app-config")
        response = requests.get('http://localhost:5000/auth/app-config')
        if response.status_code == 200:
            config = response.json()
            print(f"✅ API响应成功: {response.status_code}")
            
            # 检查ai_platforms配置
            ai_platforms = config.get('ai_platforms', {})
            print(f"📊 AI平台配置数量: {len(ai_platforms)}")
            
            if ai_platforms:
                print("📋 平台配置详情:")
                for key, platform in ai_platforms.items():
                    print(f"  - {key}: {platform.get('name', 'N/A')} ({platform.get('url', 'N/A')})")
            else:
                print("⚠️  没有找到AI平台配置")
                return False
                
        else:
            print(f"❌ API响应失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return False
    
    # 测试Settings页面
    try:
        print("\n2. 测试Settings页面")
        response = requests.get('http://localhost:5000/settings')
        if response.status_code == 200:
            print(f"✅ Settings页面加载成功: {response.status_code}")
            
            # 检查页面内容
            content = response.text
            if 'ai-platforms' in content:
                print("✅ 找到AI Platform模块引用")
            else:
                print("⚠️  未找到AI Platform模块引用")
                
        else:
            print(f"❌ Settings页面加载失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Settings页面测试失败: {e}")
        return False
    
    print("\n=== 验证完成 ===")
    print("📝 请手动测试以下功能:")
    print("1. 访问 http://localhost:5000/settings")
    print("2. 点击 'AI Platform' 导航链接")
    print("3. 检查平台选择下拉框是否显示选项")
    print("4. 查看浏览器控制台的调试信息")
    print("5. 测试平台切换功能")
    
    return True

if __name__ == "__main__":
    success = verify_settings_ai_platform()
    sys.exit(0 if success else 1)
