<template>
  <el-container class="main-container">
    <el-header class="header">
      <div class="header-left">
        <h2>城市噪音污染监测管理平台</h2>
      </div>
      <div class="header-right">
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-icon><User /></el-icon>
            {{ userInfo?.username || '用户' }}
            <el-icon class="el-icon--right"><arrow-down /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    <el-container>
      <el-aside width="200px" class="aside">
        <el-menu
          :default-active="activeMenu"
          router
          class="sidebar-menu"
        >
          <el-menu-item index="/dashboard">
            <el-icon><Odometer /></el-icon>
            <span>仪表板</span>
          </el-menu-item>
          <el-menu-item index="/noise-data">
            <el-icon><DataLine /></el-icon>
            <span>噪音数据</span>
          </el-menu-item>
          <el-menu-item index="/alerts">
            <el-icon><Bell /></el-icon>
            <span>告警管理</span>
          </el-menu-item>
          <el-menu-item index="/statistics">
            <el-icon><PieChart /></el-icon>
            <span>统计分析</span>
          </el-menu-item>
          <el-menu-item index="/map">
            <el-icon><MapLocation /></el-icon>
            <span>地图展示</span>
          </el-menu-item>
          <el-menu-item index="/regions">
            <el-icon><Location /></el-icon>
            <span>监测区域</span>
          </el-menu-item>
          <el-menu-item index="/devices">
            <el-icon><Monitor /></el-icon>
            <span>监测设备</span>
          </el-menu-item>
          <el-menu-item index="/reports">
            <el-icon><Document /></el-icon>
            <span>报告管理</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  User,
  ArrowDown,
  Odometer,
  DataLine,
  Bell,
  PieChart,
  MapLocation,
  Location,
  Monitor,
  Document
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => route.path)
const userInfo = computed(() => {
  const userStr = localStorage.getItem('user')
  return userStr ? JSON.parse(userStr) : null
})

const handleCommand = (command: string) => {
  if (command === 'logout') {
    localStorage.removeItem('user')
    localStorage.removeItem('token')
    router.push('/login')
  }
}
</script>

<style scoped>
.main-container {
  height: 100vh;
}

.header {
  background-color: #409eff;
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
}

.aside {
  background-color: #304156;
}

.sidebar-menu {
  border-right: none;
  background-color: #304156;
}

.sidebar-menu :deep(.el-menu-item) {
  color: #bfcbd9;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background-color: #409eff;
  color: white;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background-color: #263445;
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
}
</style>

