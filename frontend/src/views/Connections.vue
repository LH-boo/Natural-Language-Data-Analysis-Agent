<template>
  <div class="page">
    <div class="grid connections-layout">
      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">新建数据库连接</div>
            <div class="panel-subtitle">支持 MySQL、PostgreSQL 与 SQLite</div>
          </div>
          <el-tag size="small" effect="plain">只读访问</el-tag>
        </div>
        <div class="panel-body">
          <el-form :model="form" label-position="top" class="conn-form">
            <el-form-item label="连接名称" required>
              <el-input v-model="form.name" placeholder="例如：业务生产库" maxlength="100" />
            </el-form-item>
            <el-form-item label="数据库类型" required>
              <el-select v-model="form.db_type" style="width: 100%" @change="handleTypeChange">
                <el-option
                  v-for="item in DB_TYPE_OPTIONS"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>

            <template v-if="!isSqlite">
              <div class="form-row">
                <el-form-item label="主机地址" required>
                  <el-input v-model="form.host" placeholder="127.0.0.1" />
                </el-form-item>
                <el-form-item label="端口" required>
                  <el-input-number
                    v-model="form.port"
                    :min="1"
                    :max="65535"
                    :controls="false"
                    style="width: 100%"
                  />
                </el-form-item>
              </div>
              <div class="form-row">
                <el-form-item label="用户名">
                  <el-input v-model="form.username" placeholder="数据库用户名" />
                </el-form-item>
                <el-form-item label="密码">
                  <el-input v-model="form.password" type="password" show-password placeholder="数据库密码" />
                </el-form-item>
              </div>
              <el-form-item label="数据库名称" required>
                <el-input v-model="form.database_name" placeholder="需要分析的业务数据库" />
              </el-form-item>
            </template>

            <el-form-item v-else label="SQLite 文件路径" required>
              <el-input v-model="form.sqlite_path" placeholder="例如：D:/data/business.db" />
            </el-form-item>
          </el-form>

          <div class="form-actions">
            <el-button :icon="Link" :loading="testing" @click="testConnection">测试连接</el-button>
            <el-button type="primary" :icon="Check" :loading="saving" @click="saveConnection">
              保存连接
            </el-button>
          </div>

          <el-alert
            v-if="testResult"
            class="test-alert"
            :type="testResult.success ? 'success' : 'error'"
            :title="testResult.message"
            :closable="false"
            show-icon
          />

          <div class="form-tip">
            <el-icon><InfoFilled /></el-icon>
            <span>密码仅用于建立连接，保存后不会回显明文。</span>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">已保存的连接</div>
            <div class="panel-subtitle">共 {{ connections.length }} 个数据库连接</div>
          </div>
          <el-button :icon="Refresh" size="small" :loading="loading" @click="loadConnections">
            刷新
          </el-button>
        </div>
        <div class="panel-body">
          <el-table v-loading="loading" :data="connections" size="small" empty-text="暂无数据库连接">
            <el-table-column label="连接名称" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                <div class="conn-name">
                  <span class="conn-icon"><el-icon><Connection /></el-icon></span>
                  <div class="conn-text">
                    <span>{{ row.name }}</span>
                    <span class="muted">{{ dbTypeLabel(row.db_type) }}</span>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="连接地址" min-width="190" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="code-text">{{ addressOf(row) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="username" label="用户名" width="110" show-overflow-tooltip>
              <template #default="{ row }">{{ row.username || '-' }}</template>
            </el-table-column>
            <el-table-column label="创建时间" width="150">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openSchema(row)">查看结构</el-button>
                <el-button link type="danger" size="small" @click="removeConnection(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <el-drawer v-model="schemaVisible" title="数据库表结构" size="640px">
      <div v-loading="schemaLoading" class="schema-body">
        <template v-if="schemaData">
          <div class="schema-head">
            <div>
              <div class="schema-name">{{ schemaData.connection_name || '数据库连接' }}</div>
              <div class="muted schema-desc">
                共 {{ schemaData.tables?.length || 0 }} 张表可供分析，仅允许只读查询
              </div>
            </div>
            <el-tag size="small" type="success" effect="plain">连接正常</el-tag>
          </div>

          <div v-if="schemaData.allowed_tables?.length" class="allowed-tables">
            <div class="allowed-label">可分析的表</div>
            <div class="tag-list">
              <el-tag
                v-for="table in schemaData.allowed_tables"
                :key="table"
                size="small"
                effect="plain"
              >
                {{ table }}
              </el-tag>
            </div>
          </div>

          <el-empty
            v-if="!schemaData.tables?.length"
            description="未读取到数据表"
            :image-size="70"
          />
          <el-collapse v-else v-model="activeTables" class="schema-collapse">
            <el-collapse-item v-for="table in schemaData.tables" :key="table.name" :name="table.name">
              <template #title>
                <span class="table-title">
                  <el-icon><Grid /></el-icon>
                  {{ table.name }}
                  <el-tag size="small" effect="plain" type="info">
                    {{ table.columns?.length || 0 }} 字段
                  </el-tag>
                </span>
              </template>
              <el-table :data="table.columns || []" size="small" border>
                <el-table-column prop="name" label="字段名" min-width="130" show-overflow-tooltip />
                <el-table-column prop="dtype" label="数据类型" width="120" show-overflow-tooltip />
                <el-table-column prop="description" label="业务含义" min-width="110" show-overflow-tooltip />
                <el-table-column label="可空" width="70" align="center">
                  <template #default="{ row }">{{ row.nullable ? '是' : '否' }}</template>
                </el-table-column>
              </el-table>
            </el-collapse-item>
          </el-collapse>
        </template>
        <el-empty v-else-if="!schemaLoading" description="暂无表结构信息" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Check,
  Connection,
  Grid,
  InfoFilled,
  Link,
  Refresh
} from '@element-plus/icons-vue'
import { api } from '../api'
import { DB_TYPE_OPTIONS, dbTypeLabel } from '../utils/constants'
import { formatDateTime } from '../utils/format'

function defaultForm() {
  return {
    name: '业务数据库',
    db_type: 'mysql',
    host: '127.0.0.1',
    port: 3306,
    username: '',
    password: '',
    database_name: '',
    sqlite_path: ''
  }
}

const form = reactive(defaultForm())
const connections = ref([])
const loading = ref(true)
const testing = ref(false)
const saving = ref(false)
const testResult = ref(null)
const schemaVisible = ref(false)
const schemaLoading = ref(false)
const schemaData = ref(null)
const activeTables = ref([])

const isSqlite = computed(() => form.db_type === 'sqlite')

function handleTypeChange(value) {
  testResult.value = null
  if (value === 'mysql') form.port = 3306
  if (value === 'postgresql') form.port = 5432
}

function buildPayload() {
  return {
    name: form.name.trim(),
    db_type: form.db_type,
    host: form.host.trim(),
    port: Number(form.port) || (form.db_type === 'postgresql' ? 5432 : 3306),
    username: form.username,
    password: form.password,
    database_name: form.database_name.trim(),
    sqlite_path: form.sqlite_path.trim()
  }
}

function validateForm() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入连接名称')
    return false
  }
  if (isSqlite.value) {
    if (!form.sqlite_path.trim()) {
      ElMessage.warning('请填写 SQLite 数据库文件路径')
      return false
    }
    return true
  }
  if (!form.host.trim()) {
    ElMessage.warning('请输入主机地址')
    return false
  }
  if (!form.port) {
    ElMessage.warning('请输入数据库端口')
    return false
  }
  if (!form.database_name.trim()) {
    ElMessage.warning('请输入数据库名称')
    return false
  }
  return true
}

async function loadConnections() {
  loading.value = true
  try {
    const res = await api.listConnections()
    connections.value = res.items || []
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    loading.value = false
  }
}

async function testConnection() {
  if (!validateForm()) return
  testing.value = true
  testResult.value = null
  try {
    const res = await api.testConnection(buildPayload())
    testResult.value = res
    if (res.success) {
      ElMessage.success(res.message || '连接成功')
    } else {
      ElMessage.warning(res.message || '连接失败')
    }
  } catch (error) {
    testResult.value = { success: false, message: '连接失败，请检查配置' }
  } finally {
    testing.value = false
  }
}

async function saveConnection() {
  if (!validateForm()) return
  saving.value = true
  try {
    await api.saveConnection(buildPayload())
    ElMessage.success('数据库连接已保存')
    await loadConnections()
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    saving.value = false
  }
}

function addressOf(row) {
  if (row.db_type === 'sqlite') return row.sqlite_path || '-'
  return `${row.host || '-'}:${row.port || '-'} / ${row.database_name || '-'}`
}

async function openSchema(row) {
  schemaVisible.value = true
  schemaLoading.value = true
  schemaData.value = null
  activeTables.value = []
  try {
    const res = await api.connectionSchema(row.id)
    schemaData.value = res
    if (res.tables?.length) {
      activeTables.value = [res.tables[0].name]
    }
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  } finally {
    schemaLoading.value = false
  }
}

async function removeConnection(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除数据库连接「${row.name}」吗？删除后可重新创建。`,
      '删除连接',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch (error) {
    return
  }
  try {
    await api.deleteConnection(row.id)
    ElMessage.success('数据库连接已删除')
    await loadConnections()
  } catch (error) {
    // 错误提示由请求拦截器统一处理
  }
}

onMounted(loadConnections)
</script>

<style scoped>
.connections-layout {
  grid-template-columns: 408px minmax(0, 1fr);
  align-items: start;
}

.conn-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.conn-form :deep(.el-form-item__label) {
  padding-bottom: 5px;
  font-size: 12px;
  color: #5b6b88;
}

.form-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 112px;
  gap: 12px;
}

.form-actions {
  display: flex;
  gap: 10px;
  margin-top: 4px;
}

.form-actions .el-button {
  flex: 1;
}

.test-alert {
  margin-top: 14px;
}

.form-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
  padding: 9px 11px;
  font-size: 11.5px;
  color: #7b8aa6;
  background: #fafcff;
  border: 1px dashed #e2eaf7;
  border-radius: 9px;
}

.conn-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.conn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex: none;
  color: var(--primary);
  background: #f0f4ff;
  border-radius: 8px;
}

.conn-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-weight: 500;
  color: #33445f;
}

.conn-text .muted {
  font-size: 10.5px;
  font-weight: 400;
}

.schema-body {
  min-height: 260px;
}

.schema-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 15px 16px;
  background: linear-gradient(135deg, #f3f7ff, #f8faff);
  border: 1px solid #e2eaff;
  border-radius: 12px;
}

.schema-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}

.schema-desc {
  margin-top: 5px;
  font-size: 12px;
}

.allowed-tables {
  margin-top: 16px;
}

.allowed-label {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.schema-collapse {
  margin-top: 14px;
  border: 1px solid #edf2fa;
  border-radius: 12px;
  overflow: hidden;
}

.schema-collapse :deep(.el-collapse-item__header) {
  padding: 0 14px;
  height: 46px;
  background: #fbfcff;
  border-bottom-color: #f0f4fb;
}

.schema-collapse :deep(.el-collapse-item__wrap) {
  border-bottom-color: #f0f4fb;
}

.schema-collapse :deep(.el-collapse-item__content) {
  padding: 12px 14px;
}

.table-title {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 500;
  color: #33445f;
}

@media (max-width: 1180px) {
  .connections-layout {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr 120px;
  }
}
</style>
