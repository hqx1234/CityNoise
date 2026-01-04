from flask import Flask, request, jsonify, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_caching import Cache
from datetime import datetime, timedelta
from contextlib import contextmanager
from functools import wraps
from time import time, sleep
import hashlib
import os
import json
import logging
import threading
from logging.handlers import RotatingFileHandler
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, CheckConstraint, func, case, desc
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, joinedload
from sqlalchemy.ext.hybrid import hybrid_property
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config
from smart_noise_simulator import SmartNoiseSimulator

app = Flask(__name__)
app.config.from_object(Config)

CORS(app, resources={r"/*": {"origins": "*"}})

# 初始化缓存
cache = Cache(app, config={
    'CACHE_TYPE': Config.CACHE_TYPE,
    'CACHE_DEFAULT_TIMEOUT': Config.CACHE_DEFAULT_TIMEOUT
})

# 创建数据库引擎
engine = create_engine(
    app.config['SQLALCHEMY_DATABASE_URI'],
    echo=False
)
Base = declarative_base()
Session = sessionmaker(bind=engine)


@contextmanager
def get_db_session():
    """安全的数据库会话管理（上下文管理器）"""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# ==================== 装饰器和辅助函数 ====================

def validate_json(*expected_args):
    """JSON参数验证装饰器"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            data = request.get_json()
            if not data:
                return jsonify({'status': 'error', 'message': '缺少JSON数据'}), 400
            
            for arg in expected_args:
                if arg not in data:
                    return jsonify({'status': 'error', 'message': f'缺少参数: {arg}'}), 400
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


def log_request_time(f):
    """记录请求时间装饰器"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        start_time = time()
        try:
            response = f(*args, **kwargs)
            end_time = time()
            app.logger.info(f'请求 {request.path} 耗时: {end_time - start_time:.3f}秒')
            return response
        except Exception as e:
            end_time = time()
            app.logger.error(f'请求 {request.path} 失败，耗时: {end_time - start_time:.3f}秒，错误: {str(e)}')
            raise
    return wrapper


def get_pagination_params():
    """获取分页参数"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    return max(page, 1), min(max(per_page, 1), 100)  # 限制每页最多100条


def setup_logging(app):
    """配置日志"""
    if not os.path.exists(Config.LOG_DIR):
        os.makedirs(Config.LOG_DIR)
    
    # 文件处理器
    file_handler = RotatingFileHandler(
        os.path.join(Config.LOG_DIR, Config.LOG_FILE),
        maxBytes=Config.LOG_MAX_BYTES,
        backupCount=Config.LOG_BACKUP_COUNT
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Noise Monitoring系统启动')


# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'status': 'error', 'message': '资源不存在'}), 404


@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'服务器内部错误: {error}')
    return jsonify({'status': 'error', 'message': '服务器内部错误'}), 500


@app.errorhandler(400)
def bad_request_error(error):
    return jsonify({'status': 'error', 'message': '请求参数错误'}), 400

# ==================== 数据库模型定义 ====================

class City(Base):
    """城市表"""
    __tablename__ = 'city'
    
    CityID = Column(Integer, primary_key=True, autoincrement=True)
    CityName = Column(String(50), nullable=False, unique=True)
    Province = Column(String(50))  # 省份
    CreatedAt = Column(DateTime, default=datetime.now)
    
    # 关系
    monitoring_points = relationship('MonitoringPoint', back_populates='city', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'city_id': self.CityID,
            'city_name': self.CityName,
            'province': self.Province,
            'created_at': self.CreatedAt.isoformat() if self.CreatedAt else None
        }


class MonitoringPoint(Base):
    """监测点表 - 城市中具体的监测位置"""
    __tablename__ = 'monitoring_point'
    
    PointID = Column(Integer, primary_key=True, autoincrement=True)
    PointName = Column(String(100), nullable=False)  # 监测点名称，如"市中心广场"
    PointCode = Column(String(50), nullable=False, unique=True)  # 监测点编码，如"BJ001"
    Longitude = Column(Float, nullable=False)  # 经度
    Latitude = Column(Float, nullable=False)  # 纬度
    Address = Column(String(200))  # 详细地址
    District = Column(String(50))  # 区/县
    Street = Column(String(100))  # 街道
    Community = Column(String(100))  # 社区
    PointType = Column(String(20), nullable=False)  # 监测点类型
    NoiseThresholdDay = Column(Float, nullable=False, default=60.0)  # 昼间阈值（分贝）
    NoiseThresholdNight = Column(Float, nullable=False, default=50.0)  # 夜间阈值（分贝）
    CityID = Column(Integer, ForeignKey('city.CityID'), nullable=False)
    CreatedAt = Column(DateTime, default=datetime.now)
    UpdatedAt = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    city = relationship('City', back_populates='monitoring_points')
    sensors = relationship('Sensor', back_populates='monitoring_point', cascade='all, delete-orphan')
    realtime_data = relationship('RealtimeData', back_populates='monitoring_point', cascade='all, delete-orphan')
    
    # 检查约束
    __table_args__ = (
        CheckConstraint("PointType IN ('住宅区', '商业区', '工业区', '文教区', '混合区', '交通干线', '公园绿地', '其他')", name='chk_point_type'),
        CheckConstraint('NoiseThresholdDay >= 0 AND NoiseThresholdDay <= 120', name='chk_noise_threshold_day'),
        CheckConstraint('NoiseThresholdNight >= 0 AND NoiseThresholdNight <= 120', name='chk_noise_threshold_night'),
        CheckConstraint('Longitude >= -180 AND Longitude <= 180', name='chk_longitude'),
        CheckConstraint('Latitude >= -90 AND Latitude <= 90', name='chk_latitude'),
    )
    
    def to_dict(self):
        return {
            'point_id': self.PointID,
            'point_name': self.PointName,
            'point_code': self.PointCode,
            'location': {
                'longitude': self.Longitude,
                'latitude': self.Latitude,
                'address': self.Address,
                'district': self.District,
                'street': self.Street,
                'community': self.Community
            },
            'point_type': self.PointType,
            'threshold_day': self.NoiseThresholdDay,
            'threshold_night': self.NoiseThresholdNight,
            'city_id': self.CityID,
            'city_name': self.city.CityName if self.city else None,
            'created_at': self.CreatedAt.isoformat() if self.CreatedAt else None,
            'updated_at': self.UpdatedAt.isoformat() if self.UpdatedAt else None
        }


class Sensor(Base):
    """传感器表 - 分布在城市各处的噪音传感器"""
    __tablename__ = 'sensor'
    
    SensorID = Column(String(50), primary_key=True)  # 传感器唯一标识，如"SN001"
    SensorName = Column(String(100), nullable=False)  # 传感器名称
    SensorModel = Column(String(50))  # 传感器型号
    SensorType = Column(String(20), default='噪音传感器')  # 传感器类型
    Manufacturer = Column(String(100))  # 制造商
    InstallDate = Column(DateTime, default=datetime.now)  # 安装日期
    LastMaintenanceDate = Column(DateTime)  # 最后维护日期
    NextMaintenanceDate = Column(DateTime)  # 下次维护日期
    Status = Column(String(20), default='在线')  # 传感器状态
    BatteryLevel = Column(Integer)  # 电池电量（0-100）
    SignalStrength = Column(Integer)  # 信号强度（0-100）
    SamplingRate = Column(Integer, default=1)  # 采样频率（次/秒）
    MeasurementRange = Column(String(50), default='30-130dB')  # 测量范围
    Accuracy = Column(String(20), default='±1.5dB')  # 精度
    PointID = Column(Integer, ForeignKey('monitoring_point.PointID'), nullable=False)
    CreatedAt = Column(DateTime, default=datetime.now)
    UpdatedAt = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    monitoring_point = relationship('MonitoringPoint', back_populates='sensors')
    realtime_data = relationship('RealtimeData', back_populates='sensor', cascade='all, delete-orphan')
    
    # 检查约束
    __table_args__ = (
        CheckConstraint("Status IN ('在线', '离线', '故障', '维护中', '校准中')", name='chk_sensor_status'),
        CheckConstraint('BatteryLevel >= 0 AND BatteryLevel <= 100', name='chk_battery_level'),
        CheckConstraint('SignalStrength >= 0 AND SignalStrength <= 100', name='chk_signal_strength'),
        CheckConstraint('SamplingRate > 0 AND SamplingRate <= 100', name='chk_sampling_rate'),
    )
    
    def to_dict(self):
        return {
            'sensor_id': self.SensorID,
            'device_id': self.SensorID,  # 添加device_id字段，兼容前端
            'sensor_name': self.SensorName,
            'device_model': self.SensorModel,  # 添加device_model字段，兼容前端
            'device_status': self.Status,  # 添加device_status字段，兼容前端
            'sensor_model': self.SensorModel,
            'sensor_type': self.SensorType,
            'manufacturer': self.Manufacturer,
            'status': self.Status,
            'battery_level': self.BatteryLevel,
            'signal_strength': self.SignalStrength,
            'sampling_rate': self.SamplingRate,
            'measurement_range': self.MeasurementRange,
            'accuracy': self.Accuracy,
            'point_id': self.PointID,
            'point_name': self.monitoring_point.PointName if self.monitoring_point else None,
            'point_code': self.monitoring_point.PointCode if self.monitoring_point else None,
            'install_date': self.InstallDate.isoformat() if self.InstallDate else None,
            'last_maintenance_date': self.LastMaintenanceDate.isoformat() if self.LastMaintenanceDate else None,
            'next_maintenance_date': self.NextMaintenanceDate.isoformat() if self.NextMaintenanceDate else None,
            'created_at': self.CreatedAt.isoformat() if self.CreatedAt else None,
            'updated_at': self.UpdatedAt.isoformat() if self.UpdatedAt else None,
            'location': {
                'longitude': self.monitoring_point.Longitude if self.monitoring_point else None,
                'latitude': self.monitoring_point.Latitude if self.monitoring_point else None
            } if self.monitoring_point else None
        }


class SystemUser(Base):
    """系统用户表"""
    __tablename__ = 'system_user'
    
    UserID = Column(Integer, primary_key=True, autoincrement=True)
    Username = Column(String(50), nullable=False, unique=True)
    PasswordHash = Column(String(255), nullable=False)
    UserRole = Column(String(20), nullable=False, default='普通用户')  # 改为String类型
    Email = Column(String(100), unique=True)
    Phone = Column(String(20))
    ResponsibleRegions = Column(String(500))  # 负责的区域ID列表，逗号分隔
    CreatedAt = Column(DateTime, default=datetime.now)
    LastLogin = Column(DateTime, onupdate=datetime.now)
    
    # 关系
    alerts_handled = relationship('AlertInfo', back_populates='handler')
    
    __table_args__ = (
        CheckConstraint("UserRole IN ('管理员', '操作员', '普通用户')", name='chk_user_role'),
    )
    
    def set_password(self, password):
        self.PasswordHash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.PasswordHash, password)

    def to_dict(self):
        return {
            'user_id': self.UserID,
            'username': self.Username,
            'role': self.UserRole,
            'email': self.Email,
            'phone': self.Phone,
            'responsible_regions': self.ResponsibleRegions.split(',') if self.ResponsibleRegions else [],
            'created_at': self.CreatedAt.isoformat() if self.CreatedAt else None,
            'last_login': self.LastLogin.isoformat() if self.LastLogin else None
        }


class RealtimeData(Base):
    """实时数据采集表 - 传感器实时采集的噪音数据""" 
    __tablename__ = 'realtime_data'
    
    DataID = Column(Integer, primary_key=True, autoincrement=True)
    NoiseValue = Column(Float, nullable=False)  # 噪音值（分贝）
    Timestamp = Column(DateTime, nullable=False, default=datetime.now, index=True)  # 采集时间戳
    FrequencySpectrum = Column(String(2000))  # 频率谱数据，JSON格式存储
    DataQuality = Column(String(20), default='良好')  # 数据质量
    Temperature = Column(Float)  # 环境温度（摄氏度）
    Humidity = Column(Float)  # 环境湿度（%）
    WindSpeed = Column(Float)  # 风速（m/s）
    WeatherCondition = Column(String(50))  # 天气状况
    SensorID = Column(String(50), ForeignKey('sensor.SensorID'), nullable=False, index=True)
    PointID = Column(Integer, ForeignKey('monitoring_point.PointID'), nullable=False, index=True)
    
    # 计算字段：是否超标
    @hybrid_property
    def is_exceeded(self):
        hour = self.Timestamp.hour
        point = self.monitoring_point
        if point:
            if 6 <= hour < 22:  # 昼间（6:00-22:00）
                return self.NoiseValue > point.NoiseThresholdDay
            else:  # 夜间（22:00-6:00）
                return self.NoiseValue > point.NoiseThresholdNight
        return False
    
    # 关系
    sensor = relationship('Sensor', back_populates='realtime_data')
    monitoring_point = relationship('MonitoringPoint', back_populates='realtime_data')
    alerts = relationship('AlertInfo', back_populates='realtime_data', cascade='all, delete-orphan')
    
    # 检查约束
    __table_args__ = (
        CheckConstraint('NoiseValue >= 0 AND NoiseValue <= 200', name='chk_noise_value'),
        CheckConstraint("DataQuality IN ('优秀', '良好', '一般', '较差', '无效')", name='chk_data_quality'),
        CheckConstraint('Temperature >= -50 AND Temperature <= 60', name='chk_temperature'),
        CheckConstraint('Humidity >= 0 AND Humidity <= 100', name='chk_humidity'),
        CheckConstraint('WindSpeed >= 0 AND WindSpeed <= 100', name='chk_wind_speed'),
    )
    
    def to_dict(self):
        return {
            'data_id': self.DataID,
            'noise_id': self.DataID,  # 添加noise_id字段，兼容前端
            'noise_value': self.NoiseValue,
            'timestamp': self.Timestamp.isoformat() if self.Timestamp else None,
            'frequency_spectrum': json.loads(self.FrequencySpectrum) if self.FrequencySpectrum else None,
            'data_quality': self.DataQuality,
            'temperature': self.Temperature,
            'humidity': self.Humidity,
            'wind_speed': self.WindSpeed,
            'weather_condition': self.WeatherCondition,
            'sensor_id': self.SensorID,
            'device_id': self.SensorID,  # 添加device_id字段，兼容前端
            'sensor_name': self.sensor.SensorName if self.sensor else None,
            'point_id': self.PointID,
            'point_name': self.monitoring_point.PointName if self.monitoring_point else None,
            'point_code': self.monitoring_point.PointCode if self.monitoring_point else None,
            'region_name': self.monitoring_point.District if self.monitoring_point else None,  # 添加region_name字段，兼容前端
            'is_exceeded': self.is_exceeded,
            'threshold_day': self.monitoring_point.NoiseThresholdDay if self.monitoring_point else None,
            'threshold_night': self.monitoring_point.NoiseThresholdNight if self.monitoring_point else None
        }


class TrendAnalysis(Base):
    """趋势分析表 - 存储噪音趋势分析结果"""
    __tablename__ = 'trend_analysis'
    
    AnalysisID = Column(Integer, primary_key=True, autoincrement=True)
    AnalysisType = Column(String(20), nullable=False)  # 分析类型：日趋势、周趋势、月趋势、年趋势
    AnalysisPeriod = Column(String(100))  # 分析周期，如"2025-01-01 至 2025-01-31"
    StartDate = Column(DateTime, nullable=False)  # 开始日期
    EndDate = Column(DateTime, nullable=False)  # 结束日期
    PointID = Column(Integer, ForeignKey('monitoring_point.PointID'))  # 可为空，表示全市分析
    SensorID = Column(String(50), ForeignKey('sensor.SensorID'))  # 可为空
    AverageNoise = Column(Float)  # 平均噪音值
    MaxNoise = Column(Float)  # 最大噪音值
    MinNoise = Column(Float)  # 最小噪音值
    ExceedCount = Column(Integer, default=0)  # 超标次数
    ExceedRate = Column(Float)  # 超标率（%）
    TrendDirection = Column(String(20))  # 趋势方向：上升、下降、平稳
    TrendRate = Column(Float)  # 趋势变化率（dB/周期）
    PeakHours = Column(String(200))  # 高峰时段，JSON格式存储
    AnalysisResult = Column(String(2000))  # 分析结果详情，JSON格式存储
    CreatedAt = Column(DateTime, default=datetime.now)
    
    # 关系
    monitoring_point = relationship('MonitoringPoint')
    sensor = relationship('Sensor')
    
    # 检查约束
    __table_args__ = (
        CheckConstraint("AnalysisType IN ('日趋势', '周趋势', '月趋势', '年趋势', '自定义')", name='chk_analysis_type'),
        CheckConstraint("TrendDirection IN ('上升', '下降', '平稳', '波动')", name='chk_trend_direction'),
        CheckConstraint('AverageNoise >= 0', name='chk_avg_noise'),
        CheckConstraint('MaxNoise >= 0', name='chk_max_noise'),
        CheckConstraint('MinNoise >= 0', name='chk_min_noise'),
        CheckConstraint('ExceedRate >= 0 AND ExceedRate <= 100', name='chk_exceed_rate'),
    )
    
    def to_dict(self):
        return {
            'analysis_id': self.AnalysisID,
            'analysis_type': self.AnalysisType,
            'analysis_period': self.AnalysisPeriod,
            'start_date': self.StartDate.isoformat() if self.StartDate else None,
            'end_date': self.EndDate.isoformat() if self.EndDate else None,
            'point_id': self.PointID,
            'point_name': self.monitoring_point.PointName if self.monitoring_point else None,
            'sensor_id': self.SensorID,
            'sensor_name': self.sensor.SensorName if self.sensor else None,
            'average_noise': self.AverageNoise,
            'max_noise': self.MaxNoise,
            'min_noise': self.MinNoise,
            'exceed_count': self.ExceedCount,
            'exceed_rate': self.ExceedRate,
            'trend_direction': self.TrendDirection,
            'trend_rate': self.TrendRate,
            'peak_hours': json.loads(self.PeakHours) if self.PeakHours else None,
            'analysis_result': json.loads(self.AnalysisResult) if self.AnalysisResult else None,
            'created_at': self.CreatedAt.isoformat() if self.CreatedAt else None
        }


class PatternRecognition(Base):
    """模式识别表 - 存储噪音模式识别结果"""
    __tablename__ = 'pattern_recognition'
    
    PatternID = Column(Integer, primary_key=True, autoincrement=True)
    PatternType = Column(String(50), nullable=False)  # 模式类型：工作日模式、周末模式、节假日模式、季节性模式等
    PatternName = Column(String(100))  # 模式名称
    PatternDescription = Column(String(500))  # 模式描述
    PointID = Column(Integer, ForeignKey('monitoring_point.PointID'))
    SensorID = Column(String(50), ForeignKey('sensor.SensorID'))
    RecognitionPeriod = Column(String(100))  # 识别周期
    StartDate = Column(DateTime)
    EndDate = Column(DateTime)
    PatternData = Column(String(5000))  # 模式数据，JSON格式存储（包含时间序列、特征值等）
    Confidence = Column(Float)  # 识别置信度（0-1）
    Characteristics = Column(String(1000))  # 特征描述，JSON格式存储
    CreatedAt = Column(DateTime, default=datetime.now)
    
    # 关系
    monitoring_point = relationship('MonitoringPoint')
    sensor = relationship('Sensor')
    
    # 检查约束
    __table_args__ = (
        CheckConstraint("PatternType IN ('工作日模式', '周末模式', '节假日模式', '季节性模式', '交通高峰模式', '夜间模式', '其他')", name='chk_pattern_type'),
        CheckConstraint('Confidence >= 0 AND Confidence <= 1', name='chk_confidence'),
    )
    
    def to_dict(self):
        return {
            'pattern_id': self.PatternID,
            'pattern_type': self.PatternType,
            'pattern_name': self.PatternName,
            'pattern_description': self.PatternDescription,
            'point_id': self.PointID,
            'point_name': self.monitoring_point.PointName if self.monitoring_point else None,
            'sensor_id': self.SensorID,
            'sensor_name': self.sensor.SensorName if self.sensor else None,
            'recognition_period': self.RecognitionPeriod,
            'start_date': self.StartDate.isoformat() if self.StartDate else None,
            'end_date': self.EndDate.isoformat() if self.EndDate else None,
            'pattern_data': json.loads(self.PatternData) if self.PatternData else None,
            'confidence': self.Confidence,
            'characteristics': json.loads(self.Characteristics) if self.Characteristics else None,
            'created_at': self.CreatedAt.isoformat() if self.CreatedAt else None
        }


class AlertInfo(Base):
    """告警信息表"""
    __tablename__ = 'alert_info'
    
    AlertID = Column(Integer, primary_key=True, autoincrement=True)
    AlertLevel = Column(String(20), default='低')  # 告警级别
    TriggerTime = Column(DateTime, nullable=False, default=datetime.now, index=True)  # 触发时间
    AlertStatus = Column(String(20), default='未处理')  # 告警状态
    AlertType = Column(String(50), default='噪音超标')  # 告警类型
    ProcessNotes = Column(String(500))  # 处理备注
    DataID = Column(Integer, ForeignKey('realtime_data.DataID'), nullable=False)  # 关联实时数据
    HandlerID = Column(Integer, ForeignKey('system_user.UserID'))  # 处理人
    ProcessedAt = Column(DateTime)  # 处理时间
    
    # 关系
    realtime_data = relationship('RealtimeData', back_populates='alerts')
    handler = relationship('SystemUser', back_populates='alerts_handled')
    
    __table_args__ = (
        CheckConstraint("AlertLevel IN ('低', '中', '高', '紧急')", name='chk_alert_level'),
        CheckConstraint("AlertStatus IN ('未处理', '处理中', '已处理', '已关闭')", name='chk_alert_status'),
        CheckConstraint("AlertType IN ('噪音超标', '传感器故障', '数据异常', '连续超标', '其他')", name='chk_alert_type'),
    )
    
    def to_dict(self):
        # 获取监测点和传感器信息
        monitoring_point = self.realtime_data.monitoring_point if self.realtime_data else None
        sensor = self.realtime_data.sensor if self.realtime_data else None
        
        return {
            'alert_id': self.AlertID,
            'alert_level': self.AlertLevel,
            'alert_type': self.AlertType,
            'trigger_time': self.TriggerTime.isoformat() if self.TriggerTime else None,
            'alert_status': self.AlertStatus,
            'noise_value': self.realtime_data.NoiseValue if self.realtime_data else None,
            'point_id': self.realtime_data.PointID if self.realtime_data else None,
            'point_name': monitoring_point.PointName if monitoring_point else None,
            'point_code': monitoring_point.PointCode if monitoring_point else None,
            'sensor_id': self.realtime_data.SensorID if self.realtime_data else None,
            'sensor_name': sensor.SensorName if sensor else None,
            # 添加前端需要的字段
            'region_name': monitoring_point.District if monitoring_point else None,  # 区域名称（区/县）
            'device_id': self.realtime_data.SensorID if self.realtime_data else None,  # 设备ID（传感器ID）
            'handler': self.handler.Username if self.handler else None,
            'handler_id': self.HandlerID,
            'process_notes': self.ProcessNotes,
            'processed_at': self.ProcessedAt.isoformat() if self.ProcessedAt else None
        }


class Report(Base):
    """报告表"""
    __tablename__ = 'report'
    
    ReportID = Column(Integer, primary_key=True, autoincrement=True)
    ReportType = Column(String(20), nullable=False)  # 改为String类型
    ReportPeriod = Column(String(100))  # 报告周期，如"2025-06-01 至 2025-06-30"
    GeneratedAt = Column(DateTime, default=datetime.now)
    GeneratedBy = Column(Integer, ForeignKey('system_user.UserID'), nullable=False)
    Content = Column(String(5000))  # 报告内容，JSON格式或HTML格式
    FilePath = Column(String(255))  # 生成的报告文件路径
    IsPublic = Column(Integer, default=0)  # 0:私有, 1:公开
    
    # 关系
    generator = relationship('SystemUser')
    
    __table_args__ = (
        CheckConstraint("ReportType IN ('日报', '周报', '月报', '年报', '专项报告')", name='chk_report_type'),
    )
    
    def to_dict(self):
        content = None
        if self.Content:
            try:
                content = json.loads(self.Content)
            except:
                content = self.Content
        
        return {
            'report_id': self.ReportID,
            'report_type': self.ReportType,
            'report_period': self.ReportPeriod,
            'generated_at': self.GeneratedAt.isoformat() if self.GeneratedAt else None,
            'generated_by': self.generator.Username if self.generator else None,
            'is_public': bool(self.IsPublic),
            'file_path': self.FilePath,
            'content': content
        }


# ==================== 辅助函数 ====================

def allowed_file(filename):
    """检查文件类型"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'csv', 'xlsx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def calculate_noise_level(noise_value, region_type):
    """根据噪音值和区域类型计算噪音等级"""
    thresholds = {
        '住宅区': {'优': 50, '良': 55, '轻度': 60, '中度': 65, '重度': 70},
        '商业区': {'优': 55, '良': 60, '轻度': 65, '中度': 70, '重度': 75},
        '工业区': {'优': 60, '良': 65, '轻度': 70, '中度': 75, '重度': 80},
        '文教区': {'优': 45, '良': 50, '轻度': 55, '中度': 60, '重度': 65},
    }
    
    default_threshold = {'优': 55, '良': 60, '轻度': 65, '中度': 70, '重度': 75}
    threshold = thresholds.get(region_type, default_threshold)
    
    if noise_value <= threshold['优']:
        return '优'
    elif noise_value <= threshold['良']:
        return '良'
    elif noise_value <= threshold['轻度']:
        return '轻度污染'
    elif noise_value <= threshold['中度']:
        return '中度污染'
    else:
        return '重度污染'


def check_and_generate_alert(realtime_data, session):
    """检查实时噪音数据是否超标并生成告警"""
    if realtime_data.is_exceeded:
        # 计算告警级别
        exceed_amount = 0
        hour = realtime_data.Timestamp.hour
        point = realtime_data.monitoring_point
        
        if point:
            if 6 <= hour < 22:  # 昼间
                exceed_amount = realtime_data.NoiseValue - point.NoiseThresholdDay
            else:  # 夜间
                exceed_amount = realtime_data.NoiseValue - point.NoiseThresholdNight
        
        # 根据超标程度确定告警级别
        if exceed_amount <= 5:
            level = '低'
        elif exceed_amount <= 10:
            level = '中'
        elif exceed_amount <= 15:
            level = '高'
        else:
            level = '紧急'
        
        # 创建告警记录
        alert = AlertInfo(
            AlertLevel=level,
            TriggerTime=realtime_data.Timestamp,
            DataID=realtime_data.DataID,
            AlertStatus='未处理',
            AlertType='噪音超标'
        )
        
        session.add(alert)
        session.flush()  # 刷新以获取AlertID
        
        return alert
    return None


# ==================== API路由 ====================

@app.route('/api/init-db', methods=['POST'])
@log_request_time
def init_database():
    """初始化数据库表"""
    try:
        Base.metadata.create_all(engine)
        
        with get_db_session() as session:
            # 检查是否已有管理员账户
            existing_admin = session.query(SystemUser).filter_by(Username='admin').first()
            if not existing_admin:
                # 创建默认管理员账户
                admin = SystemUser(
                    Username='admin',
                    UserRole='管理员',
                    Email='admin@noise-monitoring.com'
                )
                admin.set_password('admin123')
                session.add(admin)
            
            # 添加示例城市（如果不存在）
            cities_data = [
                {'name': '北京市', 'province': '北京市'},
                {'name': '上海市', 'province': '上海市'},
                {'name': '广州市', 'province': '广东省'},
                {'name': '深圳市', 'province': '广东省'}
            ]
            for city_info in cities_data:
                existing_city = session.query(City).filter_by(CityName=city_info['name']).first()
                if not existing_city:
                    city = City(CityName=city_info['name'], Province=city_info['province'])
                    session.add(city)
        
        return jsonify({
            'status': 'success',
            'message': '数据库初始化成功'
        }), 200
    except Exception as e:
        app.logger.error(f'数据库初始化失败: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'数据库初始化失败: {str(e)}'
        }), 500


@app.route('/api/auth/register', methods=['POST'])
@validate_json('username', 'password', 'email', 'role')
@log_request_time
def register():
    """用户注册"""
    data = request.get_json()
    
    try:
        with get_db_session() as session:
            # 检查用户名是否已存在
            existing_user = session.query(SystemUser).filter_by(Username=data['username']).first()
            if existing_user:
                return jsonify({'status': 'error', 'message': '用户名已存在'}), 400
            
            # 检查邮箱是否已存在
            existing_email = session.query(SystemUser).filter_by(Email=data['email']).first()
            if existing_email:
                return jsonify({'status': 'error', 'message': '邮箱已注册'}), 400
            
            user = SystemUser(
                Username=data['username'],
                Email=data['email'],
                UserRole=data['role'],
                Phone=data.get('phone', ''),
                ResponsibleRegions=','.join(map(str, data.get('responsible_regions', [])))
            )
            user.set_password(data['password'])
            session.add(user)
            session.flush()  # 刷新以获取UserID
            session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '注册成功',
            'user_id': user.UserID
        }), 201
    except Exception as e:
        app.logger.error(f'注册失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'注册失败: {str(e)}'}), 500


@app.route('/api/auth/login', methods=['POST'])
@validate_json('username', 'password')
@log_request_time
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username', '')
    
    try:
        with get_db_session() as session:
            user = session.query(SystemUser).filter_by(Username=username).first()
    
            # 添加详细的日志记录
            if not user:
                app.logger.warning(f'登录失败: 用户不存在 - {username}')
                return jsonify({'status': 'error', 'message': '用户名或密码错误'}), 401
    
            app.logger.info(f'找到用户: {username}, 开始验证密码')
            password_valid = user.check_password(data['password'])
            
            if password_valid:
                # 更新最后登录时间
                user.LastLogin = datetime.now()
                session.commit()
                
                app.logger.info(f'登录成功: {username}')
                return jsonify({
                    'status': 'success',
                    'message': '登录成功',
                    'user': user.to_dict()
                }), 200
            else:
                app.logger.warning(f'登录失败: 密码错误 - {username}')
                return jsonify({'status': 'error', 'message': '用户名或密码错误'}), 401
    except Exception as e:
        app.logger.error(f'登录失败: {str(e)}', exc_info=True)
        return jsonify({'status': 'error', 'message': f'登录失败: {str(e)}'}), 500


@app.route('/api/realtime-data', methods=['POST'])
@validate_json('noise_value', 'sensor_id')
@log_request_time
def upload_realtime_data():
    """上传实时噪音数据（传感器实时采集）"""
    data = request.get_json()
    
    try:
        with get_db_session() as session:
            # 验证传感器是否存在
            sensor = session.query(Sensor).filter_by(SensorID=data['sensor_id']).first()
            if not sensor:
                return jsonify({'status': 'error', 'message': '传感器不存在'}), 404
            
            if sensor.Status != '在线':
                return jsonify({'status': 'error', 'message': f'传感器状态异常: {sensor.Status}'}), 400
    
            # 创建实时数据记录
            timestamp = datetime.fromisoformat(data['timestamp']) if isinstance(data.get('timestamp'), str) else data.get('timestamp', datetime.now())
            
            realtime_data = RealtimeData(
            NoiseValue=float(data['noise_value']),
                Timestamp=timestamp,
                FrequencySpectrum=json.dumps(data.get('frequency_spectrum')) if data.get('frequency_spectrum') else None,
            DataQuality=data.get('data_quality', '良好'),
                Temperature=data.get('temperature'),
                Humidity=data.get('humidity'),
                WindSpeed=data.get('wind_speed'),
                WeatherCondition=data.get('weather_condition'),
                SensorID=data['sensor_id'],
                PointID=sensor.PointID
        )
        
            session.add(realtime_data)
            session.flush()  # 刷新以获取DataID和关联数据
        
        # 检查是否超标并生成告警
            alert = check_and_generate_alert(realtime_data, session)
            session.commit()
        
        response = {
            'status': 'success',
            'message': '实时数据上传成功',
            'data_id': realtime_data.DataID,
            'is_exceeded': realtime_data.is_exceeded,
            'point_name': realtime_data.monitoring_point.PointName if realtime_data.monitoring_point else None
        }
        
        if alert:
            response['alert'] = {
                'alert_id': alert.AlertID,
                'alert_level': alert.AlertLevel,
                'alert_type': alert.AlertType
            }
        
        return jsonify(response), 201
    except Exception as e:
        app.logger.error(f'上传实时数据失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'上传失败: {str(e)}'}), 500


@app.route('/api/realtime-data', methods=['GET'])
@log_request_time
def get_realtime_data():
    """查询实时噪音数据（支持分页和过滤）"""
    try:
        # 获取查询参数
        point_id = request.args.get('point_id', type=int)
        sensor_id = request.args.get('sensor_id')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        page, per_page = get_pagination_params()
        offset = (page - 1) * per_page
        
        with get_db_session() as session:
            query = session.query(RealtimeData)
            
            # 应用过滤条件
            if point_id:
                query = query.filter(RealtimeData.PointID == point_id)
            if sensor_id:
                query = query.filter(RealtimeData.SensorID == sensor_id)
            if start_time:
                start_dt = datetime.fromisoformat(start_time) if isinstance(start_time, str) else start_time
                query = query.filter(RealtimeData.Timestamp >= start_dt)
            if end_time:
                end_dt = datetime.fromisoformat(end_time) if isinstance(end_time, str) else end_time
                query = query.filter(RealtimeData.Timestamp <= end_dt)
            
            # 总数查询
            total = query.count()
            
            # 数据查询（分页）
            realtime_data = query.order_by(RealtimeData.Timestamp.desc()).offset(offset).limit(per_page).all()
            
            result = [data.to_dict() for data in realtime_data]
            
        return jsonify({
            'status': 'success',
            'data': result,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        app.logger.error(f'查询噪音数据失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'查询失败: {str(e)}'}), 500


@app.route('/api/noise-data', methods=['GET'])
@log_request_time
def get_noise_data():
    """查询噪音数据（兼容前端API）"""
    try:
        # 获取查询参数
        region_id = request.args.get('region_id', type=int)  # 实际上是 point_id
        device_id = request.args.get('device_id')  # 实际上是 sensor_id
        district = request.args.get('district')  # 支持按区域（District）筛选
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        hours = request.args.get('hours', type=int)  # 支持按小时数查询最近的数据
        limit = request.args.get('limit', type=int, default=1000)  # 默认限制增加到1000，用于图表显示
        
        with get_db_session() as session:
            query = session.query(RealtimeData)
            
            # 如果指定了hours参数，计算时间范围
            if hours:
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=hours)
            
            # 应用过滤条件
            if district:
                # 按区域（District）筛选
                query = query.join(MonitoringPoint).filter(MonitoringPoint.District == district)
            elif region_id:
                query = query.filter(RealtimeData.PointID == region_id)
            if device_id:
                query = query.filter(RealtimeData.SensorID == device_id)
            if start_time:
                if isinstance(start_time, str):
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                else:
                    start_dt = start_time
                query = query.filter(RealtimeData.Timestamp >= start_dt)
            if end_time:
                if isinstance(end_time, str):
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                else:
                    end_dt = end_time
                query = query.filter(RealtimeData.Timestamp <= end_dt)
            
            # 总数查询
            total = query.count()
            
            # 数据查询（限制数量，如果指定了hours，按时间正序排列以便图表显示）
            if hours:
                realtime_data = query.order_by(RealtimeData.Timestamp.asc()).limit(limit).all()
            else:
                realtime_data = query.order_by(RealtimeData.Timestamp.desc()).limit(limit).all()
            
            result = [data.to_dict() for data in realtime_data]
            
        return jsonify({
            'status': 'success',
            'data': result,
            'count': total
        }), 200
    except Exception as e:
        app.logger.error(f'查询噪音数据失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'查询失败: {str(e)}'}), 500


@app.route('/api/noise-data', methods=['POST'])
@log_request_time
def upload_noise_data():
    """上传噪音数据（兼容前端API）"""
    data = request.get_json()
    
    try:
        with get_db_session() as session:
            # 验证设备是否存在（通过 sensor_id 或 device_id）
            sensor_id = data.get('sensor_id') or data.get('device_id')
            if not sensor_id:
                return jsonify({'status': 'error', 'message': '缺少设备ID（sensor_id或device_id）'}), 400
            
            sensor = session.query(Sensor).filter_by(SensorID=sensor_id).first()
            if not sensor:
                return jsonify({'status': 'error', 'message': '设备不存在'}), 404
            
            if sensor.Status != '在线':
                return jsonify({'status': 'error', 'message': f'设备状态异常: {sensor.Status}'}), 400
            
            # 处理 region_id（实际上是 point_id）
            point_id = data.get('region_id') or sensor.PointID
            if data.get('region_id') and data.get('region_id') != sensor.PointID:
                # 验证 region_id 是否有效
                point = session.query(MonitoringPoint).filter_by(PointID=point_id).first()
                if not point:
                    return jsonify({'status': 'error', 'message': '区域不存在'}), 404
            
            # 创建实时数据记录
            timestamp = datetime.fromisoformat(data['timestamp']) if isinstance(data.get('timestamp'), str) else data.get('timestamp', datetime.now())
            
            realtime_data = RealtimeData(
                NoiseValue=float(data['noise_value']),
                Timestamp=timestamp,
                FrequencySpectrum=json.dumps(data.get('frequency_spectrum') or data.get('frequency_analysis')) if data.get('frequency_spectrum') or data.get('frequency_analysis') else None,
                DataQuality=data.get('data_quality', '良好'),
                Temperature=data.get('temperature'),
                Humidity=data.get('humidity'),
                WindSpeed=data.get('wind_speed'),
                WeatherCondition=data.get('weather_condition') or data.get('weather'),
                SensorID=sensor_id,
                PointID=point_id
            )
            
            session.add(realtime_data)
            session.flush()  # 刷新以获取DataID和关联数据
            
            # 检查是否超标并生成告警
            alert = check_and_generate_alert(realtime_data, session)
            session.commit()
            
            response = {
                'status': 'success',
                'message': '噪音数据上传成功',
                'noise_id': realtime_data.DataID,
                'data_id': realtime_data.DataID,
                'is_exceeded': realtime_data.is_exceeded,
                'point_name': realtime_data.monitoring_point.PointName if realtime_data.monitoring_point else None
            }
            
            if alert:
                response['alert'] = {
                    'alert_id': alert.AlertID,
                    'alert_level': alert.AlertLevel,
                    'alert_type': alert.AlertType
                }
            
            return jsonify(response), 201
    except Exception as e:
        app.logger.error(f'上传噪音数据失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'上传失败: {str(e)}'}), 500


@app.route('/api/noise-data/statistics', methods=['GET'])
@log_request_time
def get_noise_statistics():
    """获取噪音统计信息"""
    try:
        point_id = request.args.get('point_id', type=int)
        region_id = request.args.get('region_id')  # 支持region_id参数（可以是数字或字符串）
        district = request.args.get('district')  # 支持按区域（District）筛选
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        hours = request.args.get('hours', type=int)  # 支持按小时数查询最近的数据
        
        with get_db_session() as session:
            query = session.query(RealtimeData)
            
            # 如果指定了hours参数，计算时间范围
            start_dt = None
            end_dt = None
            if hours:
                end_dt = datetime.now()
                start_dt = end_dt - timedelta(hours=hours)
            else:
                # 如果没有指定hours，使用start_time和end_time参数
                if start_time:
                    if isinstance(start_time, str):
                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    else:
                        start_dt = start_time
                if end_time:
                    if isinstance(end_time, str):
                        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    else:
                        end_dt = end_time
            
            if district:
                # 按区域（District）筛选
                query = query.join(MonitoringPoint).filter(MonitoringPoint.District == district)
            elif region_id:
                # 如果region_id是数字，通过监测点关联城市来筛选
                try:
                    region_id_int = int(region_id)
                    query = query.join(MonitoringPoint).filter(MonitoringPoint.CityID == region_id_int)
                except (ValueError, TypeError):
                    # 如果region_id不是数字，可能是区域名称（District）
                    query = query.join(MonitoringPoint).filter(MonitoringPoint.District == region_id)
            elif point_id:
                query = query.filter(RealtimeData.PointID == point_id)
            
            # 应用时间过滤
            if start_dt:
                query = query.filter(RealtimeData.Timestamp >= start_dt)
            if end_dt:
                query = query.filter(RealtimeData.Timestamp <= end_dt)
            
            # 确保查询包含监测点关联（用于计算超标率）
            # 检查是否已经join了监测点
            already_joined = any([district, region_id])  # district和region_id已经join了
            if not already_joined:
                # 如果没有join，需要join监测点以获取阈值信息（用于计算超标率）
                # 当没有选择区域时，显示所有区域的总体分析
                query_with_point = query.join(MonitoringPoint)
                # 同时更新query以便hourly_query也能正确工作
                query = query.join(MonitoringPoint)
            else:
                query_with_point = query
            
            # 基本统计
            avg_noise = query_with_point.with_entities(func.avg(RealtimeData.NoiseValue)).scalar() or 0
            max_noise = query_with_point.with_entities(func.max(RealtimeData.NoiseValue)).scalar() or 0
            min_noise = query_with_point.with_entities(func.min(RealtimeData.NoiseValue)).scalar() or 0
            
            # 超标统计 - 使用监测点的实际标准值判断（白天/夜间不同阈值）
            # 使用 SQL CASE 语句在数据库层面计算，提高性能
            # 昼间（6:00-22:00）：使用 NoiseThresholdDay
            # 夜间（22:00-6:00）：使用 NoiseThresholdNight
            hour_expr = func.extract('hour', RealtimeData.Timestamp)
            exceed_condition = case(
                (
                    (hour_expr >= 6) & (hour_expr < 22),
                    RealtimeData.NoiseValue > MonitoringPoint.NoiseThresholdDay
                ),
                else_=RealtimeData.NoiseValue > MonitoringPoint.NoiseThresholdNight
            )
            
            total_count = query_with_point.count()
            # 计算超标数量 - 使用 func.sum 和 case 来计算
            exceed_count = query_with_point.with_entities(
                func.sum(case((exceed_condition, 1), else_=0))
            ).scalar() or 0
            
            # 按时间段统计（日/小时）- 使用相同的筛选条件
            # 注意：hourly_query需要使用原始的query（可能已经join了MonitoringPoint）
            # 但我们需要确保只对RealtimeData进行聚合
            hourly_query = query.with_entities(
                func.extract('hour', RealtimeData.Timestamp).label('hour'),
                func.avg(RealtimeData.NoiseValue).label('avg_noise'),
                func.count(RealtimeData.DataID).label('count')
            ).group_by(func.extract('hour', RealtimeData.Timestamp)).order_by(func.extract('hour', RealtimeData.Timestamp))
            hourly_stats = hourly_query.all()
            
            hourly_data = [{
                'hour': int(stat.hour),
                'avg_noise': float(stat.avg_noise or 0),
                'count': stat.count
            } for stat in hourly_stats]
            
            # 添加调试日志
            app.logger.info(f'统计查询结果: district={district}, hours={hours}, total_count={total_count}, avg_noise={avg_noise}, hourly_data_count={len(hourly_data)}')
            
            return jsonify({
                'status': 'success',
                'statistics': {
                    'avg_noise': round(float(avg_noise), 2),
                    'max_noise': round(float(max_noise), 2),
                    'min_noise': round(float(min_noise), 2),
                    'total_count': total_count,
                    'exceed_count': exceed_count,
                    'exceed_rate': round(exceed_count / total_count * 100, 2) if total_count > 0 else 0
                },
                'hourly_data': hourly_data
            }), 200
    except Exception as e:
        app.logger.error(f'统计查询失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'统计查询失败: {str(e)}'}), 500


@app.route('/api/alerts', methods=['GET'])
@log_request_time
def get_alerts():
    """获取告警信息（支持分页）"""
    try:
        status = request.args.get('status')
        level = request.args.get('level')
        point_id = request.args.get('point_id', type=int)
        region_id = request.args.get('region_id')  # 支持region_id参数（可以是数字或字符串）
        district = request.args.get('district')  # 支持按区域（District）筛选
        page, per_page = get_pagination_params()
        offset = (page - 1) * per_page
        
        with get_db_session() as session:
            query = session.query(AlertInfo).join(RealtimeData)
            
            if status:
                query = query.filter(AlertInfo.AlertStatus == status)
            if level:
                query = query.filter(AlertInfo.AlertLevel == level)
            if district:
                # 按区域（District）筛选
                query = query.join(MonitoringPoint).filter(MonitoringPoint.District == district)
            elif region_id:
                # 如果region_id是数字，通过监测点关联城市来筛选
                try:
                    region_id_int = int(region_id)
                    query = query.join(MonitoringPoint).filter(MonitoringPoint.CityID == region_id_int)
                except (ValueError, TypeError):
                    # 如果region_id不是数字，可能是区域名称（District）
                    query = query.join(MonitoringPoint).filter(MonitoringPoint.District == region_id)
            elif point_id:
                query = query.filter(RealtimeData.PointID == point_id)
            
            # 总数查询
            total = query.count()
            
            # 数据查询（分页）
            alerts = query.order_by(AlertInfo.TriggerTime.desc()).offset(offset).limit(per_page).all()
            
            result = [alert.to_dict() for alert in alerts]
            
            return jsonify({
                'status': 'success',
                'alerts': result,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }), 200
    except Exception as e:
        app.logger.error(f'查询告警失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'查询告警失败: {str(e)}'}), 500


@app.route('/api/alerts/<int:alert_id>', methods=['PUT'])
@log_request_time
def update_alert(alert_id):
    """更新告警状态"""
    try:
        data = request.get_json() or {}
    
        with get_db_session() as session:
            alert = session.query(AlertInfo).filter_by(AlertID=alert_id).first()
            if not alert:
                return jsonify({'status': 'error', 'message': '告警不存在'}), 404
    
            if 'status' in data:
                alert.AlertStatus = data['status']
            if 'handler_id' in data:
                alert.HandlerID = data['handler_id']
            if 'process_notes' in data:
                alert.ProcessNotes = data['process_notes']
    
            session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '告警更新成功'
        }), 200
    except Exception as e:
        app.logger.error(f'更新告警失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'更新失败: {str(e)}'}), 500


@app.route('/api/regions', methods=['GET'])
@log_request_time
def get_regions():
    """获取监测区域列表"""
    try:
        city_id = request.args.get('city_id', type=int)
        region_type = request.args.get('type')
        district = request.args.get('district')  # 支持按区域（District）筛选
        districts_only = request.args.get('districts_only', type=bool)  # 是否只返回区域（District）列表
        
        with get_db_session() as session:
            if districts_only:
                # 返回所有唯一的区域（District）列表
                districts = session.query(MonitoringPoint.District).distinct().filter(
                    MonitoringPoint.District.isnot(None)
                ).all()
                
                result = []
                for (district,) in districts:
                    if district:
                        # 统计该区域的监测点和传感器数量
                        point_count = session.query(MonitoringPoint).filter_by(District=district).count()
                        sensor_count = session.query(Sensor).join(MonitoringPoint).filter(
                            MonitoringPoint.District == district
                        ).count()
                        
                        result.append({
                            'region_id': district,  # 使用区域名称作为ID
                            'region_name': district,
                            'district': district,
                            'point_count': point_count,
                            'sensor_count': sensor_count
                        })
                
                return jsonify({
                    'status': 'success',
                    'regions': result,
                    'count': len(result)
                }), 200
            
            # 原有的监测点列表逻辑
            query = session.query(MonitoringPoint)
            
            if district:
                query = query.filter(MonitoringPoint.District == district)
            if city_id:
                query = query.filter(MonitoringPoint.CityID == city_id)
            if region_type:
                query = query.filter(MonitoringPoint.PointType == region_type)
            
            points = query.all()
            
            result = []
            for point in points:
                # 获取最近24小时的统计数据
                hour = datetime.now().hour
                threshold = point.NoiseThresholdDay if 6 <= hour < 22 else point.NoiseThresholdNight
                recent_stats = session.query(
                    func.avg(RealtimeData.NoiseValue).label('avg_noise'),
                    func.count(RealtimeData.DataID).label('data_count'),
                    func.sum(case((RealtimeData.NoiseValue > threshold, 1), else_=0)).label('exceed_count')
                ).filter(
                    RealtimeData.PointID == point.PointID,
                    RealtimeData.Timestamp >= datetime.now().replace(hour=0, minute=0, second=0)
                ).first()
                
                point_dict = point.to_dict()
                point_dict['district'] = point.District  # 添加district字段，方便前端使用
                point_dict['sensor_count'] = session.query(Sensor).filter_by(PointID=point.PointID).count()
                point_dict['recent_stats'] = {
                    'avg_noise': float(recent_stats.avg_noise or 0),
                    'data_count': recent_stats.data_count or 0,
                    'exceed_count': recent_stats.exceed_count or 0
                } if recent_stats else None
                result.append(point_dict)
            
            return jsonify({
                'status': 'success',
                'regions': result,
                'count': len(result)
            }), 200
    except Exception as e:
        app.logger.error(f'查询区域失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'查询区域失败: {str(e)}'}), 500


@app.route('/api/regions/<int:point_id>/devices', methods=['GET'])
@log_request_time
def get_region_devices(point_id):
    """获取区域内的监测设备"""
    try:
        with get_db_session() as session:
            sensors = session.query(Sensor).filter_by(PointID=point_id).all()
            
            result = []
            for sensor in sensors:
                # 获取设备最近状态
                recent_data = session.query(RealtimeData).filter_by(SensorID=sensor.SensorID)\
                    .order_by(RealtimeData.Timestamp.desc()).first()
                
                sensor_dict = sensor.to_dict()
                sensor_dict['recent_noise'] = recent_data.NoiseValue if recent_data else None
                sensor_dict['recent_update'] = recent_data.Timestamp.isoformat() if recent_data else None
                result.append(sensor_dict)
            
            return jsonify({
                'status': 'success',
                'devices': result
            }), 200
    except Exception as e:
        app.logger.error(f'查询设备失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'查询设备失败: {str(e)}'}), 500


@app.route('/api/devices', methods=['GET'])
@log_request_time
def get_devices():
    """获取所有监测设备"""
    try:
        status = request.args.get('status')
        point_id = request.args.get('point_id', type=int)
        region_id = request.args.get('region_id')  # 支持region_id参数（可以是数字或字符串）
        district = request.args.get('district')  # 支持按区域（District）筛选
        
        with get_db_session() as session:
            query = session.query(Sensor)
            
            if status:
                query = query.filter(Sensor.Status == status)
            if point_id:
                query = query.filter(Sensor.PointID == point_id)
            if district:
                # 按区域（District）筛选，如：黄浦区、静安区等
                query = query.join(MonitoringPoint).filter(MonitoringPoint.District == district)
            elif region_id:
                # 如果region_id是数字，通过监测点关联城市来筛选
                try:
                    region_id_int = int(region_id)
                    query = query.join(MonitoringPoint).filter(MonitoringPoint.CityID == region_id_int)
                except (ValueError, TypeError):
                    # 如果region_id不是数字，可能是区域名称（District）
                    query = query.join(MonitoringPoint).filter(MonitoringPoint.District == region_id)
            
            sensors = query.all()
            result = []
            for sensor in sensors:
                sensor_dict = sensor.to_dict()
                # 添加监测点信息
                if sensor.monitoring_point:
                    sensor_dict['region_name'] = sensor.monitoring_point.District or (sensor.monitoring_point.city.CityName if sensor.monitoring_point.city else None)
                    sensor_dict['district'] = sensor.monitoring_point.District  # 添加区域字段
                    sensor_dict['point_name'] = sensor.monitoring_point.PointName
                    sensor_dict['point_type'] = sensor.monitoring_point.PointType
                result.append(sensor_dict)
            
            return jsonify({
                'status': 'success',
                'devices': result,
                'count': len(result)
            }), 200
    except Exception as e:
        app.logger.error(f'查询设备失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'查询设备失败: {str(e)}'}), 500


@app.route('/api/devices/statuses', methods=['GET'])
@log_request_time
def get_device_statuses():
    """获取所有可用的设备状态列表"""
    try:
        # 从数据库约束中获取所有可用的状态值
        statuses = ['在线', '离线', '故障', '维护中', '校准中']
        
        # 可选：从数据库中获取实际使用的状态值（去重）
        with get_db_session() as session:
            used_statuses = session.query(Sensor.Status).distinct().all()
            used_statuses_list = [status[0] for status in used_statuses if status[0]]
            # 如果数据库中有状态值，使用数据库中的；否则使用默认列表
            if used_statuses_list:
                statuses = sorted(list(set(statuses + used_statuses_list)))
        
        return jsonify({
            'status': 'success',
            'statuses': statuses
        }), 200
    except Exception as e:
        app.logger.error(f'获取设备状态列表失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'获取设备状态列表失败: {str(e)}'}), 500


@app.route('/api/reports', methods=['POST'])
@validate_json('report_type', 'generated_by')
@log_request_time
def generate_report():
    """生成报告"""
    data = request.get_json()
    
    try:
        with get_db_session() as session:
            # 解析报告周期
            start_date = None
            end_date = None
            if data.get('start_date') and data.get('end_date'):
                start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
                end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
                # 结束日期设置为当天的23:59:59
                end_date = end_date.replace(hour=23, minute=59, second=59)
            elif data.get('report_period'):
                # 从字符串解析日期范围（支持"至"和"到"）
                period = data['report_period']
                if '至' in period or '到' in period:
                    separator = '至' if '至' in period else '到'
                    parts = period.split(separator)
                    if len(parts) == 2:
                        try:
                            start_date = datetime.strptime(parts[0].strip(), '%Y-%m-%d')
                            end_date = datetime.strptime(parts[1].strip(), '%Y-%m-%d')
                            end_date = end_date.replace(hour=23, minute=59, second=59)
                        except ValueError:
                            # 如果解析失败，使用默认值
                            pass
            
            # 如果没有提供日期，根据报告类型自动计算
            if not start_date or not end_date:
                today = datetime.now()
                report_type = data['report_type']
                if report_type == '日报':
                    start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = today.replace(hour=23, minute=59, second=59, microsecond=999999)
                elif report_type == '周报':
                    # 本周一
                    day_of_week = today.weekday()  # 0=Monday, 6=Sunday
                    start_date = today - timedelta(days=day_of_week)
                    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = start_date + timedelta(days=6)
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                elif report_type == '月报':
                    # 本月第一天
                    start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    # 本月最后一天
                    if today.month == 12:
                        end_date = today.replace(year=today.year + 1, month=1, day=1)
                    else:
                        end_date = today.replace(month=today.month + 1, day=1)
                    end_date = end_date - timedelta(days=1)
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                elif report_type == '年报':
                    # 今年第一天
                    start_date = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                    # 今年最后一天
                    end_date = today.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
                else:  # 专项报告，默认最近30天
                    end_date = today.replace(hour=23, minute=59, second=59, microsecond=999999)
                    start_date = end_date - timedelta(days=30)
                    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 生成报告周期字符串
            report_period = f"{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}"
            
            # 查询该周期内的数据统计
            noise_query = session.query(RealtimeData).filter(
                RealtimeData.Timestamp >= start_date,
                RealtimeData.Timestamp <= end_date
            )
            
            total_count = noise_query.count()
            avg_noise = noise_query.with_entities(func.avg(RealtimeData.NoiseValue)).scalar() or 0
            max_noise = noise_query.with_entities(func.max(RealtimeData.NoiseValue)).scalar() or 0
            min_noise = noise_query.with_entities(func.min(RealtimeData.NoiseValue)).scalar() or 0
            
            # 超标统计
            exceed_count = 0
            for noise_data in noise_query.all():
                if noise_data.is_exceeded:
                    exceed_count += 1
            
            exceed_rate = (exceed_count / total_count * 100) if total_count > 0 else 0
            
            # 按区域统计
            region_stats = session.query(
                MonitoringPoint.PointID,
                MonitoringPoint.PointName,
                MonitoringPoint.PointType,
                func.avg(RealtimeData.NoiseValue).label('avg_noise'),
                func.count(RealtimeData.DataID).label('data_count')
            ).join(RealtimeData).filter(
                RealtimeData.Timestamp >= start_date,
                RealtimeData.Timestamp <= end_date
            ).group_by(
                MonitoringPoint.PointID,
                MonitoringPoint.PointName,
                MonitoringPoint.PointType
            ).all()
            
            region_statistics = []
            for stat in region_stats:
                region_statistics.append({
                    'region_id': stat.PointID,
                    'region_name': stat.PointName,
                    'region_type': stat.PointType,
                    'avg_noise': round(float(stat.avg_noise or 0), 2),
                    'data_count': stat.data_count
                })
            
            # 告警统计
            alert_query = session.query(AlertInfo).join(RealtimeData).filter(
                AlertInfo.TriggerTime >= start_date,
                AlertInfo.TriggerTime <= end_date
            )
            alert_count = alert_query.count()
            alert_by_level = {}
            for level in ['低', '中', '高', '紧急']:
                alert_by_level[level] = alert_query.filter(AlertInfo.AlertLevel == level).count()
            
            # 生成报告内容
            report_content = {
                'summary': f'{data["report_type"]}摘要',
                'period': report_period,
                'statistics': {
                    'total_data_count': total_count,
                    'avg_noise': round(avg_noise, 2),
                    'max_noise': round(max_noise, 2),
                    'min_noise': round(min_noise, 2),
                    'exceed_count': exceed_count,
                    'exceed_rate': round(exceed_rate, 2),
                    'alert_count': alert_count,
                    'alert_by_level': alert_by_level
                },
                'region_statistics': region_statistics,
                'recommendations': []
            }
            
            # 生成建议
            if exceed_rate > 20:
                report_content['recommendations'].append('超标率较高，建议加强监测和治理')
            if alert_by_level.get('紧急', 0) > 0:
                report_content['recommendations'].append('存在紧急告警，需要立即处理')
            if avg_noise > 65:
                report_content['recommendations'].append('平均噪音值偏高，建议采取降噪措施')
            
            # 创建报告记录
            report = Report(
                ReportType=data['report_type'],
                ReportPeriod=report_period,
                GeneratedBy=data['generated_by'],
                Content=json.dumps(report_content, ensure_ascii=False),
                IsPublic=data.get('is_public', 0)
            )
            
            session.add(report)
            session.flush()  # 刷新以获取ReportID
            
            return jsonify({
                'status': 'success',
                'message': '报告生成成功',
                'report_id': report.ReportID,
                'report_period': report_period
            }), 201
    except Exception as e:
        app.logger.error(f'报告生成失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'报告生成失败: {str(e)}'}), 500


@app.route('/api/reports', methods=['GET'])
@log_request_time
def get_reports():
    """获取报告列表（支持分页）"""
    try:
        report_type = request.args.get('type')
        page, per_page = get_pagination_params()
        offset = (page - 1) * per_page
        
        with get_db_session() as session:
            query = session.query(Report)
            
            if report_type:
                query = query.filter(Report.ReportType == report_type)
            
            # 总数查询
            total = query.count()
            
            # 数据查询（分页）
            reports = query.order_by(Report.GeneratedAt.desc()).offset(offset).limit(per_page).all()
            
            result = [report.to_dict() for report in reports]
            
            return jsonify({
                'status': 'success',
                'reports': result,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }), 200
    except Exception as e:
        app.logger.error(f'查询报告失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'查询报告失败: {str(e)}'}), 500


@app.route('/api/reports/<int:report_id>', methods=['DELETE'])
@log_request_time
def delete_report(report_id):
    """删除报告"""
    try:
        with get_db_session() as session:
            report = session.query(Report).filter(Report.ReportID == report_id).first()
            
            if not report:
                return jsonify({'status': 'error', 'message': '报告不存在'}), 404
            
            # 如果报告有文件，可以选择删除文件（这里只删除数据库记录）
            # 如果需要删除文件，可以添加文件删除逻辑
            
            session.delete(report)
            session.commit()
            
            return jsonify({
                'status': 'success',
                'message': '报告删除成功'
            }), 200
    except Exception as e:
        app.logger.error(f'删除报告失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'删除报告失败: {str(e)}'}), 500


@app.route('/api/dashboard/stats', methods=['GET'])
@cache.cached(timeout=60)  # 缓存60秒
@log_request_time
def get_dashboard_stats():
    """获取仪表板统计数据"""
    try:
        with get_db_session() as session:
            # 总设备数
            total_devices = session.query(Sensor).count()
            
            # 在线设备数
            online_devices = session.query(Sensor).filter_by(Status='在线').count()
            
            # 今日数据量
            today_start = datetime.now().replace(hour=0, minute=0, second=0)
            today_data_count = session.query(RealtimeData).filter(RealtimeData.Timestamp >= today_start).count()
            
            # 未处理告警数
            pending_alerts = session.query(AlertInfo).filter_by(AlertStatus='未处理').count()
            
            # 区域统计
            region_stats = session.query(
                MonitoringPoint.PointType,
                func.count(MonitoringPoint.PointID).label('count')
            ).group_by(MonitoringPoint.PointType).all()
            
            # 最近告警
            recent_alerts = session.query(AlertInfo).order_by(AlertInfo.TriggerTime.desc()).limit(5).all()
            alerts_list = [alert.to_dict() for alert in recent_alerts]
            
            return jsonify({
                'status': 'success',
                'stats': {
                    'total_devices': total_devices,
                    'online_devices': online_devices,
                    'online_rate': round(online_devices / total_devices * 100, 1) if total_devices > 0 else 0,
                    'today_data_count': today_data_count,
                    'pending_alerts': pending_alerts,
                    'regions_by_type': {stat.PointType: stat.count for stat in region_stats}
                },
                'recent_alerts': alerts_list
            }), 200
    except Exception as e:
        app.logger.error(f'获取仪表板数据失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'获取仪表板数据失败: {str(e)}'}), 500


@app.route('/api/map/data', methods=['GET'])
@cache.cached(timeout=120)  # 缓存2分钟
@log_request_time
def get_map_data():
    """获取地图展示数据"""
    try:
        with get_db_session() as session:
            # 获取所有设备及其位置
            sensors = session.query(Sensor).all()
            
            device_points = []
            for sensor in sensors:
                point = session.query(MonitoringPoint).filter_by(PointID=sensor.PointID).first()
                if point and point.Longitude and point.Latitude:
                    # 获取设备最新数据
                    recent_data = session.query(RealtimeData).filter_by(SensorID=sensor.SensorID)\
                        .order_by(RealtimeData.Timestamp.desc()).first()
                    
                    hour = datetime.now().hour
                    threshold = point.NoiseThresholdDay if 6 <= hour < 22 else point.NoiseThresholdNight
                    is_exceeded = recent_data.NoiseValue > threshold if recent_data else False
                    
                    device_points.append({
                        'device_id': sensor.SensorID,
                        'device_status': sensor.Status,
                        'coordinates': [point.Longitude, point.Latitude],
                        'point_id': point.PointID,
                        'point_name': point.PointName,
                        'recent_noise': recent_data.NoiseValue if recent_data else None,
                        'is_exceeded': is_exceeded
                    })
            
            # 获取区域边界数据（这里简化处理，实际项目需要区域边界坐标）
            points = session.query(MonitoringPoint).all()
            region_polygons = []
            
            for point in points:
                # 这里应该从数据库或其他数据源获取区域边界坐标
                # 简化示例：使用设备位置计算中心点
                point_devices = [d for d in device_points if d.get('point_id') == point.PointID]
                
                if point_devices and point.Longitude and point.Latitude:
                    # 计算区域噪音平均值
                    point_noise_data = session.query(RealtimeData).filter_by(PointID=point.PointID)\
                        .order_by(RealtimeData.Timestamp.desc()).limit(10).all()
                    
                    avg_noise = sum(d.NoiseValue for d in point_noise_data) / len(point_noise_data) if point_noise_data else 0
                    
                    region_polygons.append({
                        'point_id': point.PointID,
                        'point_name': point.PointName,
                        'region_type': point.PointType,
                        'center': [point.Longitude, point.Latitude],
                        'avg_noise': round(avg_noise, 1),
                        'noise_level': calculate_noise_level(avg_noise, point.PointType),
                        'device_count': len(point_devices)
                    })
            
            return jsonify({
                'status': 'success',
                'devices': device_points,
                'regions': region_polygons
            }), 200
    except Exception as e:
        app.logger.error(f'获取地图数据失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'获取地图数据失败: {str(e)}'}), 500


@app.route('/api/data-import', methods=['POST'])
@log_request_time
def import_data():
    """批量导入数据"""
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': '没有上传文件'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '没有选择文件'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': '不支持的文件类型'}), 400
    
    try:
        # 根据文件类型处理
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            return jsonify({'status': 'error', 'message': '不支持的文件格式'}), 400
        
        # 处理导入的数据
        imported_count = 0
        with get_db_session() as session:
            for _, row in df.iterrows():
                try:
                    # 这里根据CSV列名处理数据，需要根据实际CSV结构调整
                    realtime_data = RealtimeData(
                        NoiseValue=float(row.get('noise_value', 0)),
                        SensorID=str(row.get('sensor_id', '')),
                        PointID=int(row.get('point_id', 0)),
                        Timestamp=pd.to_datetime(row.get('timestamp', datetime.now()))
                    )
                    session.add(realtime_data)
                    imported_count += 1
                except Exception as e:
                    app.logger.warning(f"导入数据行时出错: {e}")
                    continue
            
            session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'成功导入 {imported_count} 条数据',
            'imported_count': imported_count
        }), 200
    except Exception as e:
        app.logger.error(f'导入失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'导入失败: {str(e)}'}), 500


# ==================== 实时监控和数据分析 ====================

# 初始化智能模拟器
simulator = SmartNoiseSimulator()

# 实时数据生成标志
realtime_generation_active = False
realtime_thread = None

# 存储每个传感器的上次噪音值和时间戳（用于平滑波动）
sensor_last_values = {}  # {sensor_id: {'value': float, 'timestamp': datetime}}


@app.route('/api/realtime/stream', methods=['GET'])
def realtime_stream():
    """实时数据流（Server-Sent Events）- 实时采集并推送传感器数据"""
    def generate():
        """生成实时数据流"""
        with get_db_session() as session:
            # 获取所有在线传感器
            sensors = session.query(Sensor).filter_by(Status='在线').all()
            
            if not sensors:
                yield f"data: {json.dumps({'status': 'error', 'message': '没有在线传感器'})}\n\n"
                return
            
            # 获取传感器信息
            sensors_info = []
            for sensor in sensors:
                point = sensor.monitoring_point
                if point:
                    sensors_info.append({
                        'sensor_id': sensor.SensorID,
                        'sensor_name': sensor.SensorName,
                        'point_id': point.PointID,
                        'point_name': point.PointName,
                        'point_code': point.PointCode,
                        'point_type': point.PointType,
                        'location': {'lng': point.Longitude, 'lat': point.Latitude}
                    })
        
        # 持续生成实时数据
        stream_last_values = {}  # 用于流式传输的上次值
        while True:
            try:
                realtime_data = []
                current_time = datetime.now()
                
                for sensor_info in sensors_info:
                    # 获取该传感器的上次值
                    last_data = stream_last_values.get(sensor_info['sensor_id'])
                    previous_value = None
                    time_since_last = None
                    
                    if last_data:
                        previous_value = last_data['value']
                        time_since_last = (current_time - last_data['timestamp']).total_seconds()
                    
                    # 生成实时数据（支持平滑波动）
                    noise_data = simulator.generate_realistic_noise_data(
                        region_type=sensor_info['point_type'],
                        time=current_time,
                        location=sensor_info.get('location'),
                        device_status='在线',
                        previous_value=previous_value,
                        time_since_last=time_since_last
                    )
                    
                    # 更新上次值
                    stream_last_values[sensor_info['sensor_id']] = {
                        'value': noise_data['noise_value'],
                        'timestamp': current_time
                    }
                    
                    # 保存到数据库
                    with get_db_session() as session:
                        # 获取传感器和监测点
                        sensor = session.query(Sensor).filter_by(SensorID=sensor_info['sensor_id']).first()
                        point = session.query(MonitoringPoint).filter_by(PointID=sensor_info['point_id']).first()
                        
                        if sensor and point:
                            # 创建实时数据记录
                            realtime_record = RealtimeData(
                                NoiseValue=noise_data['noise_value'],
                                Timestamp=noise_data['timestamp'],
                                FrequencySpectrum=json.dumps(noise_data['frequency_analysis']),
                                DataQuality=noise_data['data_quality'],
                                Temperature=noise_data.get('temperature'),
                                Humidity=noise_data.get('humidity'),
                                WindSpeed=noise_data.get('wind_speed'),
                                WeatherCondition=noise_data.get('weather', 'normal'),
                                SensorID=sensor.SensorID,
                                PointID=point.PointID
                            )
                            session.add(realtime_record)
                            session.flush()
                            
                            # 检查告警
                            alert = check_and_generate_alert(realtime_record, session)
                            
                            # 获取告警信息（如果有）
                            alert_dict = None
                            if alert:
                                alert_dict = alert.to_dict()
                            
                            realtime_data.append({
                                'sensor_id': sensor_info['sensor_id'],
                                'device_id': sensor_info['sensor_id'],  # 添加device_id字段，兼容前端
                                'sensor_name': sensor_info['sensor_name'],
                                'point_id': sensor_info['point_id'],
                                'point_name': sensor_info['point_name'],
                                'point_code': sensor_info['point_code'],
                                'noise_value': noise_data['noise_value'],
                                'timestamp': noise_data['timestamp'].isoformat(),
                                'data_quality': noise_data['data_quality'],
                                'is_exceeded': realtime_record.is_exceeded,
                                'alert': alert_dict
                            })
                
                # 发送数据
                yield f"data: {json.dumps({'status': 'success', 'data': realtime_data, 'timestamp': current_time.isoformat()})}\n\n"
                
                # 等待5秒后生成下一批数据
                sleep(5)
                
            except Exception as e:
                app.logger.error(f'实时数据生成错误: {str(e)}')
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
                sleep(5)
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/api/analysis/trend', methods=['GET'])
@log_request_time
def analyze_trend_simple():
    """趋势分析 - 快速分析接口"""
    try:
        point_id = request.args.get('point_id', type=int)
        sensor_id = request.args.get('sensor_id', type=str)
        days = request.args.get('days', 7, type=int)
        
        start_time = datetime.now() - timedelta(days=days)
        
        with get_db_session() as session:
            query = session.query(RealtimeData).filter(RealtimeData.Timestamp >= start_time)
            
            if point_id:
                query = query.filter(RealtimeData.PointID == point_id)
            if sensor_id:
                query = query.filter(RealtimeData.SensorID == sensor_id)
            
            data = query.order_by(RealtimeData.Timestamp).all()
            
            if not data:
                return jsonify({
                    'status': 'success',
                    'trend': [],
                    'summary': {}
                }), 200
            
            # 按小时聚合
            hourly_data = {}
            for record in data:
                hour_key = record.Timestamp.replace(minute=0, second=0, microsecond=0)
                if hour_key not in hourly_data:
                    hourly_data[hour_key] = []
                hourly_data[hour_key].append(record.NoiseValue)
            
            # 计算每小时平均值
            trend_data = []
            for hour, values in sorted(hourly_data.items()):
                trend_data.append({
                    'timestamp': hour.isoformat(),
                    'avg_noise': round(sum(values) / len(values), 1),
                    'max_noise': round(max(values), 1),
                    'min_noise': round(min(values), 1),
                    'count': len(values)
                })
            
            # 计算统计摘要
            all_values = [d.NoiseValue for d in data]
            summary = {
                'avg_noise': round(sum(all_values) / len(all_values), 1),
                'max_noise': round(max(all_values), 1),
                'min_noise': round(min(all_values), 1),
                'total_count': len(data),
                'exceeded_count': sum(1 for d in data if d.is_exceeded),
                'exceeded_rate': round(sum(1 for d in data if d.is_exceeded) / len(data) * 100, 2) if data else 0
            }
            
            return jsonify({
                'status': 'success',
                'trend': trend_data,
                'summary': summary
            }), 200
            
    except Exception as e:
        app.logger.error(f'趋势分析失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'分析失败: {str(e)}'}), 500


@app.route('/api/analysis/compare', methods=['GET'])
@log_request_time
def analyze_compare():
    """对比分析（区域间、时间段间）"""
    try:
        region_ids = request.args.get('region_ids', '').split(',')
        region_ids = [int(r) for r in region_ids if r.strip()]
        
        days = request.args.get('days', 7, type=int)
        start_time = datetime.now() - timedelta(days=days)
        
        with get_db_session() as session:
            if not region_ids:
                # 获取所有区域
                regions = session.query(MonitoringPoint).all()
                region_ids = [r.PointID for r in regions]
            
            comparison_data = []
            
            for region_id in region_ids:
                region = session.query(MonitoringPoint).filter_by(PointID=region_id).first()
                if not region:
                    continue
                
                # 查询该区域的数据
                data = session.query(RealtimeData).filter(
                    RealtimeData.PointID == region_id,
                    RealtimeData.Timestamp >= start_time
                ).all()
                
                if not data:
                    continue
                
                values = [d.NoiseValue for d in data]
                exceeded_count = sum(1 for d in data if d.is_exceeded)
                
                comparison_data.append({
                    'region_id': region_id,
                    'region_name': region.PointName,
                    'region_type': region.PointType,
                    'avg_noise': round(sum(values) / len(values), 1),
                    'max_noise': round(max(values), 1),
                    'min_noise': round(min(values), 1),
                    'exceeded_count': exceeded_count,
                    'exceeded_rate': round(exceeded_count / len(values) * 100, 2),
                    'data_count': len(values),
                    'threshold_day': region.NoiseThresholdDay,
                    'threshold_night': region.NoiseThresholdNight
                })
            
            # 排序（按平均噪音值）
            comparison_data.sort(key=lambda x: x['avg_noise'], reverse=True)
            
            return jsonify({
                'status': 'success',
                'comparison': comparison_data,
                'period': {
                    'start': start_time.isoformat(),
                    'end': datetime.now().isoformat(),
                    'days': days
                }
            }), 200
            
    except Exception as e:
        app.logger.error(f'对比分析失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'分析失败: {str(e)}'}), 500


@app.route('/api/analysis/hourly-pattern', methods=['GET'])
@log_request_time
def analyze_hourly_pattern():
    """24小时模式分析"""
    try:
        region_id = request.args.get('region_id', type=int)
        device_id = request.args.get('device_id', type=str)
        days = request.args.get('days', 30, type=int)
        
        start_time = datetime.now() - timedelta(days=days)
        
        with get_db_session() as session:
            query = session.query(RealtimeData).filter(RealtimeData.Timestamp >= start_time)
            
            if region_id:
                query = query.filter(RealtimeData.PointID == region_id)
            if device_id:
                query = query.filter(RealtimeData.SensorID == device_id)
            
            data = query.all()
            
            if not data:
                return jsonify({
                    'status': 'success',
                    'pattern': []
                }), 200
            
            # 按小时分组
            hourly_stats = {}
            for record in data:
                hour = record.Timestamp.hour
                if hour not in hourly_stats:
                    hourly_stats[hour] = []
                hourly_stats[hour].append(record.NoiseValue)
            
            # 计算每小时统计
            pattern_data = []
            for hour in range(24):
                if hour in hourly_stats:
                    values = hourly_stats[hour]
                    pattern_data.append({
                        'hour': hour,
                        'avg_noise': round(sum(values) / len(values), 1),
                        'max_noise': round(max(values), 1),
                        'min_noise': round(min(values), 1),
                        'count': len(values)
                    })
                else:
                    pattern_data.append({
                        'hour': hour,
                        'avg_noise': 0,
                        'max_noise': 0,
                        'min_noise': 0,
                        'count': 0
                    })
            
            return jsonify({
                'status': 'success',
                'pattern': pattern_data,
                'period_days': days
            }), 200
            
    except Exception as e:
        app.logger.error(f'小时模式分析失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'分析失败: {str(e)}'}), 500


@app.route('/api/analysis/correlation', methods=['GET'])
@log_request_time
def analyze_correlation():
    """相关性分析（噪音与时间、区域类型等）"""
    try:
        days = request.args.get('days', 30, type=int)
        start_time = datetime.now() - timedelta(days=days)
        
        with get_db_session() as session:
            # 获取数据
            data = session.query(RealtimeData, MonitoringPoint).join(
                MonitoringPoint, RealtimeData.PointID == MonitoringPoint.PointID
            ).filter(RealtimeData.Timestamp >= start_time).all()
            
            if not data:
                return jsonify({
                    'status': 'success',
                    'correlations': {}
                }), 200
            
            # 按区域类型分析
            region_type_stats = {}
            for noise_data, region in data:
                region_type = region.PointType
                if region_type not in region_type_stats:
                    region_type_stats[region_type] = []
                region_type_stats[region_type].append(noise_data.NoiseValue)
            
            # 计算各区域类型的统计
            region_type_analysis = {}
            for region_type, values in region_type_stats.items():
                region_type_analysis[region_type] = {
                    'avg_noise': round(sum(values) / len(values), 1),
                    'max_noise': round(max(values), 1),
                    'min_noise': round(min(values), 1),
                    'count': len(values)
                }
            
            # 按工作日/周末分析
            weekday_values = []
            weekend_values = []
            for noise_data, region in data:
                if noise_data.Timestamp.weekday() < 5:
                    weekday_values.append(noise_data.NoiseValue)
                else:
                    weekend_values.append(noise_data.NoiseValue)
            
            weekday_weekend_analysis = {
                'weekday': {
                    'avg_noise': round(sum(weekday_values) / len(weekday_values), 1) if weekday_values else 0,
                    'count': len(weekday_values)
                },
                'weekend': {
                    'avg_noise': round(sum(weekend_values) / len(weekend_values), 1) if weekend_values else 0,
                    'count': len(weekend_values)
                }
            }
            
            # 按时间段分析（白天/夜间）
            day_values = []
            night_values = []
            for noise_data, region in data:
                hour = noise_data.Timestamp.hour
                if 6 <= hour < 22:
                    day_values.append(noise_data.NoiseValue)
                else:
                    night_values.append(noise_data.NoiseValue)
            
            day_night_analysis = {
                'day': {
                    'avg_noise': round(sum(day_values) / len(day_values), 1) if day_values else 0,
                    'count': len(day_values)
                },
                'night': {
                    'avg_noise': round(sum(night_values) / len(night_values), 1) if night_values else 0,
                    'count': len(night_values)
                }
            }
            
            return jsonify({
                'status': 'success',
                'correlations': {
                    'by_region_type': region_type_analysis,
                    'weekday_vs_weekend': weekday_weekend_analysis,
                    'day_vs_night': day_night_analysis
                }
            }), 200
            
    except Exception as e:
        app.logger.error(f'相关性分析失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'分析失败: {str(e)}'}), 500


@app.route('/api/realtime/generate', methods=['POST'])
@log_request_time
def start_realtime_generation():
    """启动实时数据生成（后台任务）- 自动采集传感器数据"""
    global realtime_generation_active, realtime_thread
    
    if realtime_generation_active:
        return jsonify({
            'status': 'info',
            'message': '实时数据生成已在运行中'
        }), 200
    
    def generate_realtime_data():
        """后台生成实时数据 - 每30秒采集一次（支持平滑波动）"""
        global realtime_generation_active, sensor_last_values
        realtime_generation_active = True
        
        while realtime_generation_active:
            try:
                current_time = datetime.now()
                
                with get_db_session() as session:
                    # 获取所有在线传感器
                    sensors = session.query(Sensor).filter_by(Status='在线').all()
                    
                    if not sensors:
                        app.logger.warning('没有在线的传感器，跳过本次数据生成')
                        sleep(60)
                        continue
                    
                    app.logger.info(f'开始生成实时数据，传感器数量: {len(sensors)}')
                    generated_count = 0
                    
                    for sensor in sensors:
                        point = sensor.monitoring_point
                        if not point:
                            app.logger.warning(f'传感器 {sensor.SensorID} 没有关联的监测点，跳过')
                            continue
                        
                        # 获取该传感器的上次值
                        last_data = sensor_last_values.get(sensor.SensorID)
                        previous_value = None
                        time_since_last = None
                        
                        if last_data:
                            previous_value = last_data['value']
                            time_since_last = (current_time - last_data['timestamp']).total_seconds()
                        else:
                            # 如果没有历史数据，尝试从数据库获取最近一条记录
                            last_record = session.query(RealtimeData).filter_by(
                                SensorID=sensor.SensorID
                            ).order_by(RealtimeData.Timestamp.desc()).first()
                            
                            if last_record:
                                previous_value = last_record.NoiseValue
                                time_since_last = (current_time - last_record.Timestamp).total_seconds()
                        
                        # 生成实时数据（支持基于历史数据的平滑波动）
                        noise_data = simulator.generate_realistic_noise_data(
                            region_type=point.PointType,
                            time=current_time,
                            location={'lng': point.Longitude, 'lat': point.Latitude},
                            device_status=sensor.Status,
                            previous_value=previous_value,
                            time_since_last=time_since_last
                        )
                        
                        # 保存到数据库
                        realtime_record = RealtimeData(
                            NoiseValue=noise_data['noise_value'],
                            Timestamp=noise_data['timestamp'],
                            FrequencySpectrum=json.dumps(noise_data['frequency_analysis']),
                            DataQuality=noise_data['data_quality'],
                            Temperature=noise_data.get('temperature'),
                            Humidity=noise_data.get('humidity'),
                            WindSpeed=noise_data.get('wind_speed'),
                            WeatherCondition=noise_data.get('weather', 'normal'),
                            SensorID=sensor.SensorID,
                            PointID=point.PointID
                        )
                        session.add(realtime_record)
                        session.flush()
                        
                        # 更新传感器的上次值
                        sensor_last_values[sensor.SensorID] = {
                            'value': noise_data['noise_value'],
                            'timestamp': current_time
                        }
                        
                        # 检查告警
                        check_and_generate_alert(realtime_record, session)
                        generated_count += 1
                    
                    # 提交所有数据
                    session.commit()
                    app.logger.info(f'实时数据生成完成，共生成 {generated_count} 条数据')
                
                # 每小时记录一次汇总数据（用于历史分析）
                current_minute = current_time.minute
                current_second = current_time.second
                if current_minute == 0 and current_second < 30:
                    # 每小时整点记录一次汇总数据
                    try:
                        with get_db_session() as session:
                            # 获取所有传感器的最近一小时的平均值
                            one_hour_ago = current_time - timedelta(hours=1)
                            sensors_for_hourly = session.query(Sensor).filter_by(Status='在线').all()
                            for sensor in sensors_for_hourly:
                                # 计算该传感器最近一小时的平均值
                                hourly_data = session.query(
                                    func.avg(RealtimeData.NoiseValue).label('avg_noise'),
                                    func.max(RealtimeData.NoiseValue).label('max_noise'),
                                    func.min(RealtimeData.NoiseValue).label('min_noise'),
                                    func.count(RealtimeData.DataID).label('data_count')
                                ).filter(
                                    RealtimeData.SensorID == sensor.SensorID,
                                    RealtimeData.Timestamp >= one_hour_ago,
                                    RealtimeData.Timestamp <= current_time
                                ).first()
                                
                                if hourly_data and hourly_data.data_count > 0:
                                    # 记录每小时汇总数据（可以保存到日志或单独的表）
                                    app.logger.info(
                                        f'每小时汇总 - 传感器 {sensor.SensorID}: '
                                        f'平均={hourly_data.avg_noise:.2f}dB, '
                                        f'最大={hourly_data.max_noise:.2f}dB, '
                                        f'最小={hourly_data.min_noise:.2f}dB, '
                                        f'数据点={hourly_data.data_count}'
                                    )
                    except Exception as e:
                        app.logger.error(f'每小时汇总记录失败: {str(e)}')
                
                # 每30秒生成一次（实时采集）
                sleep(30)
                
            except Exception as e:
                app.logger.error(f'后台实时数据生成错误: {str(e)}', exc_info=True)
                sleep(60)
    
    realtime_thread = threading.Thread(target=generate_realtime_data, daemon=True)
    realtime_thread.start()
    
    return jsonify({
        'status': 'success',
        'message': '实时数据采集已启动，每30秒采集一次'
    }), 200


@app.route('/api/realtime/start', methods=['POST'])
@log_request_time
def start_realtime_generation_endpoint():
    """启动实时数据生成（API端点）"""
    return start_realtime_generation()


@app.route('/api/realtime/stop', methods=['POST'])
@log_request_time
def stop_realtime_generation():
    """停止实时数据生成"""
    global realtime_generation_active
    realtime_generation_active = False
    
    return jsonify({
        'status': 'success',
        'message': '实时数据生成已停止'
    }), 200


@app.route('/api/realtime/status', methods=['GET'])
@log_request_time
def get_realtime_generation_status():
    """获取实时数据生成状态"""
    global realtime_generation_active, realtime_thread
    
    # 检查线程是否还在运行
    thread_alive = realtime_thread is not None and realtime_thread.is_alive()
    
    # 检查最近是否有数据生成
    recent_data_count = 0
    try:
        with get_db_session() as session:
            # 检查最近1分钟内的数据
            one_minute_ago = datetime.now() - timedelta(minutes=1)
            recent_data_count = session.query(RealtimeData).filter(
                RealtimeData.Timestamp >= one_minute_ago
            ).count()
            
            # 获取在线传感器数量
            online_sensors = session.query(Sensor).filter_by(Status='在线').count()
    except Exception as e:
        app.logger.error(f'获取实时数据生成状态失败: {str(e)}')
        online_sensors = 0
    
    return jsonify({
        'status': 'success',
        'data': {
            'is_running': realtime_generation_active and thread_alive,
            'thread_alive': thread_alive,
            'recent_data_count': recent_data_count,
            'online_sensors': online_sensors,
            'generation_interval': 30  # 秒
        }
    }), 200


# ==================== 数据分析API ====================

@app.route('/api/analysis/trend', methods=['POST'])
@validate_json('analysis_type', 'start_date', 'end_date')
@log_request_time
def analyze_trend():
    """趋势分析 - 分析指定时间段的噪音趋势"""
    data = request.get_json()
    
    try:
        with get_db_session() as session:
            start_date = datetime.fromisoformat(data['start_date']) if isinstance(data['start_date'], str) else data['start_date']
            end_date = datetime.fromisoformat(data['end_date']) if isinstance(data['end_date'], str) else data['end_date']
            point_id = data.get('point_id')
            sensor_id = data.get('sensor_id')
            analysis_type = data['analysis_type']
            
            # 查询实时数据
            query = session.query(RealtimeData).filter(
                RealtimeData.Timestamp >= start_date,
                RealtimeData.Timestamp <= end_date
            )
            
            if point_id:
                query = query.filter(RealtimeData.PointID == point_id)
            if sensor_id:
                query = query.filter(RealtimeData.SensorID == sensor_id)
            
            data_list = query.order_by(RealtimeData.Timestamp).all()
            
            if not data_list:
                return jsonify({
                    'status': 'error',
                    'message': '指定时间段内无数据'
                }), 404
            
            # 计算统计指标
            noise_values = [d.NoiseValue for d in data_list]
            avg_noise = sum(noise_values) / len(noise_values)
            max_noise = max(noise_values)
            min_noise = min(noise_values)
            
            # 计算超标次数和超标率
            exceed_count = sum(1 for d in data_list if d.is_exceeded)
            exceed_rate = (exceed_count / len(data_list)) * 100 if data_list else 0
            
            # 计算趋势方向
            if len(noise_values) >= 2:
                first_half = noise_values[:len(noise_values)//2]
                second_half = noise_values[len(noise_values)//2:]
                first_avg = sum(first_half) / len(first_half)
                second_avg = sum(second_half) / len(second_half)
                
                diff = second_avg - first_avg
                if abs(diff) < 1:
                    trend_direction = '平稳'
                elif diff > 0:
                    trend_direction = '上升'
                else:
                    trend_direction = '下降'
                
                # 计算趋势变化率（dB/周期）
                days = (end_date - start_date).days
                trend_rate = (diff / days) if days > 0 else 0
            else:
                trend_direction = '数据不足'
                trend_rate = 0
            
            # 分析高峰时段
            hour_noise = {}
            for d in data_list:
                hour = d.Timestamp.hour
                if hour not in hour_noise:
                    hour_noise[hour] = []
                hour_noise[hour].append(d.NoiseValue)
            
            peak_hours = sorted(
                [(h, sum(vals)/len(vals)) for h, vals in hour_noise.items()],
                key=lambda x: x[1],
                reverse=True
            )[:3]  # 取前3个高峰时段
            
            # 保存分析结果到数据库
            analysis_result = TrendAnalysis(
                AnalysisType=analysis_type,
                AnalysisPeriod=f"{start_date.date()} 至 {end_date.date()}",
                StartDate=start_date,
                EndDate=end_date,
                PointID=point_id,
                SensorID=sensor_id,
                AverageNoise=round(avg_noise, 2),
                MaxNoise=round(max_noise, 2),
                MinNoise=round(min_noise, 2),
                ExceedCount=exceed_count,
                ExceedRate=round(exceed_rate, 2),
                TrendDirection=trend_direction,
                TrendRate=round(trend_rate, 4),
                PeakHours=json.dumps(peak_hours),
                AnalysisResult=json.dumps({
                    'total_data_points': len(data_list),
                    'hourly_distribution': {h: len(vals) for h, vals in hour_noise.items()}
                })
            )
            session.add(analysis_result)
            session.flush()
            
            return jsonify({
                'status': 'success',
                'analysis_id': analysis_result.AnalysisID,
                'data': {
                    'average_noise': round(avg_noise, 2),
                    'max_noise': round(max_noise, 2),
                    'min_noise': round(min_noise, 2),
                    'exceed_count': exceed_count,
                    'exceed_rate': round(exceed_rate, 2),
                    'trend_direction': trend_direction,
                    'trend_rate': round(trend_rate, 4),
                    'peak_hours': peak_hours,
                    'total_data_points': len(data_list)
                }
            }), 200
            
    except Exception as e:
        app.logger.error(f'趋势分析失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'分析失败: {str(e)}'}), 500


@app.route('/api/analysis/pattern', methods=['POST'])
@validate_json('pattern_type', 'start_date', 'end_date')
@log_request_time
def recognize_pattern():
    """模式识别 - 识别噪音数据中的模式"""
    data = request.get_json()
    
    try:
        with get_db_session() as session:
            start_date = datetime.fromisoformat(data['start_date']) if isinstance(data['start_date'], str) else data['start_date']
            end_date = datetime.fromisoformat(data['end_date']) if isinstance(data['end_date'], str) else data['end_date']
            point_id = data.get('point_id')
            sensor_id = data.get('sensor_id')
            pattern_type = data['pattern_type']
            
            # 查询实时数据
            query = session.query(RealtimeData).filter(
                RealtimeData.Timestamp >= start_date,
                RealtimeData.Timestamp <= end_date
            )
            
            if point_id:
                query = query.filter(RealtimeData.PointID == point_id)
            if sensor_id:
                query = query.filter(RealtimeData.SensorID == sensor_id)
            
            data_list = query.order_by(RealtimeData.Timestamp).all()
            
            if not data_list:
                return jsonify({
                    'status': 'error',
                    'message': '指定时间段内无数据'
                }), 404
            
            # 按小时分组分析
            hourly_data = {}
            for d in data_list:
                hour = d.Timestamp.hour
                weekday = d.Timestamp.weekday()  # 0=Monday, 6=Sunday
                
                if hour not in hourly_data:
                    hourly_data[hour] = {'weekday': [], 'weekend': []}
                
                if weekday < 5:  # 工作日
                    hourly_data[hour]['weekday'].append(d.NoiseValue)
                else:  # 周末
                    hourly_data[hour]['weekend'].append(d.NoiseValue)
            
            # 识别模式特征
            pattern_data = {}
            characteristics = {}
            
            if pattern_type == '工作日模式':
                for hour, values in hourly_data.items():
                    if values['weekday']:
                        pattern_data[hour] = {
                            'avg': sum(values['weekday']) / len(values['weekday']),
                            'count': len(values['weekday'])
                        }
                characteristics = {
                    'peak_hours': sorted(
                        [(h, v['avg']) for h, v in pattern_data.items()],
                        key=lambda x: x[1],
                        reverse=True
                    )[:3],
                    'description': '工作日噪音模式'
                }
            elif pattern_type == '周末模式':
                for hour, values in hourly_data.items():
                    if values['weekend']:
                        pattern_data[hour] = {
                            'avg': sum(values['weekend']) / len(values['weekend']),
                            'count': len(values['weekend'])
                        }
                characteristics = {
                    'peak_hours': sorted(
                        [(h, v['avg']) for h, v in pattern_data.items()],
                        key=lambda x: x[1],
                        reverse=True
                    )[:3],
                    'description': '周末噪音模式'
                }
            
            # 计算置信度（基于数据量）
            total_points = len(data_list)
            confidence = min(1.0, total_points / 1000)  # 数据越多，置信度越高
            
            # 保存模式识别结果
            pattern = PatternRecognition(
                PatternType=pattern_type,
                PatternName=f"{pattern_type}_{start_date.date()}_{end_date.date()}",
                PatternDescription=characteristics.get('description', ''),
                PointID=point_id,
                SensorID=sensor_id,
                RecognitionPeriod=f"{start_date.date()} 至 {end_date.date()}",
                StartDate=start_date,
                EndDate=end_date,
                PatternData=json.dumps(pattern_data),
                Confidence=round(confidence, 2),
                Characteristics=json.dumps(characteristics)
            )
            session.add(pattern)
            session.flush()
            
            return jsonify({
                'status': 'success',
                'pattern_id': pattern.PatternID,
                'data': {
                    'pattern_type': pattern_type,
                    'pattern_data': pattern_data,
                    'characteristics': characteristics,
                    'confidence': round(confidence, 2),
                    'total_data_points': total_points
                }
            }), 200
            
    except Exception as e:
        app.logger.error(f'模式识别失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'识别失败: {str(e)}'}), 500


@app.route('/api/analysis/trend/<int:analysis_id>', methods=['GET'])
@log_request_time
def get_trend_analysis(analysis_id):
    """获取趋势分析结果"""
    try:
        with get_db_session() as session:
            analysis = session.query(TrendAnalysis).filter_by(AnalysisID=analysis_id).first()
            if not analysis:
                return jsonify({'status': 'error', 'message': '分析结果不存在'}), 404
            
            return jsonify({
                'status': 'success',
                'data': analysis.to_dict()
            }), 200
    except Exception as e:
        app.logger.error(f'获取趋势分析失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'获取失败: {str(e)}'}), 500


@app.route('/api/analysis/pattern/<int:pattern_id>', methods=['GET'])
@log_request_time
def get_pattern_recognition(pattern_id):
    """获取模式识别结果"""
    try:
        with get_db_session() as session:
            pattern = session.query(PatternRecognition).filter_by(PatternID=pattern_id).first()
            if not pattern:
                return jsonify({'status': 'error', 'message': '模式识别结果不存在'}), 404
            
            return jsonify({
                'status': 'success',
                'data': pattern.to_dict()
            }), 200
    except Exception as e:
        app.logger.error(f'获取模式识别失败: {str(e)}')
        return jsonify({'status': 'error', 'message': f'获取失败: {str(e)}'}), 500


# ==================== 主程序入口 ====================

if __name__ == '__main__':
    # 确保上传目录存在
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # 配置日志
    setup_logging(app)
    
    # 创建数据库表（如果不存在）
    try:
        Base.metadata.create_all(engine)
        app.logger.info("数据库表已创建/验证")
    except Exception as e:
        app.logger.error(f"数据库表创建失败: {e}")
    
    # 初始化数据库（如果为空）
    try:
        with get_db_session() as session:
            user_count = session.query(SystemUser).count()
            if user_count == 0:
                init_database()
                app.logger.info("数据库已初始化")
    except Exception as e:
        app.logger.error(f"数据库初始化失败: {e}")
    
    # 自动启动实时数据生成
    try:
        # 先检查是否有传感器
        with get_db_session() as session:
            sensor_count = session.query(Sensor).count()
            online_sensor_count = session.query(Sensor).filter_by(Status='在线').count()
            
            if sensor_count == 0:
                app.logger.warning("没有传感器数据，请先初始化数据库（运行 init_database.py 或调用初始化接口）")
            elif online_sensor_count == 0:
                app.logger.warning(f"有 {sensor_count} 个传感器，但没有在线的传感器，实时数据生成将不会产生数据")
            else:
                app.logger.info(f"检测到 {online_sensor_count} 个在线传感器，准备启动实时数据生成")
        
        # 启动实时数据生成
        start_realtime_generation()
        app.logger.info("实时数据生成已自动启动，每30秒采集一次")
    except Exception as e:
        app.logger.warning(f"自动启动实时数据生成失败: {e}，可以稍后手动调用 /api/realtime/start")
    
    app.run(host='0.0.0.0', port=5000, debug=True)