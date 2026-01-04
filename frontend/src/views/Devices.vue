<template>
  <div class="devices">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>监测设备</span>
          <div class="header-actions">
            <el-tag type="success" size="small">
              <el-icon><Connection /></el-icon>
              实时连接中
            </el-tag>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="queryForm" class="query-form">
        <el-form-item label="设备状态">
          <el-select v-model="queryForm.status" placeholder="请选择状态" clearable style="width: 150px">
            <el-option
              v-for="status in deviceStatuses"
              :key="status"
              :label="status"
              :value="status"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="区域">
          <el-select v-model="queryForm.region_id" placeholder="请选择区域" clearable style="width: 200px">
            <el-option
              v-for="region in regions"
              :key="region.region_id"
              :label="region.region_name"
              :value="region.region_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" v-loading="loading" style="width: 100%">
        <el-table-column prop="device_id" label="设备ID" width="120" fixed="left" />
        <el-table-column prop="device_model" label="设备型号" width="150" />
        <el-table-column prop="device_status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.device_status)" size="small">
              {{ row.device_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="region_name" label="所属区域" width="150" />
        <el-table-column label="位置" width="200">
          <template #default="{ row }">
            <span v-if="row.location.longitude && row.location.latitude">
              经度: {{ row.location.longitude }}, 纬度: {{ row.location.latitude }}
            </span>
            <span v-else style="color: #909399;">未设置</span>
          </template>
        </el-table-column>
        <el-table-column label="最新噪音值" width="130">
          <template #default="{ row }">
            <div v-if="row.realtimeData">
              <span :class="{'exceeded': row.realtimeData.is_exceeded}" style="font-weight: bold; font-size: 16px;">
                {{ row.realtimeData.noise_value?.toFixed(1) }} dB
              </span>
              <el-tag 
                v-if="row.realtimeData.is_exceeded" 
                type="danger" 
                size="small" 
                style="margin-left: 5px;"
              >
                超标
              </el-tag>
            </div>
            <span v-else style="color: #909399;">等待数据...</span>
          </template>
        </el-table-column>
        <el-table-column label="数据质量" width="100">
          <template #default="{ row }">
            <el-tag 
              v-if="row.realtimeData"
              :type="getQualityTagType(row.realtimeData.data_quality)"
              size="small"
            >
              {{ row.realtimeData.data_quality }}
            </el-tag>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="180">
          <template #default="{ row }">
            <span v-if="row.realtimeData?.timestamp">
              {{ formatDateTime(row.realtimeData.timestamp) }}
            </span>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button 
              type="primary" 
              size="small" 
              @click="handleViewChart(row)"
            >
              查看图表
            </el-button>
          </template>
        </el-table-column>
        <el-table-column prop="install_date" label="安装日期" width="180">
          <template #default="{ row }">
            {{ row.install_date ? formatDateTime(row.install_date) : '-' }}
          </template>
        </el-table-column>
      </el-table>

      <!-- 噪音动态变化图表对话框 -->
      <el-dialog 
        v-model="showChartDialog" 
        :title="`设备 ${selectedDevice?.device_id} - 噪音动态变化`" 
        width="1000px"
        :close-on-click-modal="false"
      >
        <div v-if="selectedDevice" class="chart-container">
          <div class="chart-controls">
            <el-radio-group v-model="chartTimeRange" @change="handleTimeRangeChange" size="small">
              <el-radio-button label="1">最近1小时</el-radio-button>
              <el-radio-button label="6">最近6小时</el-radio-button>
              <el-radio-button label="24">最近24小时</el-radio-button>
              <el-radio-button label="168">最近7天</el-radio-button>
            </el-radio-group>
            <el-button 
              type="primary" 
              size="small" 
              :loading="chartLoading"
              @click="refreshChartData"
              style="margin-left: 10px;"
            >
              <el-icon v-if="!chartLoading"><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
          <div v-loading="chartLoading" class="chart-wrapper">
            <v-chart 
              v-if="chartData.length > 0"
              :option="chartOption" 
              style="height: 450px;" 
              :loading="chartLoading"
            />
            <el-empty v-else description="暂无数据" :image-size="100" />
          </div>
          <div v-if="selectedDevice && chartData.length > 0" class="chart-stats">
            <el-row :gutter="20">
              <el-col :span="6">
                <div class="stat-item">
                  <div class="stat-label">当前值</div>
                  <div class="stat-value" :class="{'exceeded': getLatestValue() > getThreshold()}">
                    {{ getLatestValue().toFixed(1) }} dB
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-item">
                  <div class="stat-label">平均值</div>
                  <div class="stat-value">{{ getAverageValue().toFixed(1) }} dB</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-item">
                  <div class="stat-label">最大值</div>
                  <div class="stat-value">{{ getMaxValue().toFixed(1) }} dB</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-item">
                  <div class="stat-label">阈值</div>
                  <div class="stat-value">{{ getThreshold().toFixed(1) }} dB</div>
                </div>
              </el-col>
            </el-row>
          </div>
        </div>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { deviceAPI, regionAPI, noiseDataAPI } from '../api'
import { Connection, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkPointComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

// 注册ECharts组件
use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkPointComponent
])

const loading = ref(false)
const tableData = ref<any[]>([])
const regions = ref<any[]>([])
const deviceStatuses = ref<string[]>([]) // 设备状态列表
const realtimeEnabled = ref(true) // 默认启用实时更新
const eventSource = ref<EventSource | null>(null)
const realtimeDataMap = ref<Map<string, any>>(new Map())
const showChartDialog = ref(false)
const selectedDevice = ref<any>(null)
const chartData = ref<{time: string, value: number, timestamp: string}[]>([])
const chartUpdateTimer = ref<any>(null)
const chartTimeRange = ref<string>('1') // 默认1小时
const chartLoading = ref(false)

const queryForm = reactive({
  status: '',
  region_id: null as number | null
})

const getStatusTagType = (status: string) => {
  const map: Record<string, string> = {
    '在线': 'success',
    '正常': 'success', // 兼容旧数据
    '离线': 'info',
    '故障': 'danger',
    '维护中': 'warning',
    '校准中': 'warning'
  }
  return map[status] || 'info'
}

const getQualityTagType = (quality: string) => {
  const map: Record<string, string> = {
    '良好': 'success',
    '一般': 'warning',
    '较差': 'danger'
  }
  return map[quality] || 'info'
}

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const loadRegions = async () => {
  try {
    // 获取所有区域（District）列表
    const response = await regionAPI.get({ districts_only: true })
    if (response.status === 'success') {
      regions.value = response.regions || []
    }
  } catch (error) {
    console.error('加载区域失败:', error)
  }
}

const loadDeviceStatuses = async () => {
  try {
    const response = await deviceAPI.getStatuses()
    if (response.status === 'success') {
      deviceStatuses.value = response.statuses || []
    }
  } catch (error) {
    console.error('加载设备状态列表失败:', error)
    // 如果API失败，使用默认状态列表
    deviceStatuses.value = ['在线', '离线', '故障', '维护中', '校准中']
  }
}

const handleQuery = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (queryForm.status) params.status = queryForm.status
    if (queryForm.region_id) params.region_id = queryForm.region_id

    const response = await deviceAPI.get(params)
    if (response.status === 'success') {
      tableData.value = response.devices || []
      // 合并实时数据
      mergeRealtimeData()
    }
  } catch (error) {
    console.error('查询设备失败:', error)
  } finally {
    loading.value = false
  }
}

const mergeRealtimeData = () => {
  // 将实时数据合并到设备列表中
  tableData.value = tableData.value.map(device => {
    const realtimeData = realtimeDataMap.value.get(device.device_id)
    return {
      ...device,
      realtimeData: realtimeData || null
    }
  })
}

const connectRealtimeStream = () => {
  if (eventSource.value) {
    eventSource.value.close()
  }

  // 使用相对路径，Vite代理会自动处理
  const streamUrl = '/api/realtime/stream'
  
  eventSource.value = new EventSource(streamUrl)

  eventSource.value.onmessage = (event) => {
    try {
      const response = JSON.parse(event.data)
      if (response.status === 'success' && response.data) {
        // 更新实时数据映射
        response.data.forEach((item: any) => {
          realtimeDataMap.value.set(item.device_id, {
            noise_value: item.noise_value,
            timestamp: item.timestamp,
            data_quality: item.data_quality,
            is_exceeded: item.is_exceeded,
            alert: item.alert
          })
        })
        // 合并到表格数据
        mergeRealtimeData()
      }
    } catch (error) {
      console.error('解析实时数据失败:', error)
    }
  }

  eventSource.value.onerror = (error) => {
    console.error('实时数据流连接错误:', error)
    // 尝试重连
    setTimeout(() => {
      if (realtimeEnabled.value && eventSource.value?.readyState === EventSource.CLOSED) {
        console.log('尝试重新连接实时数据流...')
        connectRealtimeStream()
      }
    }, 5000)
  }
}

const disconnectRealtimeStream = () => {
  if (eventSource.value) {
    eventSource.value.close()
    eventSource.value = null
  }
  realtimeDataMap.value.clear()
  // 清除设备列表中的实时数据
  tableData.value = tableData.value.map(device => ({
    ...device,
    realtimeData: null
  }))
}

// 实时更新始终启用，不再需要切换函数

const handleReset = () => {
  queryForm.status = ''
  queryForm.region_id = null
  handleQuery()
}

const handleViewChart = async (row: any) => {
  selectedDevice.value = row
  showChartDialog.value = true
  chartTimeRange.value = '1' // 重置为1小时
  await loadChartData(row.device_id, parseInt(chartTimeRange.value))
  
  // 定时更新图表数据
    if (chartUpdateTimer.value) {
      clearInterval(chartUpdateTimer.value)
    }
    chartUpdateTimer.value = setInterval(() => {
      if (showChartDialog.value && selectedDevice.value) {
      loadChartData(selectedDevice.value.device_id, parseInt(chartTimeRange.value))
      }
  }, 10000) // 每10秒更新一次
}

const loadChartData = async (deviceId: string, hours: number = 1) => {
  chartLoading.value = true
  try {
    console.log('加载图表数据:', { deviceId, hours })
    const response = await noiseDataAPI.get({
      device_id: deviceId,
      hours: hours
    })
    
    console.log('API响应:', response)
    
    if (response && response.status === 'success' && response.data) {
      // 按时间排序并格式化
      const sortedData = response.data
        .map((item: any) => ({
          timestamp: item.timestamp,
          time: formatChartTime(item.timestamp, hours),
          value: parseFloat(item.noise_value) || 0
        }))
        .sort((a: any, b: any) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      
      console.log('处理后的图表数据:', sortedData)
      chartData.value = sortedData
    } else {
      console.warn('API响应格式不正确或没有数据:', response)
      chartData.value = []
    }
  } catch (error: any) {
    console.error('加载图表数据失败:', error)
    console.error('错误详情:', {
      message: error.message,
      response: error.response,
      config: error.config
    })
    chartData.value = []
    ElMessage.error(`加载图表数据失败: ${error.message || '未知错误'}`)
  } finally {
    chartLoading.value = false
  }
}

const formatChartTime = (timestamp: string, hours: number) => {
  const date = new Date(timestamp)
  if (hours <= 24) {
    // 24小时内显示时分秒
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } else {
    // 超过24小时显示月日时分
    return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  }
}

const handleTimeRangeChange = (value: string) => {
  if (selectedDevice.value) {
    loadChartData(selectedDevice.value.device_id, parseInt(value))
  }
}

const refreshChartData = () => {
  if (selectedDevice.value) {
    loadChartData(selectedDevice.value.device_id, parseInt(chartTimeRange.value))
  }
}

const getLatestValue = () => {
  return chartData.value.length > 0 ? chartData.value[chartData.value.length - 1].value : 0
}

const getAverageValue = () => {
  if (chartData.value.length === 0) return 0
  const sum = chartData.value.reduce((acc, item) => acc + item.value, 0)
  return sum / chartData.value.length
}

const getMaxValue = () => {
  if (chartData.value.length === 0) return 0
  return Math.max(...chartData.value.map(item => item.value))
}

const getThreshold = () => {
  // 获取设备的阈值，如果没有则使用默认值60
  return selectedDevice.value?.realtimeData?.threshold || 60
}

const chartOption = computed(() => {
  const threshold = getThreshold()
  const maxValue = getMaxValue()
  const minValue = chartData.value.length > 0 ? Math.min(...chartData.value.map(item => item.value)) : 30
  
  // 动态调整Y轴范围
  const yAxisMin = Math.max(0, Math.floor(minValue / 10) * 10 - 10)
  const yAxisMax = Math.min(120, Math.ceil(maxValue / 10) * 10 + 10)
  
  return {
    title: {
      text: '噪音动态变化趋势',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#6a7985'
        }
      },
      formatter: (params: any) => {
        const param = params[0]
        const dataIndex = param.dataIndex
        const dataPoint = chartData.value[dataIndex]
        const isExceeded = param.value > threshold
        return `
          <div style="padding: 5px;">
            <div><strong>时间:</strong> ${param.name}</div>
            <div><strong>噪音值:</strong> <span style="color: ${isExceeded ? '#f56c6c' : '#409EFF'}; font-weight: bold;">${param.value} dB</span></div>
            <div><strong>阈值:</strong> ${threshold} dB</div>
            ${isExceeded ? '<div style="color: #f56c6c;">⚠️ 超过阈值</div>' : ''}
          </div>
        `
      }
    },
    legend: {
      data: ['噪音值', '阈值'],
      top: 30
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: chartData.value.map(item => item.time),
      boundaryGap: false,
      axisLabel: {
        rotate: chartData.value.length > 50 ? 45 : 0,
        interval: chartData.value.length > 100 ? Math.floor(chartData.value.length / 10) : 0
      }
    },
    yAxis: {
      type: 'value',
      name: '噪音值 (dB)',
      min: yAxisMin,
      max: yAxisMax,
      splitLine: {
        show: true,
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    series: [
      {
        name: '噪音值',
        type: 'line',
        data: chartData.value.map((item, index) => ({
          value: item.value,
          itemStyle: {
            color: item.value > threshold ? '#f56c6c' : '#409EFF'
          }
        })),
        smooth: true,
        symbol: chartData.value.length < 100 ? 'circle' : 'none',
        symbolSize: 6,
        lineStyle: {
          color: '#409EFF',
          width: 2
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
              { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
            ]
          }
        },
        markLine: {
          data: [
            { 
              yAxis: threshold, 
              name: '阈值',
              label: {
                formatter: `阈值: ${threshold} dB`
              }
            }
          ],
          lineStyle: {
            color: '#f56c6c',
            type: 'dashed',
            width: 2
          },
          label: {
            position: 'end',
            formatter: `阈值: ${threshold} dB`
          }
        },
        markPoint: {
          data: [
            { type: 'max', name: '最大值' },
            { type: 'min', name: '最小值' }
          ]
          }
        }
    ],
    dataZoom: chartData.value.length > 50 ? [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        start: 0,
        end: 100,
        height: 30
      }
    ] : []
  }
})

// 监听对话框关闭，清除定时器
watch(showChartDialog, (newVal) => {
  if (!newVal && chartUpdateTimer.value) {
    clearInterval(chartUpdateTimer.value)
    chartUpdateTimer.value = null
  }
})

onMounted(() => {
  loadRegions()
  loadDeviceStatuses() // 加载设备状态列表
  handleQuery()
  // 自动连接实时数据流
  connectRealtimeStream()
})

onBeforeUnmount(() => {
  // 断开实时数据流连接
  if (eventSource.value) {
    eventSource.value.close()
    eventSource.value = null
  }
  if (chartUpdateTimer.value) {
    clearInterval(chartUpdateTimer.value)
  }
})
</script>

<style scoped>
.devices {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
}

.query-form {
  margin-bottom: 20px;
}

.exceeded {
  color: #f56c6c;
}

:deep(.el-table .exceeded) {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.chart-container {
  padding: 20px 0;
}

.chart-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}

.chart-wrapper {
  min-height: 450px;
}

.chart-stats {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #ebeef5;
}

.stat-item {
  text-align: center;
}

.stat-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 5px;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.stat-value.exceeded {
  color: #f56c6c;
  animation: pulse 2s infinite;
}
</style>

