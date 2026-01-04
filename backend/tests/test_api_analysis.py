"""
分析相关 API 测试
"""
import pytest
from datetime import datetime, timedelta
from app import RealtimeData, MonitoringPoint, Sensor


class TestAnalysisAPI:
    """分析API测试"""
    
    def test_get_trend_analysis(self, client, db_session, sample_monitoring_point, sample_sensor):
        """测试获取趋势分析"""
        # 创建一些历史数据
        for i in range(5):
            data = RealtimeData(
                NoiseValue=60.0 + i,
                Timestamp=datetime.now() - timedelta(days=i),
                SensorID=sample_sensor.SensorID,
                PointID=sample_monitoring_point.PointID
            )
            db_session.add(data)
        db_session.commit()
        
        response = client.get('/api/analysis/trend', query_string={
            'point_id': sample_monitoring_point.PointID,
            'days': 7
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_get_compare_analysis(self, client, db_session, sample_monitoring_point):
        """测试获取对比分析"""
        response = client.get('/api/analysis/compare', query_string={
            'point_ids': f'{sample_monitoring_point.PointID}',
            'start_date': (datetime.now() - timedelta(days=7)).isoformat(),
            'end_date': datetime.now().isoformat()
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_get_hourly_pattern(self, client, db_session, sample_monitoring_point, sample_sensor):
        """测试获取小时模式分析"""
        # 创建不同小时的数据
        for hour in range(0, 24, 2):
            data = RealtimeData(
                NoiseValue=55.0 + (hour % 10),
                Timestamp=datetime.now().replace(hour=hour, minute=0),
                SensorID=sample_sensor.SensorID,
                PointID=sample_monitoring_point.PointID
            )
            db_session.add(data)
        db_session.commit()
        
        response = client.get('/api/analysis/hourly-pattern', query_string={
            'point_id': sample_monitoring_point.PointID
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_get_correlation_analysis(self, client, db_session, sample_monitoring_point):
        """测试获取相关性分析"""
        response = client.get('/api/analysis/correlation', query_string={
            'point_id': sample_monitoring_point.PointID
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'

