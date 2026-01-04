# 后端服务

## 项目结构

```
backend/
├── app.py                    # Flask 主应用文件
├── config.py                 # 配置文件
├── requirements.txt          # Python 依赖包
├── logs/                     # 日志文件目录
├── uploads/                  # 文件上传目录
├── init_database.py          # 数据库初始化脚本
├── run_tests.py              # 测试运行脚本
├── pytest.ini                # pytest 配置文件
└── tests/                    # 测试文件目录
    ├── __init__.py
    ├── conftest.py
    ├── test_api_*.py         # API 测试文件
    ├── test_models.py        # 模型测试文件
    ├── test_business_logic.py # 业务逻辑测试
    └── test_utils.py         # 工具函数测试
```

## 环境要求

- Python 3.8+
- pip

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行服务

```bash
python app.py
```

服务默认运行在 `http://127.0.0.1:5000`

## 配置说明

配置文件 `config.py` 支持通过环境变量进行配置：

- `SECRET_KEY`: Flask 密钥
- `UPLOAD_FOLDER`: 文件上传目录（默认：uploads）
- `LOG_DIR`: 日志目录（默认：logs）
- `DB_TYPE`: 数据库类型（sqlite/mysql）
- `DATABASE_URL`: 数据库连接字符串

## API 文档

详细的 API 文档请参考根目录下的 `API_DOCUMENTATION.md`

## 数据库初始化

首次运行前，需要初始化数据库：

```bash
python init_database.py
```

数据库文件（noise_monitoring.db）会在首次运行时自动创建，无需手动创建。

