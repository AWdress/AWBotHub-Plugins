<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'

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
  <div class="ssd">
    <div class="tabs" aria-label="SSD 助手页面">
      <button type="button" :class="['tab', { on: tab === 'settings' }]" :aria-pressed="tab === 'settings'" @click="switchTab('settings')">功能设置</button>
      <button type="button" :class="['tab', { on: tab === 'history' }]" :aria-pressed="tab === 'history'" @click="switchTab('history')">执行记录</button>
    </div>
    <div v-if="tab === 'settings'">
      <p v-if="loading" class="muted" role="status">正在读取配置…</p>
      <div v-else-if="loadError" class="error-box" role="alert">
        <p>{{ loadError }}。为保护原设置，读取成功前不能保存。</p>
        <button type="button" class="btn" @click="loadConfig">重新读取配置</button>
      </div>
      <form v-else @submit.prevent="save">
        <fieldset :disabled="!ready || saving">
          <section class="section" aria-labelledby="ssd-lottery-title">
            <div class="section-head"><h3 id="ssd-lottery-title">自动参与抽奖</h3><label class="toggle"><input v-model="cfg.lottery_enabled" type="checkbox" aria-label="开启自动参与抽奖" /><span>{{ cfg.lottery_enabled ? '开启' : '关闭' }}</span></label></div>
            <div class="field range-field" role="group" aria-labelledby="ssd-lottery-delay-label"><span id="ssd-lottery-delay-label">参与前随机等待</span><span class="number-field"><input v-model.number="cfg.lottery_delay_min_seconds" type="number" min="0" max="60" step="0.1" aria-label="最短等待" aria-describedby="ssd-lottery-help" /><span>～</span><input v-model.number="cfg.lottery_delay_max_seconds" type="number" min="0" max="60" step="0.1" aria-label="最长等待" aria-describedby="ssd-lottery-help" /><span>秒</span></span></div>
            <p id="ssd-lottery-help" class="tip">发送一次参与口令，发完即结束。</p>
          </section>
          <section class="section" aria-labelledby="ssd-transfer-title">
            <h3 id="ssd-transfer-title">自动确认转账</h3>
            <div class="control-line">
              <label class="field" for="ssd-transfer-mode"><span>确认方式</span><select id="ssd-transfer-mode" v-model="cfg.ssd_click_mode" aria-describedby="ssd-transfer-help"><option v-for="mode in MODES" :key="mode.value" :value="mode.value">{{ mode.label }}</option></select></label>
              <label class="field" for="ssd-confirm-delay"><span>点击前等待</span><span class="number-field"><input id="ssd-confirm-delay" v-model.number="cfg.confirm_delay_seconds" type="number" min="0" max="10" step="0.1" aria-describedby="ssd-transfer-help" /><span>秒</span></span></label>
            </div>
            <p id="ssd-transfer-help" class="tip">只确认本人转账，不发起转账。</p>
            <p v-if="cfg.ssd_click_mode === '5min'" class="warning" role="note">后续 5 分钟转账可能不再提示确认。</p>
          </section>
        </fieldset>
        <details class="help"><summary>使用说明</summary><div class="help-content">
          <p>使用平台已登录的 Telegram 用户账号，不是 Bot。仅监听 SSD 两个内置群（-1002014253433、-1001173590111）的官方机器人（752250569），无需填写凭据。</p>
          <p>两个功能默认关闭，不自动迁移旧开关。多站点转账保留成功回执记账和排行榜，不再自动确认。</p>
          <p>抽奖原文口令不加零宽字符。为避免误触发命令或转账，跳过 / 开头、+固定金额、+随机金额范围的口令。</p>
          <p>不跟踪开奖或中奖，不自动领奖；保留防重记录。同一抽奖及转账确认不会重复执行；发送或点击结果不明确时不自动重试。转账结果以官方机器人回执为准。</p>
          <p>参与前默认随机等待 2～5 秒（范围 0～60 秒）；确认等待默认 0.5 秒（0～10 秒）。</p>
        </div></details>
        <div class="savebar"><p v-if="formError" class="error" role="alert">{{ formError }}</p><p v-else class="save-result" role="status">{{ saveResult }}</p><button type="submit" class="btn primary" :disabled="saving || !ready || !!formError">{{ saving ? '正在保存…' : '保存配置' }}</button></div>
      </form>
    </div>
    <div v-else class="history-pane">
      <div class="toolbar"><label class="filter" for="ssd-history-filter"><span>记录类型</span><select id="ssd-history-filter" v-model="historyFilter"><option value="all">全部</option><option value="lottery">自动参与抽奖</option><option value="transfer">自动确认转账</option></select></label><button type="button" class="btn" :disabled="historyLoading" @click="loadHistory">{{ historyLoading ? '读取中…' : '刷新记录' }}</button></div>
      <p class="tip">最近 100 条；结果以官方机器人为准。</p>
      <p v-if="runtime" class="tip">运行中：抽奖{{ runtime.lottery_enabled ? '开启' : '关闭' }} · 转账{{ runtime.ssd_click_mode === 'off' ? '关闭' : MODES.find(item => item.value === runtime.ssd_click_mode)?.label || '未知' }}</p>
      <p v-if="historyLoading" class="muted" role="status">正在读取执行记录…</p>
      <p v-else-if="historyError" class="error" role="alert">{{ historyError }}</p>
      <div v-else-if="!visibleHistory.length" class="empty"><h3>{{ history.length ? '此类型暂无记录' : '暂无执行记录' }}</h3><p>{{ history.length ? '可切换记录类型查看其他操作。' : '开启功能并收到符合条件的新消息后，执行过程会显示在这里。' }}</p></div>
      <ol v-else class="records">
        <li v-for="(item, index) in visibleHistory" :key="item.key || `${item.kind}-${item.chat_id}-${item.message_id}-${index}`" class="record">
          <div class="record-head"><strong>{{ item.kind === 'lottery' ? '自动参与抽奖' : '自动确认转账' }}<span v-if="item.lottery_id" class="lottery-id"> · {{ item.lottery_id }}</span></strong><span :class="['record-status', { warning: ['uncertain', 'failed'].includes(item.status) }]">{{ statusText(item) }}</span></div>
          <p class="record-detail">{{ item.detail || '暂无补充说明' }}</p>
          <div class="record-meta"><span>群 {{ item.chat_id }} · 消息 {{ item.message_id }}</span><time>{{ formatTime(item.updated_at || item.created_at) }}</time></div>
        </li>
      </ol>
    </div>
  </div>
</template>

<style scoped>
.ssd { color: var(--text-primary, #e8ebf0); font-size: 13px; line-height: 1.6; container-type: inline-size; }
.ssd *, .ssd *::before, .ssd *::after { box-sizing: border-box; }
.ssd ::selection { color: var(--text-primary, #e8ebf0); background: var(--accent-dim, #1e3a5f); }
p { margin: 0; overflow-wrap: anywhere; }
.tabs { display: flex; gap: 6px; border-bottom: 1px solid var(--border-light, #2a2e3a); }
.tab { padding: 9px 16px; background: transparent; border: 0; border-bottom: 2px solid transparent; color: var(--text-secondary, #b9c0cc); cursor: pointer; }
.tab.on { color: var(--accent, #6ea8fe); border-bottom-color: var(--accent, #6ea8fe); }
button, input, select { font: inherit; }
button:focus-visible, input:focus-visible, select:focus-visible, summary:focus-visible { outline: 2px solid var(--accent, #6ea8fe); outline-offset: 3px; }
button:disabled, fieldset:disabled { opacity: .55; }
button:disabled { cursor: not-allowed; }
fieldset { min-width: 0; margin: 0; padding: 0; border: 0; }
.section { display: flex; flex-direction: column; gap: 10px; padding: 18px 0; border-bottom: 1px solid var(--border-light, #2a2e3a); }
.section-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
h3 { font-size: 15px; font-weight: 600; margin: 0; }
.tip, .save-result, .record-meta { color: var(--text-muted, #a3acbb); font-size: 12px; }
.tip { max-width: 75ch; }
.toggle { display: flex; align-items: center; gap: 7px; color: var(--text-secondary, #b9c0cc); }
input[type='checkbox'] { margin: 0; flex: 0 0 auto; accent-color: var(--accent, #6ea8fe); }
.control-line { display: flex; align-items: center; flex-wrap: wrap; gap: 10px 24px; }
.field { display: flex; align-items: center; gap: 12px; }
.field > span:first-child { flex: 0 0 76px; color: var(--text-secondary, #b9c0cc); }
.range-field { flex-wrap: wrap; gap: 8px 12px; }
.range-field > span:first-child { flex: 0 0 auto; }
.range-field .number-field input { width: 70px; }
input[type='number'], select { padding: 8px 10px; background: var(--bg-card, #12141c); border: 1px solid var(--border-light, #2a2e3a); border-radius: var(--radius-sm, 6px); color: var(--text-primary, #e8ebf0); min-width: 0; max-width: 100%; caret-color: var(--accent, #6ea8fe); }
select { min-width: 160px; }
.number-field { display: inline-flex; align-items: center; gap: 9px; }
.number-field input { width: 80px; font-variant-numeric: tabular-nums; }
.help { padding: 14px 0 0; color: var(--text-secondary, #b9c0cc); font-size: 12px; }
.help summary { cursor: pointer; width: fit-content; }
.help summary:hover { color: var(--accent, #6ea8fe); }
.help-content { display: flex; flex-direction: column; gap: 8px; max-width: 75ch; margin-top: 10px; }
.warning { color: var(--danger, #ff8585); font-size: 12px; }
.savebar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-top: 16px; }
.savebar p { flex: 1; }
.btn { padding: 8px 14px; border-radius: var(--radius-sm, 6px); background: var(--bg-elevated, #1a1d27); border: 1px solid var(--border-light, #2a2e3a); color: var(--text-secondary, #b9c0cc); cursor: pointer; }
.btn:hover:not(:disabled), .tab:hover { color: var(--accent, #6ea8fe); }
.btn:hover:not(:disabled) { border-color: var(--accent, #6ea8fe); }
.btn.primary { color: var(--accent, #6ea8fe); border-color: var(--accent, #6ea8fe); background: var(--accent-dim, #1e3a5f); }
.error { color: var(--danger, #ff8585); font-size: 12px; }
.error-box { display: flex; flex-direction: column; align-items: flex-start; gap: 12px; padding: 18px 0; color: var(--danger, #ff8585); }
.muted { color: var(--text-muted, #a3acbb); padding: 18px 0; }
.history-pane { display: flex; flex-direction: column; gap: 14px; padding-top: 20px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.filter { display: flex; align-items: center; gap: 12px; color: var(--text-secondary, #b9c0cc); }
.filter select { min-width: 140px; }
.empty { text-align: center; padding: 36px 8px; color: var(--text-secondary, #b9c0cc); }
.empty p { font-size: 12px; margin-top: 8px; }
.records { margin: 0; padding: 0; list-style: none; }
.record { padding: 16px 0; border-top: 1px solid var(--border-light, #2a2e3a); }
.record-head { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 6px 16px; }
.record-head strong { font-weight: 600; }
.lottery-id { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-weight: 400; }
.record-status { color: var(--accent, #6ea8fe); font-size: 12px; }
.record-status.warning { color: var(--danger, #ff8585); }
.record-detail { margin: 6px 0 8px; color: var(--text-secondary, #b9c0cc); white-space: pre-wrap; max-width: 75ch; }
.record-meta { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 4px 16px; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
@container (max-width: 480px) { .control-line { align-items: flex-start; flex-direction: column; } .control-line .field { width: 100%; } .field select { flex: 1; min-width: 0; } .toolbar { align-items: stretch; } .filter { flex: 1 1 100%; } .filter select { flex: 1; } .savebar .btn { min-width: 116px; } }
</style>
