<template>
  <div class="regions">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>监测区域</span>
        </div>
      </template>

      <el-form :inline="true" :model="queryForm" class="query-form">
        <el-form-item label="区域筛选">
          <el-select v-model="queryForm.district" placeholder="请选择区域" clearable style="width: 200px" @change="handleQuery">
            <el-option
              v-for="district in districts"
              :key="district"
              :label="district"
              :value="district"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" v-loading="loading" style="width: 100%">
        <el-table-column prop="point_id" label="监测点ID" width="100" />
        <el-table-column prop="point_name" label="监测点名称" width="150" />
        <el-table-column prop="point_type" label="区域类型" width="120" />
        <el-table-column prop="location.district" label="所属区域" width="120">
          <template #default="{ row }">
            {{ row.location?.district || row.district || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="city_name" label="所属城市" width="120" />
        <el-table-column prop="threshold_day" label="昼间阈值(dB)" width="130" />
        <el-table-column prop="threshold_night" label="夜间阈值(dB)" width="130" />
        <el-table-column prop="sensor_count" label="设备数量" width="100" />
        <el-table-column label="最近统计" width="200">
          <template #default="{ row }">
            <div v-if="row.recent_stats">
              <div>平均: {{ row.recent_stats.avg_noise.toFixed(1) }} dB</div>
              <div>数据量: {{ row.recent_stats.data_count }}</div>
              <div>超标: {{ row.recent_stats.exceed_count }}</div>
            </div>
            <span v-else style="color: #909399;">暂无数据</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="handleViewDevices(row)"
            >
              查看设备
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 设备列表对话框 -->
    <el-dialog v-model="showDevicesDialog" :title="`${selectedRegionName} - 设备列表`" width="800px">
      <div v-if="regionDevices.length === 0" style="text-align: center; padding: 40px; color: #909399;">
        <el-empty description="该监测点暂无设备" />
      </div>
      <el-table v-else :data="regionDevices" style="width: 100%" v-loading="devicesLoading">
        <el-table-column prop="device_id" label="设备ID" width="120" />
        <el-table-column prop="device_model" label="设备型号" width="150" />
        <el-table-column prop="device_status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.device_status)" size="small">
              {{ row.device_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="recent_noise" label="最新噪音值" width="120">
          <template #default="{ row }">
            <span v-if="row.recent_noise">{{ row.recent_noise }} dB</span>
            <span v-else style="color: #909399;">暂无数据</span>
          </template>
        </el-table-column>
        <el-table-column prop="recent_update" label="更新时间" width="180">
          <template #default="{ row }">
            {{ row.recent_update ? formatDateTime(row.recent_update) : '-' }}
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { regionAPI } from '../api'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const tableData = ref<any[]>([])
const showDevicesDialog = ref(false)
const regionDevices = ref<any[]>([])
const districts = ref<string[]>([])
const devicesLoading = ref(false)
const selectedRegionName = ref<string>('')

const queryForm = reactive({
  district: null as string | null
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

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const loadDistricts = async () => {
  try {
    const response = await regionAPI.get({ districts_only: true })
    if (response.status === 'success') {
      districts.value = (response.regions || []).map((r: any) => r.district || r.region_name).filter(Boolean)
    }
  } catch (error) {
    console.error('加载区域列表失败:', error)
  }
}

const loadRegions = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (queryForm.district) {
      params.district = queryForm.district
    }
    const response = await regionAPI.get(params)
    if (response.status === 'success') {
      tableData.value = response.regions || []
    }
  } catch (error) {
    console.error('加载区域失败:', error)
  } finally {
    loading.value = false
  }
}

const handleQuery = () => {
  loadRegions()
}

const handleReset = () => {
  queryForm.district = null
  loadRegions()
}

const handleViewDevices = async (row: any) => {
  try {
    // 使用 point_id 来获取该监测点的设备列表
    const pointId = row.point_id || row.PointID
    if (!pointId) {
      ElMessage.warning('该区域没有有效的监测点ID')
      return
    }
    
    // 设置选中的区域名称
    selectedRegionName.value = row.point_name || row.PointName || `监测点 ${pointId}`
    
    devicesLoading.value = true
    regionDevices.value = [] // 清空之前的数据
    
    console.log('查看设备，监测点ID:', pointId, '监测点名称:', selectedRegionName.value)
    const response = await regionAPI.getDevices(pointId)
    console.log('设备列表响应:', response)
    
    if (response.status === 'success') {
      regionDevices.value = response.devices || []
      showDevicesDialog.value = true
      if (regionDevices.value.length === 0) {
        ElMessage.info('该监测点暂无设备')
      }
    } else {
      ElMessage.error(response.message || '加载设备失败')
    }
  } catch (error: any) {
    console.error('加载设备失败:', error)
    ElMessage.error(`加载设备失败: ${error.message || '未知错误'}`)
  } finally {
    devicesLoading.value = false
  }
}

onMounted(() => {
  loadDistricts()
  loadRegions()
})
</script>

<style scoped>
.regions {
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

