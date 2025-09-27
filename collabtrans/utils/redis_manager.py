# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import os
import sys
import subprocess
import time
import signal
import atexit
from pathlib import Path
from typing import Optional
import redis


class LocalRedisManager:
    """本地Redis管理器 - 自动启动和管理Redis服务"""
    
    def __init__(self):
        self.redis_process: Optional[subprocess.Popen] = None
        self.redis_client: Optional[redis.Redis] = None
        self.redis_port = 6379
        self.redis_host = "127.0.0.1"
        
        # 注册退出时清理函数
        atexit.register(self.cleanup)
        
        # 设置信号处理器
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._signal_handler)
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\nReceived signal {signum}, shutting down Redis service...")
        self.cleanup()
        sys.exit(0)
    
    def _get_redis_path(self) -> Optional[Path]:
        """获取Redis可执行文件路径"""
        if sys.platform == "win32":
            # Windows
            redis_dir = Path(__file__).parent.parent.parent / "3rdParty" / "windows" / "Redis-x64-3.0.504"
            redis_server = redis_dir / "redis-server.exe"
            if redis_server.exists():
                return redis_server
        elif sys.platform == "darwin":
            # macOS
            redis_server = Path("/usr/local/bin/redis-server")
            if redis_server.exists():
                return redis_server
            # 或者通过Homebrew安装的路径
            redis_server = Path("/opt/homebrew/bin/redis-server")
            if redis_server.exists():
                return redis_server
        elif sys.platform.startswith("linux"):
            # Linux
            redis_server = Path("/usr/bin/redis-server")
            if redis_server.exists():
                return redis_server
        
        return None
    
    def _is_redis_running(self) -> bool:
        """检查Redis是否已经在运行"""
        try:
            client = redis.Redis(host=self.redis_host, port=self.redis_port, socket_connect_timeout=1)
            client.ping()
            return True
        except:
            return False
    
    def start_redis(self) -> bool:
        """启动Redis服务"""
        # 如果Redis已经在运行，直接返回成功
        if self._is_redis_running():
            print("✅ Redis service is already running")
            return True
        
        # 获取Redis可执行文件路径
        redis_server_path = self._get_redis_path()
        if not redis_server_path:
            print("❌ Redis executable file not found")
            return False
        
        try:
            print(f"🚀 Starting local Redis service: {redis_server_path}")
            
            # 启动Redis服务
            if sys.platform == "win32":
                # Windows: 使用配置文件启动
                config_file = redis_server_path.parent / "redis.windows.conf"
                if config_file.exists():
                    self.redis_process = subprocess.Popen(
                        [str(redis_server_path), str(config_file)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    self.redis_process = subprocess.Popen(
                        [str(redis_server_path)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
            else:
                # Linux/macOS
                self.redis_process = subprocess.Popen(
                    [str(redis_server_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            # 等待Redis启动
            for i in range(10):  # 最多等待10秒
                time.sleep(1)
                if self._is_redis_running():
                    print("✅ Redis service started successfully")
                    return True
                print(f"⏳ Waiting for Redis to start... ({i+1}/10)")
            
            print("❌ Redis service startup timeout")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start Redis service: {e}")
            return False
    
    def get_redis_client(self) -> Optional[redis.Redis]:
        """获取Redis客户端"""
        if not self._is_redis_running():
            if not self.start_redis():
                return None
        
        if not self.redis_client:
            try:
                self.redis_client = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # 测试连接
                self.redis_client.ping()
            except Exception as e:
                print(f"❌ Failed to connect to Redis: {e}")
                return None
        
        return self.redis_client
    
    def cleanup(self):
        """清理资源"""
        if self.redis_process and self.redis_process.poll() is None:
            print("🛑 Shutting down Redis service...")
            try:
                if sys.platform == "win32":
                    # Windows: 发送终止信号
                    self.redis_process.terminate()
                else:
                    # Linux/macOS: 发送SIGTERM信号
                    self.redis_process.terminate()
                
                # 等待进程结束
                try:
                    self.redis_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 强制杀死进程
                    self.redis_process.kill()
                    self.redis_process.wait()
                
                print("✅ Redis service has been shut down")
            except Exception as e:
                print(f"⚠️  Error occurred while shutting down Redis service: {e}")
        
        self.redis_process = None
        self.redis_client = None


# 全局Redis管理器实例
_redis_manager: Optional[LocalRedisManager] = None


def get_redis_manager() -> LocalRedisManager:
    """获取全局Redis管理器实例"""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = LocalRedisManager()
    return _redis_manager


def get_redis_client() -> Optional[redis.Redis]:
    """获取Redis客户端（自动启动Redis服务）"""
    manager = get_redis_manager()
    return manager.get_redis_client()
