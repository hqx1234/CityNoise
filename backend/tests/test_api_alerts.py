"""
告警相关 API 测试
"""
import pytest
from datetime import datetime
from app import AlertInfo, RealtimeData


class TestAlertsAPI:
    """告警API测试"""
    
    def test_get_alerts(self, client, db_session, sample_realtime_data):
        """测试获取告警列表"""
        # 先创建一个告警
        alert = AlertInfo(
            AlertLevel='高',
            AlertType='噪音超标',
            AlertStatus='未处理',
            DataID=sample_realtime_data.DataID
        )
        db_session.add(alert)
        db_session.commit()
        
        response = client.get('/api/alerts')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'alerts' in data or 'data' in data
    
    def test_get_alerts_with_filters(self, client, db_session, sample_realtime_data):
        """测试带过滤条件的告警查询"""
        alert = AlertInfo(
            AlertLevel='高',
            AlertType='噪音超标',
            AlertStatus='未处理',
            DataID=sample_realtime_data.DataID
        )
        db_session.add(alert)
        db_session.commit()
        
        response = client.get('/api/alerts', query_string={
            'status': '未处理',
            'level': '高'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_update_alert(self, client, db_session, sample_realtime_data, sample_user):
        """测试更新告警"""
        alert = AlertInfo(
            AlertLevel='高',
            AlertType='噪音超标',
            AlertStatus='未处理',
            DataID=sample_realtime_data.DataID
        )
        db_session.add(alert)
        db_session.commit()
        
        response = client.put(f'/api/alerts/{alert.AlertID}', json={
            'status': '已处理',
            'process_notes': '已处理完成',
            'handler_id': sample_user.UserID
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        
        # 验证更新
        db_session.refresh(alert)
        assert alert.AlertStatus == '已处理'
        assert alert.ProcessNotes == '已处理完成'
    
    def test_update_nonexistent_alert(self, client):
        """测试更新不存在的告警"""
        response = client.put('/api/alerts/99999', json={
            'status': '已处理'
        })
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['status'] == 'error'

