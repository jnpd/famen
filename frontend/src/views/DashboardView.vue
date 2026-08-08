<template>
  <div class="dashboard-page">
    <div class="page-toolbar">
      <div></div>
      <div class="toolbar-actions">
        <el-button @click="createDialog = true"><el-icon><Plus /></el-icon>新建知识库</el-button>
        <el-button type="primary" @click="drawer = true"><el-icon><DocumentAdd /></el-icon>Excel批量导入</el-button>
      </div>
    </div>

    <section class="metric-grid">
      <div class="metric-card">
        <div class="metric-icon green"><el-icon><Coin /></el-icon></div>
        <div><div class="metric-label">知识库数量</div><div class="metric-value">{{ dashboard.knowledge_base_count || 0 }}<small>个</small></div></div>
      </div>
      <div class="metric-card">
        <div class="metric-icon green"><el-icon><Document /></el-icon></div>
        <div><div class="metric-label">标准条目数</div><div class="metric-value">{{ formatNumber(dashboard.standard_record_count) }}<small>条</small></div></div>
      </div>
      <div class="metric-card">
        <div class="metric-icon purple">ƒx</div>
        <div><div class="metric-label">公式条目数</div><div class="metric-value">{{ formatNumber(dashboard.formula_record_count) }}<small>条</small></div></div>
      </div>
      <div class="metric-card">
        <div class="metric-icon blue"><el-icon><Upload /></el-icon></div>
        <div><div class="metric-label">今日导入数</div><div class="metric-value">{{ formatNumber(dashboard.today_import_count) }}<small>条</small></div></div>
      </div>
    </section>

    <section class="graph-card">
      <div class="section-title">知识库结构图</div>
      <div class="legend"><span class="dot green"></span>标准库 <span class="dot purple"></span>公式库 <span class="dot blue"></span>参数库 <span class="dot gray"></span>规则库</div>
      <div class="knowledge-graph">
        <svg class="graph-lines" viewBox="0 0 900 300" preserveAspectRatio="none">
          <path d="M245 95 C360 95, 430 95, 540 95" />
          <path d="M250 125 C250 190, 195 190, 195 225" />
          <path d="M250 125 C250 190, 385 190, 385 225" />
          <path d="M585 125 C585 185, 680 185, 680 225" class="purple-line" />
          <path d="M435 240 C505 240, 560 240, 630 240" class="dash-line" />
        </svg>
        <button class="node-card main green-border" @click="goByCode('standard')">
          <div class="node-icon"><el-icon><Coin /></el-icon></div>
          <div><b>标准数字库</b><span>B16.5 / B34 / 6D</span><small>条目数 {{ countByCode('standard') }}</small></div>
        </button>
        <button class="node-card main formula purple-border" @click="goByCode('formula')">
          <div class="node-icon fx">ƒx</div>
          <div><b>企业公式库</b><span>主任签字 · 版本管理</span><small>条目数 {{ countByCode('formula') }}</small></div>
        </button>
        <button class="node-card child left green-border" @click="goByCode('material')">
          <el-icon><Files /></el-icon><div><b>材料标准库</b><small>条目数 {{ countByCode('material') }}</small></div>
        </button>
        <button class="node-card child middle green-border" @click="goByCode('parameter')">
          <el-icon><TrendCharts /></el-icon><div><b>阀门参数库</b><small>条目数 {{ countByCode('parameter') }}</small></div>
        </button>
        <button class="node-card child right blue-border" @click="goByCode('bom')">
          <el-icon><Box /></el-icon><div><b>BOM规则库</b><small>条目数 {{ countByCode('bom') }}</small></div>
        </button>
      </div>
    </section>

    <section class="recent-card">
      <div class="section-title">近期导入记录</div>
      <el-table :data="dashboard.recent_imports || []" height="300" class="clean-table">
        <el-table-column label="库类型" width="120">
          <template #default>Excel导入</template>
        </el-table-column>
        <el-table-column prop="filename" label="名称" min-width="240" />
        <el-table-column prop="sheet_name" label="Sheet" width="130" />
        <el-table-column prop="success_rows" label="成功行" width="100" />
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="statusType(scope.row.status)" effect="light">{{ statusText(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="更新时间" width="170" />
      </el-table>
    </section>

    <ImportDrawer v-model="drawer" @imported="reload" />

    <el-dialog v-model="createDialog" title="新建知识库" width="480px">
      <el-form label-position="top">
        <el-form-item label="名称"><el-input v-model="newKb.name" /></el-form-item>
        <el-form-item label="编码"><el-input v-model="newKb.code" placeholder="例如 standard_custom" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="newKb.type" style="width:100%">
            <el-option label="标准数字库" value="standard" /><el-option label="企业公式库" value="formula" />
            <el-option label="阀门参数库" value="parameter" /><el-option label="材料标准库" value="material" />
            <el-option label="BOM规则库" value="bom" /><el-option label="基础字典库" value="dictionary" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="newKb.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="createDialog=false">取消</el-button><el-button type="primary" @click="createKb">创建</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Box, Coin, Document, DocumentAdd, Files, Plus, TrendCharts, Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import http from '../api/http.js'
import ImportDrawer from '../components/ImportDrawer.vue'

const router = useRouter()
const dashboard = ref({ knowledge_bases: [], recent_imports: [] })
const drawer = ref(false)
const createDialog = ref(false)
const newKb = reactive({ name: '', code: '', type: 'standard', description: '' })

const formatNumber = n => Number(n || 0).toLocaleString()
const countByCode = code => formatNumber(dashboard.value.knowledge_bases?.find(x => x.code === code)?.record_count || 0)

function goByCode(code) {
  const kb = dashboard.value.knowledge_bases?.find(x => x.code === code)
  if (kb) router.push({ name: 'library', params: { id: kb.id } })
}

function statusText(status) {
  return ({ SUCCESS: '导入成功', FAILED: '导入失败', READY: '待确认', INSPECTING: '解析中', UPLOADED: '已上传' })[status] || status
}
function statusType(status) { return status === 'SUCCESS' ? 'success' : status === 'FAILED' ? 'danger' : 'warning' }

async function reload() {
  const { data } = await http.get('/dashboard')
  dashboard.value = data
}

async function createKb() {
  try {
    await http.post('/knowledge-bases', newKb)
    ElMessage.success('知识库已创建')
    createDialog.value = false
    Object.assign(newKb, { name: '', code: '', type: 'standard', description: '' })
    await reload()
  } catch (e) { ElMessage.error(e.message) }
}

onMounted(reload)
</script>
