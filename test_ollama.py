#!/usr/bin/env python3
"""
Test script for Ollama API connectivity
"""
import httpx
import json
import sys
from typing import Optional

def test_ollama_connection(base_url: str, model_name: str, timeout: float = 30.0):
    """Test Ollama API connection"""
    print(f"Testing Ollama connection...")
    print(f"Base URL: {base_url}")
    print(f"Model: {model_name}")
    print(f"Timeout: {timeout}s")
    print("-" * 60)
    
    # Clean base_url
    cleaned_base_url = base_url.strip().rstrip('/')
    for prefix in ['/v1', '/v1/chat', '/v1/chat/completions', '/api', '/api/chat']:
        if cleaned_base_url.endswith(prefix):
            cleaned_base_url = cleaned_base_url[:-len(prefix)]
            print(f"Removed path prefix '{prefix}' from base_url")
    
    print(f"Cleaned base URL: {cleaned_base_url}")
    print("-" * 60)
    
    # Test 1: Get available models
    print("\n[Test 1] Fetching available models...")
    try:
        models_endpoint = f"{cleaned_base_url}/api/tags"
        print(f"Endpoint: {models_endpoint}")
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(models_endpoint)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                models_data = response.json()
                available_models = []
                if "models" in models_data:
                    for model in models_data["models"]:
                        model_name_full = model.get("name", "unknown")
                        model_size = model.get("size", 0)
                        model_size_gb = model_size / (1024**3) if model_size > 0 else 0
                        available_models.append(f"{model_name_full} ({model_size_gb:.2f}GB)")
                
                print(f"✅ Success! Found {len(available_models)} models:")
                for model in available_models:
                    print(f"   - {model}")
                
                # Check if requested model exists
                model_exists = any(model_name in m for m in available_models)
                if not model_exists:
                    print(f"\n⚠️  Warning: Model '{model_name}' not found in available models")
            else:
                print(f"❌ Failed: {response.text}")
                return False
    except httpx.TimeoutException:
        print(f"❌ Timeout: Connection timeout after 10 seconds")
        return False
    except httpx.ConnectError as e:
        print(f"❌ Connection Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 2: Test chat API endpoint
    print(f"\n[Test 2] Testing chat API endpoint...")
    try:
        chat_endpoint = f"{cleaned_base_url}/api/chat"
        print(f"Endpoint: {chat_endpoint}")
        
        test_payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "Hello, this is a connection test. Please respond with 'OK'."}
            ],
            "stream": False
        }
        
        print(f"Payload: {json.dumps(test_payload, indent=2)}")
        print(f"Timeout: {timeout}s")
        
        with httpx.Client(timeout=timeout) as client:
            response = client.post(chat_endpoint, json=test_payload, headers={"Content-Type": "application/json"})
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"✅ Success! Response:")
                print(json.dumps(response_data, indent=2, ensure_ascii=False))
                
                # Check response format
                if "message" in response_data and "content" in response_data.get("message", {}):
                    content = response_data["message"]["content"]
                    print(f"\n✅ Response content: {content}")
                    return True
                else:
                    print(f"⚠️  Warning: Unexpected response format")
                    print(f"   Expected: {{'message': {{'content': '...'}}}}")
                    return False
            else:
                print(f"❌ Failed: {response.text}")
                return False
    except httpx.TimeoutException:
        print(f"❌ Timeout: Request timeout after {timeout} seconds")
        print(f"   This may happen if the model is loading for the first time.")
        return False
    except httpx.ConnectError as e:
        print(f"❌ Connection Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Test OpenAI-compatible endpoint (should fail for Ollama)
    print(f"\n[Test 3] Testing OpenAI-compatible endpoint (should fail for Ollama)...")
    try:
        openai_endpoint = f"{cleaned_base_url}/chat/completions"
        print(f"Endpoint: {openai_endpoint}")
        
        test_payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "max_tokens": 10
        }
        
        with httpx.Client(timeout=5.0) as client:
            response = client.post(openai_endpoint, json=test_payload, headers={"Content-Type": "application/json"})
            print(f"Status: {response.status_code}")
            
            if response.status_code == 404:
                print(f"✅ Expected: Ollama doesn't support OpenAI-compatible endpoint")
                print(f"   This confirms that Ollama uses /api/chat, not /chat/completions")
            else:
                print(f"⚠️  Unexpected: Got status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"✅ Expected error: {e}")
    
    return True


def main():
    """Main function"""
    if len(sys.argv) < 3:
        print("Usage: python test_ollama.py <base_url> <model_name> [timeout]")
        print("\nExample:")
        print("  python test_ollama.py http://192.168.220.42:11434 qwen3:30b")
        print("  python test_ollama.py http://192.168.220.42:11434 qwen3:30b 120")
        sys.exit(1)
    
    base_url = sys.argv[1]
    model_name = sys.argv[2]
    timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0
    
    success = test_ollama_connection(base_url, model_name, timeout)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ All tests passed! Ollama server is accessible.")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ Tests failed! Please check the errors above.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

