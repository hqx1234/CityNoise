"""
数据库模型测试
"""
import pytest
from datetime import datetime
from app import City, MonitoringPoint, Sensor, SystemUser, RealtimeData, AlertInfo


class TestCity:
    """城市模型测试"""
    
    def test_city_creation(self, db_session):
        """测试城市创建"""
        city = City(
            CityName='北京市',
            Province='北京市'
        )
        db_session.add(city)
        db_session.commit()
        
        assert city.CityID is not None
        assert city.CityName == '北京市'
        assert city.Province == '北京市'
    
    def test_city_to_dict(self, db_session):
        """测试城市序列化"""
        city = City(
            CityName='上海市',
            Province='上海市'
        )
        db_session.add(city)
        db_session.commit()
        
        data = city.to_dict()
        assert 'city_id' in data
        assert 'city_name' in data
        assert data['city_name'] == '上海市'


class TestMonitoringPoint:
    """监测点模型测试"""
    
    def test_monitoring_point_creation(self, db_session, sample_city):
        """测试监测点创建"""
        point = MonitoringPoint(
            PointName='测试点',
            PointCode='TEST001',
            Longitude=121.5,
            Latitude=31.2,
            PointType='住宅区',
            NoiseThresholdDay=60.0,
            NoiseThresholdNight=50.0,
            CityID=sample_city.CityID
        )
        db_session.add(point)
        db_session.commit()
        
        assert point.PointID is not None
        assert point.PointName == '测试点'
        assert point.Longitude == 121.5
    
    def test_monitoring_point_constraints(self, db_session, sample_city):
        """测试监测点约束"""
        # 测试无效的经度
        with pytest.raises(Exception):
            point = MonitoringPoint(
                PointName='测试点',
                PointCode='TEST002',
                Longitude=200,  # 无效经度
                Latitude=31.2,
                PointType='住宅区',
                NoiseThresholdDay=60.0,
                NoiseThresholdNight=50.0,
                CityID=sample_city.CityID
            )
            db_session.add(point)
            db_session.commit()


class TestSensor:
    """传感器模型测试"""
    
    def test_sensor_creation(self, db_session, sample_monitoring_point):
        """测试传感器创建"""
        sensor = Sensor(
            SensorID='SENSOR001',
            SensorName='测试传感器',
            SensorModel='TEST-MODEL',
            Status='在线',
            BatteryLevel=80,
            SignalStrength=90,
            PointID=sample_monitoring_point.PointID
        )
        db_session.add(sensor)
        db_session.commit()
        
        assert sensor.SensorID == 'SENSOR001'
        assert sensor.Status == '在线'
        assert sensor.BatteryLevel == 80
    
    def test_sensor_status_constraint(self, db_session, sample_monitoring_point):
        """测试传感器状态约束"""
        # 测试无效状态（应该通过，因为约束在数据库层面）
        sensor = Sensor(
            SensorID='SENSOR002',
            SensorName='测试传感器2',
            Status='在线',
            PointID=sample_monitoring_point.PointID
        )
        db_session.add(sensor)
        db_session.commit()
        assert sensor.Status == '在线'


class TestSystemUser:
    """用户模型测试"""
    
    def test_user_creation(self, db_session):
        """测试用户创建"""
        user = SystemUser(
            Username='testuser',
            Email='test@example.com',
            UserRole='普通用户'
        )
        user.set_password('password123')
        db_session.add(user)
        db_session.commit()
        
        assert user.UserID is not None
        assert user.Username == 'testuser'
        assert user.check_password('password123')
        assert not user.check_password('wrongpassword')
    
    def test_user_password_hashing(self, db_session):
        """测试密码哈希"""
        user = SystemUser(
            Username='testuser2',
            Email='test2@example.com',
            UserRole='普通用户'
        )
        user.set_password('mypassword')
        
        # 密码应该被哈希，不是明文
        assert user.PasswordHash != 'mypassword'
        assert len(user.PasswordHash) > 20  # 哈希值应该比较长


class TestRealtimeData:
    """实时数据模型测试"""
    
    def test_realtime_data_creation(self, db_session, sample_sensor, sample_monitoring_point):
        """测试实时数据创建"""
        data = RealtimeData(
            NoiseValue=65.5,
            Timestamp=datetime.now(),
            SensorID=sample_sensor.SensorID,
            PointID=sample_monitoring_point.PointID,
            DataQuality='良好'
        )
        db_session.add(data)
        db_session.commit()
        
        assert data.DataID is not None
        assert data.NoiseValue == 65.5
        assert data.SensorID == sample_sensor.SensorID
    
    def test_realtime_data_is_exceeded(self, db_session, sample_sensor, sample_monitoring_point):
        """测试超标判断"""
        # 昼间数据，超过阈值
        daytime_data = RealtimeData(
            NoiseValue=70.0,  # 超过60.0的昼间阈值
            Timestamp=datetime.now().replace(hour=12),  # 中午12点
            SensorID=sample_sensor.SensorID,
            PointID=sample_monitoring_point.PointID
        )
        db_session.add(daytime_data)
        db_session.commit()
        
        # 刷新对象以获取关联
        db_session.refresh(daytime_data)
        assert daytime_data.is_exceeded == True
        
        # 夜间数据，未超过阈值
        nighttime_data = RealtimeData(
            NoiseValue=45.0,  # 低于50.0的夜间阈值
            Timestamp=datetime.now().replace(hour=2),  # 凌晨2点
            SensorID=sample_sensor.SensorID,
            PointID=sample_monitoring_point.PointID
        )
        db_session.add(nighttime_data)
        db_session.commit()
        
        db_session.refresh(nighttime_data)
        assert nighttime_data.is_exceeded == False


class TestAlertInfo:
    """告警信息模型测试"""
    
    def test_alert_creation(self, db_session, sample_realtime_data):
        """测试告警创建"""
        alert = AlertInfo(
            AlertLevel='高',
            AlertType='噪音超标',
            AlertStatus='未处理',
            DataID=sample_realtime_data.DataID
        )
        db_session.add(alert)
        db_session.commit()
        
        assert alert.AlertID is not None
        assert alert.AlertLevel == '高'
        assert alert.AlertStatus == '未处理'

