<template>
  <div class="standards-page" v-loading="loading">
    <div class="page-head">
      <div><div class="eyebrow">规范 → 零件 → 字段 → 规格数据</div><h1>标准规范库</h1><p>这里不只告诉你“标准是什么”，而是把标准对应的零件、字段、适用规格和平台已有数据串起来。</p></div>
      <el-tag size="large" effect="plain">{{ total }} 项规范</el-tag>
    </div>

    <div class="stats-grid">
      <div class="stat"><span>规范总数</span><b>{{ total }}</b><small>你提供的标准清单</small></div>
      <div class="stat"><span>已建立字段映射</span><b class="ok">{{ linkedCount }}</b><small>已有平台数据关系</small></div>
      <div class="stat"><span>部分可用</span><b class="warn">{{ partialCount }}</b><small>有数据但需补标准值</small></div>
      <div class="stat"><span>待授权 / 待确认</span><b class="danger">{{ pendingCount }}</b><small>不会用猜测值替代</small></div>
    </div>

    <div class="filter-card">
      <el-input v-model="filters.keyword" clearable placeholder="搜索标准号、用途、零件、字段" :prefix-icon="Search" @keyup.enter="load" />
      <el-select v-model="filters.system" clearable placeholder="标准体系" style="width:150px"><el-option v-for="x in systems" :key="x" :label="x" :value="x" /></el-select>
      <el-select v-model="filters.status" clearable placeholder="数据状态" style="width:150px"><el-option v-for="x in statuses" :key="x" :label="x" :value="x" /></el-select>
      <el-select v-model="filters.sort" style="width:145px"><el-option label="按标准号" value="code" /><el-option label="按体系" value="system" /><el-option label="按数据状态" value="status" /></el-select>
      <el-button type="primary" @click="load">筛选</el-button><el-button @click="reset">重置</el-button>
    </div>

    <div class="table-card">
      <el-table :data="rows" border stripe size="small" @row-click="open" class="standard-table">
        <el-table-column prop="code" label="标准 / 来源" min-width="205" fixed>
          <template #default="scope"><div class="standard-name"><b>{{ scope.row.code }}</b><el-tag size="small" :type="systemType(scope.row.system)" effect="light">{{ scope.row.system }}</el-tag></div><small>{{ scope.row.version }}</small></template>
        </el-table-column>
        <el-table-column prop="title" label="规范管什么" min-width="220" />
        <el-table-column prop="target_parts" label="泛指零件" min-width="190" />
        <el-table-column prop="key_fields" label="关键数据字段" min-width="260" show-overflow-tooltip />
        <el-table-column label="数据状态" width="110" fixed="right"><template #default="scope"><el-tag size="small" :type="statusType(scope.row.data_status)" effect="light">{{ scope.row.data_status }}</el-tag></template></el-table-column>
        <el-table-column label="已关联" width="75" fixed="right"><template #default="scope"><b>{{ scope.row.link_count }}</b></template></el-table-column>
      </el-table>
      <el-empty v-if="!rows.length" description="没有符合条件的标准" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import http from '../api/http.js'
const router=useRouter();const loading=ref(false);const rows=ref([]);const total=ref(0);const systems=ref([]);const statuses=ref([])
const filters=reactive({keyword:'',system:'',status:'',sort:'code'})
const linkedCount=computed(()=>rows.value.filter(x=>x.link_count>0).length)
const partialCount=computed(()=>rows.value.filter(x=>x.data_status==='部分').length)
const pendingCount=computed(()=>rows.value.filter(x=>/待/.test(x.data_status)).length)
function systemType(s){return s==='API'?'danger':s==='ASME'?'warning':s==='ISO'?'success':s==='GB'?'':s==='GOST'?'info':'info'}
function statusType(s){if(s==='部分')return'warning';if(/已录入/.test(s))return'success';if(/待/.test(s))return'danger';return'info'}
async function load(){loading.value=true;try{const{data}=await http.get('/workbench/standards',{params:{keyword:filters.keyword,system:filters.system,data_status:filters.status,sort:filters.sort}});rows.value=data.rows||[];total.value=data.total||0;systems.value=data.systems||[];statuses.value=data.statuses||[]}finally{loading.value=false}}
function reset(){Object.assign(filters,{keyword:'',system:'',status:'',sort:'code'});load()}
function open(row){router.push({name:'standardDetail',params:{id:row.id}})}
onMounted(load)
</script>

<style scoped>
.standards-page{padding-bottom:28px}.page-head{background:#fff;border:1px solid #e6ebf2;border-radius:12px;padding:18px 22px;display:flex;align-items:center;justify-content:space-between}.eyebrow{font-size:11px;color:#1262df;letter-spacing:.06em}.page-head h1{margin:4px 0 5px;font-size:23px;color:#1d2d42}.page-head p{margin:0;color:#7a899d;font-size:12px}.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:10px 0}.stat{background:#fff;border:1px solid #e6ebf2;border-radius:10px;padding:10px 14px}.stat span,.stat small{display:block;color:#8492a4;font-size:10px}.stat b{display:block;margin:3px 0;font-size:21px;color:#26384e}.stat b.ok{color:#23945d}.stat b.warn{color:#d27a12}.stat b.danger{color:#d14d4d}.filter-card{display:flex;gap:8px;align-items:center;background:#fff;border:1px solid #e6ebf2;border-radius:10px;padding:10px;margin-bottom:10px}.filter-card>.el-input{width:330px}.table-card{background:#fff;border:1px solid #e6ebf2;border-radius:10px;overflow:hidden}.standard-table{cursor:pointer}.standard-name{display:flex;align-items:center;gap:7px}.standard-name b{color:#26384e}.standard-name+small{display:block;margin-top:3px;color:#8a98a9;font-size:10px}@media(max-width:1000px){.stats-grid{grid-template-columns:repeat(2,1fr)}.filter-card{flex-wrap:wrap}.filter-card>.el-input{width:100%}}@media(max-width:700px){.page-head{align-items:flex-start;gap:10px;flex-direction:column}}
</style>
