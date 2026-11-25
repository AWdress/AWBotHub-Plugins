<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  result: { type: Object, required: true },
  busy: { type: Boolean, default: false },
})
const area = ref(null)
const panel = ref(null)
const copyNotice = ref('')
const rows = computed(() => Math.max(2, Math.min(10,
  String(props.result.message).split('\n').reduce((count, line) => count + Math.max(1, Math.ceil(line.length / 70)), 0))))
let mounted = true
onBeforeUnmount(() => { mounted = false })
onMounted(() => panel.value?.scrollIntoView?.({ block: 'center' }))

async function copy() {
  try {
    if (!navigator.clipboard?.writeText) throw new Error('当前页面不支持自动复制')
    await navigator.clipboard.writeText(props.result.message)
    if (mounted) copyNotice.value = '已复制。'
  } catch {
    if (!mounted) return
    area.value?.focus()
    area.value?.select()
    copyNotice.value = '已选中结果，请使用系统复制菜单或 Ctrl+C 复制。'
  }
}
</script>

<template>
  <section ref="panel" class="result" :class="{ 'result-error': !result.ok }" aria-label="工具执行结果">
    <div class="result-head">
      <h4>{{ result.title }}{{ busy ? '' : result.ok ? ' · 已完成' : ' · 未完成' }}</h4>
      <button type="button" class="button" :disabled="busy" @click="copy">复制结果</button>
    </div>
    <label class="sr-only" for="rp-tool-result">工具执行结果，可选中复制</label>
    <textarea id="rp-tool-result" ref="area" class="result-text" :rows="rows" readonly :value="result.message" />
    <p class="sr-only" role="status">{{ busy ? '正在执行，请稍候。' : result.ok ? '操作已完成，详细结果可在下方查看或复制。' : result.message }}</p>
    <p v-if="copyNotice" class="help" role="status">{{ copyNotice }}</p>
  </section>
</template>

<style scoped>
.result { min-width: 0; padding: 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); color: var(--ios-text); scroll-margin-block: 24px; }
.result-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
h4, p { margin: 0; }
h4 { min-width: 0; font-size: 15px; font-weight: 650; line-height: 1.6; overflow-wrap: anywhere; }
.result-error .result-head { color: var(--danger, #bd2733); }
.button { flex-shrink: 0; min-height: 44px; padding: 10px 16px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font: inherit; font-weight: 500; cursor: pointer; }
.button:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.button:disabled { opacity: .55; cursor: not-allowed; }
.result-text { box-sizing: border-box; width: 100%; min-height: 88px; max-height: 360px; padding: 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-text); font: inherit; line-height: 1.75; white-space: pre-wrap; overflow-wrap: anywhere; resize: vertical; caret-color: var(--accent, #0063dc); scrollbar-width: thin; scrollbar-color: var(--border-light, #b9bec9) transparent; }
.help { margin-top: 8px; color: var(--ios-secondary); font-size: 12px; line-height: 1.75; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip-path: inset(50%); border: 0; white-space: nowrap; }
:global(html[data-theme='transparent'] .print-config .result) { backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); -webkit-backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); }
@container (max-width: 600px) {
  .result { padding: 16px; }
  .result-head { flex-wrap: wrap; align-items: flex-start; gap: 12px; }
  .result-text { font-size: 16px; }
}
</style>
