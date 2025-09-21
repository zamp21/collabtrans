#!/usr/bin/env python3
"""
Token Performance Testing Script
Tests the impact of different token settings on model response time and success rate
"""

import time
import requests
import json
from typing import Dict, List, Tuple

class TokenPerformanceTester:
    def __init__(self, config_file: str = "global_config.json"):
        """Initialize the tester"""
        self.config_file = config_file
        self.results = []
        
    def load_config(self) -> Dict:
        """Load configuration file"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load config file: {e}")
            return {}
    
    def generate_test_text(self, token_count: int) -> str:
        """Generate test text with specified token count"""
        # Rough estimation: 1 Chinese character ≈ 1 token
        # 1 English word ≈ 1.3 tokens
        chinese_chars = int(token_count * 0.8)  # 80% Chinese
        english_words = int(token_count * 0.2 / 1.3)  # 20% English
        
        chinese_text = "这是一个测试文档。" * (chinese_chars // 8)
        english_text = "This is a test document. " * english_words
        
        return chinese_text + english_text
    
    def test_platform_performance(self, platform_key: str, platform_config: Dict, 
                                test_tokens: List[int]) -> List[Dict]:
        """Test performance of a single platform"""
        platform_results = []
        
        print(f"\nTesting platform: {platform_config['name']}")
        print(f"Configured max_tokens: {platform_config['max_tokens']}")
        
        for token_count in test_tokens:
            print(f"\nTesting {token_count} tokens...")
            
            # Generate test text
            test_text = self.generate_test_text(token_count)
            
            # Test multiple times and take average
            times = []
            success_count = 0
            total_tests = 3
            
            for i in range(total_tests):
                try:
                    start_time = time.time()
                    
                    # This should call actual API, but for demo we simulate
                    # In actual use, need to call corresponding API based on platform config
                    response_time = self.simulate_api_call(token_count, platform_config['max_tokens'])
                    
                    end_time = time.time()
                    response_duration = end_time - start_time
                    
                    if response_time > 0:  # Simulate successful response
                        times.append(response_duration)
                        success_count += 1
                        print(f"  Test {i+1}: {response_duration:.2f}s")
                    else:
                        print(f"  Test {i+1}: Failed")
                        
                except Exception as e:
                    print(f"  Test {i+1}: Error - {e}")
            
            # Calculate statistics
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                success_rate = success_count / total_tests * 100
            else:
                avg_time = min_time = max_time = 0
                success_rate = 0
            
            result = {
                'platform': platform_key,
                'platform_name': platform_config['name'],
                'configured_max_tokens': platform_config['max_tokens'],
                'test_tokens': token_count,
                'avg_response_time': avg_time,
                'min_response_time': min_time,
                'max_response_time': max_time,
                'success_rate': success_rate,
                'total_tests': total_tests
            }
            
            platform_results.append(result)
            
            print(f"  Average response time: {avg_time:.2f}s")
            print(f"  Success rate: {success_rate:.1f}%")
        
        return platform_results
    
    def simulate_api_call(self, input_tokens: int, max_tokens: int) -> float:
        """Simulate API call (replace with real API call in actual use)"""
        # Simulate response time calculation
        base_time = 1.0  # Base response time
        
        # Input token impact
        input_factor = input_tokens / 1000  # Add 1 second per 1000 tokens
        
        # Output token impact (assume output is 1/4 of input)
        output_tokens = min(input_tokens // 4, max_tokens)
        output_factor = output_tokens / 1000
        
        # Total response time
        total_time = base_time + input_factor + output_factor
        
        # Simulate timeout (when token count is too large)
        if input_tokens > max_tokens * 0.8:  # Input exceeds 80% of max tokens
            return -1  # Simulate failure
        
        # Add some randomness
        import random
        total_time += random.uniform(-0.5, 0.5)
        
        return max(0.1, total_time)  # Minimum 0.1 seconds
    
    def run_performance_test(self):
        """Run performance test"""
        config = self.load_config()
        if not config or 'ai_platforms' not in config:
            print("Config file format error or not found")
            return
        
        # Test different token counts
        test_tokens = [1000, 4000, 8000, 16000, 32000, 64000, 128000]
        
        print("Starting Token performance test...")
        print("=" * 60)
        
        all_results = []
        
        for platform_key, platform_config in config['ai_platforms'].items():
            if platform_key == 'custom':  # Skip custom platform
                continue
                
            platform_results = self.test_platform_performance(
                platform_key, platform_config, test_tokens
            )
            all_results.extend(platform_results)
        
        # Save results
        self.save_results(all_results)
        
        # Show summary
        self.show_summary(all_results)
    
    def save_results(self, results: List[Dict]):
        """Save test results"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"token_performance_test_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\nTest results saved to: {filename}")
        except Exception as e:
            print(f"Failed to save results: {e}")
    
    def show_summary(self, results: List[Dict]):
        """Show test summary"""
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        
        # Group by platform
        platforms = {}
        for result in results:
            platform = result['platform_name']
            if platform not in platforms:
                platforms[platform] = []
            platforms[platform].append(result)
        
        for platform, platform_results in platforms.items():
            print(f"\n{platform}:")
            print("-" * 40)
            
            for result in platform_results:
                tokens = result['test_tokens']
                avg_time = result['avg_response_time']
                success_rate = result['success_rate']
                
                status = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 50 else "❌"
                
                print(f"  {tokens:>6} tokens: {avg_time:>6.2f}s {success_rate:>5.1f}% {status}")

def main():
    """Main function"""
    tester = TokenPerformanceTester()
    tester.run_performance_test()

if __name__ == "__main__":
    main()
