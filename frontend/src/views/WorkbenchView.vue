<template>
  <div class="workbench-page" v-loading="loading">
    <div class="workbench-hero">
      <div>
        <div class="eyebrow">工程参数生成</div>
        <h1>固定球阀参数工作台</h1>
        <p>用户只填写设计边界，系统负责从各知识表中查值、汇总来源，并标出仍需补齐的数据。</p>
      </div>
      <div class="hero-status">
        <span>已接入数据集</span>
        <b>{{ datasets.length }}</b>
      </div>
    </div>

    <div class="workbench-layout">
      <section class="input-card">
        <div class="card-title-row">
          <div>
            <b>① 输入设计条件</b>
            <span>这些是本次阀门设计的查询条件，不是零件全部尺寸。</span>
          </div>
          <el-tag type="info" effect="plain">输入</el-tag>
        </div>

        <el-form label-position="top" class="input-grid">
          <el-form-item label="阀门结构">
            <el-input v-model="form.valve_structure" />
          </el-form-item>
          <el-form-item label="公称口径">
            <el-select v-model="form.nps" filterable allow-create default-first-option style="width:100%">
              <el-option v-for="item in options.nps" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="压力等级">
            <el-select v-model="form.pressure_class" filterable allow-create default-first-option style="width:100%">
              <el-option v-for="item in options.pressure" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="通径形式">
            <el-select v-model="form.bore_type" filterable allow-create default-first-option style="width:100%">
              <el-option v-for="item in options.boreType" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="端部连接">
            <el-select v-model="form.end_connection" filterable allow-create default-first-option style="width:100%">
              <el-option v-for="item in options.endConnection" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="阀体材料">
            <el-input v-model="form.body_material" placeholder="例如 A105" />
          </el-form-item>
          <el-form-item label="球体材料组">
            <el-select v-model="form.ball_material_group" filterable allow-create default-first-option style="width:100%">
              <el-option v-for="item in options.ballMaterial" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="阀座材料">
            <el-input v-model="form.seat_material" placeholder="例如 PEEK" />
          </el-form-item>
          <el-form-item label="设计压力">
            <el-input v-model="form.design_pressure"><template #append>MPa</template></el-input>
          </el-form-item>
          <el-form-item label="设计温度">
            <el-input v-model="form.design_temperature"><template #append>℃</template></el-input>
          </el-form-item>
          <el-form-item label="介质" class="span-2">
            <el-input v-model="form.medium" placeholder="例如 天然气" />
          </el-form-item>
        </el-form>

        <div class="generate-row">
          <el-button @click="resetForm">恢复示例</el-button>
          <el-button type="primary" :loading="generating" @click="generate">
            <el-icon><Operation /></el-icon>生成综合参数
          </el-button>
        </div>
      </section>

      <section class="snapshot-card">
        <div class="card-title-row">
          <div>
            <b>② 输入快照</b>
            <span>后续生成日志、SolidWorks 驱动和校核都应绑定这组条件。</span>
          </div>
          <el-tag type="success" effect="plain">本次设计</el-tag>
        </div>
        <div class="snapshot-grid">
          <div><span>口径 / 压力</span><b>{{ form.nps }} / {{ form.pressure_class }}</b></div>
          <div><span>通径 / 连接</span><b>{{ form.bore_type }} / {{ form.end_connection }}</b></div>
          <div><span>材料</span><b>{{ form.body_material }} / {{ form.ball_material_group }}</b></div>
          <div><span>设计工况</span><b>{{ form.design_pressure }} MPa · {{ form.design_temperature }} ℃</b></div>
          <div class="wide"><span>介质</span><b>{{ form.medium || '-' }}</b></div>
        </div>
      </section>
    </div>

    <div v-if="generated" class="result-summary">
      <div><span>汇总参数</span><b>{{ allResults.length }}</b></div>
      <div><span>已有有效值</span><b class="ok-number">{{ readyCount }}</b></div>
      <div><span>待补标准/计算</span><b class="warn-number">{{ pendingCount }}</b></div>
      <div><span>缺少数据集</span><b>{{ missingDatasets.length }}</b></div>
    </div>

    <el-alert
      v-if="generated && pendingCount"
      class="result-alert"
      type="warning"
      :closable="false"
      title="当前结果中仍有待授权标准值或待计算项。工作台会保留来源和状态，但不会用猜测值替代正式工程数据。"
    />

    <el-alert
      v-if="generated && missingDatasets.length"
      class="result-alert"
      type="error"
      :closable="false"
      :title="`缺少数据集：${missingDatasets.join('、')}。请先完成对应 Excel 数据导入。`"
    />

    <div v-if="generated" class="result-grid">
      <section class="result-card">
        <div class="result-card-head">
          <div><span class="step-dot">③</span><b>零件几何参数</b></div>
          <span>输出 · 左</span>
        </div>
        <el-table :data="geometryResults" class="result-table" border>
          <el-table-column prop="name" label="参数" min-width="150" />
          <el-table-column label="取值" min-width="145">
            <template #default="scope"><b :class="valueClass(scope.row)">{{ scope.row.value ?? '-' }}</b></template>
          </el-table-column>
          <el-table-column prop="unit" label="单位" width="80" />
          <el-table-column prop="source" label="来源" min-width="135" />
          <el-table-column label="状态" width="125">
            <template #default="scope"><el-tag size="small" :type="statusType(scope.row.status)" effect="plain">{{ scope.row.status || '待确认' }}</el-tag></template>
          </el-table-column>
        </el-table>
      </section>

      <section class="result-card">
        <div class="result-card-head">
          <div><span class="step-dot">④</span><b>装配 / 接口参数</b></div>
          <span>输出 · 右</span>
        </div>
        <el-table :data="assemblyResults" class="result-table" border>
          <el-table-column prop="name" label="参数" min-width="150" />
          <el-table-column label="取值" min-width="145">
            <template #default="scope"><b :class="valueClass(scope.row)">{{ scope.row.value ?? '-' }}</b></template>
          </el-table-column>
          <el-table-column prop="unit" label="单位" width="80" />
          <el-table-column prop="source" label="来源" min-width="135" />
          <el-table-column label="状态" width="125">
            <template #default="scope"><el-tag size="small" :type="statusType(scope.row.status)" effect="plain">{{ scope.row.status || '待确认' }}</el-tag></template>
          </el-table-column>
        </el-table>
      </section>
    </div>

    <div v-else class="workbench-empty">
      <el-empty description="填写设计条件后点击“生成综合参数”，系统会把分散在各知识表中的数据组合起来。" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Operation } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import http from '../api/http.js'

const loading = ref(false)
const generating = ref(false)
const generated = ref(false)
const datasets = ref([])
const detailCache = new Map()
const missingDatasets = ref([])
const geometryResults = ref([])
const assemblyResults = ref([])
const options = reactive({ nps: [], pressure: [], boreType: [], endConnection: [], ballMaterial: [] })

const defaults = {
  valve_structure: '固定球阀',
  nps: 'NPS12',
  pressure_class: 'CL600',
  bore_type: '全通径',
  end_connection: 'RF法兰',
  body_material: 'A105',
  ball_material_group: '碳钢/合金钢球',
  seat_material: 'PEEK',
  design_pressure: '2',
  design_temperature: '-29~120',
  medium: '天然气'
}
const form = reactive({ ...defaults })

const allResults = computed(() => [...geometryResults.value, ...assemblyResults.value])
const pendingCount = computed(() => allResults.value.filter(x => isPending(x)).length)
const readyCount = computed(() => allResults.value.length - pendingCount.value)

function datasetByName(name) {
  return datasets.value.find(x => x.name === name)
}

async function getDetail(name) {
  const ds = datasetByName(name)
  if (!ds) {
    if (!missingDatasets.value.includes(name)) missingDatasets.value.push(name)
    return null
  }
  if (detailCache.has(ds.id)) return detailCache.get(ds.id)
  const { data } = await http.get(`/datasets/${ds.id}`)
  detailCache.set(ds.id, data)
  return data
}

function findField(detail, fieldName) {
  return (detail?.fields || []).find(f => f.field_name === fieldName || f.source_name === fieldName)
}

function valueOf(detail, row, fieldName) {
  const field = findField(detail, fieldName)
  return field ? row?.[field.field_code] : undefined
}

function unitOf(detail, row, fieldName, fallback = '') {
  const field = findField(detail, fieldName)
  if (field?.unit) return field.unit
  const rowUnit = valueOf(detail, row, '单位')
  return rowUnit && rowUnit !== '-' ? rowUnit : fallback
}

async function queryDataset(name, filters = {}, pageSize = 100) {
  const detail = await getDetail(name)
  if (!detail) return { detail: null, rows: [] }
  const payloadFilters = {}
  for (const [fieldName, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === '') continue
    const field = findField(detail, fieldName)
    if (field) payloadFilters[field.field_code] = value
  }
  const { data } = await http.post(`/datasets/${detail.id}/query`, {
    page: 1,
    page_size: pageSize,
    search: '',
    filters: payloadFilters,
    sort_by: null,
    sort_order: 'asc'
  })
  return { detail, rows: data.rows || [] }
}

function result(name, value, unit, source, status = '', extra = {}) {
  return { name, value: value ?? '-', unit: unit || '-', source, status: status || inferStatus(value), ...extra }
}

function inferStatus(value) {
  const text = String(value ?? '')
  if (!text || text === '-' || text.includes('待授权') || text.includes('待计算') || text.includes('待确认')) return '待补齐'
  return '可用'
}

function isPending(row) {
  const text = `${row.value ?? ''} ${row.status ?? ''}`
  return !row.value || row.value === '-' || /待授权|待计算|待确认|待补齐|缺失/.test(text)
}

function statusType(status) {
  const text = String(status || '')
  if (/已录入|可用|通过|规则已录入/.test(text)) return 'success'
  if (/待授权|待计算|待确认|待补齐/.test(text)) return 'warning'
  if (/缺失|失败|错误/.test(text)) return 'danger'
  return 'info'
}

function valueClass(row) { return isPending(row) ? 'pending-value' : 'ready-value' }

async function generate() {
  generating.value = true
  generated.value = false
  missingDatasets.value = []
  try {
    const [diameter, bore, face, flange, ball, wall] = await Promise.all([
      queryDataset('口径基础表', { '公称口径': form.nps }),
      queryDataset('通径表', { '公称口径': form.nps, '压力等级': form.pressure_class, '通径形式': form.bore_type }),
      queryDataset('结构长度表', { '公称口径': form.nps, '压力等级': form.pressure_class, '端部连接': form.end_connection }),
      queryDataset('法兰尺寸表', { '公称口径': form.nps, '压力等级': form.pressure_class, '端部连接': form.end_connection }),
      queryDataset('球体直径表', { '公称口径': form.nps, '压力等级': form.pressure_class, '球体材料组': form.ball_material_group }),
      queryDataset('阀体壁厚表', { '压力等级': form.pressure_class, '材料组': form.body_material })
    ])

    const diameterRow = diameter.rows[0]
    const boreRow = bore.rows[0]
    const faceRow = face.rows[0]
    const flangeRow = flange.rows[0]
    const ballRow = ball.rows[0]
    const wallRow = wall.rows[0]

    geometryResults.value = [
      result('通道直径 D_BORE', valueOf(bore.detail, boreRow, '通道直径d'), unitOf(bore.detail, boreRow, '通道直径d', 'mm'), '通径表', valueOf(bore.detail, boreRow, '数据状态')),
      result('球体直径 D_BALL', valueOf(ball.detail, ballRow, '球体直径S'), unitOf(ball.detail, ballRow, '球体直径S', 'mm'), '球体直径表', valueOf(ball.detail, ballRow, '数据状态')),
      result('阀体最小壁厚', valueOf(wall.detail, wallRow, '最小壁厚'), unitOf(wall.detail, wallRow, '最小壁厚', 'mm'), '阀体壁厚表', valueOf(wall.detail, wallRow, '数据状态')),
      result('端法兰外径', valueOf(flange.detail, flangeRow, '法兰外径'), unitOf(flange.detail, flangeRow, '法兰外径', 'mm'), '法兰尺寸表'),
      result('端法兰厚度', valueOf(flange.detail, flangeRow, '法兰厚度'), unitOf(flange.detail, flangeRow, '法兰厚度', 'mm'), '法兰尺寸表'),
      result('螺栓中心圆', valueOf(flange.detail, flangeRow, '螺栓中心圆'), unitOf(flange.detail, flangeRow, '螺栓中心圆', 'mm'), '法兰尺寸表'),
      result('螺栓孔直径', valueOf(flange.detail, flangeRow, '螺栓孔直径'), unitOf(flange.detail, flangeRow, '螺栓孔直径', 'mm'), '法兰尺寸表')
    ]

    assemblyResults.value = [
      result('公称口径', form.nps, '-', '用户输入', '可用'),
      result('DN', valueOf(diameter.detail, diameterRow, 'DN'), '-', '口径基础表'),
      result('压力等级', form.pressure_class, '-', '用户输入', '可用'),
      result('结构长度 L_FACE_TO_FACE', valueOf(face.detail, faceRow, '结构长度L'), unitOf(face.detail, faceRow, '结构长度L', 'mm'), '结构长度表', valueOf(face.detail, faceRow, '数据状态')),
      result('端部连接', form.end_connection, '-', '用户输入', '可用'),
      result('螺栓规格', valueOf(flange.detail, flangeRow, '螺栓规格'), '-', '法兰尺寸表'),
      result('螺栓数量', valueOf(flange.detail, flangeRow, '螺栓数量'), '个', '法兰尺寸表'),
      result('设计压力', form.design_pressure, 'MPa', '用户输入', '可用'),
      result('设计温度', form.design_temperature, '℃', '用户输入', '可用'),
      result('介质', form.medium, '-', '用户输入', '可用')
    ]

    generated.value = true
  } catch (e) {
    ElMessage.error(`综合参数生成失败：${e.message}`)
  } finally {
    generating.value = false
  }
}

async function loadOptionValues(datasetName, fieldName) {
  const ctx = await queryDataset(datasetName, {}, 200)
  if (!ctx.detail) return []
  return [...new Set(ctx.rows.map(row => valueOf(ctx.detail, row, fieldName)).filter(Boolean).map(String))]
}

async function loadOptions() {
  const [nps, pressure, boreType, endConnection, ballMaterial] = await Promise.all([
    loadOptionValues('口径基础表', '公称口径'),
    loadOptionValues('压力等级表', '压力等级'),
    loadOptionValues('通径表', '通径形式'),
    loadOptionValues('结构长度表', '端部连接'),
    loadOptionValues('球体直径表', '球体材料组')
  ])
  options.nps = nps
  options.pressure = pressure
  options.boreType = boreType
  options.endConnection = endConnection
  options.ballMaterial = ballMaterial
}

function resetForm() { Object.assign(form, defaults) }

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await http.get('/datasets')
    datasets.value = data || []
    await loadOptions()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.workbench-page { padding-bottom: 30px; }
.workbench-hero { background:#fff; border:1px solid #e6ebf2; border-radius:12px; padding:22px 24px; display:flex; justify-content:space-between; gap:30px; align-items:flex-start; }
.workbench-hero h1 { margin:4px 0 7px; font-size:24px; color:#1f2d3d; }
.workbench-hero p { margin:0; color:#7a899d; font-size:13px; max-width:760px; line-height:1.7; }
.hero-status { min-width:130px; background:#f7f9fc; border-radius:10px; padding:14px 16px; text-align:right; }
.hero-status span { display:block; font-size:11px; color:#8896a9; }
.hero-status b { display:block; margin-top:4px; font-size:24px; color:#1f2d3d; }
.workbench-layout { display:grid; grid-template-columns:minmax(0,1.7fr) minmax(300px,.8fr); gap:14px; margin-top:14px; align-items:start; }
.input-card,.snapshot-card,.result-card { background:#fff; border:1px solid #e6ebf2; border-radius:11px; box-shadow:0 3px 12px rgba(31,50,75,.03); }
.input-card,.snapshot-card { padding:18px 20px; }
.card-title-row { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:16px; }
.card-title-row b { display:block; color:#26364b; font-size:15px; }
.card-title-row span { display:block; color:#8896a9; font-size:11px; margin-top:5px; line-height:1.5; }
.input-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:0 14px; }
.input-grid :deep(.el-form-item) { margin-bottom:14px; }
.input-grid :deep(.el-form-item__label) { font-size:12px; color:#66778e; padding-bottom:5px; }
.input-grid .span-2 { grid-column:span 2; }
.generate-row { display:flex; justify-content:flex-end; gap:8px; padding-top:14px; border-top:1px solid #edf1f5; }
.snapshot-grid { display:grid; grid-template-columns:1fr; gap:10px; }
.snapshot-grid div { padding:11px 12px; background:#f7f9fc; border-radius:8px; }
.snapshot-grid span { display:block; font-size:11px; color:#8795a8; }
.snapshot-grid b { display:block; margin-top:5px; font-size:13px; color:#33465e; line-height:1.5; }
.result-summary { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-top:14px; }
.result-summary>div { background:#fff; border:1px solid #e6ebf2; border-radius:10px; padding:15px 18px; }
.result-summary span { display:block; color:#7b8ba0; font-size:11px; }
.result-summary b { display:block; margin-top:5px; font-size:21px; color:#26364b; }
.ok-number { color:#289b63 !important; }.warn-number { color:#d88a18 !important; }
.result-alert { margin-top:14px; }
.result-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:14px; }
.result-card { padding:0 16px 14px; overflow:hidden; }
.result-card-head { min-height:58px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid #edf1f5; margin-bottom:14px; }
.result-card-head>div { display:flex; align-items:center; gap:9px; }.result-card-head b { color:#26364b; font-size:15px; }
.result-card-head>span { color:#8b99aa; font-size:11px; }
.step-dot { width:27px; height:27px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; background:#eaf2ff; color:#1262df; font-weight:700; font-size:12px; }
.result-table { --el-table-header-bg-color:#f7f9fc; }
.ready-value { color:#1f2d3d; }.pending-value { color:#d98216; font-weight:600; }
.workbench-empty { margin-top:14px; background:#fff; border:1px solid #e6ebf2; border-radius:11px; padding:40px; }
@media (max-width: 1450px) { .input-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.result-grid{grid-template-columns:1fr}.workbench-layout{grid-template-columns:1fr}.input-grid .span-2{grid-column:span 2} }
</style>
