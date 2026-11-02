<template>
  <div class="ai-assistant">
    <button class="ai-fab" type="button" title="打开 AI 智能分析助手" :style="fabStyle" @click="open">
      <span class="ai-fab-icon">
        <el-icon :size="21"><MagicStick /></el-icon>
      </span>
      <span class="ai-fab-text">AI 分析</span>
    </button>

    <el-drawer v-model="visible" direction="rtl" size="480px" :with-header="false" class="ai-drawer">
      <div class="ai-shell">
        <header class="ai-header">
          <div class="ai-title-wrap">
            <div class="ai-logo">
              <el-icon :size="20"><MagicStick /></el-icon>
            </div>
            <div>
              <div class="ai-title">AI 智能分析助手</div>
              <div class="ai-subtitle">选择数据集，直接提问即可分析</div>
            </div>
          </div>
          <el-button :icon="Close" circle text @click="visible = false" />
        </header>

        <div class="ai-toolbar">
          <el-select
            v-model="datasetId"
            placeholder="请选择数据集"
            filterable
            :loading="loadingDatasets"
            style="width: 100%"
            @change="resetSession"
          >
            <el-option
              v-for="item in datasets"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            >
              <span>{{ item.name }}</span>
              <span class="option-count">{{ item.row_count }} 行</span>
            </el-option>
          </el-select>
        </div>

        <div ref="scrollRef" class="ai-messages">
          <div v-if="loadingDatasets" class="ai-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在加载数据集…</span>
          </div>

          <EmptyDataset
            v-else-if="!hasDatasets"
            title="还没有可用的数据集"
            description="请先上传 CSV 或加载示例数据，再来向我提问。"
            @loaded="onDatasetLoaded"
          />

          <div v-else-if="!messages.length" class="ai-welcome">
            <div class="welcome-icon">
              <el-icon :size="26"><ChatDotRound /></el-icon>
            </div>
            <h3>你好，我是数据分析助手</h3>
            <p>选择一个数据集，用自然语言描述你想了解的问题，我会自动生成 SQL、图表和分析结论。</p>
            <div class="ai-suggestions">
              <button
                v-for="item in suggestions"
                :key="item"
                type="button"
                @click="askSuggestion(item)"
              >
                {{ item }}
              </button>
            </div>
          </div>

          <div v-else class="ai-message-list">
            <div
              v-for="(msg, index) in messages"
              :key="msg.id || index"
              class="ai-msg"
              :class="msg.role"
            >
              <div v-if="msg.role === 'user'" class="ai-user-bubble">
                {{ msg.content }}
              </div>
              <div v-else class="ai-reply">
                <div class="ai-reply-head">
                  <span class="ai-reply-name">
                    <el-icon><MagicStick /></el-icon>
                    AI 助手
                  </span>
                  <span class="muted">{{ formatDateTime(msg.createdAt) }}</span>
                </div>
                <div v-if="msg.pending" class="ai-pending">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>正在理解问题并生成分析…</span>
                </div>
                <template v-else>
                  <ResultView v-if="msg.payload" :payload="msg.payload" compact />
                  <p v-else class="ai-plain" :class="{ 'is-error': msg.error }">{{ msg.content }}</p>
                </template>
              </div>
            </div>
          </div>
        </div>

        <footer class="ai-composer">
          <el-input
            v-model="question"
            type="textarea"
            :rows="2"
            resize="none"
            maxlength="2000"
            :placeholder="hasDatasets ? '输入分析问题，Enter 发送，Shift + Enter 换行' : '请先准备数据集'"
            :disabled="!hasDatasets || sending"
            @keydown="onKeydown"
          />
          <div class="composer-foot">
            <span class="muted">分析结果仅供业务参考</span>
            <el-button
              type="primary"
              :icon="Promotion"
              :loading="sending"
              :disabled="!hasDatasets"
              @click="send"
            >
              发送
            </el-button>
          </div>
        </footer>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ChatDotRound,
  Close,
  Loading,
  MagicStick,
  Promotion
} from '@element-plus/icons-vue'
import { api } from '../api'
import EmptyDataset from './EmptyDataset.vue'
import ResultView from './ResultView.vue'
import { SUGGESTIONS } from '../utils/constants'
import { formatDateTime, formatLocalNow } from '../utils/format'

const route = useRoute()
const visible = ref(false)
const datasets = ref([])
const datasetId = ref(null)
const messages = ref([])
const question = ref('')
const sending = ref(false)
const loadingDatasets = ref(false)
const conversationId = ref(null)
const scrollRef = ref(null)
const suggestions = SUGGESTIONS.slice(0, 3)

const hasDatasets = computed(() => datasets.value.length > 0)
const fabStyle = computed(() =>
  route.path === '/chat' || route.path === '/history' ? { bottom: '96px' } : {}
)

async function open() {
  visible.value = true
  await loadDatasets()
  await scrollToBottom()
}

async function loadDatasets() {
  loadingDatasets.value = true
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
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    loadingDatasets.value = false
  }
}

function resetSession() {
  conversationId.value = null
  messages.value = []
}

function onDatasetLoaded() {
  loadDatasets()
}

async function scrollToBottom() {
  await nextTick()
  if (scrollRef.value) {
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  }
}

function onKeydown(event) {
  if (event.key !== 'Enter' || event.shiftKey) return
  if (event.isComposing || event.keyCode === 229) return
  event.preventDefault()
  send()
}

function askSuggestion(item) {
  question.value = item
  send()
}

async function send() {
  if (sending.value) return
  if (!datasetId.value) {
    ElMessage.warning('请先选择数据集')
    return
  }
  const text = question.value.trim()
  if (!text) {
    ElMessage.warning('请输入分析问题')
    return
  }

  messages.value.push({
    id: `u-${Date.now()}`,
    role: 'user',
    content: text,
    createdAt: formatLocalNow()
  })
  const pending = {
    id: `a-${Date.now()}`,
    role: 'assistant',
    pending: true,
    createdAt: formatLocalNow()
  }
  messages.value.push(pending)
  const pendingMessage = messages.value[messages.value.length - 1]
  question.value = ''
  sending.value = true
  await scrollToBottom()

  try {
    const res = await api.chat({
      question: text,
      dataset_id: datasetId.value,
      conversation_id: conversationId.value || undefined
    })
    conversationId.value = res.conversation_id
    pendingMessage.pending = false
    pendingMessage.payload = res
    pendingMessage.content = res.analysis
    pendingMessage.createdAt = res.created_at || formatLocalNow()
  } catch (error) {
    pendingMessage.pending = false
    pendingMessage.error = true
    pendingMessage.content = '分析失败，请稍后重试或检查后端服务。'
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}
</script>

<style scoped>
.ai-fab {
  position: fixed;
  right: 28px;
  bottom: 28px;
  z-index: 1800;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  height: 52px;
  padding: 0 19px 0 9px;
  color: #fff;
  cursor: pointer;
  background: linear-gradient(135deg, #4f7cff, #7c5cff);
  border: none;
  border-radius: 28px;
  box-shadow: 0 12px 30px rgba(79, 124, 255, 0.42);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.ai-fab:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 36px rgba(79, 124, 255, 0.52);
}

.ai-fab-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 50%;
}

.ai-fab-text {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.ai-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f7f9fd;
}

.ai-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 17px 18px;
  background: linear-gradient(120deg, #101d3d, #1b2f5c);
}

.ai-title-wrap {
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
}

.ai-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  flex: none;
  color: #fff;
  background: rgba(79, 124, 255, 0.35);
  border: 1px solid rgba(137, 166, 255, 0.35);
  border-radius: 11px;
}

.ai-title {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}

.ai-subtitle {
  margin-top: 3px;
  font-size: 11px;
  color: rgba(190, 207, 240, 0.7);
}

.ai-header :deep(.el-button) {
  color: rgba(228, 237, 253, 0.8);
}

.ai-header :deep(.el-button:hover) {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.ai-toolbar {
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid var(--line);
}

.option-count {
  float: right;
  font-size: 12px;
  color: #9aa8bf;
}

.ai-messages {
  flex: 1;
  min-height: 0;
  padding: 16px;
  overflow-y: auto;
}

.ai-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 0;
  font-size: 13px;
  color: var(--muted);
}

.ai-welcome {
  padding: 26px 18px;
  text-align: center;
}

.welcome-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 58px;
  height: 58px;
  margin: 0 auto 14px;
  color: var(--primary);
  background: #eaf0ff;
  border-radius: 17px;
}

.ai-welcome h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}

.ai-welcome p {
  max-width: 330px;
  margin: 9px auto 0;
  font-size: 12.5px;
  line-height: 1.75;
  color: var(--muted);
}

.ai-suggestions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 20px;
}

.ai-suggestions button {
  padding: 10px 13px;
  font-family: inherit;
  font-size: 12.5px;
  color: #3d4e6d;
  text-align: left;
  cursor: pointer;
  background: #fff;
  border: 1px solid #e6ecf7;
  border-radius: 10px;
  transition: all 0.18s ease;
}

.ai-suggestions button:hover {
  color: var(--primary);
  background: #f5f8ff;
  border-color: #c9d7ff;
}

.ai-message-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.ai-msg {
  display: flex;
}

.ai-msg.user {
  justify-content: flex-end;
}

.ai-user-bubble {
  max-width: 86%;
  padding: 10px 13px;
  font-size: 13px;
  line-height: 1.65;
  color: #fff;
  background: linear-gradient(135deg, #4f7cff, #6a8dff);
  border-radius: 13px 13px 3px 13px;
  word-break: break-word;
  white-space: pre-wrap;
}

.ai-reply {
  width: 100%;
  padding: 12px 13px;
  background: #fff;
  border: 1px solid #e9eef8;
  border-radius: 3px 13px 13px 13px;
  box-shadow: 0 4px 14px rgba(23, 43, 99, 0.035);
}

.ai-reply-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  font-size: 11px;
}

.ai-reply-name {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
}

.ai-pending {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  font-size: 12.5px;
  color: var(--muted);
}

.ai-plain {
  font-size: 13px;
  line-height: 1.8;
  color: #2f3f5e;
  white-space: pre-wrap;
}

.ai-plain.is-error {
  color: var(--danger);
}

.ai-composer {
  padding: 12px 16px 14px;
  background: #fff;
  border-top: 1px solid var(--line);
}

.composer-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 9px;
  font-size: 11px;
}

.ai-drawer :deep(.el-drawer__body) {
  padding: 0;
  overflow: hidden;
}

@media (max-width: 600px) {
  .ai-fab {
    right: 18px;
    bottom: 18px;
    padding-right: 12px;
  }

  .ai-fab-text {
    display: none;
  }

  .ai-drawer {
    width: 92vw !important;
  }
}
</style>
