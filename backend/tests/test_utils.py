"""
工具函数测试
"""
import pytest
from app import allowed_file, get_pagination_params
from flask import Flask, request


class TestAllowedFile:
    """文件类型检查测试"""
    
    def test_allowed_file_extensions(self):
        """测试允许的文件扩展名"""
        assert allowed_file('test.png') == True
        assert allowed_file('test.jpg') == True
        assert allowed_file('test.jpeg') == True
        assert allowed_file('test.pdf') == True
        assert allowed_file('test.csv') == True
        assert allowed_file('test.xlsx') == True
    
    def test_disallowed_file_extensions(self):
        """测试不允许的文件扩展名"""
        assert allowed_file('test.exe') == False
        assert allowed_file('test.txt') == False
        assert allowed_file('test.doc') == False
    
    def test_no_extension(self):
        """测试无扩展名文件"""
        assert allowed_file('test') == False
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        assert allowed_file('test.PNG') == True
        assert allowed_file('test.JPG') == True
        assert allowed_file('test.PDF') == True

