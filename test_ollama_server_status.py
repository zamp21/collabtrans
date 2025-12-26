#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""
Ollama Server Status and Network Diagnostic Script
"""
import json
import subprocess
import time
import httpx
from datetime import datetime

OLLAMA_BASE_URL = "http://192.168.220.42:11434"
MODEL_ID = "qwen3:30b"


def test_network_connectivity(host: str, port: int):
    """Test basic network connectivity"""
    print("=" * 80)
    print("Network Connectivity Test")
    print("=" * 80)
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ Port {port} on {host} is open and accessible")
            return True
        else:
            print(f"❌ Port {port} on {host} is not accessible (error code: {result})")
            return False
    except Exception as e:
        print(f"❌ Network test failed: {e}")
        return False


def test_http_response_time(base_url: str):
    """Test HTTP response time"""
    print("\n" + "=" * 80)
    print("HTTP Response Time Test")
    print("=" * 80)
    try:
        endpoint = f"{base_url}/api/tags"
        times = []
        for i in range(5):
            start = time.time()
            with httpx.Client(timeout=10) as client:
                response = client.get(endpoint)
                elapsed = (time.time() - start) * 1000  # ms
                times.append(elapsed)
                if response.status_code == 200:
                    print(f"  Request {i+1}: {elapsed:.2f}ms ✅")
                else:
                    print(f"  Request {i+1}: {elapsed:.2f}ms ❌ (status: {response.status_code})")
        
        avg_time = sum(times) / len(times)
        print(f"\nAverage response time: {avg_time:.2f}ms")
        if avg_time > 1000:
            print("⚠️  High latency detected (>1s). This may affect model response times.")
        return True
    except Exception as e:
        print(f"❌ HTTP test failed: {e}")
        return False


def check_model_loading_status(base_url: str, model_id: str):
    """Check if model is currently loading"""
    print("\n" + "=" * 80)
    print("Model Loading Status Check")
    print("=" * 80)
    
    # Try to make a request and see if we get "loading model" error
    endpoint = f"{base_url}/api/chat"
    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": "test"}],
        "stream": False
    }
    
    try:
        with httpx.Client(timeout=5) as client:
            response = client.post(endpoint, json=data)
            if response.status_code == 500:
                error_text = response.text
                if "loading model" in error_text.lower():
                    print("⚠️  Model is currently loading!")
                    print("   This is normal for large models (30B).")
                    print("   Wait for the model to finish loading before making requests.")
                    return True
                else:
                    print(f"⚠️  Server error (500): {error_text[:200]}")
                    return False
            elif response.status_code == 200:
                print("✅ Model appears to be loaded and ready")
                return True
            else:
                print(f"⚠️  Unexpected status: {response.status_code}")
                return False
    except httpx.ReadTimeout:
        print("⚠️  Request timed out quickly - model may be loading or server is slow")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def check_server_resources(base_url: str):
    """Try to get server resource information"""
    print("\n" + "=" * 80)
    print("Server Resource Check")
    print("=" * 80)
    
    # Check if we can get process info
    try:
        endpoint = f"{base_url}/api/ps"
        with httpx.Client(timeout=10) as client:
            response = client.get(endpoint)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                print(f"Currently loaded models: {len(models)}")
                total_vram = 0
                for model in models:
                    name = model.get("name", "unknown")
                    vram = model.get("size_vram", 0) / (1024**3)  # GB
                    total_vram += vram
                    print(f"  - {name}: {vram:.2f}GB VRAM")
                
                if total_vram > 0:
                    print(f"\nTotal VRAM used: {total_vram:.2f}GB")
                    if total_vram > 20:
                        print("⚠️  High VRAM usage detected")
                return True
            else:
                print(f"⚠️  Could not get process info (status: {response.status_code})")
                return False
    except Exception as e:
        print(f"❌ Error checking resources: {e}")
        return False


def test_model_warmup(base_url: str, model_id: str):
    """Test if model needs warmup time"""
    print("\n" + "=" * 80)
    print("Model Warmup Test")
    print("=" * 80)
    print("Testing if model responds faster on subsequent requests...")
    
    endpoint = f"{base_url}/api/chat"
    data = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Say 'ready'"}],
        "stream": False,
        "options": {"temperature": 0.3}
    }
    
    results = []
    for i in range(3):
        print(f"\n  Warmup request {i+1}/3...")
        try:
            start = time.time()
            with httpx.Client(timeout=httpx.Timeout(connect=5, read=30, write=300, pool=10)) as client:
                response = client.post(endpoint, json=data)
                elapsed = time.time() - start
                
                if response.status_code == 200:
                    print(f"    ✅ Success in {elapsed:.2f}s")
                    results.append(("success", elapsed))
                elif response.status_code == 500:
                    error_text = response.json().get("error", response.text)
                    if "loading" in error_text.lower():
                        print(f"    ⚠️  Model still loading (after {elapsed:.2f}s)")
                        results.append(("loading", elapsed))
                    else:
                        print(f"    ❌ Server error: {error_text[:100]}")
                        results.append(("error", elapsed))
                else:
                    print(f"    ❌ Status {response.status_code}")
                    results.append(("error", elapsed))
        except httpx.ReadTimeout:
            print(f"    ❌ Timeout after 30s")
            results.append(("timeout", 30))
        except Exception as e:
            print(f"    ❌ Error: {e}")
            results.append(("error", 0))
        
        if i < 2:  # Wait between requests
            time.sleep(2)
    
    # Analyze results
    print("\n  Analysis:")
    success_count = sum(1 for r in results if r[0] == "success")
    if success_count > 0:
        success_times = [r[1] for r in results if r[0] == "success"]
        avg_time = sum(success_times) / len(success_times)
        print(f"    - {success_count}/3 requests succeeded")
        print(f"    - Average response time: {avg_time:.2f}s")
        if len(success_times) > 1:
            if success_times[-1] < success_times[0]:
                print("    - ✅ Model appears to warm up (faster on later requests)")
            else:
                print("    - ⚠️  No warmup effect observed")
    else:
        print("    - ❌ No successful requests")
    
    return results


def main():
    print("Ollama Server Status and Network Diagnostic")
    print("=" * 80)
    print(f"Target: {OLLAMA_BASE_URL}")
    print(f"Model: {MODEL_ID}")
    print(f"Test Time: {datetime.now().isoformat()}")
    print("=" * 80)
    
    # Extract host and port
    from urllib.parse import urlparse
    parsed = urlparse(OLLAMA_BASE_URL)
    host = parsed.hostname
    port = parsed.port or 11434
    
    # Test 1: Network connectivity
    if not test_network_connectivity(host, port):
        print("\n❌ Basic network connectivity failed. Check:")
        print("   1. Is the server running?")
        print("   2. Is the IP address correct?")
        print("   3. Are there firewall rules blocking the connection?")
        return
    
    # Test 2: HTTP response time
    test_http_response_time(OLLAMA_BASE_URL)
    
    # Test 3: Check model loading status
    check_model_loading_status(OLLAMA_BASE_URL, MODEL_ID)
    
    # Test 4: Check server resources
    check_server_resources(OLLAMA_BASE_URL)
    
    # Test 5: Model warmup test
    test_model_warmup(OLLAMA_BASE_URL, MODEL_ID)
    
    print("\n" + "=" * 80)
    print("Server Status Diagnostic Complete")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. If model is loading: Wait for it to finish (check with: curl http://192.168.220.42:11434/api/ps)")
    print("2. If network latency is high: Check network connection and server load")
    print("3. If model doesn't respond: Check server logs and resource usage")
    print("4. Consider using a smaller model if 30B is too slow for your hardware")


if __name__ == "__main__":
    main()

