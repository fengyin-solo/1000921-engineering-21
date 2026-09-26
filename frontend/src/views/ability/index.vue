<template>
  <section class="page" data-module="ability">
    <header class="page-head">
      <div>
        <h2>能力验证管理</h2>
        <p class="page-desc">维护能力验证，围绕验证编号、组织方、检测项目、参加人员做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记能力验证</button>
        <button class="btn" type="button" @click="exportRows">导出能力验证清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <label class="filter-item">
        <span>验证状态</span>
        <select v-model="filters.status">
          <option value="">全部状态</option>
          <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] === '' || row[column] == null ? '—' : row[column] }}</td>
          <td class="row-actions">
            <button
              v-for="action in availableActions(String(row.status))"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
            <span v-if="!availableActions(String(row.status)).length" class="muted">流程已结束</span>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无能力验证数据，可先登记能力验证</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条能力验证记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/ability'
const columns = ["验证编号", "组织方", "检测项目", "参加人员", "样品编号", "上报日期", "结果评定", "验证状态"]
const statuses = ["待参加", "待评定", "已通过", "未通过"]

const rows = ref<Row[]>([])
const statsRows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = ["验证编号", "组织方", "检测项目"]

const stats = computed(() => [
  { label: "待参加验证", value: countByStatus(statsRows.value, "待参加") },
  { label: "待评定验证", value: countByStatus(statsRows.value, "待评定") },
  { label: "已通过验证", value: countByStatus(statsRows.value, "已通过") },
  { label: "未通过验证", value: countByStatus(statsRows.value, "未通过") },
])

function countByStatus(source: Row[], status: string): number {
  return source.filter((row) => String(row.status) === status).length
}

// 状态机：待参加只能报名；待评定可补报结果或接收评定；终态无动作
function availableActions(status: string): string[] {
  if (status === "待参加") return ["报名参加"]
  if (status === "待评定") return ["上报结果", "接收评定-合格", "接收评定-不合格"]
  return []
}

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '能力验证登记入口尚未接入审批流，可调用接口 POST /api/ability 直接登记'
}

async function runAction(label: string, row: Row) {
  errorMessage.value = ''
  let action = label
  const values: Record<string, string> = {}
  if (label === '报名参加') {
    const participants = window.prompt('请输入参加人员（多人用顿号分隔）', String(row['参加人员'] ?? ''))
    if (participants === null) return
    values['参加人员'] = participants
  } else if (label === '上报结果') {
    const reportDate = window.prompt('请输入上报日期（YYYY-MM-DD）', new Date().toISOString().slice(0, 10))
    if (reportDate === null) return
    values['上报日期'] = reportDate
  } else if (label.startsWith('接收评定')) {
    action = '接收评定'
    values['结果评定'] = label.endsWith('合格') ? '合格' : '不合格'
  }
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action, ...values } }),
    })
    const payload = (await response.json().catch(() => null)) as { message?: string } | null
    if (!response.ok) {
      throw new Error(payload?.message ?? '能力验证动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '能力验证操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters.value)) {
    if (value.trim()) params.set(key === '验证编号' ? 'keyword' : key, value.trim())
  }
  try {
    // 列表按条件过滤；统计卡片单独拉一次全量，互不污染
    const [listResponse, allResponse] = await Promise.all([
      request(`${ENDPOINT}?${params.toString()}`),
      request(`${ENDPOINT}?size=200`),
    ])
    if (!listResponse.ok) throw new Error('能力验证列表读取失败')
    const listPayload = await listResponse.json()
    rows.value = listPayload.items ?? []
    total.value = listPayload.total ?? rows.value.length
    if (allResponse.ok) {
      const allPayload = await allResponse.json()
      statsRows.value = allPayload.items ?? []
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '能力验证列表读取失败'
  }
}

onMounted(reload)
</script>
