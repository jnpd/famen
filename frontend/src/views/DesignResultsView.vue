<template>
  <div class="results-page" v-loading="loading">
    <div class="page-back-row"><el-button text class="back-button" @click="router.push({ name: 'workbench' })"><el-icon><ArrowLeft /></el-icon>返回参数生成工作台</el-button></div>

    <div class="page-head">
      <div><div class="eyebrow">工程成果追溯</div><h1>设计成果库</h1><p>每一次“保存为知识库”都会形成一份独立设计快照；点开即可恢复当时的输入条件和完整参数结果。</p></div>
      <el-button type="primary" @click="router.push({ name: 'workbench' })"><el-icon><Operation /></el-icon>新建参数方案</el-button>
    </div>

    <div class="stats-grid">
      <div class="stat"><span>保存方案</span><b>{{ total }}</b><small>全部历史</small></div>
      <div class="stat"><span>当前筛选</span><b>{{ rows.length }}</b><small>符合条件</small></div>
      <div class="stat"><span>最近保存</span><b class="time">{{ rows[0]?.saved_at || '-' }}</b><small>最新一条</small></div>
      <div class="stat"><span>待补齐参数</span><b class="warn">{{ pendingTotal }}</b><small>仅当前列表</small></div>
    </div>

    <div class="filter-card">
      <div class="filter-main">
        <el-input v-model="filters.keyword" clearable placeholder="搜索方案名 / 介质" :prefix-icon="Search" @keyup.enter="load" />
        <el-input v-model="filters.nps" clearable placeholder="NPS，例如 NPS12" @keyup.enter="load" />
        <el-input v-model="filters.pressure" clearable placeholder="Class，例如 CL600" @keyup.enter="load" />
        <el-input v-model="filters.leakage" clearable placeholder="泄漏等级" @keyup.enter="load" />
        <el-select v-model="filters.sort" style="width:150px">
          <el-option label="最新保存" value="newest" /><el-option label="最早保存" value="oldest" /><el-option label="按口径" value="nps" /><el-option label="按压力等级" value="pressure" />
        </el-select>
        <el-button type="primary" @click="load">筛选</el-button><el-button @click="reset">重置</el-button>
      </div>
    </div>

    <div class="history-card">
      <div class="history-head"><div><b>历史设计记录</b><span>点击任意记录查看保存时的完整输入与输出</span></div><el-tag effect="plain">{{ total }} 条</el-tag></div>
      <div v-if="rows.length" class="history-list">
        <div v-for="row in rows" :key="row.id" class="history-row" @click="open(row)">
          <div class="history-main">
            <div class="result-name"><b>{{ row.name }}</b><el-tag size="small" :type="row.pending_count ? 'warning' : 'success'" effect="light">{{ row.pending_count ? `${row.pending_count} 项待补齐` : '参数完整' }}</el-tag></div>
            <div class="tag-line"><el-tag size="small">{{ row.nps }}</el-tag><el-tag size="small" type="info">{{ row.pressure_class }}</el-tag><el-tag size="small" type="warning" effect="plain">{{ row.leakage_level || '未指定泄漏等级' }}</el-tag><span>{{ row.medium || '-' }}</span></div>
            <div class="snapshot-line"><span>设计压力 <b>{{ row.design_pressure }} MPa</b></span><span>设计温度 <b>{{ row.design_temperature }} ℃</b></span><span>几何 {{ row.geometry_count }} 项</span><span>装配 {{ row.assembly_count }} 项</span></div>
          </div>
          <div class="history-time"><span>{{ row.saved_at }}</span><el-icon><ArrowRight /></el-icon></div>
        </div>
      </div>
      <el-empty v-else description="还没有保存过设计成果。先去参数生成工作台生成并保存一份。" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, Operation, Search } from '@element-plus/icons-vue'
import http from '../api/http.js'

const router = useRouter()
const loading = ref(false)
const total = ref(0)
const rows = ref([])
const filters = reactive({ keyword:'', nps:'', pressure:'', leakage:'', sort:'newest' })
const pendingTotal = computed(() => rows.value.reduce((sum, x) => sum + Number(x.pending_count || 0), 0))

async function load() {
  loading.value = true
  try {
    const { data } = await http.get('/workbench/results', { params:{ keyword:filters.keyword, nps:filters.nps, pressure_class:filters.pressure, leakage_level:filters.leakage, sort:filters.sort } })
    total.value = data.total || 0; rows.value = data.rows || []
  } finally { loading.value = false }
}
function reset(){ Object.assign(filters,{keyword:'',nps:'',pressure:'',leakage:'',sort:'newest'}); load() }
function open(row){ router.push({ name:'designResultDetail', params:{ id:row.id } }) }
onMounted(load)
</script>

<style scoped>
.results-page{padding-bottom:28px}.page-back-row{margin-bottom:8px}.back-button{padding-left:2px;color:#61748a}.back-button:hover{color:#1262df}.page-head{background:#fff;border:1px solid #e6ebf2;border-radius:12px;padding:18px 22px;display:flex;justify-content:space-between;align-items:center;gap:20px}.page-head h1{margin:3px 0 5px;font-size:23px;color:#1d2d42}.page-head p{margin:0;color:#7a899d;font-size:12px}.eyebrow{font-size:11px;color:#1262df;letter-spacing:.08em}.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:10px 0}.stat{background:#fff;border:1px solid #e6ebf2;border-radius:10px;padding:11px 14px}.stat span,.stat small{display:block;color:#8492a4;font-size:11px}.stat b{display:block;margin:4px 0;font-size:21px;color:#26384e}.stat b.time{font-size:13px}.stat b.warn{color:#d27a12}.filter-card,.history-card{background:#fff;border:1px solid #e6ebf2;border-radius:10px}.filter-card{padding:10px}.filter-main{display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr 150px auto auto;gap:8px}.history-card{margin-top:10px;overflow:hidden}.history-head{height:48px;padding:0 15px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #edf1f5}.history-head b{font-size:14px;color:#26384e}.history-head span{margin-left:9px;color:#8a98a9;font-size:11px}.history-list{display:flex;flex-direction:column}.history-row{display:flex;justify-content:space-between;align-items:center;gap:20px;padding:12px 15px;border-bottom:1px solid #edf1f5;cursor:pointer;transition:.15s;background:#fff}.history-row:hover{background:#f7faff}.history-row:last-child{border-bottom:0}.history-main{min-width:0}.result-name{display:flex;align-items:center;gap:8px}.result-name b{font-size:13px;color:#26384e;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.tag-line,.snapshot-line{display:flex;align-items:center;gap:8px;margin-top:6px;font-size:11px;color:#7c8b9d}.snapshot-line{gap:18px}.snapshot-line b{color:#40536b}.history-time{display:flex;align-items:center;gap:12px;white-space:nowrap;color:#8a98a9;font-size:11px}.history-time .el-icon{color:#1262df}@media(max-width:1100px){.filter-main{grid-template-columns:1fr 1fr 1fr}.stats-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:760px){.page-head{align-items:flex-start;flex-direction:column}.filter-main{grid-template-columns:1fr}.history-row{align-items:flex-start;flex-direction:column}.history-time{width:100%;justify-content:space-between}}
</style>
