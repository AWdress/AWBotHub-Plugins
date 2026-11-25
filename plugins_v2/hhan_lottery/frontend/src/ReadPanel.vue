<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

const props = defineProps({
  pluginId: { type: String, required: true },
  host: { type: Object, required: true },
})

const cfg = reactive({ enabled: true, notify_result: true, page_delay: 1, max_pages: 200 })
const status = ref({
  running: false, phase: 'idle', message: '正在读取状态…', current_page: 0,
  total_pages: 0, processed: 0, started_at: '', finished_at: '', stop_requested: false,
})
const history = ref([])
const loading = ref(true)
const saving = ref(false)
const starting = ref(false)
const deleting = ref(false)
const stopping = ref(false)
const checking = ref(false)
const clearing = ref(false)
const apiError = ref('')
let timer = null

const phaseLabel = computed(() => ({
  idle: '待运行', checking: '检查登录', searching: '查找未读', processing: '处理中',
  completed: '已完成', stopped: '已停止', failed: '运行失败',
}[status.value.phase] || '待运行'))

const progress = computed(() => {
  const total = Number(status.value.total_pages || 0)
  const current = Number(status.value.current_page || 0)
  if (!total) return 0
  return Math.max(0, Math.min(100, Math.round(current / total * 100)))
})

const statusTone = computed(() => {
  if (status.value.running) return 'active'
  if (status.value.phase === 'failed') return 'danger'
  if (status.value.phase === 'completed') return 'success'
  return 'neutral'
})

function iconPath(name) {
  const paths = {
    inbox: '<path d="M4 5.5h16v13H4z"/><path d="M4 14h4l2 2h4l2-2h4"/>',
    play: '<path d="m8 5 11 7-11 7z"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="1"/>',
    shield: '<path d="M12 3 5.5 5.8v5.1c0 4.3 2.8 7.8 6.5 9.1 3.7-1.3 6.5-4.8 6.5-9.1V5.8z"/><path d="m9 12 2 2 4-4"/>',
    trash: '<path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v5m4-5v5"/>',
    refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.1 9a7 7 0 0 1 11.3-2.4L20 9M4 15l2.6 2.4A7 7 0 0 0 17.9 15"/>',
  }
  return paths[name] || ''
}

async function loadStatus() {
  try {
    const result = await props.host.callApi('/read/status', { method: 'POST', body: {} })
    if (!result || typeof result !== 'object' || !Object.hasOwn(result, 'running') || !Object.hasOwn(result, 'phase')) throw new Error('状态接口响应缺少运行字段')
    status.value = result
    apiError.value = ''
  } catch (error) { apiError.value = error?.message || String(error) }
}

async function loadHistory() {
  try { history.value = (await props.host.callApi('/read/history', { method: 'POST', body: {} })).items || [] }
  catch (error) { props.host.toast.error('读取运行记录失败：' + (error.message || error)) }
}

async function save() {
  saving.value = true
  try {
    cfg.page_delay = Math.max(0.2, Math.min(Number(cfg.page_delay) || 1, 10))
    cfg.max_pages = Math.max(1, Math.min(Number(cfg.max_pages) || 200, 1000))
    await props.host.saveConfig({ ...cfg })
    props.host.toast.success('配置已保存')
  } catch (error) {
    props.host.toast.error('保存失败：' + (error.message || error))
  } finally { saving.value = false }
}

async function run() {
  starting.value = true
  try {
    await props.host.saveConfig({ ...cfg })
    const result = await props.host.callApi('/read/run', { method: 'POST', body: {} })
    result.ok ? props.host.toast.success(result.message) : props.host.toast.error(result.message)
    await loadStatus()
  } catch (error) {
    props.host.toast.error('启动失败：' + (error.message || error))
  } finally { starting.value = false }
}

async function runDelete() {
  if (!confirm('确定删除 HHanClub 收件箱中的全部消息吗？\n\n已读和未读消息都会被永久删除，此操作无法撤销。')) return
  deleting.value = true
  try {
    await props.host.saveConfig({ ...cfg })
    const result = await props.host.callApi('/read/delete', { method: 'POST', body: {} })
    result.ok ? props.host.toast.success(result.message) : props.host.toast.error(result.message)
    await loadStatus()
  } catch (error) {
    props.host.toast.error('启动删除失败：' + (error.message || error))
  } finally { deleting.value = false }
}

async function stop() {
  stopping.value = true
  try {
    const result = await props.host.callApi('/read/stop', { method: 'POST', body: {} })
    result.ok ? props.host.toast.success(result.message) : props.host.toast.error(result.message)
    await loadStatus()
  } catch (error) {
    props.host.toast.error('停止失败：' + (error.message || error))
  } finally { stopping.value = false }
}

async function checkCookie() {
  checking.value = true
  try {
    const result = await props.host.callApi('/read/cookie/check')
    result.ok ? props.host.toast.success(result.message) : props.host.toast.error(result.message)
  } catch (error) {
    props.host.toast.error('检查失败：' + (error.message || error))
  } finally { checking.value = false }
}

async function clearHistory() {
  if (!confirm('清空最近运行记录？')) return
  clearing.value = true
  try {
    const result = await props.host.callApi('/read/history/clear', { method: 'POST', body: {} })
    history.value = []
    props.host.toast.success(result.message)
  } catch (error) {
    props.host.toast.error('清空失败：' + (error.message || error))
  } finally { clearing.value = false }
}

function historyStatus(item) {
  return ({ completed: '完成', stopped: '停止', failed: '失败' }[item.status] || item.status)
}

function operationLabel(item) { return item.operation === 'delete' ? '删除' : '已读' }

onMounted(async () => {
  try {
    Object.assign(cfg, await props.host.getConfig() || {})
    await Promise.all([loadStatus(), loadHistory()])
  } catch (error) {
    props.host.toast.error('读取插件数据失败：' + (error.message || error))
  } finally { loading.value = false }
  timer = window.setInterval(async () => {
    const wasRunning = status.value.running
    await loadStatus()
    if (wasRunning && !status.value.running) await loadHistory()
  }, 1500)
})

onBeforeUnmount(() => { if (timer) window.clearInterval(timer) })
</script>

<template>
  <div class="hh-read">
    <div v-if="loading" class="hh-read-skeleton" aria-label="正在加载">
      <span></span><span></span><span></span>
    </div>

    <template v-else>
      <p v-if="apiError" class="hh-read-api-error">无法读取消息管理状态：{{ apiError }}。请检查插件是否完整启动。</p>
      <header class="hh-read-header">
        <div class="hh-read-title-wrap">
          <svg class="hh-read-title-icon" viewBox="0 0 24 24" aria-hidden="true" v-html="iconPath('inbox')"></svg>
          <div>
            <h2>消息管理</h2>
            <p>可以将未读消息批量设为已读，或删除收件箱全部消息。</p>
          </div>
        </div>
        <span class="hh-read-state" :class="statusTone"><i></i>{{ phaseLabel }}</span>
      </header>

      <section class="hh-read-run-area" aria-labelledby="run-heading">
        <div class="hh-read-run-copy">
          <span id="run-heading" class="hh-read-section-label">当前任务</span>
          <strong>{{ status.message }}</strong>
          <span class="hh-read-meta">
            <template v-if="status.total_pages">第 {{ status.current_page }}/{{ status.total_pages }} 页 · </template>
            已处理 {{ status.processed }} 条
          </span>
        </div>
        <div class="hh-read-actions">
          <button v-if="!status.running" class="hh-read-button hh-read-primary" :disabled="starting || !cfg.enabled" @click="run">
            <svg viewBox="0 0 24 24" aria-hidden="true" v-html="iconPath('play')"></svg>
            {{ starting ? '启动中…' : '开始全部已读' }}
          </button>
          <button v-if="!status.running" class="hh-read-button hh-read-danger" :disabled="deleting || !cfg.enabled" @click="runDelete">
            <svg viewBox="0 0 24 24" aria-hidden="true" v-html="iconPath('trash')"></svg>
            {{ deleting ? '启动中…' : '删除全部消息' }}
          </button>
          <button v-else class="hh-read-button hh-read-danger" :disabled="stopping || status.stop_requested" @click="stop">
            <svg viewBox="0 0 24 24" aria-hidden="true" v-html="iconPath('stop')"></svg>
            {{ status.stop_requested ? '等待停止…' : stopping ? '提交中…' : '停止任务' }}
          </button>
          <button class="hh-read-button" :disabled="checking || status.running" @click="checkCookie">
            <svg viewBox="0 0 24 24" aria-hidden="true" v-html="iconPath('shield')"></svg>
            {{ checking ? '检查中…' : '检查 Cookie' }}
          </button>
        </div>
        <div class="hh-read-progress" role="progressbar" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100">
          <span :style="{ transform: `scaleX(${progress / 100})` }"></span>
        </div>
      </section>

      <div class="hh-read-content-grid">
        <section class="hh-read-settings" aria-labelledby="settings-heading">
          <div class="hh-read-section-head">
            <div><h3 id="settings-heading">运行设置</h3><p>开始任务时会先自动保存这些设置。</p></div>
            <button class="hh-read-button hh-read-compact" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
          </div>
          <label class="hh-read-toggle-row">
            <span><b>启用插件</b><small>关闭后不能启动新任务</small></span>
            <input v-model="cfg.enabled" type="checkbox" role="switch" /><span class="hh-read-track" aria-hidden="true"><span></span></span>
          </label>
          <label class="hh-read-toggle-row">
            <span><b>完成后推送结果</b><small>通过平台通知渠道发送处理汇总</small></span>
            <input v-model="cfg.notify_result" type="checkbox" role="switch" /><span class="hh-read-track" aria-hidden="true"><span></span></span>
          </label>
          <div class="hh-read-field-grid">
            <label><span>翻页间隔</span><div class="hh-read-input-unit"><input v-model.number="cfg.page_delay" type="number" min="0.2" max="10" step="0.1" /><em>秒</em></div></label>
            <label><span>最多扫描</span><div class="hh-read-input-unit"><input v-model.number="cfg.max_pages" type="number" min="1" max="1000" /><em>页</em></div></label>
          </div>
          <p class="hh-read-notice"><b>全部已读</b>只处理带 <code>icon-unread.svg</code> 标记的消息；<b>删除全部消息</b>会清空当前收件箱中的已读和未读消息，且无法撤销。</p>
        </section>

        <section class="hh-read-history-area" aria-labelledby="history-heading">
          <div class="hh-read-section-head">
            <div><h3 id="history-heading">最近运行</h3><p>保留最近 20 次处理结果。</p></div>
            <div class="hh-read-head-actions">
              <button class="hh-read-icon-button" title="刷新记录" aria-label="刷新记录" @click="loadHistory">
                <svg viewBox="0 0 24 24" aria-hidden="true" v-html="iconPath('refresh')"></svg>
              </button>
              <button class="hh-read-icon-button hh-read-danger-text" title="清空记录" aria-label="清空记录" :disabled="clearing || !history.length" @click="clearHistory">
                <svg viewBox="0 0 24 24" aria-hidden="true" v-html="iconPath('trash')"></svg>
              </button>
            </div>
          </div>
          <div v-if="!history.length" class="hh-read-empty">
            <svg viewBox="0 0 24 24" aria-hidden="true" v-html="iconPath('inbox')"></svg>
            <b>还没有运行记录</b><span>首次执行后，处理数量和结果会显示在这里。</span>
          </div>
          <div v-else class="hh-read-history-list">
            <article v-for="(item, index) in history" :key="item.time + index" class="hh-read-history-item">
              <span class="hh-read-history-status" :class="item.status">{{ historyStatus(item) }}</span>
              <div><b>{{ operationLabel(item) }} · {{ item.processed }} 条消息</b><span>{{ item.detail }}</span></div>
              <div class="hh-read-history-meta"><time>{{ item.time }}</time><span>{{ item.pages }} 页</span></div>
            </article>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>

.hh-read { display: flex; flex-direction: column; gap: 22px; color: var(--ios-text); container-type: inline-size; }
.hh-read h2, .hh-read h3, .hh-read p { margin: 0; }
.hh-read h2 { color: var(--ios-text); font-size: 22px; line-height: 1.4; font-weight: 650; letter-spacing: -.035em; }
.hh-read h3 { color: var(--ios-text); font-size: 14px; line-height: 1.5; font-weight: 650; }
.hh-read-api-error { padding: 14px 16px; border: 1px solid color-mix(in srgb, var(--danger, #d94a53) 20%, transparent); border-radius: 15px; background: color-mix(in srgb, var(--danger, #d94a53) 7%, transparent); color: var(--danger, #d94a53); font-size: 12px; line-height: 1.75; overflow-wrap: anywhere; }
.hh-read-header, .hh-read-title-wrap, .hh-read-actions, .hh-read-section-head, .hh-read-head-actions, .hh-read-history-meta { display: flex; align-items: center; }
.hh-read-header { justify-content: space-between; gap: 20px; }
.hh-read-title-wrap { min-width: 0; gap: 13px; }
.hh-read-title-icon { flex: 0 0 44px; width: 44px; height: 44px; padding: 10px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-inset); color: var(--ios-accent-text); fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.hh-read-title-wrap p, .hh-read-section-head p { margin-top: 5px; color: var(--ios-secondary); font-size: 11px; line-height: 1.75; }
.hh-read-state { display: inline-flex; align-items: center; flex: 0 0 auto; gap: 7px; padding: 7px 12px; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 11px; line-height: 1.5; }
.hh-read-state i { width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
.hh-read-state.active { color: var(--ios-accent-text); border-color: color-mix(in srgb, var(--ios-accent) 20%, transparent); background: color-mix(in srgb, var(--ios-accent) 7%, transparent); }
.hh-read-state.success { color: var(--success, #28a56a); border-color: color-mix(in srgb, var(--success, #28a56a) 20%, transparent); background: color-mix(in srgb, var(--success, #28a56a) 7%, transparent); }
.hh-read-state.danger { color: var(--danger, #d94a53); border-color: color-mix(in srgb, var(--danger, #d94a53) 20%, transparent); background: color-mix(in srgb, var(--danger, #d94a53) 7%, transparent); }
.hh-read-run-area { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 20px; padding: 22px; border: 1px solid var(--ios-line); border-radius: 24px; background: var(--ios-surface); }
.hh-read-run-copy { display: flex; flex-direction: column; gap: 7px; min-width: 0; }
.hh-read-section-label { color: var(--ios-secondary); font-size: 10px; font-weight: 600; letter-spacing: .03em; }
.hh-read-run-copy strong { color: var(--ios-text); font-size: 16px; font-weight: 600; line-height: 1.6; overflow-wrap: anywhere; }
.hh-read-meta { color: var(--ios-secondary); font-size: 11px; line-height: 1.6; font-variant-numeric: tabular-nums; }
.hh-read-actions { flex-wrap: wrap; justify-content: flex-end; gap: 9px; max-width: 470px; }
.hh-read-button, .hh-read-icon-button { border: 1px solid var(--ios-line); border-radius: 13px; background: var(--ios-control); color: var(--ios-text); font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; transition: border-color var(--ios-fast) ease, color var(--ios-fast) ease, background var(--ios-fast) ease; }
.hh-read-button { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-height: 40px; padding: 9px 14px; }
.hh-read-button svg, .hh-read-icon-button svg, .hh-read-empty svg { width: 17px; height: 17px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.hh-read-button:hover:not(:disabled), .hh-read-icon-button:hover:not(:disabled) { color: var(--ios-accent-text); border-color: color-mix(in srgb, var(--ios-accent) 30%, var(--ios-line)); }
.hh-read-button.hh-read-primary, .hh-read-button.hh-read-primary:hover:not(:disabled) { color: #fff; border-color: transparent; background: var(--ios-accent); }
.hh-read-button.hh-read-danger { color: var(--danger, #d94a53); border-color: color-mix(in srgb, var(--danger, #d94a53) 25%, var(--ios-line)); background: color-mix(in srgb, var(--danger, #d94a53) 7%, transparent); }
.hh-read-button.hh-read-compact { min-height: 36px; padding: 7px 13px; }
.hh-read-button:disabled, .hh-read-icon-button:disabled { opacity: .45; cursor: not-allowed; }
.hh-read-progress { grid-column: 1 / -1; height: 5px; overflow: hidden; border-radius: 999px; background: color-mix(in srgb, var(--ios-text) 9%, transparent); }
.hh-read-progress span { display: block; width: 100%; height: 100%; transform-origin: left center; border-radius: inherit; background: var(--ios-accent); transition: transform var(--ios-duration) var(--ios-ease); }
.hh-read-content-grid { display: grid; grid-template-columns: minmax(0, .85fr) minmax(0, 1.15fr); align-items: start; gap: 18px; }
.hh-read-settings, .hh-read-history-area { min-width: 0; padding: 22px; border: 1px solid var(--ios-line); border-radius: 24px; background: var(--ios-surface); }
.hh-read-section-head { justify-content: space-between; gap: 13px; padding-bottom: 16px; border-bottom: 1px solid var(--ios-line); }
.hh-read-head-actions { gap: 6px; flex-shrink: 0; }
.hh-read-toggle-row { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 17px; min-height: 76px; padding: 15px 0; border-bottom: 1px solid var(--ios-line); cursor: pointer; }
.hh-read-toggle-row > span:first-child { display: grid; min-width: 0; gap: 4px; }
.hh-read-toggle-row b { color: var(--ios-text); font-size: 13px; line-height: 1.5; font-weight: 600; }
.hh-read-toggle-row small { color: var(--ios-secondary); font-size: 11px; line-height: 1.7; }
.hh-read-toggle-row > input { position: absolute; inset-inline-end: 0; width: 50px; height: 30px; margin: 0; opacity: 0; z-index: 2; cursor: pointer; }
.hh-read-track { position: relative; flex: 0 0 50px; width: 50px; height: 30px; padding: 3px; border: 1px solid color-mix(in srgb, var(--ios-text) 5%, transparent); border-radius: 20px; background: color-mix(in srgb, var(--ios-text) 18%, transparent); transition: background var(--ios-duration) var(--ios-ease); }
.hh-read-track > span { display: block; width: 24px; height: 24px; margin: -1px; border-radius: 50%; background: #fff; box-shadow: 0 2px 5px #0002; transition: transform var(--ios-duration) var(--ios-ease); }
.hh-read-toggle-row > input:checked + .hh-read-track { background: var(--ios-accent); }
.hh-read-toggle-row > input:checked + .hh-read-track > span { transform: translateX(20px); }
.hh-read-toggle-row > input:focus-visible + .hh-read-track { outline: 3px solid var(--ios-accent-text); outline-offset: 3px; }
.hh-read-field-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; padding-top: 20px; }
.hh-read-field-grid label { display: grid; min-width: 0; gap: 8px; color: var(--ios-secondary); font-size: 12px; line-height: 1.5; }
.hh-read-input-unit { display: flex; align-items: center; min-width: 0; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-control); }
.hh-read-input-unit:focus-within { outline: 3px solid var(--ios-accent-text); border-color: var(--ios-accent-text); }
.hh-read-input-unit input { width: 100%; min-width: 0; min-height: 42px; padding: 10px 12px; border: 0; border-radius: inherit; background: transparent; color: var(--ios-text); font: inherit; font-size: 13px; font-variant-numeric: tabular-nums; }
.hh-read-input-unit em { padding-right: 12px; color: var(--ios-secondary); font-size: 11px; font-style: normal; }
.hh-read p.hh-read-notice { margin-top: 18px; padding: 13px; border: 1px solid var(--ios-line); border-radius: 13px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 11px; line-height: 1.85; overflow-wrap: anywhere; }
.hh-read-notice b { color: var(--ios-text); font-weight: 600; }
.hh-read-notice code { color: var(--ios-text); font-size: 10px; }
.hh-read-icon-button { display: grid; place-items: center; width: 36px; height: 36px; padding: 0; border-radius: 11px; }
.hh-read-danger-text:hover:not(:disabled) { color: var(--danger, #d94a53); border-color: color-mix(in srgb, var(--danger, #d94a53) 25%, var(--ios-line)); }
.hh-read-history-list { display: flex; flex-direction: column; max-height: 500px; overflow-y: auto; overscroll-behavior: contain; }
.hh-read-history-item { display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: start; gap: 7px 12px; padding: 16px 0; border-bottom: 1px solid var(--ios-line); }
.hh-read-history-item:last-child { border-bottom: 0; padding-bottom: 0; }
.hh-read-history-item > div:nth-child(2) { display: grid; min-width: 0; gap: 4px; }
.hh-read-history-item b { color: var(--ios-text); font-size: 12px; line-height: 1.6; font-weight: 600; }
.hh-read-history-item div > span { color: var(--ios-secondary); font-size: 11px; line-height: 1.7; overflow-wrap: anywhere; }
.hh-read-history-status { min-width: 32px; padding-top: 2px; color: var(--ios-secondary); font-size: 10px; line-height: 1.6; }
.hh-read-history-status.completed { color: var(--success, #28a56a); }
.hh-read-history-status.failed { color: var(--danger, #d94a53); }
.hh-read-history-status.stopped { color: var(--warning, #b58118); }
.hh-read-history-meta { grid-column: 2; justify-content: space-between; gap: 12px; color: var(--ios-secondary); font-size: 10px; line-height: 1.7; font-variant-numeric: tabular-nums; }
.hh-read-history-meta time { overflow-wrap: anywhere; }
.hh-read-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 9px; min-height: 240px; padding: 30px 10px; color: var(--ios-secondary); text-align: center; }
.hh-read-empty svg { width: 26px; height: 26px; margin-bottom: 5px; opacity: .65; }
.hh-read-empty b { color: var(--ios-text); font-size: 13px; font-weight: 600; }
.hh-read-empty span { max-width: 32ch; font-size: 11px; line-height: 1.8; }
.hh-read-skeleton { display: grid; gap: 17px; }
.hh-read-skeleton span { display: block; height: 78px; border: 1px solid var(--ios-line); border-radius: 22px; background: var(--ios-inset); opacity: .65; }
.hh-read-skeleton span:nth-child(2) { height: 130px; }
.hh-read-skeleton span:nth-child(3) { height: 240px; }
:global(html[data-theme='transparent'] .hh-read-run-area),
:global(html[data-theme='transparent'] .hh-read-settings),
:global(html[data-theme='transparent'] .hh-read-history-area) { box-shadow: inset 0 1px 0 color-mix(in srgb, var(--ios-text) 5%, transparent); }
@container (max-width: 820px) {
 .hh-read-content-grid { grid-template-columns: minmax(0, 1fr); }
 .hh-read-run-area { grid-template-columns: minmax(0, 1fr); }
 .hh-read-actions { max-width: none; justify-content: flex-start; }
}
@container (max-width: 450px) {
 .hh-read-header { flex-wrap: wrap; gap: 13px; }
 .hh-read-title-icon { display: none; }
 .hh-read h2 { font-size: 20px; }
 .hh-read-run-area, .hh-read-settings, .hh-read-history-area { padding: 18px; border-radius: 21px; }
 .hh-read-actions .hh-read-button { flex: 1 1 40%; padding-inline: 10px; }
 .hh-read-field-grid { grid-template-columns: minmax(0, 1fr); }
 .hh-read-section-head { align-items: flex-start; }
}

</style>
