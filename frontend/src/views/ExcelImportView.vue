<template>
  <div class="excel-import-page">
    <div class="library-header">
      <div>
        <div class="eyebrow">数据管理 / Excel 导入</div>
        <h1>Excel 批量导入</h1>
        <p>上传工程 Excel，系统自动识别 Sheet、表头与字段，确认映射后写入 SQLite 并生成参数查询页面。</p>
      </div>
      <el-button type="primary" size="large" @click="drawer = true"><el-icon><UploadFilled /></el-icon>选择 Excel 文件</el-button>
    </div>

    <section class="import-guide-grid">
      <div class="guide-card"><div class="guide-num">01</div><b>上传 Excel</b><span>支持 .xlsx / .xls，允许首行是表名、下一行才是真实字段。</span></div>
      <div class="guide-card"><div class="guide-num">02</div><b>字段映射</b><span>自动猜测字段编码和数据类型，也可以人工调整显示名称、单位。</span></div>
      <div class="guide-card"><div class="guide-num">03</div><b>预览校验</b><span>正式入库前预览数据，确认 Sheet、表头行和目标知识库。</span></div>
      <div class="guide-card"><div class="guide-num">04</div><b>自动展示</b><span>导入完成后立即生成可搜索、筛选、排序、编辑和导出的参数页面。</span></div>
    </section>

    <section class="dataset-card import-example-card">
      <div class="dataset-toolbar">
        <div>
          <div class="section-title">推荐 Excel 结构</div>
          <div class="example-desc">不要求固定模板；下面这种工程表格可以直接识别。</div>
        </div>
        <el-button @click="drawer = true">立即导入</el-button>
      </div>
      <el-table :data="exampleRows" class="clean-table">
        <el-table-column prop="nps" label="公称口径" />
        <el-table-column prop="npsValue" label="NPS数值" />
        <el-table-column prop="dn" label="DN" />
        <el-table-column prop="inch" label="英寸显示" />
        <el-table-column prop="mm" label="毫米参考" />
        <el-table-column prop="remark" label="备注" min-width="220" />
      </el-table>
    </section>

    <ImportDrawer v-model="drawer" @imported="onImported" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ImportDrawer from '../components/ImportDrawer.vue'

const drawer = ref(false)
const exampleRows = [
  { nps: 'NPS2', npsValue: 2, dn: 'DN50', inch: '2"', mm: 50, remark: '常用固定球阀口径' },
  { nps: 'NPS8', npsValue: 8, dn: 'DN200', inch: '8"', mm: 200, remark: '常用固定球阀口径' },
  { nps: 'NPS12', npsValue: 12, dn: 'DN300', inch: '12"', mm: 300, remark: '常用固定球阀口径' }
]

function onImported(data) {
  ElMessage.success(`已导入 ${data.record_count || 0} 条数据`)
}
</script>
