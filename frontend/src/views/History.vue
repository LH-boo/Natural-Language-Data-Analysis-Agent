<template>
  <div class="history-page">
    <aside class="history-side panel">
      <div class="side-head">
        <div>
          <div class="side-title">历史会话</div>
          <div class="side-count">{{ conversations.length }} 个会话</div>
        </div>
        <el-button :icon="Refresh" circle size="small" :loading="loadingConversations" @click="loadConversations" />
      </div>
      <el-scrollbar class="side-scroll">
        <div class="conv-list">
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
            :class="{ active: item.id === selectedId }"
            @click="selectConversation(item.id)"
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
      <div class="side-foot">
        <el-button plain type="primary" :icon="Plus" style="width: 100%" @click="router.push('/chat')">
          新建分析会话
        </el-button>
      </div>
    </aside>

    <section class="history-main panel">
      <template v-if="!conversations.length && !loadingConversations">
        <div class="history-empty">
          <el-empty description="暂无历史会话，去 AI 智能分析发起第一次提问">
            <el-button type="primary" @click="router.push('/chat')">前往 AI 智能分析</el-button>
          </el-empty>
        </div>
      </template>

      <template v-else>
        <header class="history-toolbar">
          <div class="history-title-wrap">
            <div class="history-title">
              {{ detail?.conversation?.title || selectedConversation?.title || '会话详情' }}
            </div>
            <div class="history-meta">
              <el-tag v-if="datasetName" size="small" effect="plain">{{ datasetName }}</el-tag>
              <span v-if="detail?.conversation?.created_at" class="muted">
                创建于 {{ formatDateTime(detail.conversation.created_at) }}
              </span>
              <span v-if="messages.length" class="muted">{{ messages.length }} 条消息</span>
            </div>
          </div>
          <div class="toolbar-actions">
            <el-button type="primary" :icon="ChatDotRound" :disabled="!selectedId" @click="continueConversation">
              继续对话
            </el-button>
          </div>
        </header>

        <div ref="messageArea" v-loading="loadingDetail" class="history-messages">
          <div v-if="!loadingDetail && !messages.length" class="chat-center">
            <span>该会话暂无消息记录</span>
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
                  <ResultView v-if="msg.payload" :payload="msg.payload" />
                  <p v-else class="assistant-text">{{ msg.content || '暂无分析内容' }}</p>
                </div>
              </template>
            </div>
          </div>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ChatDotRound,
  Delete,
  MagicStick,
  Plus,
  Refresh
} from '@element-plus/icons-vue'
import { api } from '../api'
import ResultView from '../components/ResultView.vue'
import { formatDateTime } from '../utils/format'

const route = useRoute()
const router = useRouter()

const conversations = ref([])
const datasets = ref([])
const selectedId = ref(null)
const detail = ref(null)
const loadingConversations = ref(true)
const loadingDetail = ref(false)
const messageArea = ref(null)

const selectedConversation = computed(
  () => conversations.value.find((item) => item.id === selectedId.value) || null
)
const messages = computed(() => detail.value?.messages || [])
const datasetName = computed(() => {
  const datasetId = detail.value?.conversation?.dataset_id
  if (!datasetId) return ''
  return datasets.value.find((item) => item.id === datasetId)?.name || `数据集 #${datasetId}`
})

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

async function loadDatasets() {
  try {
    const res = await api.listDatasets()
    datasets.value = res.items || []
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  }
}

async function scrollToBottom() {
  await new Promise((resolve) => setTimeout(resolve, 0))
  if (messageArea.value) {
    messageArea.value.scrollTop = messageArea.value.scrollHeight
  }
}

async function selectConversation(id) {
  selectedId.value = id
  loadingDetail.value = true
  detail.value = null
  try {
    const res = await api.getConversation(id)
    detail.value = res
    const datasetId = res.conversation?.dataset_id
    const query = { conversation_id: id }
    if (datasetId) query.dataset_id = datasetId
    router.replace({ path: '/history', query })
    await scrollToBottom()
  } catch (error) {
    detail.value = null
  } finally {
    loadingDetail.value = false
  }
}

function continueConversation() {
  if (!selectedId.value) return
  const query = { conversation_id: selectedId.value }
  const datasetId = detail.value?.conversation?.dataset_id
  if (datasetId) query.dataset_id = datasetId
  router.push({ path: '/chat', query })
}

async function removeConversation(item) {
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
  const deletingCurrent = selectedId.value === item.id
  await loadConversations()
  if (deletingCurrent) {
    selectedId.value = null
    detail.value = null
    if (conversations.value.length) {
      await selectConversation(conversations.value[0].id)
    } else {
      router.replace({ path: '/history' })
    }
  }
}

async function init() {
  await Promise.all([loadDatasets(), loadConversations()])
  const queryId = route.query.conversation_id
  if (queryId && conversations.value.some((item) => item.id === String(queryId))) {
    await selectConversation(String(queryId))
  } else if (conversations.value.length) {
    await selectConversation(conversations.value[0].id)
  }
}

onMounted(init)
</script>

<style scoped>
.history-page {
  display: flex;
  gap: 16px;
  height: calc(100vh - 110px);
  min-height: 540px;
}

.history-side {
  display: flex;
  flex-direction: column;
  width: 290px;
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

.side-foot {
  padding: 12px 14px 14px;
  border-top: 1px solid #f0f4fb;
}

.history-main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.history-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.history-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 20px;
  border-bottom: 1px solid #f0f4fb;
  flex-wrap: wrap;
}

.history-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
  font-size: 11.5px;
  flex-wrap: wrap;
}

.history-messages {
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
  min-height: 220px;
  font-size: 13px;
  color: var(--muted);
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

@media (max-width: 1100px) {
  .history-side {
    width: 248px;
  }
}

@media (max-width: 860px) {
  .history-page {
    height: auto;
    flex-direction: column;
  }

  .history-side {
    width: 100%;
    max-height: 240px;
  }

  .history-main {
    height: 700px;
  }
}
</style>
