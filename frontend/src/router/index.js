import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'
import DashboardView from '../views/DashboardView.vue'
import WorkbenchShellView from '../views/WorkbenchShellView.vue'
import LibraryView from '../views/LibraryView.vue'
import DatasetView from '../views/DatasetView.vue'
import ImportHistoryView from '../views/ImportHistoryView.vue'
import ExcelImportView from '../views/ExcelImportView.vue'
import LoginView from '../views/LoginView.vue'
import DesignResultsView from '../views/DesignResultsView.vue'
import DesignResultDetailView from '../views/DesignResultDetailView.vue'
import StandardsView from '../views/StandardsView.vue'
import StandardDetailView from '../views/StandardDetailView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView, meta: { guest: true } },
    { path: '/', component: MainLayout, meta: { requiresAuth: true }, children: [
      { path: '', name: 'dashboard', component: DashboardView },
      { path: 'workbench', name: 'workbench', component: WorkbenchShellView },
      { path: 'design-results', name: 'designResults', component: DesignResultsView },
      { path: 'design-results/:id', name: 'designResultDetail', component: DesignResultDetailView },
      { path: 'standards', name: 'standards', component: StandardsView },
      { path: 'standards/:id', name: 'standardDetail', component: StandardDetailView },
      { path: 'libraries/:id', name: 'library', component: LibraryView },
      { path: 'datasets/:id', name: 'dataset', component: DatasetView },
      { path: 'excel-import', name: 'excelImport', component: ExcelImportView },
      { path: 'imports', name: 'imports', component: ImportHistoryView }
    ]},
    { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
})

router.beforeEach(to => {
  const token = localStorage.getItem('valve_kb_token')
  if (to.matched.some(r => r.meta.requiresAuth) && !token) return { name: 'login', query: { redirect: to.fullPath } }
  if (to.name === 'login' && token) return { name: 'dashboard' }
  return true
})

export default router
