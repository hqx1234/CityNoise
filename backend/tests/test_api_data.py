"""
数据相关 API 测试
"""
import pytest
from datetime import datetime, timedelta
from app import RealtimeData, Sensor, MonitoringPoint


class TestRealtimeDataAPI:
    """实时数据API测试"""
    
    def test_post_realtime_data(self, client, db_session, sample_sensor, sample_monitoring_point):
        """测试提交实时数据"""
        # 确保传感器关联到监测点
        sample_sensor.PointID = sample_monitoring_point.PointID
        db_session.commit()
        
        response = client.post('/api/realtime-data', json={
            'sensor_id': sample_sensor.SensorID,
            'noise_value': 65.5,
            'timestamp': datetime.now().isoformat(),
            'temperature': 25.0,
            'humidity': 60.0
        })
        
        assert response.status_code in [201, 200]  # 可能是200或201
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'data_id' in data or 'message' in data
    
    def test_get_realtime_data(self, client, db_session, sample_realtime_data):
        """测试获取实时数据"""
        response = client.get('/api/realtime-data')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'data' in data
        assert len(data['data']) > 0
    
    def test_get_realtime_data_with_filters(self, client, db_session, sample_realtime_data, sample_sensor):
        """测试带过滤条件的实时数据查询"""
        response = client.get('/api/realtime-data', query_string={
            'sensor_id': sample_sensor.SensorID,
            'limit': 10
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_get_realtime_data_pagination(self, client, db_session, sample_realtime_data):
        """测试实时数据分页"""
        response = client.get('/api/realtime-data', query_string={
            'page': 1,
            'per_page': 5
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'pagination' in data or 'total' in data


class TestNoiseDataAPI:
    """噪音数据API测试"""
    
    def test_get_noise_data(self, client, db_session, sample_realtime_data):
        """测试获取噪音数据"""
        response = client.get('/api/noise-data')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_post_noise_data(self, client, db_session, sample_sensor, sample_monitoring_point):
        """测试提交噪音数据"""
        response = client.post('/api/noise-data', json={
            'sensor_id': sample_sensor.SensorID,
            'point_id': sample_monitoring_point.PointID,
            'noise_value': 70.0,
            'timestamp': datetime.now().isoformat()
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_get_noise_data_statistics(self, client, db_session, sample_realtime_data, sample_monitoring_point):
        """测试获取噪音数据统计"""
        # 测试基本统计
        response = client.get('/api/noise-data/statistics')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'statistics' in data
        stats = data['statistics']
        assert 'avg_noise' in stats
        assert 'max_noise' in stats
        assert 'min_noise' in stats
        assert 'exceed_rate' in stats
        assert 'total_count' in stats
        assert 'exceed_count' in stats
        
        # 验证超标率计算（应该是0-100之间的值）
        assert 0 <= stats['exceed_rate'] <= 100
        
        # 测试按区域筛选
        response = client.get('/api/noise-data/statistics', query_string={
            'district': sample_monitoring_point.District
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'statistics' in data


class TestDashboardAPI:
    """仪表板API测试"""
    
    def test_get_dashboard_stats(self, client, db_session, sample_realtime_data):
        """测试获取仪表板统计"""
        response = client.get('/api/dashboard/stats')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        # 检查返回的统计字段
        assert 'total_sensors' in data or 'total_points' in data or 'data' in data


class TestMapAPI:
    """地图API测试"""
    
    def test_get_map_data(self, client, db_session, sample_monitoring_point, sample_sensor):
        """测试获取地图数据"""
        response = client.get('/api/map/data')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'points' in data or 'data' in data

