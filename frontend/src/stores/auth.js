import { defineStore } from 'pinia'
import http from '../api/http.js'

const TOKEN_KEY = 'valve_kb_token'
const USER_KEY = 'valve_kb_user'

function readUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: readUser(),
    loading: false
  }),
  getters: {
    isLoggedIn: state => Boolean(state.token),
    displayName: state => state.user?.display_name || state.user?.username || '管理员'
  },
  actions: {
    persist(token, user) {
      this.token = token
      this.user = user
      localStorage.setItem(TOKEN_KEY, token)
      localStorage.setItem(USER_KEY, JSON.stringify(user || null))
    },
    clear() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },
    async login(username, password) {
      this.loading = true
      try {
        const { data } = await http.post('/auth/login', { username, password })
        this.persist(data.access_token, data.user)
        return data.user
      } finally {
        this.loading = false
      }
    },
    async fetchMe() {
      if (!this.token) return null
      const { data } = await http.get('/auth/me')
      this.persist(this.token, data)
      return data
    },
    async logout() {
      try {
        if (this.token) await http.post('/auth/logout')
      } finally {
        this.clear()
      }
    }
  }
})
