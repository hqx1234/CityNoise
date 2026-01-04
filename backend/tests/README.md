# 测试文档

本目录包含噪音监测系统的测试代码。

## 测试结构

```
tests/
├── __init__.py              # 测试包初始化
├── conftest.py              # Pytest 配置和测试固件
├── test_models.py           # 数据库模型测试
├── test_api_auth.py         # 认证API测试
├── test_api_data.py         # 数据API测试
├── test_api_alerts.py       # 告警API测试
├── test_api_regions.py      # 区域API测试
├── test_api_analysis.py     # 分析API测试
├── test_business_logic.py   # 业务逻辑测试
└── test_utils.py            # 工具函数测试
```

## 运行测试

### 安装测试依赖

```bash
pip install -r requirements.txt
```

### 运行所有测试

```bash
# 方式1：使用 pytest
pytest tests/

# 方式2：使用测试脚本
python run_tests.py

# 方式3：运行特定测试文件
pytest tests/test_api_auth.py

# 方式4：运行特定测试类或函数
pytest tests/test_api_auth.py::TestAuthAPI::test_login_success
```

### 运行测试并查看覆盖率

```bash
pytest tests/ --cov=app --cov-report=html
```

覆盖率报告将生成在 `htmlcov/` 目录中。

### 运行测试的详细选项

```bash
# 详细输出
pytest tests/ -v

# 显示打印语句
pytest tests/ -s

# 只运行失败的测试
pytest tests/ --lf

# 运行上次失败的测试并继续
pytest tests/ --ff

# 并行运行测试（需要 pytest-xdist）
pytest tests/ -n auto
```

## 测试类型

### 1. 模型测试 (test_models.py)

测试数据库模型的创建、验证和序列化：
- 城市模型
- 监测点模型
- 传感器模型
- 用户模型
- 实时数据模型
- 告警模型

### 2. API 测试

#### 认证API (test_api_auth.py)
- 用户注册
- 用户登录
- 参数验证

#### 数据API (test_api_data.py)
- 实时数据提交和查询
- 噪音数据查询
- 统计数据获取
- 仪表板数据

#### 告警API (test_api_alerts.py)
- 告警列表查询
- 告警更新
- 告警过滤

#### 区域API (test_api_regions.py)
- 区域列表查询
- 区域设备查询
- 设备列表查询

#### 分析API (test_api_analysis.py)
- 趋势分析
- 对比分析
- 小时模式分析
- 相关性分析

### 3. 业务逻辑测试 (test_business_logic.py)

测试核心业务逻辑：
- 噪音等级计算
- 告警生成逻辑
- 数据验证

### 4. 工具函数测试 (test_utils.py)

测试工具函数：
- 文件类型检查
- 分页参数处理

## 测试固件 (Fixtures)

在 `conftest.py` 中定义了以下测试固件：

- `test_db`: 创建临时测试数据库
- `db_session`: 数据库会话
- `client`: Flask 测试客户端
- `sample_city`: 示例城市
- `sample_monitoring_point`: 示例监测点
- `sample_sensor`: 示例传感器
- `sample_user`: 示例用户
- `admin_user`: 管理员用户
- `sample_realtime_data`: 示例实时数据
- `auth_headers`: 认证头

## 编写新测试

### 测试函数命名

测试函数应以 `test_` 开头：

```python
def test_something():
    """测试描述"""
    assert True
```

### 使用测试固件

```python
def test_example(client, sample_user):
    """使用测试客户端和示例用户"""
    response = client.get('/api/some-endpoint')
    assert response.status_code == 200
```

### 测试API端点

```python
def test_api_endpoint(client, db_session):
    """测试API端点"""
    response = client.post('/api/endpoint', json={
        'key': 'value'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
```

### 测试数据库操作

```python
def test_database_operation(db_session, sample_user):
    """测试数据库操作"""
    user = db_session.query(SystemUser).filter_by(Username='testuser').first()
    assert user is not None
    assert user.Username == 'testuser'
```

## 持续集成

可以在 CI/CD 流程中运行测试：

```yaml
# GitHub Actions 示例
- name: Run tests
  run: |
    cd backend
    pip install -r requirements.txt
    pytest tests/ --cov=app --cov-report=xml
```

## 注意事项

1. 测试使用临时数据库，不会影响生产数据
2. 每个测试函数都是独立的，使用独立的数据库会话
3. 测试完成后会自动清理临时文件
4. 确保测试环境安装了所有依赖

## 故障排除

### 导入错误

如果遇到导入错误，确保：
1. 已安装所有依赖：`pip install -r requirements.txt`
2. Python 路径正确
3. 在 `backend/` 目录下运行测试

### 数据库错误

如果遇到数据库相关错误：
1. 检查 SQLite 是否可用
2. 确保有写入临时文件的权限
3. 检查数据库连接配置

### 测试失败

如果测试失败：
1. 查看详细错误信息：`pytest tests/ -v`
2. 检查测试数据是否正确设置
3. 验证 API 端点是否正常工作
4. 检查数据库模型是否正确

