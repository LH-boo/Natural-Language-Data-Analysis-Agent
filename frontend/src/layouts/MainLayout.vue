<template>
  <el-container class="app-shell">
    <el-aside width="232px" class="sidebar">
      <div class="brand">
        <div class="brand-logo">
          <el-icon :size="22"><DataAnalysis /></el-icon>
        </div>
        <div class="brand-text">
          <div class="brand-name">数据智析</div>
          <div class="brand-sub">自然语言数据分析</div>
        </div>
      </div>

      <el-scrollbar class="sidebar-scroll">
        <div class="menu-label">功能导航</div>
        <el-menu :default-active="activeMenu" router class="side-menu">
          <el-menu-item v-for="item in menus" :key="item.path" :index="item.path">
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
          </el-menu-item>
        </el-menu>
      </el-scrollbar>

      <div class="sidebar-foot">
        <div class="foot-card">
          <div class="foot-icon">
            <el-icon :size="18"><MagicStick /></el-icon>
          </div>
          <div>
            <div class="foot-title">自然语言分析</div>
            <div class="foot-desc">用一句话完成取数与洞察</div>
          </div>
        </div>
      </div>
    </el-aside>

    <el-container class="main-container">
      <el-header class="app-header" height="64px">
        <div class="header-left">
          <h1 class="header-title">{{ pageTitle }}</h1>
          <span class="header-divider"></span>
          <span class="header-subtitle">{{ pageSubtitle }}</span>
        </div>
        <div class="header-right">
          <span
            class="service-state"
            :class="health.ok === true ? 'is-online' : health.ok === false ? 'is-offline' : ''"
          >
            <i class="dot"></i>
            {{
              health.ok === true
                ? `服务正常 · v${health.version}`
                : health.ok === false
                  ? '服务未连接'
                  : '服务检测中'
            }}
          </span>
          <el-tooltip content="刷新服务状态" placement="bottom">
            <el-button :icon="Refresh" circle size="small" @click="checkHealth" />
          </el-tooltip>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <AiAssistant />
  </el-container>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  ChatDotRound,
  Clock,
  Coin,
  Connection,
  DataAnalysis,
  Document,
  MagicStick,
  Monitor,
  Notebook,
  PieChart,
  Refresh,
  View
} from '@element-plus/icons-vue'
import AiAssistant from '../components/AiAssistant.vue'
import { api } from '../api'

const route = useRoute()

const menus = [
  { path: '/', title: '数据分析首页', icon: DataAnalysis },
  { path: '/chat', title: 'AI 智能分析', icon: ChatDotRound },
  { path: '/datasets', title: '数据集管理', icon: Coin },
  { path: '/preview', title: '数据预览', icon: View },
  { path: '/connections', title: '数据库连接', icon: Connection },
  { path: '/sql', title: 'SQL 查询管理', icon: Document },
  { path: '/visualization', title: '数据可视化', icon: PieChart },
  { path: '/reports', title: '分析报告', icon: Notebook },
  { path: '/history', title: '历史会话', icon: Clock },
  { path: '/monitoring', title: '系统监控', icon: Monitor }
]

const activeMenu = computed(() => route.path)
const pageTitle = computed(() => route.meta?.title || '数据分析')
const pageSubtitle = computed(() => route.meta?.subtitle || '')
const health = ref({ ok: null, version: '' })
let healthTimer = null

async function checkHealth() {
  try {
    const res = await api.health(true)
    health.value = { ok: true, version: res.version || '' }
  } catch (error) {
    health.value = { ok: false, version: '' }
  }
}

onMounted(() => {
  checkHealth()
  healthTimer = setInterval(checkHealth, 60000)
})

onBeforeUnmount(() => {
  if (healthTimer) clearInterval(healthTimer)
})
</script>

<style scoped>
.app-shell {
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  position: relative;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
  color: #dbe5f8;
  background: linear-gradient(180deg, #0a1124 0%, #101d3d 54%, #0c1730 100%);
}

.sidebar::before {
  content: '';
  position: absolute;
  top: -100px;
  right: -90px;
  width: 260px;
  height: 260px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(79, 124, 255, 0.28), transparent 68%);
  pointer-events: none;
}

.sidebar::after {
  content: '';
  position: absolute;
  bottom: 60px;
  left: -100px;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(124, 92, 255, 0.16), transparent 68%);
  pointer-events: none;
}

.brand {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 11px;
  height: 72px;
  padding: 0 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.brand-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  color: #fff;
  background: linear-gradient(135deg, #4f7cff, #7c5cff);
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(79, 124, 255, 0.4);
}

.brand-name {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #fff;
}

.brand-sub {
  margin-top: 2px;
  font-size: 9px;
  letter-spacing: 1.4px;
  color: rgba(167, 188, 225, 0.62);
}

.sidebar-scroll {
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 0;
}

.menu-label {
  padding: 20px 24px 8px;
  font-size: 11px;
  letter-spacing: 1px;
  color: rgba(150, 172, 212, 0.55);
}

.side-menu {
  padding: 0 10px 10px;
  border-right: none;
  background: transparent;
}

.side-menu :deep(.el-menu-item) {
  position: relative;
  height: 43px;
  line-height: 43px;
  margin: 4px 0;
  padding: 0 14px !important;
  font-size: 13.5px;
  color: rgba(205, 219, 243, 0.72);
  border-radius: 10px;
  transition: all 0.18s ease;
}

.side-menu :deep(.el-menu-item .el-icon) {
  margin-right: 10px;
  font-size: 18px;
  color: rgba(165, 187, 227, 0.7);
}

.side-menu :deep(.el-menu-item:hover) {
  color: #fff;
  background: rgba(79, 124, 255, 0.13);
}

.side-menu :deep(.el-menu-item.is-active) {
  color: #fff;
  background: linear-gradient(90deg, rgba(79, 124, 255, 0.32), rgba(79, 124, 255, 0.1));
  box-shadow: inset 0 0 0 1px rgba(124, 156, 255, 0.18);
}

.side-menu :deep(.el-menu-item.is-active .el-icon) {
  color: #a9c0ff;
}

.side-menu :deep(.el-menu-item.is-active::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: #7c9cff;
}

.sidebar-foot {
  position: relative;
  z-index: 1;
  padding: 14px;
}

.foot-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 13px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
}

.foot-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex: none;
  color: #a9c0ff;
  background: rgba(79, 124, 255, 0.22);
  border-radius: 9px;
}

.foot-title {
  font-size: 12px;
  color: rgba(226, 235, 250, 0.9);
}

.foot-desc {
  margin-top: 3px;
  font-size: 10.5px;
  color: rgba(160, 180, 215, 0.55);
}

.main-container {
  height: 100vh;
  min-width: 0;
  overflow: hidden;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.88);
  border-bottom: 1px solid var(--line);
  backdrop-filter: blur(10px);
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
  min-width: 0;
}

.header-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--ink);
  white-space: nowrap;
}

.header-divider {
  width: 1px;
  height: 12px;
  background: #dbe3f1;
  align-self: center;
}

.header-subtitle {
  font-size: 12px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: none;
}

.service-state {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 11px;
  font-size: 12px;
  color: #5b6b88;
  background: #f6f8fd;
  border: 1px solid #e9eef8;
  border-radius: 20px;
}

.service-state .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #cbd5e1;
}

.service-state.is-online {
  color: #0f9d85;
  background: #effaf7;
  border-color: #d6f3ec;
}

.service-state.is-online .dot {
  background: #22c3a6;
  box-shadow: 0 0 0 3px rgba(34, 195, 166, 0.16);
}

.service-state.is-offline {
  color: #d64b68;
  background: #fff4f6;
  border-color: #f8dce3;
}

.service-state.is-offline .dot {
  background: #ef5b7b;
}

.app-main {
  padding: 20px 22px 26px;
  overflow-y: auto;
  background: radial-gradient(circle at 88% -8%, rgba(79, 124, 255, 0.06), transparent 34%), var(--bg);
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (max-width: 1000px) {
  .header-subtitle,
  .header-divider {
    display: none;
  }
}
</style>
