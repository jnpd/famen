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
        <router-link class="nav-item workbench-nav" :class="{ active: route.name === 'workbench' }" to="/workbench">
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

        <div class="nav-divider"></div>
        <router-link class="nav-item" :class="{ active: route.name === 'imports' }" to="/imports">
          <el-icon><Clock /></el-icon><span>导入记录</span>
        </router-link>
      </nav>

      <div class="sidebar-note">
        <div class="note-title">专业阀门行业知识沉淀</div>
        <div class="note-text">把散落 Excel 统一变成可检索、可维护、可复用的工程数字库。</div>
        <div class="note-version">版本：v1.0.0</div>
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
          <div class="admin-avatar">A</div>
          <span class="admin-name">管理员</span>
          <el-icon><ArrowDown /></el-icon>
        </div>
      </header>
      <main class="main-content">
        <router-view @refresh-libraries="loadLibraries" />
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  Bell,
  Clock,
  Collection,
  DataAnalysis,
  FolderOpened,
  House,
  Menu,
  Operation,
  QuestionFilled,
  Search,
  Setting,
  TrendCharts
} from '@element-plus/icons-vue'
import http from '../api/http.js'

const route = useRoute()
const router = useRouter()
const libraries = ref([])

const basicLibraries = computed(() => libraries.value.filter(x => x.type === 'dictionary'))
const engineeringLibraries = computed(() => libraries.value.filter(x => x.type !== 'dictionary'))

const pageTitle = computed(() => {
  if (route.name === 'dashboard') return '知识库总览'
  if (route.name === 'workbench') return '参数生成工作台'
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
  } catch (e) {
    console.error(e)
  }
}

function goLibrary(id) {
  router.push({ name: 'library', params: { id } })
}

onMounted(loadLibraries)
</script>

<style scoped>
.workbench-nav { margin-top: 4px; }
</style>
