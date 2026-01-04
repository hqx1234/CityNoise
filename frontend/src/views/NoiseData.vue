<template>
  <div class="noise-data">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>噪音数据查询</span>
          <el-button type="primary" @click="showUploadDialog = true">
            <el-icon><Upload /></el-icon>
            上传数据
          </el-button>
        </div>
      </template>

      <el-form :inline="true" :model="queryForm" class="query-form">
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
        <el-form-item label="设备">
          <el-select v-model="queryForm.device_id" placeholder="请选择设备" clearable style="width: 200px">
            <el-option
              v-for="device in devices"
              :key="device.device_id"
              :label="device.device_id"
              :value="device.device_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker
            v-model="queryForm.start_time"
            type="datetime"
            placeholder="选择开始时间"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker
            v-model="queryForm.end_time"
            type="datetime"
            placeholder="选择结束时间"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" v-loading="loading" style="width: 100%">
        <el-table-column prop="noise_id" label="ID" width="80" />
        <el-table-column prop="noise_value" label="噪音值(dB)" width="120">
          <template #default="{ row }">
            <span :style="{ color: row.is_exceeded ? '#f56c6c' : '#67c23a' }">
              {{ row.noise_value }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="region_name" label="区域" width="150" />
        <el-table-column prop="device_id" label="设备ID" width="120" />
        <el-table-column prop="timestamp" label="时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column prop="data_quality" label="数据质量" width="120">
          <template #default="{ row }">
            <el-tag :type="getQualityTagType(row.data_quality)" size="small">
              {{ row.data_quality }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_exceeded" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_exceeded ? 'danger' : 'success'" size="small">
              {{ row.is_exceeded ? '超标' : '正常' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleQuery"
        @current-change="handleQuery"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </el-card>

    <!-- 上传数据对话框 -->
    <el-dialog v-model="showUploadDialog" title="上传噪音数据" width="500px">
      <el-form :model="uploadForm" label-width="100px">
        <el-form-item label="噪音值" required>
          <el-input-number v-model="uploadForm.noise_value" :min="0" :max="200" />
        </el-form-item>
        <el-form-item label="设备ID" required>
          <el-select v-model="uploadForm.device_id" placeholder="请选择设备" style="width: 100%">
            <el-option
              v-for="device in devices"
              :key="device.device_id"
              :label="device.device_id"
              :value="device.device_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="区域" required>
          <el-select v-model="uploadForm.district" placeholder="请选择区域" style="width: 100%">
            <el-option
              v-for="region in regions"
              :key="region.region_id"
              :label="region.region_name"
              :value="region.district || region.region_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="数据质量">
          <el-select v-model="uploadForm.data_quality" style="width: 100%">
            <el-option label="优秀" value="优秀" />
            <el-option label="良好" value="良好" />
            <el-option label="一般" value="一般" />
            <el-option label="较差" value="较差" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" @click="handleUpload" :loading="uploading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import { noiseDataAPI, regionAPI, deviceAPI } from '../api'

const loading = ref(false)
const uploading = ref(false)
const showUploadDialog = ref(false)
const tableData = ref<any[]>([])
const regions = ref<any[]>([])
const devices = ref<any[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const queryForm = reactive({
  district: null as string | null,
  device_id: '',
  start_time: '',
  end_time: ''
})

const uploadForm = reactive({
  noise_value: 0,
  device_id: '',
  district: null as string | null,
  data_quality: '良好'
})

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const getQualityTagType = (quality: string) => {
  const map: Record<string, string> = {
    '优秀': 'success',
    '良好': 'info',
    '一般': 'warning',
    '较差': 'danger'
  }
  return map[quality] || 'info'
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

const loadDevices = async () => {
  try {
    const response = await deviceAPI.get()
    if (response.status === 'success') {
      devices.value = response.devices || []
    }
  } catch (error) {
    console.error('加载设备失败:', error)
  }
}

const handleQuery = async () => {
  loading.value = true
  try {
    const params: any = {
      limit: pageSize.value
    }
    if (queryForm.district) params.district = queryForm.district
    if (queryForm.device_id) params.device_id = queryForm.device_id
    if (queryForm.start_time) params.start_time = queryForm.start_time
    if (queryForm.end_time) params.end_time = queryForm.end_time

    const response = await noiseDataAPI.get(params)
    if (response.status === 'success') {
      tableData.value = response.data || []
      total.value = response.count || 0
    }
  } catch (error) {
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  queryForm.district = null
  queryForm.device_id = ''
  queryForm.start_time = ''
  queryForm.end_time = ''
  handleQuery()
}

const handleUpload = async () => {
  if (!uploadForm.device_id || !uploadForm.district) {
    ElMessage.warning('请填写完整信息')
    return
  }

  uploading.value = true
  try {
    const response = await noiseDataAPI.post({
      noise_value: uploadForm.noise_value,
      device_id: uploadForm.device_id,
      district: uploadForm.district,
      data_quality: uploadForm.data_quality
    })
    if (response.status === 'success') {
      ElMessage.success('上传成功')
      showUploadDialog.value = false
      uploadForm.noise_value = 0
      uploadForm.device_id = ''
      uploadForm.district = null
      handleQuery()
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

onMounted(() => {
  loadRegions()
  loadDevices()
  handleQuery()
})
</script>

<style scoped>
.noise-data {
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

