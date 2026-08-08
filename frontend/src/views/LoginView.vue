<template>
  <div class="login-page">
    <div class="login-brand-panel">
      <div class="login-brand">
        <div class="login-logo"><el-icon><Setting /></el-icon></div>
        <div>
          <div class="login-brand-title">阀门工程知识库平台</div>
          <div class="login-brand-subtitle">Valve Engineering Knowledge Base</div>
        </div>
      </div>

      <div class="login-hero-copy">
        <div class="hero-kicker">ENGINEERING DATA PLATFORM</div>
        <h1>让阀门标准、公式与参数<br />真正沉淀成可复用的数据资产</h1>
        <p>Excel 批量导入 · 动态字段映射 · SQLite 本地存储 · 工程参数快速检索</p>
        <div class="hero-points">
          <div><span>01</span><b>标准数字库</b><small>ASME / API / GB 参数沉淀</small></div>
          <div><span>02</span><b>企业公式库</b><small>设计公式与内部规则统一管理</small></div>
          <div><span>03</span><b>阀门参数库</b><small>不同 Excel 自动生成查询页面</small></div>
        </div>
      </div>

      <div class="login-tech-lines">
        <span class="line l1"></span><span class="line l2"></span><span class="line l3"></span>
        <span class="tech-dot d1"></span><span class="tech-dot d2"></span><span class="tech-dot d3"></span>
      </div>
      <div class="login-copyright">V1.1 · Vue3 + FastAPI + SQLite</div>
    </div>

    <div class="login-form-panel">
      <div class="login-card">
        <div class="login-card-head">
          <div class="mini-logo"><el-icon><Setting /></el-icon></div>
          <div>
            <h2>欢迎登录</h2>
            <p>请输入账号密码进入阀门工程知识库</p>
          </div>
        </div>

        <el-form :model="form" label-position="top" @submit.prevent>
          <el-form-item label="账号">
            <el-input v-model="form.username" size="large" placeholder="请输入用户名" :prefix-icon="User" @keyup.enter="submit" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" size="large" type="password" show-password placeholder="请输入密码" :prefix-icon="Lock" @keyup.enter="submit" />
          </el-form-item>
          <div class="login-options">
            <el-checkbox v-model="remember">记住账号</el-checkbox>
            <span>本地部署版</span>
          </div>
          <el-button class="login-submit" type="primary" size="large" :loading="auth.loading" @click="submit">
            登录系统
          </el-button>
        </el-form>

        <div class="first-login-tip">
          <el-icon><InfoFilled /></el-icon>
          <span>首次启动默认账号 <b>admin</b>，密码 <b>Admin@123456</b>。登录后建议立即修改密码。</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { InfoFilled, Lock, Setting, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth.js'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const remember = ref(true)
const savedUsername = localStorage.getItem('valve_kb_username') || 'admin'
const form = reactive({ username: savedUsername, password: '' })

async function submit() {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  try {
    await auth.login(form.username.trim(), form.password)
    if (remember.value) localStorage.setItem('valve_kb_username', form.username.trim())
    else localStorage.removeItem('valve_kb_username')
    ElMessage.success('登录成功')
    const target = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
      ? route.query.redirect
      : '/'
    router.replace(target)
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>
