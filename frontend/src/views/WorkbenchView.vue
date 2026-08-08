<template>
  <div class="workbench-page" v-loading="loading">
    <div class="workbench-hero">
      <div>
        <div class="eyebrow">VALVE DESIGN ENGINE</div>
        <h1>固定球阀参数工作台</h1>
        <p>左侧给设计要求；右侧一次求解，直接输出计算过程、零件参数、装配元参数和 SolidWorks 映射。</p>
      </div>
      <div class="hero-actions">
        <el-tag effect="plain">{{ datasets.length }} 个知识数据集</el-tag>
        <el-button size="small" @click="resetForm">恢复示例</el-button>
      </div>
    </div>

    <div class="workspace-grid">
      <section class="panel input-panel">
        <div class="panel-title">
          <div><b>① 设计输入</b><span>用户输入设计边界，系统负责查表 + 公式计算。</span></div>
          <el-tag type="primary" effect="light">L1 驱动参数</el-tag>
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
          <el-form-item label="阀体材料"><el-input v-model="form.body_material" placeholder="例如 A105 / WCB" /></el-form-item>
          <el-form-item label="球体材料组">
            <el-select v-model="form.ball_material_group" filterable allow-create style="width:100%"><el-option v-for="x in options.ballMaterial" :key="x" :label="x" :value="x" /></el-select>
          </el-form-item>
          <el-form-item label="阀座材料"><el-input v-model="form.seat_material" placeholder="例如 PEEK" /></el-form-item>
          <el-form-item label="设计压力"><el-input v-model="form.design_pressure"><template #append>MPa</template></el-input></el-form-item>
          <el-form-item label="设计温度"><el-input v-model="form.design_temperature"><template #append>℃</template></el-input></el-form-item>
          <el-form-item label="泄漏等级">
            <el-select v-model="form.leakage_level" filterable allow-create clearable placeholder="请选择或输入" style="width:100%"><el-option v-for="x in options.leakage" :key="x" :label="x" :value="x" /></el-select>
          </el-form-item>
          <el-form-item label="介质"><el-input v-model="form.medium" placeholder="例如 天然气" /></el-form-item>
        </el-form>

        <el-collapse class="engineering-collapse">
          <el-collapse-item name="engineering">
            <template #title><span class="collapse-title">企业计算条件 <em>（当前为演示/待企业确认，可在公式库正式化）</em></span></template>
            <div class="engineering-grid">
              <el-form-item label="座角"><el-input v-model="engineering.seat_angle"><template #append>°</template></el-input></el-form-item>
              <el-form-item label="操作扭矩"><el-input v-model="engineering.operating_torque"><template #append>N·m</template></el-input></el-form-item>
              <el-form-item label="阀杆许用剪应力"><el-input v-model="engineering.allowable_shear"><template #append>MPa</template></el-input></el-form-item>
              <el-form-item label="座轴向预压"><el-input v-model="engineering.seat_preload"><template #append>mm</template></el-input></el-form-item>
              <el-form-item label="阀杆啮合系数 k"><el-input v-model="engineering.stem_engage_factor" /></el-form-item>
              <el-form-item label="体螺栓节圆（可选）"><el-input v-model="engineering.body_bolt_circle" placeholder="未建立规则时留空"><template #append>mm</template></el-input></el-form-item>
            </div>
          </el-collapse-item>
        </el-collapse>

        <div v-if="isDirty" class="dirty-tip">输入条件已经变化，下方仍是上一次计算结果。请重新生成后再保存。</div>
        <div class="action-row">
          <el-button type="success" plain :loading="saving" :disabled="!generated || isDirty" @click="saveToKnowledgeBase">保存设计成果</el-button>
          <el-button type="primary" size="large" :loading="generating" @click="generate"><el-icon><Operation /></el-icon>生成完整参数</el-button>
        </div>

        <div class="input-summary">
          <span>{{ form.nps }}</span><strong>{{ form.pressure_class }}</strong><span>{{ form.body_material }}</span><span>{{ form.bore_type }}</span>
        </div>
      </section>

      <section class="panel output-panel">
        <div class="output-head">
          <div>
            <div class="eyebrow">ONE PASS RESULT</div>
            <h2>② {{ resultTitle }}</h2>
            <p>同一次求解：标准查表 + 企业公式 → 零件参数与装配元参数同步产出。</p>
          </div>
          <div class="output-status">
            <el-tag v-if="generated" type="success" effect="dark">已生成</el-tag>
            <el-tag v-else type="info" effect="plain">等待计算</el-tag>
            <span v-if="generated">{{ readyCount }} 可用 / {{ pendingCount }} 待补</span>
          </div>
        </div>

        <template v-if="generated">
          <el-tabs v-model="activeTab" class="result-tabs">
            <el-tab-pane label="计算过程" name="process">
              <div class="table-toolbar">
                <div><b>计算链路</b><span>每一行说明：为什么算、算出什么、写到哪里。</span></div>
                <el-input v-model="resultKeyword" clearable placeholder="筛选步骤、参数、来源" style="width:220px" />
              </div>
              <el-table :data="filteredCalculationRows" border stripe size="small" class="process-table" :row-class-name="rowClassName">
                <el-table-column prop="step" label="步骤" width="86" fixed />
                <el-table-column label="计算 / 查表" min-width="220">
                  <template #default="scope"><b class="calc-title">{{ scope.row.title }}</b><div class="calc-detail">{{ scope.row.calculation }}</div></template>
                </el-table-column>
                <el-table-column label="零件参数 → .sldprt" min-width="270">
                  <template #default="scope"><div v-if="scope.row.part_output" class="output-cell"><b>{{ scope.row.part_output }}</b><small>{{ scope.row.part_target || '—' }}</small></div><span v-else class="muted">— 无零件产物</span></template>
                </el-table-column>
                <el-table-column label="装配元参数 → .sldasm" min-width="285">
                  <template #default="scope"><div v-if="scope.row.assembly_output" class="output-cell"><b>{{ scope.row.assembly_output }}</b><small>{{ scope.row.assembly_target || '—' }}</small></div><span v-else class="muted">— 无独立装配产物</span></template>
                </el-table-column>
                <el-table-column label="来源" width="118" fixed="right">
                  <template #default="scope"><el-tag size="small" effect="light" :type="sourceType(scope.row.source_type)">{{ scope.row.source }}</el-tag><small class="status-text">{{ scope.row.status }}</small></template>
                </el-table-column>
              </el-table>
            </el-tab-pane>

            <el-tab-pane :label="`零件参数 ${geometryResults.length}`" name="part">
              <el-table :data="geometryResults" border stripe size="small" class="compact-table">
                <el-table-column prop="name" label="参数 / 变量" min-width="190" />
                <el-table-column label="取值" min-width="120"><template #default="scope"><b :class="isPending(scope.row) ? 'pending' : 'ready-value'">{{ scope.row.value ?? '-' }}</b></template></el-table-column>
                <el-table-column prop="unit" label="单位" width="72" />
                <el-table-column prop="source" label="来源" min-width="150" />
                <el-table-column label="状态" width="100"><template #default="scope"><el-tag size="small" :type="tagType(scope.row.status)">{{ scope.row.status }}</el-tag></template></el-table-column>
              </el-table>
            </el-tab-pane>

            <el-tab-pane :label="`装配参数 ${assemblyResults.length}`" name="assembly">
              <el-table :data="assemblyResults" border stripe size="small" class="compact-table">
                <el-table-column prop="name" label="参数 / 变量" min-width="190" />
                <el-table-column label="取值" min-width="120"><template #default="scope"><b :class="isPending(scope.row) ? 'pending' : 'ready-value'">{{ scope.row.value ?? '-' }}</b></template></el-table-column>
                <el-table-column prop="unit" label="单位" width="72" />
                <el-table-column prop="source" label="来源" min-width="150" />
                <el-table-column label="状态" width="100"><template #default="scope"><el-tag size="small" :type="tagType(scope.row.status)">{{ scope.row.status }}</el-tag></template></el-table-column>
              </el-table>
            </el-tab-pane>

            <el-tab-pane :label="`SolidWorks 映射 ${swMappings.length}`" name="sw">
              <el-table :data="swMappings" border stripe size="small" class="compact-table">
                <el-table-column prop="parameter" label="系统参数" min-width="150" />
                <el-table-column prop="value" label="值" width="105" />
                <el-table-column prop="unit" label="单位" width="70" />
                <el-table-column prop="target_file" label="目标文件" min-width="170" />
                <el-table-column prop="variable" label="SW变量" min-width="140" />
                <el-table-column prop="feature" label="Feature / Mate" min-width="220" />
                <el-table-column label="状态" width="95"><template #default="scope"><el-tag size="small" :type="tagType(scope.row.status)">{{ scope.row.status }}</el-tag></template></el-table-column>
              </el-table>
            </el-tab-pane>
          </el-tabs>

          <div class="result-footer">
            <span>数据来源：标准库 / 企业参数表 / 企业计算条件；待补项不会冒充正式工程值。</span>
            <div v-if="lastSaved" class="saved-inline"><el-tag type="success">已保存</el-tag><el-button link type="primary" @click="openSavedDataset">查看本次历史</el-button></div>
          </div>
        </template>

        <div v-else class="result-empty">
          <el-empty description="左侧确认设计条件后，点击“生成完整参数”">
            <template #description><p>生成后这里直接显示你示例中的 10 步计算表，而不是只给几个汇总数字。</p></template>
          </el-empty>
        </div>
      </section>
    </div>

    <el-alert v-if="generated && missingDatasets.length" class="message-alert" type="warning" :closable="false" :title="`缺少/未匹配数据集：${missingDatasets.join('、')}。对应步骤已标为待补，不影响其它已知参数显示。`" />
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
const activeTab = ref('process')
const resultKeyword = ref('')
const datasets = ref([])
const detailCache = new Map()
const missingDatasets = ref([])
const geometryResults = ref([])
const assemblyResults = ref([])
const calculationRows = ref([])
const swMappings = ref([])
const options = reactive({ nps: [], pressure: [], boreType: [], endConnection: [], ballMaterial: [], leakage: [] })

const defaults = {
  valve_structure:'固定球阀', nps:'NPS12', pressure_class:'CL600', bore_type:'全通径', end_connection:'RF法兰',
  body_material:'A105', ball_material_group:'碳钢/合金钢球', seat_material:'PEEK', design_pressure:'2',
  design_temperature:'-29~120', leakage_level:'', medium:'天然气'
}
const engineeringDefaults = { seat_angle:'45', operating_torque:'1500', allowable_shear:'70', seat_preload:'0.8', stem_engage_factor:'1.25', body_bolt_circle:'' }
const form = reactive({ ...defaults })
const engineering = reactive({ ...engineeringDefaults })

const allResults = computed(() => [...geometryResults.value, ...assemblyResults.value])
const pendingCount = computed(() => allResults.value.filter(isPending).length)
const readyCount = computed(() => allResults.value.length - pendingCount.value)
const currentSnapshot = computed(() => ({ ...form, engineering: { ...engineering } }))
const isDirty = computed(() => generated.value && JSON.stringify(currentSnapshot.value) !== JSON.stringify(generatedSnapshot.value || {}))
const resultTitle = computed(() => `${form.nps || '-'} ${form.pressure_class || '-'} ${form.body_material || '-'} ${form.valve_structure || '阀门'}`)
const filteredCalculationRows = computed(() => {
  const k = resultKeyword.value.trim().toLowerCase()
  if (!k) return calculationRows.value
  return calculationRows.value.filter(r => `${r.step} ${r.title} ${r.calculation} ${r.part_output} ${r.assembly_output} ${r.source}`.toLowerCase().includes(k))
})

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
function unit(detail, row, name, fallback='') { const f=field(detail,name); if(f?.unit)return f.unit; const u=value(detail,row,'单位'); return u&&u!=='-'?u:fallback }
async function query(name, filters={}, pageSize=200, markMissing=true) {
  const detail = await getDetail(name, markMissing)
  if (!detail) return { detail:null, rows:[] }
  const mapped = {}
  Object.entries(filters).forEach(([fieldName, val]) => { const f=field(detail,fieldName); if(f && val!=='' && val!=null) mapped[f.field_code]=val })
  const { data } = await http.post(`/datasets/${detail.id}/query`, { page:1, page_size:pageSize, search:'', filters:mapped, sort_by:null, sort_order:'asc' })
  return { detail, rows:data.rows || [] }
}

function numeric(v) {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  const text=String(v ?? '').replace(/,/g,'')
  if (/待|缺失|无数据|未录入/.test(text)) return null
  const m=text.match(/-?\d+(?:\.\d+)?/)
  return m ? Number(m[0]) : null
}
function round(v, digits=1) { if (v == null || !Number.isFinite(v)) return null; const p=10**digits; return Math.round(v*p)/p }
function display(v,u='') { return v==null || v==='' || v==='-' ? '待补齐' : `${v}${u && u!=='-' ? ` ${u}` : ''}` }
function inferStatus(v) { const t=String(v ?? ''); return !t || t==='-' || /待授权|待计算|待确认|待补齐|缺失/.test(t) ? '待补齐' : '可用' }
function makeResult(name,v,u,source,status='') { return { name, value:v ?? '-', unit:u || '-', source, status:status || inferStatus(v) } }
function isPending(row) { return !row?.value || row.value==='-' || /待授权|待计算|待确认|待补齐|缺失/.test(`${row.value} ${row.status}`) }
function tagType(status) { if(/可用|已录入|通过|已保存/.test(status||''))return'success'; if(/待/.test(status||''))return'warning'; if(/缺失|错误/.test(status||''))return'danger'; return'info' }
function sourceType(type){ if(type==='standard')return'success'; if(type==='enterprise')return'warning'; if(type==='calc')return'primary'; return'info' }
function rowClassName({row}) { return /待/.test(row.status || '') ? 'pending-row' : '' }
function calcRow(step,title,calculation,partOutput,partTarget,assemblyOutput,assemblyTarget,source,sourceTypeName,status){
  return { step, title, calculation, part_output:partOutput, part_target:partTarget, assembly_output:assemblyOutput, assembly_target:assemblyTarget, source, source_type:sourceTypeName, status }
}

async function generate() {
  generating.value=true; generated.value=false; missingDatasets.value=[]; activeTab.value='process'
  try {
    const [diameter,bore,face,flange,ball,wall] = await Promise.all([
      query('口径基础表',{'公称口径':form.nps}),
      query('通径表',{'公称口径':form.nps,'压力等级':form.pressure_class,'通径形式':form.bore_type}),
      query('结构长度表',{'公称口径':form.nps,'压力等级':form.pressure_class,'端部连接':form.end_connection}),
      query('法兰尺寸表',{'公称口径':form.nps,'压力等级':form.pressure_class,'端部连接':form.end_connection}),
      query('球体直径表',{'公称口径':form.nps,'压力等级':form.pressure_class,'球体材料组':form.ball_material_group}),
      query('阀体壁厚表',{'压力等级':form.pressure_class,'材料组':form.body_material})
    ])
    const dr=diameter.rows[0], br=bore.rows[0], fr=face.rows[0], fl=flange.rows[0], ba=ball.rows[0], wr=wall.rows[0]

    const boreRaw=value(bore.detail,br,'通道直径d'); const boreMm=numeric(boreRaw)
    const f2fRaw=value(face.detail,fr,'结构长度L'); const f2fMm=numeric(f2fRaw)
    const ballRaw=value(ball.detail,ba,'球体直径S'); let ballMm=numeric(ballRaw); let ballSource='球体直径表'; let ballSourceType='standard'; let ballCalc='按 NPS / Class / 球体材料组查球体直径表'
    const seatAngle=numeric(engineering.seat_angle)
    if(ballMm==null && boreMm!=null && seatAngle!=null && seatAngle>0 && seatAngle<90){ ballMm=round(boreMm/Math.sin(seatAngle*Math.PI/180),1); ballSource='企业公式示例'; ballSourceType='enterprise'; ballCalc=`Db = d_bore / sin(${seatAngle}°)` }
    const torque=numeric(engineering.operating_torque), tau=numeric(engineering.allowable_shear)
    const stemMm=torque&&tau ? round(Math.cbrt((16*torque*1000)/(Math.PI*tau)),1) : null
    const splitMm=f2fMm!=null ? round(f2fMm/2,1) : null
    const preloadMm=numeric(engineering.seat_preload)
    const engageFactor=numeric(engineering.stem_engage_factor)
    const engageMm=stemMm!=null&&engageFactor!=null ? round(stemMm*engageFactor,1) : null
    const boltCircleMm=numeric(engineering.body_bolt_circle)

    const flangeOd=value(flange.detail,fl,'法兰外径'), flangePcd=value(flange.detail,fl,'螺栓中心圆'), flangeThk=value(flange.detail,fl,'法兰厚度'), flangeHole=value(flange.detail,fl,'螺栓孔直径'), flangeBolt=value(flange.detail,fl,'螺栓规格'), flangeCount=value(flange.detail,fl,'螺栓数量')
    const wallRaw=value(wall.detail,wr,'最小壁厚')

    geometryResults.value=[
      makeResult('D_BORE · 通道直径',boreRaw,unit(bore.detail,br,'通道直径d','mm'),'通径表',value(bore.detail,br,'数据状态')),
      makeResult('D_BALL · 球体直径',ballMm,'mm',ballSource,ballMm==null?'待补齐':'可用'),
      makeResult('D_STEM · 阀杆直径',stemMm,'mm','企业扭矩/剪应力公式',stemMm==null?'待补齐':'企业计算'),
      makeResult('T_WALL · 阀体最小壁厚',wallRaw,unit(wall.detail,wr,'最小壁厚','mm'),'阀体壁厚表',value(wall.detail,wr,'数据状态')),
      makeResult('FLANGE_OD · 法兰外径',flangeOd,unit(flange.detail,fl,'法兰外径','mm'),'法兰尺寸表'),
      makeResult('FLANGE_PCD · 螺栓中心圆',flangePcd,unit(flange.detail,fl,'螺栓中心圆','mm'),'法兰尺寸表'),
      makeResult('FLANGE_T · 法兰厚度',flangeThk,unit(flange.detail,fl,'法兰厚度','mm'),'法兰尺寸表'),
      makeResult('FLANGE_HOLE · 螺栓孔直径',flangeHole,unit(flange.detail,fl,'螺栓孔直径','mm'),'法兰尺寸表')
    ]

    assemblyResults.value=[
      makeResult('F2F · 结构长度',f2fRaw,unit(face.detail,fr,'结构长度L','mm'),'结构长度表',value(face.detail,fr,'数据状态')),
      makeResult('BODY_SPLIT_POS · 体分界面',splitMm,'mm','F2F / 2',splitMm==null?'待补齐':'计算'),
      makeResult('SEAT_PRELOAD · 座轴向预压',preloadMm,'mm','企业计算条件',preloadMm==null?'待企业公式库':'企业示例'),
      makeResult('STEM_ENGAGE · 阀杆啮合深',engageMm,'mm',`k × D_STEM (k=${engineering.stem_engage_factor})`,engageMm==null?'待企业公式库':'企业计算'),
      makeResult('BODY_BOLT_CIRCLE · 体螺栓节圆',boltCircleMm,'mm','企业螺栓规则',boltCircleMm==null?'待企业公式库':'企业输入'),
      makeResult('端法兰螺栓规格',flangeBolt,'-','法兰尺寸表'),
      makeResult('端法兰螺栓数量',flangeCount,'个','法兰尺寸表'),
      makeResult('DN',value(diameter.detail,dr,'DN'),'-','口径基础表')
    ]

    calculationRows.value=[
      calcRow('1. 孔径','通道直径',`${form.nps} + ${form.pressure_class} + ${form.bore_type} → 查“通径表”`,boreMm!=null?`d_bore = ${boreMm} mm`:'待标准数据','valve_body.sldprt · 流道切除 Feature · 直径',boreMm!=null?`全局变量 d_bore = ${boreMm} mm`:'待标准数据','.sldasm · 流道轴 / 球-座同心 mate 引用','通径表','standard',boreMm!=null?'可用':'待补齐'),
      calcRow('2. 法兰','端法兰尺寸',`${form.nps} + ${form.pressure_class} + ${form.end_connection} → 查“法兰尺寸表”`,flangeOd?`OD ${display(flangeOd,'mm')} / PCD ${display(flangePcd,'mm')} / ${flangeCount||'-'}×Φ${flangeHole||'-'} / 厚 ${flangeThk||'-'} mm`:'待标准数据','valve_body.sldprt · 两端法兰 Feature','', '', '法兰尺寸表','standard',flangeOd?'可用':'待补齐'),
      calcRow('3. F2F','结构长度',`${form.nps} + ${form.pressure_class} + ${form.end_connection} → 查“结构长度表”`,'','',f2fMm!=null?`F2F = ${f2fMm} mm`:'待标准数据','.sldasm · 全局变量 f2f；驱动总长 / 分界面','结构长度表','standard',f2fMm!=null?'可用':'待补齐'),
      calcRow('4. 壁厚','阀体最小壁厚',`${form.pressure_class} + ${form.body_material} → 查“阀体壁厚表”`,numeric(wallRaw)!=null?`t_wall = ${numeric(wallRaw)} mm`:'待标准/材料数据','valve_body.sldprt · 阀体承压壁厚','','','阀体壁厚表','standard',numeric(wallRaw)!=null?'可用':'待补齐'),
      calcRow('5. 球径','球体直径',ballCalc,ballMm!=null?`D_BALL = ${ballMm} mm`:'待球体数据','ball.sldprt · 球体旋转 Feature · 直径',ballMm!=null?`全局变量 ball_d = ${ballMm} mm`:'待球体数据','.sldasm · 座位置 / 相切关系引用',ballSource,ballSourceType,ballMm!=null?(ballSourceType==='enterprise'?'企业计算':'可用'):'待补齐'),
      calcRow('6. 阀杆径','阀杆直径',torque&&tau?`d = (16T / πτ)^(1/3)，T=${torque} N·m，τ=${tau} MPa`:'缺少扭矩或许用剪应力',stemMm!=null?`D_STEM = ${stemMm} mm`:'待企业计算','stem.sldprt · 阀杆旋转 Feature · 直径',stemMm!=null?`全局变量 stem_d = ${stemMm} mm`:'待企业计算','.sldasm · 杆-球传扭 / 填料函同心引用','企业公式','enterprise',stemMm!=null?'企业计算':'待补齐'),
      calcRow('7. 体分界面','球居中 / 阀体分界',f2fMm!=null?`split = f2f / 2 = ${f2fMm} / 2`:'需要先得到 F2F',splitMm!=null?'上下阀体建模基准':'待 F2F','valve_body_top/bottom.sldprt · 基准面',splitMm!=null?`split = ${splitMm} mm`:'待 F2F','.sldasm · body_split_pos / 重合 mate','计算·几何','calc',splitMm!=null?'计算':'待补齐'),
      calcRow('8. 体螺栓节圆','阀体连接螺栓',boltCircleMm!=null?'使用企业已确认节圆值':'需要“压力 + 密封径 + 安全系数 + 螺栓规则”完整公式库',boltCircleMm!=null?`体法兰孔阵列 PCD = ${boltCircleMm} mm`:'待企业公式库','阀体连接法兰孔阵列',boltCircleMm!=null?`body_bolt_circle = ${boltCircleMm} mm`:'待企业公式库','.sldasm · 上/下阀体孔位同心','企业公式','enterprise',boltCircleMm!=null?'企业输入':'待企业公式库'),
      calcRow('9. 座预压','阀座轴向预压',preloadMm!=null?`当前企业示例值 ${preloadMm} mm；正式应由密封比压/刚度规则求解`:'需要密封比压、接触宽和刚度规则',preloadMm!=null?'阀座接触区按预压联动':'待企业公式库','seat.sldprt · 接触面/球面半径',preloadMm!=null?`seat_preload = ${preloadMm} mm`:'待企业公式库','.sldasm · 左右阀座距离 mate','企业示例','enterprise',preloadMm!=null?'企业示例·待确认':'待企业公式库'),
      calcRow('10. 啮合深','阀杆-球体啮合',stemMm!=null&&engageFactor!=null?`stem_engage = k × D_STEM = ${engageFactor} × ${stemMm}`:'需要阀杆径与企业啮合系数',engageMm!=null?`阀杆方头/花键长度 = ${engageMm} mm`:'待企业公式库','stem.sldprt · 下端传扭 Feature',engageMm!=null?`stem_engage = ${engageMm} mm`:'待企业公式库','.sldasm · 杆-球距离 / 啮合 mate','企业公式','enterprise',engageMm!=null?'企业计算·待确认':'待企业公式库')
    ]

    swMappings.value=[
      {parameter:'D_BORE',value:boreMm??'-',unit:'mm',target_file:'valve_body.sldprt',variable:'D_BORE',feature:'流道切除 Feature · 直径',status:boreMm!=null?'可用':'待补齐'},
      {parameter:'D_BALL',value:ballMm??'-',unit:'mm',target_file:'ball.sldprt',variable:'D_BALL',feature:'球体旋转 Feature · 直径',status:ballMm!=null?'可用':'待补齐'},
      {parameter:'D_STEM',value:stemMm??'-',unit:'mm',target_file:'stem.sldprt',variable:'D_STEM',feature:'阀杆旋转 Feature · 直径',status:stemMm!=null?'企业计算':'待补齐'},
      {parameter:'T_WALL',value:numeric(wallRaw)??'-',unit:'mm',target_file:'valve_body.sldprt',variable:'T_WALL',feature:'阀体承压壁厚',status:numeric(wallRaw)!=null?'可用':'待补齐'},
      {parameter:'F2F',value:f2fMm??'-',unit:'mm',target_file:'assembly.sldasm',variable:'F2F',feature:'两端连接面总长 / 装配基准',status:f2fMm!=null?'可用':'待补齐'},
      {parameter:'BODY_SPLIT_POS',value:splitMm??'-',unit:'mm',target_file:'assembly.sldasm',variable:'BODY_SPLIT_POS',feature:'上/下阀体分界基准 mate',status:splitMm!=null?'计算':'待补齐'},
      {parameter:'SEAT_PRELOAD',value:preloadMm??'-',unit:'mm',target_file:'assembly.sldasm',variable:'SEAT_PRELOAD',feature:'左右阀座轴向距离 mate',status:preloadMm!=null?'企业示例·待确认':'待补齐'},
      {parameter:'STEM_ENGAGE',value:engageMm??'-',unit:'mm',target_file:'assembly.sldasm',variable:'STEM_ENGAGE',feature:'阀杆-球体啮合距离',status:engageMm!=null?'企业计算·待确认':'待补齐'}
    ]

    generatedSnapshot.value=JSON.parse(JSON.stringify(currentSnapshot.value)); generated.value=true; lastSaved.value=null
  } catch(e) { ElMessage.error(`参数生成失败：${e.message}`) } finally { generating.value=false }
}

async function saveToKnowledgeBase() {
  if(!generated.value){ElMessage.warning('请先生成完整参数');return}
  if(isDirty.value){ElMessage.warning('输入条件已经变化，请重新生成后再保存');return}
  saving.value=true
  try{
    const {data}=await http.post('/workbench/save',{input_snapshot:generatedSnapshot.value,geometry_results:geometryResults.value,assembly_results:assemblyResults.value})
    lastSaved.value=data; emit('refresh-libraries'); ElMessage.success(`已保存到设计成果库：${data.dataset_name}`)
  }catch(e){ElMessage.error(`保存失败：${e.message}`)}finally{saving.value=false}
}

async function loadValues(dsName,fieldName){const x=await query(dsName,{},200,false);return[...new Set(x.rows.map(r=>value(x.detail,r,fieldName)).filter(Boolean).map(String))]}
async function loadLeakageValues(){const x=await query('泄漏等级表',{},200,false);if(!x.detail)return[];const preferred=['用户输入示例','泄漏等级','泄露等级','等级/叫法','等级','级别'];let target=preferred.map(name=>field(x.detail,name)).find(Boolean);if(!target)target=(x.detail.fields||[]).find(f=>/(泄漏|泄露|等级|级别|rate|class)/i.test(`${f.field_name} ${f.source_name}`));if(!target)return[];return[...new Set(x.rows.map(r=>r[target.field_code]).filter(Boolean).map(String))]}
async function loadOptions(){const[a,b,c,d,e,f]=await Promise.all([loadValues('口径基础表','公称口径'),loadValues('压力等级表','压力等级'),loadValues('通径表','通径形式'),loadValues('结构长度表','端部连接'),loadValues('球体直径表','球体材料组'),loadLeakageValues()]);options.nps=a;options.pressure=b;options.boreType=c;options.endConnection=d;options.ballMaterial=e;options.leakage=f}
function resetForm(){Object.assign(form,defaults);Object.assign(engineering,engineeringDefaults)}
function openSavedDataset(){if(lastSaved.value?.dataset_id)router.push({name:'designResultDetail',params:{id:lastSaved.value.dataset_id}}).catch(()=>router.push({name:'dataset',params:{id:lastSaved.value.dataset_id}}))}

onMounted(async()=>{loading.value=true;try{const{data}=await http.get('/datasets');datasets.value=data||[];await loadOptions()}catch(e){ElMessage.error(e.message)}finally{loading.value=false}})
</script>

<style scoped>
.workbench-page{padding-bottom:24px}.workbench-hero{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;gap:18px}.eyebrow{font-size:10px;letter-spacing:.1em;color:#1262df;font-weight:700}.workbench-hero h1{margin:2px 0 3px;font-size:21px;color:#162a43}.workbench-hero p{margin:0;color:#7b899b;font-size:11px}.hero-actions{display:flex;gap:8px;align-items:center}.workspace-grid{display:grid;grid-template-columns:minmax(340px,.72fr) minmax(680px,1.55fr);gap:12px;margin-top:12px;align-items:start}.panel{background:#fff;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 2px 10px rgba(29,47,71,.035)}.input-panel{padding:14px}.panel-title{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:10px}.panel-title b{display:block;font-size:14px;color:#24384f}.panel-title span{display:block;margin-top:2px;color:#8996a7;font-size:10px}.input-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 9px}.input-grid :deep(.el-form-item),.engineering-grid :deep(.el-form-item){margin-bottom:9px}.input-grid :deep(.el-form-item__label),.engineering-grid :deep(.el-form-item__label){height:23px;line-height:23px;font-size:11px;color:#536579}.input-grid :deep(.el-input__wrapper),.input-grid :deep(.el-select__wrapper),.engineering-grid :deep(.el-input__wrapper){min-height:31px}.engineering-collapse{border-top:1px solid #edf1f5;border-bottom:0}.engineering-collapse :deep(.el-collapse-item__header){height:34px;font-size:11px}.engineering-collapse :deep(.el-collapse-item__wrap){border-bottom:0}.collapse-title{font-weight:600;color:#3e526a}.collapse-title em{font-style:normal;font-weight:400;color:#a16c18}.engineering-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 9px;padding-top:6px}.dirty-tip{margin:6px 0;padding:7px 9px;border-radius:6px;background:#fff7e6;color:#a96c0d;font-size:10px}.action-row{display:flex;justify-content:flex-end;gap:7px;margin-top:8px;padding-top:10px;border-top:1px solid #edf1f5}.input-summary{margin-top:10px;padding:8px 10px;background:#f6f8fb;border-radius:7px;display:flex;flex-wrap:wrap;gap:6px}.input-summary span,.input-summary strong{font-size:10px;padding:2px 7px;border-radius:12px;background:#fff;border:1px solid #e2e8f0;color:#42566d}.input-summary strong{color:#1262df;border-color:#cfe0fb}.output-panel{min-width:0;padding:0 14px 13px}.output-head{min-height:76px;display:flex;align-items:center;justify-content:space-between;gap:16px;border-bottom:1px solid #edf1f5}.output-head h2{margin:2px 0;font-size:17px;color:#1c3048}.output-head p{margin:0;color:#8694a6;font-size:10px}.output-status{text-align:right}.output-status>span{display:block;margin-top:4px;color:#7c8b9d;font-size:10px}.result-tabs{margin-top:4px}.result-tabs :deep(.el-tabs__header){margin-bottom:8px}.result-tabs :deep(.el-tabs__item){height:34px;font-size:12px}.table-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:7px}.table-toolbar b{font-size:12px;color:#30445b}.table-toolbar span{margin-left:7px;color:#8a98a9;font-size:10px}.process-table{width:100%}.process-table :deep(.el-table__cell){padding:6px 0}.process-table :deep(.cell){line-height:1.45}.process-table :deep(.pending-row){background:#fffaf0}.calc-title{display:block;color:#24384f;font-size:12px}.calc-detail{margin-top:3px;color:#66778a;font-size:10px;white-space:normal}.output-cell b{display:block;color:#162a43;font-size:12px;white-space:normal}.output-cell small{display:block;margin-top:3px;color:#78889a;font-size:10px;line-height:1.4;white-space:normal}.muted{color:#a0a9b5;font-size:10px}.status-text{display:block;margin-top:4px;color:#8b98a8;font-size:9px}.compact-table :deep(.el-table__cell){padding:6px 0}.pending{color:#d77b10}.ready-value{color:#17385c}.result-footer{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:9px;padding-top:9px;border-top:1px solid #edf1f5;color:#8794a5;font-size:10px}.saved-inline{display:flex;align-items:center;gap:5px}.result-empty{height:490px;display:flex;align-items:center;justify-content:center}.result-empty p{color:#8391a3;font-size:11px}.message-alert{margin-top:10px}@media(max-width:1280px){.workspace-grid{grid-template-columns:1fr}.input-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.result-empty{height:300px}}@media(max-width:850px){.workbench-hero,.output-head{align-items:flex-start;flex-direction:column}.input-grid,.engineering-grid{grid-template-columns:1fr}.action-row{flex-wrap:wrap}.table-toolbar{align-items:flex-start;flex-direction:column}}
</style>