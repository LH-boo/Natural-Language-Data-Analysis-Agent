<template>
  <div class="page">
    <EmptyDataset v-if="!datasetsLoading && !datasets.length" @loaded="handleSampleLoaded" />

    <template v-else>
      <div class="grid visualization-layout">
        <div class="panel">
          <div class="panel-header">
            <div>
              <div class="panel-title">图表配置</div>
              <div class="panel-subtitle">选择维度、指标与聚合方式</div>
            </div>
          </div>
          <div class="panel-body">
            <el-form label-position="top" class="chart-form">
              <el-form-item label="数据集" required>
                <el-select
                  v-model="datasetId"
                  placeholder="请选择数据集"
                  filterable
                  :loading="datasetsLoading || schemaLoading"
                  style="width: 100%"
                  @change="handleDatasetChange"
                >
                  <el-option
                    v-for="item in datasets"
                    :key="item.id"
                    :label="item.name"
                    :value="item.id"
                  />
                </el-select>
              </el-form-item>

              <el-form-item label="维度字段" required>
                <el-select v-model="dimension" placeholder="请选择维度字段" filterable style="width: 100%">
                  <el-option
                    v-for="column in columns"
                    :key="column.name"
                    :label="column.name"
                    :value="column.name"
                  >
                    <span>{{ column.name }}</span>
                    <span class="option-type">{{ column.dtype }}</span>
                  </el-option>
                </el-select>
              </el-form-item>

              <el-form-item label="聚合方式" required>
                <el-select v-model="agg" style="width: 100%">
                  <el-option
                    v-for="item in AGG_OPTIONS"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"
                  />
                </el-select>
              </el-form-item>

              <el-form-item label="指标字段" :required="agg !== 'count'">
                <el-select
                  v-model="metric"
                  :disabled="agg === 'count'"
                  :placeholder="agg === 'count' ? '计数聚合无需指标' : '请选择数值指标'"
                  filterable
                  style="width: 100%"
                >
                  <el-option
                    v-for="column in numericColumns"
                    :key="column.name"
                    :label="column.name"
                    :value="column.name"
                  />
                </el-select>
              </el-form-item>

              <el-form-item label="图表类型">
                <el-radio-group v-model="chartType" class="chart-type-group">
                  <el-radio-button
                    v-for="item in CHART_TYPE_OPTIONS"
                    :key="item.value"
                    :value="item.value"
                  >
                    {{ item.label }}
                  </el-radio-button>
                </el-radio-group>
              </el-form-item>
            </el-form>

            <el-button
              type="primary"
              class="generate-button"
              :icon="MagicStick"
              :loading="building"
              @click="generateChart"
            >
              {{ building ? '正在生成…' : '生成图表' }}
            </el-button>

            <div class="form-tip">
              <el-icon><InfoFilled /></el-icon>
              <span>指标字段仅支持数值类型，图表默认展示聚合结果前 50 条。</span>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-header">
            <div>
              <div class="panel-title">{{ chartTitle }}</div>
              <div class="panel-subtitle">基于数据集聚合结果自动生成</div>
            </div>
            <el-tag v-if="result" size="small" effect="plain" type="success">
              {{ chartTypeLabel(result.chart_type || chartType) }}
            </el-tag>
          </div>
          <div class="panel-body">
            <ChartPanel
              :option="result?.chart || null"
              height="380px"
              empty-text="请选择维度与指标后生成图表"
            />

            <div v-if="result" class="result-meta">
              <el-tag size="small" effect="plain" type="info">返回 {{ result.row_count }} 行</el-tag>
              <el-tag size="small" effect="plain">耗时 {{ formatDuration(result.execution_time) }}</el-tag>
              <el-tag size="small" effect="plain">{{ metricLabel }}</el-tag>
            </div>

            <el-collapse v-if="result?.sql" v-model="activePanels" class="result-collapse">
              <el-collapse-item name="sql">
                <template #title>
                  <span class="collapse-title">
                    <el-icon><Document /></el-icon>
                    查看生成的 SQL
                  </span>
                </template>
                <pre class="sql-code">{{ result.sql }}</pre>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
      </div>

      <div v-if="result?.rows?.length" class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">图表数据</div>
            <div class="panel-subtitle">共 {{ result.row_count }} 行聚合结果</div>
          </div>
        </div>
        <div class="panel-body">
          <el-table :data="result.rows" border stripe size="small" max-height="300">
            <el-table-column
              v-for="column in result.columns"
              :key="column"
              :prop="column"
              :label="column"
              min-width="140"
              show-overflow-tooltip
            />
          </el-table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, InfoFilled, MagicStick } from '@element-plus/icons-vue'
import { api } from '../api'
import ChartPanel from '../components/ChartPanel.vue'
import EmptyDataset from '../components/EmptyDataset.vue'
import {
  AGG_OPTIONS,
  CHART_TYPE_OPTIONS,
  chartTypeLabel
} from '../utils/constants'
import { formatDuration } from '../utils/format'

const datasets = ref([])
const datasetId = ref(null)
const schema = ref(null)
const dimension = ref('')
const metric = ref('')
const agg = ref('sum')
const chartType = ref('bar')
const building = ref(false)
const datasetsLoading = ref(true)
const schemaLoading = ref(false)
const result = ref(null)
const activePanels = ref([])

const columns = computed(() => schema.value?.columns || [])
const numericColumns = computed(() =>
  columns.value.filter((column) => isNumeric(column.dtype))
)
const chartTitle = computed(() => {
  if (!dimension.value) return '可视化结果'
  return `${dimension.value} · ${metricLabel.value}`
})
const metricLabel = computed(() => {
  if (agg.value === 'count') return '记录数'
  const text = AGG_OPTIONS.find((item) => item.value === agg.value)?.label || ''
  return metric.value ? `${text}(${metric.value})` : text
})

function isNumeric(dtype) {
  return /int|float|double|decimal|real|numeric|bigint|smallint|number/i.test(String(dtype || ''))
}

async function loadDatasets() {
  datasetsLoading.value = true
  try {
    const res = await api.listDatasets()
    datasets.value = res.items || []
    if (!datasets.value.length) {
      datasetId.value = null
      return
    }
    if (!datasets.value.some((item) => item.id === datasetId.value)) {
      datasetId.value = datasets.value[0].id
    }
    await loadSchema()
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    datasetsLoading.value = false
  }
}

async function loadSchema() {
  if (!datasetId.value) {
    schema.value = null
    return
  }
  schemaLoading.value = true
  try {
    schema.value = await api.datasetSchema(datasetId.value)
    const all = schema.value.columns || []
    const numeric = all.filter((column) => isNumeric(column.dtype))
    const preferred = all.find((column) => !isNumeric(column.dtype)) || all[0]
    dimension.value = preferred?.name || ''
    metric.value = numeric[0]?.name || ''
    result.value = null
  } catch (error) {
    schema.value = null
  } finally {
    schemaLoading.value = false
  }
}

async function handleDatasetChange() {
  result.value = null
  await loadSchema()
}

async function generateChart() {
  if (!datasetId.value) {
    ElMessage.warning('请先选择数据集')
    return
  }
  if (!dimension.value) {
    ElMessage.warning('请选择维度字段')
    return
  }
  if (agg.value !== 'count' && !metric.value) {
    ElMessage.warning('请选择指标字段，或使用计数聚合')
    return
  }
  building.value = true
  result.value = null
  try {
    const res = await api.buildChart({
      dataset_id: datasetId.value,
      dimension: dimension.value,
      metric: agg.value === 'count' ? '' : metric.value,
      agg: agg.value,
      chart_type: chartType.value
    })
    result.value = res
    if (res.chart) {
      ElMessage.success('图表生成成功')
    } else {
      ElMessage.info('当前结果暂无可视化图表')
    }
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    building.value = false
  }
}

async function handleSampleLoaded() {
  await loadDatasets()
}

onMounted(loadDatasets)
</script>

<style scoped>
.visualization-layout {
  grid-template-columns: 372px minmax(0, 1fr);
  align-items: start;
}

.chart-form :deep(.el-form-item) {
  margin-bottom: 15px;
}

.chart-form :deep(.el-form-item__label) {
  padding-bottom: 5px;
  font-size: 12px;
  color: #5b6b88;
}

.option-type {
  float: right;
  font-size: 11px;
  color: #9aa8bf;
}

.chart-type-group {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  width: 100%;
  gap: 7px;
}

.chart-type-group :deep(.el-radio-button) {
  width: 100%;
}

.chart-type-group :deep(.el-radio-button__inner) {
  width: 100%;
  padding: 8px 6px;
  font-size: 12px;
  border: 1px solid #e2e9f5;
  border-radius: 8px;
  box-shadow: none;
}

.chart-type-group :deep(.el-radio-button.is-active .el-radio-button__inner) {
  border-color: var(--primary);
}

.generate-button {
  width: 100%;
  margin-top: 2px;
}

.form-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 13px;
  padding: 9px 11px;
  font-size: 11.5px;
  color: #7b8aa6;
  background: #fafcff;
  border: 1px dashed #e2eaf7;
  border-radius: 9px;
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.result-collapse {
  margin-top: 12px;
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

@media (max-width: 1180px) {
  .visualization-layout {
    grid-template-columns: 1fr;
  }
}
</style>
