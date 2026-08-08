<template>
  <div class="library-page" v-loading="loading">
    <div class="page-back-row">
      <el-button text class="back-button" @click="goBack">
        <el-icon><ArrowLeft /></el-icon>返回知识库总览
      </el-button>
    </div>

    <div class="library-header">
      <div>
        <div class="eyebrow">工程知识库</div>
        <h1>{{ library.name || '知识库' }}</h1>
        <p>{{ library.description }}</p>
      </div>
      <el-button type="primary" @click="drawer = true"><el-icon><DocumentAdd /></el-icon>Excel批量导入</el-button>
    </div>

    <div class="library-stat-row">
      <div><span>数据集</span><b>{{ library.dataset_count || 0 }}</b></div>
      <div><span>参数条目</span><b>{{ (library.record_count || 0).toLocaleString() }}</b></div>
      <div><span>状态</span><b class="enabled">启用中</b></div>
    </div>

    <div class="dataset-card">
      <div class="dataset-toolbar">
        <div class="section-title">数据集</div>
        <el-input v-model="keyword" :prefix-icon="Search" placeholder="搜索数据集" clearable style="width:260px" />
      </div>
      <el-table :data="filtered" class="clean-table" @row-click="openDataset">
        <el-table-column prop="name" label="数据集名称" min-width="260" />
        <el-table-column prop="category" label="分类" width="140" />
        <el-table-column prop="standard_no" label="标准号" width="150" />
        <el-table-column prop="source_file_name" label="来源文件" min-width="220" />
        <el-table-column prop="field_count" label="字段" width="90" />
        <el-table-column prop="record_count" label="记录" width="100" />
        <el-table-column prop="updated_at" label="更新时间" width="170" />
        <el-table-column label="操作" width="100">
          <template #default="scope"><el-button link type="primary" @click.stop="openDataset(scope.row)">查看</el-button></template>
        </el-table-column>
      </el-table>
      <div v-if="!filtered.length" class="empty-state">
        <el-empty description="还没有数据集，直接上传 Excel 即可自动生成参数页面。" />
      </div>
    </div>

    <ImportDrawer v-model="drawer" :default-knowledge-base-id="Number(route.params.id)" @imported="load" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, DocumentAdd, Search } from '@element-plus/icons-vue'
import http from '../api/http.js'
import ImportDrawer from '../components/ImportDrawer.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const drawer = ref(false)
const library = ref({})
const datasets = ref([])
const keyword = ref('')

const filtered = computed(() => !keyword.value ? datasets.value : datasets.value.filter(x => x.name.toLowerCase().includes(keyword.value.toLowerCase())))

async function load() {
  loading.value = true
  try {
    const { data } = await http.get(`/knowledge-bases/${route.params.id}/datasets`)
    library.value = data.knowledge_base
    datasets.value = data.datasets
  } finally { loading.value = false }
}

function goBack() { router.push({ name: 'dashboard' }) }
function openDataset(row) { router.push({ name: 'dataset', params: { id: row.id } }) }

watch(() => route.params.id, load)
onMounted(load)
</script>

<style scoped>
.page-back-row { margin-bottom: 10px; }
.back-button { padding-left: 2px; color: #5f7188; }
.back-button:hover { color: #1262df; }
</style>
