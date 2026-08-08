import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'
import DashboardView from '../views/DashboardView.vue'
import LibraryView from '../views/LibraryView.vue'
import DatasetView from '../views/DatasetView.vue'
import ImportHistoryView from '../views/ImportHistoryView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
      children: [
        { path: '', name: 'dashboard', component: DashboardView },
        { path: 'libraries/:id', name: 'library', component: LibraryView },
        { path: 'datasets/:id', name: 'dataset', component: DatasetView },
        { path: 'imports', name: 'imports', component: ImportHistoryView }
      ]
    }
  ]
})

export default router
