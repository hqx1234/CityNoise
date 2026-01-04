<template>
  <div class="reports">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>报告管理</span>
          <el-button type="primary" @click="showGenerateDialog = true">
            <el-icon><Plus /></el-icon>
            生成报告
          </el-button>
        </div>
      </template>

      <el-form :inline="true" :model="queryForm" class="query-form">
        <el-form-item label="报告类型">
          <el-select v-model="queryForm.type" placeholder="请选择类型" clearable style="width: 150px">
            <el-option label="日报" value="日报" />
            <el-option label="周报" value="周报" />
            <el-option label="月报" value="月报" />
            <el-option label="年报" value="年报" />
            <el-option label="专项报告" value="专项报告" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="tableData" v-loading="loading" style="width: 100%">
        <el-table-column prop="report_id" label="报告ID" width="100" />
        <el-table-column prop="report_type" label="报告类型" width="120" />
        <el-table-column prop="report_period" label="报告周期" width="200" />
        <el-table-column prop="generated_at" label="生成时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.generated_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="generated_by" label="生成人" width="120" />
        <el-table-column prop="is_public" label="公开状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_public ? 'success' : 'info'" size="small">
              {{ row.is_public ? '公开' : '私有' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="handleView(row)"
            >
              查看详情
            </el-button>
            <el-button
              v-if="row.file_path"
              type="success"
              size="small"
              @click="handleDownload(row)"
            >
              下载
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 生成报告对话框 -->
    <el-dialog v-model="showGenerateDialog" title="生成报告" width="600px">
      <el-form :model="generateForm" label-width="100px">
        <el-form-item label="报告类型" required>
          <el-select v-model="generateForm.report_type" style="width: 100%" @change="handleReportTypeChange">
            <el-option label="日报" value="日报" />
            <el-option label="周报" value="周报" />
            <el-option label="月报" value="月报" />
            <el-option label="年报" value="年报" />
            <el-option label="专项报告" value="专项报告" />
          </el-select>
        </el-form-item>
        <el-form-item label="报告周期">
          <el-date-picker
            v-model="generateForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 100%"
            @change="handleDateRangeChange"
          />
        </el-form-item>
        <el-form-item label="周期显示">
          <el-input
            v-model="generateForm.report_period"
            placeholder="自动生成或手动输入"
            readonly
          />
        </el-form-item>
        <el-form-item label="公开状态">
          <el-switch v-model="generateForm.is_public" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGenerateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleGenerate" :loading="generating">生成报告</el-button>
      </template>
    </el-dialog>

    <!-- 报告详情对话框 -->
    <el-dialog v-model="showReportDialog" title="报告详情" width="800px">
      <div v-if="reportDetail" class="report-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="报告类型">{{ reportDetail.report_type }}</el-descriptions-item>
          <el-descriptions-item label="报告周期">{{ reportDetail.report_period || '无' }}</el-descriptions-item>
          <el-descriptions-item label="生成时间">{{ formatDateTime(reportDetail.generated_at) }}</el-descriptions-item>
          <el-descriptions-item label="生成人">{{ reportDetail.generated_by || '未知' }}</el-descriptions-item>
          <el-descriptions-item label="公开状态">
            <el-tag :type="reportDetail.is_public ? 'success' : 'info'" size="small">
              {{ reportDetail.is_public ? '公开' : '私有' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <el-divider>统计信息</el-divider>
        <div v-if="reportDetail.content && reportDetail.content.statistics" class="statistics-section">
          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic title="数据总数" :value="reportDetail.content.statistics.total_data_count || 0" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="平均噪音" :value="reportDetail.content.statistics.avg_noise || 0" suffix="dB" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="最大噪音" :value="reportDetail.content.statistics.max_noise || 0" suffix="dB" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="超标率" :value="reportDetail.content.statistics.exceed_rate || 0" suffix="%" />
            </el-col>
          </el-row>
          
          <el-divider />
          
          <div v-if="reportDetail.content.statistics.alert_count !== undefined">
            <h4>告警统计</h4>
            <p>总告警数: {{ reportDetail.content.statistics.alert_count }}</p>
            <div v-if="reportDetail.content.statistics.alert_by_level">
              <el-tag v-for="(count, level) in reportDetail.content.statistics.alert_by_level" 
                      :key="level" 
                      :type="level === '紧急' ? 'danger' : level === '高' ? 'warning' : 'info'"
                      style="margin-right: 10px; margin-bottom: 5px;">
                {{ level }}: {{ count }}
              </el-tag>
            </div>
          </div>

          <el-divider />

          <div v-if="reportDetail.content.region_statistics && reportDetail.content.region_statistics.length > 0">
            <h4>区域统计</h4>
            <el-table :data="reportDetail.content.region_statistics" size="small" max-height="200">
              <el-table-column prop="region_name" label="区域名称" width="150" />
              <el-table-column prop="region_type" label="区域类型" width="120" />
              <el-table-column prop="avg_noise" label="平均噪音" width="120">
                <template #default="{ row }">
                  {{ row.avg_noise }} dB
                </template>
              </el-table-column>
              <el-table-column prop="data_count" label="数据量" width="100" />
            </el-table>
          </div>

          <el-divider />

          <div v-if="reportDetail.content.recommendations && reportDetail.content.recommendations.length > 0">
            <h4>建议</h4>
            <ul>
              <li v-for="(rec, index) in reportDetail.content.recommendations" :key="index">
                {{ rec }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { reportAPI } from '../api'

const loading = ref(false)
const generating = ref(false)
const showGenerateDialog = ref(false)
const tableData = ref<any[]>([])

const queryForm = reactive({
  type: ''
})

const generateForm = reactive({
  report_type: '日报',
  dateRange: [] as string[],
  report_period: '',
  is_public: false
})

// 根据报告类型自动计算日期范围
const handleReportTypeChange = () => {
  const today = new Date()
  let startDate: Date
  let endDate: Date = new Date(today)
  
  switch (generateForm.report_type) {
    case '日报':
      startDate = new Date(today)
      endDate = new Date(today)
      break
    case '周报':
      // 本周一
      const dayOfWeek = today.getDay()
      const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
      startDate = new Date(today)
      startDate.setDate(today.getDate() + diff)
      startDate.setHours(0, 0, 0, 0)
      endDate = new Date(startDate)
      endDate.setDate(startDate.getDate() + 6)
      break
    case '月报':
      // 本月第一天
      startDate = new Date(today.getFullYear(), today.getMonth(), 1)
      // 本月最后一天
      endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0)
      break
    case '年报':
      // 今年第一天
      startDate = new Date(today.getFullYear(), 0, 1)
      // 今年最后一天
      endDate = new Date(today.getFullYear(), 11, 31)
      break
    default:
      // 专项报告：默认最近30天
      startDate = new Date(today)
      startDate.setDate(today.getDate() - 30)
      endDate = new Date(today)
  }
  
  generateForm.dateRange = [
    formatDate(startDate),
    formatDate(endDate)
  ]
  handleDateRangeChange()
}

// 格式化日期为 YYYY-MM-DD
const formatDate = (date: Date): string => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// 日期范围变化时更新周期显示
const handleDateRangeChange = () => {
  if (generateForm.dateRange && generateForm.dateRange.length === 2) {
    generateForm.report_period = `${generateForm.dateRange[0]} 至 ${generateForm.dateRange[1]}`
  } else {
    generateForm.report_period = ''
  }
}

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const handleQuery = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (queryForm.type) params.type = queryForm.type

    const response = await reportAPI.get(params)
    if (response.status === 'success') {
      tableData.value = response.reports || []
    }
  } catch (error) {
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  queryForm.type = ''
  handleQuery()
}

const handleGenerate = async () => {
  if (!generateForm.report_type) {
    ElMessage.warning('请选择报告类型')
    return
  }
  
  if (!generateForm.dateRange || generateForm.dateRange.length !== 2) {
    ElMessage.warning('请选择报告周期')
    return
  }

  generating.value = true
  try {
    const userStr = localStorage.getItem('user')
    const user = userStr ? JSON.parse(userStr) : null

    const response = await reportAPI.post({
      report_type: generateForm.report_type,
      report_period: generateForm.report_period,
      start_date: generateForm.dateRange[0],
      end_date: generateForm.dateRange[1],
      generated_by: user?.user_id || 1,
      is_public: generateForm.is_public ? 1 : 0
    })
    
    if (response.status === 'success') {
      ElMessage.success('报告生成成功')
      showGenerateDialog.value = false
      generateForm.report_type = '日报'
      generateForm.dateRange = []
      generateForm.report_period = ''
      generateForm.is_public = false
      handleQuery()
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '生成失败')
  } finally {
    generating.value = false
  }
}

const showReportDialog = ref(false)
const reportDetail = ref<any>(null)

const handleView = (row: any) => {
  // 解析报告内容
  try {
    if (row.content) {
      reportDetail.value = {
        ...row,
        content: typeof row.content === 'string' ? JSON.parse(row.content) : row.content
      }
    } else {
      reportDetail.value = row
    }
    showReportDialog.value = true
  } catch (error) {
    ElMessage.error('解析报告内容失败')
  }
}

const handleDownload = (row: any) => {
  if (row.file_path) {
    window.open(row.file_path, '_blank')
  } else {
    ElMessage.warning('报告文件不存在')
  }
}

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除报告"${row.report_type} - ${row.report_period}"吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const response = await reportAPI.delete(row.report_id)
    if (response.status === 'success') {
      ElMessage.success('删除成功')
      handleQuery() // 刷新列表
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.message || '删除失败')
    }
  }
}

onMounted(() => {
  handleQuery()
  // 初始化时设置默认日期范围
  handleReportTypeChange()
})
</script>

<style scoped>
.reports {
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

.report-detail {
  padding: 10px 0;
}

.statistics-section {
  margin-top: 20px;
}

.statistics-section h4 {
  margin: 15px 0 10px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.statistics-section ul {
  margin: 10px 0;
  padding-left: 20px;
}

.statistics-section li {
  margin: 5px 0;
  line-height: 1.8;
}
</style>

