<template>
  <div class="standard-detail" v-loading="loading">
    <div class="page-back-row"><el-button text class="back-button" @click="router.push({name:'standards'})"><el-icon><ArrowLeft /></el-icon>返回标准规范库</el-button></div>

    <div class="standard-hero">
      <div class="hero-main"><div class="eyebrow">{{ detail.system }} · {{ detail.version }}</div><h1>{{ detail.code }}</h1><p>{{ detail.title }}</p></div>
      <div class="hero-status"><el-tag :type="statusType(detail.data_status)" effect="light">{{ detail.data_status }}</el-tag><span>{{ detail.linked_dataset_count || 0 }} 个数据集已关联</span></div>
    </div>

    <div class="overview-grid">
      <section class="overview-card emphasis"><span>这份规范主要管什么</span><b>{{ detail.title || '-' }}</b><p>{{ detail.key_fields || '-' }}</p></section>
      <section class="overview-card"><span>泛指哪些零件</span><div class="tag-wrap"><el-tag v-for="x in parts" :key="x" effect="plain" type="info">{{ x }}</el-tag></div></section>
      <section class="overview-card"><span>适用版本 / 来源</span><b>{{ detail.version || '待核版' }}</b><a v-if="detail.official_url" :href="detail.official_url" target="_blank">查看官方标准信息</a><small v-else>暂未登记官方来源</small></section>
    </div>

    <div class="meaning-card">
      <div class="section-title"><b>字段含义：不要只看“字段名”</b><span>这里把“标准 → 零件 → 数据字段 → 工程用途”拆开</span></div>
      <div v-if="detail.links?.length" class="meaning-list">
        <div v-for="link in detail.links" :key="`${link.standard_code}-${link.part_name}-${link.dataset_name}`" class="meaning-block">
          <div class="meaning-head"><div><el-tag size="small" effect="light" type="primary">{{ link.part_name }}</el-tag><b>{{ link.dataset_name }}</b></div><el-tag size="small" :type="linkStatusType(link.data_status)" effect="plain">{{ link.data_status }}</el-tag></div>
          <div class="applicability">适用：{{ link.applicability }} <span>·</span> {{ link.note }}</div>
          <div v-if="link.fields?.length" class="field-grid">
            <div v-for="field in link.fields" :key="field.field_code" class="field-card">
              <div><b>{{ field.field_name }}</b><em v-if="field.unit">{{ field.unit }}</em></div>
              <p>{{ field.description }}</p>
            </div>
          </div>
          <div v-else class="no-data">平台还没有建立这张标准数据表。这里保留字段设计，等你导入/授权后即可落数据。</div>

          <div v-if="link.rows?.length" class="data-section">
            <div class="data-head"><div><b>当前平台规格数据</b><span>不是标准“说明”，而是当前数据库里真实存在的记录</span></div><el-input v-model="localFilters[link.dataset_name]" clearable size="small" placeholder="筛选 NPS / Class / 规格" style="width:220px" /></div>
            <el-table :data="filteredRows(link)" border stripe size="small" class="spec-table">
              <el-table-column type="index" label="#" width="48" />
              <el-table-column v-for="field in link.fields" :key="field.field_code" :prop="field.field_code" :label="field.unit ? `${field.field_name} (${field.unit})` : field.field_name" min-width="125" show-overflow-tooltip>
                <template #default="scope"><span :class="cellClass(scope.row[field.field_code])">{{ scope.row[field.field_code] ?? '-' }}</span></template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>
      <el-empty v-else description="这份规范目前还没有建立字段映射。" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import http from '../api/http.js'
const route=useRoute();const router=useRouter();const loading=ref(false);const detail=ref({links:[]});const localFilters=reactive({})
const parts=computed(()=>String(detail.value.target_parts||'').split(/[\/、]/).map(x=>x.trim()).filter(Boolean))
function statusType(s){if(s==='部分')return'warning';if(/已录入/.test(s))return'success';if(/待/.test(s))return'danger';return'info'}
function linkStatusType(s){return s==='已关联'?'success':/待/.test(s)?'warning':'info'}
function filteredRows(link){const q=(localFilters[link.dataset_name]||'').trim().toLowerCase();if(!q)return link.rows||[];return(link.rows||[]).filter(row=>Object.values(row).some(v=>String(v??'').toLowerCase().includes(q)))}
function cellClass(v){return /待授权|待录入|待计算|待确认|缺失/.test(String(v??''))?'pending':''}
async function load(){loading.value=true;try{const{data}=await http.get(`/workbench/standards/${route.params.id}`);detail.value=data;(data.links||[]).forEach(x=>{if(localFilters[x.dataset_name]===undefined)localFilters[x.dataset_name]=''})}finally{loading.value=false}}
onMounted(load)
</script>

<style scoped>
.standard-detail{padding-bottom:30px}.page-back-row{margin-bottom:8px}.back-button{padding-left:2px;color:#61748a}.back-button:hover{color:#1262df}.standard-hero{background:#fff;border:1px solid #e6ebf2;border-radius:12px;padding:20px 22px;display:flex;align-items:center;justify-content:space-between;gap:20px}.eyebrow{font-size:11px;color:#1262df;letter-spacing:.06em}.hero-main h1{margin:4px 0 4px;font-size:24px;color:#1d2d42}.hero-main p{margin:0;color:#74869b;font-size:13px}.hero-status{display:flex;flex-direction:column;align-items:flex-end;gap:7px;color:#8996a7;font-size:11px}.overview-grid{display:grid;grid-template-columns:1.25fr 1fr .8fr;gap:10px;margin:10px 0}.overview-card{background:#fff;border:1px solid #e6ebf2;border-radius:10px;padding:12px 14px;min-height:88px}.overview-card>span{display:block;color:#8996a7;font-size:10px}.overview-card>b{display:block;margin-top:6px;color:#2a3d55;font-size:14px}.overview-card p{margin:6px 0 0;color:#7b8b9e;font-size:11px;line-height:1.5}.overview-card.emphasis{border-left:3px solid #1262df}.tag-wrap{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}.overview-card a{display:block;margin-top:7px;color:#1262df;font-size:11px}.overview-card small{display:block;margin-top:7px;color:#9aa6b4}.meaning-card{background:#fff;border:1px solid #e6ebf2;border-radius:10px;overflow:hidden}.section-title{padding:12px 15px;border-bottom:1px solid #edf1f5}.section-title b{color:#293c54;font-size:14px}.section-title span{margin-left:9px;color:#8a98a9;font-size:11px}.meaning-list{padding:0 14px}.meaning-block{padding:14px 0;border-bottom:1px solid #edf1f5}.meaning-block:last-child{border-bottom:0}.meaning-head{display:flex;align-items:center;justify-content:space-between}.meaning-head>div{display:flex;align-items:center;gap:8px}.meaning-head b{font-size:13px;color:#30445c}.applicability{margin:7px 0 9px;color:#7f8ea0;font-size:10px}.applicability span{margin:0 5px;color:#b6c0ca}.field-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.field-card{background:#f7f9fc;border:1px solid #edf1f5;border-radius:7px;padding:8px 9px}.field-card>div{display:flex;justify-content:space-between;gap:6px}.field-card b{font-size:11px;color:#31445b}.field-card em{font-style:normal;font-size:9px;color:#1262df;background:#eaf2ff;border-radius:4px;padding:2px 4px}.field-card p{margin:5px 0 0;color:#8a98a9;font-size:10px;line-height:1.45}.no-data{padding:10px;background:#fff8e8;color:#a66a11;border-radius:6px;font-size:11px}.data-section{margin-top:10px}.data-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px}.data-head b{font-size:12px;color:#30445c}.data-head span{margin-left:8px;color:#8b99aa;font-size:10px}.spec-table{width:100%}.pending{color:#d27a12;font-weight:600}@media(max-width:1100px){.overview-grid{grid-template-columns:1fr 1fr}.field-grid{grid-template-columns:repeat(3,1fr)}}@media(max-width:760px){.standard-hero{align-items:flex-start;flex-direction:column}.hero-status{align-items:flex-start}.overview-grid{grid-template-columns:1fr}.field-grid{grid-template-columns:repeat(2,1fr)}}
</style>
