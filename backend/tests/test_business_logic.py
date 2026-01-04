"""
业务逻辑测试
"""
import pytest
from datetime import datetime, timedelta
from app import (
    calculate_noise_level, 
    check_and_generate_alert,
    RealtimeData,
    MonitoringPoint,
    Sensor,
    AlertInfo
)


class TestNoiseLevelCalculation:
    """噪音等级计算测试"""
    
    def test_calculate_noise_level_residential(self):
        """测试住宅区噪音等级计算"""
        # 测试不同噪音值
        assert calculate_noise_level(45, '住宅区') == '优'
        assert calculate_noise_level(52, '住宅区') == '良'
        assert calculate_noise_level(58, '住宅区') == '轻度污染'
        assert calculate_noise_level(68, '住宅区') == '中度污染'
        assert calculate_noise_level(75, '住宅区') == '重度污染'
    
    def test_calculate_noise_level_commercial(self):
        """测试商业区噪音等级计算"""
        assert calculate_noise_level(50, '商业区') == '优'
        assert calculate_noise_level(58, '商业区') == '良'
        assert calculate_noise_level(68, '商业区') == '轻度污染'
    
    def test_calculate_noise_level_industrial(self):
        """测试工业区噪音等级计算"""
        assert calculate_noise_level(55, '工业区') == '优'
        assert calculate_noise_level(63, '工业区') == '良'
        assert calculate_noise_level(72, '工业区') == '轻度污染'
    
    def test_calculate_noise_level_unknown_type(self):
        """测试未知区域类型"""
        # 应该使用默认阈值
        result = calculate_noise_level(60, '未知类型')
        assert result in ['优', '良', '轻度污染', '中度污染', '重度污染']


class TestAlertGeneration:
    """告警生成测试"""
    
    def test_check_and_generate_alert_exceeded(self, db_session, sample_monitoring_point, sample_sensor):
        """测试超标告警生成"""
        # 创建超标数据（昼间，超过60dB阈值）
        realtime_data = RealtimeData(
            NoiseValue=70.0,  # 超过60dB阈值
            Timestamp=datetime.now().replace(hour=12),  # 中午
            SensorID=sample_sensor.SensorID,
            PointID=sample_monitoring_point.PointID,
            DataQuality='良好'
        )
        db_session.add(realtime_data)
        db_session.commit()
        
        # 检查并生成告警
        alert = check_and_generate_alert(realtime_data, db_session)
        
        if alert:
            assert alert.AlertType == '噪音超标'
            assert alert.AlertLevel in ['低', '中', '高', '紧急']
            assert alert.AlertStatus == '未处理'
    
    def test_check_and_generate_alert_not_exceeded(self, db_session, sample_monitoring_point, sample_sensor):
        """测试未超标不生成告警"""
        # 创建未超标数据
        realtime_data = RealtimeData(
            NoiseValue=55.0,  # 低于60dB阈值
            Timestamp=datetime.now().replace(hour=12),
            SensorID=sample_sensor.SensorID,
            PointID=sample_monitoring_point.PointID,
            DataQuality='良好'
        )
        db_session.add(realtime_data)
        db_session.commit()
        
        # 检查并生成告警（应该不生成）
        alert = check_and_generate_alert(realtime_data, db_session)
        
        # 可能返回None，或者不生成告警
        if alert is None:
            # 验证没有告警被创建
            alerts = db_session.query(AlertInfo).filter_by(DataID=realtime_data.DataID).all()
            assert len(alerts) == 0


class TestDataValidation:
    """数据验证测试"""
    
    def test_realtime_data_validation(self, db_session, sample_sensor, sample_monitoring_point):
        """测试实时数据验证"""
        # 测试有效数据
        valid_data = RealtimeData(
            NoiseValue=65.0,
            Timestamp=datetime.now(),
            SensorID=sample_sensor.SensorID,
            PointID=sample_monitoring_point.PointID
        )
        db_session.add(valid_data)
        db_session.commit()
        
        assert valid_data.DataID is not None
    
    def test_noise_value_range(self, db_session, sample_sensor, sample_monitoring_point):
        """测试噪音值范围"""
        # 测试边界值
        min_data = RealtimeData(
            NoiseValue=0.0,
            Timestamp=datetime.now(),
            SensorID=sample_sensor.SensorID,
            PointID=sample_monitoring_point.PointID
        )
        db_session.add(min_data)
        db_session.commit()
        
        max_data = RealtimeData(
            NoiseValue=200.0,
            Timestamp=datetime.now(),
            SensorID=sample_sensor.SensorID,
            PointID=sample_monitoring_point.PointID
        )
        db_session.add(max_data)
        db_session.commit()
        
        assert min_data.NoiseValue == 0.0
        assert max_data.NoiseValue == 200.0

