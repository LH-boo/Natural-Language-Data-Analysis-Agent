<template>
  <div class="page">
    <EmptyDataset v-if="!datasetsLoading && !datasets.length" @loaded="handleSampleLoaded" />

    <template v-else>
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">SQL 查询</div>
            <div class="panel-subtitle">在只读环境中执行 SQL，结果最多返回 500 行</div>
          </div>
          <div class="toolbar-right">
            <el-select
              v-model="datasetId"
              placeholder="请选择数据集"
              filterable
              :loading="datasetsLoading"
              style="width: 230px"
              @change="handleDatasetChange"
            >
              <el-option
                v-for="item in datasets"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
            <el-tag v-if="schema" size="small" effect="plain" type="info">
              {{ schema.table_name }}
            </el-tag>
          </div>
        </div>
        <div class="panel-body">
          <el-alert type="info" :closable="false" show-icon title="SQL 安全校验已启用" class="safety-alert">
            <template #default>
              仅允许只读 SELECT 查询，禁止 INSERT、UPDATE、DELETE、DROP 等写操作；查询超时时间为 30 秒。
            </template>
          </el-alert>

          <div class="editor-wrap">
            <el-input
              v-model="sql"
              type="textarea"
              :rows="7"
              resize="vertical"
              spellcheck="false"
              placeholder="请输入只读 SQL 查询，例如：SELECT * FROM 数据表 LIMIT 20"
              class="sql-editor"
              @keydown.ctrl.enter.prevent="execute"
            />
          </div>

          <div class="editor-actions">
            <div class="editor-hint">
              <el-icon><InfoFilled /></el-icon>
              <span>Ctrl + Enter 快速执行</span>
            </div>
            <div class="action-buttons">
              <el-button :icon="MagicStick" @click="applyExample">重置示例</el-button>
              <el-button @click="clearQuery">清空</el-button>
              <el-button type="primary" :icon="VideoPlay" :loading="executing" @click="execute">
                {{ executing ? '执行中…' : '执行查询' }}
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">查询结果</div>
            <div class="panel-subtitle">
              <template v-if="result">
                返回 {{ result.row_count }} 行，执行耗时 {{ formatDuration(result.execution_time) }}
              </template>
              <template v-else>执行 SQL 后将在此展示结果数据</template>
            </div>
          </div>
          <div v-if="result" class="tag-list">
            <el-tag size="small" effect="plain" type="success">查询成功</el-tag>
            <el-tag size="small" effect="plain" type="info">{{ result.columns?.length || 0 }} 列</el-tag>
          </div>
        </div>
        <div class="panel-body">
          <el-alert
            v-if="issues.length"
            type="error"
            :closable="false"
            show-icon
            title="SQL 未通过安全校验或执行失败"
            class="issue-alert"
          >
            <template #default>
              <div v-for="(item, index) in issues" :key="index" class="issue-item">{{ item }}</div>
            </template>
          </el-alert>

          <el-table
            v-if="result"
            :data="result.rows"
            border
            stripe
            size="small"
            max-height="420"
            empty-text="查询结果为空"
          >
            <el-table-column
              v-for="column in result.columns"
              :key="column"
              :prop="column"
              :label="column"
              min-width="130"
              show-overflow-tooltip
            />
          </el-table>
          <el-empty v-else-if="!issues.length" :image-size="60" description="暂无查询结果" />
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">SQL 执行日志</div>
            <div class="panel-subtitle">最近 100 条 SQL 执行与安全拦截记录</div>
          </div>
          <el-button :icon="Refresh" size="small" :loading="logsLoading" @click="loadLogs">
            刷新
          </el-button>
        </div>
        <div class="panel-body">
          <el-table v-loading="logsLoading" :data="logs" size="small" max-height="340" empty-text="暂无执行日志">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column label="SQL 语句" min-width="260" show-overflow-tooltip>
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
            <el-table-column label="错误信息" min-width="160" show-overflow-tooltip>
              <template #default="{ row }">
                <span :class="{ 'text-danger': row.error_message }">
                  {{ row.error_message || '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="执行时间" width="150">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  InfoFilled,
  MagicStick,
  Refresh,
  VideoPlay
} from '@element-plus/icons-vue'
import { api } from '../api'
import EmptyDataset from '../components/EmptyDataset.vue'
import { formatDateTime, formatDuration } from '../utils/format'

const datasets = ref([])
const datasetId = ref(null)
const schema = ref(null)
const sql = ref('')
const executing = ref(false)
const datasetsLoading = ref(true)
const logs = ref([])
const logsLoading = ref(false)
const result = ref(null)
const issues = ref([])

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
  try {
    schema.value = await api.datasetSchema(datasetId.value)
    applyExample()
  } catch (error) {
    schema.value = null
  }
}

function applyExample() {
  if (!schema.value?.table_name) {
    sql.value = ''
    return
  }
  sql.value = `SELECT * FROM "${schema.value.table_name}" LIMIT 20`
}

async function handleDatasetChange() {
  result.value = null
  issues.value = []
  await loadSchema()
}

function clearQuery() {
  sql.value = ''
  result.value = null
  issues.value = []
}

async function execute() {
  if (!datasetId.value) {
    ElMessage.warning('请先选择数据集')
    return
  }
  const text = sql.value.trim()
  if (!text) {
    ElMessage.warning('请输入 SQL 查询语句')
    return
  }
  executing.value = true
  issues.value = []
  result.value = null
  try {
    const res = await api.runSql({ sql: text, dataset_id: datasetId.value })
    if (!res.success) {
      issues.value = res.issues?.length ? res.issues : [res.message || 'SQL 执行失败']
      ElMessage.warning('SQL 未通过安全校验或执行失败')
    } else {
      result.value = res
      ElMessage.success(`查询完成，返回 ${res.row_count} 行`)
    }
  } catch (error) {
    issues.value = ['查询请求失败，请稍后重试']
  } finally {
    executing.value = false
    loadLogs()
  }
}

async function loadLogs() {
  logsLoading.value = true
  try {
    const res = await api.sqlLogs(100)
    logs.value = res.items || []
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    logsLoading.value = false
  }
}

async function handleSampleLoaded() {
  await loadDatasets()
}

async function init() {
  await loadDatasets()
  await loadLogs()
}

onMounted(init)
</script>

<style scoped>
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.safety-alert {
  margin-bottom: 14px;
}

.editor-wrap {
  border-radius: 11px;
  overflow: hidden;
}

.sql-editor :deep(.el-textarea__inner) {
  padding: 14px 16px;
  font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
  font-size: 12.5px;
  line-height: 1.75;
  color: #dbeafe;
  background: #101a33;
  border: 1px solid #1c2c4f;
  border-radius: 11px;
  box-shadow: none;
}

.sql-editor :deep(.el-textarea__inner::placeholder) {
  color: rgba(148, 173, 214, 0.45);
}

.sql-editor :deep(.el-textarea__inner:focus) {
  border-color: #4f7cff;
  box-shadow: 0 0 0 3px rgba(79, 124, 255, 0.14);
}

.editor-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.editor-hint {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: #93a1b8;
}

.action-buttons {
  display: flex;
  gap: 9px;
  flex-wrap: wrap;
}

.issue-alert {
  margin-bottom: 14px;
}

.issue-item {
  font-size: 12px;
  line-height: 1.7;
}
</style>
