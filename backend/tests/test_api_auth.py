"""
认证相关 API 测试
"""
import pytest
import json
from app import SystemUser


class TestAuthAPI:
    """认证API测试"""
    
    def test_register_success(self, client, db_session):
        """测试成功注册"""
        response = client.post('/api/auth/register', json={
            'username': 'newuser',
            'password': 'password123',
            'email': 'newuser@example.com',
            'role': '普通用户'
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'user_id' in data
    
    def test_register_duplicate_username(self, client, db_session, sample_user):
        """测试重复用户名注册"""
        response = client.post('/api/auth/register', json={
            'username': 'testuser',  # 已存在的用户名
            'password': 'password123',
            'email': 'different@example.com',
            'role': '普通用户'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
        assert '用户名已存在' in data['message']
    
    def test_register_missing_fields(self, client):
        """测试缺少必填字段"""
        response = client.post('/api/auth/register', json={
            'username': 'newuser',
            # 缺少 password, email, role
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
    
    def test_login_success(self, client, db_session, sample_user):
        """测试成功登录"""
        response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'user' in data
        assert data['user']['username'] == 'testuser'
    
    def test_login_wrong_password(self, client, db_session, sample_user):
        """测试错误密码登录"""
        response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['status'] == 'error'
    
    def test_login_nonexistent_user(self, client):
        """测试不存在的用户登录"""
        response = client.post('/api/auth/login', json={
            'username': 'nonexistent',
            'password': 'password123'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['status'] == 'error'
    
    def test_login_missing_fields(self, client):
        """测试缺少登录字段"""
        response = client.post('/api/auth/login', json={
            'username': 'testuser'
            # 缺少 password
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'

