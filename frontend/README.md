# 前端应用

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API 接口定义
│   ├── assets/           # 静态资源
│   ├── components/       # Vue 组件
│   ├── layouts/          # 布局组件
│   ├── router/           # 路由配置
│   ├── views/            # 页面视图
│   ├── App.vue           # 根组件
│   ├── main.ts           # 入口文件
│   └── style.css         # 全局样式
├── public/               # 公共静态资源
├── index.html            # HTML 模板
├── package.json          # 项目依赖配置
├── vite.config.ts        # Vite 配置
└── tsconfig.json         # TypeScript 配置
```

## 环境要求

- Node.js 16+
- npm 或 yarn

## 安装依赖

```bash
npm install
```

## 开发模式

```bash
npm run dev
```

应用默认运行在 `http://localhost:5174`

## 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist/` 目录

## 预览生产构建

```bash
npm run preview
```

## 技术栈

- Vue 3
- TypeScript
- Element Plus
- Vue Router
- Axios
- ECharts
- Vite

## API 代理配置

开发模式下，API 请求会自动代理到后端服务（`http://127.0.0.1:5000`），配置在 `vite.config.ts` 中。

