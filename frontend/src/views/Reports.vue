<template>
  <div class="page">
    <div class="report-summary">
      <div class="summary-text">
        <span class="summary-value">{{ reports.length }}</span>
        <span class="summary-label">份分析报告</span>
        <span class="summary-divider"></span>
        <span class="muted">成功的智能分析任务会自动生成可导出的分析报告</span>
      </div>
      <div class="summary-actions">
        <el-input
          v-model="keyword"
          placeholder="搜索问题或数据集"
          clearable
          :prefix-icon="Search"
          style="width: 220px"
        />
        <el-button :icon="Refresh" size="small" :loading="loading" @click="loadReports">刷新</el-button>
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">报告列表</div>
          <div class="panel-subtitle">共 {{ filteredReports.length }} 条记录</div>
        </div>
        <el-tag size="small" effect="plain" type="success">自动归档</el-tag>
      </div>
      <div class="panel-body">
        <el-table
          v-if="reports.length || loading"
          v-loading="loading"
          :data="filteredReports"
          size="small"
          empty-text="暂无分析报告"
        >
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="question" label="分析问题" min-width="230" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="report-question">{{ row.question }}</span>
            </template>
          </el-table-column>
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
          <el-table-column label="生成时间" width="155">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
              <el-dropdown trigger="click" @command="(format) => exportReport(row, format)">
                <el-button link type="primary" size="small">
                  导出
                  <el-icon><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="csv">导出 CSV</el-dropdown-item>
                    <el-dropdown-item command="json">导出 JSON</el-dropdown-item>
                    <el-dropdown-item command="html">导出 HTML</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-if="!loading && !reports.length"
          :image-size="80"
          description="暂无分析报告，完成一次智能分析后将自动生成"
        >
          <el-button type="primary" @click="router.push('/chat')">前往 AI 智能分析</el-button>
        </el-empty>
        <el-empty
          v-else-if="!loading && reports.length && !filteredReports.length"
          :image-size="70"
          description="没有匹配的报告"
        />
      </div>
    </div>

    <el-drawer v-model="detailVisible" title="分析报告详情" size="720px">
      <div v-loading="detailLoading" class="detail-body">
        <template v-if="detail">
          <div class="report-head">
            <div class="head-top">
              <el-tag size="small" effect="plain">报告 #{{ detail.report?.id || detail.id }}</el-tag>
              <div class="head-actions">
                <el-button size="small" :icon="Download" @click="exportReport(detail, 'csv')">CSV</el-button>
                <el-button size="small" @click="exportReport(detail, 'json')">JSON</el-button>
                <el-button size="small" @click="exportReport(detail, 'html')">HTML</el-button>
              </div>
            </div>
            <h2 class="report-title">{{ detail.report?.title || detail.question }}</h2>
            <div class="report-meta">
              <span>数据集：{{ detail.dataset_name || '-' }}</span>
              <span>生成时间：{{ formatDateTime(detail.report?.created_at || detail.created_at) }}</span>
              <span>返回 {{ detail.row_count }} 行</span>
            </div>
            <div v-if="detail.report?.summary" class="report-brief">{{ detail.report.summary }}</div>
          </div>
          <ResultView :payload="detail" />
        </template>
        <el-empty v-else-if="!detailLoading" description="暂无报告详情" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowDown, Download, Refresh, Search } from '@element-plus/icons-vue'
import { api, exportReportUrl } from '../api'
import ResultView from '../components/ResultView.vue'
import { chartTypeLabel } from '../utils/constants'
import { formatDateTime, formatDuration } from '../utils/format'

const router = useRouter()
const reports = ref([])
const loading = ref(true)
const keyword = ref('')
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)

const filteredReports = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return reports.value
  return reports.value.filter(
    (item) =>
      String(item.question || '').toLowerCase().includes(text) ||
      String(item.dataset_name || '').toLowerCase().includes(text)
  )
})

async function loadReports() {
  loading.value = true
  try {
    const res = await api.listReports(100)
    reports.value = res.items || []
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

function exportReport(row, format) {
  const taskId = row.id || row.task_id
  if (!taskId) return
  window.open(exportReportUrl(taskId, format), '_blank')
}

onMounted(loadReports)
</script>

<style scoped>
.report-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
}

.summary-text {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 12.5px;
}

.summary-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--ink);
  line-height: 1;
}

.summary-label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}

.summary-divider {
  width: 1px;
  height: 13px;
  margin: 0 4px;
  background: #dbe3f1;
  align-self: center;
}

.summary-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.report-question {
  font-weight: 500;
  color: #33445f;
}

.detail-body {
  min-height: 240px;
}

.report-head {
  padding: 16px 18px;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #f3f7ff, #f8faff);
  border: 1px solid #e2eaff;
  border-radius: 13px;
}

.head-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.head-actions {
  display: flex;
  gap: 6px;
}

.report-title {
  margin-top: 12px;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.5;
  color: var(--ink);
}

.report-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 9px;
  font-size: 11.5px;
  color: var(--muted);
}

.report-brief {
  margin-top: 12px;
  padding-left: 11px;
  font-size: 12.5px;
  line-height: 1.75;
  color: #4a5a78;
  border-left: 3px solid var(--primary);
}
</style>
