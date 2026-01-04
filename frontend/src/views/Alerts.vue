<template>
  <div class="alerts">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>告警管理</span>
        </div>
      </template>

      <el-form :inline="true" :model="queryForm" class="query-form">
        <el-form-item label="告警状态">
          <el-select v-model="queryForm.status" placeholder="请选择状态" clearable style="width: 150px">
            <el-option label="未处理" value="未处理" />
            <el-option label="处理中" value="处理中" />
            <el-option label="已处理" value="已处理" />
            <el-option label="已关闭" value="已关闭" />
          </el-select>
        </el-form-item>
        <el-form-item label="告警级别">
          <el-select v-model="queryForm.level" placeholder="请选择级别" clearable style="width: 150px">
            <el-option label="低" value="低" />
            <el-option label="中" value="中" />
            <el-option label="高" value="高" />
            <el-option label="紧急" value="紧急" />
          </el-select>
        </el-form-item>
        <el-form-item label="区域">
          <el-select v-model="queryForm.district" placeholder="请选择区域" clearable style="width: 200px">
            <el-option
              v-for="region in regions"
              :key="region.region_id"
              :label="region.region_name"
              :value="region.district || region.region_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" v-loading="loading" style="width: 100%">
        <el-table-column prop="alert_id" label="告警ID" width="100" />
        <el-table-column prop="alert_level" label="级别" width="100">
          <template #default="{ row }">
            <el-tag :type="getLevelTagType(row.alert_level)" size="small">
              {{ row.alert_level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="region_name" label="区域" width="150" />
        <el-table-column prop="device_id" label="设备ID" width="120" />
        <el-table-column prop="noise_value" label="噪音值(dB)" width="120">
          <template #default="{ row }">
            <span style="color: #f56c6c; font-weight: bold;">{{ row.noise_value }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="trigger_time" label="触发时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.trigger_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="alert_status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.alert_status)" size="small">
              {{ row.alert_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="handler" label="处理人" width="120" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.alert_status === '未处理'"
              type="primary"
              size="small"
              @click="handleProcess(row)"
            >
              处理
            </el-button>
            <el-button
              type="info"
              size="small"
              @click="handleView(row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 处理告警对话框 -->
    <el-dialog v-model="showProcessDialog" title="处理告警" width="500px">
      <el-form :model="processForm" label-width="100px">
        <el-form-item label="告警ID">
          <el-input v-model="processForm.alert_id" disabled />
        </el-form-item>
        <el-form-item label="告警级别">
          <el-tag :type="getLevelTagType(processForm.alert_level)">
            {{ processForm.alert_level }}
          </el-tag>
        </el-form-item>
        <el-form-item label="噪音值">
          {{ processForm.noise_value }} dB
        </el-form-item>
        <el-form-item label="处理状态" required>
          <el-select v-model="processForm.status" style="width: 100%">
            <el-option label="处理中" value="处理中" />
            <el-option label="已处理" value="已处理" />
            <el-option label="已关闭" value="已关闭" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理备注">
          <el-input
            v-model="processForm.process_notes"
            type="textarea"
            :rows="4"
            placeholder="请输入处理备注"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showProcessDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitProcess" :loading="processing">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { alertAPI, regionAPI } from '../api'

const loading = ref(false)
const processing = ref(false)
const showProcessDialog = ref(false)
const tableData = ref<any[]>([])
const regions = ref<any[]>([])

const queryForm = reactive({
  status: '',
  level: '',
  district: null as string | null
})

const processForm = reactive({
  alert_id: 0,
  alert_level: '',
  noise_value: 0,
  status: '处理中',
  process_notes: ''
})

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const getLevelTagType = (level: string) => {
  const map: Record<string, string> = {
    '低': 'info',
    '中': 'warning',
    '高': 'danger',
    '紧急': 'danger'
  }
  return map[level] || 'info'
}

const getStatusTagType = (status: string) => {
  const map: Record<string, string> = {
    '未处理': 'warning',
    '处理中': 'primary',
    '已处理': 'success',
    '已关闭': 'info'
  }
  return map[status] || 'info'
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

const handleQuery = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (queryForm.status) params.status = queryForm.status
    if (queryForm.level) params.level = queryForm.level
    if (queryForm.district) params.district = queryForm.district

    const response = await alertAPI.get(params)
    if (response.status === 'success') {
      tableData.value = response.alerts || []
    }
  } catch (error) {
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  queryForm.status = ''
  queryForm.level = ''
  queryForm.district = null
  handleQuery()
}

const handleProcess = (row: any) => {
  processForm.alert_id = row.alert_id
  processForm.alert_level = row.alert_level
  processForm.noise_value = row.noise_value
  processForm.status = '处理中'
  processForm.process_notes = ''
  showProcessDialog.value = true
}

const handleView = (row: any) => {
  ElMessage.info(`告警详情: ${row.region_name} - ${row.noise_value}dB - ${row.alert_level}级别`)
}

const handleSubmitProcess = async () => {
  processing.value = true
  try {
    const userStr = localStorage.getItem('user')
    const user = userStr ? JSON.parse(userStr) : null
    
    const response = await alertAPI.update(processForm.alert_id, {
      status: processForm.status,
      handler_id: user?.user_id,
      process_notes: processForm.process_notes
    })
    
    if (response.status === 'success') {
      ElMessage.success('处理成功')
      showProcessDialog.value = false
      handleQuery()
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '处理失败')
  } finally {
    processing.value = false
  }
}

onMounted(() => {
  loadRegions()
  handleQuery()
})
</script>

<style scoped>
.alerts {
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

