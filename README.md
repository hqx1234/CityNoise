# CityNoise - 城市噪音污染监测管理平台

> 现代化的城市噪音污染监测与管理平台，提供实时数据监测、可视化分析和智能告警功能 | 同济大学数据库课程设计项目

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.5+-green.svg)](https://vuejs.org/)

## 📋 项目简介

**同济大学数据库课程设计项目**

CityNoise 是一个现代化的城市噪音污染监测与管理平台，提供实时数据监测、可视化分析、告警管理和报告生成等功能。本项目旨在通过先进的技术栈和完整的系统架构，实现对城市噪音污染的有效监测和管理，为城市环境治理提供数据支持和决策依据。

## ✨ 功能特性

- 📊 **实时监测** - 实时采集和展示噪音数据
- 🗺️ **地图可视化** - 在地图上直观展示监测点和数据分布
- 📈 **统计分析** - 多维度数据统计和趋势分析
- 🔔 **智能告警** - 自动检测超标情况并发送告警
- 📱 **设备管理** - 完整的监测设备管理功能
- 📄 **报告生成** - 自动生成数据报告和导出
- 🔐 **用户认证** - 安全的用户登录和权限管理
- 📊 **数据可视化** - 使用 ECharts 提供丰富的图表展示
- 🔄 **实时数据流** - 支持实时数据推送和更新

## 🛠️ 技术栈

### 后端
- **Flask** - Python Web 框架
- **SQLAlchemy** - ORM 数据库操作
- **SQLite/MySQL** - 数据库支持
- **Flask-CORS** - 跨域支持
- **Flask-Caching** - 缓存支持
- **Pandas** - 数据处理和分析

### 前端
- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - 类型安全的 JavaScript
- **Element Plus** - Vue 3 UI 组件库
- **Vue Router** - 路由管理
- **Axios** - HTTP 客户端
- **ECharts** - 数据可视化图表库
- **Vite** - 快速的前端构建工具

## 📦 项目结构

```
CityNoise/
├── backend/                 # 后端服务
│   ├── app.py              # Flask 主应用
│   ├── config.py           # 配置文件
│   ├── init_database.py    # 数据库初始化脚本
│   ├── smart_noise_simulator.py  # 智能噪音数据模拟器
│   ├── requirements.txt    # Python 依赖
│   ├── tests/              # 测试文件
│   ├── logs/               # 日志文件
│   └── uploads/            # 文件上传目录
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── api/           # API 接口
│   │   ├── components/    # 组件
│   │   ├── layouts/       # 布局
│   │   ├── router/        # 路由配置
│   │   ├── views/         # 页面视图
│   │   └── main.ts        # 入口文件
│   ├── package.json       # 项目依赖
│   └── vite.config.ts     # Vite 配置
├── API_DOCUMENTATION.md   # API 文档
├── LICENSE                # 许可证
└── README.md              # 本文件
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+
- npm 或 yarn

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/hqx1234/CityNoise.git
cd CityNoise
```

#### 2. 后端设置

```bash
# 进入后端目录
cd backend

# 安装 Python 依赖
pip install -r requirements.txt

# 初始化数据库
python init_database.py

# 启动后端服务
python app.py
```

后端服务将运行在 `http://127.0.0.1:5000`

#### 3. 前端设置

```bash
# 进入前端目录（新终端窗口）
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端应用将运行在 `http://localhost:5174`

### 默认账户

数据库初始化后会创建默认管理员账户：
- 用户名: `admin`
- 密码: `admin123`

**⚠️ 注意：生产环境请务必修改默认密码！**

## 📖 使用说明

### 开发模式

1. 启动后端服务（在 `backend/` 目录）：
   ```bash
   python app.py
   ```

2. 启动前端开发服务器（在 `frontend/` 目录）：
   ```bash
   npm run dev
   ```

前端开发服务器已配置代理，API 请求会自动转发到后端服务。

### 生产部署

1. 构建前端：
   ```bash
   cd frontend
   npm run build
   ```

2. 配置后端服务静态文件路径指向 `frontend/dist`

3. 配置环境变量（如需要）：
   ```bash
   export SECRET_KEY=your-secret-key
   export DB_TYPE=mysql  # 或 sqlite
   export DATABASE_URL=your-database-url
   ```

4. 启动后端服务

## 📚 文档

- [API 文档](API_DOCUMENTATION.md) - 完整的 API 接口文档
- [后端 README](backend/README.md) - 后端详细说明
- [前端 README](frontend/README.md) - 前端详细说明

## 🧪 测试

运行后端测试：

```bash
cd backend
python run_tests.py
```

或使用 pytest：

```bash
pytest tests/
```

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 👥 作者

- **hqx1234** - [GitHub](https://github.com/hqx1234)

## 🙏 致谢

- [Vue.js](https://vuejs.org/)
- [Flask](https://flask.palletsprojects.com/)
- [Element Plus](https://element-plus.org/)
- [ECharts](https://echarts.apache.org/)

## 📧 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 [Issue](https://github.com/hqx1234/CityNoise/issues)
- 发送 Pull Request

---

⭐ 如果这个项目对你有帮助，请给个 Star！
