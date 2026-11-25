<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'
import { apiError, configValues, sources, validate } from './config.js'

const props = defineProps({ host: { type: Object, required: true } })
const tabs = [{ id: 'status', label: '榜单状态' }, { id: 'config', label: '配置' }, { id: 'widget', label: 'Widget 地址' }]
const tab = ref('status')
const values = ref(configValues({}))
const baseline = ref('')
const loaded = ref(false)
const loading = ref(false)
const saving = ref(false)
const acting = ref('')
const revealing = ref('')
const visible = ref({})
const errors = ref({})
const loadError = ref('')
const notice = ref('')
const noticeOk = ref(true)
const saveNotice = ref('')
const saveFailed = ref(false)
const status = ref(null)
const statusError = ref('')
const address = ref('')
const preview = ref(null)
const rotateConfirm = ref(false)
let mounted = true
let pollTimer = null
let polling = false
const tabButtons = []
const busy = computed(() => loading.value || saving.value || !!acting.value || !!revealing.value)
const dirty = computed(() => loaded.value && JSON.stringify(values.value) !== baseline.value)
watch(values, () => { if (!saving.value) saveNotice.value = '' }, { deep: true, flush: 'sync' })
const stateLabels = { empty: '未更新', cached: '已有缓存', success: '更新成功', running: '更新中', failed: '更新失败', skipped: '未配置', cancelled: '已停止' }
const rows = computed(() => status.value?.sources || sources.map(([id, name]) => ({ id, name, state: 'empty', count: 0, enabled: values.value.sources.includes(id) })))
const currentName = computed(() => sources.find(([id]) => id === status.value?.current)?.[1] || '')
const previewRows = computed(() => {
  const result = []
  function walk(value, path = '') {
    if (Array.isArray(value)) {
      for (const item of value) if (item?.tmdbId) result.push({ ...item, category: path })
    } else if (value && typeof value === 'object') {
      for (const [key, nested] of Object.entries(value)) walk(nested, path ? `${path} / ${key}` : key)
    }
  }
  walk(preview.value?.data)
  return result.slice(0, 60)
})
function setNotice(text, ok = true) { notice.value = text; noticeOk.value = ok }
function date(value) {
  if (!value) return '尚未更新'
  const time = new Date(value)
  return Number.isNaN(time.getTime()) ? String(value) : time.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
}
function tabKey(event, index) {
  const next = { ArrowRight: (index + 1) % 3, ArrowLeft: (index + 2) % 3, Home: 0, End: 2 }[event.key]
  if (next === undefined) return
  event.preventDefault(); tab.value = tabs[next].id; tabButtons[next]?.focus()
}
async function load() {
  if (busy.value || dirty.value) { if (dirty.value) setNotice('还有未保存的修改，请先保存再重新读取。', false); return }
  loading.value = true; loadError.value = ''; loaded.value = false
  try {
    const config = configValues(await props.host.getConfig())
    if (!mounted) return
    values.value = config; baseline.value = JSON.stringify(config); loaded.value = true; errors.value = {}; visible.value = {}
  } catch (error) { if (mounted) loadError.value = apiError(error, '读取配置') + ' 未读取成功前不能保存。' }
  finally { loading.value = false }
  if (loaded.value) await refresh()
}
async function refresh() {
  if (polling || !loaded.value) return
  polling = true
  try {
    const result = await props.host.callApi('/status')
    if (!mounted) return
    if (result?.ok === false) throw new Error()
    status.value = result; statusError.value = ''
    clearTimeout(pollTimer)
    if (result.running) pollTimer = setTimeout(refresh, 5000)
  } catch (error) { if (mounted) { statusError.value = apiError(error, '读取榜单状态'); clearTimeout(pollTimer) } }
  finally { polling = false }
}
async function save() {
  if (!loaded.value || busy.value) return
  errors.value = validate(values.value)
  if (Object.keys(errors.value).length) {
    tab.value = 'config'; saveNotice.value = '未保存，请检查标红的设置。'; saveFailed.value = true; return
  }
  saving.value = true; saveNotice.value = ''; saveFailed.value = false
  try {
    const payload = JSON.parse(JSON.stringify(values.value))
    payload.public_base_url = payload.public_base_url.trim().replace(/\/$/, '')
    const result = await props.host.saveConfig(payload)
    if (result?.ok === false) throw new Error()
    if (!mounted) return
    values.value = payload; baseline.value = JSON.stringify(payload); address.value = ''; rotateConfirm.value = false
    saveNotice.value = '配置已保存。更新与客户端读取使用已保存的设置。'
  } catch (error) {
    if (mounted) { saveNotice.value = apiError(error, '保存配置'); saveFailed.value = true }
  }
  finally { saving.value = false }
  await refresh()
}
async function reveal(key) {
  if (busy.value || !loaded.value) return
  if (visible.value[key]) { visible.value[key] = false; return }
  if (values.value[key] !== '********') { visible.value[key] = true; return }
  revealing.value = key
  try {
    const secret = await props.host.revealSecret(key)
    if (typeof secret !== 'string' || secret === '********') throw new Error()
    if (!mounted) return
    const saved = JSON.parse(baseline.value)
    values.value[key] = secret
    if (saved[key] === '********') { saved[key] = secret; baseline.value = JSON.stringify(saved) }
    visible.value[key] = true
  } catch (error) { if (mounted) setNotice(apiError(error, '查看密钥'), false) }
  finally { revealing.value = '' }
}
async function action(path, body, label) {
  if (!loaded.value || busy.value) return null
  if (dirty.value) { setNotice('还有未保存的设置，请先保存再操作。', false); return null }
  acting.value = label
  try {
    const result = await props.host.callApi(path, body === undefined ? {} : { method: 'POST', body })
    if (!mounted) return null
    setNotice(result.message || `${label}完成。`, result.ok !== false)
    return result.ok === false ? null : result
  } catch (error) { if (mounted) setNotice(apiError(error, label), false); return null }
  finally { acting.value = '' }
}
async function update(source = 'all') { await action('/update', { source }, '更新榜单'); await refresh() }
async function stop() { await action('/cancel', {}, '停止更新'); await refresh() }
async function showPreview(id) { const result = await action(`/preview?source=${encodeURIComponent(id)}`, undefined, '查看预览'); if (result) preview.value = result }
async function getAddress() { const result = await action('/widget', undefined, '获取 Widget 地址'); if (result) address.value = result.url }
async function copy() {
  try { await navigator.clipboard.writeText(address.value); setNotice('Widget 地址已复制。请粘贴到客户端的模块导入处。') }
  catch { setNotice('浏览器不允许复制，请选中地址后手动复制。', false) }
}
async function rotate() { const result = await action('/rotate-token', { confirmed: true }, '更换只读密钥'); if (result) { address.value = ''; rotateConfirm.value = false } }
onMounted(load)
onBeforeUnmount(() => { mounted = false; clearTimeout(pollTimer) })
</script>

<template>
  <IosSettings>
  <div class="vw-config">
    <header class="vw-page-head"><h2>VPS-Widget</h2></header>
    <nav class="vw-tabs" :style="{ '--vw-tab-index': tabs.findIndex(item => item.id === tab) }" role="tablist" aria-label="VPS-Widget 设置分组">
      <button v-for="(item, index) in tabs" :id="`vw-tab-${item.id}`" :key="item.id" :ref="el => tabButtons[index] = el" type="button" role="tab" :aria-selected="tab === item.id" :aria-controls="`vw-panel-${item.id}`" :tabindex="tab === item.id ? 0 : -1" :class="{ active: tab === item.id }" @click="tab = item.id" @keydown="tabKey($event, index)">{{ item.label }}</button>
    </nav>
    <p v-if="loading" class="vw-note" role="status">正在读取配置…</p>
    <div v-if="loadError" class="vw-message bad" role="alert">{{ loadError }} <button type="button" @click="load">重新读取</button></div>
    <p v-if="notice" class="vw-message" :class="{ bad: !noticeOk }" :role="noticeOk ? 'status' : 'alert'">{{ notice }}</p>

    <section v-show="tab === 'status'" id="vw-panel-status" role="tabpanel" aria-labelledby="vw-tab-status">
      <header class="vw-heading"><div><h3>影视榜单</h3><p>先填写 TMDB 密钥并保存，再更新。源站失败时保留上次有效榜单。</p></div><button class="vw-primary" type="button" :disabled="!loaded || busy || status?.running" @click="update()">{{ status?.running ? '正在更新…' : '更新全部榜单' }}</button></header>
      <div class="vw-toolbar"><span>{{ status?.auto_update ? `每天 ${status.update_time} 自动更新（北京时间）` : '自动更新已关闭，仅手动更新' }}</span><button type="button" :disabled="!loaded || busy" @click="refresh">刷新状态</button><button v-if="status?.running" type="button" :disabled="busy" @click="stop">停止更新</button></div>
      <p v-if="statusError" class="vw-message bad" role="alert">{{ statusError }}</p>
      <p v-if="status?.running" class="vw-progress" role="status">正在更新 {{ currentName }} · 已完成 {{ status.progress.done }}/{{ status.progress.total }} 个来源 · 已匹配 {{ status.progress.matched }}/{{ status.progress.checked }} 条</p>
      <div class="vw-ledger">
        <div v-for="row in rows" :key="row.id" class="vw-row">
          <div class="vw-source"><strong>{{ row.name }}</strong><span class="vw-state" :class="row.state">{{ !row.enabled ? '未选择' : stateLabels[row.state] || row.state }}</span></div>
          <div class="vw-detail"><span>{{ row.count || 0 }} 条 · {{ date(row.last_success) }}</span><p v-if="row.error" :class="{ 'vw-error': row.state === 'failed' }">{{ row.error }}</p><p v-else-if="row.unmatched">{{ row.unmatched }} 条未匹配到 TMDB 或海报，不显示在客户端。</p></div>
          <div class="vw-row-actions"><button type="button" :disabled="!loaded || busy || !row.count" @click="showPreview(row.id)">预览</button><button type="button" :disabled="!loaded || busy || status?.running || !row.enabled" @click="update(row.id)">更新</button></div>
        </div>
      </div>
      <div v-if="preview" class="vw-preview"><header class="vw-heading"><h4>{{ sources.find(([id]) => id === preview.source)?.[1] }} 预览</h4><button type="button" @click="preview = null">收起预览</button></header><p v-if="!previewRows.length">还没有可预览的榜单，请先更新这个来源。</p><ul v-else><li v-for="(item, index) in previewRows" :key="index"><strong>{{ item.title }}</strong><span>{{ item.category }} · {{ item.mediaType === 'tv' ? '剧集' : '电影' }} · TMDB {{ item.tmdbId }}</span></li></ul><p class="vw-note">最多显示前 60 条，客户端仍可分页读取全部缓存。</p></div>
    </section>

    <section v-show="tab === 'config'" id="vw-panel-config" role="tabpanel" aria-labelledby="vw-tab-config">
      <header class="vw-heading"><div><h3>采集与更新设置</h3><p>采集使用平台网络与代理，不需要另外安装 Node 或开放端口。</p></div></header>
      <fieldset :disabled="!loaded || busy" class="vw-fields">
        <div class="vw-field"><label for="vw-tmdb">TMDB 密钥</label><div class="vw-secret"><input id="vw-tmdb" v-model="values.tmdb_key" :type="visible.tmdb_key ? 'text' : 'password'" autocomplete="off" spellcheck="false" :aria-invalid="!!errors.tmdb_key"><button type="button" @click="reveal('tmdb_key')">{{ visible.tmdb_key ? '隐藏' : '查看' }}</button></div><p>生成可用榜单必填。支持 v3 API Key 或 v4 API Read Access Token，不会写入 Widget。</p><p v-if="errors.tmdb_key" class="vw-error">{{ errors.tmdb_key }}</p></div>
        <div class="vw-field"><label for="vw-trakt">Trakt Client ID（仅 Trakt 使用）</label><div class="vw-secret"><input id="vw-trakt" v-model="values.trakt_client_id" :type="visible.trakt_client_id ? 'text' : 'password'" autocomplete="off" spellcheck="false"><button type="button" @click="reveal('trakt_client_id')">{{ visible.trakt_client_id ? '隐藏' : '查看' }}</button></div><p>填写 Trakt 应用的 Client ID，不是 OAuth Token。留空只跳过 Trakt，其他来源照常更新。</p><p v-if="errors.trakt_client_id" class="vw-error">{{ errors.trakt_client_id }}</p></div>
        <div class="vw-field vw-full"><span class="vw-label" id="vw-sources-label">采集哪些榜单</span><div class="vw-choices" role="group" aria-labelledby="vw-sources-label"><label v-for="[id, name] in sources" :key="id"><input v-model="values.sources" type="checkbox" :value="id">{{ name }}</label></div><p>默认选择全部十个来源；取消选择后不再采集或向客户端提供该来源，原有缓存不会删除。</p><p v-if="errors.sources" class="vw-error">{{ errors.sources }}</p></div>
        <div class="vw-field"><label for="vw-limit">每个分类最多采集多少条</label><input id="vw-limit" v-model.number="values.category_limit" type="number" min="10" max="100" step="1" :aria-invalid="!!errors.category_limit"><p>默认 30 条，可填 10～100。条数越多，TMDB 请求和更新时间越多。</p><p v-if="errors.category_limit" class="vw-error">{{ errors.category_limit }}</p></div>
        <div class="vw-field"><label for="vw-time">每天几点更新（北京时间）</label><input id="vw-time" v-model="values.update_time" type="time" :aria-invalid="!!errors.update_time"><p>默认 17:00。不开启下面的自动更新时，不会定时执行。</p><p v-if="errors.update_time" class="vw-error">{{ errors.update_time }}</p></div>
        <div class="vw-field vw-full vw-toggles"><label><input v-model="values.auto_update" type="checkbox" role="switch">每天自动更新</label><p>默认关闭。开启后每天只在指定时间执行，没有频繁空轮询。</p><label><input v-model="values.notify_results" type="checkbox" role="switch">更新完成后通知</label><p>默认关闭。使用平台关联的通知渠道，不重复填写机器人。</p></div>
        <div class="vw-field vw-full vw-subsection"><h4>客户端读取</h4><label for="vw-base">平台访问地址</label><input id="vw-base" v-model="values.public_base_url" type="url" placeholder="https://bot.example.com" :aria-invalid="!!errors.public_base_url"><p>填平台地址，不含 /api 路径；有部署子路径需带上。客户端必须能够访问这个地址。</p><p v-if="errors.public_base_url" class="vw-error">{{ errors.public_base_url }}</p><label class="vw-check"><input v-model="values.public_enabled" type="checkbox" role="switch">允许客户端读取 Widget</label><p>默认关闭。开启后，持有地址的人只能读取影视榜单，不能更新或查看 TMDB 密钥。</p></div>
      </fieldset>
    </section>

    <section v-show="tab === 'widget'" id="vw-panel-widget" role="tabpanel" aria-labelledby="vw-tab-widget">
      <header class="vw-heading"><div><h3>导入影视榜单</h3><p>先更新榜单，再把这里的地址导入客户端。不需要另开一个服务端口。</p></div></header>
      <ol class="vw-steps"><li>在“配置”填写平台访问地址，开启“允许客户端读取 Widget”，保存。</li><li>在“榜单状态”更新需要的来源，确认有有效条目。</li><li>获取并复制地址，粘贴到 Forward 的 Widget 模块导入处。</li></ol>
      <p class="vw-note">输出使用 Forward 的 Widget 格式；Rex、Capy 等客户端请以其当前版本的导入支持为准。</p>
      <p class="vw-message" :class="{ bad: !status?.public_enabled }">{{ status?.public_enabled ? '客户端读取已开启。地址包含独立只读密钥，请不要公开分享。' : '客户端读取未开启。请先在配置中开启并保存。' }}</p>
      <div class="vw-address-actions"><button class="vw-primary" type="button" :disabled="!loaded || busy" @click="getAddress">获取 Widget 地址</button><button v-if="address" type="button" @click="copy">复制地址</button></div>
      <div v-if="address" class="vw-field"><label for="vw-address">只读 Widget 地址</label><textarea id="vw-address" :value="address" readonly rows="3" spellcheck="false"></textarea><p>TMDB 和 Trakt 密钥不会出现在这个地址或生成的模块中。</p></div>
      <details class="vw-maintenance"><summary>地址泄露或需要更换？</summary><p>更换只读密钥会让所有旧地址立即失效；已导入的客户端也要重新导入新地址。</p><button v-if="!rotateConfirm" type="button" :disabled="!loaded || busy" @click="rotateConfirm = true">更换只读密钥…</button><div v-else class="vw-confirm"><p>确认让所有旧 Widget 地址失效？</p><button class="vw-danger" type="button" :disabled="busy" @click="rotate">确认更换</button><button type="button" :disabled="busy" @click="rotateConfirm = false">取消</button></div></details>
    </section>
    <footer class="vw-footer"><div class="vw-save-state"><span>{{ dirty ? '有未保存的修改' : loaded ? '配置已读取' : '等待读取配置' }}</span><p v-if="saveNotice" :class="{ 'vw-error': saveFailed }" :role="saveFailed ? 'alert' : 'status'">{{ saveNotice }}<span v-if="saveFailed"> 可点击“保存配置”重试。</span></p></div><div class="vw-save-actions"><button type="button" :disabled="busy || dirty" @click="load">重新读取</button><button class="vw-primary" type="button" :disabled="!loaded || busy" @click="save">{{ saving ? '正在保存…' : '保存配置' }}</button></div></footer>
  </div>
  </IosSettings>
</template>

<style scoped>
/* iOS source ledger, grouped configuration and Widget delivery. Data and actions are unchanged. */
.vw-config { min-width: 0; color: var(--ios-text); }
.vw-config h2, .vw-config h3, .vw-config h4, .vw-config p { margin: 0; }
.vw-page-head { padding: 4px 0 22px; }
.vw-page-head h2 { font-size: 22px; font-weight: 650; line-height: 1.4; letter-spacing: -.025em; }
.vw-config button { display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 9px 16px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font-weight: 500; cursor: pointer; }
.vw-config button:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.vw-config button:disabled { opacity: .5; cursor: not-allowed; }
.vw-config button.vw-primary { border-color: transparent; background: var(--ios-accent); color: #fff; font-weight: 600; }
.vw-config button.vw-primary:hover:not(:disabled) { filter: brightness(1.08); }
.vw-config button.vw-danger, .vw-error { color: var(--danger, #bd2733); }
.vw-tabs { position: relative; isolation: isolate; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; width: 100%; max-width: 540px; margin-bottom: 24px; padding: 4px; border-radius: 16px; background: var(--ios-inset); }
.vw-tabs::before { content: ''; position: absolute; inset: 4px auto 4px 4px; width: calc((100% - 16px) / 3); border-radius: 12px; background: var(--ios-control); box-shadow: 0 2px 5px rgb(0 0 0 / .08); transform: translateX(calc(var(--vw-tab-index) * (100% + 4px))); transition: transform var(--ios-duration) var(--ios-ease); pointer-events: none; z-index: -1; }
.vw-config .vw-tabs button { min-height: 42px; padding: 8px 12px; border: 0; border-radius: 12px; background: transparent; color: var(--ios-secondary); }
.vw-config .vw-tabs button.active { color: var(--ios-text); font-weight: 650; }
.vw-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin: 0 4px 16px; }
.vw-heading h3 { font-size: 16px; font-weight: 650; line-height: 1.5; letter-spacing: -.015em; }
.vw-heading h4 { font-size: 15px; font-weight: 650; }
.vw-heading p { max-width: 70ch; margin-top: 5px; color: var(--ios-secondary); font-size: 13px; line-height: 1.65; }
.vw-heading > button { flex: 0 0 auto; }
.vw-note, .vw-field p, .vw-detail, .vw-toolbar, .vw-preview li span, .vw-footer { color: var(--ios-secondary); font-size: 12px; line-height: 1.7; }
.vw-message { display: block; padding: 14px 18px; margin-bottom: 16px !important; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); color: var(--ios-text); font-size: 13px; line-height: 1.7; overflow-wrap: anywhere; }
.vw-message.bad { color: var(--danger, #bd2733); }
.vw-message button { margin-left: 8px; }
.vw-toolbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin: 12px 0 16px; }
.vw-toolbar > span { flex: 1; min-width: 180px; }
.vw-progress { margin-bottom: 14px !important; padding: 12px 16px; border-radius: 12px; background: var(--ios-inset); color: var(--accent, #0063dc); font-size: 13px; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.vw-ledger { overflow: hidden; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.vw-row { display: grid; grid-template-columns: minmax(105px, .7fr) minmax(0, 1.7fr) auto; align-items: center; gap: 16px; padding: 17px 20px; }
.vw-row + .vw-row { border-top: 1px solid var(--ios-line); }
.vw-source { display: flex; align-items: flex-start; flex-direction: column; gap: 4px; min-width: 0; }
.vw-source strong { font-size: 14px; font-weight: 600; overflow-wrap: anywhere; }
.vw-state { color: var(--ios-secondary); font-size: 12px; }
.vw-state.success { color: var(--success, #087758); }
.vw-state.running { color: var(--accent, #0063dc); }
.vw-state.failed { color: var(--danger, #bd2733); }
.vw-detail { min-width: 0; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.vw-detail p { max-height: 132px; margin-top: 4px; overflow: auto; }
.vw-row-actions { display: flex; gap: 8px; }
.vw-preview { margin-top: 26px; padding: 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.vw-preview .vw-heading { margin-inline: 0; }
.vw-preview ul { max-height: 360px; margin: 0 0 12px; padding: 0; list-style: none; overflow: auto; scrollbar-width: thin; scrollbar-color: var(--ios-line) transparent; }
.vw-preview li { display: flex; flex-direction: column; gap: 4px; padding: 13px 0; border-bottom: 1px solid var(--ios-line); }
.vw-preview li:last-child { border-bottom: 0; }
.vw-preview li strong { font-weight: 600; font-size: 13px; overflow-wrap: anywhere; }
.vw-preview li span { overflow-wrap: anywhere; }
.vw-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 22px 24px; min-width: 0; margin: 0; padding: 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.vw-field { min-width: 0; }
.vw-field.vw-full { grid-column: 1 / -1; }
.vw-field > label, .vw-label { display: block; margin-bottom: 8px; font-size: 13px; font-weight: 500; }
.vw-field input:not([type='checkbox']), .vw-field textarea { display: block; min-width: 0; width: 100%; min-height: 44px; padding: 10px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-text); transition: border-color var(--ios-fast) ease; }
.vw-field input:focus, .vw-field textarea:focus { border-color: var(--accent, #0063dc); }
.vw-field input[aria-invalid='true'] { border-color: var(--danger, #bd2733); }
.vw-field textarea { line-height: 1.7; resize: vertical; }
.vw-field input[type='checkbox'] { flex: 0 0 18px; width: 18px; height: 18px; margin: 0; accent-color: var(--ios-accent); }
.vw-field p { margin-top: 7px; max-width: 72ch; overflow-wrap: anywhere; }
.vw-field p.vw-error { color: var(--danger, #bd2733); }
.vw-secret { display: flex; gap: 8px; }
.vw-secret button { flex: 0 0 auto; }
.vw-choices { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px 20px; }
.vw-choices label { display: flex; align-items: center; gap: 9px; min-width: 0; min-height: 42px; margin: 0; padding: 7px 10px; border: 1px solid var(--ios-line); border-radius: 11px; color: var(--ios-secondary); font-size: 13px; cursor: pointer; }
.vw-choices label:has(input:checked) { border-color: var(--accent, #0063dc); color: var(--ios-text); background: var(--accent-dim, #e8f1ff); }
.vw-toggles { padding-top: 16px; border-top: 1px solid var(--ios-line); }
.vw-toggles label, .vw-field label.vw-check { display: flex; align-items: center; flex-direction: row-reverse; justify-content: space-between; gap: 20px; min-height: 44px; margin: 0; color: var(--ios-text); cursor: pointer; }
.vw-toggles label:not(:first-child) { margin-top: 20px; padding-top: 18px; border-top: 1px solid var(--ios-line); }
.vw-toggles p { margin-top: 4px; padding-right: 66px; }
.vw-config .vw-toggles input, .vw-config .vw-check input { appearance: none; -webkit-appearance: none; position: relative; display: block; flex: 0 0 50px; width: 50px; height: 30px; margin: 0; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); cursor: pointer; transition: background-color var(--ios-fast) ease, border-color var(--ios-fast) ease; }
.vw-config .vw-toggles input::before, .vw-config .vw-check input::before { content: ''; position: absolute; top: 2px; left: 2px; width: 24px; height: 24px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .18); transition: transform var(--ios-duration) var(--ios-ease); }
.vw-config .vw-toggles input:checked, .vw-config .vw-check input:checked { border-color: transparent; background: var(--ios-accent); }
.vw-config .vw-toggles input:checked::before, .vw-config .vw-check input:checked::before { transform: translateX(20px); }
.vw-config .vw-toggles input:active::before, .vw-config .vw-check input:active::before { transform: scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.vw-config .vw-toggles input:checked:active::before, .vw-config .vw-check input:checked:active::before { transform: translateX(20px) scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.vw-fields:disabled { opacity: .65; }
.vw-fields:disabled label, .vw-fields:disabled input { cursor: not-allowed; }
.vw-subsection { padding-top: 22px; border-top: 1px solid var(--ios-line); }
.vw-subsection h4 { margin-bottom: 18px; font-size: 14px; font-weight: 650; }
.vw-field.vw-subsection .vw-check { margin-top: 20px; }
.vw-steps { margin: 0 0 16px; padding: 18px 20px 8px 42px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.vw-steps li { padding-left: 4px; margin-bottom: 12px; line-height: 1.75; font-size: 13px; }
#vw-panel-widget > .vw-note { margin-bottom: 18px; }
.vw-address-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 18px; }
#vw-panel-widget > .vw-field { padding: 18px 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.vw-maintenance { margin-top: 26px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); overflow: hidden; }
.vw-maintenance summary { position: relative; min-height: 52px; padding: 14px 46px 14px 20px; list-style: none; font-weight: 500; cursor: pointer; }
.vw-maintenance summary::-webkit-details-marker { display: none; }
.vw-maintenance summary::after { content: ''; position: absolute; right: 22px; top: 21px; width: 8px; height: 8px; border-top: 1.5px solid currentColor; border-right: 1.5px solid currentColor; transform: rotate(45deg); transition: transform var(--ios-duration) var(--ios-ease); }
.vw-maintenance[open] summary::after { transform: rotate(135deg); }
.vw-maintenance p { margin: 0 20px 14px; max-width: 72ch; color: var(--ios-secondary); font-size: 12px; line-height: 1.75; }
.vw-maintenance > button { margin: 0 20px 18px; }
.vw-confirm { padding-bottom: 18px; }
.vw-confirm button { margin-left: 20px; }
.vw-confirm button + button { margin-left: 8px; }
.vw-footer { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; margin-top: 28px; padding-top: 18px; }
.vw-save-state { flex: 1; min-width: 0; max-width: 65ch; }
.vw-save-state p { margin-top: 5px; font-size: 12px; overflow-wrap: anywhere; }
.vw-save-actions { display: flex; flex: 0 0 auto; gap: 10px; }
:global(html[data-theme='transparent'] .vw-ledger),
:global(html[data-theme='transparent'] .vw-fields),
:global(html[data-theme='transparent'] .vw-preview),
:global(html[data-theme='transparent'] .vw-message),
:global(html[data-theme='transparent'] .vw-maintenance),
:global(html[data-theme='transparent'] .vw-steps),
:global(html[data-theme='transparent'] #vw-panel-widget > .vw-field) { backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); -webkit-backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); }
@container (max-width: 620px) {
  .vw-page-head h2 { font-size: 20px; }
  .vw-tabs { max-width: none; margin-bottom: 20px; }
  .vw-config .vw-tabs button { padding-inline: 8px; font-size: 13px; }
  .vw-heading { flex-wrap: wrap; gap: 12px; }
  .vw-heading > div { flex: 1 1 100%; }
  .vw-fields { grid-template-columns: minmax(0, 1fr); padding: 16px; gap: 22px; }
  .vw-choices { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 12px; }
  .vw-row { grid-template-columns: minmax(0, 1fr) auto; gap: 6px 16px; padding: 16px; }
  .vw-source { grid-column: 1; flex-direction: row; flex-wrap: wrap; gap: 8px; align-items: center; }
  .vw-detail { grid-column: 1; }
  .vw-row-actions { grid-column: 2; grid-row: 1 / 3; flex-direction: column; }
  .vw-config .vw-row-actions button { min-height: 40px; padding: 7px 12px; }
  .vw-preview { padding: 16px; }
  .vw-field input:not([type='checkbox']), .vw-field textarea { font-size: 16px; }
  .vw-footer { align-items: flex-start; flex-direction: column; }
  .vw-save-actions { width: 100%; }
  .vw-save-actions button { flex: 1; }
  .vw-toolbar > span { flex: 1 1 100%; }
  .vw-toggles p { padding-right: 0; }
}
@container (max-width: 360px) {
  .vw-tabs { gap: 2px; }
  .vw-tabs::before { width: calc((100% - 12px) / 3); transform: translateX(calc(var(--vw-tab-index) * (100% + 2px))); }
  .vw-config .vw-tabs button { font-size: 12px; padding-inline: 5px; }
  .vw-address-actions { flex-direction: column; }
}
@media (forced-colors: active) {
  .vw-config .vw-toggles input, .vw-config .vw-check input { appearance: auto; -webkit-appearance: auto; }
  .vw-config .vw-toggles input::before, .vw-config .vw-check input::before { display: none; }
  .vw-tabs::before { border: 2px solid Highlight; }
}
</style>
