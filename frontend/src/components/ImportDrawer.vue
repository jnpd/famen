<template>
  <el-drawer
    :model-value="modelValue"
    title="Excel批量导入"
    size="760px"
    :destroy-on-close="false"
    @close="emit('update:modelValue', false)"
  >
    <div class="import-wrap">
      <el-steps :active="step" finish-status="success" align-center>
        <el-step title="识别结构" />
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
            <div class="el-upload__tip">不要求固定模板；系统会分析 Sheet、表头、字段和数据结构，识别不确定时由你确认。</div>
          </template>
        </el-upload>

        <div v-if="inspect" class="inspect-card smart-inspect-card">
          <div class="file-line">
            <el-icon><Document /></el-icon>
            <span>{{ inspect.filename }}</span>
            <el-tag size="small" effect="plain">{{ (inspect.sheets || []).length }} 个 Sheet</el-tag>
          </div>

          <div class="source-config smart-source-config">
            <div>
              <label>选择 Sheet</label>
              <el-select v-model="source.sheet_name" size="small" style="width:100%" @change="onSheetChange">
                <el-option v-for="s in inspect.sheets || []" :key="s" :label="s" :value="s" />
              </el-select>
            </div>
            <div>
              <label>表头策略</label>
              <el-select v-model="source.header_mode" size="small" style="width:100%" @change="onHeaderModeChange">
                <el-option label="自动识别" value="auto" />
                <el-option label="手动指定" value="row" />
                <el-option label="无表头" value="none" />
              </el-select>
            </div>
            <div>
              <label>表头所在行</label>
              <el-input-number
                v-model="source.header_row_display"
                :min="1"
                :max="200"
                size="small"
                style="width:100%"
                :disabled="source.header_mode !== 'row'"
                @change="() => refreshPreview(false)"
              />
            </div>
          </div>

          <div class="analysis-card" :class="`analysis-${inspect.confidence_level || 'low'}`">
            <div class="analysis-top">
              <div>
                <div class="analysis-title">
                  <span>结构识别</span>
                  <el-tag :type="confidenceTagType" size="small" effect="light">{{ confidenceText }}</el-tag>
                  <el-tag v-if="inspect.structure_type === 'document'" type="warning" size="small" effect="plain">说明/配置型</el-tag>
                  <el-tag v-else-if="inspect.structure_type === 'table'" type="success" size="small" effect="plain">数据表型</el-tag>
                </div>
                <div class="analysis-message">{{ inspect.analysis_message || '请确认识别结果。' }}</div>
              </div>
              <div class="confidence-number">
                <b>{{ inspect.header_confidence ?? 0 }}%</b>
                <span>可信度</span>
              </div>
            </div>
            <el-progress
              :percentage="inspect.header_confidence ?? 0"
              :status="inspect.confidence_level === 'high' ? 'success' : inspect.confidence_level === 'low' ? 'exception' : ''"
              :show-text="false"
              :stroke-width="6"
            />
          </div>

          <div class="inspect-grid smart-inspect-grid">
            <div><span>当前 Sheet</span><b>{{ inspect.sheet_name }}</b></div>
            <div>
              <span>当前表头</span>
              <b>{{ inspect.header_row >= 0 ? `第 ${inspect.header_row + 1} 行` : '无表头' }}</b>
            </div>
            <div><span>数据开始</span><b>第 {{ inspect.data_start_row || 1 }} 行</b></div>
            <div><span>识别字段</span><b>{{ inspect.columns?.length || 0 }} 个</b></div>
            <div><span>数据行</span><b>{{ inspect.row_count || 0 }} 条</b></div>
            <div><span>建议数据集名</span><b>{{ inspect.suggested_dataset_name || '-' }}</b></div>
          </div>

          <div v-if="inspect.header_candidates?.length" class="candidate-row">
            <span>候选表头：</span>
            <el-button
              v-for="candidate in inspect.header_candidates"
              :key="candidate.row"
              size="small"
              plain
              :type="inspect.header_row === candidate.row ? 'primary' : ''"
              @click="applyCandidate(candidate.row)"
            >
              第 {{ candidate.display_row }} 行
            </el-button>
            <el-button size="small" plain :type="source.header_mode === 'none' ? 'primary' : ''" @click="useNoHeader">无表头</el-button>
          </div>

          <el-alert
            v-if="source.header_mode === 'auto' && (inspect.header_confidence ?? 0) < 60"
            class="low-confidence-alert"
            title="系统没有足够把握自动采用表头，请手动选择候选行，或明确选择“无表头”后再继续。"
            type="warning"
            :closable="false"
            show-icon
          />

          <div class="structure-preview">
            <div class="preview-section-head">
              <div>
                <b>即时预览</b>
                <span>确认第一行确实是字段名，而不是标题或第一条数据</span>
              </div>
              <el-button size="small" text type="primary" :loading="loading" @click="refreshPreview(false)">重新解析</el-button>
            </div>
            <div class="preview-table-wrap smart-preview-wrap">
              <table class="mini-table">
                <thead>
                  <tr>
                    <th v-for="col in inspect.columns || []" :key="col.source_name">{{ col.field_name }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in (inspect.preview || []).slice(0, 6)" :key="idx">
                    <td v-for="col in inspect.columns || []" :key="col.source_name">{{ row[col.source_name] ?? '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="step === 1" class="step-panel mapping-panel">
        <el-form label-position="top">
          <div class="form-grid-two">
            <el-form-item label="目标知识库">
              <el-select v-model="form.knowledge_base_id" style="width:100%" placeholder="请选择">
                <el-option v-for="kb in libraries" :key="kb.id" :label="kb.name" :value="kb.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="数据集名称">
              <el-input v-model="form.dataset_name" placeholder="例如：ASME B16.5 法兰尺寸表" />
            </el-form-item>
          </div>
        </el-form>

        <div class="mapping-title">字段映射</div>
        <div class="mapping-tip">字段名称和数量不固定。系统只做推荐，你可以改显示名、字段编码、类型和单位，也可以取消不需要的字段。</div>
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
        <div class="preview-head final-preview-head">
          <div>
            <b>{{ form.dataset_name }}</b>
            <span>{{ inspect?.sheet_name }} · {{ inspect?.header_row >= 0 ? `第 ${inspect.header_row + 1} 行表头` : '无表头' }}</span>
          </div>
          <div>{{ inspect?.row_count || 0 }} 条数据 · {{ enabledMappings.length }} 个字段</div>
        </div>
        <div class="preview-table-wrap">
          <table class="mini-table">
            <thead>
              <tr>
                <th v-for="m in enabledMappings" :key="m.field_code">{{ m.field_name }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in (inspect?.preview || []).slice(0, 8)" :key="idx">
                <td v-for="m in enabledMappings" :key="m.field_code">{{ row[m.source_name] ?? '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <el-alert title="确认后才会写入 SQLite。当前预览看到的字段和第一条数据，就是正式导入后的结构。" type="success" :closable="false" />
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

const AUTO_HEADER = -2
const NO_HEADER = -1

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
const source = reactive({ sheet_name: '', header_mode: 'auto', header_row_display: 1 })

const enabledMappings = computed(() => mappings.value.filter(x => x.enabled))
const confidenceTagType = computed(() => {
  if (inspect.value?.confidence_level === 'high') return 'success'
  if (inspect.value?.confidence_level === 'medium') return 'warning'
  return 'danger'
})
const confidenceText = computed(() => {
  const level = inspect.value?.confidence_level
  if (level === 'high') return '高可信'
  if (level === 'medium') return '建议确认'
  return '需要人工确认'
})

watch(() => props.modelValue, async visible => {
  if (visible) {
    const { data } = await http.get('/knowledge-bases')
    libraries.value = data
    form.knowledge_base_id = props.defaultKnowledgeBaseId || data.find(x => x.code === 'standard')?.id || data[0]?.id
  }
})

function syncPreview(data, updateDatasetName = false) {
  inspect.value = data
  source.sheet_name = data.sheet_name
  if (data.header_row >= 0) source.header_row_display = data.header_row + 1
  mappings.value = (data.columns || []).map(x => ({ ...x }))
  if (updateDatasetName) {
    form.dataset_name = data.suggested_dataset_name || data.sheet_name || data.filename?.replace(/\.(xlsx|xls)$/i, '') || ''
  }
}

async function onFileChange(uploadFile) {
  if (!uploadFile?.raw) return
  loading.value = true
  try {
    const fd = new FormData()
    fd.append('file', uploadFile.raw)
    const { data } = await http.post('/imports/inspect', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    source.header_mode = 'auto'
    syncPreview(data, true)
    ElMessage.success('Excel结构分析完成')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function requestHeaderRow() {
  if (source.header_mode === 'auto') return AUTO_HEADER
  if (source.header_mode === 'none') return NO_HEADER
  return Math.max(0, Number(source.header_row_display || 1) - 1)
}

async function refreshPreview(updateDatasetName = false) {
  if (!inspect.value?.import_id || !source.sheet_name) return
  loading.value = true
  try {
    const { data } = await http.post(`/imports/${inspect.value.import_id}/preview`, {
      sheet_name: source.sheet_name,
      header_row: requestHeaderRow()
    })
    syncPreview(data, updateDatasetName)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function onSheetChange() {
  source.header_mode = 'auto'
  source.header_row_display = 1
  await refreshPreview(true)
}

async function onHeaderModeChange() {
  if (source.header_mode === 'row') {
    const candidate = inspect.value?.detected_header_row
    if (candidate >= 0) source.header_row_display = candidate + 1
  }
  await refreshPreview(false)
}

async function applyCandidate(row) {
  source.header_mode = 'row'
  source.header_row_display = row + 1
  await refreshPreview(false)
}

async function useNoHeader() {
  source.header_mode = 'none'
  await refreshPreview(false)
}

function onRemove() {
  inspect.value = null
  mappings.value = []
}

async function next() {
  if (step.value === 0) {
    if (source.header_mode === 'auto' && (inspect.value?.header_confidence ?? 0) < 60) {
      ElMessage.warning('当前识别可信度较低，请手动选择表头行，或明确选择“无表头”')
      return
    }
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
      const confirmedHeaderRow = source.header_mode === 'none'
        ? NO_HEADER
        : source.header_mode === 'row'
          ? Math.max(0, Number(source.header_row_display || 1) - 1)
          : inspect.value.header_row
      const payload = {
        knowledge_base_id: form.knowledge_base_id,
        dataset_name: form.dataset_name,
        sheet_name: inspect.value.sheet_name,
        header_row: confirmedHeaderRow,
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
  source.header_mode = 'auto'
  source.header_row_display = 1
}

function openDataset() {
  emit('update:modelValue', false)
  router.push({ name: 'dataset', params: { id: result.value.dataset_id } })
}
</script>

<style scoped>
.smart-inspect-card { padding: 16px; }
.file-line { flex-wrap: wrap; }
.smart-source-config { grid-template-columns: 1.3fr 1fr .8fr; }
.analysis-card { margin-top: 14px; padding: 13px 14px; border: 1px solid #e3e9f2; border-radius: 9px; background: #f8fafc; }
.analysis-high { background: #f5fbf7; border-color: #cfe9d8; }
.analysis-medium { background: #fffaf1; border-color: #f0dfb5; }
.analysis-low { background: #fff7f5; border-color: #f1d3cc; }
.analysis-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; margin-bottom: 10px; }
.analysis-title { display: flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 700; color: #30445f; }
.analysis-message { margin-top: 7px; color: #6e7e92; font-size: 12px; line-height: 1.6; }
.confidence-number { flex: 0 0 auto; min-width: 58px; text-align: right; }
.confidence-number b { display: block; color: #24364d; font-size: 18px; }
.confidence-number span { display: block; margin-top: 2px; color: #96a2b2; font-size: 10px; }
.smart-inspect-grid { grid-template-columns: repeat(3, 1fr); }
.smart-inspect-grid b { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.candidate-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 14px; }
.candidate-row > span { color: #75859a; font-size: 12px; margin-right: 2px; }
.low-confidence-alert { margin-top: 14px; }
.structure-preview { margin-top: 16px; }
.preview-section-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; margin-bottom: 8px; }
.preview-section-head b { display: block; color: #304159; font-size: 13px; }
.preview-section-head span { display: block; margin-top: 4px; color: #8a98aa; font-size: 11px; }
.smart-preview-wrap { max-height: 255px; margin-bottom: 0; }
.form-grid-two { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.mapping-tip { margin: -2px 0 10px; color: #8290a3; font-size: 11px; line-height: 1.6; }
.final-preview-head > div:first-child b { display: block; color: #2f4057; font-size: 14px; }
.final-preview-head > div:first-child span { display: block; margin-top: 4px; color: #8896a8; font-size: 11px; }
@media (max-width: 1350px) {
  .smart-source-config { grid-template-columns: 1fr 1fr; }
  .smart-inspect-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
