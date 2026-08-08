<template>
  <div class="result-detail-page" v-loading="loading">
    <div class="page-back-row"><el-button text class="back-button" @click="router.push({ name:'designResults' })"><el-icon><ArrowLeft /></el-icon>返回设计成果库</el-button></div>

    <div class="hero">
      <div><div class="eyebrow">历史设计快照</div><h1>{{ detail.name || '设计成果' }}</h1><p>保存时间：{{ detail.saved_at || '-' }} · {{ detail.record_count || 0 }} 条记录</p></div>
      <el-button type="primary" @click="backToWorkbench"><el-icon><Operation /></el-icon>返回工作台继续设计</el-button>
    </div>

    <section class="snapshot-card">
      <div class="section-head"><div><b>① 保存时的输入条件</b><span>以下内容与当时点击“保存为知识库”的状态一致</span></div><el-tag type="success" effect="light">历史快照</el-tag></div>
      <div class="snapshot-grid">
        <div v-for="item in snapshotEntries" :key="item.name" class="snapshot-item"><span>{{ item.name }}</span><b>{{ item.value || '-' }}</b><small v-if="item.unit && item.unit !== '-'">{{ item.unit }}</small></div>
      </div>
    </section>

    <div class="result-summary">
      <div><span>零件几何</span><b>{{ detail.geometry_results?.length || 0 }}</b></div>
      <div><span>装配 / 接口</span><b>{{ detail.assembly_results?.length || 0 }}</b></div>
      <div><span>可用参数</span><b class="ok">{{ readyCount }}</b></div>
      <div><span>待补齐</span><b class="warn">{{ pendingCount }}</b></div>
    </div>

    <div class="result-grid">
      <section class="result-panel">
        <div class="panel-title"><div><span class="num blue">③</span><div><b>零件几何参数</b><small>用于零件建模 / SolidWorks变量</small></div></div><el-tag effect="plain">{{ detail.geometry_results?.length || 0 }} 项</el-tag></div>
        <el-table :data="detail.geometry_results || []" border stripe size="small" class="compact-table">
          <el-table-column prop="name" label="参数 / 变量" min-width="190" />
          <el-table-column label="取值" min-width="120"><template #default="scope"><b :class="valueClass(scope.row)">{{ scope.row.value || '-' }}</b></template></el-table-column>
          <el-table-column prop="unit" label="单位" width="72" />
          <el-table-column prop="source" label="来源" min-width="125" />
          <el-table-column label="状态" width="95"><template #default="scope"><el-tag size="small" :type="statusType(scope.row.status)" effect="light">{{ scope.row.status }}</el-tag></template></el-table-column>
        </el-table>
      </section>

      <section class="result-panel">
        <div class="panel-title"><div><span class="num green">④</span><div><b>装配 / 接口参数</b><small>用于总装、连接、执行机构</small></div></div><el-tag effect="plain">{{ detail.assembly_results?.length || 0 }} 项</el-tag></div>
        <el-table :data="detail.assembly_results || []" border stripe size="small" class="compact-table">
          <el-table-column prop="name" label="参数 / 接口" min-width="190" />
          <el-table-column label="取值" min-width="120"><template #default="scope"><b :class="valueClass(scope.row)">{{ scope.row.value || '-' }}</b></template></el-table-column>
          <el-table-column prop="unit" label="单位" width="72" />
          <el-table-column prop="source" label="来源" min-width="125" />
          <el-table-column label="状态" width="95"><template #default="scope"><el-tag size="small" :type="statusType(scope.row.status)" effect="light">{{ scope.row.status }}</el-tag></template></el-table-column>
        </el-table>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Operation } from '@element-plus/icons-vue'
import http from '../api/http.js'

const route = useRoute(); const router = useRouter(); const loading = ref(false); const detail = ref({ snapshot:{}, geometry_results:[], assembly_results:[] })
const snapshotEntries = computed(() => {
  const order=['阀门结构','公称口径','压力等级','通径形式','端部连接','阀体材料','球体材料组','阀座材料','设计压力','设计温度','泄漏等级','介质']
  return order.map(name=>({name,value:detail.value.snapshot?.[name] || '-'}))
})
const all = computed(()=>[...(detail.value.geometry_results||[]),...(detail.value.assembly_results||[])])
const pendingCount = computed(()=>all.value.filter(x=>!x.value || x.value==='-' || /待|缺失|错误/.test(`${x.value} ${x.status}`)).length)
const readyCount = computed(()=>all.value.length-pendingCount.value)
function statusType(s){if(/可用|已录入|通过|已保存/.test(s||''))return'success';if(/待/.test(s||''))return'warning';if(/缺失|错误/.test(s||''))return'danger';return'info'}
function valueClass(r){return !r.value||r.value==='-'||/待|缺失|错误/.test(`${r.value} ${r.status}`)?'pending':'normal'}
async function load(){loading.value=true;try{const{data}=await http.get(`/workbench/results/${route.params.id}`);detail.value=data}finally{loading.value=false}}
function backToWorkbench(){router.push({name:'workbench'})}
onMounted(load)
</script>

<style scoped>
.result-detail-page{padding-bottom:30px}.page-back-row{margin-bottom:8px}.back-button{padding-left:2px;color:#61748a}.back-button:hover{color:#1262df}.hero{background:#fff;border:1px solid #e6ebf2;border-radius:12px;padding:18px 22px;display:flex;justify-content:space-between;align-items:center;gap:20px}.eyebrow{font-size:11px;color:#1262df;letter-spacing:.08em}.hero h1{margin:4px 0 5px;font-size:21px;color:#1d2d42}.hero p{margin:0;color:#8391a4;font-size:11px}.snapshot-card,.result-panel{background:#fff;border:1px solid #e6ebf2;border-radius:10px}.snapshot-card{margin-top:10px;padding:13px 15px}.section-head,.panel-title{display:flex;align-items:center;justify-content:space-between;gap:12px}.section-head b{font-size:14px;color:#26384e}.section-head span{margin-left:8px;color:#8a98a9;font-size:11px}.snapshot-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:7px;margin-top:10px}.snapshot-item{min-width:0;padding:8px 10px;background:#f7f9fc;border:1px solid #edf1f5;border-radius:7px}.snapshot-item span{display:block;color:#8795a8;font-size:10px}.snapshot-item b{display:block;margin-top:3px;color:#2f425a;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.snapshot-item small{color:#8a98a9;font-size:10px}.result-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;margin:10px 0}.result-summary>div{background:#fff;border:1px solid #e6ebf2;border-radius:9px;padding:9px 13px}.result-summary span{display:block;color:#8795a8;font-size:10px}.result-summary b{display:block;margin-top:3px;font-size:19px;color:#2c3f57}.result-summary .ok{color:#23945d}.result-summary .warn{color:#d27a12}.result-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.result-panel{padding:0 13px 12px;overflow:hidden}.panel-title{min-height:53px;border-bottom:1px solid #edf1f5}.panel-title>div{display:flex;align-items:center;gap:8px}.panel-title b{display:block;color:#2a3c53;font-size:13px}.panel-title small{display:block;color:#8a98a9;font-size:10px;margin-top:3px}.num{width:25px;height:25px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700}.num.blue{background:#eaf2ff;color:#1262df}.num.green{background:#eaf8f1;color:#23945d}.compact-table{margin-top:10px}.normal{color:#2f425a}.pending{color:#d27a12}@media(max-width:1250px){.snapshot-grid{grid-template-columns:repeat(4,1fr)}.result-grid{grid-template-columns:1fr}}@media(max-width:760px){.hero{align-items:flex-start;flex-direction:column}.snapshot-grid{grid-template-columns:repeat(2,1fr)}.result-summary{grid-template-columns:repeat(2,1fr)}}
</style>
