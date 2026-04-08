#!/usr/bin/env python3
import urllib.request
import urllib.error

# Test different API paths
base_url = "http://192.168.220.141:7860"
test_paths = [
    "/api",
    "/api/v1",
    "/api/v2",
    "/api/v3",
    "/api/v4",
    "/docs",
    "/openapi.json",
    "/swagger.json",
    "/redoc",
    "/extract",
    "/file-urls",
    "/extract-results"
]

print("Testing different API paths...")
print("=" * 60)

for path in test_paths:
    url = f"{base_url}{path}"
    try:
        response = urllib.request.urlopen(url, timeout=10)
        status = response.status
        content = response.read().decode('utf-8')[:200]
        print(f"✓ {url} - Status: {status}")
        print(f"  Content: {content}...")
    except urllib.error.HTTPError as e:
        print(f"✗ {url} - HTTP Error: {e.code}")
        try:
            content = e.read().decode('utf-8')[:200]
            print(f"  Content: {content}...")
        except:
            pass
    except urllib.error.URLError as e:
        print(f"✗ {url} - URL Error: {e}")
    except Exception as e:
        print(f"✗ {url} - Error: {e}")
    print("-" * 60)
