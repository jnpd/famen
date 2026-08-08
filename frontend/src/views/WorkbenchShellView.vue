<template>
  <div class="compact-workbench-shell"><WorkbenchView /></div>
</template>

<script setup>
import WorkbenchView from './WorkbenchView.vue'
</script>

<style scoped>
.compact-workbench-shell :deep(.workbench-hero){padding:14px 18px}.compact-workbench-shell :deep(.workbench-hero h1){font-size:21px;margin:2px 0 4px}.compact-workbench-shell :deep(.workbench-hero p){font-size:11px;line-height:1.45}.compact-workbench-shell :deep(.hero-count){padding:10px 13px;min-width:110px}.compact-workbench-shell :deep(.hero-count b){font-size:20px}.compact-workbench-shell :deep(.workbench-top){grid-template-columns:minmax(0,1.8fr) minmax(280px,.75fr);gap:10px;margin-top:10px}.compact-workbench-shell :deep(.input-panel),.compact-workbench-shell :deep(.snapshot-panel){padding:13px 15px}.compact-workbench-shell :deep(.panel-title){margin-bottom:10px}.compact-workbench-shell :deep(.input-grid){grid-template-columns:repeat(4,minmax(0,1fr));gap:0 10px}.compact-workbench-shell :deep(.input-grid :deep(.el-form-item)){margin-bottom:9px}.compact-workbench-shell :deep(.snapshot-list){grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.compact-workbench-shell :deep(.snapshot-list div){padding:8px 9px}.compact-workbench-shell :deep(.snapshot-list b){font-size:12px;margin-top:3px}.compact-workbench-shell :deep(.action-row){padding-top:9px}.compact-workbench-shell :deep(.summary-row){gap:10px;margin-top:10px}.compact-workbench-shell :deep(.summary-row>div){padding:10px 13px}.compact-workbench-shell :deep(.result-grid){gap:10px;margin-top:10px}.compact-workbench-shell :deep(.result-panel){padding:0 12px 10px}.compact-workbench-shell :deep(.result-title){min-height:46px;margin-bottom:9px}.compact-workbench-shell :deep(.result-title small){font-size:10px}@media(max-width:1450px){.compact-workbench-shell :deep(.input-grid){grid-template-columns:repeat(3,minmax(0,1fr))}.compact-workbench-shell :deep(.workbench-top){grid-template-columns:1fr}}@media(max-width:900px){.compact-workbench-shell :deep(.input-grid){grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:620px){.compact-workbench-shell :deep(.input-grid){grid-template-columns:1fr}}
</style>
