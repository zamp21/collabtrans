#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

"""
日志配置管理工具
用于修改系统日志级别和其他日志相关设置
"""

import sys
import json
import argparse
from pathlib import Path
from collabtrans.config.global_config import get_global_config, save_global_config


def get_log_levels():
    """获取可用的日志级别"""
    return ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def show_current_config():
    """显示当前日志配置"""
    config = get_global_config()
    logging_config = config.logging
    
    print("当前日志配置:")
    print(f"  级别: {logging_config.level}")
    print(f"  控制台输出: {'启用' if logging_config.console_enabled else '禁用'}")
    print(f"  文件输出: {'启用' if logging_config.file_enabled else '禁用'}")
    print(f"  最大文件大小: {logging_config.max_file_size_mb} MB")
    print(f"  备份文件数量: {logging_config.backup_count}")


def set_log_level(level: str):
    """设置日志级别"""
    if level.upper() not in get_log_levels():
        print(f"错误: 无效的日志级别 '{level}'")
        print(f"可用的级别: {', '.join(get_log_levels())}")
        return False
    
    config = get_global_config()
    config.logging.level = level.upper()
    
    if save_global_config():
        print(f"✅ 日志级别已设置为: {level.upper()}")
        print("💡 重启服务后生效")
        return True
    else:
        print("❌ 保存配置失败")
        return False


def toggle_console_output(enabled: bool):
    """切换控制台输出"""
    config = get_global_config()
    config.logging.console_enabled = enabled
    
    if save_global_config():
        status = "启用" if enabled else "禁用"
        print(f"✅ 控制台输出已{status}")
        print("💡 重启服务后生效")
        return True
    else:
        print("❌ 保存配置失败")
        return False


def toggle_file_output(enabled: bool):
    """切换文件输出"""
    config = get_global_config()
    config.logging.file_enabled = enabled
    
    if save_global_config():
        status = "启用" if enabled else "禁用"
        print(f"✅ 文件输出已{status}")
        print("💡 重启服务后生效")
        return True
    else:
        print("❌ 保存配置失败")
        return False


def set_file_size(max_size_mb: int):
    """设置最大文件大小"""
    if max_size_mb <= 0:
        print("错误: 文件大小必须大于0")
        return False
    
    config = get_global_config()
    config.logging.max_file_size_mb = max_size_mb
    
    if save_global_config():
        print(f"✅ 最大文件大小已设置为: {max_size_mb} MB")
        print("💡 重启服务后生效")
        return True
    else:
        print("❌ 保存配置失败")
        return False


def set_backup_count(count: int):
    """设置备份文件数量"""
    if count < 0:
        print("错误: 备份数量不能为负数")
        return False
    
    config = get_global_config()
    config.logging.backup_count = count
    
    if save_global_config():
        print(f"✅ 备份文件数量已设置为: {count}")
        print("💡 重启服务后生效")
        return True
    else:
        print("❌ 保存配置失败")
        return False


def main():
    parser = argparse.ArgumentParser(description="日志配置管理工具")
    parser.add_argument("--show", action="store_true", help="显示当前配置")
    parser.add_argument("--level", choices=get_log_levels(), help="设置日志级别")
    parser.add_argument("--console", choices=["on", "off"], help="启用/禁用控制台输出")
    parser.add_argument("--file", choices=["on", "off"], help="启用/禁用文件输出")
    parser.add_argument("--max-size", type=int, help="设置最大文件大小(MB)")
    parser.add_argument("--backup-count", type=int, help="设置备份文件数量")
    
    args = parser.parse_args()
    
    # 如果没有参数，显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        print("\n示例:")
        print("  python manage_logging.py --show                    # 显示当前配置")
        print("  python manage_logging.py --level DEBUG             # 设置为DEBUG级别")
        print("  python manage_logging.py --level INFO              # 设置为INFO级别")
        print("  python manage_logging.py --console off             # 禁用控制台输出")
        print("  python manage_logging.py --file on                 # 启用文件输出")
        print("  python manage_logging.py --max-size 20             # 设置最大文件大小为20MB")
        print("  python manage_logging.py --backup-count 10         # 设置备份文件数量为10")
        return
    
    success = True
    
    if args.show:
        show_current_config()
    
    if args.level:
        success &= set_log_level(args.level)
    
    if args.console:
        success &= toggle_console_output(args.console == "on")
    
    if args.file:
        success &= toggle_file_output(args.file == "on")
    
    if args.max_size is not None:
        success &= set_file_size(args.max_size)
    
    if args.backup_count is not None:
        success &= set_backup_count(args.backup_count)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
