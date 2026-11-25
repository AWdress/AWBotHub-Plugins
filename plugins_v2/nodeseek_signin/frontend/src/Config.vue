<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

const props = defineProps({pluginId: String, host: {type: Object, required: true}})
const CronInput = computed(() => props.host.ui.CronInput)
const defaults = {
  enabled: false,
  notify: true,
  auto_save_cookie: true,
  cookies: '',
  accounts: [],
  browser_login: 'Cookie 失效时自动使用 CloakBrowser 完成验证并重新登录，无需第三方验证码服务。',
  random_reward: true,
  cron: '0 8 * * *',
  timeout: 30,
  captcha_timeout: 90,
  last_result: '尚未运行',
  history: '暂无记录',
}
const form = reactive({...defaults})
const visiblePasswords = reactive({})
const cookiesVisible = ref(false)
const loading = ref(true)
const saving = ref(false)
const running = ref(false)
const loadError = ref('')
const resultText = ref('')
const savedSnapshot = ref('')
let statusTimer

function toast(type, text) { props.host.toast?.[type]?.(text) }
function snapshot() { return JSON.stringify(form) }
function normalizeAccounts(value) {
  if (Array.isArray(value)) {
    return value.map((item) => ({
      user: String(item?.user || item?.username || ''),
      password: String(item?.password || ''),
    }))
  }
  if (typeof value !== 'string' || !value.trim() || value === '********') return []
  return value.split(/(?:\r?\n|\s+&\s+)/).map((line) => {
    const separator = ['----', '，', ',', '：', ':', '|', '\t'].find((item) => line.includes(item))
    if (!separator) return null
    const at = line.indexOf(separator)
    const user = line.slice(0, at).trim()
    const password = line.slice(at + separator.length).trim()
    return user && password ? {user, password} : null
  }).filter(Boolean)
}
function addAccount() { form.accounts.push({user: '', password: ''}) }
function removeAccount(index) {
  form.accounts.splice(index, 1)
  delete visiblePasswords[index]
}
function validate() {
  const incomplete = form.accounts.findIndex((item) => !item.user.trim() || !item.password)
  if (incomplete >= 0) {
    toast('error', '账号 ' + (incomplete + 1) + ' 的用户名或密码未填写完整')
    return false
  }
  return true
}
async function refreshStatus() {
  try {
    const status = await props.host.callApi('/status')
    running.value = Boolean(status?.running)
    if (status?.last_result) {
      const item = status.last_result
      form.last_result = (item['时间'] || '') + ' · 成功 ' + (item['成功'] || 0) + '/' + (item['总数'] || 0)
    }
    if (Array.isArray(status?.history) && status.history.length) {
      form.history = status.history.map((item) =>
        (item['时间'] || '') + ' · 成功 ' + (item['成功'] || 0) + '/' + (item['总数'] || 0)
      ).join('\n')
    }
  } catch {}
}
async function load() {
  loading.value = true
  try {
    const saved = await props.host.getConfig()
    Object.assign(form, defaults, saved || {})
    if (saved?.cookies === '********') form.cookies = String(await props.host.revealSecret('cookies') || '')
    if (saved?.accounts === '********') {
      form.accounts = normalizeAccounts(await props.host.revealSecret('accounts'))
    } else {
      form.accounts = normalizeAccounts(saved?.accounts)
    }
    savedSnapshot.value = snapshot()
  } catch (error) {
    loadError.value = '读取配置失败：' + (error.message || error)
  } finally {
    loading.value = false
  }
  await refreshStatus()
  statusTimer = setInterval(refreshStatus, 3000)
}
async function save() {
  if (loadError.value) return toast('error', '配置尚未成功读取，请刷新后重试')
  if (!validate()) return
  saving.value = true
  try {
    await props.host.saveConfig(JSON.parse(JSON.stringify(form)))
    savedSnapshot.value = snapshot()
    toast('success', '配置已保存并应用')
  } catch (error) {
    toast('error', '保存失败：' + (error.message || error))
  } finally {
    saving.value = false
  }
}
async function runNow() {
  if (running.value || saving.value || !validate()) return
  if (snapshot() !== savedSnapshot.value) {
    resultText.value = '配置有未保存的修改，请先保存，待插件重载后再立即签到。'
    return toast('error', resultText.value)
  }
  running.value = true
  resultText.value = ''
  try {
    const result = await props.host.callApi('/run', {method: 'POST', body: {}})
    resultText.value = result?.message || '签到任务已开始'
    toast(result?.ok === false ? 'error' : 'success', resultText.value)
  } catch (error) {
    resultText.value = '启动签到失败：' + (error.message || error)
    toast('error', resultText.value)
  } finally {
    await refreshStatus()
  }
}

onMounted(load)
onBeforeUnmount(() => clearInterval(statusTimer))
</script>

<template>
  <IosSettings>
  <main class="nsk-shell">
    <header class="nsk-page-head">
      <div>
        <h2>NodeSeek 签到</h2>
        <p>Cookie 可直接签到；失效时使用对应账号密码通过 CloakBrowser 自动登录。</p>
      </div>
      <span class="nsk-state" :class="{busy: running}">{{ running ? '签到中' : '就绪' }}</span>
    </header>

    <p v-if="loadError" class="nsk-alert" role="alert">{{ loadError }}</p>

    <section aria-labelledby="account-title">
      <div class="nsk-section-head">
        <div>
          <h3 id="account-title">账号与 Cookie</h3>
          <p>账号逐个添加；多个 Cookie 仍用“ &amp; ”分隔，并与账号顺序对应。</p>
        </div>
        <button class="nsk-secondary" type="button" :disabled="loading" @click="addAccount">添加账号</button>
      </div>
      <label class="nsk-field nsk-wide">
        <span>NodeSeek Cookie（可选）</span>
        <div class="nsk-secret">
          <input v-model="form.cookies" :type="cookiesVisible ? 'text' : 'password'" autocomplete="off" placeholder="多个 Cookie 使用 & 分隔">
          <button type="button" :disabled="!form.cookies" :aria-label="cookiesVisible ? '隐藏 Cookie' : '显示 Cookie'" @click="cookiesVisible = !cookiesVisible">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>
        <small>留空也可以，插件会使用下方账密登录并获取 Cookie。</small>
      </label>
      <div v-if="loading" class="nsk-empty">正在安全读取账号配置…</div>
      <div v-else-if="!form.accounts.length" class="nsk-empty">尚未添加登录账号。已有有效 Cookie 时可以不添加。</div>
      <div v-else class="nsk-account-list">
        <article v-for="(account, index) in form.accounts" :key="index" class="nsk-account-row">
          <div class="nsk-row-number">{{ index + 1 }}</div>
          <label class="nsk-field"><span>用户名或邮箱</span><input v-model.trim="account.user" type="text" autocomplete="username"></label>
          <label class="nsk-field">
            <span>密码</span>
            <div class="nsk-secret">
              <input v-model="account.password" :type="visiblePasswords[index] ? 'text' : 'password'" autocomplete="current-password">
              <button type="button" :disabled="!account.password" :aria-label="visiblePasswords[index] ? '隐藏密码' : '显示密码'" @click="visiblePasswords[index] = !visiblePasswords[index]">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>
              </button>
            </div>
          </label>
          <button class="nsk-remove" type="button" @click="removeAccount(index)">删除</button>
        </article>
      </div>
    </section>

    <section aria-labelledby="switch-title">
      <h3 id="switch-title">功能开关</h3>
      <div class="nsk-switch-grid">
        <label><span>启用自动签到</span><input v-model="form.enabled" type="checkbox" role="switch"></label>
        <label><span>发送签到通知</span><input v-model="form.notify" type="checkbox" role="switch"></label>
        <label><span>自动回写新 Cookie</span><input v-model="form.auto_save_cookie" type="checkbox" role="switch"></label>
        <label><span>随机鸡腿奖励</span><input v-model="form.random_reward" type="checkbox" role="switch"></label>
      </div>
    </section>

    <section aria-labelledby="schedule-title">
      <h3 id="schedule-title">签到设置</h3>
      <div class="nsk-form-grid">
        <label class="nsk-field nsk-wide"><span>签到 Cron</span><component :is="CronInput" v-model="form.cron" /><small>标准五段 Cron，默认每天 08:00。</small></label>
        <label class="nsk-field"><span>请求超时（秒）</span><input v-model.number="form.timeout" type="number" min="5" max="120"></label>
        <label class="nsk-field"><span>浏览器验证超时（秒）</span><input v-model.number="form.captcha_timeout" type="number" min="30" max="300"></label>
      </div>
    </section>

    <section aria-labelledby="status-title">
      <h3 id="status-title">运行状态</h3>
      <div class="nsk-status-grid">
        <div><span>最近结果</span><p>{{ form.last_result || '尚未运行' }}</p></div>
        <div><span>最近记录</span><pre>{{ form.history || '暂无记录' }}</pre></div>
      </div>
    </section>

    <p v-if="resultText" class="nsk-result" aria-live="polite">{{ resultText }}</p>
    <footer class="nsk-actions">
      <button class="nsk-secondary" type="button" :disabled="running || saving || loading" @click="runNow">{{ running ? '签到中…' : '立即签到' }}</button>
      <button class="nsk-primary" type="button" :disabled="saving || running || loading || !!loadError" @click="save">{{ saving ? '正在保存…' : '保存配置' }}</button>
    </footer>
  </main>
  </IosSettings>
</template>

<style scoped>
/* iOS account and Cookie groups. Login, scheduling and status polling remain unchanged. */
.nsk-shell { display: grid; gap: 28px; min-width: 0; color: var(--ios-text); }
.nsk-shell h2, .nsk-shell h3, .nsk-shell p { margin: 0; }
.nsk-page-head, .nsk-section-head, .nsk-actions { display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.nsk-page-head { padding: 4px 0 0; align-items: flex-start; }
.nsk-page-head h2 { font-size: 22px; font-weight: 650; line-height: 1.4; letter-spacing: -.025em; }
.nsk-page-head p, .nsk-section-head p { max-width: 70ch; margin-top: 5px; color: var(--ios-secondary); font-size: 13px; line-height: 1.65; }
.nsk-shell h3 { font-size: 15px; font-weight: 650; line-height: 1.5; }
.nsk-shell section > h3 { margin: 0 4px 12px; }
.nsk-section-head { align-items: flex-start; margin: 0 4px 14px; }
.nsk-state { flex: 0 0 auto; padding: 5px 9px; border-radius: 8px; color: var(--ios-secondary); background: var(--ios-inset); font-size: 12px; }
.nsk-state.busy { color: var(--accent, #0063dc); background: var(--accent-dim, #e8f1ff); }
.nsk-alert, .nsk-result { padding: 14px 18px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); color: var(--danger, #bd2733); font-size: 13px; overflow-wrap: anywhere; }
.nsk-result { color: var(--ios-text); }
.nsk-field { display: block; min-width: 0; }
.nsk-field > span { display: block; margin-bottom: 7px; color: var(--ios-secondary); font-size: 12px; line-height: 1.6; }
.nsk-field small { display: block; margin-top: 7px; max-width: 72ch; color: var(--ios-secondary); font-size: 12px; line-height: 1.65; }
.nsk-shell section > .nsk-field.nsk-wide { padding: 18px 20px; margin-bottom: 16px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.nsk-shell input:not([type='checkbox']) { display: block; min-width: 0; width: 100%; min-height: 44px; padding: 10px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-text); transition: border-color var(--ios-fast) ease; }
.nsk-shell input:not([type='checkbox']):focus { border-color: var(--accent, #0063dc); }
.nsk-secret { position: relative; }
.nsk-shell .nsk-secret input { padding-right: 50px; }
.nsk-secret button { position: absolute; inset-inline-end: 0; top: 0; display: grid; place-items: center; width: 44px; height: 44px; border: 0; border-radius: 12px; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.nsk-secret button:hover:not(:disabled) { color: var(--ios-text); }
.nsk-secret svg { width: 19px; height: 19px; fill: none; stroke: currentColor; stroke-width: 1.8; }
.nsk-secondary, .nsk-primary, .nsk-remove { display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 9px 16px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font-weight: 500; cursor: pointer; }
.nsk-secondary:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.nsk-primary { min-width: 132px; border-color: transparent; background: var(--ios-accent); color: #fff; font-weight: 600; }
.nsk-primary:hover:not(:disabled) { filter: brightness(1.08); }
.nsk-remove { padding-inline: 12px; border-color: transparent; background: transparent; color: var(--danger, #bd2733); }
.nsk-remove:hover { background: color-mix(in srgb, var(--danger, #bd2733) 8%, transparent); }
.nsk-shell button:disabled { opacity: .5; cursor: not-allowed; }
.nsk-empty { padding: 36px 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); color: var(--ios-secondary); font-size: 13px; text-align: center; }
.nsk-account-list { overflow: hidden; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.nsk-account-row { display: grid; grid-template-columns: 28px minmax(0, 1fr) minmax(0, 1fr) auto; align-items: end; gap: 16px; padding: 20px; }
.nsk-account-row + .nsk-account-row { border-top: 1px solid var(--ios-line); }
.nsk-row-number { display: grid; place-items: center; align-self: center; width: 28px; height: 28px; border-radius: 8px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 12px; font-variant-numeric: tabular-nums; }
.nsk-switch-grid { padding: 0 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.nsk-switch-grid label { display: flex; align-items: center; justify-content: space-between; gap: 20px; min-height: 66px; padding: 13px 0; cursor: pointer; }
.nsk-switch-grid label + label { border-top: 1px solid var(--ios-line); }
.nsk-switch-grid label > span { flex: 1; margin: 0; color: var(--ios-text); font-size: 14px; }
.nsk-shell input[type='checkbox'] { appearance: none; -webkit-appearance: none; position: relative; display: block; flex: 0 0 50px; width: 50px; height: 30px; margin: 0; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); cursor: pointer; transition: background-color var(--ios-fast) ease, border-color var(--ios-fast) ease; }
.nsk-shell input[type='checkbox']::before { content: ''; position: absolute; top: 2px; left: 2px; width: 24px; height: 24px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .18); transition: transform var(--ios-duration) var(--ios-ease); }
.nsk-shell input[type='checkbox']:checked { border-color: transparent; background: var(--ios-accent); }
.nsk-shell input[type='checkbox']:checked::before { transform: translateX(20px); }
.nsk-shell input[type='checkbox']:active::before { transform: scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.nsk-shell input[type='checkbox']:checked:active::before { transform: translateX(20px) scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.nsk-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px 20px; min-width: 0; padding: 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.nsk-form-grid .nsk-wide { grid-column: 1 / -1; }
.nsk-status-grid { overflow: hidden; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.nsk-status-grid > div { display: grid; grid-template-columns: 110px minmax(0, 1fr); align-items: baseline; gap: 16px; padding: 16px 20px; min-width: 0; }
.nsk-status-grid > div + div { border-top: 1px solid var(--ios-line); }
.nsk-status-grid > div > span { color: var(--ios-secondary); font-size: 12px; }
.nsk-status-grid p, .nsk-status-grid pre { min-width: 0; margin: 0; max-height: 260px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; color: var(--ios-text); font: inherit; font-size: 13px; line-height: 1.7; }
.nsk-actions { justify-content: flex-end; gap: 12px; }
:global(html[data-theme='transparent'] .nsk-switch-grid),
:global(html[data-theme='transparent'] .nsk-account-list),
:global(html[data-theme='transparent'] .nsk-shell section > .nsk-field.nsk-wide),
:global(html[data-theme='transparent'] .nsk-form-grid),
:global(html[data-theme='transparent'] .nsk-status-grid),
:global(html[data-theme='transparent'] .nsk-empty),
:global(html[data-theme='transparent'] .nsk-alert),
:global(html[data-theme='transparent'] .nsk-result) { backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); -webkit-backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); }
@container (max-width: 620px) {
  .nsk-page-head h2 { font-size: 20px; }
  .nsk-section-head { flex-wrap: wrap; gap: 12px; }
  .nsk-account-row { grid-template-columns: minmax(0, 1fr) auto; align-items: center; padding: 16px; gap: 14px; }
  .nsk-row-number { grid-column: 1; grid-row: 1; }
  .nsk-account-row .nsk-field { grid-column: 1 / -1; }
  .nsk-account-row .nsk-remove { grid-column: 2; grid-row: 1; justify-self: end; }
  .nsk-shell section > .nsk-field.nsk-wide { padding: 16px; }
  .nsk-form-grid { padding: 16px; }
  .nsk-switch-grid { padding-inline: 16px; }
  .nsk-shell input:not([type='checkbox']) { font-size: 16px; }
  .nsk-status-grid > div { grid-template-columns: minmax(0, 1fr); gap: 7px; padding: 16px; }
}
@container (max-width: 380px) {
  .nsk-page-head { flex-wrap: wrap; gap: 10px; }
  .nsk-form-grid { grid-template-columns: minmax(0, 1fr); }
  .nsk-actions { flex-direction: column-reverse; align-items: stretch; }
}
@media (forced-colors: active) {
  .nsk-shell input[type='checkbox'] { appearance: auto; -webkit-appearance: auto; }
  .nsk-shell input[type='checkbox']::before { display: none; }
}
</style>
