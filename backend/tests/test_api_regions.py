"""
区域相关 API 测试
"""
import pytest
from app import MonitoringPoint, City, Sensor


class TestRegionsAPI:
    """区域API测试"""
    
    def test_get_regions(self, client, db_session, sample_monitoring_point):
        """测试获取区域列表"""
        response = client.get('/api/regions')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'regions' in data or 'points' in data or 'data' in data
    
    def test_get_region_devices(self, client, db_session, sample_monitoring_point, sample_sensor):
        """测试获取区域设备"""
        response = client.get(f'/api/regions/{sample_monitoring_point.PointID}/devices')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'devices' in data or 'sensors' in data or 'data' in data
    
    def test_get_region_devices_nonexistent(self, client):
        """测试获取不存在区域的设备"""
        response = client.get('/api/regions/99999/devices')
        
        # 应该返回空列表或404
        assert response.status_code in [200, 404]


class TestDevicesAPI:
    """设备API测试"""
    
    def test_get_devices(self, client, db_session, sample_sensor):
        """测试获取设备列表"""
        response = client.get('/api/devices')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'devices' in data or 'sensors' in data or 'data' in data
    
    def test_get_devices_with_filters(self, client, db_session, sample_sensor):
        """测试带过滤条件的设备查询"""
        response = client.get('/api/devices', query_string={
            'status': '在线',
            'point_id': sample_sensor.PointID
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

