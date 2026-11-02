<template>
  <div v-loading="loading" class="page dashboard">
    <div class="overview-bar">
      <div class="overview-text">
        <span class="pulse"></span>
        <span class="overview-label">数据概览</span>
        <span class="muted">平台核心指标与最近分析动态</span>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadDashboard">刷新数据</el-button>
    </div>

    <div class="grid grid-6">
      <StatCard
        v-for="card in statCards"
        :key="card.label"
        :label="card.label"
        :value="card.value"
        :hint="card.hint"
        :icon="card.icon"
        :color="card.color"
      />
    </div>

    <div class="grid dashboard-charts">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">近 7 天分析任务</div>
            <div class="panel-subtitle">每日完成的分析任务数量</div>
          </div>
          <el-tag size="small" effect="plain">最近 7 天</el-tag>
        </div>
        <div class="panel-body">
          <ChartPanel :option="lineOption" height="280px" empty-text="暂无任务趋势数据" />
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">图表类型分布</div>
            <div class="panel-subtitle">历史分析结果使用的图表类型</div>
          </div>
        </div>
        <div class="panel-body">
          <ChartPanel :option="pieOption" height="280px" empty-text="暂无图表统计数据" />
        </div>
      </div>
    </div>

    <div class="grid dashboard-lower">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">最近分析记录</div>
            <div class="panel-subtitle">最新 8 条智能分析任务</div>
          </div>
          <el-button link type="primary" @click="router.push('/reports')">
            查看全部
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
        <div class="panel-body">
          <el-table :data="recentTasks" size="small" empty-text="暂无分析记录">
            <el-table-column prop="question" label="分析问题" min-width="220" show-overflow-tooltip />
            <el-table-column prop="dataset_name" label="数据集" width="130" show-overflow-tooltip />
            <el-table-column label="图表类型" width="100">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ chartTypeLabel(row.chart_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="row_count" label="返回行数" width="90" align="right" />
            <el-table-column label="耗时" width="90" align="right">
              <template #default="{ row }">{{ formatDuration(row.execution_time) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'success' ? 'success' : 'danger'">
                  {{ row.status === 'success' ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="150">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="70" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openDetail(row)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">快捷入口</div>
        </div>
        <div class="panel-body quick-list">
          <button
            v-for="item in quickLinks"
            :key="item.path"
            type="button"
            class="quick-item"
            @click="router.push(item.path)"
          >
            <span class="quick-icon" :style="{ color: item.color, backgroundColor: `${item.color}1a` }">
              <el-icon :size="19"><component :is="item.icon" /></el-icon>
            </span>
            <span class="quick-text">
              <span class="quick-title">{{ item.title }}</span>
              <span class="quick-desc">{{ item.desc }}</span>
            </span>
            <el-icon class="quick-arrow"><ArrowRight /></el-icon>
          </button>
        </div>
      </div>
    </div>

    <el-drawer v-model="detailVisible" title="分析详情" size="680px">
      <div v-loading="detailLoading" class="detail-body">
        <ResultView v-if="detail" :payload="detail" />
        <el-empty v-else-if="!detailLoading" description="暂无分析详情" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight,
  ChatDotRound,
  Coin,
  Connection,
  DataAnalysis,
  Document,
  MagicStick,
  Monitor,
  Notebook,
  PieChart,
  Refresh,
  Timer
} from '@element-plus/icons-vue'
import { api } from '../api'
import ChartPanel from '../components/ChartPanel.vue'
import ResultView from '../components/ResultView.vue'
import StatCard from '../components/StatCard.vue'
import { chartTypeLabel } from '../utils/constants'
import { formatDateTime, formatDuration } from '../utils/format'

const router = useRouter()
const loading = ref(false)
const dashboard = ref({
  stats: {},
  recent_tasks: [],
  chart_distribution: [],
  daily_tasks: []
})
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)

const stats = computed(() => dashboard.value.stats || {})
const recentTasks = computed(() => dashboard.value.recent_tasks || [])

const statCards = computed(() => [
  {
    label: '数据集总数',
    value: stats.value.dataset_count ?? 0,
    hint: '已导入的数据集',
    icon: Coin,
    color: '#4f7cff'
  },
  {
    label: '分析任务',
    value: stats.value.task_count ?? 0,
    hint: '累计完成的智能分析',
    icon: DataAnalysis,
    color: '#22c3a6'
  },
  {
    label: '对话会话',
    value: stats.value.conversation_count ?? 0,
    hint: '累计分析会话数',
    icon: ChatDotRound,
    color: '#8b5cf6'
  },
  {
    label: '分析报告',
    value: stats.value.report_count ?? 0,
    hint: '可导出报告数量',
    icon: Document,
    color: '#f6a93b'
  },
  {
    label: '平均耗时',
    value: formatDuration(stats.value.avg_execution_time),
    hint: '分析任务平均执行耗时',
    icon: Timer,
    color: '#38bdf8'
  },
  {
    label: 'LLM 状态',
    value: stats.value.llm_configured ? '已接入' : '未配置',
    hint: stats.value.llm_configured ? '智能生成 SQL 与结论' : '当前使用规则解析',
    icon: MagicStick,
    color: stats.value.llm_configured ? '#22c3a6' : '#f6a93b'
  }
])

const lineOption = computed(() => {
  const daily = dashboard.value.daily_tasks || []
  return {
    color: ['#4f7cff'],
    tooltip: { trigger: 'axis', axisPointer: { type: 'line' } },
    grid: { left: 18, right: 20, top: 26, bottom: 12, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: daily.map((item) => item.date),
      axisLine: { lineStyle: { color: '#dbe4f3' } },
      axisTick: { show: false },
      axisLabel: { color: '#71809b' }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { type: 'dashed', color: '#edf2fa' } },
      axisLabel: { color: '#71809b' }
    },
    series: [
      {
        name: '分析任务',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        data: daily.map((item) => item.count),
        lineStyle: { width: 3 },
        itemStyle: { borderWidth: 2, borderColor: '#fff' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(79, 124, 255, 0.26)' },
              { offset: 1, color: 'rgba(79, 124, 255, 0.02)' }
            ]
          }
        }
      }
    ]
  }
})

const pieOption = computed(() => {
  const distribution = dashboard.value.chart_distribution || []
  if (!distribution.length) return null
  return {
    color: ['#4f7cff', '#22c3a6', '#f6a93b', '#ef5b7b', '#8b5cf6', '#38bdf8'],
    tooltip: { trigger: 'item', formatter: '{b}：{c} 次（{d}%）' },
    legend: { bottom: 0, type: 'scroll', textStyle: { color: '#5b6b88', fontSize: 12 } },
    series: [
      {
        type: 'pie',
        radius: ['44%', '68%'],
        center: ['50%', '45%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { formatter: '{b}\n{d}%', color: '#5b6b88', fontSize: 11 },
        labelLine: { length: 8, length2: 8 },
        data: distribution.map((item) => ({
          name: chartTypeLabel(item.name),
          value: item.value
        }))
      }
    ]
  }
})

const quickLinks = [
  {
    title: 'AI 智能分析',
    desc: '用自然语言提问，自动生成 SQL 与图表',
    path: '/chat',
    icon: ChatDotRound,
    color: '#4f7cff'
  },
  {
    title: '数据集管理',
    desc: '上传 CSV 或加载示例数据',
    path: '/datasets',
    icon: Coin,
    color: '#22c3a6'
  },
  {
    title: 'SQL 查询管理',
    desc: '编写只读 SQL 并安全执行',
    path: '/sql',
    icon: Document,
    color: '#8b5cf6'
  },
  {
    title: '数据可视化',
    desc: '选择维度与指标快速生成图表',
    path: '/visualization',
    icon: PieChart,
    color: '#f6a93b'
  },
  {
    title: '分析报告',
    desc: '查看并导出历史分析报告',
    path: '/reports',
    icon: Notebook,
    color: '#ef5b7b'
  },
  {
    title: '系统监控',
    desc: '服务健康、LLM 与存储状态',
    path: '/monitoring',
    icon: Monitor,
    color: '#38bdf8'
  }
]

async function loadDashboard() {
  loading.value = true
  try {
    dashboard.value = await api.dashboard()
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    loading.value = false
  }
}

async function openDetail(row) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await api.reportDetail(row.id)
  } catch (error) {
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

onMounted(loadDashboard)
</script>

<style scoped>
.overview-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
}

.overview-text {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 12.5px;
}

.overview-label {
  font-weight: 600;
  color: var(--ink);
}

.pulse {
  position: relative;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary);
  box-shadow: 0 0 0 4px rgba(79, 124, 255, 0.14);
}

.dashboard-charts {
  grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr);
}

.dashboard-lower {
  grid-template-columns: minmax(0, 1.65fr) minmax(0, 1fr);
}

.quick-list {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.quick-item {
  display: flex;
  align-items: center;
  gap: 11px;
  width: 100%;
  padding: 11px 12px;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  background: #fbfcff;
  border: 1px solid #edf2fa;
  border-radius: 11px;
  transition: all 0.18s ease;
}

.quick-item:hover {
  background: #f4f8ff;
  border-color: #cfdcff;
  transform: translateX(2px);
}

.quick-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  flex: none;
  border-radius: 10px;
}

.quick-text {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.quick-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}

.quick-desc {
  font-size: 11.5px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quick-arrow {
  margin-left: auto;
  color: #b9c5d9;
  flex: none;
}

.detail-body {
  min-height: 200px;
}

@media (max-width: 1240px) {
  .dashboard-charts,
  .dashboard-lower {
    grid-template-columns: 1fr;
  }
}
</style>
