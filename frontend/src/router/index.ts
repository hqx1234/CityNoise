import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '仪表板' }
      },
      {
        path: 'noise-data',
        name: 'NoiseData',
        component: () => import('../views/NoiseData.vue'),
        meta: { title: '噪音数据' }
      },
      {
        path: 'alerts',
        name: 'Alerts',
        component: () => import('../views/Alerts.vue'),
        meta: { title: '告警管理' }
      },
      {
        path: 'statistics',
        name: 'Statistics',
        component: () => import('../views/Statistics.vue'),
        meta: { title: '统计分析' }
      },
      {
        path: 'map',
        name: 'Map',
        component: () => import('../views/Map.vue'),
        meta: { title: '地图展示' }
      },
      {
        path: 'regions',
        name: 'Regions',
        component: () => import('../views/Regions.vue'),
        meta: { title: '监测区域' }
      },
      {
        path: 'devices',
        name: 'Devices',
        component: () => import('../views/Devices.vue'),
        meta: { title: '监测设备' }
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('../views/Reports.vue'),
        meta: { title: '报告管理' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const user = localStorage.getItem('user')
  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth && !user) {
    next('/login')
  } else if (to.path === '/login' && user) {
    next('/')
  } else {
    next()
  }
})

export default router

