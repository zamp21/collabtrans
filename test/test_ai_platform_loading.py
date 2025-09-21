#!/usr/bin/env python3
"""
测试Settings页面AI Platform加载功能
"""

import requests
import json
import sys

def test_ai_platform_loading():
    """测试AI Platform配置加载"""
    print("=== 测试Settings页面AI Platform加载功能 ===")
    
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
                
        else:
            print(f"❌ API响应失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return False
    
    # 测试前端页面
    try:
        print("\n2. 测试前端页面 /settings")
        response = requests.get('http://localhost:5000/settings')
        if response.status_code == 200:
            print(f"✅ Settings页面加载成功: {response.status_code}")
        else:
            print(f"❌ Settings页面加载失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 前端页面测试失败: {e}")
        return False
    
    print("\n=== 测试完成 ===")
    return True

if __name__ == "__main__":
    success = test_ai_platform_loading()
    sys.exit(0 if success else 1)
