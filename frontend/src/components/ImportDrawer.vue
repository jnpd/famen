<template>
  <el-drawer
    :model-value="modelValue"
    title="Excel批量导入"
    size="540px"
    :destroy-on-close="false"
    @close="emit('update:modelValue', false)"
  >
    <div class="import-wrap">
      <el-steps :active="step" finish-status="success" align-center>
        <el-step title="上传Excel" />
        <el-step title="字段映射" />
        <el-step title="预览校验" />
        <el-step title="导入完成" />
      </el-steps>

      <div v-if="step === 0" class="step-panel">
        <el-upload
          drag
          :auto-upload="false"
          :limit="1"
          accept=".xlsx,.xls"
          :on-change="onFileChange"
          :on-remove="onRemove"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">将 Excel 文件拖到此处，或 <em>点击上传</em></div>
          <template #tip>
            <div class="el-upload__tip">支持 .xlsx / .xls；系统会自动识别 Sheet 和表头。</div>
          </template>
        </el-upload>

        <div v-if="inspect" class="inspect-card">
          <div class="file-line"><el-icon><Document /></el-icon><span>{{ inspect.filename }}</span></div>
          <div class="source-config">
            <div>
              <label>Sheet</label>
              <el-select v-model="source.sheet_name" size="small" style="width:100%" @change="refreshPreview">
                <el-option v-for="s in inspect.sheets || []" :key="s" :label="s" :value="s" />
              </el-select>
            </div>
            <div>
              <label>表头行</label>
              <el-input-number v-model="source.header_row_display" :min="1" :max="50" size="small" style="width:100%" @change="refreshPreview" />
            </div>
          </div>
          <div class="inspect-grid">
            <div><span>当前 Sheet</span><b>{{ inspect.sheet_name }}</b></div>
            <div><span>识别表头</span><b>第 {{ inspect.header_row + 1 }} 行</b></div>
            <div><span>字段</span><b>{{ inspect.columns?.length || 0 }}</b></div>
            <div><span>数据行</span><b>{{ inspect.row_count || 0 }}</b></div>
          </div>
        </div>
      </div>

      <div v-else-if="step === 1" class="step-panel mapping-panel">
        <el-form label-position="top">
          <el-form-item label="目标知识库">
            <el-select v-model="form.knowledge_base_id" style="width:100%" placeholder="请选择">
              <el-option v-for="kb in libraries" :key="kb.id" :label="kb.name" :value="kb.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="数据集名称">
            <el-input v-model="form.dataset_name" placeholder="例如：ASME B16.5 法兰尺寸表" />
          </el-form-item>
        </el-form>

        <div class="mapping-title">字段映射</div>
        <div class="mapping-list">
          <div v-for="m in mappings" :key="m.source_name" class="mapping-row">
            <el-checkbox v-model="m.enabled" />
            <div class="mapping-source" :title="m.source_name">{{ m.source_name }}</div>
            <el-input v-model="m.field_name" size="small" placeholder="显示名称" />
            <el-input v-model="m.field_code" size="small" placeholder="字段编码" />
            <el-select v-model="m.data_type" size="small" class="mapping-type">
              <el-option label="文本" value="text" />
              <el-option label="数值" value="number" />
            </el-select>
            <el-input v-model="m.unit" size="small" placeholder="单位" class="mapping-unit" />
          </div>
        </div>
      </div>

      <div v-else-if="step === 2" class="step-panel">
        <div class="preview-head">
          <div><b>{{ form.dataset_name }}</b></div>
          <div>{{ inspect?.row_count || 0 }} 条数据 · {{ mappings.filter(x => x.enabled).length }} 个字段</div>
        </div>
        <div class="preview-table-wrap">
          <table class="mini-table">
            <thead>
              <tr>
                <th v-for="m in enabledMappings" :key="m.field_code">{{ m.field_name }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in (inspect?.preview || []).slice(0, 6)" :key="idx">
                <td v-for="m in enabledMappings" :key="m.field_code">{{ row[m.source_name] ?? '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <el-alert title="校验通过后会写入 SQLite，并自动生成参数展示页面。" type="success" :closable="false" />
      </div>

      <div v-else class="step-panel done-panel">
        <el-result icon="success" title="导入完成" :sub-title="`已成功导入 ${result.record_count || 0} 条数据`">
          <template #extra>
            <el-button type="primary" @click="openDataset">查看参数页面</el-button>
            <el-button @click="reset">继续导入</el-button>
          </template>
        </el-result>
      </div>

      <div v-if="step < 3" class="drawer-footer">
        <el-button v-if="step > 0" @click="step--">上一步</el-button>
        <el-button
          type="primary"
          :loading="loading"
          :disabled="step === 0 && !inspect"
          @click="next"
        >
          {{ step === 2 ? '确认导入' : '下一步' }}
        </el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Document, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import http from '../api/http.js'

const props = defineProps({
  modelValue: Boolean,
  defaultKnowledgeBaseId: Number
})
const emit = defineEmits(['update:modelValue', 'imported'])
const router = useRouter()
const step = ref(0)
const loading = ref(false)
const inspect = ref(null)
const mappings = ref([])
const libraries = ref([])
const result = ref({})
const form = reactive({ knowledge_base_id: null, dataset_name: '' })
const source = reactive({ sheet_name: '', header_row_display: 1 })

const enabledMappings = computed(() => mappings.value.filter(x => x.enabled))

watch(() => props.modelValue, async visible => {
  if (visible) {
    const { data } = await http.get('/knowledge-bases')
    libraries.value = data
    form.knowledge_base_id = props.defaultKnowledgeBaseId || data.find(x => x.code === 'standard')?.id || data[0]?.id
  }
})

async function onFileChange(uploadFile) {
  if (!uploadFile?.raw) return
  loading.value = true
  try {
    const fd = new FormData()
    fd.append('file', uploadFile.raw)
    const { data } = await http.post('/imports/inspect', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    inspect.value = data
    source.sheet_name = data.sheet_name
    source.header_row_display = data.header_row + 1
    mappings.value = (data.columns || []).map(x => ({ ...x }))
    form.dataset_name = data.filename.replace(/\.(xlsx|xls)$/i, '')
    ElMessage.success('Excel 识别成功')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}


async function refreshPreview() {
  if (!inspect.value?.import_id || !source.sheet_name) return
  loading.value = true
  try {
    const { data } = await http.post(`/imports/${inspect.value.import_id}/preview`, {
      sheet_name: source.sheet_name,
      header_row: Math.max(0, Number(source.header_row_display || 1) - 1)
    })
    inspect.value = data
    source.sheet_name = data.sheet_name
    source.header_row_display = data.header_row + 1
    mappings.value = (data.columns || []).map(x => ({ ...x }))
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function onRemove() {
  inspect.value = null
  mappings.value = []
}

async function next() {
  if (step.value === 0) {
    step.value = 1
    return
  }
  if (step.value === 1) {
    if (!form.knowledge_base_id || !form.dataset_name.trim()) {
      ElMessage.warning('请选择知识库并填写数据集名称')
      return
    }
    if (!enabledMappings.value.length) {
      ElMessage.warning('至少保留一个字段')
      return
    }
    step.value = 2
    return
  }
  if (step.value === 2) {
    loading.value = true
    try {
      const payload = {
        knowledge_base_id: form.knowledge_base_id,
        dataset_name: form.dataset_name,
        sheet_name: inspect.value.sheet_name,
        header_row: inspect.value.header_row,
        mappings: mappings.value
      }
      const { data } = await http.post(`/imports/${inspect.value.import_id}/commit`, payload)
      result.value = data
      step.value = 3
      emit('imported', data)
      ElMessage.success('导入完成')
    } catch (e) {
      ElMessage.error(e.message)
    } finally {
      loading.value = false
    }
  }
}

function reset() {
  step.value = 0
  inspect.value = null
  mappings.value = []
  result.value = {}
  form.dataset_name = ''
  source.sheet_name = ''
  source.header_row_display = 1
}

function openDataset() {
  emit('update:modelValue', false)
  router.push({ name: 'dataset', params: { id: result.value.dataset_id } })
}
</script>
