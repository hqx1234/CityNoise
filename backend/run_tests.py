#!/usr/bin/env python
"""
测试运行脚本
"""
import sys
import pytest

if __name__ == '__main__':
    # 运行所有测试
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # 默认参数
    default_args = [
        'tests/',
        '-v',  # 详细输出
        '--tb=short',  # 简短的错误追踪
        '--cov=app',  # 代码覆盖率
        '--cov-report=html',  # HTML覆盖率报告
        '--cov-report=term-missing',  # 终端显示缺失的覆盖率
    ]
    
    # 合并参数
    pytest_args = default_args + args
    
    exit_code = pytest.main(pytest_args)
    sys.exit(exit_code)

