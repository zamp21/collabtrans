#!/usr/bin/env python3
"""
恢复完整的AI平台配置
"""

import json
import os

# 默认的平台配置
DEFAULT_PLATFORMS = {
    "deepseek": {
        "name": "DeepSeek",
        "url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "max_tokens": 64000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "openai": {
        "name": "OpenAI",
        "url": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "azure": {
        "name": "Azure OpenAI",
        "url": "https://your-resource.openai.azure.com/openai/deployments/your-deployment",
        "model": "gpt-4o",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "anthropic": {
        "name": "Anthropic",
        "url": "https://api.anthropic.com/v1",
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 200000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "google": {
        "name": "Google",
        "url": "https://generativelanguage.googleapis.com/v1beta",
        "model": "gemini-1.5-pro",
        "max_tokens": 1000000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "mistral": {
        "name": "Mistral",
        "url": "https://api.mistral.ai/v1",
        "model": "mistral-large-latest",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "cohere": {
        "name": "Cohere",
        "url": "https://api.cohere.ai/v1",
        "model": "command-r-plus",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "xai": {
        "name": "xAI",
        "url": "https://api.x.ai/v1",
        "model": "grok-beta",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "groq": {
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-70b-versatile",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "together": {
        "name": "Together",
        "url": "https://api.together.xyz/v1",
        "model": "meta-llama/Llama-3.1-70B-Instruct-Turbo",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "dashscope": {
        "name": "DashScope",
        "url": "https://dashscope.aliyuncs.com/api/v1",
        "model": "qwen-plus",
        "max_tokens": 30000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "volcengine_ark": {
        "name": "VolcEngine",
        "url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "ep-20241220180000-abcde",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "siliconflow": {
        "name": "SiliconFlow",
        "url": "https://api.siliconflow.cn/v1",
        "model": "deepseek-ai/deepseek-chat",
        "max_tokens": 64000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "zhipu": {
        "name": "智谱AI",
        "url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "dmxapi": {
        "name": "DMX API",
        "url": "https://api.dmxapi.com/v1",
        "model": "gpt-4o",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "openrouter": {
        "name": "OpenRouter",
        "url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4o",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "ollama": {
        "name": "Ollama",
        "url": "http://localhost:11434/v1",
        "model": "llama3.1:70b",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "lmstudio": {
        "name": "LM Studio",
        "url": "http://localhost:1234/v1",
        "model": "gpt-4o",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "hunyuan": {
        "name": "混元",
        "url": "https://hunyuan.tencentcloudapi.com",
        "model": "hunyuan-lite",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "baidu": {
        "name": "百度",
        "url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
        "model": "ernie-4.0-8k",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "moonshot": {
        "name": "月之暗面",
        "url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    },
    "custom": {
        "name": "自定义",
        "url": "https://api.example.com/v1",
        "model": "custom-model",
        "max_tokens": 128000,
        "temperature": 0.7,
        "recommended_tokens": None,
        "performance_note": None
    }
}

def restore_global_config():
    """恢复global_config.json中的完整平台配置"""
    
    # 读取当前的global_config.json
    config_file = "global_config.json"
    if not os.path.exists(config_file):
        print(f"❌ 配置文件 {config_file} 不存在")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"📋 当前配置中的平台: {list(config.get('ai_platforms', {}).keys())}")
        
        # 恢复完整的平台配置
        config['ai_platforms'] = DEFAULT_PLATFORMS
        
        # 备份原文件
        backup_file = f"{config_file}.backup"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"📋 已备份原配置到: {backup_file}")
        
        # 写入新配置
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 已恢复 {len(DEFAULT_PLATFORMS)} 个平台的配置")
        print(f"📋 恢复的平台: {list(DEFAULT_PLATFORMS.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ 恢复配置失败: {e}")
        return False

if __name__ == "__main__":
    print("🔧 开始恢复AI平台配置...")
    success = restore_global_config()
    if success:
        print("✅ 平台配置恢复完成！")
    else:
        print("❌ 平台配置恢复失败！")
