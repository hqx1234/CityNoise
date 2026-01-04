# 城市噪音污染监测管理平台 API 文档

## 基础信息

- **Base URL**: `http://localhost:5000`
- **Content-Type**: `application/json`
- **字符编码**: UTF-8

---

## 目录

1. [数据库初始化](#数据库初始化)
2. [用户认证](#用户认证)
3. [噪音数据管理](#噪音数据管理)
4. [告警管理](#告警管理)
5. [监测区域管理](#监测区域管理)
6. [设备管理](#设备管理)
7. [报告管理](#报告管理)
8. [仪表板](#仪表板)
9. [地图展示](#地图展示)
10. [数据导入](#数据导入)

---

## 数据库初始化

### 初始化数据库表

初始化数据库表结构，并创建默认管理员账户和示例城市数据。

**请求**
- **方法**: `POST`
- **路径**: `/api/init-db`
- **请求体**: 无

**响应**

成功响应 (200):
```json
{
  "status": "success",
  "message": "数据库初始化成功"
}
```

错误响应 (500):
```json
{
  "status": "error",
  "message": "数据库初始化失败: {错误信息}"
}
```

---

## 用户认证

### 用户注册

注册新用户账户。

**请求**
- **方法**: `POST`
- **路径**: `/api/auth/register`
- **请求体**:
```json
{
  "username": "string (必填)",
  "password": "string (必填)",
  "email": "string (必填)",
  "role": "string (必填, 可选值: '管理员', '操作员', '普通用户')",
  "phone": "string (可选)",
  "responsible_regions": [1, 2, 3] (可选, 负责的区域ID列表)
}
```

**响应**

成功响应 (201):
```json
{
  "status": "success",
  "message": "注册成功",
  "user_id": 1
}
```

错误响应 (400/500):
```json
{
  "status": "error",
  "message": "错误信息"
}
```

### 用户登录

用户登录验证。

**请求**
- **方法**: `POST`
- **路径**: `/api/auth/login`
- **请求体**:
```json
{
  "username": "string (必填)",
  "password": "string (必填)"
}
```

**响应**

成功响应 (200):
```json
{
  "status": "success",
  "message": "登录成功",
  "user": {
    "user_id": 1,
    "username": "admin",
    "role": "管理员",
    "email": "admin@noise-monitoring.com",
    "last_login": "2025-01-01T12:00:00"
  }
}
```

错误响应 (401/500):
```json
{
  "status": "error",
  "message": "用户名或密码错误"
}
```

---

## 噪音数据管理

### 上传噪音数据

上传新的噪音监测数据。

**请求**
- **方法**: `POST`
- **路径**: `/api/noise-data`
- **请求体**:
```json
{
  "noise_value": "float (必填, 分贝值)",
  "device_id": "string (必填, 设备ID)",
  "region_id": "integer (必填, 区域ID)",
  "frequency_analysis": "string (可选, 频率分析结果JSON)",
  "data_quality": "string (可选, 可选值: '优秀', '良好', '一般', '较差', 默认: '良好')",
  "timestamp": "string (可选, ISO格式时间, 默认: 当前时间)"
}
```

**响应**

成功响应 (201):
```json
{
  "status": "success",
  "message": "噪音数据上传成功",
  "noise_id": 1,
  "is_exceeded": false,
  "alert": {
    "alert_id": 1,
    "alert_level": "中"
  }
}
```
> 注: 如果数据超标，会返回 `alert` 字段

错误响应 (400/500):
```json
{
  "status": "error",
  "message": "错误信息"
}
```

### 查询噪音数据

查询噪音监测数据列表。

**请求**
- **方法**: `GET`
- **路径**: `/api/noise-data`
- **查询参数**:
  - `region_id` (integer, 可选): 区域ID
  - `device_id` (string, 可选): 设备ID
  - `start_time` (string, 可选): 开始时间 (ISO格式)
  - `end_time` (string, 可选): 结束时间 (ISO格式)
  - `limit` (integer, 可选): 返回数量限制 (默认: 100)

**响应**

成功响应 (200):
```json
{
  "status": "success",
  "data": [
    {
      "noise_id": 1,
      "noise_value": 65.5,
      "timestamp": "2025-01-01T12:00:00",
      "device_id": "DEV001",
      "region_id": 1,
      "region_name": "市中心商业区",
      "is_exceeded": true,
      "data_quality": "良好"
    }
  ],
  "count": 1
}
```

### 获取噪音统计信息

获取噪音数据的统计分析。

**请求**
- **方法**: `GET`
- **路径**: `/api/noise-data/statistics`
- **查询参数**:
  - `region_id` (integer, 可选): 区域ID
  - `start_time` (string, 可选): 开始时间
  - `end_time` (string, 可选): 结束时间

**响应**

成功响应 (200):
```json
{
  "status": "success",
  "statistics": {
    "avg_noise": 58.5,
    "max_noise": 75.2,
    "min_noise": 45.3,
    "total_count": 1000,
    "exceed_count": 150,
    "exceed_rate": 15.0
  },
  "hourly_data": [
    {
      "hour": 0,
      "avg_noise": 52.3,
      "count": 50
    },
    {
      "hour": 1,
      "avg_noise": 51.8,
      "count": 48
    }
  ]
}
```

---

## 告警管理

### 获取告警信息

查询告警信息列表。

**请求**
- **方法**: `GET`
- **路径**: `/api/alerts`
- **查询参数**:
  - `status` (string, 可选): 告警状态 ('未处理', '处理中', '已处理', '已关闭')
  - `level` (string, 可选): 告警级别 ('低', '中', '高', '紧急')
  - `region_id` (integer, 可选): 区域ID
  - `limit` (integer, 可选): 返回数量限制 (默认: 50)

**响应**

成功响应 (200):
```json
{
  "status": "success",
  "alerts": [
    {
      "alert_id": 1,
      "alert_level": "中",
      "trigger_time": "2025-01-01T12:00:00",
      "alert_status": "未处理",
      "noise_value": 68.5,
      "region_id": 1,
      "region_name": "市中心商业区",
      "device_id": "DEV001",
      "handler": null,
      "process_notes": null
    }
  ],
  "count": 1
}
```

### 更新告警状态

更新指定告警的状态和处理信息。

**请求**
- **方法**: `PUT`
- **路径**: `/api/alerts/<alert_id>`
- **路径参数**:
  - `alert_id` (integer): 告警ID
- **请求体**:
```json
{
  "status": "string (可选, 告警状态)",
  "handler_id": "integer (可选, 处理人ID)",
  "process_notes": "string (可选, 处理备注)"
}
```

**响应**

成功响应 (200):
```json
{
  "status": "success",
  "message": "告警更新成功"
}
```

错误响应 (404/500):
```json
{
  "status": "error",
  "message": "错误信息"
}
```

---

## 监测区域管理

### 获取监测区域列表

查询监测区域信息。

**请求**
- **方法**: `GET`
- **路径**: `/api/regions`
- **查询参数**:
  - `city_id` (integer, 可选): 城市ID
  - `type` (string, 可选): 区域类型 ('住宅区', '商业区', '工业区', '文教区', '混合区', '交通干线', '其他')

**响应**

成功响应 (200):
```json
{
  "status": "success",
  "regions": [
    {
      "region_id": 1,
      "region_name": "市中心商业区",
      "region_type": "商业区",
      "city_id": 1,
      "city_name": "北京市",
      "threshold_day": 65.0,
      "threshold_night": 55.0,
      "population_density": 5000.0,
      "device_count": 5,
      "recent_stats": {
        "avg_noise": 62.5,
        "data_count": 120,
        "exceed_count": 15
      }
    }
  ],
  "count": 1
}
```

### 获取区域内的监测设备

获取指定区域内的所有监测设备。

**请求**
- **方法**: `GET`
- **路径**: `/api/regions/<region_id>/devices`
- **路径参数**:
  - `region_id` (integer): 区域ID

**响应**

成功响应 (200):
```json
{
  "status": "success",
  "devices": [
    {
      "device_id": "DEV001",
      "device_model": "NoiseMonitor-2024",
      "install_date": "2024-01-01T00:00:00",
      "device_status": "正常",
      "longitude": 116.3974,
      "latitude": 39.9093,
      "recent_noise": 65.5,
      "recent_update": "2025-01-01T12:00:00"
    }
  ]
}
```

---

## 设备管理

### 获取所有监测设备

查询所有监测设备信息。

**请求**
- **方法**: `GET`
- **路径**: `/api/devices`
- **查询参数**:
  - `status` (string, 可选): 设备状态 ('正常', '故障', '校准中', '离线')
  - `region_id` (integer, 可选): 区域ID

**响应**

成功响应 (200):
```json
{
  "status": "success",
  "devices": [
    {
      "device_id": "DEV001",
      "device_model": "NoiseMonitor-2024",
      "device_status": "正常",
      "region_id": 1,
      "region_name": "市中心商业区",
      "location": {
        "longitude": 116.3974,
        "latitude": 39.9093
      },
      "install_date": "2024-01-01T00:00:00"
    }
  ],
  "count": 1
}
```

---

## 报告管理

### 生成报告

生成指定类型的监测报告。

**请求**
- **方法**: `POST`
- **路径**: `/api/reports`
- **请求体**:
```json
{
  "report_type": "string (必填, 可选值: '日报', '周报', '月报', '年报', '专项报告')",
  "generated_by": "integer (必填, 生成人用户ID)",
  "start_date": "string (可选, 格式: 'YYYY-MM-DD')",
  "end_date": "string (可选, 格式: 'YYYY-MM-DD')",
  "report_period": "string (可选, 格式: 'YYYY-MM-DD 至 YYYY-MM-DD')",
  "is_public": "integer (可选, 0:私有, 1:公开, 默认: 0)"
}
```

**响应**

成功响应 (201):
```json
{
  "status": "success",
  "message": "报告生成成功",
  "report_id": 1,
  "report_period": "2025-01-01 至 2025-01-31"
}
```

> 注: 如果不提供日期范围，系统会根据报告类型自动计算周期

### 获取报告列表

查询已生成的报告列表。

**请求**
- **方法**: `GET`
- **路径**: `/api/reports`
- **查询参数**:
  - `type` (string, 可选): 报告类型
  - `limit` (integer, 可选): 返回数量限制 (默认: 20)

**响应**

成功响应 (200):
```json
{
  "status": "success",
  "reports": [
    {
      "report_id": 1,
      "report_type": "月报",
      "report_period": "2025-01-01 至 2025-01-31",
      "generated_at": "2025-01-31T23:59:59",
      "generated_by": "admin",
      "is_public": false,
      "file_path": null,
      "content": {
        "summary": "月报摘要",
        "period": "2025-01-01 至 2025-01-31",
        "statistics": {
          "total_data_count": 10000,
          "avg_noise": 58.5,
          "max_noise": 85.2,
          "min_noise": 42.3,
          "exceed_count": 1500,
          "exceed_rate": 15.0,
          "alert_count": 200,
          "alert_by_level": {
            "低": 100,
            "中": 70,
            "高": 25,
            "紧急": 5
          }
        },
        "region_statistics": [],
        "recommendations": []
      }
    }
  ]
}
```

### 删除报告

删除指定的报告。

**请求**
- **方法**: `DELETE`
- **路径**: `/api/reports/<report_id>`
- **路径参数**:
  - `report_id` (integer): 报告ID

**响应**

成功响应 (200):
```json
{
  "status": "success",
  "message": "报告删除成功"
}
```

错误响应 (404/500):
```json
{
  "status": "error",
  "message": "错误信息"
}
```

---

## 仪表板

### 获取仪表板统计数据

获取仪表板展示所需的统计数据。

**请求**
- **方法**: `GET`
- **路径**: `/api/dashboard/stats`

**响应**

成功响应 (200):
```json
{
  "status": "success",
  "stats": {
    "total_devices": 50,
    "online_devices": 45,
    "online_rate": 90.0,
    "today_data_count": 1200,
    "pending_alerts": 15,
    "regions_by_type": {
      "住宅区": 10,
      "商业区": 8,
      "工业区": 5,
      "文教区": 3
    }
  },
  "recent_alerts": [
    {
      "id": 1,
      "level": "中",
      "time": "2025-01-01T12:00:00",
      "region": "市中心商业区",
      "noise_value": 68.5
    }
  ]
}
```

---

## 地图展示

### 获取地图展示数据

获取地图展示所需的设备和区域数据。

**请求**
- **方法**: `GET`
- **路径**: `/api/map/data`

**响应**

成功响应 (200):
```json
{
  "status": "success",
  "devices": [
    {
      "device_id": "DEV001",
      "device_status": "正常",
      "coordinates": [116.3974, 39.9093],
      "region_id": 1,
      "region_name": "市中心商业区",
      "recent_noise": 65.5,
      "is_exceeded": false
    }
  ],
  "regions": [
    {
      "region_id": 1,
      "region_name": "市中心商业区",
      "region_type": "商业区",
      "center": [116.3974, 39.9093],
      "avg_noise": 62.5,
      "noise_level": "良",
      "device_count": 5
    }
  ]
}
```

---

## 数据导入

### 批量导入数据

通过CSV或Excel文件批量导入噪音数据。

**请求**
- **方法**: `POST`
- **路径**: `/api/data-import`
- **Content-Type**: `multipart/form-data`
- **请求参数**:
  - `file` (file, 必填): CSV或Excel文件

**文件格式要求**:
CSV/Excel文件应包含以下列：
- `noise_value`: 噪音值 (float)
- `device_id`: 设备ID (string)
- `region_id`: 区域ID (integer)
- `timestamp`: 时间戳 (datetime, 可选)

**响应**

成功响应 (200):
```json
{
  "status": "success",
  "message": "成功导入 100 条数据",
  "imported_count": 100
}
```

错误响应 (400/500):
```json
{
  "status": "error",
  "message": "错误信息"
}
```

**支持的文件类型**:
- CSV (.csv)
- Excel (.xlsx)

---

## 错误码说明

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未授权/认证失败 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 响应格式说明

所有API响应都遵循统一的格式：

**成功响应**:
```json
{
  "status": "success",
  "message": "操作成功信息",
  "data": {} // 具体数据
}
```

**错误响应**:
```json
{
  "status": "error",
  "message": "错误描述信息"
}
```

---

## 注意事项

1. **时间格式**: 所有时间字段使用ISO 8601格式 (例如: `2025-01-01T12:00:00`)
2. **分页**: 部分列表接口支持 `limit` 参数限制返回数量，但暂不支持分页
3. **认证**: 当前版本未实现JWT Token认证，实际部署时建议添加
4. **文件上传**: 数据导入接口支持最大16MB的文件
5. **数据库**: 默认使用SQLite，生产环境建议使用MySQL或PostgreSQL

---

## 更新日志

- **v1.0.0** (2025-01-01): 初始版本，包含所有基础功能API

