<template>
  <div class="dataset-page" v-loading="loading">
    <div class="dataset-head">
      <div>
        <div class="breadcrumbs">{{ detail.knowledge_base?.name }} / 参数数据</div>
        <h1>{{ detail.name }}</h1>
        <div class="dataset-meta">
          <el-tag effect="plain">{{ detail.record_count || 0 }} 条</el-tag>
          <el-tag effect="plain">{{ detail.field_count || 0 }} 字段</el-tag>
          <span>来源：{{ detail.source_file_name || '手工创建' }}</span>
          <span>Sheet：{{ detail.sheet_name || '-' }}</span>
        </div>
      </div>
      <div>
        <el-button @click="exportExcel"><el-icon><Download /></el-icon>导出Excel</el-button>
        <el-button type="primary" @click="drawer=true"><el-icon><DocumentAdd /></el-icon>继续导入</el-button>
      </div>
    </div>

    <div class="query-card">
      <div class="query-top">
        <div class="section-title">参数查询</div>
        <div class="query-actions">
          <el-input v-model="query.search" clearable placeholder="搜索任意可检索字段" style="width:260px" @keyup.enter="loadRows" />
          <el-button type="primary" @click="resetPageAndLoad">搜索</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </div>
      </div>
      <div class="filter-grid">
        <div v-for="f in filterFields.slice(0, 6)" :key="f.field_code" class="filter-item">
          <label>{{ f.field_name }}</label>
          <el-input v-model="query.filters[f.field_code]" clearable :placeholder="`筛选${f.field_name}`" @keyup.enter="resetPageAndLoad" />
        </div>
      </div>
    </div>

    <div class="data-table-card">
      <div class="table-head">
        <div><b>参数指标</b><span>动态字段来自 Excel 映射</span></div>
        <el-button @click="showFields = !showFields">{{ showFields ? '收起字段定义' : '字段定义' }}</el-button>
      </div>

      <div v-if="showFields" class="field-chips">
        <el-tag v-for="f in detail.fields || []" :key="f.id" effect="plain">
          {{ f.field_name }} · {{ f.field_code }}<template v-if="f.unit"> · {{ f.unit }}</template>
        </el-tag>
      </div>

      <el-table :data="rows" border class="data-table" @sort-change="sortChange">
        <el-table-column type="index" label="#" width="56" fixed />
        <el-table-column
          v-for="f in detail.fields || []"
          :key="f.field_code"
          :prop="f.field_code"
          :label="f.unit ? `${f.field_name} (${f.unit})` : f.field_name"
          min-width="140"
          sortable="custom"
          show-overflow-tooltip
        />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="scope">
            <el-button link type="primary" @click="editRow(scope.row)">编辑</el-button>
            <el-button link type="danger" @click="removeRow(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-row">
        <span>共 {{ total }} 条</span>
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          layout="sizes, prev, pager, next, jumper"
          :page-sizes="[10,20,50,100]"
          :total="total"
          @change="loadRows"
        />
      </div>
    </div>

    <el-dialog v-model="editVisible" title="编辑参数" width="620px">
      <el-form label-position="top" class="edit-grid">
        <el-form-item v-for="f in detail.fields || []" :key="f.field_code" :label="f.unit ? `${f.field_name} (${f.unit})` : f.field_name">
          <el-input v-model="editData[f.field_code]" />
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="editVisible=false">取消</el-button><el-button type="primary" @click="saveRow">保存</el-button></template>
    </el-dialog>

    <ImportDrawer v-model="drawer" :default-knowledge-base-id="detail.knowledge_base?.id" />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { DocumentAdd, Download } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api/http.js'
import ImportDrawer from '../components/ImportDrawer.vue'

const route = useRoute()
const detail = ref({ fields: [] })
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const drawer = ref(false)
const showFields = ref(false)
const editVisible = ref(false)
const editId = ref(null)
const editData = reactive({})
const query = reactive({ page: 1, page_size: 20, search: '', filters: {}, sort_by: null, sort_order: 'asc' })

const filterFields = computed(() => (detail.value.fields || []).filter(x => x.filterable))

async function loadDetail() {
  const { data } = await http.get(`/datasets/${route.params.id}`)
  detail.value = data
  query.filters = {}
}

async function loadRows() {
  const { data } = await http.post(`/datasets/${route.params.id}/query`, query)
  rows.value = data.rows
  total.value = data.total
}

async function load() {
  loading.value = true
  try { await loadDetail(); await loadRows() } finally { loading.value = false }
}

function resetPageAndLoad() { query.page = 1; loadRows() }
function resetFilters() { query.search = ''; query.filters = {}; query.page = 1; loadRows() }
function sortChange({ prop, order }) { query.sort_by = prop; query.sort_order = order === 'descending' ? 'desc' : 'asc'; loadRows() }

function editRow(row) {
  editId.value = row._id
  for (const key of Object.keys(editData)) delete editData[key]
  for (const f of detail.value.fields || []) editData[f.field_code] = row[f.field_code] ?? ''
  editVisible.value = true
}
async function saveRow() {
  try {
    await http.put(`/records/${editId.value}`, { data: { ...editData } })
    ElMessage.success('保存成功')
    editVisible.value = false
    loadRows()
  } catch (e) { ElMessage.error(e.message) }
}
async function removeRow(row) {
  try {
    await ElMessageBox.confirm('确定删除这条参数吗？', '删除确认', { type: 'warning' })
    await http.delete(`/records/${row._id}`)
    ElMessage.success('已删除')
    await loadDetail(); await loadRows()
  } catch (e) { if (e !== 'cancel') console.warn(e) }
}
async function exportExcel() {
  try {
    const response = await http.get(`/datasets/${route.params.id}/export`, { responseType: 'blob' })
    const disposition = response.headers['content-disposition'] || ''
    let filename = `${detail.value.name || '参数数据'}.xlsx`
    const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
    const normalMatch = disposition.match(/filename=\"?([^\";]+)\"?/i)
    if (utf8Match?.[1]) filename = decodeURIComponent(utf8Match[1])
    else if (normalMatch?.[1]) filename = normalMatch[1]
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error(e.message || '导出失败')
  }
}

watch(() => route.params.id, load)
onMounted(load)
</script>
