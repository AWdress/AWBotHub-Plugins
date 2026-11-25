<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { createHostBridge } from './bridge.js'
import IosSettings from '../../../_frontend/IosSettings.vue'
const props = defineProps({ host: { type: Object, required: true } })
const VERSION = '0.0.2'
const tab = ref('admin')
const tabs = [{ id: 'admin', label: '管理页面' }, { id: 'settings', label: '插件设置' }, { id: 'status', label: '运行状态' }]
const defaults = { auto_tasks: false, allow_downloads: false, notify_results: false, database_url: '' }
const values = ref({ ...defaults })
const baseline = ref('')
const loading = ref(true)
const saving = ref(false)
const loaded = ref(false)
const loadError = ref('')
const notice = ref('')
const failed = ref(false)
const status = ref(null)
const statusError = ref('')
const refreshing = ref(false)
const stopping = ref('')
const frame = ref(null)
const frameReady = ref(false)
const frameError = ref('')
const frameRevision = ref(0)
const session = ref('')
const tabButtons = []
let bridge = null
let connectTimer = null
let mounted = true
const dirty = computed(() => loaded.value && JSON.stringify(values.value) !== baseline.value)
const frameSrc = computed(() => session.value ? `/api/plugins/${encodeURIComponent(props.host.pluginId || 'immortal')}/fe/app/index.html?v=${VERSION}&bridge=${session.value}` : '')
const databaseLabel = computed(() => status.value?.database || (values.value.database_url.trim() ? '外部数据库' : 'SQLite（插件独立文件）'))
const stateLabels = { queued: '等待执行', running: '运行中', stopping: '正在停止', cancelled: '已停止', failed: '失败', success: '已完成', completed: '已完成' }
watch(values, () => { if (!saving.value) notice.value = '' }, { deep: true, flush: 'sync' })
function tabKey(event, index) {
  const next = { ArrowRight: (index + 1) % tabs.length, ArrowLeft: (index + tabs.length - 1) % tabs.length, Home: 0, End: tabs.length - 1 }[event.key]
  if (next === undefined) return
  event.preventDefault(); tab.value = tabs[next].id; tabButtons[next]?.focus()
}
function resetFrame() {
  bridge?.close(); clearTimeout(connectTimer); frameReady.value = false; frameError.value = ''
  const random = new Uint8Array(24); crypto.getRandomValues(random)
  session.value = Array.from(random, n => n.toString(16).padStart(2, '0')).join('')
  frameRevision.value++
  bridge = createHostBridge({ host: props.host, iframe: () => frame.value, session: session.value, origin: location.origin,
    connected() { frameReady.value = true; clearTimeout(connectTimer) }, error(message) { frameError.value = message } })
  connectTimer = setTimeout(() => { if (mounted && !frameReady.value) frameError.value = '管理页面未连接成功，请确认插件已启用，再重新打开。' }, 20000)
}
async function receive(event) { await bridge?.receive(event) }
async function load() {
  if (saving.value || dirty.value) return
  loading.value = true; loadError.value = ''; loaded.value = false
  try {
    const result = await props.host.getConfig()
    if (!mounted) return
    values.value = { ...defaults, ...result }
    for (const key of ['auto_tasks', 'allow_downloads', 'notify_results']) values.value[key] = result?.[key] === true
    values.value.database_url = typeof result?.database_url === 'string' ? result.database_url : ''
    baseline.value = JSON.stringify(values.value); loaded.value = true
  } catch (error) { if (mounted) loadError.value = `读取配置失败：${error.message || '请重试'}。读取成功前不能保存。` }
  finally { loading.value = false }
  if (loaded.value) { await refresh(); if (mounted) resetFrame() }
}
async function refresh() {
  if (refreshing.value) return
  refreshing.value = true
  try { const result = await props.host.callApi('/status'); if (mounted) { status.value = result; statusError.value = '' } }
  catch (error) { if (mounted) statusError.value = error.message || '状态读取失败，请确认插件已启用。' }
  finally { refreshing.value = false }
}
async function save() {
  if (!loaded.value || saving.value || !dirty.value) return
  const database = values.value.database_url.trim()
  const unchangedSecret = database === '********' && JSON.parse(baseline.value).database_url === database
  if (database && !unchangedSecret && !/^postgresql(?:\+psycopg2)?:\/\//.test(database)) { notice.value = '数据库地址需使用 postgresql:// 或 postgresql+psycopg2://；留空使用插件独立 SQLite。'; failed.value = true; return }
  saving.value = true; notice.value = ''; failed.value = false
  try {
    await props.host.saveConfig({ ...values.value, database_url: database })
    if (!mounted) return
    values.value.database_url = database; baseline.value = JSON.stringify(values.value)
    notice.value = '配置已保存。管理页将重新连接以应用当前设置。'
    await refresh(); if (mounted) resetFrame()
  } catch (error) { if (mounted) { notice.value = `保存失败：${error.message || '请重试'}。填写内容已保留。`; failed.value = true } }
  finally { saving.value = false }
}
async function stop(job) {
  if (stopping.value || !job.id) return
  stopping.value = job.id
  try { await props.host.callApi('/cancel', { method: 'POST', body: { id: job.id } }); await refresh() }
  catch (error) { statusError.value = error.message || '停止失败，请刷新状态查看。' }
  finally { stopping.value = '' }
}
onMounted(() => { window.addEventListener('message', receive); void load() })
onBeforeUnmount(() => { mounted = false; bridge?.close(); clearTimeout(connectTimer); window.removeEventListener('message', receive) })
</script>

<template>
  <IosSettings>
  <section class="immortal-config">
    <nav :style="{ '--im-tab-index': tabs.findIndex(item => item.id === tab) }" class="im-tabs" role="tablist" aria-label="Immortal 设置分组">
      <button v-for="(item, index) in tabs" :id="`immortal-tab-${item.id}`" :key="item.id" :ref="element => tabButtons[index] = element" role="tab" :aria-selected="tab === item.id" :aria-controls="`immortal-panel-${item.id}`" :tabindex="tab === item.id ? 0 : -1" :class="{ selected: tab === item.id }" @click="tab = item.id" @keydown="tabKey($event, index)">{{ item.label }}</button>
    </nav>
    <p v-if="loading" class="im-hint" role="status">正在读取插件配置…</p>
    <div v-if="loadError" class="im-message im-error" role="alert"><p>{{ loadError }}</p><button class="im-button" @click="load">重新读取</button></div>

    <div v-show="tab === 'admin'" id="immortal-panel-admin" role="tabpanel" aria-labelledby="immortal-tab-admin">
      <header class="im-section-head"><div><h3>Immortal</h3><p>源码内置管理台，无需另开服务。保留原有采集、订阅和下载管理界面。</p></div><button class="im-button" :disabled="!loaded || saving" @click="resetFrame">重新打开管理页</button></header>
      <p v-if="statusError" class="im-message im-error" role="alert">{{ statusError }} 请先启用插件。</p>
      <p v-if="session && !frameReady && !frameError" class="im-hint" role="status">正在连接管理页面…</p>
      <p v-if="frameError" class="im-message im-error" role="alert">{{ frameError }}</p>
      <iframe v-if="frameSrc" :key="frameRevision" ref="frame" :src="frameSrc" title="Immortal 管理页面" class="im-admin-frame" referrerpolicy="no-referrer" />
    </div>

    <div v-show="tab === 'settings'" id="immortal-panel-settings" role="tabpanel" aria-labelledby="immortal-tab-settings">
      <header class="im-section-head"><div><h3>插件设置</h3><p>三个功能默认关闭。修改后保存，设置才会生效。</p></div></header>
      <fieldset :disabled="!loaded || saving" class="im-settings-fields">
        <div class="im-toggles"><label class="immortal-toggle-row"><input v-model="values.auto_tasks" type="checkbox" role="switch"><i aria-hidden="true"></i><span><b>运行自动任务</b><small>允许运行 Immortal 内启用的定时采集和订阅任务；关闭时不自动执行。</small></span></label>
        <label class="immortal-toggle-row"><input v-model="values.allow_downloads" type="checkbox" role="switch"><i aria-hidden="true"></i><span><b>允许提交下载</b><small>开启后才允许向已配置的下载器提交任务，可能产生下载流量。</small></span></label>
        <label class="immortal-toggle-row"><input v-model="values.notify_results" type="checkbox" role="switch"><i aria-hidden="true"></i><span><b>任务结果通知</b><small>通过平台已有通知渠道发送，不需要重复填写 Telegram 或企业微信凭证。</small></span></label>
        </div><label class="im-field"><span>数据库地址（可选）</span><input v-model="values.database_url" type="password" autocomplete="new-password" placeholder="留空：使用插件独立 SQLite 数据库"><small>默认空值，使用插件独立 SQLite 文件。外部 PostgreSQL 连接使用 postgresql:// 或 postgresql+psycopg2://；不接受外部 SQLite 文件路径。切换地址不会自动迁移旧数据。</small><small v-if="values.database_url === '********'">已保存的连接信息由平台保护。保持原样不会更改；需要更换时输入新地址。</small></label>
      </fieldset>
      <footer class="im-save-bar"><p :class="['im-save-message', { 'im-error': failed }]" :role="failed ? 'alert' : 'status'">{{ notice || (dirty ? '有未保存的修改。' : loaded ? '当前配置已保存。' : '配置尚未读取成功。') }}</p>
      <button class="im-button im-primary" :disabled="!loaded || saving || !dirty" @click="save">{{ saving ? '正在保存…' : '保存配置' }}</button></footer>
    </div>

    <div v-show="tab === 'status'" id="immortal-panel-status" role="tabpanel" aria-labelledby="immortal-tab-status">
      <header class="im-section-head"><div><h3>运行状态</h3><p>按需刷新，不进行空闲轮询。</p></div><button class="im-button" :disabled="refreshing" @click="refresh">{{ refreshing ? '正在读取…' : '刷新状态' }}</button></header>
      <p v-if="statusError" class="im-message im-error" role="alert">{{ statusError }}</p>
      <dl v-if="status" class="im-status-list"><div><dt>插件版本</dt><dd>{{ status.version || VERSION }}</dd></div><div><dt>数据库</dt><dd>{{ databaseLabel }}</dd></div><div><dt>自动任务</dt><dd>{{ status.auto_tasks ? '已开启' : '已关闭' }}</dd></div><div><dt>提交下载</dt><dd>{{ status.allow_downloads ? '允许' : '禁止' }}</dd></div><div><dt>结果通知</dt><dd>{{ status.notify_results ? '已开启' : '已关闭' }}</dd></div></dl>
      <h4>当前任务</h4>
      <ul v-if="status?.running?.length" class="im-jobs"><li v-for="job in status.running" :key="job.id"><b>{{ job.label || job.id }}</b><span>{{ job.error || stateLabels[job.state] || '运行中' }}</span><button v-if="['queued', 'running', 'stopping'].includes(job.state)" class="im-button" :disabled="!!stopping || job.state === 'stopping'" @click="stop(job)">{{ stopping === job.id || job.state === 'stopping' ? '正在停止…' : '停止任务' }}</button></li></ul>
      <p v-else class="im-hint">{{ status ? '当前没有任务运行。' : '尚未读取运行状态。' }}</p>
      <p class="im-hint">采集网站和下载器需要能从平台服务器访问；配置页打开正常不代表外部账号已经登录。</p>
    </div>
  </section>
  </IosSettings>
</template>

<style scoped>
.immortal-config { color:var(--ios-text); min-width:0; padding-top:4px; }
.im-tabs { position:relative; isolation:isolate; display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:3px; margin-bottom:24px; padding:4px; border-radius:15px; background:var(--ios-inset); }
.im-tabs::before { content:""; position:absolute; z-index:-1; inset:4px auto 4px 4px; width:calc((100% - 10px)/3); border-radius:11px; background:var(--ios-control); box-shadow:0 2px 6px var(--shadow-sm,rgba(0,0,0,.09)); transform:translateX(calc(var(--im-tab-index,0)*100% + var(--im-tab-index,0)*3px)); transition:transform var(--ios-duration) var(--ios-ease); }
.im-tabs button { min-height:40px; padding:8px 10px; border:0; border-radius:11px; background:transparent; color:var(--ios-secondary); cursor:pointer; }
.im-tabs button.selected { color:var(--ios-text); font-weight:650; }
.im-tabs button:hover:not(.selected) { color:var(--ios-text); background:var(--hover-bg,var(--ios-surface)); }
.im-section-head { display:flex; align-items:start; justify-content:space-between; gap:20px; margin:0 2px 20px; }
h3 { font-size:23px; font-weight:690; letter-spacing:-.02em; line-height:1.3; margin:0 0 6px; }
h4 { margin:26px 4px 10px; font-size:15px; font-weight:650; }
p { margin:0; line-height:1.65; max-width:70ch; }
.im-section-head p,.im-hint,small { color:var(--ios-secondary); font-size:13px; }
.im-button { display:inline-flex; align-items:center; justify-content:center; gap:8px; min-height:44px; border:0; border-radius:12px; background:var(--accent-dim,var(--ios-inset)); color:var(--ios-accent-text); padding:10px 16px; font-weight:620; cursor:pointer; }
.im-button:hover:not(:disabled) { background:var(--hover-bg,var(--ios-inset)); }
.im-button.im-primary { background:var(--ios-accent); color:var(--btn-primary-text,#fff); }
.im-button.im-primary:hover:not(:disabled) { background:var(--ios-accent); filter:brightness(1.08); }
button:disabled,fieldset:disabled { opacity:.48; }
button:disabled { cursor:not-allowed; }
.im-admin-frame { display:block; width:100%; height:min(80vh,1000px); min-height:610px; border:1px solid var(--ios-line); border-radius:16px; background:var(--ios-surface); }
.im-message { display:flex; align-items:center; flex-wrap:wrap; gap:12px; padding:14px 16px; margin:12px 0; border-radius:12px; background:var(--ios-inset); }
.im-message.im-error { background:var(--danger-bg,var(--ios-inset)); }
.im-error { color:var(--danger,#c73036); }
.im-settings-fields { border:0; margin:0; padding:0; display:grid; grid-template-columns:minmax(0,1fr); gap:20px; min-width:0; }
.im-toggles { padding:4px 20px; background:var(--ios-surface); border-radius:16px; }
.immortal-toggle-row { position:relative; display:flex; align-items:center; justify-content:space-between; gap:20px; min-width:0; padding:17px 0; cursor:pointer; }
.immortal-toggle-row+.immortal-toggle-row { border-top:1px solid var(--ios-line); }
.immortal-toggle-row input { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip-path:inset(50%); white-space:nowrap; border:0; }
.immortal-toggle-row>i { position:relative; order:2; flex:none; width:50px; height:30px; border-radius:15px; background:var(--switch-bg,var(--ios-line)); transition:background-color var(--ios-fast) ease; }
.immortal-toggle-row>i::after { content:""; position:absolute; inset-inline-start:3px; top:3px; width:24px; height:24px; border-radius:50%; background:var(--switch-thumb,#fff); box-shadow:0 2px 4px rgba(0,0,0,.15); transition:transform var(--ios-duration) var(--ios-ease); }
.immortal-toggle-row input:checked+i { background:var(--success,#178a45); }
.immortal-toggle-row input:checked+i::after { transform:translateX(20px); }
.immortal-toggle-row input:focus-visible+i { outline:3px solid var(--ios-accent-text); outline-offset:3px; }
.immortal-toggle-row>span { order:1; display:grid; grid-template-columns:minmax(0,1fr); gap:4px; flex:1; min-width:0; overflow-wrap:anywhere; }
.immortal-toggle-row b { font-size:14px; font-weight:600; }
small { display:block; line-height:1.65; max-width:70ch; font-size:12px; }
.im-field { display:grid; gap:9px; font-size:13px; padding:20px; border-radius:16px; background:var(--ios-surface); }
.im-field>span { font-weight:600; }
.im-field input { width:100%; min-height:44px; border:1px solid transparent; border-radius:11px; background:var(--ios-inset); color:var(--ios-text); padding:11px 12px; outline:none; transition:background-color var(--ios-fast),border-color var(--ios-fast); }
.im-field input:focus { border-color:var(--ios-accent-text); background:var(--ios-control); }
.im-save-bar { position:sticky; z-index:2; bottom:0; display:flex; align-items:center; justify-content:space-between; gap:16px; margin-top:24px; padding:13px 16px max(13px,env(safe-area-inset-bottom)); border-radius:16px; background:var(--glass-surface,var(--ios-surface)); backdrop-filter:blur(var(--glass-custom-blur,18px)); -webkit-backdrop-filter:blur(var(--glass-custom-blur,18px)); box-shadow:0 6px 20px var(--shadow-sm,rgba(0,0,0,.08)); }
.im-save-message { color:var(--ios-secondary); font-size:12px; }
.im-save-message.im-error { color:var(--danger,#c73036); }
.im-save-bar>.im-button { flex:none; }
.im-status-list { margin:0; padding:0 20px; border-radius:16px; background:var(--ios-surface); }
.im-status-list>div { display:grid; grid-template-columns:140px minmax(0,1fr); gap:20px; padding:16px 0; font-size:13px; }
.im-status-list>div+div { border-top:1px solid var(--ios-line); }
.im-status-list dt { color:var(--ios-secondary); }
.im-status-list dd { margin:0; overflow-wrap:anywhere; font-variant-numeric:tabular-nums; text-align:end; }
.im-jobs { list-style:none; margin:0 0 16px; padding:0 20px; border-radius:16px; background:var(--ios-surface); }
.im-jobs li { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px 16px; padding:16px 0; }
.im-jobs li+li { border-top:1px solid var(--ios-line); }
.im-jobs b { font-size:14px; font-weight:600; overflow-wrap:anywhere; }
.im-jobs span { color:var(--ios-secondary); font-size:13px; overflow-wrap:anywhere; }
.im-hint { margin:12px 4px; }
@container(max-width:600px) {
  .im-tabs button { padding-inline:6px; font-size:13px; }
  .im-section-head { flex-direction:column; gap:14px; }
  .im-section-head .im-button { align-self:flex-start; }
  h3 { font-size:21px; }
  .im-toggles { padding-inline:16px; }
  .im-field { padding:18px 16px; }
  .im-status-list,.im-jobs { padding-inline:16px; }
  .im-status-list>div { grid-template-columns:100px minmax(0,1fr); gap:12px; }
  .im-admin-frame { min-height:650px; }
}
@media(forced-colors:active) {
  .im-toggles,.im-field,.im-save-bar,.im-status-list,.im-jobs,.im-tabs::before,input,button { border:1px solid CanvasText; }
  .immortal-toggle-row input { position:static; order:2; width:24px; height:24px; margin:0; clip-path:none; }
  .immortal-toggle-row>i { display:none; }
}
</style>
