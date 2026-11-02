<template>
  <div class="page">
    <EmptyDataset v-if="!loading && !datasets.length" @loaded="handleSampleLoaded" />

    <template v-else>
      <div class="panel preview-toolbar">
        <div class="toolbar-left">
          <span class="toolbar-label">选择数据集</span>
          <el-select
            v-model="datasetId"
            placeholder="请选择数据集"
            filterable
            :loading="loading"
            style="width: 260px"
            @change="handleDatasetChange"
          >
            <el-option
              v-for="item in datasets"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
          <div v-if="dataset" class="dataset-meta">
            <el-tag size="small" effect="plain">{{ dataset.name }}</el-tag>
            <span class="muted">{{ dataset.row_count }} 行 · {{ dataset.column_count }} 列</span>
          </div>
        </div>
        <el-button :icon="Refresh" size="small" :loading="loading || previewLoading" @click="loadDataset">
          刷新
        </el-button>
      </div>

      <div class="grid preview-summary">
        <div class="summary-item">
          <span class="summary-label">数据表名</span>
          <span class="summary-value code-text">{{ schema?.table_name || '-' }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">数据行数</span>
          <span class="summary-value">{{ dataset?.row_count ?? preview.total ?? 0 }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">字段数量</span>
          <span class="summary-value">{{ schema?.columns?.length ?? dataset?.column_count ?? 0 }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">数据来源</span>
          <span class="summary-value">{{ SOURCE_TYPE_LABELS[dataset?.source_type] || 'CSV 文件' }}</span>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">字段结构</div>
            <div class="panel-subtitle">字段类型、业务含义与缺失值统计</div>
          </div>
          <el-tag size="small" effect="plain" type="info">
            {{ schema?.columns?.length || 0 }} 个字段
          </el-tag>
        </div>
        <div class="panel-body">
          <el-table v-loading="schemaLoading" :data="schema?.columns || []" size="small" empty-text="暂无字段信息">
            <el-table-column prop="name" label="字段名" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="field-name">{{ row.name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="数据类型" width="140">
              <template #default="{ row }">
                <el-tag size="small" effect="plain" type="info">{{ row.dtype }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="业务含义" min-width="130" show-overflow-tooltip />
            <el-table-column prop="missing_count" label="缺失值" width="100" align="right">
              <template #default="{ row }">
                <span :class="{ 'text-danger': row.missing_count > 0 }">{{ row.missing_count }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="unique_count" label="唯一值" width="100" align="right" />
          </el-table>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">数据明细</div>
            <div class="panel-subtitle">
              <template v-if="preview.total">
                第 {{ preview.offset + 1 }} -
                {{ Math.min(preview.offset + (preview.rows?.length || 0), preview.total) }} 行，共
                {{ preview.total }} 行
              </template>
              <template v-else>暂无数据</template>
            </div>
          </div>
          <el-tag size="small" effect="plain">每页 {{ pageSize }} 行</el-tag>
        </div>
        <div class="panel-body">
          <el-table
            v-loading="previewLoading"
            :data="preview.rows"
            border
            stripe
            size="small"
            max-height="520"
            empty-text="暂无数据"
          >
            <el-table-column
              v-for="column in preview.columns"
              :key="column"
              :prop="column"
              :label="column"
              min-width="130"
              show-overflow-tooltip
            />
          </el-table>

          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="page"
              v-model:page-size="pageSize"
              :total="preview.total"
              :page-sizes="[20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              background
              @current-change="handlePageChange"
              @size-change="handleSizeChange"
            />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { api } from '../api'
import EmptyDataset from '../components/EmptyDataset.vue'
import { SOURCE_TYPE_LABELS } from '../utils/constants'

const route = useRoute()
const router = useRouter()

const datasets = ref([])
const datasetId = ref(null)
const dataset = ref(null)
const schema = ref(null)
const preview = ref({ columns: [], rows: [], total: 0, limit: 20, offset: 0 })
const loading = ref(true)
const schemaLoading = ref(false)
const previewLoading = ref(false)
const page = ref(1)
const pageSize = ref(20)

async function loadDatasets() {
  loading.value = true
  try {
    const res = await api.listDatasets()
    datasets.value = res.items || []
    const queryId = Number(route.query.id)
    if (queryId && datasets.value.some((item) => item.id === queryId)) {
      datasetId.value = queryId
    } else if (!datasets.value.some((item) => item.id === datasetId.value)) {
      datasetId.value = datasets.value[0]?.id || null
    }
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    loading.value = false
  }
}

async function loadSchema() {
  if (!datasetId.value) return
  schemaLoading.value = true
  try {
    schema.value = await api.datasetSchema(datasetId.value)
  } catch (error) {
    schema.value = null
  } finally {
    schemaLoading.value = false
  }
}

async function loadPreview() {
  if (!datasetId.value) return
  previewLoading.value = true
  try {
    const res = await api.previewDataset({
      id: datasetId.value,
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value
    })
    preview.value = res
    if (res.dataset) dataset.value = res.dataset
  } catch (error) {
    preview.value = { columns: [], rows: [], total: 0, limit: pageSize.value, offset: 0 }
  } finally {
    previewLoading.value = false
  }
}

async function loadDataset() {
  if (!datasetId.value) {
    dataset.value = null
    schema.value = null
    preview.value = { columns: [], rows: [], total: 0, limit: pageSize.value, offset: 0 }
    return
  }
  await Promise.all([loadSchema(), loadPreview()])
}

async function handleDatasetChange() {
  page.value = 1
  router.replace({ path: '/preview', query: datasetId.value ? { id: datasetId.value } : {} })
  await loadDataset()
}

function handlePageChange(value) {
  page.value = value
  loadPreview()
}

function handleSizeChange(value) {
  pageSize.value = value
  page.value = 1
  loadPreview()
}

async function handleSampleLoaded() {
  await loadDatasets()
  await loadDataset()
}

async function init() {
  await loadDatasets()
  await loadDataset()
}

onMounted(init)
</script>

<style scoped>
.preview-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 18px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.toolbar-label {
  font-size: 12.5px;
  font-weight: 600;
  color: #475569;
}

.dataset-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
}

.preview-summary {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 18px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
}

.summary-label {
  font-size: 11.5px;
  color: var(--muted);
}

.summary-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--ink);
}

.summary-value.code-text {
  font-size: 14px;
}

.field-name {
  font-weight: 500;
  color: #33445f;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

@media (max-width: 900px) {
  .preview-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
