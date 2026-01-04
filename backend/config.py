"""配置文件"""
import os
from dotenv import load_dotenv

load_dotenv()  # 加载环境变量


class Config:
    """应用配置类"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    
    # 数据库配置
    DB_TYPE = os.getenv('DB_TYPE', 'sqlite')
    if DB_TYPE == 'mysql':
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', '')}"
            f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}"
            f"/{os.getenv('DB_NAME', 'noise_monitoring')}"
        )
    else:
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///noise_monitoring.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 日志配置
    LOG_DIR = os.getenv('LOG_DIR', 'logs')
    LOG_FILE = os.getenv('LOG_FILE', 'noise_monitoring.log')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10240))
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 10))
    
    # 缓存配置
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', 300))

