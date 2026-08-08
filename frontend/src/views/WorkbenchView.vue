<template>
  <div class="workbench-page" v-loading="loading">
    <div class="workbench-hero">
      <div>
        <div class="eyebrow">工程参数生成</div>
        <h1>固定球阀参数工作台</h1>
        <p>这里不是另一张 Excel，而是把基础字典、标准数字、阀门参数和企业规则组合成“一台阀门的一份结果”。</p>
      </div>
      <div class="hero-count"><span>已接入数据集</span><b>{{ datasets.length }}</b></div>
    </div>

    <div class="workbench-top">
      <section class="panel input-panel">
        <div class="panel-title">
          <div><b>① 输入设计条件</b><span>用户只输入设计边界，系统负责查表和汇总。</span></div>
          <el-tag effect="plain">输入</el-tag>
        </div>

        <el-form label-position="top" class="input-grid">
          <el-form-item label="阀门结构"><el-input v-model="form.valve_structure" /></el-form-item>
          <el-form-item label="公称口径">
            <el-select v-model="form.nps" filterable allow-create style="width:100%"><el-option v-for="x in options.nps" :key="x" :label="x" :value="x" /></el-select>
          </el-form-item>
          <el-form-item label="压力等级">
            <el-select v-model="form.pressure_class" filterable allow-create style="width:100%"><el-option v-for="x in options.pressure" :key="x" :label="x" :value="x" /></el-select>
          </el-form-item>

          <el-form-item label="通径形式">
            <el-select v-model="form.bore_type" filterable allow-create style="width:100%"><el-option v-for="x in options.boreType" :key="x" :label="x" :value="x" /></el-select>
          </el-form-item>
          <el-form-item label="端部连接">
            <el-select v-model="form.end_connection" filterable allow-create style="width:100%"><el-option v-for="x in options.endConnection" :key="x" :label="x" :value="x" /></el-select>
          </el-form-item>
          <el-form-item label="阀体材料"><el-input v-model="form.body_material" placeholder="例如 A105" /></el-form-item>

          <el-form-item label="球体材料组">
            <el-select v-model="form.ball_material_group" filterable allow-create style="width:100%"><el-option v-for="x in options.ballMaterial" :key="x" :label="x" :value="x" /></el-select>
          </el-form-item>
          <el-form-item label="阀座材料"><el-input v-model="form.seat_material" placeholder="例如 PEEK" /></el-form-item>
          <el-form-item label="设计压力"><el-input v-model="form.design_pressure"><template #append>MPa</template></el-input></el-form-item>

          <el-form-item label="设计温度"><el-input v-model="form.design_temperature"><template #append>℃</template></el-input></el-form-item>
          <el-form-item label="泄漏等级">
            <el-select v-model="form.leakage_level" filterable allow-create default-first-option placeholder="请选择或输入泄漏等级" style="width:100%">
              <el-option v-for="x in options.leakage" :key="x" :label="x" :value="x" />
            </el-select>
          </el-form-item>
          <el-form-item label="介质"><el-input v-model="form.medium" placeholder="例如 天然气" /></el-form-item>
        </el-form>

        <div v-if="isDirty" class="dirty-tip">输入条件已变化，当前结果仍是上一次生成结果。请重新生成后再保存。</div>
        <div class="action-row">
          <el-button @click="resetForm">恢复示例</el-button>
          <el-button type="success" plain :loading="saving" :disabled="!generated || isDirty" @click="saveToKnowledgeBase">保存为知识库</el-button>
          <el-button type="primary" :loading="generating" @click="generate"><el-icon><Operation /></el-icon>生成综合参数</el-button>
        </div>
      </section>

      <section class="panel snapshot-panel">
        <div class="panel-title"><div><b>② 本次设计快照</b><span>后面 SolidWorks 生成、校核、日志都绑定这组输入。</span></div></div>
        <div class="snapshot-list">
          <div><span>口径 / 压力</span><b>{{ form.nps }} / {{ form.pressure_class }}</b></div>
          <div><span>通径 / 连接</span><b>{{ form.bore_type }} / {{ form.end_connection }}</b></div>
          <div><span>材料</span><b>{{ form.body_material }} / {{ form.ball_material_group }}</b></div>
          <div><span>设计工况</span><b>{{ form.design_pressure }} MPa · {{ form.design_temperature }} ℃</b></div>
          <div><span>泄漏等级</span><b>{{ form.leakage_level || '-' }}</b></div>
          <div><span>介质</span><b>{{ form.medium || '-' }}</b></div>
        </div>

        <div v-if="lastSaved" class="saved-card">
          <div class="saved-head"><span>最近一次保存</span><el-tag type="success" size="small">已入知识库</el-tag></div>
          <b>{{ lastSaved.dataset_name }}</b>
          <small>{{ lastSaved.saved_at }} · {{ lastSaved.record_count }} 条参数记录</small>
          <div class="saved-actions">
            <el-button size="small" @click="openSavedDataset">查看本次记录</el-button>
            <el-button size="small" type="primary" plain @click="openResultLibrary">打开设计成果库</el-button>
          </div>
        </div>
      </section>
    </div>

    <template v-if="generated">
      <div class="summary-row">
        <div><span>汇总参数</span><b>{{ allResults.length }}</b></div>
        <div><span>已有有效值</span><b class="ok">{{ readyCount }}</b></div>
        <div><span>待补标准/计算</span><b class="warn">{{ pendingCount }}</b></div>
        <div><span>缺少数据集</span><b>{{ missingDatasets.length }}</b></div>
      </div>

      <el-alert v-if="isDirty" class="message-alert" type="info" :closable="false" title="输入条件已经修改；下方结果属于上一次生成。重新点击“生成综合参数”后才能保存为知识库。" />
      <el-alert v-if="pendingCount" class="message-alert" type="warning" :closable="false" title="有些标准数据仍是“待授权录入/待计算”。系统会明确标出来源和状态，不会用猜测值冒充正式工程参数。" />
      <el-alert v-if="missingDatasets.length" class="message-alert" type="error" :closable="false" :title="`缺少数据集：${missingDatasets.join('、')}`" />

      <div class="result-grid">
        <section class="panel result-panel">
          <div class="result-title"><div><span>③</span><b>零件几何参数</b></div><small>输出 · 左</small></div>
          <el-table :data="geometryResults" border>
            <el-table-column prop="name" label="参数" min-width="170" />
            <el-table-column label="取值" min-width="145"><template #default="scope"><b :class="isPending(scope.row) ? 'pending' : ''">{{ scope.row.value ?? '-' }}</b></template></el-table-column>
            <el-table-column prop="unit" label="单位" width="80" />
            <el-table-column prop="source" label="来源表" min-width="130" />
            <el-table-column label="状态" width="120"><template #default="scope"><el-tag size="small" effect="plain" :type="tagType(scope.row.status)">{{ scope.row.status }}</el-tag></template></el-table-column>
          </el-table>
        </section>

        <section class="panel result-panel">
          <div class="result-title"><div><span>④</span><b>装配 / 接口参数</b></div><small>输出 · 右</small></div>
          <el-table :data="assemblyResults" border>
            <el-table-column prop="name" label="参数" min-width="170" />
            <el-table-column label="取值" min-width="145"><template #default="scope"><b :class="isPending(scope.row) ? 'pending' : ''">{{ scope.row.value ?? '-' }}</b></template></el-table-column>
            <el-table-column prop="unit" label="单位" width="80" />
            <el-table-column prop="source" label="来源表" min-width="130" />
            <el-table-column label="状态" width="120"><template #default="scope"><el-tag size="small" effect="plain" :type="tagType(scope.row.status)">{{ scope.row.status }}</el-tag></template></el-table-column>
          </el-table>
        </section>
      </div>
    </template>

    <div v-else class="empty-panel"><el-empty description="填写设计条件后点击“生成综合参数”，系统会把分散在各知识表中的数据汇总到这里。" /></div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Operation } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import http from '../api/http.js'

const emit = defineEmits(['refresh-libraries'])
const router = useRouter()
const loading = ref(false)
const generating = ref(false)
const saving = ref(false)
const generated = ref(false)
const generatedSnapshot = ref(null)
const lastSaved = ref(null)
const datasets = ref([])
const detailCache = new Map()
const missingDatasets = ref([])
const geometryResults = ref([])
const assemblyResults = ref([])
const options = reactive({ nps: [], pressure: [], boreType: [], endConnection: [], ballMaterial: [], leakage: [] })
const defaults = {
  valve_structure:'固定球阀',
  nps:'NPS12',
  pressure_class:'CL600',
  bore_type:'全通径',
  end_connection:'RF法兰',
  body_material:'A105',
  ball_material_group:'碳钢/合金钢球',
  seat_material:'PEEK',
  design_pressure:'2',
  design_temperature:'-29~120',
  leakage_level:'',
  medium:'天然气'
}
const form = reactive({ ...defaults })

const allResults = computed(() => [...geometryResults.value, ...assemblyResults.value])
const pendingCount = computed(() => allResults.value.filter(isPending).length)
const readyCount = computed(() => allResults.value.length - pendingCount.value)
const isDirty = computed(() => generated.value && JSON.stringify(form) !== JSON.stringify(generatedSnapshot.value || {}))

function findDataset(name) { return datasets.value.find(x => x.name === name) }
async function getDetail(name, markMissing = true) {
  const ds = findDataset(name)
  if (!ds) {
    if (markMissing && !missingDatasets.value.includes(name)) missingDatasets.value.push(name)
    return null
  }
  if (detailCache.has(ds.id)) return detailCache.get(ds.id)
  const { data } = await http.get(`/datasets/${ds.id}`)
  detailCache.set(ds.id, data)
  return data
}
function field(detail, name) { return (detail?.fields || []).find(f => f.field_name === name || f.source_name === name) }
function value(detail, row, name) { const f = field(detail, name); return f ? row?.[f.field_code] : undefined }
function unit(detail, row, name, fallback='') {
  const f = field(detail, name)
  if (f?.unit) return f.unit
  const u = value(detail, row, '单位')
  return u && u !== '-' ? u : fallback
}

async function query(name, filters={}, pageSize=200, markMissing=true) {
  const detail = await getDetail(name, markMissing)
  if (!detail) return { detail:null, rows:[] }
  const mapped = {}
  Object.entries(filters).forEach(([name, val]) => { const f = field(detail, name); if (f && val !== '' && val != null) mapped[f.field_code] = val })
  const { data } = await http.post(`/datasets/${detail.id}/query`, { page:1, page_size:pageSize, search:'', filters:mapped, sort_by:null, sort_order:'asc' })
  return { detail, rows:data.rows || [] }
}

function inferStatus(v) { const t=String(v ?? ''); return !t || t==='-' || /待授权|待计算|待确认/.test(t) ? '待补齐' : '可用' }
function makeResult(name, v, u, source, status='') { return { name, value:v ?? '-', unit:u || '-', source, status:status || inferStatus(v) } }
function isPending(row) { return !row?.value || row.value==='-' || /待授权|待计算|待确认|待补齐|缺失/.test(`${row.value} ${row.status}`) }
function tagType(status) { if (/可用|已录入|通过|已保存/.test(status || '')) return 'success'; if (/待/.test(status || '')) return 'warning'; if (/缺失|错误/.test(status || '')) return 'danger'; return 'info' }

async function generate() {
  generating.value = true
  generated.value = false
  missingDatasets.value = []
  try {
    const [diameter,bore,face,flange,ball,wall] = await Promise.all([
      query('口径基础表', {'公称口径':form.nps}),
      query('通径表', {'公称口径':form.nps,'压力等级':form.pressure_class,'通径形式':form.bore_type}),
      query('结构长度表', {'公称口径':form.nps,'压力等级':form.pressure_class,'端部连接':form.end_connection}),
      query('法兰尺寸表', {'公称口径':form.nps,'压力等级':form.pressure_class,'端部连接':form.end_connection}),
      query('球体直径表', {'公称口径':form.nps,'压力等级':form.pressure_class,'球体材料组':form.ball_material_group}),
      query('阀体壁厚表', {'压力等级':form.pressure_class,'材料组':form.body_material})
    ])
    const dr=diameter.rows[0], br=bore.rows[0], fr=face.rows[0], fl=flange.rows[0], ba=ball.rows[0], wr=wall.rows[0]
    geometryResults.value = [
      makeResult('通道直径 D_BORE', value(bore.detail,br,'通道直径d'), unit(bore.detail,br,'通道直径d','mm'), '通径表', value(bore.detail,br,'数据状态')),
      makeResult('球体直径 D_BALL', value(ball.detail,ba,'球体直径S'), unit(ball.detail,ba,'球体直径S','mm'), '球体直径表', value(ball.detail,ba,'数据状态')),
      makeResult('阀体最小壁厚', value(wall.detail,wr,'最小壁厚'), unit(wall.detail,wr,'最小壁厚','mm'), '阀体壁厚表', value(wall.detail,wr,'数据状态')),
      makeResult('端法兰外径', value(flange.detail,fl,'法兰外径'), unit(flange.detail,fl,'法兰外径','mm'), '法兰尺寸表'),
      makeResult('端法兰厚度', value(flange.detail,fl,'法兰厚度'), unit(flange.detail,fl,'法兰厚度','mm'), '法兰尺寸表'),
      makeResult('螺栓中心圆', value(flange.detail,fl,'螺栓中心圆'), unit(flange.detail,fl,'螺栓中心圆','mm'), '法兰尺寸表'),
      makeResult('螺栓孔直径', value(flange.detail,fl,'螺栓孔直径'), unit(flange.detail,fl,'螺栓孔直径','mm'), '法兰尺寸表')
    ]
    assemblyResults.value = [
      makeResult('公称口径', form.nps, '-', '用户输入', '可用'),
      makeResult('DN', value(diameter.detail,dr,'DN'), '-', '口径基础表'),
      makeResult('压力等级', form.pressure_class, '-', '用户输入', '可用'),
      makeResult('结构长度 L_FACE_TO_FACE', value(face.detail,fr,'结构长度L'), unit(face.detail,fr,'结构长度L','mm'), '结构长度表', value(face.detail,fr,'数据状态')),
      makeResult('端部连接', form.end_connection, '-', '用户输入', '可用'),
      makeResult('螺栓规格', value(flange.detail,fl,'螺栓规格'), '-', '法兰尺寸表'),
      makeResult('螺栓数量', value(flange.detail,fl,'螺栓数量'), '个', '法兰尺寸表'),
      makeResult('设计压力', form.design_pressure, 'MPa', '用户输入', '可用'),
      makeResult('设计温度', form.design_temperature, '℃', '用户输入', '可用'),
      makeResult('泄漏等级', form.leakage_level, '-', '用户输入', form.leakage_level ? '可用' : '待补齐'),
      makeResult('介质', form.medium, '-', '用户输入', '可用')
    ]
    generatedSnapshot.value = JSON.parse(JSON.stringify(form))
    generated.value = true
    lastSaved.value = null
  } catch(e) {
    ElMessage.error(`综合参数生成失败：${e.message}`)
  } finally {
    generating.value = false
  }
}

async function saveToKnowledgeBase() {
  if (!generated.value) {
    ElMessage.warning('请先生成综合参数')
    return
  }
  if (isDirty.value) {
    ElMessage.warning('输入条件已经变化，请重新生成后再保存')
    return
  }
  saving.value = true
  try {
    const { data } = await http.post('/workbench/save', {
      input_snapshot: generatedSnapshot.value,
      geometry_results: geometryResults.value,
      assembly_results: assemblyResults.value
    })
    lastSaved.value = data
    emit('refresh-libraries')
    ElMessage.success(`已保存到设计成果库：${data.dataset_name}`)
  } catch (e) {
    ElMessage.error(`保存失败：${e.message}`)
  } finally {
    saving.value = false
  }
}

async function loadValues(dsName, fieldName) {
  const x=await query(dsName,{},200,false)
  return [...new Set(x.rows.map(r=>value(x.detail,r,fieldName)).filter(Boolean).map(String))]
}

async function loadLeakageValues() {
  const x = await query('泄漏等级表', {}, 200, false)
  if (!x.detail) return []
  const fields = x.detail.fields || []
  const target = fields.find(f => /(泄漏|泄露).*(等级|级别|rate|class)/i.test(`${f.field_name} ${f.source_name}`))
    || fields.find(f => /(等级|级别|rate|class)/i.test(`${f.field_name} ${f.source_name}`))
  if (!target) return []
  return [...new Set(x.rows.map(r => r[target.field_code]).filter(Boolean).map(String))]
}

async function loadOptions() {
  const [a,b,c,d,e,f] = await Promise.all([
    loadValues('口径基础表','公称口径'),
    loadValues('压力等级表','压力等级'),
    loadValues('通径表','通径形式'),
    loadValues('结构长度表','端部连接'),
    loadValues('球体直径表','球体材料组'),
    loadLeakageValues()
  ])
  options.nps=a
  options.pressure=b
  options.boreType=c
  options.endConnection=d
  options.ballMaterial=e
  options.leakage=f
  if (!form.leakage_level && f.length) form.leakage_level = f[0]
}

function resetForm() { Object.assign(form, defaults); if (options.leakage.length) form.leakage_level = options.leakage[0] }
function openSavedDataset() { if (lastSaved.value?.dataset_id) router.push({ name:'dataset', params:{ id:lastSaved.value.dataset_id } }) }
function openResultLibrary() { if (lastSaved.value?.knowledge_base_id) router.push({ name:'library', params:{ id:lastSaved.value.knowledge_base_id } }) }

onMounted(async()=>{
  loading.value=true
  try {
    const {data}=await http.get('/datasets')
    datasets.value=data||[]
    await loadOptions()
  } catch(e) {
    ElMessage.error(e.message)
  } finally {
    loading.value=false
  }
})
</script>

<style scoped>
.workbench-page{padding-bottom:30px}.workbench-hero{background:#fff;border:1px solid #e6ebf2;border-radius:12px;padding:22px 24px;display:flex;justify-content:space-between;gap:30px}.workbench-hero h1{margin:4px 0 7px;font-size:24px;color:#1f2d3d}.workbench-hero p{margin:0;color:#7a899d;font-size:13px;line-height:1.7}.hero-count{min-width:130px;background:#f7f9fc;border-radius:10px;padding:14px 16px;text-align:right}.hero-count span{display:block;font-size:11px;color:#8896a9}.hero-count b{display:block;margin-top:4px;font-size:24px}.workbench-top{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(300px,.8fr);gap:14px;margin-top:14px}.panel{background:#fff;border:1px solid #e6ebf2;border-radius:11px;box-shadow:0 3px 12px rgba(31,50,75,.03)}.input-panel,.snapshot-panel{padding:18px 20px}.panel-title{display:flex;justify-content:space-between;gap:15px;margin-bottom:16px}.panel-title b{display:block;color:#26364b}.panel-title span{display:block;margin-top:5px;color:#8896a9;font-size:11px}.input-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0 14px}.input-grid :deep(.el-form-item){margin-bottom:14px}.dirty-tip{margin:0 0 10px;padding:9px 12px;border-radius:7px;background:#fff8e8;color:#a66a11;font-size:11px}.action-row{display:flex;justify-content:flex-end;gap:8px;padding-top:14px;border-top:1px solid #edf1f5}.snapshot-list{display:grid;gap:10px}.snapshot-list div{padding:11px 12px;background:#f7f9fc;border-radius:8px}.snapshot-list span{display:block;font-size:11px;color:#8795a8}.snapshot-list b{display:block;margin-top:5px;font-size:13px;color:#33465e}.saved-card{margin-top:14px;padding:13px 14px;border:1px solid #cae9d7;border-radius:9px;background:#f5fbf7}.saved-head{display:flex;align-items:center;justify-content:space-between;gap:8px}.saved-head span{font-size:11px;color:#6c7e72}.saved-card>b{display:block;margin-top:8px;font-size:13px;color:#294b37;word-break:break-all}.saved-card>small{display:block;margin-top:5px;color:#799083;line-height:1.5}.saved-actions{display:flex;gap:7px;margin-top:10px}.summary-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:14px}.summary-row>div{background:#fff;border:1px solid #e6ebf2;border-radius:10px;padding:15px 18px}.summary-row span{display:block;color:#7b8ba0;font-size:11px}.summary-row b{display:block;margin-top:5px;font-size:21px}.summary-row .ok{color:#289b63}.summary-row .warn{color:#d88a18}.message-alert{margin-top:14px}.result-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}.result-panel{padding:0 16px 14px;overflow:hidden}.result-title{min-height:58px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #edf1f5;margin-bottom:14px}.result-title>div{display:flex;align-items:center;gap:9px}.result-title>div span{width:27px;height:27px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;background:#eaf2ff;color:#1262df;font-weight:700}.result-title small{color:#8b99aa}.pending{color:#d98216}.empty-panel{margin-top:14px;background:#fff;border:1px solid #e6ebf2;border-radius:11px;padding:40px}@media(max-width:1450px){.workbench-top,.result-grid{grid-template-columns:1fr}.input-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:900px){.input-grid{grid-template-columns:1fr}.action-row{flex-wrap:wrap}.summary-row{grid-template-columns:repeat(2,1fr)}}
</style>