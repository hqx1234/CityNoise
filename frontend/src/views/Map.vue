<template>
  <div class="map-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>地图展示</span>
          <el-button @click="refreshMap">刷新</el-button>
        </div>
      </template>

      <div ref="mapContainer" style="height: 600px; width: 100%;"></div>

      <el-row :gutter="20" style="margin-top: 20px;">
        <el-col :span="12">
          <el-card>
            <template #header>
              <span>设备列表</span>
            </template>
            <el-table :data="devices" style="width: 100%" size="small" max-height="300">
              <el-table-column prop="device_id" label="设备ID" width="120" />
              <el-table-column prop="device_status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="getStatusTagType(row.device_status)" size="small">
                    {{ row.device_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="region_name" label="区域" width="150" />
              <el-table-column prop="recent_noise" label="最新噪音值" width="120">
                <template #default="{ row }">
                  <span v-if="row.recent_noise">{{ row.recent_noise }} dB</span>
                  <span v-else style="color: #909399;">暂无数据</span>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>
              <span>区域统计</span>
            </template>
            <el-table :data="regions" style="width: 100%" size="small" max-height="300">
              <el-table-column prop="region_name" label="区域名称" width="150" />
              <el-table-column prop="region_type" label="类型" width="120" />
              <el-table-column prop="avg_noise" label="平均噪音" width="120">
                <template #default="{ row }">
                  <span v-if="row.avg_noise">{{ row.avg_noise }} dB</span>
                  <span v-else style="color: #909399;">暂无数据</span>
                </template>
              </el-table-column>
              <el-table-column prop="noise_level" label="噪音等级" width="120">
                <template #default="{ row }">
                  <el-tag :type="getLevelTagType(row.noise_level)" size="small">
                    {{ row.noise_level }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { mapAPI } from '../api'

const mapContainer = ref<HTMLElement>()
let mapChart: echarts.ECharts | null = null
const devices = ref<any[]>([])
const regions = ref<any[]>([])

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

const getLevelTagType = (level: string) => {
  const map: Record<string, string> = {
    '优': 'success',
    '良': 'info',
    '轻度污染': 'warning',
    '中度污染': 'danger',
    '重度污染': 'danger'
  }
  return map[level] || 'info'
}

const loadMapData = async () => {
  try {
    const response = await mapAPI.getData()
    if (response.status === 'success') {
      devices.value = response.devices || []
      regions.value = response.regions || []
      
      // 更新地图（如果使用百度地图，需要配置bmap，否则使用普通散点图）
      if (mapChart && devices.value.length > 0) {
        const scatterData = devices.value
          .filter(d => d.coordinates && d.coordinates.length === 2)
          .map(d => [d.coordinates[0], d.coordinates[1], d.recent_noise || 0])
        
        // 计算中心点和范围
        const lngs = scatterData.map(d => d[0])
        const lats = scatterData.map(d => d[1])
        const centerLng = (Math.max(...lngs) + Math.min(...lngs)) / 2
        const centerLat = (Math.max(...lats) + Math.min(...lats)) / 2
        
        mapChart.setOption({
          xAxis: {
            min: Math.min(...lngs) - 0.01,
            max: Math.max(...lngs) + 0.01
          },
          yAxis: {
            min: Math.min(...lats) - 0.01,
            max: Math.max(...lats) + 0.01
          },
          series: [
            {
              name: '监测设备',
              type: 'scatter',
              data: scatterData,
              symbolSize: (val: number[]) => {
                return val[2] > 70 ? 20 : val[2] > 60 ? 15 : 10
              },
              itemStyle: {
                color: (params: any) => {
                  const device = devices.value.find(d => 
                    d.coordinates && 
                    Math.abs(d.coordinates[0] - params.value[0]) < 0.001 &&
                    Math.abs(d.coordinates[1] - params.value[1]) < 0.001
                  )
                  return device?.is_exceeded ? '#f56c6c' : '#67c23a'
                }
              },
              label: {
                show: true,
                formatter: (params: any) => {
                  const device = devices.value.find(d => 
                    d.coordinates && 
                    Math.abs(d.coordinates[0] - params.value[0]) < 0.001 &&
                    Math.abs(d.coordinates[1] - params.value[1]) < 0.001
                  )
                  return device?.device_id || ''
                }
              }
            }
          ],
          tooltip: {
            trigger: 'item',
            formatter: (params: any) => {
              const device = devices.value.find(d => 
                d.coordinates && 
                Math.abs(d.coordinates[0] - params.value[0]) < 0.001 &&
                Math.abs(d.coordinates[1] - params.value[1]) < 0.001
              )
              if (device) {
                return `设备: ${device.device_id}<br/>噪音值: ${params.value[2]} dB<br/>状态: ${device.device_status}<br/>区域: ${device.region_name || '未知'}`
              }
              return ''
            }
          }
        })
      }
    }
  } catch (error) {
    console.error('加载地图数据失败:', error)
    ElMessage.error('加载地图数据失败')
  }
}

const refreshMap = () => {
  loadMapData()
}

onMounted(async () => {
  if (mapContainer.value) {
    mapChart = echarts.init(mapContainer.value)
    
    // 初始化图表配置
    mapChart.setOption({
      title: {
        text: '监测设备分布图',
        left: 'center'
      },
      tooltip: {
        trigger: 'item'
      },
      xAxis: {
        type: 'value',
        name: '经度'
      },
      yAxis: {
        type: 'value',
        name: '纬度'
      },
      series: [
        {
          name: '监测设备',
          type: 'scatter',
          data: []
        }
      ]
    })
    
    // 加载地图数据
    await loadMapData()
    
    // 更新为散点图
    if (mapChart && devices.value.length > 0) {
      const scatterData = devices.value
        .filter(d => d.coordinates && d.coordinates.length === 2)
        .map(d => [d.coordinates[0], d.coordinates[1], d.recent_noise || 0])
      
      mapChart.setOption({
        series: [
          {
            name: '监测设备',
            type: 'scatter',
            data: scatterData,
            symbolSize: (val: number[]) => {
              return val[2] > 70 ? 20 : val[2] > 60 ? 15 : 10
            },
            itemStyle: {
              color: (params: any) => {
                const device = devices.value.find(d => 
                  d.coordinates && 
                  Math.abs(d.coordinates[0] - params.value[0]) < 0.001 &&
                  Math.abs(d.coordinates[1] - params.value[1]) < 0.001
                )
                return device?.is_exceeded ? '#f56c6c' : '#67c23a'
              }
            },
            label: {
              show: true,
              formatter: (params: any) => {
                const device = devices.value.find(d => 
                  d.coordinates && 
                  Math.abs(d.coordinates[0] - params.value[0]) < 0.001 &&
                  Math.abs(d.coordinates[1] - params.value[1]) < 0.001
                )
                return device?.device_id || ''
              }
            }
          }
        ],
        tooltip: {
          trigger: 'item',
          formatter: (params: any) => {
            const device = devices.value.find(d => 
              d.coordinates && 
              Math.abs(d.coordinates[0] - params.value[0]) < 0.001 &&
              Math.abs(d.coordinates[1] - params.value[1]) < 0.001
            )
            if (device) {
              return `设备: ${device.device_id}<br/>噪音值: ${params.value[2]} dB<br/>状态: ${device.device_status}`
            }
            return ''
          }
        }
      })
    }
  }
})

onUnmounted(() => {
  if (mapChart) {
    mapChart.dispose()
  }
})
</script>

<style scoped>
.map-view {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

