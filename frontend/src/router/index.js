import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '数据分析首页', subtitle: '平台运行概览与最近分析动态' }
      },
      {
        path: 'chat',
        name: 'chat',
        component: () => import('../views/Chat.vue'),
        meta: { title: 'AI 智能分析', subtitle: '用自然语言提问，自动生成 SQL、图表与分析结论' }
      },
      {
        path: 'datasets',
        name: 'datasets',
        component: () => import('../views/Datasets.vue'),
        meta: { title: '数据集管理', subtitle: '上传 CSV 文件或加载示例数据' }
      },
      {
        path: 'preview',
        name: 'preview',
        component: () => import('../views/Preview.vue'),
        meta: { title: '数据预览', subtitle: '查看字段类型、缺失值与原始数据' }
      },
      {
        path: 'connections',
        name: 'connections',
        component: () => import('../views/Connections.vue'),
        meta: { title: '数据库连接', subtitle: '接入 MySQL、PostgreSQL 与 SQLite 数据源' }
      },
      {
        path: 'sql',
        name: 'sql',
        component: () => import('../views/SqlQuery.vue'),
        meta: { title: 'SQL 查询管理', subtitle: '编写只读 SQL，安全执行并查看结果' }
      },
      {
        path: 'visualization',
        name: 'visualization',
        component: () => import('../views/Visualization.vue'),
        meta: { title: '数据可视化', subtitle: '选择维度与指标，快速生成可视化图表' }
      },
      {
        path: 'reports',
        name: 'reports',
        component: () => import('../views/Reports.vue'),
        meta: { title: '分析报告', subtitle: '浏览、查看并导出历史分析报告' }
      },
      {
        path: 'history',
        name: 'history',
        component: () => import('../views/History.vue'),
        meta: { title: '历史会话', subtitle: '回顾历史分析对话并继续追问' }
      },
      {
        path: 'monitoring',
        name: 'monitoring',
        component: () => import('../views/Monitoring.vue'),
        meta: { title: '系统监控', subtitle: '服务健康、LLM 配置、存储与 SQL 执行日志' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.afterEach((to) => {
  const title = to.meta?.title
  document.title = title ? `${title} · 自然语言数据分析 Agent` : '自然语言数据分析 Agent'
})

export default router
