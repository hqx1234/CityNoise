"""
数据库初始化脚本 - 城市噪音污染监测管理平台
创建数据库表并初始化示例数据
"""
import os
from app import app, engine, Base, get_db_session
from app import City, MonitoringPoint, Sensor, RealtimeData, SystemUser
from datetime import datetime
from werkzeug.security import generate_password_hash

def init_database():
    """初始化数据库"""
    print("正在创建数据库表...")
    Base.metadata.create_all(engine)
    print("数据库表创建完成！")
    
    with get_db_session() as session:
        # 检查是否已有数据
        if session.query(City).count() > 0:
            print("数据库已有数据，跳过初始化")
            return
        
        print("正在初始化示例数据...")
        
        # 1. 创建城市
        cities_data = [
            {'name': '北京市', 'province': '北京市'},
            {'name': '上海市', 'province': '上海市'},
            {'name': '广州市', 'province': '广东省'},
            {'name': '深圳市', 'province': '广东省'}
        ]
        
        cities = {}
        for city_info in cities_data:
            city = City(CityName=city_info['name'], Province=city_info['province'])
            session.add(city)
            session.flush()
            cities[city_info['name']] = city
            print(f"创建城市: {city_info['name']}")
        
        # 2. 创建监测点
        points_data = [
            # 北京市
            {'name': '天安门广场监测点', 'code': 'BJ001', 'type': '商业区', 'lng': 116.3974, 'lat': 39.9093, 'city': '北京市'},
            {'name': '中关村科技园监测点', 'code': 'BJ002', 'type': '文教区', 'lng': 116.3168, 'lat': 39.9834, 'city': '北京市'},
            {'name': '朝阳区住宅区监测点', 'code': 'BJ003', 'type': '住宅区', 'lng': 116.4435, 'lat': 39.9219, 'city': '北京市'},
            {'name': '三环路交通监测点', 'code': 'BJ004', 'type': '交通干线', 'lng': 116.4074, 'lat': 39.9042, 'city': '北京市'},
            # 上海市
            {'name': '外滩监测点', 'code': 'SH001', 'type': '商业区', 'lng': 121.4879, 'lat': 31.2397, 'city': '上海市'},
            {'name': '浦东新区监测点', 'code': 'SH002', 'type': '混合区', 'lng': 121.5444, 'lat': 31.2304, 'city': '上海市'},
            {'name': '徐家汇住宅区监测点', 'code': 'SH003', 'type': '住宅区', 'lng': 121.4376, 'lat': 31.1923, 'city': '上海市'},
            {'name': '内环高架监测点', 'code': 'SH004', 'type': '交通干线', 'lng': 121.4737, 'lat': 31.2304, 'city': '上海市'},
        ]
        
        points = {}
        for point_info in points_data:
            city = cities.get(point_info['city'])
            if city:
                point = MonitoringPoint(
                    PointName=point_info['name'],
                    PointCode=point_info['code'],
                    PointType=point_info['type'],
                    Longitude=point_info['lng'],
                    Latitude=point_info['lat'],
                    CityID=city.CityID,
                    NoiseThresholdDay=60.0 if point_info['type'] != '文教区' else 55.0,
                    NoiseThresholdNight=50.0 if point_info['type'] != '文教区' else 45.0
                )
                session.add(point)
                session.flush()
                points[point_info['code']] = point
                print(f"创建监测点: {point_info['name']} ({point_info['code']})")
        
        # 3. 创建传感器
        sensors_data = [
            {'id': 'SN001', 'name': '天安门广场传感器1', 'point': 'BJ001', 'model': 'NS-2000', 'status': '在线'},
            {'id': 'SN002', 'name': '中关村传感器1', 'point': 'BJ002', 'model': 'NS-2000', 'status': '在线'},
            {'id': 'SN003', 'name': '朝阳住宅区传感器1', 'point': 'BJ003', 'model': 'NS-1500', 'status': '在线'},
            {'id': 'SN004', 'name': '三环路传感器1', 'point': 'BJ004', 'model': 'NS-2000', 'status': '在线'},
            {'id': 'SN005', 'name': '外滩传感器1', 'point': 'SH001', 'model': 'NS-2000', 'status': '在线'},
            {'id': 'SN006', 'name': '浦东新区传感器1', 'point': 'SH002', 'model': 'NS-2000', 'status': '在线'},
            {'id': 'SN007', 'name': '徐家汇传感器1', 'point': 'SH003', 'model': 'NS-1500', 'status': '在线'},
            {'id': 'SN008', 'name': '内环高架传感器1', 'point': 'SH004', 'model': 'NS-2000', 'status': '在线'},
        ]
        
        for sensor_info in sensors_data:
            point = points.get(sensor_info['point'])
            if point:
                sensor = Sensor(
                    SensorID=sensor_info['id'],
                    SensorName=sensor_info['name'],
                    SensorModel=sensor_info['model'],
                    Status=sensor_info['status'],
                    BatteryLevel=85,
                    SignalStrength=90,
                    SamplingRate=1,
                    PointID=point.PointID
                )
                session.add(sensor)
                print(f"创建传感器: {sensor_info['name']} ({sensor_info['id']})")
        
        # 4. 创建管理员账户
        admin = SystemUser(
            Username='admin',
            UserRole='管理员',
            Email='admin@noise-monitoring.com'
        )
        admin.set_password('admin123')
        session.add(admin)
        print("创建管理员账户: admin / admin123")
        
        print("\n数据库初始化完成！")
        print("=" * 50)
        print("系统信息:")
        print(f"- 城市数量: {session.query(City).count()}")
        print(f"- 监测点数量: {session.query(MonitoringPoint).count()}")
        print(f"- 传感器数量: {session.query(Sensor).count()}")
        print(f"- 用户数量: {session.query(SystemUser).count()}")
        print("=" * 50)
        print("\n提示:")
        print("1. 启动实时数据采集: POST /api/realtime/generate")
        print("2. 查看实时数据流: GET /api/realtime/stream")
        print("3. 登录系统: admin / admin123")

if __name__ == '__main__':
    with app.app_context():
        init_database()

