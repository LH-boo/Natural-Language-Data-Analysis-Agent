<template>
  <div v-if="payload" class="result-view" :class="{ 'is-compact': compact }">
    <div class="result-meta">
      <el-tag size="small" effect="plain" type="info">返回 {{ payload.row_count ?? 0 }} 行</el-tag>
      <el-tag size="small" effect="plain">耗时 {{ formatDuration(payload.execution_time) }}</el-tag>
      <el-tag size="small" effect="plain" :type="payload.llm_used ? 'success' : 'info'">
        {{ payload.llm_used ? 'LLM 生成' : '规则解析' }}
      </el-tag>
      <el-tag size="small" effect="plain">{{ chartTypeLabel(payload.chart_type) }}</el-tag>
    </div>

    <div v-if="showResolved" class="resolved-question">
      <span class="resolved-label">理解后的问题</span>
      <span>{{ payload.resolved_question }}</span>
    </div>

    <el-alert
      v-if="payload.success === false"
      class="result-alert"
      type="error"
      :closable="false"
      show-icon
      title="分析未成功完成"
      :description="warningsText || '请调整问题描述或检查数据集后重试'"
    />
    <el-alert
      v-else-if="warnings.length"
      class="result-alert"
      type="warning"
      :closable="false"
      show-icon
      title="分析提示"
    >
      <template #default>
        <div v-for="(item, index) in warnings" :key="index" class="warning-item">{{ item }}</div>
      </template>
    </el-alert>

    <div v-if="payload.analysis" class="analysis-block">
      <div class="block-label">
        <el-icon><MagicStick /></el-icon>
        <span>分析结论</span>
      </div>
      <p class="analysis-text">{{ payload.analysis }}</p>
    </div>

    <div v-if="payload.chart" class="chart-block">
      <ChartPanel :option="payload.chart" :height="compact ? '220px' : '330px'" />
    </div>
    <div v-else-if="payload.success !== false" class="no-chart">
      <el-icon><Histogram /></el-icon>
      <span>{{ payload.row_count ? '本次结果以数据表形式呈现' : '本次分析未返回可用数据' }}</span>
    </div>

    <el-collapse v-if="payload.sql" v-model="activePanels" class="result-collapse">
      <el-collapse-item name="sql">
        <template #title>
          <span class="collapse-title">
            <el-icon><Document /></el-icon>
            查看生成的 SQL
          </span>
        </template>
        <div v-if="payload.sql_explanation" class="sql-explain">{{ payload.sql_explanation }}</div>
        <pre class="sql-code">{{ payload.sql }}</pre>
      </el-collapse-item>
    </el-collapse>

    <div v-if="!compact && steps.length" class="steps-block">
      <div class="block-title">Agent 执行步骤</div>
      <el-timeline>
        <el-timeline-item
          v-for="step in steps"
          :key="step.key"
          :type="step.status === 'error' ? 'danger' : 'success'"
          :hollow="step.status !== 'success'"
        >
          <div class="step-title">{{ step.title }}</div>
          <div v-if="step.detail" class="step-detail">{{ step.detail }}</div>
        </el-timeline-item>
      </el-timeline>
    </div>

    <div v-if="!compact && tableRows.length" class="table-block">
      <div class="block-title">
        结果数据
        <span class="muted">（共 {{ payload.row_count || tableRows.length }} 行）</span>
      </div>
      <el-table :data="tableRows" border stripe size="small" max-height="320">
        <el-table-column
          v-for="column in tableColumns"
          :key="column"
          :prop="column"
          :label="column"
          min-width="110"
          show-overflow-tooltip
        />
      </el-table>
      <div v-if="(payload.row_count || 0) > tableRows.length" class="table-tip muted">
        仅展示前 {{ tableRows.length }} 行，可在分析报告中导出完整数据。
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Document, Histogram, MagicStick } from '@element-plus/icons-vue'
import ChartPanel from './ChartPanel.vue'
import { chartTypeLabel } from '../utils/constants'
import { formatDuration } from '../utils/format'

const props = defineProps({
  payload: {
    type: Object,
    default: null
  },
  compact: {
    type: Boolean,
    default: false
  }
})

const activePanels = ref([])
const warnings = computed(() => props.payload?.warnings || [])
const steps = computed(() => props.payload?.steps || [])
const warningsText = computed(() => warnings.value.join('；'))
const showResolved = computed(() => {
  const payload = props.payload
  return Boolean(
    payload?.resolved_question &&
      payload?.question &&
      payload.resolved_question !== payload.question
  )
})

const tableRows = computed(() => (props.payload?.rows || []).slice(0, 50))
const tableColumns = computed(() => {
  if (props.payload?.columns?.length) return props.payload.columns
  const firstRow = tableRows.value[0]
  return firstRow ? Object.keys(firstRow) : []
})
</script>

<style scoped>
.result-view {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.resolved-question {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  font-size: 12px;
  color: #5b6b88;
  background: #f7f9fe;
  border-radius: 9px;
  line-height: 1.6;
}

.resolved-label {
  flex: none;
  color: var(--primary);
  font-weight: 600;
}

.result-alert {
  margin: 0;
}

.warning-item {
  font-size: 12px;
  line-height: 1.7;
}

.analysis-block {
  padding: 14px 16px;
  background: linear-gradient(135deg, #f3f7ff 0%, #f8faff 100%);
  border: 1px solid #e2eaff;
  border-left: 3px solid var(--primary);
  border-radius: 11px;
}

.block-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--primary);
}

.analysis-text {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.85;
  color: #2f3f5e;
  white-space: pre-wrap;
  word-break: break-word;
}

.chart-block {
  padding: 10px 6px 0;
  background: #fff;
  border: 1px solid #eef3fb;
  border-radius: 12px;
}

.no-chart {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  font-size: 12px;
  color: #93a1b8;
  background: #fafcff;
  border: 1px dashed #e1e9f6;
  border-radius: 10px;
}

.result-collapse {
  border: 1px solid #eef3fb;
  border-radius: 10px;
  overflow: hidden;
  background: #fbfcff;
}

.result-collapse :deep(.el-collapse-item__header) {
  padding: 0 14px;
  height: 42px;
  background: transparent;
  border-bottom: none;
  font-size: 13px;
  color: #475569;
}

.result-collapse :deep(.el-collapse-item__wrap) {
  background: transparent;
  border-bottom: none;
}

.result-collapse :deep(.el-collapse-item__content) {
  padding: 0 14px 14px;
}

.collapse-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.sql-explain {
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.6;
}

.sql-code {
  margin: 0;
  padding: 12px 14px;
  overflow: auto;
  font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.7;
  color: #cfe0ff;
  background: #101a33;
  border-radius: 9px;
  white-space: pre-wrap;
  word-break: break-word;
}

.steps-block {
  padding: 14px 16px 2px;
  background: #fbfcff;
  border: 1px solid #eef3fb;
  border-radius: 11px;
}

.block-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 12px;
}

.step-title {
  font-size: 13px;
  font-weight: 500;
  color: #33445f;
}

.step-detail {
  margin-top: 3px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.6;
  word-break: break-word;
}

.table-block {
  padding: 14px 16px 16px;
  background: #fff;
  border: 1px solid #eef3fb;
  border-radius: 11px;
}

.table-tip {
  margin-top: 8px;
  font-size: 12px;
}

.is-compact {
  gap: 11px;
}

.is-compact .analysis-block {
  padding: 12px 14px;
}

.is-compact .analysis-text {
  font-size: 12.5px;
  line-height: 1.75;
}
</style>
