<script setup>
import { ref } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'
import LotteryPanel from './LotteryPanel.vue'
import ReadPanel from './ReadPanel.vue'
import BonusPanel from './BonusPanel.vue'
import ActivityPanel from './ActivityPanel.vue'
import CookiePanel from './CookiePanel.vue'

defineProps({ pluginId: { type: String, required: true }, host: { type: Object, required: true } })
const tab = ref('bonus')
</script>

<template>
  <IosSettings>
  <div class="hh-config">
    <nav class="hh-config-tabs" aria-label="插件功能">
      <button :class="{ active: tab === 'bonus' }" @click="tab = 'bonus'">赠豆</button>
      <button :class="{ active: tab === 'activity' }" @click="tab = 'activity'">抢红包/抽奖</button>
      <button :class="{ active: tab === 'lottery' }" @click="tab = 'lottery'">幸运转盘</button>
      <button :class="{ active: tab === 'read' }" @click="tab = 'read'">消息管理</button>
      <button :class="{ active: tab === 'auth' }" @click="tab = 'auth'">登录设置</button>
    </nav>
    <BonusPanel v-if="tab === 'bonus'" :plugin-id="pluginId" :host="host" />
    <ActivityPanel v-else-if="tab === 'activity'" :plugin-id="pluginId" :host="host" />
    <LotteryPanel v-else-if="tab === 'lottery'" :plugin-id="pluginId" :host="host" />
    <ReadPanel v-else-if="tab === 'read'" :plugin-id="pluginId" :host="host" />
    <CookiePanel v-else :plugin-id="pluginId" :host="host" />
  </div>

  </IosSettings>
</template>

<style scoped>
.hh-config { color: var(--ios-text); }
.hh-config-tabs { display: flex; gap: 4px; width: fit-content; max-width: 100%; overflow-x: auto; overscroll-behavior-x: contain; padding: 4px; margin: 0 0 28px; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-inset); scrollbar-width: none; }
.hh-config-tabs::-webkit-scrollbar { display: none; }
.hh-config-tabs button { flex: 1 0 auto; min-height: 40px; padding: 9px 18px; border: 1px solid transparent; border-radius: 13px; background: transparent; color: var(--ios-secondary); font: inherit; font-size: 13px; font-weight: 600; white-space: nowrap; cursor: pointer; transition: background var(--ios-duration) var(--ios-ease), color var(--ios-fast) ease, box-shadow var(--ios-duration) ease; }
.hh-config-tabs button:hover { color: var(--ios-text); }
.hh-config-tabs button.active { background: var(--ios-surface); border-color: var(--ios-line); color: var(--ios-text); box-shadow: 0 2px 6px color-mix(in srgb, var(--ios-text) 6%, transparent); }
@media (max-width: 560px) { .hh-config-tabs { width: 100%; margin-bottom: 22px; } .hh-config-tabs button { padding-inline: 13px; font-size: 12px; } }
@container (max-width: 600px) {
  .hh-config :deep(input:not([type=checkbox]):not([type=radio])), .hh-config :deep(textarea), .hh-config :deep(select) { font-size: 16px; }
}
</style>
