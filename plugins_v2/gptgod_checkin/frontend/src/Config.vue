<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

const props = defineProps({pluginId: String, host: {type: Object, required: true}})
const CronInput = computed(() => props.host.ui.CronInput)
const defaults = {
  auto_checkin: true, notify: true, auto_retry: true, accounts: [],
  schedule_mode: 'daily', checkin_hour: 8, checkin_minute: 5,
  cron_expression: '5 8 * * *', retry_count: 2, retry_interval: 20,
}
const form = reactive({...defaults})
const status = reactive({running: false, last_result: null, history: []})
const results = computed(() => {
  const accounts = status.last_result?.accounts
  return Array.isArray(accounts) ? accounts : []
})
const visible = reactive({})
const loading = ref(true)
const saving = ref(false)
const running = ref(false)
const loadError = ref('')
let timer

function toast(type, message) { props.host.toast?.[type]?.(message) }
function normalizeAccounts(value) {
  if (Array.isArray(value)) return value.map((item) => ({email: String(item?.email || ''), password: String(item?.password || '')}))
  if (typeof value !== 'string' || !value.trim() || value === '********') return []
  return value.split(/(?:\r?\n|\s+&\s+)/).map((item) => {
    const at = item.indexOf('----')
    return at < 0 ? null : {email: item.slice(0, at).trim(), password: item.slice(at + 4).trim()}
  }).filter((item) => item?.email && item?.password)
}
function addAccount() { form.accounts.push({email: '', password: ''}) }
function removeAccount(index) { form.accounts.splice(index, 1); delete visible[index] }

async function refresh() {
  try { Object.assign(status, await props.host.callApi('/status')) } catch {}
}
async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const saved = await props.host.getConfig()
    Object.assign(form, defaults, saved || {})
    if (saved?.accounts === '********') {
      const accounts = await props.host.revealSecret('accounts')
      form.accounts = normalizeAccounts(accounts)
    } else {
      form.accounts = normalizeAccounts(saved?.accounts)
    }
  } catch (error) {
    loadError.value = `读取账号配置失败：${error.message || error}`
  } finally {
    loading.value = false
  }
  await refresh()
  timer = setInterval(refresh, 3000)
}
async function save() {
  if (loadError.value) return toast('error', '账号配置尚未成功读取，请刷新后重试')
  const incomplete = form.accounts.findIndex((item) => !item.email.trim() || !item.password)
  if (incomplete >= 0) return toast('error', `账号 ${incomplete + 1} 的邮箱或密码未填写完整`)
  saving.value = true
  try {
    await props.host.saveConfig(JSON.parse(JSON.stringify(form)))
    toast('success', '配置已保存并应用')
  } catch (error) {
    toast('error', `保存失败：${error.message || error}`)
  } finally { saving.value = false }
}
async function runNow() {
  if (running.value || status.running) return
  running.value = true
  try {
    const result = await props.host.callApi('/run', {method: 'POST'})
    toast(result.ok === false ? 'error' : 'success', result.message || '签到已开始')
    await refresh()
  } catch (error) {
    toast('error', `启动失败：${error.message || error}`)
  } finally { running.value = false }
}

onMounted(load)
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <IosSettings>
  <main class="gpc-shell">
    <header class="gpc-page-head">
      <div>
        <h2>GPT-GOD 自动签到</h2>
        <p>逐个管理签到账号，密码默认隐藏并由平台受控保存。</p>
      </div>
      <span class="gpc-state" :class="{busy: status.running}">{{ status.running ? '签到中' : '就绪' }}</span>
    </header>

    <p v-if="loadError" class="gpc-alert" role="alert">{{ loadError }}</p>

    <section aria-labelledby="switches-title">
      <h3 id="switches-title">功能开关</h3>
      <div class="gpc-switch-grid">
        <label><span>启用自动签到</span><input v-model="form.auto_checkin" type="checkbox" role="switch"></label>
        <label><span>推送签到结果</span><input v-model="form.notify" type="checkbox" role="switch"></label>
        <label><span>失败后自动重试</span><input v-model="form.auto_retry" type="checkbox" role="switch"></label>
      </div>
    </section>

    <section aria-labelledby="accounts-title">
      <div class="gpc-section-head">
        <div><h3 id="accounts-title">签到账号</h3><p>一个账号一行，支持独立添加和删除。</p></div>
        <button class="gpc-secondary" type="button" :disabled="loading" @click="addAccount">添加账号</button>
      </div>
      <div v-if="loading" class="gpc-empty">正在安全读取账号配置…</div>
      <div v-else-if="!form.accounts.length" class="gpc-empty">尚未添加账号，点击“添加账号”开始配置。</div>
      <div v-else class="gpc-account-list">
        <article v-for="(account, index) in form.accounts" :key="index" class="gpc-account-row">
          <div class="gpc-row-number">{{ index + 1 }}</div>
          <label><span>登录邮箱</span><input v-model.trim="account.email" type="email" autocomplete="username" placeholder="name@example.com"></label>
          <label><span>账户密码</span><div class="gpc-secret"><input v-model="account.password" :type="visible[index] ? 'text' : 'password'" autocomplete="current-password" placeholder="GPT-GOD 账户密码"><button type="button" :aria-label="visible[index] ? '隐藏密码' : '显示密码'" @click="visible[index] = !visible[index]"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div></label>
          <button class="gpc-remove" type="button" @click="removeAccount(index)">删除</button>
        </article>
      </div>
    </section>

    <section aria-labelledby="schedule-title">
      <h3 id="schedule-title">定时与重试</h3>
      <div class="gpc-form-grid">
        <label><span>定时方式</span><select v-model="form.schedule_mode"><option value="daily">每天指定时间</option><option value="cron">Cron 表达式</option></select></label>
        <template v-if="form.schedule_mode === 'daily'">
          <label><span>签到小时</span><input v-model.number="form.checkin_hour" type="number" min="0" max="23"></label>
          <label><span>签到分钟</span><input v-model.number="form.checkin_minute" type="number" min="0" max="59"></label>
        </template>
        <label v-else class="gpc-wide"><span>Cron 表达式</span><component :is="CronInput" v-model="form.cron_expression" /></label>
        <label><span>失败重试次数</span><input v-model.number="form.retry_count" type="number" min="0" max="5"></label>
        <label><span>重试间隔（秒）</span><input v-model.number="form.retry_interval" type="number" min="5" max="300" step="5"></label>
      </div>
    </section>

    <footer class="gpc-actions">
      <button class="gpc-secondary" type="button" :disabled="running || status.running || !form.accounts.length" @click="runNow">{{ running || status.running ? '签到进行中…' : '立即签到' }}</button>
      <button class="gpc-primary" type="button" :disabled="saving || loading || !!loadError" @click="save">{{ saving ? '正在保存…' : '保存配置' }}</button>
    </footer>

    <section v-if="results.length" aria-labelledby="result-title">
      <div class="gpc-section-head">
        <div>
          <h3 id="result-title">最近签到结果</h3>
          <p>{{ status.last_result?.time || '' }}</p>
        </div>
      </div>
      <div class="gpc-result-list">
        <article v-for="(item, index) in results" :key="index" class="gpc-result-row">
          <span class="gpc-result-account">{{ item.account }}</span>
          <span class="gpc-result-state" :class="{failed: !item.ok}">{{ item.already ? '已签到' : (item.ok ? '成功' : '失败') }}</span>
          <span class="gpc-result-points">{{ item.points ? `剩余积分 ${item.points}` : '积分未读取' }}</span>
        </article>
      </div>
    </section>
  </main>
  </IosSettings>
</template>

<style scoped>
/* iOS grouped account settings; all original scheduling, credentials and actions are retained. */
.gpc-shell { display: grid; gap: 28px; min-width: 0; color: var(--ios-text); }
.gpc-shell h2, .gpc-shell h3, .gpc-shell p { margin: 0; }
.gpc-page-head, .gpc-section-head, .gpc-actions { display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.gpc-page-head { padding: 4px 0 0; align-items: flex-start; }
.gpc-page-head h2 { font-size: 22px; font-weight: 650; line-height: 1.4; letter-spacing: -.025em; }
.gpc-page-head p, .gpc-section-head p { max-width: 70ch; margin-top: 5px; color: var(--ios-secondary); font-size: 13px; line-height: 1.6; }
.gpc-shell h3 { font-size: 15px; font-weight: 650; line-height: 1.5; }
.gpc-shell section > h3 { margin: 0 4px 12px; }
.gpc-section-head { margin: 0 4px 14px; align-items: flex-start; }
.gpc-state { flex: 0 0 auto; padding: 5px 9px; border-radius: 8px; color: var(--ios-secondary); background: var(--ios-inset); font-size: 12px; }
.gpc-state.busy { color: var(--accent, #0063dc); background: var(--accent-dim, #e8f1ff); }
.gpc-alert { padding: 14px 18px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); color: var(--danger, #bd2733); font-size: 13px; overflow-wrap: anywhere; }
.gpc-switch-grid { padding: 0 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.gpc-switch-grid label { display: flex; align-items: center; justify-content: space-between; gap: 20px; min-height: 66px; padding: 13px 0; cursor: pointer; }
.gpc-switch-grid label + label { border-top: 1px solid var(--ios-line); }
.gpc-switch-grid label > span { flex: 1; margin: 0; color: var(--ios-text); font-size: 14px; }
.gpc-shell input[type='checkbox'] { appearance: none; -webkit-appearance: none; position: relative; display: block; flex: 0 0 50px; width: 50px; height: 30px; margin: 0; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); cursor: pointer; transition: background-color var(--ios-fast) ease, border-color var(--ios-fast) ease; }
.gpc-shell input[type='checkbox']::before { content: ''; position: absolute; top: 2px; left: 2px; width: 24px; height: 24px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .18); transition: transform var(--ios-duration) var(--ios-ease); }
.gpc-shell input[type='checkbox']:checked { border-color: transparent; background: var(--ios-accent); }
.gpc-shell input[type='checkbox']:checked::before { transform: translateX(20px); }
.gpc-shell input[type='checkbox']:active::before { transform: scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.gpc-shell input[type='checkbox']:checked:active::before { transform: translateX(20px) scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.gpc-secondary, .gpc-primary, .gpc-remove { display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 9px 16px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font-weight: 500; cursor: pointer; }
.gpc-secondary:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.gpc-primary { min-width: 132px; border-color: transparent; background: var(--ios-accent); color: #fff; font-weight: 600; }
.gpc-primary:hover:not(:disabled) { filter: brightness(1.08); }
.gpc-remove { padding-inline: 12px; border-color: transparent; background: transparent; color: var(--danger, #bd2733); }
.gpc-remove:hover { background: color-mix(in srgb, var(--danger, #bd2733) 8%, transparent); }
.gpc-shell button:disabled { opacity: .5; cursor: not-allowed; }
.gpc-account-list { overflow: hidden; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.gpc-account-row { display: grid; grid-template-columns: 28px minmax(0, 1fr) minmax(0, 1fr) auto; align-items: end; gap: 16px; padding: 20px; }
.gpc-account-row + .gpc-account-row { border-top: 1px solid var(--ios-line); }
.gpc-row-number { display: grid; place-items: center; align-self: center; width: 28px; height: 28px; border-radius: 8px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 12px; font-variant-numeric: tabular-nums; }
.gpc-shell label { min-width: 0; }
.gpc-shell label > span { display: block; margin-bottom: 7px; color: var(--ios-secondary); font-size: 12px; line-height: 1.6; }
.gpc-shell .gpc-switch-grid label > span { margin-bottom: 0; color: var(--ios-text); font-size: 14px; }
.gpc-shell input:not([type='checkbox']), .gpc-shell select { display: block; min-width: 0; width: 100%; min-height: 44px; padding: 10px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-text); transition: border-color var(--ios-fast) ease; }
.gpc-shell input:not([type='checkbox']):focus, .gpc-shell select:focus { border-color: var(--accent, #0063dc); }
.gpc-secret { position: relative; }
.gpc-shell .gpc-secret input { padding-right: 50px; }
.gpc-secret button { position: absolute; inset-inline-end: 0; top: 0; display: grid; place-items: center; width: 44px; height: 44px; border: 0; border-radius: 12px; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.gpc-secret button:hover { color: var(--ios-text); }
.gpc-secret svg { width: 19px; height: 19px; fill: none; stroke: currentColor; stroke-width: 1.8; }
.gpc-empty { padding: 36px 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); color: var(--ios-secondary); font-size: 13px; text-align: center; }
.gpc-form-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px 20px; min-width: 0; padding: 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.gpc-form-grid .gpc-wide { grid-column: 1 / -1; }
.gpc-actions { justify-content: flex-end; padding-top: 0; gap: 12px; }
.gpc-result-list { overflow: hidden; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.gpc-result-row { display: grid; grid-template-columns: minmax(0, 1fr) 90px minmax(0, 1fr); align-items: center; gap: 12px; padding: 16px 20px; }
.gpc-result-row + .gpc-result-row { border-top: 1px solid var(--ios-line); }
.gpc-result-account { min-width: 0; overflow-wrap: anywhere; }
.gpc-result-state { color: var(--success, #087758); font-size: 13px; }
.gpc-result-state.failed { color: var(--danger, #bd2733); }
.gpc-result-points { color: var(--ios-secondary); font-size: 12px; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
:global(html[data-theme='transparent'] .gpc-switch-grid),
:global(html[data-theme='transparent'] .gpc-account-list),
:global(html[data-theme='transparent'] .gpc-form-grid),
:global(html[data-theme='transparent'] .gpc-result-list),
:global(html[data-theme='transparent'] .gpc-empty),
:global(html[data-theme='transparent'] .gpc-alert) { backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); -webkit-backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); }
@container (max-width: 620px) {
  .gpc-page-head h2 { font-size: 20px; }
  .gpc-section-head { align-items: flex-start; flex-wrap: wrap; gap: 12px; }
  .gpc-account-row { grid-template-columns: minmax(0, 1fr) auto; align-items: center; padding: 16px; gap: 14px; }
  .gpc-row-number { grid-column: 1; grid-row: 1; }
  .gpc-account-row > label { grid-column: 1 / -1; }
  .gpc-account-row .gpc-remove { grid-column: 2; grid-row: 1; justify-self: end; }
  .gpc-form-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); padding: 16px; }
  .gpc-shell input:not([type='checkbox']), .gpc-shell select { font-size: 16px; }
  .gpc-switch-grid { padding-inline: 16px; }
  .gpc-result-row { grid-template-columns: minmax(0, 1fr) auto; gap: 6px 16px; padding: 16px; }
  .gpc-result-points { grid-column: 1 / -1; }
}
@container (max-width: 380px) {
  .gpc-page-head { flex-wrap: wrap; gap: 10px; }
  .gpc-form-grid { grid-template-columns: minmax(0, 1fr); }
  .gpc-actions { flex-direction: column-reverse; align-items: stretch; }
}
@media (forced-colors: active) {
  .gpc-shell input[type='checkbox'] { appearance: auto; -webkit-appearance: auto; }
  .gpc-shell input[type='checkbox']::before { display: none; }
}
</style>
