<template>
  <div class="page" v-loading="loading">
    <div class="panel status-hero">
      <div class="hero-left">
        <div class="status-icon">
          <el-icon :size="26"><Monitor /></el-icon>
        </div>
        <div>
          <div class="hero-title">
            系统运行正常
            <el-tag size="small" type="success" effect="dark">运行中</el-tag>
          </div>
          <div class="hero-sub">
            已稳定运行 {{ formatUptime(monitoring?.uptime_seconds) }} · 版本 v{{ monitoring?.version || '-' }}
          </div>
        </div>
      </div>
      <div class="hero-right">
        <div class="hero-meta">
          <span>LLM 状态</span>
          <strong :class="llm.configured ? 'text-success' : 'text-danger'">
            {{ llm.configured ? '已配置' : '未配置' }}
          </strong>
        </div>
        <div class="hero-meta">
          <span>SQL 日志</span>
          <strong>{{ counts.sql_logs ?? 0 }}</strong>
        </div>
        <el-button :icon="Refresh" :loading="loading" @click="loadMonitoring">刷新状态</el-button>
      </div>
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

    <div class="grid monitoring-info">
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">LLM 配置</div>
          <el-tag size="small" :type="llm.configured ? 'success' : 'warning'" effect="plain">
            {{ llm.configured ? '已接入' : '未配置' }}
          </el-tag>
        </div>
        <div class="panel-body">
          <div class="info-row">
            <span class="info-label">模型名称</span>
            <span class="info-value code-text">{{ llm.model || '-' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">接口地址</span>
            <span class="info-value code-text">{{ llm.base_url || '-' }}</span>
          </div>
          <el-alert
            v-if="!llm.configured"
            type="warning"
            :closable="false"
            show-icon
            title="LLM 未配置"
            description="系统将使用规则解析生成 SQL；配置大模型后可获得更灵活的自然语言理解能力。"
            class="info-alert"
          />
          <el-alert
            v-else
            type="success"
            :closable="false"
            show-icon
            title="LLM 已接入"
            description="自然语言问题将优先由大模型理解并生成 SQL。"
            class="info-alert"
          />
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">存储配置</div>
          <el-tag size="small" effect="plain" type="info">本地存储</el-tag>
        </div>
        <div class="panel-body">
          <div class="storage-block">
            <div class="storage-head">
              <span class="storage-icon"><el-icon><FolderOpened /></el-icon></span>
              <span>元数据存储</span>
            </div>
            <div class="storage-path code-text">{{ storage.metadata || '-' }}</div>
          </div>
          <div class="storage-block">
            <div class="storage-head">
              <span class="storage-icon"><el-icon><Coin /></el-icon></span>
              <span>DuckDB 数据文件</span>
            </div>
            <div class="storage-path code-text">{{ storage.duckdb || '-' }}</div>
          </div>
          <div class="storage-tip">
            数据集与分析结果保存在本地 DuckDB 中，SQL 执行采用只读模式。
          </div>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">最近 SQL 执行日志</div>
          <div class="panel-subtitle">包含正常执行、异常与安全拦截记录</div>
        </div>
        <div class="log-tags">
          <el-tag size="small" effect="plain" type="danger">异常 {{ counts.errors ?? 0 }}</el-tag>
          <el-tag size="small" effect="plain" type="warning">拦截 {{ counts.blocked ?? 0 }}</el-tag>
        </div>
      </div>
      <div class="panel-body">
        <el-table :data="recentLogs" size="small" max-height="360" empty-text="暂无 SQL 执行日志">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="task_id" label="任务" width="70">
            <template #default="{ row }">{{ row.task_id ?? '-' }}</template>
          </el-table-column>
          <el-table-column label="SQL 语句" min-width="280" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="code-text">{{ row.sql }}</span>
            </template>
          </el-table-column>
          <el-table-column label="安全校验" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="row.is_safe ? 'success' : 'danger'" effect="plain">
                {{ row.is_safe ? '通过' : '已拦截' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="result_count" label="结果行数" width="90" align="right" />
          <el-table-column label="耗时" width="90" align="right">
            <template #default="{ row }">{{ formatDuration(row.execution_time) }}</template>
          </el-table-column>
          <el-table-column label="错误信息" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <span :class="{ 'text-danger': row.error_message }">{{ row.error_message || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="执行时间" width="155">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  Coin,
  DataAnalysis,
  Document,
  FolderOpened,
  Lock,
  Monitor,
  Refresh,
  Timer,
  WarningFilled
} from '@element-plus/icons-vue'
import { api } from '../api'
import StatCard from '../components/StatCard.vue'
import { formatDateTime, formatDuration, formatUptime } from '../utils/format'

const monitoring = ref(null)
const loading = ref(true)

const llm = computed(() => monitoring.value?.llm || {})
const storage = computed(() => monitoring.value?.storage || {})
const counts = computed(() => monitoring.value?.counts || {})
const recentLogs = computed(() => monitoring.value?.recent_logs || [])

const statCards = computed(() => [
  {
    label: '数据集',
    value: counts.value.datasets ?? 0,
    hint: '已导入的数据集',
    icon: Coin,
    color: '#4f7cff'
  },
  {
    label: '分析任务',
    value: counts.value.tasks ?? 0,
    hint: '累计分析任务',
    icon: DataAnalysis,
    color: '#22c3a6'
  },
  {
    label: 'SQL 日志',
    value: counts.value.sql_logs ?? 0,
    hint: '累计执行记录',
    icon: Document,
    color: '#8b5cf6'
  },
  {
    label: '异常日志',
    value: counts.value.errors ?? 0,
    hint: '存在错误信息的记录',
    icon: WarningFilled,
    color: '#ef5b7b'
  },
  {
    label: '安全拦截',
    value: counts.value.blocked ?? 0,
    hint: '被安全校验拦截的 SQL',
    icon: Lock,
    color: '#f6a93b'
  },
  {
    label: '平均耗时',
    value: formatDuration(counts.value.avg_execution_time),
    hint: 'SQL 平均执行耗时',
    icon: Timer,
    color: '#38bdf8'
  }
])

async function loadMonitoring() {
  loading.value = true
  try {
    monitoring.value = await api.monitoring()
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    loading.value = false
  }
}

onMounted(loadMonitoring)
</script>

<style scoped>
.status-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 20px 22px;
  background: linear-gradient(115deg, #ffffff 0%, #f7faff 62%, #eef4ff 100%);
  border: 1px solid #e3ebfa;
  flex-wrap: wrap;
}

.hero-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  color: #fff;
  background: linear-gradient(135deg, #22c3a6, #14a58d);
  border-radius: 16px;
  box-shadow: 0 10px 22px rgba(34, 195, 166, 0.26);
}

.hero-title {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 18px;
  font-weight: 700;
  color: var(--ink);
}

.hero-sub {
  margin-top: 6px;
  font-size: 12.5px;
  color: var(--muted);
}

.hero-right {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.hero-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: var(--muted);
}

.hero-meta strong {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.monitoring-info {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.info-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 11px 0;
  border-bottom: 1px dashed #edf2fa;
}

.info-row:first-child {
  padding-top: 0;
}

.info-label {
  flex: none;
  font-size: 12.5px;
  color: var(--muted);
}

.info-value {
  text-align: right;
  word-break: break-all;
}

.info-alert {
  margin-top: 14px;
}

.storage-block {
  padding: 12px 14px;
  margin-bottom: 10px;
  background: #fafcff;
  border: 1px solid #edf2fa;
  border-radius: 11px;
}

.storage-head {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12.5px;
  font-weight: 500;
  color: #33445f;
}

.storage-icon {
  display: inline-flex;
  align-items: center;
  color: var(--primary);
}

.storage-path {
  margin-top: 8px;
  padding: 7px 9px;
  background: #f3f6fd;
  border-radius: 7px;
  word-break: break-all;
}

.storage-tip {
  font-size: 11.5px;
  line-height: 1.7;
  color: var(--muted);
}

.log-tags {
  display: flex;
  gap: 8px;
}

@media (max-width: 1100px) {
  .monitoring-info {
    grid-template-columns: 1fr;
  }
}
</style>
