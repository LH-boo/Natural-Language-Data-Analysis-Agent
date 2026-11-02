<template>
  <div class="page">
    <div class="grid datasets-top">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">上传 CSV 数据集</div>
            <div class="panel-subtitle">支持 CSV / TXT / TSV 文件，首行需为列名</div>
          </div>
          <el-tag size="small" effect="plain">最大 20MB</el-tag>
        </div>
        <div class="panel-body">
          <el-upload
            drag
            action="#"
            accept=".csv,.txt,.tsv"
            :show-file-list="false"
            :http-request="handleUpload"
            :before-upload="beforeUpload"
            :disabled="uploading"
          >
            <div class="upload-zone">
              <div class="upload-icon" :class="{ 'is-loading': uploading }">
                <el-icon :size="30"><UploadFilled /></el-icon>
              </div>
              <div class="upload-title">
                {{ uploading ? '正在导入数据，请稍候…' : '拖拽文件到此处，或点击选择 CSV 文件' }}
              </div>
              <div class="upload-desc">系统会自动识别字段类型，并写入 DuckDB 分析引擎</div>
            </div>
          </el-upload>
        </div>
      </div>

      <div class="panel sample-panel">
        <div class="panel-header">
          <div class="panel-title">示例数据</div>
        </div>
        <div class="panel-body">
          <div class="sample-icon">
            <el-icon :size="24"><MagicStick /></el-icon>
          </div>
          <h3>示例销售数据</h3>
          <p>内置商品、地区、销售额、利润等字段，适合快速体验自然语言分析与图表生成。</p>
          <div class="tag-list">
            <el-tag size="small" effect="plain">商品</el-tag>
            <el-tag size="small" effect="plain">地区</el-tag>
            <el-tag size="small" effect="plain">销售额</el-tag>
            <el-tag size="small" effect="plain">利润</el-tag>
          </div>
          <el-button type="primary" class="sample-button" :icon="MagicStick" :loading="sampleLoading" @click="loadSample">
            加载示例数据
          </el-button>
          <div class="sample-tip">加载后可直接前往「AI 智能分析」体验</div>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <div>
          <div class="panel-title">数据集列表</div>
          <div class="panel-subtitle">共 {{ datasets.length }} 个数据集</div>
        </div>
        <el-button :icon="Refresh" size="small" :loading="loading" @click="loadDatasets">刷新</el-button>
      </div>
      <div class="panel-body">
        <el-table
          v-if="datasets.length || loading"
          v-loading="loading"
          :data="datasets"
          size="small"
          empty-text="暂无数据集"
        >
          <el-table-column prop="name" label="数据集名称" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <div class="dataset-name">
                <span class="dataset-icon"><el-icon><Coin /></el-icon></span>
                <span>{{ row.name }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="来源" width="110">
            <template #default="{ row }">
              <el-tag size="small" effect="plain" :type="row.source_type === 'database' ? 'warning' : 'info'">
                {{ SOURCE_TYPE_LABELS[row.source_type] || 'CSV 文件' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="row_count" label="数据行数" width="100" align="right" />
          <el-table-column prop="column_count" label="字段数" width="90" align="right" />
          <el-table-column label="创建时间" width="160">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="210" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="goPreview(row)">预览</el-button>
              <el-button link type="primary" size="small" @click="goAnalyze(row)">去分析</el-button>
              <el-button link type="danger" size="small" @click="removeDataset(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="!loading && !datasets.length" class="empty-wrap">
          <EmptyDataset @loaded="loadDatasets" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Coin, MagicStick, Refresh, UploadFilled } from '@element-plus/icons-vue'
import { api } from '../api'
import EmptyDataset from '../components/EmptyDataset.vue'
import { SOURCE_TYPE_LABELS } from '../utils/constants'
import { formatDateTime } from '../utils/format'

const router = useRouter()
const datasets = ref([])
const loading = ref(true)
const uploading = ref(false)
const sampleLoading = ref(false)

async function loadDatasets() {
  loading.value = true
  try {
    const res = await api.listDatasets()
    datasets.value = res.items || []
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    loading.value = false
  }
}

function beforeUpload(file) {
  const name = (file.name || '').toLowerCase()
  if (!['.csv', '.txt', '.tsv'].some((ext) => name.endsWith(ext))) {
    ElMessage.warning('仅支持上传 CSV、TXT、TSV 文件')
    return false
  }
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.warning('文件大小不能超过 20MB')
    return false
  }
  return true
}

async function handleUpload(options) {
  uploading.value = true
  try {
    const res = await api.uploadDataset(options.file)
    ElMessage.success(`数据集「${res.dataset?.name || options.file.name}」导入成功`)
    await loadDatasets()
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    uploading.value = false
  }
}

async function loadSample() {
  sampleLoading.value = true
  try {
    const res = await api.loadSampleDataset()
    ElMessage.success(`示例数据「${res.dataset?.name || '示例数据'}」加载成功`)
    await loadDatasets()
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    sampleLoading.value = false
  }
}

function goPreview(row) {
  router.push({ path: '/preview', query: { id: row.id } })
}

function goAnalyze(row) {
  router.push({ path: '/chat', query: { dataset_id: row.id } })
}

async function removeDataset(row) {
  try {
    await ElMessageBox.confirm(
      `删除后数据集「${row.name}」及其表结构将无法恢复，确定继续吗？`,
      '删除数据集',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch (error) {
    return
  }
  try {
    await api.deleteDataset(row.id)
    ElMessage.success('数据集已删除')
    await loadDatasets()
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  }
}

onMounted(loadDatasets)
</script>

<style scoped>
.datasets-top {
  grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr);
}

.upload-zone {
  padding: 18px 0 8px;
}

.upload-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 62px;
  height: 62px;
  margin: 0 auto 14px;
  color: var(--primary);
  background: #eef3ff;
  border-radius: 18px;
  transition: all 0.2s ease;
}

.upload-icon.is-loading {
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.06);
    opacity: 0.72;
  }
}

.upload-title {
  font-size: 14px;
  font-weight: 500;
  color: #33445f;
}

.upload-desc {
  margin-top: 7px;
  font-size: 12px;
  color: var(--muted);
}

:deep(.el-upload-dragger) {
  padding: 18px;
  background: linear-gradient(180deg, #fbfdff, #f6f9ff);
  border: 1px dashed #cfdcf3;
  border-radius: 14px;
  transition: all 0.2s ease;
}

:deep(.el-upload-dragger:hover) {
  border-color: var(--primary);
  background: #f4f8ff;
}

.sample-panel {
  display: flex;
  flex-direction: column;
}

.sample-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  color: #fff;
  background: linear-gradient(135deg, #4f7cff, #7c5cff);
  border-radius: 15px;
  box-shadow: 0 10px 22px rgba(79, 124, 255, 0.24);
}

.sample-panel h3 {
  margin-top: 14px;
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}

.sample-panel p {
  margin-top: 8px;
  font-size: 12.5px;
  line-height: 1.75;
  color: var(--muted);
}

.sample-panel .tag-list {
  margin-top: 12px;
}

.sample-button {
  width: 100%;
  margin-top: 16px;
}

.sample-tip {
  margin-top: 9px;
  font-size: 11px;
  text-align: center;
  color: #9aa8bf;
}

.dataset-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #33445f;
}

.dataset-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  flex: none;
  color: var(--primary);
  background: #f0f4ff;
  border-radius: 7px;
}

.empty-wrap {
  margin-top: 16px;
}

@media (max-width: 1100px) {
  .datasets-top {
    grid-template-columns: 1fr;
  }
}
</style>
