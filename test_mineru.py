#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import urllib.request
import urllib.error
import time
import argparse
import json


def test_mineru_connection(base_url, api_key=None, api_prefix=''):
    """
    Test connection to MinerU server
    
    Args:
        base_url: MinerU server URL (e.g., http://localhost:8920)
        api_key: MinerU API key (optional, not needed for local deployment)
        api_prefix: API path prefix (e.g., api/v4)
    
    Returns:
        dict: Test result
    """
    print(f"Testing MinerU connection to: {base_url}")
    print(f"Using API key: {'Yes' if api_key else 'No (local deployment mode)'}")
    
    # Prepare headers
    headers = {
        'Content-Type': 'application/json'
    }
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    
    # Test API endpoint (new path structure)
    test_url = f'{base_url}/file/parse'
    test_data = {
        "files": [],
        "lang_list": ["ch"],
        "backend": "hybrid-auto-engine",
        "parse_method": "auto",
        "formula_enable": True,
        "table_enable": True,
        "return_md": True
    }
    
    try:
        # First check if this is a Gradio interface
        try:
            check_url = f'{base_url}/docs'
            check_req = urllib.request.Request(check_url, method='GET')
            with urllib.request.urlopen(check_req, timeout=10.0) as check_response:
                check_content = check_response.read().decode('utf-8')
                if '<!doctype html>' in check_content and 'Swagger UI' in check_content:
                    print("✓ Found FastAPI Swagger UI - MinerU API is running")
                    print("  API documentation available at: http://192.168.220.141:8920/docs")
                    return {
                        "success": True,
                        "message": "MinerU API is running correctly",
                        "batch_id": "test",
                        "upload_url": "test"
                    }
        except:
            pass
        
        # If we get here, let's try a simple GET request to the root
        try:
            check_url = f'{base_url}/'
            check_req = urllib.request.Request(check_url, method='GET')
            with urllib.request.urlopen(check_req, timeout=10.0) as check_response:
                print("✓ MinerU API is running")
                print(f"  Status code: {check_response.status}")
                return {
                    "success": True,
                    "message": "MinerU API is running correctly",
                    "batch_id": "test",
                    "upload_url": "test"
                }
        except:
            pass
        
        # If all else fails, try to access the openapi.json
        try:
            check_url = f'{base_url}/openapi.json'
            check_req = urllib.request.Request(check_url, method='GET')
            with urllib.request.urlopen(check_req, timeout=10.0) as check_response:
                print("✓ MinerU API is running")
                print("  API documentation available at: http://192.168.220.141:8920/docs")
                return {
                    "success": True,
                    "message": "MinerU API is running correctly",
                    "batch_id": "test",
                    "upload_url": "test"
                }
        except:
            pass
        
        # If we reach here, the server is not responding correctly
        print("✗ MinerU API is not responding correctly")
        return {
            "success": False,
            "message": "MinerU API is not responding correctly"
        }
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return {
            "success": False,
            "message": f"Unexpected error: {e}"
        }


def test_mineru_upload(base_url, upload_url, test_file_path, api_key=None, api_prefix=''):
    """
    Test uploading a file to MinerU
    
    Args:
        base_url: MinerU server URL
        upload_url: Upload URL obtained from connection test
        test_file_path: Path to test file
        api_key: MinerU API key (optional)
        api_prefix: API path prefix (e.g., api/v4)
    
    Returns:
        dict: Test result
    """
    print(f"Testing file upload to: {upload_url}")
    
    try:
        with open(test_file_path, 'rb') as f:
            file_content = f.read()
        
        print(f"File size: {len(file_content) / 1024:.2f} KB")
        
        # Create request for PUT method
        req = urllib.request.Request(upload_url, data=file_content, method='PUT')
        
        # Set timeout
        with urllib.request.urlopen(req, timeout=60.0) as response:
            # Check response status
            if response.status == 200:
                print("✓ File upload successful")
                return {
                    "success": True,
                    "message": "File upload successful"
                }
            else:
                print(f"✗ Upload failed with status: {response.status}")
                return {
                    "success": False,
                    "message": f"Upload failed with status: {response.status}"
                }
            
    except FileNotFoundError:
        print(f"✗ Test file not found: {test_file_path}")
        return {
            "success": False,
            "message": f"Test file not found: {test_file_path}"
        }
    except Exception as e:
        print(f"✗ Upload error: {e}")
        return {
            "success": False,
            "message": f"Upload error: {e}"
        }


def test_mineru_extract(base_url, batch_id, api_key=None, api_prefix=''):
    """
    Test extracting results from MinerU
    
    Args:
        base_url: MinerU server URL
        batch_id: Batch ID obtained from connection test
        api_key: MinerU API key (optional)
        api_prefix: API path prefix (e.g., api/v4)
    
    Returns:
        dict: Test result
    """
    print(f"Testing result extraction for batch: {batch_id}")
    
    # Prepare headers
    headers = {
        'Content-Type': 'application/json'
    }
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    
    extract_url = f'{base_url}/{api_prefix}/extract-results/batch/{batch_id}'
    
    try:
        # Poll for completion
        max_retries = 30  # Increased for local deployment which may be slower
        for i in range(max_retries):
            # Create request
            req = urllib.request.Request(extract_url, headers=headers, method='GET')
            
            # Set timeout
            with urllib.request.urlopen(req, timeout=30.0) as response:
                # Read response
                response_data = response.read().decode('utf-8')
                result = json.loads(response_data)
                
                fileinfo = result['data']['extract_result'][0]
                if fileinfo['state'] == 'done':
                    print("✓ Extraction completed successfully")
                    print(f"  Full ZIP URL: {fileinfo['full_zip_url']}")
                    print(f"  MD URL: {fileinfo['md_url']}")
                    return {
                        "success": True,
                        "message": "Extraction completed successfully",
                        "full_zip_url": fileinfo['full_zip_url'],
                        "md_url": fileinfo['md_url']
                    }
                elif fileinfo['state'] == 'failed':
                    print(f"✗ Extraction failed: {fileinfo.get('error', 'Unknown error')}")
                    return {
                        "success": False,
                        "message": f"Extraction failed: {fileinfo.get('error', 'Unknown error')}"
                    }
                else:
                    print(f"  Extraction in progress... ({i+1}/{max_retries})")
                    time.sleep(3)
            
            print("✗ Extraction timed out")
            print("  Tips: ")
            print("  1. Local deployment may take longer to process documents")
            print("  2. Check MinerU server logs for more information")
            return {
                "success": False,
                "message": "Extraction timed out"
            }
            
    except urllib.error.HTTPError as e:
        print(f"✗ HTTP error: {e.code} - {e.url}")
        try:
            response_content = e.read().decode('utf-8')[:200]
            print(f"  Response content: {response_content}...")
        except:
            pass
        return {
            "success": False,
            "message": f"HTTP error: {e.code} - {e.url}"
        }
    except urllib.error.URLError as e:
        print(f"✗ Connection error: {e}")
        print("  Possible issues: ")
        print("  1. MinerU server is not running")
        print("  2. Incorrect URL or port")
        print("  3. Network connectivity issues")
        return {
            "success": False,
            "message": f"Connection error: {e}"
        }
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return {
            "success": False,
            "message": f"Unexpected error: {e}"
        }

def main():
    parser = argparse.ArgumentParser(description='Test MinerU server connection and functionality')
    parser.add_argument('--url', default='http://localhost:8920', help='MinerU server URL (default: http://localhost:8920)')
    parser.add_argument('--api-key', help='MinerU API key (optional, not needed for local deployment)')
    parser.add_argument('--test-file', default='test/test_files/sample.pdf', help='Path to test file for upload testing (default: test/test_files/sample.pdf)')
    parser.add_argument('--full-test', action='store_true', help='Run full test including upload and extraction')
    parser.add_argument('--connection-only', action='store_true', help='Run only connection test')
    parser.add_argument('--api-prefix', default='', help='API path prefix (default: none)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MinerU Server Test Tool")
    print("=" * 60)
    
    # Run connection test
    connection_result = test_mineru_connection(args.url, args.api_key, args.api_prefix)
    
    if connection_result['success'] and not args.connection_only:
        if args.full_test:
            print("\nRunning full test...")
            print("=" * 60)
            # Run upload test
            upload_result = test_mineru_upload(args.url, connection_result['upload_url'], args.test_file, args.api_key, args.api_prefix)
            
            if upload_result['success']:
                # Run extraction test
                extract_result = test_mineru_extract(args.url, connection_result['batch_id'], args.api_key, args.api_prefix)
        
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)

if __name__ == '__main__':
    main()
