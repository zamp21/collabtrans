#!/usr/bin/env python3
"""
测试本地部署的MinerU服务
"""

import json
import urllib.request
import urllib.error
import io
import os

# 测试本地部署的MinerU服务
def test_local_mineru():
    base_url = "http://localhost:8920"
    
    print("测试本地部署的MinerU服务...")
    print(f"Base URL: {base_url}")
    
    # 测试文件解析端点
    test_paths = [
        "/file_parse",
        "/tasks"
    ]
    
    # 测试文件路径
    test_file_path = "test/test_files/example.pdf"
    
    # 检查测试文件是否存在
    if not os.path.exists(test_file_path):
        print(f"测试文件 {test_file_path} 不存在，创建一个测试文件...")
        # 创建一个简单的PDF文件
        with open(test_file_path, "wb") as f:
            f.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/MediaBox [0 0 612 792]\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/Name /F1\n/BaseFont /Helvetica\n/Encoding /WinAnsiEncoding\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Hello, MinerU!) Tj\nET\nendstream\nendobj\ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\n")
    
    # 读取测试文件内容
    with open(test_file_path, "rb") as f:
        pdf_content = f.read()
    
    for path in test_paths:
        test_url = f"{base_url}{path}"
        print(f"\n测试端点: {test_url}")
        
        try:
            # 创建multipart form data
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            data = []
            data.append(f"--{boundary}")
            data.append('Content-Disposition: form-data; name="backend"')
            data.append('')
            data.append('hybrid-auto-engine')
            data.append(f"--{boundary}")
            data.append('Content-Disposition: form-data; name="parse_method"')
            data.append('')
            data.append('auto')
            data.append(f"--{boundary}")
            data.append('Content-Disposition: form-data; name="formula_enable"')
            data.append('')
            data.append('true')
            data.append(f"--{boundary}")
            data.append('Content-Disposition: form-data; name="table_enable"')
            data.append('')
            data.append('true')
            data.append(f"--{boundary}")
            data.append('Content-Disposition: form-data; name="return_md"')
            data.append('')
            data.append('true')
            data.append(f"--{boundary}")
            data.append('Content-Disposition: form-data; name="files"; filename="1.pdf"')
            data.append('Content-Type: application/pdf')
            data.append('')
            data.append(pdf_content.decode('latin1'))
            data.append(f"--{boundary}--")
            data.append('')
            
            # 构建请求数据
            body = '\r\n'.join(data).encode('latin1')
            
            # 创建请求
            req = urllib.request.Request(test_url, data=body, method='POST')
            req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
            
            # 发送请求
            with urllib.request.urlopen(req, timeout=300.0) as response:  # 5分钟超时
                response_data = response.read().decode('utf-8')
                result = json.loads(response_data)
                
                print(f"✓ 请求成功，状态码: {response.status}")
                print(f"  响应: {json.dumps(result, indent=2)}")
                
                if result.get("status") == "completed" and result.get("results"):
                    print("✓ 解析成功！")
                elif result.get("success"):
                    print("✓ 解析成功！")
                else:
                    print("✗ 解析失败！")
                    
        except urllib.error.HTTPError as e:
            print(f"✗ HTTP错误: {e.code}")
            try:
                response_content = e.read().decode('utf-8')
                print(f"  响应内容: {response_content}")
            except:
                pass
        except urllib.error.URLError as e:
            print(f"✗ 连接错误: {e}")
        except Exception as e:
            print(f"✗ 其他错误: {e}")

if __name__ == "__main__":
    test_local_mineru()
