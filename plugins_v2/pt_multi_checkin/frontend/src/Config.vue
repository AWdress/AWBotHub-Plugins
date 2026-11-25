<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

const props = defineProps({ pluginId: { type: String, required: true }, host: { type: Object, required: true } })
const config = reactive({ auto_checkin: true, notify_result: true, headless: true, checkin_hour: 8, checkin_minute: 10, u2_checkin_hour: 9, u2_checkin_minute: 0, retry_count: 2, retry_interval: 20, failed_retry_count: 3, tjupt_ai_assist: true, tjupt_confirm_timeout: 300, selected_sites: [], custom_sites: [], piggo_username: '', piggo_password: '' })
const sites = ref([]), history = ref([]), logs = ref([]), cookieState = reactive({})
const status = reactive({ running: false, current: '', phase: '', message: '', completed: 0, total: 0, finished_at: '' })
const loading = ref(true), loadingError = ref(''), saving = ref(false), checking = ref(false)
const failedRetryInput = ref(null), failedRetryError = ref('')
let timer
const groups = computed(() => Object.entries(sites.value.reduce((all, site) => ((all[site.group] ||= []).push(site), all), {})))
const progress = computed(() => status.total ? Math.round(status.completed / status.total * 100) : 0)
const piggoSelected = computed(() => sites.value.some(site => config.selected_sites.includes(site.key) && ['piggo.me', 'www.piggo.me'].includes(site.domain)))

function withoutLegacyPiggoToken(values) {
  const cleaned = { ...values }
  delete cleaned.piggo_token
  return cleaned
}
async function saveValues(values) {
  const payload = withoutLegacyPiggoToken(values)
  const result = await props.host.saveConfig(payload)
  if (result?.ok === false) throw new Error(result.message || '配置未保存，请重试')
  // 已保存掩码照常提交以保留原密码；保存成功后不在页面状态中留存明文。
  config.piggo_password = (result?.values?.piggo_password ?? payload.piggo_password) ? '********' : ''
}

function withTimeout(promise, label, timeout = 12000) {
  return Promise.race([promise, new Promise((_, reject) => setTimeout(() => reject(new Error(`${label}超时，请确认插件已启用并重新加载`)), timeout))])
}
async function refresh() {
  const [statusResult, historyResult, logsResult] = await Promise.allSettled([
    withTimeout(props.host.callApi('/status'), '读取运行状态'),
    withTimeout(props.host.callApi('/history'), '读取运行记录'),
    withTimeout(props.host.callApi('/logs'), '读取运行日志'),
  ])
  if (statusResult.status === 'fulfilled') Object.assign(status, statusResult.value)
  if (historyResult.status === 'fulfilled') history.value = historyResult.value.items || []
  if (logsResult.status === 'fulfilled') logs.value = logsResult.value.items || []
  if (status.running && !timer) timer = setInterval(refresh, 2500)
  if (!status.running && timer) { clearInterval(timer); timer = null }
}
async function load() {
  loading.value = true; loadingError.value = ''
  try {
    const [saved, meta] = await Promise.all([
      withTimeout(props.host.getConfig(), '读取插件配置'),
      withTimeout(props.host.callApi('/meta'), '读取签到站点'),
    ])
    Object.assign(config, withoutLegacyPiggoToken(meta.defaults), withoutLegacyPiggoToken(saved))
    if (config.failed_retry_count == null) config.failed_retry_count = 3
    sites.value = meta.sites || []
    if (!Array.isArray(config.selected_sites)) config.selected_sites = sites.value.map(site => site.key)
    const customKeys = sites.value.filter(site => site.group === '通用签到').map(site => site.key)
    if (customKeys.length && !customKeys.some(key => config.selected_sites.includes(key))) config.selected_sites.push(...customKeys)
    await refresh()
  } catch (error) { loadingError.value = error.message || String(error); props.host.toast.error(`读取失败：${loadingError.value}`) }
  finally { loading.value = false }
}
async function save() {
  saving.value = true
  try {
    if (!Number.isInteger(config.failed_retry_count) || config.failed_retry_count < 0 || config.failed_retry_count > 10) {
      failedRetryError.value = '失败后补签次数请填写 0～10 的整数，0 表示关闭补签。'
      failedRetryInput.value?.focus()
      throw new Error(failedRetryError.value)
    }
    failedRetryError.value = ''
    await saveValues({ ...config, piggo_username: config.piggo_username.trim(), selected_sites: [...config.selected_sites] })
    // 保存后重新取一次元数据，拿到后端为通用站点生成的稳定 key，并持久化选择状态。
    const meta = await props.host.callApi('/meta')
    sites.value = meta.sites || sites.value
    const customKeys = sites.value.filter(site => site.group === '通用签到').map(site => site.key)
    const merged = [...new Set([...config.selected_sites, ...customKeys])]
    if (merged.length !== config.selected_sites.length) {
      config.selected_sites = merged
      await saveValues({ ...config, selected_sites: merged })
    }
    props.host.toast.success('配置已保存')
  }
  catch (error) { props.host.toast.error(`保存失败：${error.message || error}`) }
  finally { saving.value = false }
}
async function run() {
  const result = await props.host.callApi('/run', { method: 'POST' })
  result.ok ? props.host.toast.success(result.message) : props.host.toast.error(result.message)
  await refresh(); if (!timer) timer = setInterval(refresh, 2500)
}
async function checkCookies() {
  checking.value = true
  try {
    Object.keys(cookieState).forEach(key => delete cookieState[key])
    const data = await props.host.callApi('/cookies/check', { method: 'POST', body: { selected_sites: [...config.selected_sites] } })
    ;(data.items || []).forEach(item => { cookieState[item.key] = item })
    props.host.toast[data.ok ? 'success' : 'warning'](data.ok ? '所选站点凭证已填写，实际有效性将在签到时验证' : (data.message || '部分站点缺少登录凭证，请查看站点提示'))
  }
  catch (error) { props.host.toast.error(`检查失败：${error.message || error}`) }
  finally { checking.value = false }
}
function toggleGroup(items, enabled) { const keys = new Set(config.selected_sites); items.forEach(site => enabled ? keys.add(site.key) : keys.delete(site.key)); config.selected_sites = [...keys] }
function addCustomSite() {
  if (!Array.isArray(config.custom_sites)) config.custom_sites = []
  config.custom_sites.push({ name: '', url: '' })
}
function removeCustomSite(index) {
  const item = config.custom_sites[index]
  const old = sites.value.filter(site => site.group === '通用签到')[index]
  if (old) config.selected_sites = config.selected_sites.filter(key => key !== old.key)
  config.custom_sites.splice(index, 1)
}
async function clearHistory() { const result = await props.host.callApi('/history/clear', { method: 'POST' }); if (result.ok) { history.value = []; props.host.toast.success(result.message) } }
async function clearLogs() { const result = await props.host.callApi('/logs/clear', { method: 'POST' }); if (result.ok) { props.host.toast.success(result.message); await refresh() } }
onMounted(load); onBeforeUnmount(() => timer && clearInterval(timer))
</script>

<template>
  <IosSettings>
  <main class="pt-ios" v-if="!loading && !loadingError">
    <header class="pt-ios-mast">
      <div class="pt-ios-title-block"><span class="pt-ios-brand-mark" aria-hidden="true">PT</span><div><h2>多站签到</h2><p>平台 Cookie 自动同步 · 猪猪支持账号登录 · 已选择 <b>{{ config.selected_sites.length }}</b> / {{ sites.length }} 个站点</p></div></div>
      <div class="pt-ios-mast-actions"><button type="button" class="pt-ios-button pt-ios-quiet" :disabled="checking || !config.selected_sites.length" @click="checkCookies"><span class="pt-ios-button-icon" aria-hidden="true"></span>{{ checking ? '正在检查' : '检查凭证' }}</button><button type="button" class="pt-ios-button pt-ios-primary" :disabled="status.running || !config.selected_sites.length" @click="run"><span class="pt-ios-play" aria-hidden="true"></span>{{ status.running ? '签到进行中' : '立即签到' }}</button></div>
    </header>

    <section class="pt-ios-control-rail" aria-label="签到设置">
      <div class="pt-ios-toggles">
        <label class="pt-ios-toggle"><input v-model="config.auto_checkin" type="checkbox" role="switch"><i></i><span>自动签到</span></label>
        <label class="pt-ios-toggle"><input v-model="config.notify_result" type="checkbox" role="switch"><i></i><span>结果推送</span></label>
        <label class="pt-ios-toggle"><input v-model="config.headless" type="checkbox" role="switch"><i></i><span>浏览器静默运行</span></label>
      </div>
      <div class="pt-ios-schedule-fields">
        <label><span>其他站点执行</span><span class="pt-ios-time-field"><input v-model.number="config.checkin_hour" aria-label="其他站点执行小时" type="number" min="0" max="23"><b>:</b><input v-model.number="config.checkin_minute" aria-label="其他站点执行分钟" type="number" min="0" max="59"></span></label>
        <label><span>U2 执行（≥09:00）</span><span class="pt-ios-time-field"><input v-model.number="config.u2_checkin_hour" aria-label="U2 执行小时" type="number" min="9" max="23"><b>:</b><input v-model.number="config.u2_checkin_minute" aria-label="U2 执行分钟" type="number" min="0" max="59"></span></label>
        <label><span>单站即时重试</span><input v-model.number="config.retry_count" type="number" min="0" max="5"></label>
        <label><span>即时重试间隔</span><span class="pt-ios-unit-field"><input v-model.number="config.retry_interval" type="number" min="5" max="300"><i>秒</i></span></label>
        <label><span>失败后补签次数</span><input ref="failedRetryInput" v-model.number="config.failed_retry_count" type="number" min="0" max="10" step="1" :aria-describedby="failedRetryError ? 'failed-retry-help failed-retry-error' : 'failed-retry-help'" :aria-invalid="!!failedRetryError" @input="failedRetryError = ''"></label>
        <p id="failed-retry-help" class="pt-ios-retry-note">首次签到失败后，每隔 30 分钟只补签仍失败的站点；默认最多 3 次，0 为关闭。成功后不再补签。</p>
        <p v-if="failedRetryError" id="failed-retry-error" class="pt-ios-retry-note pt-ios-retry-error" role="alert">{{ failedRetryError }}</p>
      </div>
    </section>

    <section v-if="status.running || status.finished_at" class="pt-ios-run-status" aria-live="polite">
      <span :class="['pt-ios-pulse', { active: status.running }]"></span><div><b>{{ status.running ? `${status.phase} · ${status.current}` : '最近任务已完成' }}</b><small>{{ status.message || `${status.completed} / ${status.total} 个站点` }}</small></div><strong>{{ progress }}%</strong><div class="pt-ios-progress"><i :style="{ width: `${progress}%` }"></i></div>
    </section>

    <section class="pt-ios-sites-panel">
      <div class="pt-ios-section-head"><div><h3>选择签到站点</h3><p>点击标签即可勾选。Cookie 由平台读取，猪猪需在下方填写登录凭证。</p></div><div class="pt-ios-section-actions"><button type="button" class="pt-ios-link-button" @click="toggleGroup(sites, true)">全选</button><span></span><button type="button" class="pt-ios-link-button" @click="toggleGroup(sites, false)">清空</button></div></div>
      <div v-for="[group, items] in groups" :key="group" class="pt-ios-site-group">
        <div class="pt-ios-group-title"><span>{{ group }}</span><small>{{ items.filter(site => config.selected_sites.includes(site.key)).length }}/{{ items.length }}</small><button type="button" @click="toggleGroup(items, !items.every(site => config.selected_sites.includes(site.key)))">{{ items.every(site => config.selected_sites.includes(site.key)) ? '取消本组' : '选择本组' }}</button></div>
        <div class="pt-ios-site-chips">
          <label v-for="site in items" :key="site.key" :class="['pt-ios-site-chip', { selected: config.selected_sites.includes(site.key), checked: cookieState[site.key]?.ok, missing: cookieState[site.key] && !cookieState[site.key].ok }]">
            <input v-model="config.selected_sites" type="checkbox" :value="site.key">
            <span class="pt-ios-checkmark"><i></i></span>
            <span class="pt-ios-site-badge">{{ site.name.slice(0, 2).toUpperCase() }}</span>
            <span class="pt-ios-site-copy"><span class="pt-ios-site-name"><b>{{ site.name }}</b><em v-if="site.status === 'pending'">待适配</em></span><small>{{ site.domain }}</small></span>
            <span v-if="cookieState[site.key]" class="pt-ios-cookie-dot" :title="cookieState[site.key].message"></span>
          </label>
        </div>
      </div>
      <section v-if="piggoSelected" class="pt-ios-piggo-login" aria-labelledby="piggo-login-title">
        <h3 id="piggo-login-title">猪猪登录</h3>
        <p id="piggo-login-help">仅填写猪猪网站的用户名和密码。每轮签到使用新的浏览器会话，通过官网登录页面登录，不复用历史登录凭证。</p>
        <div class="pt-ios-piggo-fields">
          <label for="piggo-username">猪猪用户名<input id="piggo-username" v-model="config.piggo_username" :disabled="saving" autocomplete="off" spellcheck="false" aria-describedby="piggo-login-help" placeholder="填写猪猪网站的用户名"></label>
          <label for="piggo-password">猪猪密码<input id="piggo-password" v-model="config.piggo_password" :disabled="saving" type="password" autocomplete="new-password" aria-describedby="piggo-password-help" :placeholder="config.piggo_password === '********' ? '已保存，直接输入可替换' : '填写网站登录密码'"></label>
        </div>
        <p id="piggo-password-help" class="pt-ios-piggo-note">密码保存后仅显示掩码。遇到验证码或二次验证时按日志提示处理，插件不会反复提交账号密码。登录与签到结果以官网确认为准。</p>
      </section>
      <div class="pt-ios-custom-sites">
        <div class="pt-ios-custom-head"><div><h3>任意站点通用签到</h3><p>填写站点名称和地址，插件会优先访问 /attendance.php；Cookie 仍由平台按域名同步。</p></div><button type="button" class="pt-ios-link-button" @click="addCustomSite">添加站点</button></div>
        <div v-if="config.custom_sites?.length" class="pt-ios-custom-list">
          <div v-for="(item, index) in config.custom_sites" :key="index" class="pt-ios-custom-row">
            <input v-model="item.name" aria-label="站点名称或账号" placeholder="站点名称 / 账号">
            <input v-model="item.url" aria-label="PT站点地址" placeholder="https://example.com">
            <button type="button" class="pt-ios-link-button pt-ios-danger" @click="removeCustomSite(index)">删除</button>
          </div>
        </div>
        <div v-else class="pt-ios-custom-empty">尚未添加通用站点</div>
      </div>
      <footer class="pt-ios-save-bar"><p><span class="pt-ios-shield" aria-hidden="true"></span>Cookie 只从平台读取，不会保存在插件配置中。</p><button type="button" class="pt-ios-button pt-ios-primary" :disabled="saving" @click="save">{{ saving ? '正在保存…' : '保存并应用' }}</button></footer>
    </section>

    <section class="pt-ios-history-panel">
      <div class="pt-ios-section-head"><div><h3>最近运行</h3><p>保留最近 30 次签到结果。</p></div><button type="button" class="pt-ios-link-button pt-ios-danger" :disabled="!history.length" @click="clearHistory">清空记录</button></div>
      <div class="pt-ios-history" v-if="history.length"><details v-for="item in history" :key="item.time"><summary><span :class="['pt-ios-result-mark', item.ok ? 'success' : 'failed']"></span><b>{{ item.summary }}</b><time>{{ item.time }}</time><span class="pt-ios-chevron"></span></summary><ul><li v-for="site in item.sites" :key="site.key || site.site"><span>{{ site.site }}</span><em :class="site.ok ? 'pt-ios-success-text' : 'pt-ios-failed-text'">{{ site.message }}</em></li></ul></details></div>
      <div v-else class="pt-ios-empty"><span class="pt-ios-empty-mark"></span><b>等待第一次签到</b><p>运行完成后，站点结果会显示在这里。</p></div>
    </section>

    <section class="pt-ios-history-panel pt-ios-log-panel">
      <div class="pt-ios-section-head"><div><h3>运行日志</h3><p>实时显示本次签到过程，最多保留 200 条。</p></div><button type="button" class="pt-ios-link-button pt-ios-danger" :disabled="!logs.length" @click="clearLogs">清空日志</button></div>
      <div class="pt-ios-runtime-logs" v-if="logs.length"><div v-for="(item, index) in logs" :key="`${item.time}-${index}`" :class="['pt-ios-log-row', item.level]"><time>{{ item.time }}</time><b>{{ item.site || '系统' }}</b><span>{{ item.message }}</span></div></div>
      <div v-else class="pt-ios-empty"><b>暂无运行日志</b><p>启动签到后，执行过程会实时显示在这里。</p></div>
    </section>
  </main>
  <div v-else-if="loading" class="pt-ios-loading">正在读取签到配置…</div>
  <div v-else class="pt-ios-load-error"><b>签到配置读取失败</b><p>{{ loadingError }}</p><button type="button" class="pt-ios-button pt-ios-primary" @click="load">重新加载</button></div>
  </IosSettings>
</template>

<style scoped>
.pt-ios { display: flex; flex-direction: column; gap: 22px; min-width: 0; color: var(--ios-text); }
.pt-ios *, .pt-ios *::before, .pt-ios *::after { box-sizing: border-box; }
.pt-ios h2, .pt-ios h3, .pt-ios p { margin: 0; }
.pt-ios h2 { font-size: 21px; font-weight: 650; letter-spacing: -.02em; }
.pt-ios h3 { font-size: 16px; font-weight: 650; letter-spacing: -.015em; }
.pt-ios p { color: var(--ios-secondary); font-size: 12px; line-height: 1.8; overflow-wrap: anywhere; }
.pt-ios-mast { display: flex; justify-content: space-between; align-items: center; gap: 20px; }
.pt-ios-title-block { display: flex; align-items: center; gap: 13px; min-width: 0; }
.pt-ios-title-block > div { min-width: 0; }
.pt-ios-brand-mark { display: grid; place-items: center; flex: none; width: 44px; height: 44px; border-radius: 13px; background: var(--ios-accent); color: #fff; font-size: 15px; font-weight: 700; }
.pt-ios-mast p { margin-top: 4px; }
.pt-ios-mast p b { color: var(--ios-text); font-variant-numeric: tabular-nums; }
.pt-ios-mast-actions, .pt-ios-section-actions { display: flex; align-items: center; gap: 9px; flex: none; }
.pt-ios-button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; padding: 9px 16px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font: inherit; font-weight: 500; white-space: nowrap; cursor: pointer; }
.pt-ios-button:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.pt-ios-button.pt-ios-primary { border-color: transparent; background: var(--ios-accent); color: #fff; font-weight: 600; }
.pt-ios-primary:hover:not(:disabled) { filter: brightness(1.08); }
.pt-ios-button:disabled, .pt-ios-link-button:disabled { opacity: .5; cursor: not-allowed; }
.pt-ios-button-icon { position: relative; width: 17px; height: 17px; border: 1px solid currentColor; border-radius: 5px; }
.pt-ios-button-icon::after, .pt-ios-shield::after, .pt-ios-result-mark.success::after, .pt-ios-empty-mark::after { content: ''; position: absolute; width: 8px; height: 5px; border-left: 2px solid currentColor; border-bottom: 2px solid currentColor; transform: translate(3px, 4px) rotate(-45deg); }
.pt-ios-play { width: 9px; height: 11px; background: currentColor; clip-path: polygon(0 0, 100% 50%, 0 100%); }
.pt-ios-control-rail { display: grid; grid-template-columns: minmax(0, .8fr) minmax(0, 1.2fr); border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-surface); overflow: hidden; }
.pt-ios-toggles { display: flex; flex-direction: column; padding: 5px 18px; border-right: 1px solid var(--ios-line); }
.pt-ios-toggle { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 16px; min-height: 64px; margin: 0; cursor: pointer; }
.pt-ios-toggle + .pt-ios-toggle { border-top: 1px solid var(--ios-line); }
.pt-ios-toggle > span { order: 1; }
.pt-ios-toggle input, .pt-ios-site-chip input { position: absolute; width: 1px; height: 1px; margin: 0; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.pt-ios-toggle > i { position: relative; display: block; flex: 0 0 50px; width: 50px; height: 30px; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); order: 2; transition: background var(--ios-fast) ease, border-color var(--ios-fast) ease; }
.pt-ios-toggle > i::after { content: ''; position: absolute; top: 2px; left: 2px; width: 24px; height: 24px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .2); transition: transform var(--ios-duration) var(--ios-ease); }
.pt-ios-toggle input:checked + i { background: var(--ios-accent); border-color: transparent; }
.pt-ios-toggle input:checked + i::after { transform: translateX(20px); }
.pt-ios-toggle input:focus-visible + i { outline: 3px solid var(--accent, #0063dc); outline-offset: 3px; }
.pt-ios-toggle:active > i::after { transform: scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.pt-ios-toggle:active input:checked + i::after { transform: translateX(20px) scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.pt-ios-schedule-fields { display: flex; flex-direction: column; padding: 0 18px 16px; }
.pt-ios-schedule-fields > label { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 62px; }
.pt-ios-schedule-fields > label + label { border-top: 1px solid var(--ios-line); }
.pt-ios-schedule-fields input { width: 70px; min-width: 70px; min-height: 40px; padding: 7px 10px; border: 1px solid var(--ios-line); border-radius: 11px; background: var(--ios-inset); color: var(--ios-text); text-align: center; font: inherit; font-variant-numeric: tabular-nums; }
.pt-ios-schedule-fields input[aria-invalid='true'] { border-color: var(--danger, #bd2733); }
.pt-ios-time-field, .pt-ios-unit-field { display: inline-flex; align-items: center; gap: 6px; flex: none; }
.pt-ios-time-field input { width: 55px; min-width: 55px; }
.pt-ios-time-field b, .pt-ios-unit-field i { color: var(--ios-secondary); font-style: normal; }
.pt-ios-schedule-fields > .pt-ios-retry-note { margin-top: 8px; }
.pt-ios-schedule-fields > .pt-ios-retry-error { color: var(--danger, #bd2733); }
.pt-ios-run-status { display: grid; grid-template-columns: 10px minmax(0, 1fr) auto; align-items: center; gap: 12px; padding: 16px 18px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); }
.pt-ios-run-status > div:first-of-type { display: flex; flex-direction: column; gap: 3px; min-width: 0; overflow-wrap: anywhere; }
.pt-ios-run-status small { color: var(--ios-secondary); }
.pt-ios-run-status strong { color: var(--accent, #0063dc); font-variant-numeric: tabular-nums; }
.pt-ios-pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--ios-secondary); }
.pt-ios-pulse.active { background: var(--success, #087758); }
.pt-ios-progress { grid-column: 1 / -1; height: 4px; overflow: hidden; border-radius: 3px; background: var(--ios-inset); }
.pt-ios-progress i { display: block; height: 100%; border-radius: inherit; background: var(--ios-accent); transition: width var(--ios-duration) var(--ios-ease); }
.pt-ios-sites-panel, .pt-ios-history-panel { border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-surface); overflow: hidden; }
.pt-ios-section-head { display: flex; justify-content: space-between; align-items: center; gap: 20px; padding: 19px 20px; border-bottom: 1px solid var(--ios-line); }
.pt-ios-section-head p { margin-top: 4px; }
.pt-ios-section-head > div { min-width: 0; }
.pt-ios-link-button, .pt-ios-group-title button { min-height: 36px; padding: 6px 3px; border: 0; border-radius: 6px; background: transparent; color: var(--accent, #0063dc); font: inherit; font-size: 12px; white-space: nowrap; cursor: pointer; }
.pt-ios-link-button.pt-ios-danger { color: var(--danger, #bd2733); }
.pt-ios-section-actions span { width: 1px; height: 13px; background: var(--ios-line); }
.pt-ios-site-group { padding: 0 20px 20px; }
.pt-ios-site-group + .pt-ios-site-group { border-top: 1px solid var(--ios-line); }
.pt-ios-group-title { display: flex; align-items: center; gap: 8px; padding: 15px 0 10px; }
.pt-ios-group-title > span { font-weight: 600; }
.pt-ios-group-title small { padding: 2px 6px; border-radius: 6px; background: var(--ios-inset); color: var(--ios-secondary); font-variant-numeric: tabular-nums; }
.pt-ios-group-title button { margin-left: auto; }
.pt-ios-site-chips { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(180px, 100%), 1fr)); gap: 9px; }
.pt-ios-site-chip { position: relative; display: grid; grid-template-columns: 18px 30px minmax(0, 1fr) 7px; align-items: center; gap: 8px; min-width: 0; min-height: 62px; padding: 10px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); cursor: pointer; user-select: none; transition: border-color var(--ios-fast), background var(--ios-fast); }
.pt-ios-site-chip:hover { border-color: var(--accent, #0063dc); }
.pt-ios-site-chip.selected { border-color: var(--accent, #0063dc); background: var(--accent-dim, #e8f1ff); }
.pt-ios-checkmark { display: grid; place-items: center; width: 18px; height: 18px; border: 1px solid var(--border-light, #b9bec9); border-radius: 5px; background: var(--ios-inset); }
.pt-ios-site-chip.selected .pt-ios-checkmark { background: var(--ios-accent); border-color: transparent; }
.pt-ios-site-chip.selected .pt-ios-checkmark i { width: 9px; height: 5px; border-left: 2px solid #fff; border-bottom: 2px solid #fff; transform: translateY(-1px) rotate(-45deg); }
.pt-ios-site-chip:has(input:focus-visible) { outline: 3px solid var(--accent, #0063dc); outline-offset: 3px; }
.pt-ios-site-badge { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 8px; background: var(--ios-control); color: var(--ios-secondary); font-size: 10px; font-weight: 650; }
.pt-ios-site-copy { min-width: 0; }
.pt-ios-site-copy b, .pt-ios-site-copy small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pt-ios-site-copy b { font-size: 13px; }
.pt-ios-site-copy small { color: var(--ios-secondary); font-size: 11px; }
.pt-ios-site-name { display: flex; align-items: center; gap: 5px; min-width: 0; }
.pt-ios-site-name > b { min-width: 0; }
.pt-ios-site-name > em { flex: none; padding: 1px 4px; border-radius: 4px; background: color-mix(in srgb, var(--warning, #926100) 10%, transparent); color: var(--warning, #926100); font-size: 9px; font-style: normal; }
.pt-ios-cookie-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--success, #087758); }
.pt-ios-site-chip.missing .pt-ios-cookie-dot { background: var(--danger, #bd2733); }
.pt-ios-piggo-login, .pt-ios-custom-sites { padding: 20px; border-top: 1px solid var(--ios-line); overflow-wrap: anywhere; }
.pt-ios-piggo-login p, .pt-ios-custom-head p { max-width: 75ch; margin-top: 6px; }
.pt-ios-piggo-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-top: 16px; }
.pt-ios-piggo-fields label { display: flex; flex-direction: column; gap: 8px; min-width: 0; font-size: 13px; }
.pt-ios-piggo-fields input, .pt-ios-custom-row input { width: 100%; min-width: 0; min-height: 44px; padding: 9px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-text); font: inherit; }
.pt-ios input:focus { border-color: var(--accent, #0063dc); }
.pt-ios-piggo-fields input:disabled { opacity: .65; cursor: wait; }
.pt-ios-custom-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.pt-ios-custom-list { display: grid; gap: 12px; margin-top: 16px; }
.pt-ios-custom-row { display: grid; grid-template-columns: minmax(100px, .7fr) minmax(160px, 1.3fr) auto; align-items: center; gap: 10px; }
.pt-ios-custom-empty { margin-top: 12px; padding: 18px; border-radius: 12px; background: var(--ios-inset); color: var(--ios-secondary); text-align: center; font-size: 12px; }
.pt-ios-save-bar { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 16px 20px; border-top: 1px solid var(--ios-line); background: var(--ios-inset); }
.pt-ios-save-bar p { display: flex; align-items: center; gap: 8px; }
.pt-ios-shield { position: relative; width: 18px; height: 18px; flex: none; border: 1px solid currentColor; border-radius: 6px; color: var(--success, #087758); }
.pt-ios-history details + details { border-top: 1px solid var(--ios-line); }
.pt-ios-history summary { display: grid; grid-template-columns: 24px minmax(0, 1fr) auto 12px; align-items: center; gap: 10px; min-height: 64px; padding: 14px 20px; cursor: pointer; list-style: none; }
.pt-ios-history summary::-webkit-details-marker { display: none; }
.pt-ios-history summary b { font-weight: 500; overflow-wrap: anywhere; }
.pt-ios-history time { color: var(--ios-secondary); font-size: 12px; font-variant-numeric: tabular-nums; }
.pt-ios-result-mark { position: relative; width: 22px; height: 22px; border-radius: 7px; }
.pt-ios-result-mark.success { color: var(--success, #087758); background: color-mix(in srgb, var(--success, #087758) 12%, transparent); }
.pt-ios-result-mark.failed { color: var(--danger, #bd2733); background: var(--danger-dim, #ffebed); }
.pt-ios-result-mark.failed::after { content: '!'; display: grid; place-items: center; width: 22px; height: 22px; font-size: 14px; font-weight: 700; }
.pt-ios-chevron { width: 7px; height: 7px; border-right: 1px solid var(--ios-secondary); border-bottom: 1px solid var(--ios-secondary); transform: rotate(45deg); transition: transform var(--ios-duration) var(--ios-ease); }
.pt-ios-history details[open] .pt-ios-chevron { transform: rotate(225deg); }
.pt-ios-history ul { margin: 0; padding: 0 20px 16px 54px; list-style: none; }
.pt-ios-history li { display: flex; justify-content: space-between; gap: 16px; padding: 6px 0; color: var(--ios-secondary); font-size: 13px; overflow-wrap: anywhere; }
.pt-ios-history em { font-style: normal; text-align: right; }
.pt-ios-success-text { color: var(--success, #087758); }
.pt-ios-failed-text { color: var(--danger, #bd2733); }
.pt-ios-empty { padding: 34px 24px; text-align: center; color: var(--ios-secondary); }
.pt-ios-empty b { display: block; color: var(--ios-text); font-weight: 600; }
.pt-ios-empty p { margin-top: 5px; }
.pt-ios-empty-mark { display: block; position: relative; width: 34px; height: 34px; margin: 0 auto 12px; border: 1px solid var(--ios-line); border-radius: 10px; background: var(--ios-inset); color: var(--accent, #0063dc); }
.pt-ios-empty-mark::after { width: 11px; height: 7px; transform: translate(10px, 10px) rotate(-45deg); }
.pt-ios-runtime-logs { max-height: 340px; overflow: auto; scrollbar-width: thin; scrollbar-color: var(--border-light, #b9bec9) transparent; }
.pt-ios-log-row { display: grid; grid-template-columns: 66px 100px minmax(0, 1fr); gap: 12px; padding: 11px 20px; font-size: 12px; line-height: 1.7; }
.pt-ios-log-row + .pt-ios-log-row { border-top: 1px solid var(--ios-line); }
.pt-ios-log-row time { color: var(--ios-secondary); font-variant-numeric: tabular-nums; }
.pt-ios-log-row b { overflow: hidden; color: var(--ios-text); font-weight: 500; text-overflow: ellipsis; white-space: nowrap; }
.pt-ios-log-row span { min-width: 0; color: var(--ios-secondary); overflow-wrap: anywhere; }
.pt-ios-log-row.success span { color: var(--success, #087758); }
.pt-ios-log-row.warning span { color: var(--warning, #926100); }
.pt-ios-log-row.error span { color: var(--danger, #bd2733); }
.pt-ios-loading { padding: 40px 24px; color: var(--ios-secondary); text-align: center; }
.pt-ios-load-error { padding: 32px 24px; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-surface); color: var(--ios-text); text-align: center; }
.pt-ios-load-error b { font-size: 17px; font-weight: 600; }
.pt-ios-load-error p { max-width: 75ch; margin: 10px auto 20px; color: var(--danger, #bd2733); overflow-wrap: anywhere; }
:global(html[data-theme='transparent'] .pt-ios-control-rail),
:global(html[data-theme='transparent'] .pt-ios-sites-panel),
:global(html[data-theme='transparent'] .pt-ios-history-panel),
:global(html[data-theme='transparent'] .pt-ios-run-status) { backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); -webkit-backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); }
@container (max-width: 760px) {
  .pt-ios-mast { align-items: stretch; flex-direction: column; gap: 16px; }
  .pt-ios-mast-actions .pt-ios-button { flex: 1; }
  .pt-ios-control-rail { grid-template-columns: minmax(0, 1fr); }
  .pt-ios-toggles { border-right: 0; border-bottom: 1px solid var(--ios-line); }
  .pt-ios-schedule-fields { padding-top: 3px; }
}
@container (max-width: 520px) {
  .pt-ios { gap: 18px; }
  .pt-ios-section-head { padding: 16px; align-items: flex-start; gap: 12px; }
  .pt-ios-site-group { padding-inline: 16px; }
  .pt-ios-site-chips { grid-template-columns: minmax(0, 1fr); }
  .pt-ios-piggo-login, .pt-ios-custom-sites { padding: 16px; }
  .pt-ios-piggo-fields { grid-template-columns: minmax(0, 1fr); }
  .pt-ios-custom-head { align-items: flex-start; flex-direction: column; gap: 8px; }
  .pt-ios-custom-row { grid-template-columns: minmax(0, 1fr); padding-top: 12px; }
  .pt-ios-custom-row + .pt-ios-custom-row { border-top: 1px solid var(--ios-line); }
  .pt-ios-custom-row .pt-ios-link-button { justify-self: start; }
  .pt-ios-save-bar { flex-direction: column; align-items: stretch; padding: 16px; gap: 14px; }
  .pt-ios-history summary { grid-template-columns: 24px minmax(0, 1fr) 12px; padding-inline: 16px; }
  .pt-ios-history time { grid-column: 2; grid-row: 2; }
  .pt-ios-history .pt-ios-chevron { grid-column: 3; grid-row: 1; }
  .pt-ios-history ul { padding-inline: 50px 16px; }
  .pt-ios-history li { flex-direction: column; gap: 3px; }
  .pt-ios-history em { text-align: left; }
  .pt-ios-log-row { grid-template-columns: 66px minmax(0, 1fr); gap: 3px 10px; padding-inline: 16px; }
  .pt-ios-log-row span { grid-column: 1 / -1; }
}
@media (forced-colors: active) {
  .pt-ios-toggle input, .pt-ios-site-chip input { position: static; width: 22px; height: 22px; clip-path: none; }
  .pt-ios-toggle > i, .pt-ios-site-chip .pt-ios-checkmark { display: none; }
}
</style>
