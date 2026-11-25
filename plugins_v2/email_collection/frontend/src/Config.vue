<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

const props = defineProps({pluginId: String, host: {type: Object, required: true}})
const providers = [
  {value: 'qq', label: 'QQ 邮箱', hint: '使用 IMAP 授权码'},
  {value: '163', label: '163 邮箱', hint: '使用客户端授权密码'},
  {value: '126', label: '126 邮箱', hint: '使用客户端授权密码'},
  {value: 'gmail', label: 'Gmail', hint: '使用 Google 应用专用密码'},
  {value: 'outlook', label: 'Outlook', hint: '使用应用密码或可用的 IMAP 密码'},
  {value: 'sina', label: '新浪邮箱', hint: '使用客户端授权码'},
]
const defaults = {
  enabled: false,
  push_all: false,
  mailboxes: [],
  keywords: '验证码|重要通知|账单|订单',
  poll_seconds: 30,
  manual_check_limit: 10,
  imap_proxy_url: '',
  ai_verification: false,
  ai_summary_enabled: false,
  verification_prompt: '',
  summary_prompt: '',
  ai_timeout: 60,
}
const form = reactive({...defaults})
const visible = reactive({})
const proxyVisible = ref(false)
const loading = ref(true)
const saving = ref(false)
const checking = ref(false)
const running = ref(false)
const loadError = ref('')
const lastResult = ref('')
const savedSnapshot = ref('')
let timer

function toast(type, message) { props.host.toast?.[type]?.(message) }
function normalizeMailboxes(value) {
  if (Array.isArray(value)) {
    return value.map((item) => ({
      provider: String(item?.provider || 'qq'),
      email: String(item?.email || ''),
      password: String(item?.password || ''),
    }))
  }
  if (typeof value !== 'string' || !value.trim() || value === '********') return []
  const domainProvider = {'qq.com': 'qq', '163.com': '163', '126.com': '126', 'gmail.com': 'gmail', 'outlook.com': 'outlook', 'hotmail.com': 'outlook', 'live.com': 'outlook', 'sina.com': 'sina', 'sina.cn': 'sina'}
  return value.split(/(?:\r?\n|\s+&\s+)/).map((line) => {
    const at = line.indexOf('|')
    if (at < 0) return null
    const email = line.slice(0, at).trim()
    const password = line.slice(at + 1).trim()
    const provider = domainProvider[email.split('@').pop()?.toLowerCase()] || 'qq'
    return email && password ? {provider, email, password} : null
  }).filter(Boolean)
}
function addMailbox() { form.mailboxes.push({provider: 'qq', email: '', password: ''}) }
function removeMailbox(index) { form.mailboxes.splice(index, 1); delete visible[index] }
function providerHint(value) { return providers.find((item) => item.value === value)?.hint || '' }
function snapshot() { return JSON.stringify(form) }
function validate() {
  const incomplete = form.mailboxes.findIndex((item) => !item.provider || !item.email.trim() || !item.password)
  if (incomplete >= 0) {
    toast('error', `邮箱 ${incomplete + 1} 的类型、地址或授权码未填写完整`)
    return false
  }
  if (form.imap_proxy_url && !/^(?:http:\/\/|socks4a?:\/\/|socks5h?:\/\/)/i.test(form.imap_proxy_url)) {
    toast('error', 'IMAP 代理地址必须以 http://、socks4://、socks5:// 或 socks5h:// 开头')
    return false
  }
  return true
}
async function refreshStatus() {
  try { running.value = Boolean((await props.host.callApi('/status'))?.running) } catch {}
}
async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const saved = await props.host.getConfig()
    Object.assign(form, defaults, saved || {})
    if (saved?.imap_proxy_url === '********') {
      form.imap_proxy_url = await props.host.revealSecret('imap_proxy_url')
    }
    if (saved?.mailboxes === '********') {
      form.mailboxes = normalizeMailboxes(await props.host.revealSecret('mailboxes'))
    } else {
      form.mailboxes = normalizeMailboxes(saved?.mailboxes)
    }
    savedSnapshot.value = snapshot()
  } catch (error) {
    loadError.value = `读取邮箱配置失败：${error.message || error}`
  } finally {
    loading.value = false
  }
  await refreshStatus()
  timer = setInterval(refreshStatus, 3000)
}
async function save(showToast = true) {
  if (loadError.value) {
    toast('error', '邮箱配置尚未成功读取，请刷新后重试')
    return false
  }
  if (!validate()) return false
  saving.value = true
  try {
    await props.host.saveConfig(JSON.parse(JSON.stringify(form)))
    savedSnapshot.value = snapshot()
    if (showToast) toast('success', '配置已保存并应用')
    return true
  } catch (error) {
    toast('error', `保存失败：${error.message || error}`)
    return false
  } finally {
    saving.value = false
  }
}
async function checkNow() {
  if (checking.value || running.value) return
  if (!validate()) return
  if (snapshot() !== savedSnapshot.value) {
    lastResult.value = '配置有未保存的修改，请先保存配置，待插件重载后再点击立即检查。'
    toast('error', lastResult.value)
    return
  }
  checking.value = true
  lastResult.value = ''
  try {
    const result = await props.host.callApi('/check', {method: 'POST', body: {}})
    lastResult.value = result.message || '检查完成'
    toast(result.ok === false ? 'error' : 'success', lastResult.value)
  } catch (error) {
    lastResult.value = `检查失败：${error.message || error}`
    toast('error', lastResult.value)
  } finally {
    checking.value = false
    await refreshStatus()
  }
}

onMounted(load)
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <IosSettings>
  <main class="ecl-shell">
    <header class="ecl-page-head">
      <div>
        <h2>邮件集</h2>
        <p>后台按间隔检查未读邮件；立即检查会回查近期已读和未读邮件。</p>
      </div>
      <span class="ecl-state" :class="{busy: running || checking}">{{ running || checking ? '检查中' : '就绪' }}</span>
    </header>

    <p v-if="loadError" class="ecl-alert" role="alert">{{ loadError }}</p>

    <section aria-labelledby="mailboxes-title">
      <div class="ecl-section-head">
        <div><h3 id="mailboxes-title">邮箱账号</h3><p>每个邮箱单独选择服务商，授权码默认隐藏。</p></div>
        <button class="ecl-secondary" type="button" :disabled="loading" @click="addMailbox">添加邮箱</button>
      </div>
      <div v-if="loading" class="ecl-empty">正在安全读取邮箱配置…</div>
      <div v-else-if="!form.mailboxes.length" class="ecl-empty">尚未添加邮箱，点击“添加邮箱”开始配置。</div>
      <div v-else class="ecl-mailbox-list">
        <article v-for="(mailbox, index) in form.mailboxes" :key="index" class="ecl-mailbox-row">
          <div class="ecl-row-number">{{ index + 1 }}</div>
          <label><span>邮箱类型</span><select v-model="mailbox.provider"><option v-for="provider in providers" :key="provider.value" :value="provider.value">{{ provider.label }}</option></select><small>{{ providerHint(mailbox.provider) }}</small></label>
          <label><span>邮箱地址</span><input v-model.trim="mailbox.email" type="email" autocomplete="username" placeholder="name@example.com"></label>
          <label><span>授权码或应用密码</span><div class="ecl-secret"><input v-model="mailbox.password" :type="visible[index] ? 'text' : 'password'" autocomplete="current-password" placeholder="不是网页登录密码"><button type="button" :aria-label="visible[index] ? '隐藏授权码' : '显示授权码'" @click="visible[index] = !visible[index]"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div></label>
          <button class="ecl-remove" type="button" @click="removeMailbox(index)">删除</button>
        </article>
      </div>
    </section>

    <section aria-labelledby="monitor-title">
      <h3 id="monitor-title">监控与过滤</h3>
      <div class="ecl-switch-grid">
        <label><span>启用后台监控</span><input v-model="form.enabled" type="checkbox" role="switch"></label>
        <label>
          <span class="ecl-switch-copy">
            <strong>推送所有新邮件</strong>
            <small>开启后忽略关键词和验证码筛选，普通邮件也会推送；通常保持关闭。</small>
          </span>
          <input v-model="form.push_all" type="checkbox" role="switch">
        </label>
      </div>
      <div class="ecl-form-grid ecl-monitor-grid">
        <label class="ecl-wide"><span>关键词（用 | 分隔）</span><input v-model.trim="form.keywords" type="text" placeholder="验证码|重要通知|账单|订单"></label>
        <label><span>轮询间隔（秒）</span><input v-model.number="form.poll_seconds" type="number" min="10" max="300"></label>
        <label><span>立即检查回查数量</span><input v-model.number="form.manual_check_limit" type="number" min="1" max="500"></label>
        <label class="ecl-wide"><span>IMAP 代理地址（可选）</span><div class="ecl-secret"><input v-model.trim="form.imap_proxy_url" :type="proxyVisible ? 'text' : 'password'" autocomplete="off" placeholder="容器无法直连 993 时填写，如 socks5://host:port"><button type="button" :aria-label="proxyVisible ? '隐藏代理地址' : '显示代理地址'" @click="proxyVisible = !proxyVisible"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div><small>留空时固定使用 IPv4 直连并自动重试；支持 HTTP、SOCKS4 和 SOCKS5 代理。</small></label>
      </div>
    </section>

    <section aria-labelledby="ai-title">
      <h3 id="ai-title">AI 处理</h3>
      <div class="ecl-switch-grid">
        <label><span>AI 验证码识别</span><input v-model="form.ai_verification" type="checkbox" role="switch"></label>
        <label><span>AI 邮件概要</span><input v-model="form.ai_summary_enabled" type="checkbox" role="switch"></label>
      </div>
      <div class="ecl-form-grid">
        <label class="ecl-wide"><span>验证码提示词</span><textarea v-model="form.verification_prompt" rows="3" placeholder="留空使用内置提示词"></textarea></label>
        <label class="ecl-wide"><span>概要提示词</span><textarea v-model="form.summary_prompt" rows="3" placeholder="留空使用内置提示词"></textarea></label>
        <label><span>AI 超时（秒）</span><input v-model.number="form.ai_timeout" type="number" min="10" max="180"></label>
      </div>
    </section>

    <p v-if="lastResult" class="ecl-result" aria-live="polite">{{ lastResult }}</p>
    <footer class="ecl-actions">
      <button class="ecl-secondary" type="button" :disabled="checking || running || saving || loading || !form.mailboxes.length" @click="checkNow">{{ checking || running ? '正在检查…' : '立即检查' }}</button>
      <button class="ecl-primary" type="button" :disabled="saving || checking || loading || !!loadError" @click="save()">{{ saving ? '正在保存…' : '保存配置' }}</button>
    </footer>
  </main>
  </IosSettings>
</template>

<style scoped>
/* iOS grouped mailbox settings. Credentials, polling, filters and AI bindings remain untouched. */
.ecl-shell { display: grid; gap: 28px; min-width: 0; color: var(--ios-text); }
.ecl-shell h2, .ecl-shell h3, .ecl-shell p { margin: 0; }
.ecl-page-head, .ecl-section-head, .ecl-actions { display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.ecl-page-head { padding: 4px 0 0; align-items: flex-start; }
.ecl-page-head h2 { font-size: 22px; font-weight: 650; line-height: 1.4; letter-spacing: -.025em; }
.ecl-page-head p, .ecl-section-head p { max-width: 70ch; margin-top: 5px; color: var(--ios-secondary); font-size: 13px; line-height: 1.65; }
.ecl-shell h3 { font-size: 15px; font-weight: 650; line-height: 1.5; }
.ecl-shell section > h3 { margin: 0 4px 12px; }
.ecl-section-head { align-items: flex-start; margin: 0 4px 14px; }
.ecl-section-head .ecl-secondary { flex: 0 0 auto; }
.ecl-state { flex: 0 0 auto; padding: 5px 9px; border-radius: 8px; color: var(--ios-secondary); background: var(--ios-inset); font-size: 12px; }
.ecl-state.busy { color: var(--accent, #0063dc); background: var(--accent-dim, #e8f1ff); }
.ecl-alert, .ecl-result { padding: 14px 18px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); color: var(--danger, #bd2733); font-size: 13px; line-height: 1.7; overflow-wrap: anywhere; }
.ecl-result { color: var(--ios-text); }
.ecl-secondary, .ecl-primary, .ecl-remove { display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 9px 16px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font-weight: 500; cursor: pointer; }
.ecl-secondary:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.ecl-primary { min-width: 132px; border-color: transparent; background: var(--ios-accent); color: #fff; font-weight: 600; }
.ecl-primary:hover:not(:disabled) { filter: brightness(1.08); }
.ecl-remove { padding-inline: 12px; border-color: transparent; background: transparent; color: var(--danger, #bd2733); }
.ecl-remove:hover { background: color-mix(in srgb, var(--danger, #bd2733) 8%, transparent); }
.ecl-shell button:disabled { opacity: .5; cursor: not-allowed; }
.ecl-mailbox-list { overflow: hidden; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.ecl-mailbox-row { display: grid; grid-template-columns: 28px minmax(0, .75fr) minmax(0, 1fr) minmax(0, 1fr) auto; align-items: start; gap: 16px; padding: 20px; }
.ecl-mailbox-row + .ecl-mailbox-row { border-top: 1px solid var(--ios-line); }
.ecl-mailbox-row .ecl-remove { align-self: start; margin-top: 26px; }
.ecl-row-number { display: grid; place-items: center; width: 28px; height: 28px; margin-top: 34px; border-radius: 8px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 12px; font-variant-numeric: tabular-nums; }
.ecl-shell label { min-width: 0; }
.ecl-shell label > span { display: block; margin-bottom: 7px; color: var(--ios-secondary); font-size: 12px; line-height: 1.6; }
.ecl-shell label small { display: block; margin-top: 7px; max-width: 72ch; color: var(--ios-secondary); font-size: 12px; line-height: 1.65; }
.ecl-shell input:not([type='checkbox']), .ecl-shell select, .ecl-shell textarea { display: block; min-width: 0; width: 100%; min-height: 44px; padding: 10px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-text); transition: border-color var(--ios-fast) ease; }
.ecl-shell input:not([type='checkbox']):focus, .ecl-shell select:focus, .ecl-shell textarea:focus { border-color: var(--accent, #0063dc); }
.ecl-shell textarea { min-height: 100px; line-height: 1.7; resize: vertical; }
.ecl-secret { position: relative; }
.ecl-shell .ecl-secret input { padding-right: 50px; }
.ecl-secret button { position: absolute; inset-inline-end: 0; top: 0; display: grid; place-items: center; width: 44px; height: 44px; border: 0; border-radius: 12px; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.ecl-secret button:hover { color: var(--ios-text); }
.ecl-secret svg { width: 19px; height: 19px; fill: none; stroke: currentColor; stroke-width: 1.8; }
.ecl-empty { padding: 36px 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); color: var(--ios-secondary); font-size: 13px; text-align: center; }
.ecl-switch-grid { padding: 0 20px; border: 1px solid var(--ios-line); border-bottom: 0; border-radius: 20px 20px 0 0; background: var(--ios-surface); }
.ecl-switch-grid label { display: flex; align-items: center; justify-content: space-between; gap: 20px; min-height: 66px; padding: 13px 0; cursor: pointer; }
.ecl-switch-grid label + label { border-top: 1px solid var(--ios-line); }
.ecl-shell .ecl-switch-grid label > span { flex: 1; min-width: 0; margin: 0; color: var(--ios-text); font-size: 14px; }
.ecl-switch-copy strong { display: block; color: var(--ios-text); font-size: 14px; font-weight: 600; }
.ecl-switch-copy small { margin-top: 4px; }
.ecl-shell input[type='checkbox'] { appearance: none; -webkit-appearance: none; position: relative; display: block; flex: 0 0 50px; width: 50px; height: 30px; margin: 0; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); cursor: pointer; transition: background-color var(--ios-fast) ease, border-color var(--ios-fast) ease; }
.ecl-shell input[type='checkbox']::before { content: ''; position: absolute; top: 2px; left: 2px; width: 24px; height: 24px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .18); transition: transform var(--ios-duration) var(--ios-ease); }
.ecl-shell input[type='checkbox']:checked { border-color: transparent; background: var(--ios-accent); }
.ecl-shell input[type='checkbox']:checked::before { transform: translateX(20px); }
.ecl-shell input[type='checkbox']:active::before { transform: scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.ecl-shell input[type='checkbox']:checked:active::before { transform: translateX(20px) scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.ecl-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px 20px; min-width: 0; padding: 20px; border: 1px solid var(--ios-line); border-radius: 0 0 20px 20px; background: var(--ios-surface); }
.ecl-form-grid .ecl-wide { grid-column: 1 / -1; }
.ecl-actions { justify-content: flex-end; gap: 12px; }
:global(html[data-theme='transparent'] .ecl-switch-grid),
:global(html[data-theme='transparent'] .ecl-mailbox-list),
:global(html[data-theme='transparent'] .ecl-form-grid),
:global(html[data-theme='transparent'] .ecl-empty),
:global(html[data-theme='transparent'] .ecl-alert),
:global(html[data-theme='transparent'] .ecl-result) { backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); -webkit-backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); }
@container (max-width: 800px) {
  .ecl-mailbox-row { grid-template-columns: minmax(0, 1fr) auto; align-items: center; padding: 16px; gap: 14px; }
  .ecl-row-number { grid-column: 1; grid-row: 1; margin: 0; }
  .ecl-mailbox-row > label { grid-column: 1 / -1; }
  .ecl-mailbox-row .ecl-remove { grid-column: 2; grid-row: 1; justify-self: end; margin: 0; }
}
@container (max-width: 520px) {
  .ecl-page-head h2 { font-size: 20px; }
  .ecl-section-head { flex-wrap: wrap; gap: 12px; }
  .ecl-form-grid { grid-template-columns: minmax(0, 1fr); padding: 16px; }
  .ecl-switch-grid { padding-inline: 16px; }
  .ecl-shell input:not([type='checkbox']), .ecl-shell select, .ecl-shell textarea { font-size: 16px; }
}
@container (max-width: 380px) {
  .ecl-page-head { flex-wrap: wrap; gap: 10px; }
  .ecl-actions { flex-direction: column-reverse; align-items: stretch; }
}
@media (forced-colors: active) {
  .ecl-shell input[type='checkbox'] { appearance: auto; -webkit-appearance: auto; }
  .ecl-shell input[type='checkbox']::before { display: none; }
}
</style>
