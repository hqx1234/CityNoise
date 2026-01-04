# GitHub 仓库设置指南

## 如何在 GitHub 上设置仓库描述、网站和主题

### 方法一：通过 GitHub 网页界面设置

1. 访问你的仓库：https://github.com/hqx1234/CityNoise
2. 点击仓库页面右上角的 **⚙️ Settings**（设置）
3. 在左侧菜单中找到 **General**（常规设置）
4. 在 **Repository details**（仓库详情）部分：
   - **Description（描述）**：输入以下内容
     ```
     现代化的城市噪音污染监测与管理平台，提供实时数据监测、可视化分析和智能告警功能 | 同济大学数据库课程设计项目
     ```
   - **Website（网站）**：可以留空或填写项目演示地址
   - **Topics（主题标签）**：添加以下标签（用逗号分隔）
     ```
     noise-monitoring, environmental-monitoring, vue3, flask, python, typescript, echarts, database-design, real-time-monitoring, data-visualization, city-noise, pollution-monitoring, tongji-university
     ```

### 方法二：使用 GitHub CLI

如果你安装了 GitHub CLI，可以使用以下命令：

```bash
gh repo edit hqx1234/CityNoise \
  --description "现代化的城市噪音污染监测与管理平台，提供实时数据监测、可视化分析和智能告警功能 | 同济大学数据库课程设计项目" \
  --add-topic "noise-monitoring" \
  --add-topic "environmental-monitoring" \
  --add-topic "vue3" \
  --add-topic "flask" \
  --add-topic "python" \
  --add-topic "typescript" \
  --add-topic "echarts" \
  --add-topic "database-design" \
  --add-topic "real-time-monitoring" \
  --add-topic "data-visualization" \
  --add-topic "city-noise" \
  --add-topic "pollution-monitoring" \
  --add-topic "tongji-university"
```

### 推荐的仓库描述

```
现代化的城市噪音污染监测与管理平台，提供实时数据监测、可视化分析和智能告警功能 | 同济大学数据库课程设计项目
```

### 推荐的主题标签

- `noise-monitoring` - 噪音监测
- `environmental-monitoring` - 环境监测
- `vue3` - Vue 3 框架
- `flask` - Flask 框架
- `python` - Python 语言
- `typescript` - TypeScript 语言
- `echarts` - ECharts 图表库
- `database-design` - 数据库设计
- `real-time-monitoring` - 实时监测
- `data-visualization` - 数据可视化
- `city-noise` - 城市噪音
- `pollution-monitoring` - 污染监测
- `tongji-university` - 同济大学

