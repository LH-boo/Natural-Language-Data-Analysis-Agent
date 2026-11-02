<template>
  <div class="chat-page">
    <aside class="chat-side panel">
      <div class="side-head">
        <div>
          <div class="side-title">会话列表</div>
          <div class="side-count">{{ conversations.length }} 个历史会话</div>
        </div>
        <el-tooltip content="新建会话" placement="bottom">
          <el-button type="primary" :icon="Plus" circle size="small" @click="startNew" />
        </el-tooltip>
      </div>
      <el-scrollbar class="side-scroll">
        <div v-loading="loadingConversations" class="conv-list">
          <el-empty
            v-if="!conversations.length && !loadingConversations"
            :image-size="56"
            description="暂无历史会话"
          />
          <button
            v-for="item in conversations"
            :key="item.id"
            type="button"
            class="conv-item"
            :class="{ active: item.id === conversationId }"
            @click="openConversation(item.id)"
          >
            <span class="conv-icon">
              <el-icon><ChatDotRound /></el-icon>
            </span>
            <span class="conv-body">
              <span class="conv-title">{{ item.title || '未命名会话' }}</span>
              <span class="conv-meta">
                {{ item.message_count }} 条消息 · {{ formatDateTime(item.updated_at) }}
              </span>
            </span>
            <span class="conv-delete" @click.stop="removeConversation(item)">
              <el-icon><Delete /></el-icon>
            </span>
          </button>
        </div>
      </el-scrollbar>
    </aside>

    <section class="chat-main panel">
      <div class="chat-toolbar">
        <div class="toolbar-left">
          <el-select
            v-model="datasetId"
            placeholder="请选择数据集"
            filterable
            :loading="loadingDatasets"
            :disabled="sending"
            style="width: 220px"
            @change="handleDatasetChange"
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
          <span v-if="currentDataset" class="dataset-meta">
            {{ currentDataset.row_count }} 行 · {{ currentDataset.column_count }} 列
          </span>
        </div>
        <div class="toolbar-right">
          <el-tag size="small" effect="plain" type="info">
            {{ conversationId ? '历史会话' : '新会话' }}
          </el-tag>
          <el-tooltip content="刷新会话列表" placement="bottom">
            <el-button :icon="Refresh" circle size="small" @click="loadConversations" />
          </el-tooltip>
        </div>
      </div>

      <div ref="messageArea" class="chat-messages">
        <div v-if="loadingDatasets" class="chat-center">
          <el-icon class="is-loading" :size="18"><Loading /></el-icon>
          <span>正在加载数据集…</span>
        </div>

        <EmptyDataset
          v-else-if="!hasDatasets"
          @loaded="handleDatasetLoaded"
        />

        <div v-else-if="loadingMessages" class="chat-center">
          <el-icon class="is-loading" :size="18"><Loading /></el-icon>
          <span>正在加载会话记录…</span>
        </div>

        <div v-else-if="!messages.length" class="chat-welcome">
          <div class="welcome-logo">
            <el-icon :size="30"><MagicStick /></el-icon>
          </div>
          <h2>开始你的自然语言数据分析</h2>
          <p>选择左侧数据集，直接提问即可获得分析结论、可视化图表和可追溯的 SQL。</p>
          <div class="suggestion-grid">
            <button
              v-for="item in suggestions"
              :key="item"
              type="button"
              class="suggestion-card"
              @click="askSuggestion(item)"
            >
              <el-icon><ChatDotRound /></el-icon>
              <span>{{ item }}</span>
            </button>
          </div>
        </div>

        <div v-else class="message-list">
          <div
            v-for="(msg, index) in messages"
            :key="msg.id || index"
            class="msg-row"
            :class="msg.role"
          >
            <template v-if="msg.role === 'user'">
              <div class="user-bubble">
                <p>{{ msg.content }}</p>
                <span class="bubble-time">{{ formatDateTime(msg.createdAt) }}</span>
              </div>
              <div class="msg-avatar user-avatar">我</div>
            </template>
            <template v-else>
              <div class="msg-avatar ai-avatar">
                <el-icon><MagicStick /></el-icon>
              </div>
              <div class="assistant-bubble">
                <div class="assistant-head">
                  <span class="assistant-name">AI 分析助手</span>
                  <span class="assistant-time">{{ formatDateTime(msg.createdAt) }}</span>
                </div>
                <div v-if="msg.pending" class="pending-state">
                  <el-icon class="is-loading" :size="18"><Loading /></el-icon>
                  <div class="pending-text">
                    <strong>正在分析数据…</strong>
                    <span>理解问题 · 生成 SQL · 执行查询 · 生成图表</span>
                  </div>
                </div>
                <template v-else>
                  <ResultView v-if="msg.payload" :payload="msg.payload" />
                  <p v-else class="assistant-text" :class="{ 'is-error': msg.error }">
                    {{ msg.content }}
                  </p>
                </template>
              </div>
            </template>
          </div>
        </div>
      </div>

      <footer class="chat-composer">
        <div class="composer-box">
          <el-input
            v-model="question"
            type="textarea"
            :rows="2"
            :autosize="{ minRows: 2, maxRows: 5 }"
            resize="none"
            maxlength="2000"
            :disabled="!hasDatasets || loadingMessages"
            :placeholder="
              hasDatasets
                ? '输入你的分析问题，例如：各地区销售额排名如何？'
                : '请先上传 CSV 或加载示例数据'
            "
            @keydown="onKeydown"
          />
          <div class="composer-actions">
            <span class="composer-hint">
              Enter 发送，Shift + Enter 换行
              <template v-if="currentDataset"> · 当前数据集：{{ currentDataset.name }}</template>
            </span>
            <el-button
              type="primary"
              :icon="Promotion"
              :loading="sending"
              :disabled="!hasDatasets || loadingMessages"
              @click="send"
            >
              {{ sending ? '分析中' : '开始分析' }}
            </el-button>
          </div>
        </div>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatDotRound,
  Delete,
  Loading,
  MagicStick,
  Plus,
  Promotion,
  Refresh
} from '@element-plus/icons-vue'
import { api } from '../api'
import EmptyDataset from '../components/EmptyDataset.vue'
import ResultView from '../components/ResultView.vue'
import { SUGGESTIONS } from '../utils/constants'
import { formatDateTime, formatLocalNow } from '../utils/format'

const route = useRoute()
const router = useRouter()

const datasets = ref([])
const datasetId = ref(null)
const conversations = ref([])
const conversationId = ref(null)
const messages = ref([])
const question = ref('')
const sending = ref(false)
const loadingDatasets = ref(true)
const loadingConversations = ref(false)
const loadingMessages = ref(false)
const messageArea = ref(null)
const suggestions = SUGGESTIONS.slice(0, 6)

const hasDatasets = computed(() => datasets.value.length > 0)
const currentDataset = computed(
  () => datasets.value.find((item) => item.id === datasetId.value) || null
)

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

async function loadConversations() {
  loadingConversations.value = true
  try {
    const res = await api.listConversations()
    conversations.value = res.items || []
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    loadingConversations.value = false
  }
}

async function scrollToBottom() {
  await nextTick()
  if (messageArea.value) {
    messageArea.value.scrollTop = messageArea.value.scrollHeight
  }
}

async function openConversation(id) {
  if (sending.value) {
    ElMessage.warning('分析进行中，请稍后再切换会话')
    return
  }
  loadingMessages.value = true
  try {
    const res = await api.getConversation(id)
    const conversation = res.conversation || {}
    conversationId.value = conversation.id
    if (conversation.dataset_id) {
      if (datasets.value.some((item) => item.id === conversation.dataset_id)) {
        datasetId.value = conversation.dataset_id
      } else {
        datasetId.value = null
      }
    }
    messages.value = (res.messages || []).map((item) => ({
      id: item.id,
      role: item.role,
      content: item.content,
      payload: item.payload,
      createdAt: item.created_at
    }))
    const query = { conversation_id: id }
    if (conversation.dataset_id) query.dataset_id = conversation.dataset_id
    router.replace({ path: '/chat', query })
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    loadingMessages.value = false
    await scrollToBottom()
  }
}

function startNew() {
  if (sending.value) return
  conversationId.value = null
  messages.value = []
  question.value = ''
  const query = datasetId.value ? { dataset_id: datasetId.value } : {}
  router.replace({ path: '/chat', query })
}

function handleDatasetChange() {
  if (sending.value) return
  conversationId.value = null
  messages.value = []
  question.value = ''
  const query = datasetId.value ? { dataset_id: datasetId.value } : {}
  router.replace({ path: '/chat', query })
}

async function handleDatasetLoaded() {
  await loadDatasets()
  await scrollToBottom()
}

async function removeConversation(item) {
  if (sending.value) {
    ElMessage.warning('分析进行中，请稍后再删除会话')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除会话「${item.title || '未命名会话'}」吗？`, '删除会话', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch (error) {
    return
  }
  try {
    await api.deleteConversation(item.id)
    ElMessage.success('会话已删除')
  } catch (error) {
    return
  }
  if (conversationId.value === item.id) {
    startNew()
  }
  await loadConversations()
}

function askSuggestion(item) {
  if (sending.value) return
  question.value = item
  send()
}

function onKeydown(event) {
  if (event.key !== 'Enter' || event.shiftKey) return
  if (event.isComposing || event.keyCode === 229) return
  event.preventDefault()
  send()
}

async function send() {
  if (sending.value) return
  if (!hasDatasets.value) {
    ElMessage.warning('请先上传 CSV 或加载示例数据')
    return
  }
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
    const query = { conversation_id: res.conversation_id }
    if (datasetId.value) query.dataset_id = datasetId.value
    router.replace({ path: '/chat', query })
    await loadConversations()
  } catch (error) {
    pendingMessage.pending = false
    pendingMessage.error = true
    pendingMessage.content = '分析失败，请稍后重试或检查后端服务。'
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}

async function init() {
  await loadDatasets()
  const queryDatasetId = Number(route.query.dataset_id)
  if (queryDatasetId && datasets.value.some((item) => item.id === queryDatasetId)) {
    datasetId.value = queryDatasetId
  }
  await loadConversations()
  const queryConversationId = route.query.conversation_id
  if (queryConversationId) {
    await openConversation(String(queryConversationId))
  }
  await scrollToBottom()
}

onMounted(init)
</script>

<style scoped>
.chat-page {
  display: flex;
  gap: 16px;
  height: calc(100vh - 110px);
  min-height: 540px;
}

.chat-side {
  display: flex;
  flex-direction: column;
  width: 278px;
  flex: none;
  overflow: hidden;
}

.side-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 17px 16px 12px;
  border-bottom: 1px solid #f0f4fb;
}

.side-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.side-count {
  margin-top: 4px;
  font-size: 11px;
  color: var(--muted);
}

.side-scroll {
  flex: 1;
  min-height: 0;
}

.conv-list {
  padding: 10px;
  min-height: 120px;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 10px 9px;
  margin-bottom: 5px;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 10px;
  transition: all 0.16s ease;
}

.conv-item:hover {
  background: #f6f9ff;
}

.conv-item.active {
  background: #eef3ff;
  border-color: #dbe5ff;
}

.conv-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  flex: none;
  color: var(--primary);
  background: #f0f4ff;
  border-radius: 8px;
}

.conv-item.active .conv-icon {
  color: #fff;
  background: var(--primary);
}

.conv-body {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}

.conv-title {
  font-size: 12.5px;
  font-weight: 500;
  color: #33445f;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-meta {
  font-size: 10.5px;
  color: #97a5bb;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-delete {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  flex: none;
  color: #b7c2d6;
  border-radius: 6px;
  opacity: 0;
  transition: all 0.16s ease;
}

.conv-item:hover .conv-delete {
  opacity: 1;
}

.conv-delete:hover {
  color: var(--danger);
  background: #fff1f4;
}

.option-count {
  float: right;
  font-size: 12px;
  color: #9aa8bf;
}

.chat-main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.chat-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 13px 18px;
  border-bottom: 1px solid #f0f4fb;
  flex-wrap: wrap;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.dataset-meta {
  font-size: 11.5px;
  color: var(--muted);
  padding: 3px 9px;
  background: #f6f8fd;
  border-radius: 6px;
}

.chat-messages {
  flex: 1;
  min-height: 0;
  padding: 22px 24px;
  overflow-y: auto;
  background: linear-gradient(180deg, #fbfcff 0%, #f8faff 100%);
}

.chat-center {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 220px;
  font-size: 13px;
  color: var(--muted);
}

.chat-welcome {
  max-width: 720px;
  margin: 34px auto 0;
  text-align: center;
}

.welcome-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 68px;
  height: 68px;
  margin: 0 auto 16px;
  color: #fff;
  background: linear-gradient(135deg, #4f7cff, #7c5cff);
  border-radius: 20px;
  box-shadow: 0 12px 26px rgba(79, 124, 255, 0.28);
}

.chat-welcome h2 {
  font-size: 20px;
  font-weight: 700;
  color: var(--ink);
}

.chat-welcome p {
  max-width: 500px;
  margin: 9px auto 0;
  font-size: 13px;
  line-height: 1.75;
  color: var(--muted);
}

.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 26px;
}

.suggestion-card {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 13px 14px;
  font-family: inherit;
  font-size: 12.5px;
  color: #3d4e6d;
  text-align: left;
  cursor: pointer;
  background: #fff;
  border: 1px solid #e6ecf7;
  border-radius: 11px;
  transition: all 0.18s ease;
}

.suggestion-card .el-icon {
  color: var(--primary);
  flex: none;
}

.suggestion-card:hover {
  color: var(--primary);
  border-color: #c9d7ff;
  box-shadow: 0 8px 18px rgba(79, 124, 255, 0.09);
  transform: translateY(-1px);
}

.message-list {
  max-width: 940px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.msg-row {
  display: flex;
  gap: 10px;
}

.msg-row.user {
  justify-content: flex-end;
}

.msg-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex: none;
  font-size: 12px;
  border-radius: 10px;
}

.user-avatar {
  color: #fff;
  background: linear-gradient(135deg, #38bdf8, #4f7cff);
}

.ai-avatar {
  color: #fff;
  background: linear-gradient(135deg, #4f7cff, #7c5cff);
  box-shadow: 0 5px 12px rgba(79, 124, 255, 0.25);
}

.user-bubble {
  max-width: 72%;
  padding: 11px 14px 8px;
  color: #fff;
  background: linear-gradient(135deg, #4f7cff, #6a8dff);
  border-radius: 14px 14px 3px 14px;
  box-shadow: 0 6px 16px rgba(79, 124, 255, 0.18);
}

.user-bubble p {
  font-size: 13.5px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.bubble-time {
  display: block;
  margin-top: 5px;
  font-size: 10px;
  text-align: right;
  color: rgba(255, 255, 255, 0.68);
}

.assistant-bubble {
  flex: 1;
  min-width: 0;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid #e8eef8;
  border-radius: 3px 14px 14px 14px;
  box-shadow: 0 6px 18px rgba(23, 43, 99, 0.045);
}

.assistant-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.assistant-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink);
}

.assistant-time {
  font-size: 10.5px;
  color: #9aa8bf;
}

.assistant-text {
  font-size: 13px;
  line-height: 1.8;
  color: #2f3f5e;
  white-space: pre-wrap;
}

.assistant-text.is-error {
  color: var(--danger);
}

.pending-state {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 8px 2px 10px;
  color: var(--primary);
}

.pending-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pending-text strong {
  font-size: 13px;
  font-weight: 500;
}

.pending-text span {
  font-size: 11.5px;
  color: var(--muted);
}

.chat-composer {
  padding: 12px 18px 14px;
  background: #fff;
  border-top: 1px solid #f0f4fb;
}

.composer-box {
  padding: 10px 12px 8px;
  background: #fafcff;
  border: 1px solid #e8eef8;
  border-radius: 12px;
}

.composer-box :deep(.el-textarea__inner) {
  padding: 4px 2px;
  background: transparent;
  box-shadow: none;
  font-size: 13px;
}

.composer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 7px;
}

.composer-hint {
  font-size: 11px;
  color: #97a5bb;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 1100px) {
  .chat-side {
    width: 238px;
  }

  .suggestion-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .chat-page {
    height: auto;
    flex-direction: column;
  }

  .chat-side {
    width: 100%;
    max-height: 220px;
  }

  .chat-main {
    height: 720px;
  }
}
</style>
