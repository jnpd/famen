<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">
          <el-icon><Setting /></el-icon>
        </div>
        <div>
          <div class="brand-title">阀门工程知识库平台</div>
          <div class="brand-subtitle">标准 · 公式 · 参数 · 知识沉淀</div>
        </div>
      </div>

      <nav class="nav-block">
        <router-link class="nav-item" :class="{ active: route.name === 'dashboard' }" to="/">
          <el-icon><House /></el-icon><span>知识库总览</span>
        </router-link>
        <router-link class="nav-item" :class="{ active: route.name === 'workbench' }" to="/workbench">
          <el-icon><Operation /></el-icon><span>参数生成工作台</span>
        </router-link>

        <div class="nav-section">基础数据</div>
        <button
          v-for="kb in basicLibraries"
          :key="kb.id"
          class="nav-item nav-button"
          :class="{ active: Number(route.params.id) === kb.id && route.name === 'library' }"
          @click="goLibrary(kb.id)"
        >
          <el-icon><Collection /></el-icon>
          <span>{{ kb.name }}</span>
        </button>

        <div class="nav-section">工程知识库</div>
        <button
          v-for="kb in engineeringLibraries"
          :key="kb.id"
          class="nav-item nav-button"
          :class="{ active: Number(route.params.id) === kb.id && route.name === 'library' }"
          @click="goLibrary(kb.id)"
        >
          <el-icon>
            <Collection v-if="kb.type === 'standard'" />
            <DataAnalysis v-else-if="kb.type === 'formula'" />
            <TrendCharts v-else-if="kb.type === 'parameter'" />
            <FolderOpened v-else />
          </el-icon>
          <span>{{ kb.name }}</span>
        </button>

        <div class="nav-section">数据管理</div>
        <router-link class="nav-item" :class="{ active: route.name === 'excelImport' }" to="/excel-import">
          <el-icon><DocumentAdd /></el-icon><span>Excel导入</span>
        </router-link>
        <router-link class="nav-item" :class="{ active: route.name === 'imports' }" to="/imports">
          <el-icon><Clock /></el-icon><span>导入记录</span>
        </router-link>
      </nav>

      <div class="sidebar-note">
        <div class="note-title">专业阀门行业知识沉淀</div>
        <div class="note-text">把散落 Excel 统一变成可检索、可维护、可复用的工程数字库。</div>
        <div class="note-version">版本：v1.1.0</div>
      </div>
    </aside>

    <section class="content-shell">
      <header class="topbar">
        <div class="top-left">
          <el-icon class="menu-icon"><Menu /></el-icon>
          <div class="breadcrumb-text">{{ pageTitle }}</div>
        </div>
        <div class="top-actions">
          <div class="global-search">
            <el-icon><Search /></el-icon>
            <input placeholder="搜索知识库、条目、字段…" />
            <span>Ctrl + K</span>
          </div>
          <el-badge :value="5" class="top-icon"><el-icon><Bell /></el-icon></el-badge>
          <el-icon class="top-icon"><QuestionFilled /></el-icon>
          <el-dropdown trigger="click" @command="handleUserCommand">
            <div class="user-menu-trigger">
              <div class="admin-avatar">{{ avatarText }}</div>
              <div class="user-copy">
                <span class="admin-name">{{ auth.displayName }}</span>
                <small>{{ auth.user?.role === 'admin' ? '系统管理员' : '用户' }}</small>
              </div>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password"><el-icon><Key /></el-icon>修改密码</el-dropdown-item>
                <el-dropdown-item divided command="logout"><el-icon><SwitchButton /></el-icon>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <main class="main-content">
        <router-view @refresh-libraries="loadLibraries" />
      </main>
    </section>

    <el-dialog v-model="passwordVisible" title="修改登录密码" width="430px" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="当前密码"><el-input v-model="passwordForm.old_password" type="password" show-password autocomplete="current-password" /></el-form-item>
        <el-form-item label="新密码"><el-input v-model="passwordForm.new_password" type="password" show-password autocomplete="new-password" placeholder="至少 8 位" /></el-form-item>
        <el-form-item label="确认新密码"><el-input v-model="passwordForm.confirm_password" type="password" show-password autocomplete="new-password" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="passwordVisible = false">取消</el-button><el-button type="primary" :loading="passwordSaving" @click="changePassword">保存新密码</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  Bell,
  Clock,
  Collection,
  DataAnalysis,
  DocumentAdd,
  FolderOpened,
  House,
  Key,
  Menu,
  Operation,
  QuestionFilled,
  Search,
  Setting,
  SwitchButton,
  TrendCharts
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api/http.js'
import { useAuthStore } from '../stores/auth.js'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const libraries = ref([])
const passwordVisible = ref(false)
const passwordSaving = ref(false)
const passwordForm = reactive({ old_password: '', new_password: '', confirm_password: '' })

const basicLibraries = computed(() => libraries.value.filter(x => x.type === 'dictionary'))
const engineeringLibraries = computed(() => libraries.value.filter(x => x.type !== 'dictionary'))
const avatarText = computed(() => (auth.displayName || 'A').trim().slice(0, 1).toUpperCase())

const pageTitle = computed(() => {
  if (route.name === 'dashboard') return '知识库总览'
  if (route.name === 'workbench') return '参数生成工作台'
  if (route.name === 'excelImport') return 'Excel批量导入'
  if (route.name === 'imports') return '导入记录'
  if (route.name === 'dataset') return '参数数据详情'
  if (route.name === 'library') {
    const kb = libraries.value.find(x => x.id === Number(route.params.id))
    return kb?.name || '知识库'
  }
  return '阀门工程知识库'
})

async function loadLibraries() {
  try {
    const { data } = await http.get('/knowledge-bases')
    libraries.value = data
  } catch (e) { console.error(e) }
}
function goLibrary(id) { router.push({ name: 'library', params: { id } }) }

async function handleUserCommand(command) {
  if (command === 'password') {
    Object.assign(passwordForm, { old_password: '', new_password: '', confirm_password: '' })
    passwordVisible.value = true
    return
  }
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定退出当前账号吗？', '退出登录', { type: 'warning' })
      await auth.logout()
      ElMessage.success('已退出登录')
      router.replace('/login')
    } catch (e) { if (e !== 'cancel') console.warn(e) }
  }
}

async function changePassword() {
  if (!passwordForm.old_password || !passwordForm.new_password) { ElMessage.warning('请填写当前密码和新密码'); return }
  if (passwordForm.new_password.length < 8) { ElMessage.warning('新密码至少 8 位'); return }
  if (passwordForm.new_password !== passwordForm.confirm_password) { ElMessage.warning('两次输入的新密码不一致'); return }
  passwordSaving.value = true
  try {
    await http.post('/auth/change-password', { old_password: passwordForm.old_password, new_password: passwordForm.new_password })
    passwordVisible.value = false
    ElMessage.success('密码修改成功')
  } catch (e) { ElMessage.error(e.message) } finally { passwordSaving.value = false }
}

onMounted(async () => {
  try { await auth.fetchMe() } catch {}
  await loadLibraries()
})
</script>
