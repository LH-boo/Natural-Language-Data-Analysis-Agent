<template>
  <div class="empty-dataset">
    <div class="empty-icon">
      <el-icon :size="30"><FolderOpened /></el-icon>
    </div>
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
    <div class="empty-actions">
      <el-button type="primary" :icon="UploadFilled" @click="goDatasets">前往数据集管理</el-button>
      <el-button :loading="loading" :icon="MagicStick" @click="loadSample">加载示例数据</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { FolderOpened, MagicStick, UploadFilled } from '@element-plus/icons-vue'
import { api } from '../api'

const props = defineProps({
  title: {
    type: String,
    default: '还没有可用的数据集'
  },
  description: {
    type: String,
    default: '请先上传 CSV 或加载示例数据，开启自然语言数据分析。'
  }
})

const emit = defineEmits(['loaded'])
const router = useRouter()
const loading = ref(false)

function goDatasets() {
  router.push('/datasets')
}

async function loadSample() {
  loading.value = true
  try {
    const res = await api.loadSampleDataset()
    ElMessage.success(`示例数据「${res.dataset?.name || '示例数据'}」加载成功`)
    emit('loaded', res.dataset)
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.empty-dataset {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 44px 24px;
  text-align: center;
  background: linear-gradient(180deg, #fbfdff 0%, #f6f9ff 100%);
  border: 1px dashed #d6e1f5;
  border-radius: 16px;
}

.empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  color: var(--primary);
  background: #eaf0ff;
  border-radius: 18px;
}

.empty-dataset h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}

.empty-dataset p {
  max-width: 420px;
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--muted);
}

.empty-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  flex-wrap: wrap;
  justify-content: center;
}
</style>
