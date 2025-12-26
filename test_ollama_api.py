#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""
Test script for Ollama API to diagnose translation issues
"""
import json
import time
import httpx
from datetime import datetime

# Configuration from the saved API call
OLLAMA_BASE_URL = "http://192.168.220.42:11434"
MODEL_ID = "qwen3:30b"
TIMEOUT = 120  # seconds

# Test data from the saved API call
SYSTEM_PROMPT = """
# Role
- You are a professional machine translation engine with expertise in natural, fluent translation.

# Task
- You will receive a sequence of segments to be translated, represented in JSON format. The keys are the segment IDs, and the values are the segments for translation.
- You need to translate these segments into English.

# Requirements
- **Natural and Fluent Translation**: The translation must sound natural and fluent in the target language. Avoid literal word-for-word translations that sound awkward or unnatural.
- **Cultural Adaptation**: Adapt cultural references, idioms, and expressions to be appropriate for the target language and culture. Use equivalent expressions that native speakers would naturally use.
- **Professional Quality**: The translation must be professional, accurate, and maintain the original meaning while being easily readable.
- **No Explanations**: Do not output any explanations, annotations, or meta-commentary.
- **Format Preservation**: The format of the translated segments should be as close as possible to the source format.
- **Proper Nouns**: For personal names and proper nouns, use the most commonly accepted translations.
- **Technical Elements**: Keep special tags, codes, brand names, and technical jargon in their original form when appropriate.
- **Target Language Check**: If a segment is already in the target language(English), keep it as is.
- **Segment Integrity**: Do not merge multiple segment translations into one translation.
- **JSON Structure**: (very important) All keys that appear in the input JSON must exist in the output JSON.
# Output
- The translated sequence of segments, represented as JSON text (note: not a code block). The keys are the segment IDs, and the values are the translated segments.
- The response must be a JSON object with the following structure: 
{
"<segment_id>": "<translation>"
}
- (very important) The segment IDs in the output must exactly match those in the input. And all segment IDs in input must appear in the output.
# Example(Assuming the target language is English in the example, English is the actual target language)
## Input
{
"10": "Tom said: "Hello"",
"11": "Apple",
"12": true,
"13": "Error",
"14": null
}
## Correct Output
{
"21": "Tom says:\"hello\"",
"22": "apple",
"23": "error",
"24": "banana"
}
"""

# Test chunk from the saved API call
TEST_CHUNK = {
    "0": "别让\"可爱肥\"害了猫！",
    "1": "猫咪肥胖的危害与减肥妙招",
    "2": "圆滚滚的猫咪确实憨态可掬，戳中不少铲屎官的萌点。但",
    "3": "你知道吗？如果任由猫咪\"肆无忌惮\"地胖下去，这份\"可爱肥\"背后，隐藏着对它们健康的巨大威胁！保持健康的体",
    "4": "重，对猫咪来说至关重要！",
    "5": "猫咪为什么会\"发福\"？",
    "6": "猫咪变胖不是无缘无故的，常见的原因有：",
    "7": "•\"干饭王\"遇上\"溺爱家长\"：吃得太好、太多是主因！有些猫咪天生\"干饭魂\"熊熊燃烧，根本不懂得控制食量。如果铲屎官不主动帮它们\"踩刹车\"，很容易就喂出个\"小煤气罐\"。",
    "8": "•零食无限量供应：小鱼干、猫条固然是爱的表达，但无节制地投喂零食，不仅会导致肥胖，还可能让猫咪挑食，拒绝吃主食，营养失衡雪上加霜。"
}


def test_ollama_connection(base_url: str, timeout: int = 5):
    """Test basic connection to Ollama server"""
    print("=" * 80)
    print("Test 1: Basic Connection Test")
    print("=" * 80)
    try:
        endpoint = f"{base_url}/api/tags"
        print(f"Testing connection to: {endpoint}")
        with httpx.Client(timeout=timeout) as client:
            response = client.get(endpoint)
            response.raise_for_status()
            data = response.json()
            print(f"✅ Connection successful!")
            print(f"Available models: {[m.get('name', 'unknown') for m in data.get('models', [])]}")
            return True
    except httpx.ConnectError as e:
        print(f"❌ Connection failed: {e}")
        print("   Check if Ollama server is running and accessible")
        return False
    except httpx.TimeoutException as e:
        print(f"❌ Connection timeout: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_model_status(base_url: str, model_id: str, timeout: int = 10):
    """Test if model is loaded and ready"""
    print("\n" + "=" * 80)
    print("Test 2: Model Status Check")
    print("=" * 80)
    try:
        endpoint = f"{base_url}/api/show"
        print(f"Checking model status: {model_id}")
        with httpx.Client(timeout=timeout) as client:
            response = client.post(endpoint, json={"name": model_id})
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Model '{model_id}' is available")
                print(f"   Model details: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
                return True
            else:
                print(f"⚠️  Model status check returned: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
    except Exception as e:
        print(f"❌ Error checking model: {e}")
        return False


def test_simple_chat(base_url: str, model_id: str, timeout: int = 30):
    """Test simple chat request"""
    print("\n" + "=" * 80)
    print("Test 3: Simple Chat Test (Short Prompt)")
    print("=" * 80)
    try:
        endpoint = f"{base_url}/api/chat"
        data = {
            "model": model_id,
            "messages": [
                {"role": "user", "content": "Translate to English: 你好"}
            ],
            "stream": False,
            "options": {
                "temperature": 0.3
            }
        }
        print(f"Sending simple request to: {endpoint}")
        print(f"Model: {model_id}")
        print(f"Timeout: {timeout}s")
        
        start_time = time.time()
        with httpx.Client(timeout=timeout) as client:
            response = client.post(endpoint, json=data)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("message", {}).get("content", "")
                print(f"✅ Request successful! (took {elapsed:.2f}s)")
                print(f"Response: {content[:200]}")
                return True, elapsed
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False, elapsed
    except httpx.ReadTimeout:
        elapsed = time.time() - start_time if 'start_time' in locals() else timeout
        print(f"❌ ReadTimeout: Server did not respond within {timeout}s (actual: {elapsed:.2f}s)")
        return False, elapsed
    except httpx.ConnectError as e:
        print(f"❌ Connection error: {e}")
        return False, 0
    except Exception as e:
        elapsed = time.time() - start_time if 'start_time' in locals() else 0
        print(f"❌ Error: {e}")
        return False, elapsed


def test_translation_request(base_url: str, model_id: str, chunk: dict, system_prompt: str, 
                             timeout: int = 120, test_name: str = "Translation Request"):
    """Test the actual translation request format"""
    print("\n" + "=" * 80)
    print(f"Test 4: {test_name}")
    print("=" * 80)
    try:
        endpoint = f"{base_url}/api/chat"
        chunk_json = json.dumps(chunk, ensure_ascii=False, indent=0)
        
        data = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chunk_json}
            ],
            "stream": False,
            "options": {
                "temperature": 0.3
            }
        }
        
        print(f"Endpoint: {endpoint}")
        print(f"Model: {model_id}")
        print(f"Timeout: {timeout}s")
        print(f"Chunk size: {len(chunk_json)} characters, {len(chunk)} segments")
        print(f"Chunk preview: {chunk_json[:200]}...")
        
        start_time = time.time()
        with httpx.Client(timeout=httpx.Timeout(connect=5, read=timeout, write=300, pool=10)) as client:
            response = client.post(endpoint, json=data)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("message", {}).get("content", "")
                print(f"✅ Request successful! (took {elapsed:.2f}s)")
                print(f"Response length: {len(content)} characters")
                print(f"Response preview: {content[:300]}...")
                
                # Try to parse as JSON
                try:
                    parsed = json.loads(content)
                    print(f"✅ Response is valid JSON with {len(parsed)} keys")
                except json.JSONDecodeError as e:
                    print(f"⚠️  Response is not valid JSON: {e}")
                
                return True, elapsed
            elif response.status_code == 500:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", response.text)
                print(f"❌ Server error (500): {error_msg}")
                if "loading model" in error_msg.lower():
                    print("   ⚠️  Model is still loading! Wait for it to finish loading.")
                return False, elapsed
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False, elapsed
                
    except httpx.ReadTimeout:
        elapsed = time.time() - start_time if 'start_time' in locals() else timeout
        print(f"❌ ReadTimeout: Server did not respond within {timeout}s (actual: {elapsed:.2f}s)")
        print("   Possible causes:")
        print("   1. Model is too slow for this chunk size")
        print("   2. Model is still loading")
        print("   3. Server is overloaded")
        print("   4. Network issues")
        return False, elapsed
    except httpx.ConnectError as e:
        print(f"❌ Connection error: {e}")
        return False, 0
    except Exception as e:
        elapsed = time.time() - start_time if 'start_time' in locals() else 0
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False, elapsed


def test_smaller_chunk(base_url: str, model_id: str, system_prompt: str, timeout: int = 120):
    """Test with a smaller chunk"""
    print("\n" + "=" * 80)
    print("Test 5: Smaller Chunk Test")
    print("=" * 80)
    
    # Create a smaller chunk with just 2 segments
    small_chunk = {
        "0": "别让\"可爱肥\"害了猫！",
        "1": "猫咪肥胖的危害与减肥妙招"
    }
    
    return test_translation_request(base_url, model_id, small_chunk, system_prompt, timeout, "Smaller Chunk Test")


def test_running_models(base_url: str, timeout: int = 10):
    """Check which models are currently running/loaded"""
    print("\n" + "=" * 80)
    print("Test 6: Running Models Check")
    print("=" * 80)
    try:
        endpoint = f"{base_url}/api/ps"
        print(f"Checking running models: {endpoint}")
        with httpx.Client(timeout=timeout) as client:
            response = client.get(endpoint)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                if models:
                    print(f"✅ Found {len(models)} running model(s):")
                    for model in models:
                        name = model.get("name", "unknown")
                        size = model.get("size_vram", 0) / (1024**3)  # GB
                        print(f"   - {name} (VRAM: {size:.2f}GB)")
                    return True
                else:
                    print("⚠️  No models currently loaded in memory")
                    print("   Model will be loaded on first request (this may take time)")
                    return False
            else:
                print(f"⚠️  Status check returned: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
    except Exception as e:
        print(f"❌ Error checking running models: {e}")
        return False


def test_streaming_response(base_url: str, model_id: str, timeout: int = 60):
    """Test streaming response (may be faster than non-streaming)"""
    print("\n" + "=" * 80)
    print("Test 7: Streaming Response Test")
    print("=" * 80)
    try:
        endpoint = f"{base_url}/api/chat"
        data = {
            "model": model_id,
            "messages": [
                {"role": "user", "content": "Say hello in one word"}
            ],
            "stream": True,  # Enable streaming
            "options": {
                "temperature": 0.3
            }
        }
        print(f"Testing streaming request to: {endpoint}")
        print(f"Model: {model_id}, Timeout: {timeout}s")
        
        start_time = time.time()
        chunks_received = 0
        full_response = ""
        
        with httpx.Client(timeout=timeout) as client:
            with client.stream("POST", endpoint, json=data) as response:
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            try:
                                chunk_data = json.loads(line)
                                if "message" in chunk_data:
                                    content = chunk_data["message"].get("content", "")
                                    if content:
                                        full_response += content
                                        chunks_received += 1
                                if chunk_data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
                    
                    elapsed = time.time() - start_time
                    print(f"✅ Streaming successful! (took {elapsed:.2f}s)")
                    print(f"   Received {chunks_received} chunks")
                    print(f"   Response: {full_response[:200]}")
                    return True, elapsed
                else:
                    elapsed = time.time() - start_time
                    print(f"❌ Request failed: {response.status_code}")
                    print(f"Response: {response.text[:500]}")
                    return False, elapsed
    except httpx.ReadTimeout:
        elapsed = time.time() - start_time if 'start_time' in locals() else timeout
        print(f"❌ ReadTimeout: Server did not respond within {timeout}s")
        return False, elapsed
    except Exception as e:
        elapsed = time.time() - start_time if 'start_time' in locals() else 0
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False, elapsed


def test_minimal_request(base_url: str, model_id: str, timeout: int = 60):
    """Test with minimal request (no system prompt, very short user prompt)"""
    print("\n" + "=" * 80)
    print("Test 8: Minimal Request Test")
    print("=" * 80)
    try:
        endpoint = f"{base_url}/api/chat"
        data = {
            "model": model_id,
            "messages": [
                {"role": "user", "content": "Hi"}
            ],
            "stream": False,
            "options": {
                "temperature": 0.3
            }
        }
        print(f"Testing minimal request: single word 'Hi'")
        print(f"Endpoint: {endpoint}, Model: {model_id}, Timeout: {timeout}s")
        
        start_time = time.time()
        with httpx.Client(timeout=httpx.Timeout(connect=5, read=timeout, write=300, pool=10)) as client:
            response = client.post(endpoint, json=data)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("message", {}).get("content", "")
                print(f"✅ Minimal request successful! (took {elapsed:.2f}s)")
                print(f"Response: {content[:200]}")
                return True, elapsed
            elif response.status_code == 500:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", response.text)
                print(f"❌ Server error (500): {error_msg}")
                if "loading model" in error_msg.lower():
                    print("   ⚠️  Model is still loading!")
                return False, elapsed
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False, elapsed
    except httpx.ReadTimeout:
        elapsed = time.time() - start_time if 'start_time' in locals() else timeout
        print(f"❌ ReadTimeout: Server did not respond within {timeout}s (actual: {elapsed:.2f}s)")
        return False, elapsed
    except Exception as e:
        elapsed = time.time() - start_time if 'start_time' in locals() else 0
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False, elapsed


def test_generate_endpoint(base_url: str, model_id: str, timeout: int = 60):
    """Test /api/generate endpoint (alternative to /api/chat)"""
    print("\n" + "=" * 80)
    print("Test 9: Generate Endpoint Test")
    print("=" * 80)
    try:
        endpoint = f"{base_url}/api/generate"
        data = {
            "model": model_id,
            "prompt": "Hello",
            "stream": False,
            "options": {
                "temperature": 0.3
            }
        }
        print(f"Testing /api/generate endpoint")
        print(f"Endpoint: {endpoint}, Model: {model_id}, Timeout: {timeout}s")
        
        start_time = time.time()
        with httpx.Client(timeout=httpx.Timeout(connect=5, read=timeout, write=300, pool=10)) as client:
            response = client.post(endpoint, json=data)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "")
                print(f"✅ Generate endpoint successful! (took {elapsed:.2f}s)")
                print(f"Response: {content[:200]}")
                return True, elapsed
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False, elapsed
    except httpx.ReadTimeout:
        elapsed = time.time() - start_time if 'start_time' in locals() else timeout
        print(f"❌ ReadTimeout: Server did not respond within {timeout}s")
        return False, elapsed
    except Exception as e:
        elapsed = time.time() - start_time if 'start_time' in locals() else 0
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False, elapsed


def test_alternative_model(base_url: str, timeout: int = 30):
    """Test with a smaller alternative model"""
    print("\n" + "=" * 80)
    print("Test 10: Alternative Model Test")
    print("=" * 80)
    
    # Try smaller models that were shown in the available models list
    alternative_models = ["qwen2.5-coder:1.5b", "qwen2.5-coder:latest"]
    
    for alt_model in alternative_models:
        print(f"\n--- Testing with model: {alt_model} ---")
        success, elapsed = test_minimal_request(base_url, alt_model, timeout)
        if success:
            print(f"✅ Alternative model '{alt_model}' works!")
            return True, alt_model
    
    print("❌ All alternative models failed")
    return False, None


def test_with_different_timeouts(base_url: str, model_id: str, chunk: dict, system_prompt: str):
    """Test with different timeout values"""
    print("\n" + "=" * 80)
    print("Test 11: Different Timeout Values")
    print("=" * 80)
    
    timeouts = [60, 120, 180, 300]
    results = []
    
    for timeout in timeouts:
        print(f"\n--- Testing with timeout: {timeout}s ---")
        success, elapsed = test_translation_request(
            base_url, model_id, chunk, system_prompt, timeout, 
            f"Timeout Test ({timeout}s)"
        )
        results.append((timeout, success, elapsed))
        
        if success:
            print(f"✅ Success with {timeout}s timeout!")
            break
        elif elapsed < timeout - 5:  # If it failed but didn't timeout
            print(f"⚠️  Failed before timeout, may not be a timeout issue")
            break
    
    print("\n" + "-" * 80)
    print("Timeout Test Summary:")
    for timeout, success, elapsed in results:
        status = "✅ Success" if success else "❌ Failed"
        print(f"  {timeout}s: {status} (took {elapsed:.2f}s)")
    
    return results


def main():
    print("Ollama API Diagnostic Test Script")
    print("=" * 80)
    print(f"Target: {OLLAMA_BASE_URL}")
    print(f"Model: {MODEL_ID}")
    print(f"Default Timeout: {TIMEOUT}s")
    print(f"Test Time: {datetime.now().isoformat()}")
    print("=" * 80)
    
    # Test 1: Basic connection
    if not test_ollama_connection(OLLAMA_BASE_URL):
        print("\n❌ Cannot connect to Ollama server. Please check:")
        print("   1. Is Ollama server running?")
        print("   2. Is the URL correct?")
        print("   3. Is the server accessible from this machine?")
        return
    
    # Test 2: Model status
    if not test_model_status(OLLAMA_BASE_URL, MODEL_ID):
        print("\n⚠️  Model status check failed, but continuing with tests...")
    
    # Test 3: Simple chat
    success, elapsed = test_simple_chat(OLLAMA_BASE_URL, MODEL_ID, timeout=30)
    if not success:
        print("\n⚠️  Simple chat test failed, but continuing with translation test...")
    
    # Test 6: Check running models
    test_running_models(OLLAMA_BASE_URL)
    
    # Test 7: Test streaming response
    print("\n" + "⚠️" * 40)
    print("Testing streaming response (may be faster)...")
    test_streaming_response(OLLAMA_BASE_URL, MODEL_ID, timeout=60)
    
    # Test 8: Test minimal request
    print("\n" + "⚠️" * 40)
    print("Testing minimal request (no system prompt, single word)...")
    test_minimal_request(OLLAMA_BASE_URL, MODEL_ID, timeout=60)
    
    # Test 9: Test generate endpoint
    print("\n" + "⚠️" * 40)
    print("Testing /api/generate endpoint (alternative to /api/chat)...")
    test_generate_endpoint(OLLAMA_BASE_URL, MODEL_ID, timeout=60)
    
    # Test 10: Test alternative models
    print("\n" + "⚠️" * 40)
    print("Testing with smaller alternative models...")
    test_alternative_model(OLLAMA_BASE_URL, timeout=30)
    
    # Test 4: Actual translation request
    print("\n" + "=" * 80)
    print("Now testing actual translation request...")
    success, elapsed = test_translation_request(
        OLLAMA_BASE_URL, MODEL_ID, TEST_CHUNK, SYSTEM_PROMPT, TIMEOUT
    )
    
    if not success:
        # Test 5: Try with smaller chunk
        print("\n" + "⚠️" * 40)
        print("Original request failed. Trying with smaller chunk...")
        test_smaller_chunk(OLLAMA_BASE_URL, MODEL_ID, SYSTEM_PROMPT, TIMEOUT)
        
        # Test 11: Try with different timeouts
        print("\n" + "⚠️" * 40)
        print("Trying with different timeout values...")
        test_with_different_timeouts(OLLAMA_BASE_URL, MODEL_ID, TEST_CHUNK, SYSTEM_PROMPT)
    
    print("\n" + "=" * 80)
    print("Diagnostic Test Complete")
    print("=" * 80)
    print("\nRecommendations:")
    print("1. If connection fails: Check Ollama server status and network connectivity")
    print("2. If model is loading: Wait for model to finish loading before retrying")
    print("3. If timeout occurs: Try increasing timeout or reducing chunk size")
    print("4. If 500 error with 'loading model': The model is still loading, wait and retry")
    print("5. Check Ollama server logs for more details")


if __name__ == "__main__":
    main()

