<template>
  <div class="dataset-card">
    <div class="dataset-toolbar">
      <div><div class="eyebrow">数据管理</div><h1 style="margin:4px 0 0">导入记录</h1></div>
      <el-button type="primary" @click="drawer=true"><el-icon><DocumentAdd /></el-icon>Excel批量导入</el-button>
    </div>
    <el-table :data="rows" class="clean-table">
      <el-table-column prop="filename" label="文件名" min-width="260" />
      <el-table-column prop="sheet_name" label="Sheet" width="140" />
      <el-table-column prop="total_rows" label="识别行数" width="100" />
      <el-table-column prop="success_rows" label="成功" width="90" />
      <el-table-column prop="failed_rows" label="失败" width="90" />
      <el-table-column prop="status" label="状态" width="120" />
      <el-table-column prop="message" label="说明" min-width="260" show-overflow-tooltip />
      <el-table-column prop="created_at" label="时间" width="180" />
    </el-table>
    <ImportDrawer v-model="drawer" @imported="load" />
  </div>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import { DocumentAdd } from '@element-plus/icons-vue'
import http from '../api/http.js'
import ImportDrawer from '../components/ImportDrawer.vue'
const rows = ref([]); const drawer = ref(false)
async function load(){ const {data}=await http.get('/imports/recent?limit=100'); rows.value=data }
onMounted(load)
</script>
