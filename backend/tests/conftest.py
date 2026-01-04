"""
Pytest 配置文件和测试固件
"""
import pytest
import os
import sys
import tempfile
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, Base, get_db_session, City, MonitoringPoint, Sensor, SystemUser, RealtimeData, AlertInfo


@pytest.fixture(scope='session')
def test_db():
    """创建测试数据库"""
    # 使用临时数据库文件
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    test_db_uri = f'sqlite:///{db_path}'
    
    engine = create_engine(test_db_uri, echo=False)
    Base.metadata.create_all(engine)
    
    yield engine, db_path
    
    # 清理
    os.close(db_fd)
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def db_session(test_db):
    """创建数据库会话"""
    engine, _ = test_db
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture
def client(test_db):
    """创建测试客户端"""
    engine, _ = test_db
    
    # 临时修改应用的数据库URI
    original_uri = app.config['SQLALCHEMY_DATABASE_URI']
    app.config['SQLALCHEMY_DATABASE_URI'] = str(engine.url)
    
    # 重新创建数据库表
    Base.metadata.create_all(engine)
    
    # 创建测试客户端
    with app.test_client() as client:
        yield client
    
    # 恢复原始配置
    app.config['SQLALCHEMY_DATABASE_URI'] = original_uri


@pytest.fixture
def sample_city(db_session):
    """创建示例城市"""
    city = City(
        CityName='测试市',
        Province='测试省'
    )
    db_session.add(city)
    db_session.commit()
    return city


@pytest.fixture
def sample_monitoring_point(db_session, sample_city):
    """创建示例监测点"""
    point = MonitoringPoint(
        PointName='测试监测点',
        PointCode='TEST001',
        Longitude=121.5,
        Latitude=31.2,
        Address='测试地址',
        District='测试区',
        PointType='住宅区',
        NoiseThresholdDay=60.0,
        NoiseThresholdNight=50.0,
        CityID=sample_city.CityID
    )
    db_session.add(point)
    db_session.commit()
    return point


@pytest.fixture
def sample_sensor(db_session, sample_monitoring_point):
    """创建示例传感器"""
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
    return sensor


@pytest.fixture
def sample_user(db_session):
    """创建示例用户"""
    user = SystemUser(
        Username='testuser',
        Email='test@example.com',
        UserRole='普通用户'
    )
    user.set_password('testpass123')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin_user(db_session):
    """创建管理员用户"""
    admin = SystemUser(
        Username='admin',
        Email='admin@example.com',
        UserRole='管理员'
    )
    admin.set_password('admin123')
    db_session.add(admin)
    db_session.commit()
    return admin


@pytest.fixture
def sample_realtime_data(db_session, sample_sensor, sample_monitoring_point):
    """创建示例实时数据"""
    data = RealtimeData(
        NoiseValue=65.5,
        Timestamp=datetime.now(),
        SensorID=sample_sensor.SensorID,
        PointID=sample_monitoring_point.PointID,
        DataQuality='良好',
        Temperature=25.0,
        Humidity=60.0
    )
    db_session.add(data)
    db_session.commit()
    return data


@pytest.fixture
def auth_headers(client, sample_user):
    """获取认证头（如果需要token认证）"""
    # 注意：当前API可能不使用token，而是使用session
    # 如果需要token认证，可以在这里实现
    response = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'testpass123'
    })
    if response.status_code == 200:
        # 如果API返回token，使用token
        data = response.get_json()
        token = data.get('token')
        if token:
            return {'Authorization': f'Bearer {token}'}
    return {}

