<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="card-header">
          <h2>城市噪音污染监测管理平台</h2>
        </div>
      </template>
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="rules"
        label-width="80px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            prefix-icon="User"
          />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            @click="handleLogin"
            style="width: 100%"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authAPI } from '../api'

const router = useRouter()
const loginFormRef = ref()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  try {
    const valid = await loginFormRef.value.validate()
    if (!valid) {
      return
    }
    
    loading.value = true
    console.log('开始登录，用户名:', loginForm.username)
    
    try {
      const response = await authAPI.login(loginForm.username, loginForm.password)
      console.log('登录响应:', response)
      
      if (response && response.status === 'success') {
        localStorage.setItem('user', JSON.stringify(response.user))
        localStorage.setItem('token', 'mock-token') // 实际项目中应该使用真实的token
        ElMessage.success('登录成功')
        console.log('登录成功，准备跳转')
        await router.push('/')
        console.log('跳转完成')
      } else {
        ElMessage.error(response?.message || '登录失败')
      }
    } catch (error: any) {
      console.error('登录错误:', error)
      console.error('错误详情:', {
        message: error.message,
        response: error.response,
        data: error.response?.data
      })
      
      let errorMessage = '登录失败，请检查网络连接'
      if (error.response) {
        // 服务器返回了错误响应
        errorMessage = error.response.data?.message || error.response.data?.error || `服务器错误: ${error.response.status}`
      } else if (error.request) {
        // 请求已发出但没有收到响应
        errorMessage = '无法连接到服务器，请检查后端服务是否运行'
      } else {
        // 其他错误
        errorMessage = error.message || '登录失败'
      }
      
      ElMessage.error(errorMessage)
    } finally {
      loading.value = false
    }
  } catch (validationError) {
    console.log('表单验证失败')
    // 表单验证失败，Element Plus 会自动显示错误消息
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0;
  color: #409eff;
}
</style>

