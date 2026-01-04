<template>
  <div class="statistics">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>统计分析</span>
        </div>
      </template>

      <el-form :inline="true" :model="queryForm" class="query-form">
        <el-form-item label="区域">
          <el-select v-model="queryForm.district" placeholder="请选择区域" clearable style="width: 200px" @change="handleQuery">
            <el-option
              v-for="region in regions"
              :key="region.region_id"
              :label="region.region_name"
              :value="region.district || region.region_name"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-text type="info">
            {{ queryForm.district ? `显示"${queryForm.district}"区域数据` : '显示所有区域总体数据' }}（最近24小时）
          </el-text>
        </el-form-item>
      </el-form>

      <el-row :gutter="20" style="margin-bottom: 20px;">
        <el-col :span="6">
          <el-statistic title="平均噪音值" :value="statistics.avg_noise" suffix="dB">
            <template #prefix>
              <el-icon style="vertical-align: -0.125em;"><DataLine /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="最大噪音值" :value="statistics.max_noise" suffix="dB">
            <template #prefix>
              <el-icon style="vertical-align: -0.125em;"><ArrowUp /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="最小噪音值" :value="statistics.min_noise" suffix="dB">
            <template #prefix>
              <el-icon style="vertical-align: -0.125em;"><ArrowDown /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="超标率" :value="statistics.exceed_rate" suffix="%">
            <template #prefix>
              <el-icon style="vertical-align: -0.125em;"><Warning /></el-icon>
            </template>
          </el-statistic>
        </el-col>
      </el-row>

      <el-row :gutter="20">
        <el-col :span="24">
          <el-card>
            <template #header>
              <span>24小时噪音趋势</span>
            </template>
            <div ref="hourlyChartRef" style="height: 400px;"></div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { DataLine, ArrowUp, ArrowDown, Warning } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { noiseDataAPI, regionAPI } from '../api'

const regions = ref<any[]>([])
const statistics = ref<any>({
  avg_noise: 0,
  max_noise: 0,
  min_noise: 0,
  exceed_rate: 0
})
const hourlyChartRef = ref<HTMLElement>()
let hourlyChart: echarts.ECharts | null = null

const queryForm = reactive({
  district: null as string | null
})

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

const handleQuery = async () => {
  try {
    const params: any = {
      hours: 24  // 默认查询最近24小时
    }
    if (queryForm.district) {
      params.district = queryForm.district
    }

    console.log('查询统计参数:', params)
    const response = await noiseDataAPI.getStatistics(params)
    console.log('统计响应:', response)
    
    if (response.status === 'success') {
      statistics.value = response.statistics || {
        avg_noise: 0,
        max_noise: 0,
        min_noise: 0,
        exceed_rate: 0
      }
      
      // 更新小时趋势图
      if (hourlyChart) {
        if (response.hourly_data && response.hourly_data.length > 0) {
          const hours = response.hourly_data.map((item: any) => item.hour)
          const values = response.hourly_data.map((item: any) => item.avg_noise)
          
          hourlyChart.setOption({
            tooltip: {
              trigger: 'axis',
              formatter: (params: any) => {
                const param = params[0]
                return `${param.name}<br/>${param.seriesName}: ${param.value}dB`
              }
            },
            xAxis: {
              type: 'category',
              data: hours.map((h: number) => `${String(h).padStart(2, '0')}:00`),
              name: '时间(小时)'
            },
            yAxis: {
              type: 'value',
              name: '噪音值(dB)'
            },
            series: [
              {
                name: '平均噪音值',
                type: 'line',
                data: values,
                smooth: true,
                areaStyle: {
                  opacity: 0.3
                },
                itemStyle: {
                  color: '#409eff'
                }
              }
            ]
          })
        } else {
          // 如果没有数据，显示空图表并提示
          hourlyChart.setOption({
            xAxis: { 
              type: 'category',
              data: []
            },
            yAxis: {
              type: 'value',
              name: '噪音值(dB)'
            },
            series: [{ 
              name: '平均噪音值',
              type: 'line',
              data: [] 
            }]
          })
          if (queryForm.district) {
            ElMessage.warning('该区域在最近24小时内没有数据')
          }
        }
      }
      
      // 如果没有数据，显示提示
      if (statistics.value.total_count === 0 && queryForm.district) {
        ElMessage.warning('该区域在最近24小时内没有数据')
      }
    } else {
      console.error('查询统计失败:', response.message || '未知错误')
      ElMessage.error(response.message || '查询统计失败')
    }
  } catch (error: any) {
    console.error('查询统计失败:', error)
    // 显示错误提示
    const errorMsg = error.response?.data?.message || error.message || '查询统计失败，请稍后重试'
    ElMessage.error(errorMsg)
    
    // 重置统计数据
    statistics.value = {
      avg_noise: 0,
      max_noise: 0,
      min_noise: 0,
      exceed_rate: 0
    }
    // 清空图表
    if (hourlyChart) {
      hourlyChart.setOption({
        xAxis: { data: [] },
        series: [{ data: [] }]
      })
    }
  }
}

onMounted(async () => {
  await loadRegions()
  await nextTick()
  
  if (hourlyChartRef.value) {
    hourlyChart = echarts.init(hourlyChartRef.value)
    // 初始化图表配置
    hourlyChart.setOption({
      tooltip: {
        trigger: 'axis'
      },
      xAxis: {
        type: 'category',
        data: [],
        name: '时间(小时)'
      },
      yAxis: {
        type: 'value',
        name: '噪音值(dB)'
      },
      series: [{
        name: '平均噪音值',
        type: 'line',
        data: [],
        smooth: true,
        areaStyle: {
          opacity: 0.3
        },
        itemStyle: {
          color: '#409eff'
        }
      }]
    })
  }
  
  // 页面加载时自动查询所有区域的总体数据
  await handleQuery()
})
</script>

<style scoped>
.statistics {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.query-form {
  margin-bottom: 20px;
}
</style>

