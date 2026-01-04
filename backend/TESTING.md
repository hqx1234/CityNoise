# 测试快速指南

## 快速开始

### 1. 安装测试依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 运行所有测试

```bash
# 方式1：使用 pytest
pytest

# 方式2：使用测试脚本
python run_tests.py

# 方式3：运行并查看覆盖率
pytest --cov=app --cov-report=html
```

### 3. 运行特定测试

```bash
# 运行特定测试文件
pytest tests/test_api_auth.py

# 运行特定测试类
pytest tests/test_api_auth.py::TestAuthAPI

# 运行特定测试函数
pytest tests/test_api_auth.py::TestAuthAPI::test_login_success
```

## 测试覆盖

测试套件包括：

- ✅ 数据库模型测试
- ✅ 认证API测试（注册、登录）
- ✅ 数据API测试（实时数据、噪音数据）
- ✅ 告警API测试
- ✅ 区域和设备API测试
- ✅ 分析API测试
- ✅ 业务逻辑测试
- ✅ 工具函数测试

## 测试输出示例

```
tests/test_api_auth.py::TestAuthAPI::test_login_success PASSED
tests/test_api_auth.py::TestAuthAPI::test_register_success PASSED
tests/test_models.py::TestSystemUser::test_user_creation PASSED
...
```

## 查看覆盖率报告

运行覆盖率测试后，打开 `htmlcov/index.html` 查看详细的覆盖率报告。

## 常见问题

### Q: 测试失败，提示数据库错误
A: 确保在 `backend/` 目录下运行测试，测试使用临时数据库，不会影响生产数据。

### Q: 导入错误
A: 确保已安装所有依赖：`pip install -r requirements.txt`

### Q: 如何只运行失败的测试？
A: 使用 `pytest --lf` 或 `pytest --last-failed`

## 持续集成

在 CI/CD 中使用：

```bash
cd backend
pip install -r requirements.txt
pytest --cov=app --cov-report=xml --junitxml=test-results.xml
```

