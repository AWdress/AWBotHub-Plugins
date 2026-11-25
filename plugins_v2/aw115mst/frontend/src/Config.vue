<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import SwitchField from './SwitchField.vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

const props = defineProps({pluginId: {type: String, required: true}, host: {type: Object, required: true}})
const MASK = '********'
const DEFAULTS = Object.freeze({
  cookie: '', target_pid: '0', qr_app: 'qandroid',
  input_dir: '待检测', rapid_dir: '可秒传', non_rapid_dir: '待秒传',
  use_copy: true, keep_structure: true, check_only: false,
  delete_after_rapid: false, delete_source_after_rapid: false,
  upload_enabled: false, delete_after_upload: false,
  include_extensions: '', exclude_extensions: '.txt,.log,.tmp,.part,.crdownload,.!qb,.!ut,.download,.aria2,.mp',
  min_size_mb: 0, max_size_gb: 100, hash_chunk_mb: 1, stable_seconds: 5,
  watch_enabled: false, watch_interval_seconds: 5,
  schedule_enabled: false, interval_minutes: 30,
  recheck_enabled: false, max_recheck_times: 10,
  notify: false, request_timeout: 30, telegram_control: false, telegram_admin_ids: '',
})
const TABS = [{key: 'account', label: '账号'}, {key: 'files', label: '文件规则'}, {key: 'tasks', label: '自动任务'}, {key: 'records', label: '运行记录'}]
const STATES = {rapid: '已秒传', pending: '待重检', non_rapid: '待秒传', local_pending: '待完成本地整理', failed: '处理失败', upload_failed: '上传失败', uploaded: '已上传', processed: '已处理', checking: '检测中', moved: '已整理', skipped: '已跳过', done: '已完成', dispatched: '已暂存，待重检', dispatch_pending: '待暂存整理', uploading: '真实上传中', cloud_unknown: '网盘结果待核对', missing: '本地文件缺失'}
const form = reactive({...DEFAULTS})
const activeTab = ref('account')
const loading = ref(true)
const saving = ref(false)
const busy = ref('')
const loadError = ref('')
const actionError = ref('')
const actionMessage = ref('')
const statusError = ref('')
const savedSnapshot = ref('')
const status = ref(null)
const refreshing = ref(false)
const cookieVisible = ref(false)
const cookieReveal = ref('')
const revealing = ref(false)
const loginResult = ref('')
const actionAlert = ref(null)
const qr = reactive({session: '', image: '', state: '', message: '', expiresAt: 0})
const clearConfirmation = ref(false)
let pollTimer = null
let alive = true
let qrPolling = false

const snapshot = () => JSON.stringify(form)
const dirty = computed(() => !loading.value && snapshot() !== savedSnapshot.value)
const locked = computed(() => saving.value || !!busy.value || loading.value || !!loadError.value)
const hasCookie = computed(() => !!String(form.cookie || '').trim())
const cookieDisplay = computed(() => cookieVisible.value && form.cookie === MASK ? cookieReveal.value : form.cookie)
const items = computed(() => Array.isArray(status.value?.items) ? status.value.items : Array.isArray(status.value?.records) ? status.value.records : [])
const qrActive = computed(() => !!qr.session && ['waiting', 'scanned'].includes(qr.state))
const runProgress = computed(() => {
  const value = status.value?.progress
  if (typeof value === 'number') return Math.max(0, Math.min(100, value))
  const current = Number(value?.done ?? value?.current ?? 0)
  const total = Number(value?.total ?? 0)
  return total > 0 ? Math.max(0, Math.min(100, current * 100 / total)) : null
})

function notify(type, message) { props.host.toast?.[type]?.(message) }
function errorMessage(error) { return error?.message || String(error) }
function tabEnabled(key) {
  if (key === 'account') return Boolean(loginResult.value) || qr.state === 'confirmed'
  if (key === 'files') return form.upload_enabled
  if (key === 'tasks') return form.watch_enabled || form.schedule_enabled || form.telegram_control
  return Boolean(status.value?.running)
}

async function focusActionError() {
  await nextTick()
  if (!alive || !actionAlert.value) return
  actionAlert.value.focus({preventScroll: true})
  actionAlert.value.scrollIntoView({block: 'center', behavior: 'auto'})
}

function validate() {
  for (const [field, label] of [['input_dir', '待检测目录'], ['rapid_dir', '可秒传目录'], ['non_rapid_dir', '待秒传目录']]) {
    if (!String(form[field] || '').trim()) return {message: `${label}不能为空`, tab: 'files'}
  }
  if (new Set([form.input_dir, form.rapid_dir, form.non_rapid_dir].map((value) => value.trim().replace(/[\\/]+$/, '').toLowerCase())).size !== 3) {
    return {message: '三个文件目录必须分别设置，不能使用同一目录', tab: 'files'}
  }
  if (!/^\d+$/.test(String(form.target_pid).trim())) return {message: '115 目标目录 ID 必须是非负整数，根目录填 0', tab: 'account'}
  const ranges = {
    min_size_mb: [0, 102400, '最小文件大小', 'files'], max_size_gb: [0, 102400, '最大文件大小', 'files'],
    hash_chunk_mb: [1, 16, '哈希读取分块', 'files'], stable_seconds: [0, 3600, '文件稳定等待', 'files'],
    watch_interval_seconds: [5, 3600, '目录检查间隔', 'tasks'], interval_minutes: [1, 10080, '定时处理间隔', 'tasks'],
    max_recheck_times: [0, 10000, '最大重检次数', 'tasks'], request_timeout: [5, 300, '请求超时', 'account'],
  }
  for (const [field, [min, max, label, tab]] of Object.entries(ranges)) {
    const value = form[field]
    if (value === '' || value === null || !Number.isFinite(Number(value)) || Number(value) < min || Number(value) > max) {
      return {message: `${label}必须在 ${min} 到 ${max} 之间`, tab}
    }
    if (!Number.isInteger(Number(value))) return {message: `${label}必须是整数`, tab}
  }
  if (form.check_only && (form.delete_after_rapid || form.delete_source_after_rapid || form.delete_after_upload)) return {message: '仅检测模式不能同时开启本地删除，请关闭三个删除开关后再保存', tab: 'files'}
  if (Number(form.max_size_gb) > 0 && Number(form.min_size_mb) > Number(form.max_size_gb) * 1024) return {message: '最小文件大小不能大于最大文件大小', tab: 'files'}
  if (form.telegram_control && !/^\s*\d+(?:[\s,，]+\d+)*\s*$/.test(form.telegram_admin_ids)) return {message: '请填写允许控制的 Telegram 用户 ID，多个 ID 用逗号或换行分隔', tab: 'tasks'}
  return null
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const saved = await props.host.getConfig()
    if (!alive) return
    Object.assign(form, DEFAULTS)
    for (const key of Object.keys(DEFAULTS)) if (saved && Object.hasOwn(saved, key) && saved[key] !== null && saved[key] !== undefined) form[key] = saved[key]
    savedSnapshot.value = snapshot()
  } catch (error) {
    if (alive) loadError.value = `读取配置失败：${errorMessage(error)}。请重新读取后再保存。`
  } finally {
    if (alive) loading.value = false
  }
}

async function save({quiet = false} = {}) {
  if (loadError.value || loading.value) return false
  const problem = validate()
  if (problem) {
    actionError.value = problem.message
    activeTab.value = problem.tab
    await focusActionError()
    return false
  }
  saving.value = true
  actionError.value = ''
  try {
    const payload = JSON.parse(JSON.stringify(form))
    for (const key of Object.keys(DEFAULTS)) {
      if (typeof DEFAULTS[key] === 'number') payload[key] = Number(payload[key])
      if (typeof DEFAULTS[key] === 'boolean') payload[key] = Boolean(payload[key])
    }
    for (const key of ['input_dir', 'rapid_dir', 'non_rapid_dir', 'target_pid']) payload[key] = String(payload[key]).trim()
    const result = await props.host.saveConfig(payload)
    if (result?.ok === false) throw new Error(result.message || '平台未能保存配置')
    if (!alive) return false
    Object.assign(form, payload)
    savedSnapshot.value = snapshot()
    if (!quiet) {
      actionMessage.value = '配置已保存并应用'
      notify('success', actionMessage.value)
    }
    return true
  } catch (error) {
    if (alive) {
      actionError.value = `保存失败：${errorMessage(error)}`
      await focusActionError()
    }
    return false
  } finally {
    if (alive) saving.value = false
  }
}

async function refreshStatus() {
  if (refreshing.value || !alive) return
  refreshing.value = true
  try {
    const result = await props.host.callApi('/status')
    if (result?.ok === false) throw new Error(result.message || '状态暂不可用')
    if (alive) { status.value = result || null; statusError.value = '' }
  } catch (error) {
    if (alive) statusError.value = `读取运行状态失败：${errorMessage(error)}`
  } finally {
    if (alive) { refreshing.value = false; schedulePoll() }
  }
}

async function postAction(name, path, body = {}) {
  if (busy.value || saving.value || loading.value) return null
  busy.value = name
  actionError.value = ''
  actionMessage.value = ''
  try {
    // Saving may reload the plugin. Stop must address the existing worker;
    // clean action requests must not recreate it or invalidate a QR session.
    if (path !== '/stop' && dirty.value && !await save({quiet: true})) return null
    const result = await props.host.callApi(path, {method: 'POST', body})
    if (result?.ok === false) throw new Error(result.message || '操作未成功')
    if (!alive) return null
    actionMessage.value = result?.message || '操作已完成'
    await refreshStatus()
    return result
  } catch (error) {
    if (alive) actionError.value = errorMessage(error)
    return null
  } finally {
    if (alive) busy.value = ''
  }
}

async function revealCookie() {
  if (cookieVisible.value) { cookieVisible.value = false; cookieReveal.value = ''; return }
  revealing.value = true
  try {
    if (form.cookie === MASK) cookieReveal.value = await props.host.revealSecret('cookie') || ''
    if (alive) cookieVisible.value = true
  } catch (error) {
    if (alive) actionError.value = `无法显示 Cookie：${errorMessage(error)}`
  } finally { if (alive) revealing.value = false }
}

async function testLogin() {
  const result = await postAction('login', '/login_test')
  if (result) loginResult.value = result.user_name ? `已连接账号：${result.user_name}` : result.message || '115 登录有效'
}

async function startQr() {
  const result = await postAction('qr', '/qr/start', {app: form.qr_app})
  if (!result) return
  if (!result.session || !result.image) { actionError.value = '未取得二维码，请重试生成'; return }
  Object.assign(qr, {session: result.session, image: result.image, state: 'waiting', message: '使用 115 客户端扫描二维码', expiresAt: Date.now() + Number(result.expires_in || 300) * 1000})
  schedulePoll()
}

async function pollQr() {
  if (!qrActive.value || activeTab.value !== 'account' || busy.value || qrPolling) return
  if (Date.now() >= qr.expiresAt) { qr.state = 'expired'; qr.message = '二维码已过期，请重新生成'; return }
  const session = qr.session
  qrPolling = true
  try {
    const result = await props.host.callApi('/qr/poll', {method: 'POST', body: {session}})
    if (result?.ok === false) throw new Error(result.message || '扫码状态检查失败')
    if (!result || !alive || session !== qr.session) return
    qr.state = result.status || 'waiting'
    qr.message = result.message || ({waiting: '等待扫码', scanned: '已扫码，请在手机上确认', confirmed: '登录已确认', expired: '二维码已过期，请重新生成'}[qr.state] || '等待登录确认')
    if (qr.state === 'confirmed') {
      // Preserve unsaved edits to other fields when the server updates its cookie.
      const wasDirty = dirty.value
      const previousSaved = JSON.parse(savedSnapshot.value || '{}')
      const saved = await props.host.getConfig()
      if (!alive) return
      form.cookie = saved?.cookie || MASK
      cookieVisible.value = false
      cookieReveal.value = ''
      previousSaved.cookie = form.cookie
      savedSnapshot.value = wasDirty ? JSON.stringify(previousSaved) : snapshot()
      loginResult.value = '扫码登录成功，Cookie 已由平台保存'
      await refreshStatus()
    }
  } catch (error) {
    if (alive) qr.message = `检查扫码状态失败：${errorMessage(error)}。稍后自动重试。`
  } finally {
    qrPolling = false
  }
}

function schedulePoll() {
  clearTimeout(pollTimer)
  pollTimer = null
  if (!alive || !(status.value?.running || (activeTab.value === 'account' && qrActive.value))) return
  pollTimer = setTimeout(async () => {
    try {
      if (status.value?.running) await refreshStatus()
      if (activeTab.value === 'account' && qrActive.value) await pollQr()
    } catch (error) {
      if (alive) actionError.value = errorMessage(error)
    } finally { schedulePoll() }
  }, 5000)
}

async function run(mode) {
  const result = await postAction(`run-${mode}`, '/run', {mode})
  if (result) { activeTab.value = 'records'; schedulePoll() }
}
async function clearRecords() {
  const result = await postAction('clear', '/clear_records', {confirm: true})
  if (result) clearConfirmation.value = false
}
function formatBytes(value) {
  const bytes = Number(value)
  if (!Number.isFinite(bytes) || bytes < 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  const unit = Math.min(4, Math.floor(Math.log(bytes) / Math.log(1024)))
  return `${(bytes / 1024 ** unit).toFixed(1)} ${['B', 'KB', 'MB', 'GB', 'TB'][unit]}`
}
function formatTime(value) {
  if (!value) return '—'
  const date = new Date(typeof value === 'number' && value < 1e12 ? value * 1000 : value)
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('zh-CN', {hour12: false})
}
function stateLabel(value) { return STATES[value] || value || '待处理' }
function attentionState(value) { return String(value).includes('fail') || ['cloud_unknown', 'missing'].includes(value) }
function count(key) {
  if (!status.value) return '—'
  const counts = status.value.counts || {}
  if (Object.hasOwn(counts, 'total')) return counts[key] ?? 0
  if (key === 'total') return Object.values(counts).reduce((total, value) => total + (Number(value) || 0), 0)
  if (key === 'pending') return Number(counts.pending || 0) + Number(counts.non_rapid || 0) + Number(counts.local_pending || 0) + Number(counts.dispatched || 0) + Number(counts.dispatch_pending || 0)
  if (key === 'failed') return Number(counts.failed || 0) + Number(counts.upload_failed || 0) + Number(counts.cloud_unknown || 0) + Number(counts.missing || 0)
  if (key === 'rapid') return Number(counts.rapid || 0) + Number(counts.done || 0) + Number(counts.uploaded || 0)
  return 0
}
function tabKeyboard(event, index) {
  const direction = event.key === 'ArrowRight' || event.key === 'ArrowDown' ? 1 : event.key === 'ArrowLeft' || event.key === 'ArrowUp' ? -1 : 0
  if (!direction && !['Home', 'End'].includes(event.key)) return
  event.preventDefault()
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? TABS.length - 1 : (index + direction + TABS.length) % TABS.length
  activeTab.value = TABS[next].key
  nextTick(() => document.getElementById(`mst-tab-${activeTab.value}`)?.focus())
}

watch([activeTab, () => status.value?.running, () => qr.state], schedulePoll)
onMounted(async () => { await load(); if (alive && !loadError.value) await refreshStatus() })
onBeforeUnmount(() => { alive = false; clearTimeout(pollTimer); cookieReveal.value = '' })
</script>

<template>
  <IosSettings>
  <main class="mst-shell">
    <header class="mst-page-head">
      <div><h2>AW115MST</h2><p>115 秒传检测与文件整理</p></div>
      <span class="mst-save-state" :class="{changed: dirty}">{{ saving ? '正在保存' : dirty ? '有未保存修改' : loading ? '正在读取' : loadError ? '读取失败' : '配置已同步' }}</span>
    </header>
    <div v-if="loadError" class="mst-alert mst-error" role="alert"><p>{{ loadError }}</p><button class="mst-secondary" type="button" @click="load">重新读取</button></div>
    <p v-if="actionError" ref="actionAlert" class="mst-alert mst-error" role="alert" tabindex="-1">{{ actionError }}</p>
    <p v-else-if="actionMessage" class="mst-alert mst-success" role="status">{{ actionMessage }}</p>
    <p v-if="loading" class="mst-loading" role="status">正在读取配置…</p>

    <div v-else class="mst-workspace">
      <nav :style="{ '--mst-tab-index': TABS.findIndex(item => item.key === activeTab) }" class="mst-section-nav" role="tablist" aria-label="AW115MST 配置分组">
        <button v-for="(item, index) in TABS" :id="`mst-tab-${item.key}`" :key="item.key" type="button" role="tab" :aria-selected="activeTab === item.key" :aria-controls="`mst-panel-${item.key}`" :tabindex="activeTab === item.key ? 0 : -1" :class="{active: activeTab === item.key}" @click="activeTab = item.key" @keydown="tabKeyboard($event, index)">
          <span>{{ item.label }}</span><i :class="{on: tabEnabled(item.key)}" aria-hidden="true"></i>
        </button>
      </nav>

      <section :id="`mst-panel-${activeTab}`" class="mst-panel" role="tabpanel" :aria-labelledby="`mst-tab-${activeTab}`">
        <fieldset class="mst-fields" :disabled="locked">
          <template v-if="activeTab === 'account'">
            <div class="mst-panel-head"><h3>115 账号</h3><p>使用 Cookie 或扫码连接账号，服务可独立运行。</p></div>
            <div class="mst-subsection">
              <div class="mst-form-grid">
                <label class="mst-wide"><span>115 Cookie</span><div class="mst-secret-field"><input :value="cookieDisplay" :type="cookieVisible ? 'text' : 'password'" autocomplete="off" spellcheck="false" placeholder="留空使用平台 115 Cookie，或在下方扫码登录" @input="form.cookie = $event.target.value"><button type="button" :aria-label="cookieVisible ? '隐藏 Cookie' : '显示 Cookie'" :aria-pressed="cookieVisible" :disabled="revealing || !hasCookie" @click="revealCookie"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12C4.5 7.5 8 5 12 5s7.5 2.5 10 7c-2.5 4.5-6 7-10 7S4.5 16.5 2 12Z"/><circle cx="12" cy="12" r="3"/><path v-if="!cookieVisible" d="m4 3 16 18"/></svg></button></div><small>留空读取平台保存的 115 Cookie；填写后优先使用本插件配置。默认隐藏，点击眼睛可查看。</small></label>
                <label><span>115 目标目录 ID</span><input v-model.trim="form.target_pid" inputmode="numeric"><small>根目录填 0；子目录可从 115 目录链接中查看 ID。</small></label>
                <label><span>请求超时（秒）</span><input v-model.number="form.request_timeout" type="number" min="5" max="300" step="1"></label>
              </div>
              <div class="mst-action-row"><button class="mst-secondary" type="button" :disabled="!!busy" @click="testLogin">{{ busy === 'login' ? '正在检测…' : '检测登录' }}</button><p v-if="loginResult" class="mst-login-result" role="status">{{ loginResult }}</p></div>
            </div>
            <div class="mst-subsection">
              <div class="mst-section-head"><div><h4>扫码登录</h4><p>使用 115 客户端扫描，并在手机上确认登录。</p></div></div>
              <div class="mst-form-grid mst-qr-controls"><label><span>登录客户端</span><select v-model="form.qr_app"><option value="qandroid">115 管理 Android</option><option value="ios">115 生活 iOS</option><option value="web">115 网页端</option></select></label><button class="mst-secondary" type="button" :disabled="!!busy" @click="startQr">{{ busy === 'qr' ? '正在生成…' : qr.session ? '重新生成二维码' : '生成登录二维码' }}</button></div>
              <div v-if="qr.image" class="mst-qr-area"><img :src="qr.image" alt="115 登录二维码" width="192" height="192"><div><b>{{ qr.state === 'confirmed' ? '登录成功' : qr.state === 'scanned' ? '等待手机确认' : qr.state === 'expired' ? '二维码已过期' : '等待扫码' }}</b><p role="status">{{ qr.message }}</p><small>停留在账号页时每 5 秒检查一次扫码状态。</small></div></div>
            </div>
          </template>

          <template v-else-if="activeTab === 'files'">
            <div class="mst-panel-head"><h3>文件规则</h3><p>目录指向服务运行环境；三个目录需独立设置。</p></div>
            <div class="mst-subsection"><div class="mst-form-grid"><label class="mst-wide"><span>待检测目录</span><input v-model.trim="form.input_dir"></label><label><span>可秒传目录</span><input v-model.trim="form.rapid_dir"></label><label><span>待秒传目录</span><input v-model.trim="form.non_rapid_dir"></label></div><p v-if="status?.roots" class="mst-hint mst-root-note">实际目录：{{ typeof status.roots === 'string' ? status.roots : Object.values(status.roots).join(' · ') }}</p></div>
            <div class="mst-subsection mst-switch-list"><SwitchField v-model="form.use_copy" title="复制整理" hint="启用时保留待检测原件；关闭后按移动方式整理。"/><SwitchField v-model="form.keep_structure" title="保留子目录结构" hint="本地整理和 115 目标目录保留相对目录层级。"/><SwitchField v-model="form.check_only" title="仅检测，不整理本地文件" hint="秒传命中会入 115 网盘；仅检测只不改本地文件。"/></div>
            <div class="mst-subsection">
              <div class="mst-section-head"><h4>筛选与文件稳定</h4></div>
              <div class="mst-form-grid">
                <label class="mst-wide"><span>仅包含扩展名</span><input v-model.trim="form.include_extensions" placeholder="留空表示不限；多个扩展名用逗号分隔"><small>例如 .mkv,.mp4；匹配不区分大小写。</small></label>
                <label class="mst-wide"><span>排除扩展名</span><input v-model.trim="form.exclude_extensions"><small>避免处理日志、临时文件和未完成的下载。</small></label>
                <label><span>最小文件大小（MB）</span><input v-model.number="form.min_size_mb" type="number" min="0" max="102400" step="1"></label>
                <label><span>最大文件大小（GB）</span><input v-model.number="form.max_size_gb" type="number" min="0" max="102400" step="1"><small>0 表示不限大小。</small></label>
                <label><span>哈希读取分块（MB）</span><input v-model.number="form.hash_chunk_mb" type="number" min="1" max="16" step="1"></label>
                <label><span>文件稳定等待（秒）</span><input v-model.number="form.stable_seconds" type="number" min="0" max="3600" step="1"></label>
              </div>
            </div>
            <div class="mst-subsection"><div class="mst-section-head"><h4>成功后的本地处理</h4></div><div class="mst-switch-list"><SwitchField v-model="form.delete_after_rapid" title="秒传确认后删除当前处理文件" hint="直接删除当前处理文件，不生成可秒传目录副本。"/><SwitchField v-model="form.delete_source_after_rapid" title="重检入库确认后删除关联输入源文件" hint="仅处理重检记录关联的输入源文件；内容已变化时保留。"/><SwitchField v-model="form.upload_enabled" title="重检达上限后真实上传" hint="秒传仍未命中时上传完整文件，会产生上传流量。"/><SwitchField v-model="form.delete_after_upload" title="真实上传确认后删除当前处理文件" hint="仅在真实上传已确认成功后执行。"/></div></div>
          </template>

          <template v-else-if="activeTab === 'tasks'">
            <div class="mst-panel-head"><h3>自动任务</h3><p>每项任务独立控制，修改后保存即可应用。</p></div>
            <div class="mst-subsection"><SwitchField v-model="form.watch_enabled" title="目录监控（定期检查新文件）" hint="按间隔扫描新文件，并等待文件稳定后处理。"/><div class="mst-form-grid mst-following"><label><span>目录检查间隔（秒）</span><input v-model.number="form.watch_interval_seconds" type="number" min="5" max="3600" step="1"></label></div></div>
            <div class="mst-subsection"><SwitchField v-model="form.schedule_enabled" title="定时处理" hint="按设定间隔检测待检测目录，可同时处理待秒传重检。"/><div class="mst-form-grid mst-following"><label><span>处理间隔（分钟）</span><input v-model.number="form.interval_minutes" type="number" min="1" max="10080" step="1"></label></div></div>
            <div class="mst-subsection"><SwitchField v-model="form.recheck_enabled" title="重检待秒传文件" hint="自动任务中检查已暂存的文件，确认是否能够秒传。"/><div class="mst-form-grid mst-following"><label><span>最大重检次数</span><input v-model.number="form.max_recheck_times" type="number" min="0" max="10000" step="1"><small>0 表示不限次数，不触发达上限真实上传。</small></label></div></div>
            <div class="mst-subsection mst-switch-list"><SwitchField v-model="form.notify" title="Telegram 结果通知" hint="通过平台已有账号发送，不需要新增 Bot Token。"/><SwitchField v-model="form.telegram_control" title="Telegram 命令控制" hint="只接受下方明确允许的用户发送控制命令。"/><div class="mst-form-grid mst-following"><label class="mst-wide"><span>允许控制的 Telegram 用户 ID</span><textarea v-model.trim="form.telegram_admin_ids" rows="3" placeholder="多个用户 ID 用逗号或换行分隔"></textarea><small>开启命令控制时必填；只允许配置中的用户执行。</small></label></div></div>
          </template>

          <template v-else>
            <div class="mst-panel-head mst-records-heading"><div><h3>运行记录</h3><p>查看当前进度与文件处理结果。</p></div><button class="mst-secondary" type="button" :disabled="refreshing" @click="refreshStatus">{{ refreshing ? '正在刷新…' : '刷新状态' }}</button></div>
            <div class="mst-subsection"><p class="mst-hint">秒传命中会入 115 网盘；仅检测只不改本地文件。启动前会保存当前修改，停止任务不会保存。</p><div class="mst-action-row mst-run-actions"><button class="mst-primary" type="button" :disabled="status?.running || !!busy" @click="run('scan')">{{ busy === 'run-scan' ? '正在启动…' : '检测待检测目录' }}</button><button class="mst-secondary" type="button" :disabled="status?.running || !!busy" @click="run('recheck')">重检待秒传文件</button><button class="mst-secondary" type="button" :disabled="status?.running || !!busy" @click="run('all')">检测并重检</button><button v-if="status?.running" class="mst-secondary mst-danger-text" type="button" :disabled="!!busy" @click="postAction('stop', '/stop')">{{ busy === 'stop' ? '正在停止…' : '停止任务' }}</button></div><p class="mst-hint">Cookie 留空时读取平台已保存的 115 Cookie；无法连接时可到账号页检测登录。</p></div>
            <p v-if="statusError" class="mst-alert mst-error mst-status-error" role="alert">{{ statusError }}</p>
            <div v-if="status" class="mst-subsection mst-runtime-status">
              <div class="mst-status-line"><b>{{ status.running ? '任务运行中' : '当前没有任务运行' }}</b><span v-if="status.running">每 5 秒刷新</span></div>
              <p v-if="status.current" class="mst-current-file">{{ typeof status.current === 'string' ? status.current : status.current.path || status.current.name || '' }}</p>
              <progress v-if="status.running && runProgress !== null" :value="runProgress" max="100" :aria-label="`当前进度 ${Math.round(runProgress)}%`"></progress>
              <dl class="mst-counts"><div><dt>文件记录</dt><dd>{{ count('total') }}</dd></div><div><dt>已完成记录</dt><dd>{{ count('rapid') }}</dd></div><div><dt>待重检</dt><dd>{{ count('pending') }}</dd></div><div><dt>失败 / 待核对</dt><dd>{{ count('failed') }}</dd></div></dl>
              <p v-if="status.last_result?.message" class="mst-hint">{{ status.last_result.message }}</p>
            </div>
            <div class="mst-subsection">
              <div class="mst-section-head"><div><h4>文件记录</h4><p>最多显示最近 100 条记录；统计包含全部记录。</p></div><button class="mst-text-button mst-danger-text" type="button" :disabled="!items.length || status?.running || !!busy" @click="clearConfirmation = true">清空记录</button></div>
              <div v-if="clearConfirmation" class="mst-confirmation"><b>清空文件处理记录？</b><p>文件不会删除。清空后会重新检测、可能重复云端入库。</p><div class="mst-action-row"><button class="mst-secondary" type="button" @click="clearConfirmation = false">取消</button><button class="mst-secondary mst-danger-text" type="button" :disabled="!!busy" @click="clearRecords">{{ busy === 'clear' ? '正在清空…' : '确认清空记录' }}</button></div></div>
              <div v-if="!status && statusError" class="mst-empty"><b>运行记录暂不可用</b><p>请点击刷新状态重新读取。</p></div>
              <div v-else-if="!items.length" class="mst-empty"><b>尚无文件处理记录</b><p>连接账号并执行检测后，结果将显示在这里。</p></div>
              <ul v-else class="mst-record-list">
                <li v-for="(item, index) in items" :key="item.path || index">
                  <div class="mst-record-main"><b class="mst-file-path">{{ item.path || item.name }}</b><span :class="['mst-record-state', {failed: attentionState(item.state)}]">{{ stateLabel(item.state) }}</span></div>
                  <div class="mst-record-meta"><span>{{ formatBytes(item.size) }}</span><span>检查 {{ item.checks ?? 0 }} 次</span><time>{{ formatTime(item.updated) }}</time></div>
                  <p v-if="item.message" class="mst-hint" :class="{'mst-danger-text': attentionState(item.state)}">{{ item.message }}</p>
                </li>
              </ul>
            </div>
          </template>
        </fieldset>
      </section>
    </div>

    <footer v-if="!loading" class="mst-save-bar"><span>{{ loadError ? '配置读取失败，暂不可保存' : dirty ? '修改尚未保存' : '当前配置已保存' }}</span><button class="mst-primary" type="button" :disabled="locked || !dirty" @click="save()">{{ saving ? '正在保存…' : '保存配置' }}</button></footer>
  </main>
  </IosSettings>
</template>

<style scoped>
.mst-shell { min-width:0; color:var(--ios-text); padding:4px 0 0; }
h2,h3,h4,p { margin:0; }
h2 { font-size:27px; line-height:1.2; letter-spacing:-.025em; font-weight:720; }
h3 { font-size:18px; line-height:1.4; font-weight:680; }
h4 { font-size:15px; font-weight:650; }
.mst-page-head { display:flex; align-items:center; justify-content:space-between; gap:16px; margin:0 2px 24px; }
.mst-page-head p,.mst-panel-head p,.mst-section-head p { color:var(--ios-secondary); font-size:13px; margin-top:5px; }
.mst-save-state { flex:none; padding:5px 10px; border-radius:9px; background:var(--ios-inset); color:var(--ios-secondary); font-size:12px; }
.mst-save-state.changed { color:var(--ios-accent-text); background:var(--accent-dim,var(--ios-inset)); }
.mst-workspace { display:grid; gap:24px; }
.mst-section-nav { position:relative; isolation:isolate; display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:3px; padding:4px; border-radius:15px; background:var(--ios-inset); }
.mst-section-nav::before { content:""; position:absolute; z-index:-1; inset:4px auto 4px 4px; width:calc((100% - 11px)/4); border-radius:11px; background:var(--ios-control); box-shadow:0 2px 6px var(--shadow-sm,rgba(0,0,0,.09)); transform:translateX(calc(var(--mst-tab-index,0)*100% + var(--mst-tab-index,0)*3px)); transition:transform var(--ios-duration) var(--ios-ease); }
.mst-section-nav button { display:flex; align-items:center; justify-content:center; gap:7px; min-height:40px; padding:8px; border:0; border-radius:11px; color:var(--ios-secondary); background:transparent; cursor:pointer; }
.mst-section-nav button.active { color:var(--ios-text); font-weight:650; }
.mst-section-nav button:hover:not(.active) { color:var(--ios-text); background:var(--hover-bg,var(--ios-surface)); }
.mst-section-nav i { width:5px; height:5px; border-radius:50%; background:var(--ios-line); }
.mst-section-nav i.on { background:var(--success,#178a45); }
.mst-panel,.mst-fields { min-width:0; }
.mst-fields { margin:0; padding:0; border:0; display:grid; gap:16px; }
.mst-panel-head { padding:0 4px 2px; }
.mst-subsection { min-width:0; padding:20px; border-radius:16px; background:var(--ios-surface); }
.mst-section-head { display:flex; align-items:center; justify-content:space-between; gap:14px; margin-bottom:16px; }
.mst-form-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px 20px; }
.mst-form-grid label { min-width:0; }
.mst-form-grid label>span { display:block; font-size:13px; font-weight:600; margin-bottom:8px; }
.mst-form-grid small,.mst-hint { display:block; margin-top:7px; color:var(--ios-secondary); font-size:12px; line-height:1.65; overflow-wrap:anywhere; }
.mst-wide { grid-column:1/-1; }
input:not([type=checkbox]),textarea,select { display:block; width:100%; min-height:44px; padding:11px 12px; color:var(--ios-text); border:1px solid transparent; border-radius:11px; background:var(--ios-inset); outline:none; transition:background-color var(--ios-fast),border-color var(--ios-fast); }
input:not([type=checkbox]):hover,textarea:hover,select:hover { background:var(--hover-bg,var(--ios-inset)); }
input:not([type=checkbox]):focus,textarea:focus,select:focus { border-color:var(--ios-accent-text); background:var(--ios-control); }
textarea { min-height:90px; resize:vertical; line-height:1.6; }
.mst-secret-field { position:relative; }
.mst-secret-field input { padding-inline-end:48px; }
.mst-secret-field button { position:absolute; inset-inline-end:0; top:0; display:grid; place-items:center; width:44px; height:44px; padding:0; border:0; border-radius:11px; color:var(--ios-secondary); background:transparent; cursor:pointer; }
.mst-secret-field button:hover { color:var(--ios-accent-text); }
.mst-secret-field svg { width:20px; height:20px; fill:none; stroke:currentColor; stroke-width:1.7; stroke-linecap:round; }
.mst-primary,.mst-secondary { display:inline-flex; align-items:center; justify-content:center; gap:8px; min-height:44px; padding:10px 17px; border:0; border-radius:12px; color:var(--ios-accent-text); background:var(--accent-dim,var(--ios-inset)); font-weight:620; cursor:pointer; }
.mst-primary { color:var(--btn-primary-text,#fff); background:var(--ios-accent); min-width:112px; }
.mst-primary:hover:not(:disabled) { filter:brightness(1.08); }
.mst-secondary:hover:not(:disabled) { background:var(--hover-bg,var(--ios-inset)); }
button:disabled { opacity:.48; cursor:not-allowed; }
.mst-action-row { display:flex; align-items:center; flex-wrap:wrap; gap:12px; margin-top:16px; }
.mst-login-result { color:var(--success,#178a45); font-size:13px; }
.mst-qr-controls { align-items:end; }
.mst-qr-controls>button { justify-self:start; }
.mst-qr-area { display:flex; align-items:center; gap:22px; margin-top:20px; }
.mst-qr-area img { display:block; flex:0 0 192px; max-width:100%; object-fit:contain; border:8px solid #fff; border-radius:14px; background:#fff; }
.mst-qr-area b { font-size:15px; }
.mst-qr-area p { margin-top:6px; color:var(--ios-secondary); font-size:13px; overflow-wrap:anywhere; }
.mst-qr-area small { display:block; margin-top:10px; color:var(--ios-secondary); font-size:12px; }
.mst-switch-list { display:grid; gap:0; }
.mst-switch-list :deep(.mst-switch-field+.mst-switch-field) { border-top:1px solid var(--ios-line); }
.mst-switch-list :deep(.mst-switch-field) { padding-block:15px; }
.mst-switch-list :deep(.mst-switch-field:first-child) { padding-top:0; }
.mst-switch-list :deep(.mst-switch-field:last-child) { padding-bottom:0; }
.mst-following { margin-top:18px; padding-top:17px; border-top:1px solid var(--ios-line); }
.mst-alert { margin:0 0 16px; padding:14px 16px; border-radius:13px; overflow-wrap:anywhere; font-size:13px; background:var(--ios-inset); }
.mst-alert.mst-error { color:var(--danger,#c73036); background:var(--danger-bg,var(--ios-inset)); }
.mst-alert.mst-success { color:var(--success,#178a45); background:var(--success-bg,var(--ios-inset)); }
.mst-alert>button { margin-top:10px; }
.mst-loading { padding:52px 16px; color:var(--ios-secondary); text-align:center; }
.mst-records-heading { display:flex; align-items:center; justify-content:space-between; gap:16px; }
.mst-run-actions { gap:9px; }
.mst-danger-text { color:var(--danger,#c73036); }
.mst-status-error { margin:0; }
.mst-status-line { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.mst-status-line span { color:var(--ios-secondary); font-size:12px; }
.mst-current-file { margin-top:10px; color:var(--ios-secondary); overflow-wrap:anywhere; }
progress { display:block; width:100%; height:6px; margin-top:16px; overflow:hidden; border:0; border-radius:3px; accent-color:var(--ios-accent); }
progress::-webkit-progress-bar { background:var(--ios-inset); border-radius:3px; }
progress::-webkit-progress-value { background:var(--ios-accent); border-radius:3px; transition:width var(--ios-duration) var(--ios-ease); }
.mst-counts { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; padding-top:17px; margin:18px 0 0; border-top:1px solid var(--ios-line); }
.mst-counts dt { color:var(--ios-secondary); font-size:12px; }
.mst-counts dd { margin:3px 0 0; font-size:18px; font-weight:650; font-variant-numeric:tabular-nums; }
.mst-text-button { min-height:44px; padding:8px 0; border:0; background:transparent; font-size:13px; cursor:pointer; }
.mst-confirmation { padding:16px; margin-bottom:16px; border-radius:12px; color:var(--danger,#c73036); background:var(--danger-bg,var(--ios-inset)); }
.mst-confirmation p { margin-top:5px; color:var(--ios-secondary); font-size:13px; }
.mst-confirmation .mst-action-row { margin-top:12px; }
.mst-empty { padding:32px 12px; text-align:center; }
.mst-empty b { font-size:14px; font-weight:600; }
.mst-empty p { margin-top:6px; color:var(--ios-secondary); font-size:13px; }
.mst-record-list { margin:0; padding:0; list-style:none; }
.mst-record-list li { padding:17px 0; border-top:1px solid var(--ios-line); }
.mst-record-list li:first-child { border-top:0; padding-top:0; }
.mst-record-list li:last-child { padding-bottom:0; }
.mst-record-main { display:flex; justify-content:space-between; align-items:start; gap:16px; }
.mst-file-path { min-width:0; font-size:13px; font-weight:550; overflow-wrap:anywhere; }
.mst-record-state { flex:none; padding:2px 7px; border-radius:6px; color:var(--success,#178a45); background:var(--success-bg,var(--ios-inset)); font-size:12px; }
.mst-record-state.failed { color:var(--danger,#c73036); background:var(--danger-bg,var(--ios-inset)); }
.mst-record-meta { display:flex; flex-wrap:wrap; gap:5px 16px; margin-top:7px; color:var(--ios-secondary); font-size:12px; font-variant-numeric:tabular-nums; }
.mst-save-bar { position:sticky; z-index:3; bottom:0; display:flex; align-items:center; justify-content:space-between; gap:16px; margin-top:24px; padding:13px 16px max(13px,env(safe-area-inset-bottom)); border-radius:16px; background:var(--glass-surface,var(--ios-surface)); backdrop-filter:blur(var(--glass-custom-blur,18px)); -webkit-backdrop-filter:blur(var(--glass-custom-blur,18px)); box-shadow:0 6px 20px var(--shadow-sm,rgba(0,0,0,.08)); }
.mst-save-bar>span { color:var(--ios-secondary); font-size:12px; }
@container(max-width:600px) {
  h2 { font-size:24px; }
  .mst-page-head { align-items:flex-start; gap:12px; margin-bottom:20px; }
  .mst-save-state { max-width:110px; text-align:center; }
  .mst-workspace { gap:20px; }
  .mst-section-nav button { font-size:12px; white-space:nowrap; padding-inline:4px; gap:4px; }
  .mst-subsection { padding:16px; }
  .mst-form-grid { grid-template-columns:1fr; gap:16px; }
  .mst-wide { grid-column:auto; }
  .mst-qr-area { align-items:flex-start; flex-direction:column; gap:14px; }
  .mst-qr-controls>button { width:100%; }
  .mst-records-heading { align-items:flex-start; }
  .mst-records-heading .mst-secondary { padding-inline:10px; font-size:12px; }
  .mst-counts { grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
  .mst-status-line { align-items:flex-start; }
  .mst-record-main { gap:10px; }
  .mst-run-actions>.mst-primary,.mst-run-actions>.mst-secondary { flex:1 1 140px; }
}
@media(forced-colors:active) {
  .mst-subsection,.mst-save-bar,input,textarea,select,button,.mst-confirmation { border:1px solid CanvasText; }
  .mst-section-nav::before { border:1px solid Highlight; }
  .mst-section-nav i.on { background:Highlight; }
}
</style>
