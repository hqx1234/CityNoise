<template>
  <div class="dashboard">
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #409eff;">
              <el-icon><Monitor /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total_devices || 0 }}</div>
              <div class="stat-label">总设备数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #67c23a;">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.online_devices || 0 }}</div>
              <div class="stat-label">在线设备 ({{ stats.online_rate || 0 }}%)</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #e6a23c;">
              <el-icon><DataLine /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.today_data_count || 0 }}</div>
              <div class="stat-label">今日数据量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #f56c6c;">
              <el-icon><Bell /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.pending_alerts || 0 }}</div>
              <div class="stat-label">未处理告警</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="16">
        <el-card>
          <template #header>
            <span>区域类型分布</span>
          </template>
          <div ref="regionChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>最近告警</span>
          </template>
          <el-table :data="recentAlerts" style="width: 100%" size="small">
            <el-table-column prop="region" label="区域" width="100" />
            <el-table-column prop="level" label="级别" width="80">
              <template #default="{ row }">
                <el-tag
                  :type="getAlertTagType(row.level)"
                  size="small"
                >
                  {{ row.level }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="noise_value" label="噪音值" width="80" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Monitor, CircleCheck, DataLine, Bell } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { dashboardAPI } from '../api'

const stats = ref<any>({})
const recentAlerts = ref<any[]>([])
const regionChartRef = ref<HTMLElement>()
let regionChart: echarts.ECharts | null = null

const getAlertTagType = (level: string) => {
  const map: Record<string, string> = {
    '低': 'info',
    '中': 'warning',
    '高': 'danger',
    '紧急': 'danger'
  }
  return map[level] || 'info'
}

const loadDashboardData = async () => {
  try {
    const response = await dashboardAPI.getStats()
    if (response.status === 'success') {
      stats.value = response.stats
      recentAlerts.value = response.recent_alerts || []
      
      // 更新区域类型分布图表
      if (regionChart && response.stats.regions_by_type) {
        const regionData = Object.entries(response.stats.regions_by_type).map(([name, value]) => ({
          name,
          value
        }))
        
        regionChart.setOption({
          tooltip: {
            trigger: 'item'
          },
          legend: {
            orient: 'vertical',
            left: 'left'
          },
          series: [
            {
              name: '区域类型',
              type: 'pie',
              radius: '50%',
              data: regionData,
              emphasis: {
                itemStyle: {
                  shadowBlur: 10,
                  shadowOffsetX: 0,
                  shadowColor: 'rgba(0, 0, 0, 0.5)'
                }
              }
            }
          ]
        })
      }
    }
  } catch (error) {
    console.error('加载仪表板数据失败:', error)
  }
}

onMounted(() => {
  if (regionChartRef.value) {
    regionChart = echarts.init(regionChartRef.value)
  }
  loadDashboardData()
  
  // 每30秒刷新一次数据
  const timer = setInterval(loadDashboardData, 30000)
  onUnmounted(() => {
    clearInterval(timer)
    if (regionChart) {
      regionChart.dispose()
    }
  })
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  height: 120px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}
</style>

