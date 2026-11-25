<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

const props = defineProps({
  pluginId: { type: String, required: true },
  host: { type: Object, required: true },
})
const DEFAULTS = {
  lottery_enabled: false,
  lottery_delay_min_seconds: 2,
  lottery_delay_max_seconds: 5,
  ssd_click_mode: 'off',
  confirm_delay_seconds: 0.5,
}
const MODES = [
  { value: 'off', label: '关闭（默认）' },
  { value: 'once', label: '单次确认' },
  { value: '5min', label: '5 分钟免确认' },
]
const cfg = reactive({ ...DEFAULTS })
const tab = ref('settings')
const loading = ref(true)
const ready = ref(false)
const saving = ref(false)
const loadError = ref('')
const saveResult = ref('')
watch(cfg, () => { saveResult.value = '' }, { deep: true, flush: 'sync' })
const historyLoading = ref(false)
const historyLoaded = ref(false)
const historyError = ref('')
const history = ref([])
const historyFilter = ref('all')
const runtime = ref(null)
const visibleHistory = computed(() => history.value.filter(item => historyFilter.value === 'all' || item.kind === historyFilter.value))
const formError = computed(() => {
  const lotteryMin = Number(cfg.lottery_delay_min_seconds)
  const lotteryMax = Number(cfg.lottery_delay_max_seconds)
  const confirm = Number(cfg.confirm_delay_seconds)
  if ([cfg.lottery_delay_min_seconds, cfg.lottery_delay_max_seconds].some(value => value == null || String(value).trim() === '' || !Number.isFinite(Number(value)) || Number(value) < 0 || Number(value) > 60)) return '最短和最长等待请填写 0～60 秒。'
  if (lotteryMin > lotteryMax) return '最短等待不能大于最长等待。'
  if (cfg.confirm_delay_seconds === '' || !Number.isFinite(confirm) || confirm < 0 || confirm > 10) return '确认等待时间请填写 0～10 秒。'
  if (!MODES.some(item => item.value === cfg.ssd_click_mode)) return '请选择有效的自动确认方式。'
  return ''
})
function errorText(error) { return String(error?.message || error || '未知错误') }
function asBoolean(value) { return value === true || value === 1 || typeof value === 'string' && value.trim().toLowerCase() === 'true' }

async function loadConfig() {
  if (saving.value) return
  loading.value = true
  ready.value = false
  loadError.value = ''
  try {
    const saved = await props.host.getConfig()
    if (saved != null && (typeof saved !== 'object' || Array.isArray(saved))) throw new Error('配置格式不正确')
    Object.assign(cfg, DEFAULTS, saved || {})
    if (saved && Object.hasOwn(saved, 'lottery_delay_seconds') && !Object.hasOwn(saved, 'lottery_delay_min_seconds') && !Object.hasOwn(saved, 'lottery_delay_max_seconds')) {
      cfg.lottery_delay_min_seconds = saved.lottery_delay_seconds
      cfg.lottery_delay_max_seconds = saved.lottery_delay_seconds
    }
    delete cfg.lottery_delay_seconds
    cfg.lottery_enabled = asBoolean(cfg.lottery_enabled)
    ready.value = true
  } catch (error) {
    loadError.value = '读取配置失败：' + errorText(error)
    props.host.toast.error(loadError.value)
  } finally { loading.value = false }
}
async function save() {
  if (!ready.value || saving.value) return
  saveResult.value = ''
  if (formError.value) { props.host.toast.error(formError.value); return }
  saving.value = true
  try {
    const values = {
      lottery_enabled: cfg.lottery_enabled,
      lottery_delay_min_seconds: Number(cfg.lottery_delay_min_seconds),
      lottery_delay_max_seconds: Number(cfg.lottery_delay_max_seconds),
      ssd_click_mode: cfg.ssd_click_mode,
      confirm_delay_seconds: Number(cfg.confirm_delay_seconds),
    }
    await props.host.saveConfig(values)
    saveResult.value = '配置已保存'
    props.host.toast.success(saveResult.value)
  } catch (error) {
    saveResult.value = '保存失败：' + errorText(error)
    props.host.toast.error(saveResult.value)
  } finally { saving.value = false }
}
async function loadHistory() {
  if (historyLoading.value) return
  historyLoading.value = true
  historyError.value = ''
  try {
    const result = await props.host.callApi('/history')
    if (!Array.isArray(result?.items)) throw new Error('记录格式不正确')
    history.value = result.items.slice(0, 100)
    historyLoaded.value = true
    try { runtime.value = await props.host.callApi('/status') } catch { runtime.value = null }
  } catch (error) {
    historyError.value = '读取记录失败：' + errorText(error) + '。请点击“刷新记录”重试。'
    props.host.toast.error(historyError.value)
  } finally { historyLoading.value = false }
}
function switchTab(value) {
  tab.value = value
  if (value === 'history' && !historyLoaded.value) loadHistory()
}
function statusText(item) {
  const names = { prepared: '已登记，待核对', sent: '口令已发送', clicked: '确认已点击', uncertain: '结果待核对', failed: '执行失败', skipped: '已跳过' }
  return names[item.status] || String(item.status || '未知状态')
}
function formatTime(value) {
  if (!value) return '时间未知'
  const date = typeof value === 'number' ? new Date(value < 1e12 ? value * 1000 : value) : new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('zh-CN', { hour12: false })
}
onMounted(loadConfig)
</script>

<template>
  <IosSettings>
  <div class="ssd">
    <div class="ssd-tabs" :style="{ '--ssd-tab-index': tab === 'settings' ? 0 : 1 }" aria-label="SSD 助手页面">
      <button type="button" :class="['ssd-tab', { on: tab === 'settings' }]" :aria-pressed="tab === 'settings'" @click="switchTab('settings')"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h9m4 0h3M4 17h3m4 0h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/></svg>功能设置</button>
      <button type="button" :class="['ssd-tab', { on: tab === 'history' }]" :aria-pressed="tab === 'history'" @click="switchTab('history')"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 5h14v15H5zM9 3v4m6-4v4M9 11h6m-6 4h4"/></svg>执行记录</button>
    </div>
    <div v-if="tab === 'settings'" class="ssd-settings">
      <p v-if="loading" class="ssd-loading" role="status">正在读取配置…</p>
      <div v-else-if="loadError" class="ssd-error-box" role="alert">
        <p>{{ loadError }}。为保护原设置，读取成功前不能保存。</p>
        <button type="button" class="ssd-button" @click="loadConfig">重新读取配置</button>
      </div>
      <form v-else @submit.prevent="save">
        <fieldset :disabled="!ready || saving">
          <section class="ssd-section" aria-labelledby="ssd-lottery-title">
            <div class="ssd-section-head"><div><h3 id="ssd-lottery-title">自动参与抽奖</h3><p id="ssd-lottery-help" class="ssd-tip">发送一次参与口令，发完即结束。</p></div><label class="ssd-lottery-toggle"><input v-model="cfg.lottery_enabled" class="ssd-lottery-toggle-input" type="checkbox" role="switch" aria-label="开启自动参与抽奖" /><span class="ssd-lottery-toggle-track" aria-hidden="true"></span><span class="ssd-lottery-toggle-state">{{ cfg.lottery_enabled ? '开启' : '关闭' }}</span></label></div>
            <div class="ssd-field ssd-range-field" role="group" aria-labelledby="ssd-lottery-delay-label"><div class="ssd-field-label"><span id="ssd-lottery-delay-label">参与前随机等待</span><span class="ssd-field-note">默认 2～5 秒，最多 60 秒</span></div><span class="ssd-number-field"><input v-model.number="cfg.lottery_delay_min_seconds" type="number" min="0" max="60" step="0.1" aria-label="最短等待" aria-describedby="ssd-lottery-help" /><span>～</span><input v-model.number="cfg.lottery_delay_max_seconds" type="number" min="0" max="60" step="0.1" aria-label="最长等待" aria-describedby="ssd-lottery-help" /><span>秒</span></span></div>
          </section>
          <section class="ssd-section" aria-labelledby="ssd-transfer-title">
            <div class="ssd-section-head"><div><h3 id="ssd-transfer-title">自动确认转账</h3><p id="ssd-transfer-help" class="ssd-tip">只确认本人转账，不发起转账。</p></div><span class="ssd-mode-state" :class="{ on: cfg.ssd_click_mode !== 'off' }">{{ cfg.ssd_click_mode === 'off' ? '已关闭' : '已开启' }}</span></div>
            <label class="ssd-field" for="ssd-transfer-mode"><span class="ssd-field-label">确认方式</span><select id="ssd-transfer-mode" v-model="cfg.ssd_click_mode" aria-describedby="ssd-transfer-help"><option v-for="mode in MODES" :key="mode.value" :value="mode.value">{{ mode.label }}</option></select></label>
            <label class="ssd-field" for="ssd-confirm-delay"><span class="ssd-field-label">点击前等待<span class="ssd-field-note">默认 0.5 秒，最多 10 秒</span></span><span class="ssd-number-field"><input id="ssd-confirm-delay" v-model.number="cfg.confirm_delay_seconds" type="number" min="0" max="10" step="0.1" aria-describedby="ssd-transfer-help" /><span>秒</span></span></label>
            <p v-if="cfg.ssd_click_mode === '5min'" class="ssd-warning" role="note">后续 5 分钟转账可能不再提示确认。</p>
          </section>
        </fieldset>
        <details class="ssd-help"><summary><span>使用说明</span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7"/></svg></summary><div class="ssd-help-content">
          <p>使用平台已登录的 Telegram 用户账号，不是 Bot。仅监听 SSD 两个内置群（-1002014253433、-1001173590111）的官方机器人（752250569），无需填写凭据。</p>
          <p>两个功能默认关闭，不自动迁移旧开关。多站点转账保留成功回执记账和排行榜，不再自动确认。</p>
          <p>抽奖原文口令不加零宽字符。为避免误触发命令或转账，跳过 / 开头、+固定金额、+随机金额范围的口令。</p>
          <p>不跟踪开奖或中奖，不自动领奖；保留防重记录。同一抽奖及转账确认不会重复执行；发送或点击结果不明确时不自动重试。转账结果以官方机器人回执为准。</p>
          <p>参与前默认随机等待 2～5 秒（范围 0～60 秒）；确认等待默认 0.5 秒（0～10 秒）。</p>
        </div></details>
        <div class="ssd-savebar"><p v-if="formError" class="ssd-error" role="alert">{{ formError }}</p><p v-else class="ssd-save-result" role="status">{{ saveResult }}</p><button type="submit" class="ssd-button ssd-primary" :disabled="saving || !ready || !!formError">{{ saving ? '正在保存…' : '保存配置' }}</button></div>
      </form>
    </div>
    <div v-else class="ssd-history-pane">
      <div class="ssd-toolbar"><label class="ssd-filter" for="ssd-history-filter"><span>记录类型</span><select id="ssd-history-filter" v-model="historyFilter"><option value="all">全部</option><option value="lottery">自动参与抽奖</option><option value="transfer">自动确认转账</option></select></label><button type="button" class="ssd-button" :disabled="historyLoading" @click="loadHistory"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 11.5-2L20 8M4 16l2.5 3A7 7 0 0 0 18 17"/></svg>{{ historyLoading ? '读取中…' : '刷新记录' }}</button></div>
      <div class="ssd-history-notes"><p class="ssd-tip">最近 100 条；结果以官方机器人为准。</p><p v-if="runtime" class="ssd-tip">运行中：抽奖{{ runtime.lottery_enabled ? '开启' : '关闭' }} · 转账{{ runtime.ssd_click_mode === 'off' ? '关闭' : MODES.find(item => item.value === runtime.ssd_click_mode)?.label || '未知' }}</p></div>
      <p v-if="historyLoading" class="ssd-loading" role="status">正在读取执行记录…</p>
      <p v-else-if="historyError" class="ssd-error-box" role="alert">{{ historyError }}</p>
      <div v-else-if="!visibleHistory.length" class="ssd-empty"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3h8l4 4v14H5V3zM15 3v5h4M9 12h6m-6 4h4"/></svg><h3>{{ history.length ? '此类型暂无记录' : '暂无执行记录' }}</h3><p>{{ history.length ? '可切换记录类型查看其他操作。' : '开启功能并收到符合条件的新消息后，执行过程会显示在这里。' }}</p></div>
      <ol v-else class="ssd-records">
        <li v-for="(item, index) in visibleHistory" :key="item.key || `${item.kind}-${item.chat_id}-${item.message_id}-${index}`" class="ssd-record">
          <div class="ssd-record-head"><strong>{{ item.kind === 'lottery' ? '自动参与抽奖' : '自动确认转账' }}<span v-if="item.lottery_id" class="ssd-lottery-id"> · {{ item.lottery_id }}</span></strong><span :class="['ssd-record-status', { 'ssd-status-warning': ['uncertain', 'failed'].includes(item.status) }]">{{ statusText(item) }}</span></div>
          <p class="ssd-record-detail">{{ item.detail || '暂无补充说明' }}</p>
          <div class="ssd-record-meta"><span>群 {{ item.chat_id }} · 消息 {{ item.message_id }}</span><time>{{ formatTime(item.updated_at || item.created_at) }}</time></div>
        </li>
      </ol>
    </div>
  </div>
  </IosSettings>
</template>

<style scoped>
.ssd { min-width: 0; color: var(--ios-text); }
.ssd p { margin: 0; overflow-wrap: anywhere; }
.ssd svg { width: 19px; height: 19px; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; flex: none; }
.ssd h3 { margin: 0; font-size: 16px; font-weight: 650; line-height: 1.5; letter-spacing: -.015em; }
.ssd-tabs { position: relative; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); isolation: isolate; gap: 4px; padding: 4px; margin-bottom: 24px; background: var(--ios-inset); border: 1px solid var(--ios-line); border-radius: 16px; }
.ssd-tabs::before { content: ''; position: absolute; inset: 4px auto 4px 4px; width: calc((100% - 12px) / 2); border-radius: 11px; background: var(--ios-control); box-shadow: 0 2px 5px rgb(0 0 0 / .08); transform: translateX(calc(var(--ssd-tab-index) * (100% + 4px))); transition: transform var(--ios-duration) var(--ios-ease); z-index: -1; }
.ssd-tab { display: inline-flex; justify-content: center; align-items: center; gap: 8px; min-height: 42px; padding: 8px 12px; border: 0; border-radius: 11px; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.ssd-tab.on { color: var(--ios-text); font-weight: 650; }
.ssd-tab:hover { color: var(--ios-text); }
.ssd fieldset { min-width: 0; margin: 0; padding: 0; border: 0; }
.ssd fieldset:disabled { opacity: .65; }
.ssd-section { overflow: hidden; margin-bottom: 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.ssd-section-head { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 20px; }
.ssd-section-head > div { min-width: 0; }
.ssd-tip, .ssd-field-note, .ssd-save-result, .ssd-record-meta { font-size: 12px; line-height: 1.65; color: var(--ios-secondary); }
.ssd-section-head .ssd-tip { margin-top: 4px; }
.ssd-field { display: flex; align-items: center; justify-content: space-between; gap: 16px; min-height: 70px; padding: 15px 20px; border-top: 1px solid var(--ios-line); }
.ssd-field-label { display: flex; flex-direction: column; gap: 3px; min-width: 0; font-weight: 500; }
.ssd-field-note { font-weight: 400; }
.ssd input[type='number'], .ssd select { min-width: 0; max-width: 100%; min-height: 42px; padding: 8px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-text); transition: border-color var(--ios-fast), box-shadow var(--ios-fast); }
.ssd input[type='number']:focus, .ssd select:focus { border-color: var(--accent, #0063dc); }
.ssd select { width: 184px; cursor: pointer; }
.ssd-number-field { display: inline-flex; align-items: center; flex: none; gap: 9px; color: var(--ios-secondary); }
.ssd-number-field input { width: 80px; text-align: center; font-variant-numeric: tabular-nums; }
.ssd-lottery-toggle { position: relative; display: inline-flex; align-items: center; flex: 0 0 auto; gap: 9px; min-height: 44px; margin: 0; white-space: nowrap; color: var(--ios-secondary); cursor: pointer; }
.ssd-lottery-toggle-input { position: absolute; width: 1px; height: 1px; margin: 0; padding: 0; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.ssd-lottery-toggle-track { position: relative; display: inline-block; flex: 0 0 50px; width: 50px; height: 30px; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); transition: background var(--ios-fast) ease, border-color var(--ios-fast) ease; }
.ssd-lottery-toggle-track::after { content: ''; position: absolute; top: 2px; left: 2px; width: 24px; height: 24px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .2); transition: transform var(--ios-duration) var(--ios-ease); }
.ssd-lottery-toggle-input:checked + .ssd-lottery-toggle-track { border-color: transparent; background: var(--ios-accent); }
.ssd-lottery-toggle-input:checked + .ssd-lottery-toggle-track::after { transform: translateX(20px); }
.ssd-lottery-toggle:active .ssd-lottery-toggle-track::after { transform: scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.ssd-lottery-toggle:active .ssd-lottery-toggle-input:checked + .ssd-lottery-toggle-track::after { transform: translateX(20px) scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.ssd-lottery-toggle-input:focus-visible + .ssd-lottery-toggle-track { outline: 3px solid var(--accent, #0063dc); outline-offset: 3px; }
.ssd-lottery-toggle-state { min-width: 2em; font-size: 12px; }
.ssd fieldset:disabled .ssd-lottery-toggle { cursor: not-allowed; }
.ssd-mode-state { flex: none; padding: 4px 9px; border-radius: 8px; color: var(--ios-secondary); background: var(--ios-inset); font-size: 12px; }
.ssd-mode-state.on { color: var(--success, #087758); background: color-mix(in srgb, var(--success, #087758) 12%, transparent); }
.ssd-warning { padding: 12px 20px; color: var(--warning, #926100); background: color-mix(in srgb, var(--warning, #926100) 8%, transparent); border-top: 1px solid var(--ios-line); font-size: 12px; }
.ssd-help { color: var(--ios-secondary); border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); }
.ssd-help summary { display: flex; justify-content: space-between; align-items: center; gap: 16px; min-height: 52px; padding: 13px 20px; list-style: none; cursor: pointer; color: var(--ios-text); }
.ssd-help summary::-webkit-details-marker { display: none; }
.ssd-help summary svg { width: 15px; height: 15px; color: var(--ios-secondary); transition: transform var(--ios-duration) var(--ios-ease); }
.ssd-help[open] summary svg { transform: rotate(90deg); }
.ssd-help-content { display: flex; flex-direction: column; gap: 12px; padding: 0 20px 20px; max-width: 75ch; font-size: 12px; line-height: 1.8; }
.ssd-savebar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; padding-top: 24px; }
.ssd-savebar p { flex: 1; min-width: 0; }
.ssd-button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; padding: 9px 18px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font-weight: 500; cursor: pointer; }
.ssd-button:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.ssd-button:disabled { opacity: .5; }
.ssd-button.ssd-primary { min-width: 132px; border-color: transparent; background: var(--ios-accent); color: #fff; font-weight: 600; }
.ssd-primary:hover:not(:disabled) { filter: brightness(1.08); }
.ssd-error { color: var(--danger, #bd2733); font-size: 12px; }
.ssd-error-box { display: flex; flex-direction: column; align-items: flex-start; gap: 14px; padding: 20px; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-surface); color: var(--danger, #bd2733); }
.ssd-loading { padding: 36px 20px; text-align: center; color: var(--ios-secondary); }
.ssd-history-pane { display: flex; flex-direction: column; gap: 16px; }
.ssd-toolbar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.ssd-filter { display: flex; align-items: center; gap: 12px; color: var(--ios-secondary); }
.ssd-filter select { width: 164px; }
.ssd-history-notes { display: flex; flex-direction: column; gap: 3px; }
.ssd-empty { padding: 40px 24px; text-align: center; background: var(--ios-surface); border: 1px solid var(--ios-line); border-radius: 20px; color: var(--ios-secondary); }
.ssd-empty > svg { display: block; width: 32px; height: 32px; margin: 0 auto 16px; }
.ssd-empty h3 { color: var(--ios-text); }
.ssd-empty p { margin: 7px auto 0; max-width: 40ch; font-size: 12px; }
.ssd-records { margin: 0; padding: 0; list-style: none; overflow: hidden; background: var(--ios-surface); border: 1px solid var(--ios-line); border-radius: 20px; }
.ssd-record { padding: 18px 20px; }
.ssd-record + .ssd-record { border-top: 1px solid var(--ios-line); }
.ssd-record-head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px 16px; }
.ssd-record-head strong { font-weight: 600; min-width: 0; overflow-wrap: anywhere; }
.ssd-lottery-id { font-family: var(--font-mono, ui-monospace, monospace); font-weight: 400; font-size: 12px; }
.ssd-record-status { padding: 3px 8px; border-radius: 7px; color: var(--accent, #0063dc); background: var(--accent-dim, #e8f1ff); font-size: 12px; }
.ssd-record-status.ssd-status-warning { color: var(--danger, #bd2733); background: var(--danger-dim, #ffebed); }
.ssd-record-detail { margin: 10px 0 12px !important; color: var(--ios-secondary); white-space: pre-wrap; max-width: 75ch; }
.ssd-record-meta { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 4px 16px; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
:global(html[data-theme='transparent'] .ssd-section),
:global(html[data-theme='transparent'] .ssd-records),
:global(html[data-theme='transparent'] .ssd-help),
:global(html[data-theme='transparent'] .ssd-empty),
:global(html[data-theme='transparent'] .ssd-error-box) { backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); -webkit-backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); }
@container (max-width: 520px) {
  .ssd-tabs { margin-bottom: 20px; }
  .ssd-section-head { padding: 17px 16px; gap: 12px; }
  .ssd-field { padding: 14px 16px; }
  .ssd-range-field { flex-wrap: wrap; gap: 12px; }
  .ssd-range-field .ssd-field-label { flex: 1 1 100%; }
  .ssd-range-field .ssd-number-field { width: 100%; }
  .ssd-range-field input { flex: 1; width: 0; }
  .ssd select { width: 164px; }
  .ssd-help summary { padding-inline: 16px; }
  .ssd-help-content { padding-inline: 16px; }
  .ssd-toolbar { align-items: stretch; }
  .ssd-filter { flex: 1 1 100%; }
  .ssd-filter select { flex: 1; width: 0; }
  .ssd-toolbar .ssd-button { margin-left: auto; }
  .ssd-savebar { gap: 14px; }
  .ssd-savebar p:not(:empty) { flex: 1 1 100%; }
  .ssd-savebar .ssd-primary { width: 100%; }
  .ssd-record { padding: 16px; }
  .ssd-record-head { align-items: flex-start; }
  .ssd-record-meta { flex-direction: column; }
}
@container (max-width: 340px) {
  .ssd-section-head { flex-wrap: wrap; }
  .ssd-section-head > div { flex: 1 1 100%; }
  .ssd-field { flex-wrap: wrap; }
  .ssd-field > select { width: 100%; }
  .ssd-tab { gap: 6px; padding-inline: 8px; }
}
@media (forced-colors: active) {
  .ssd-lottery-toggle-input { position: static; width: 24px; height: 24px; clip-path: none; }
  .ssd-lottery-toggle-track { display: none; }
  .ssd-tabs::before { border: 2px solid Highlight; }
}
</style>
