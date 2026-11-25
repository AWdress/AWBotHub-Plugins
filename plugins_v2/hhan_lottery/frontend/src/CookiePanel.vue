<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

const props = defineProps({ pluginId: String, host: { type: Object, required: true } })
const cfg = reactive({ cookie_source: 'platform', manual_cookie: '' })
const loading = ref(true)
const saving = ref(false)
const checking = ref(false)
const cookieVisible = ref(false)
const checked = ref(null)
const hasManual = computed(() => Boolean(String(cfg.manual_cookie || '').trim()))

async function save(showToast = true) {
  saving.value = true
  try {
    cfg.cookie_source = cfg.cookie_source === 'manual' ? 'manual' : 'platform'
    cfg.manual_cookie = String(cfg.manual_cookie || '').trim().replace(/^cookie:\s*/i, '')
    if (cfg.cookie_source === 'manual' && !cfg.manual_cookie) throw new Error('请先填写手动 Cookie')
    await props.host.saveConfig({ ...cfg })
    checked.value = null
    if (showToast) props.host.toast.success('登录设置已保存')
    return true
  } catch (error) { props.host.toast.error('保存失败：' + (error.message || error)); return false }
  finally { saving.value = false }
}

async function check() {
  checking.value = true
  try {
    if (!await save(false)) return
    const result = await props.host.callApi('/auth/check')
    checked.value = result
    ;(result.ok ? props.host.toast.success : props.host.toast.error)(result.message)
  } catch (_) { checked.value = { ok: false, message: '登录设置未通过检查' } }
  finally { checking.value = false }
}

async function clearManual() {
  if (!confirm('清空已保存的手动 Cookie？')) return
  cfg.manual_cookie = ''
  if (cfg.cookie_source === 'manual') cfg.cookie_source = 'platform'
  try { await props.host.saveConfig({ ...cfg }); checked.value = null; props.host.toast.success('手动 Cookie 已清空，已切换到平台读取') }
  catch (error) { props.host.toast.error('清空失败：' + (error.message || error)) }
}

onMounted(async () => {
  try { const saved = await props.host.getConfig() || {}; if (saved.manual_cookie === '********') saved.manual_cookie = await props.host.revealSecret('manual_cookie'); Object.assign(cfg, saved) }
  catch (error) { props.host.toast.error('读取登录设置失败：' + (error.message || error)) }
  finally { loading.value = false }
})
</script>

<template>
  <section class="hh-cookie">
    <div v-if="loading" class="hh-cookie-loading">正在读取登录设置…</div>
    <template v-else>
      <header><div><p class="hh-cookie-eyebrow">ACCOUNT ACCESS</p><h2>登录设置</h2><p>选择憨憨小助手访问 HHanClub 时使用的 Cookie 来源。</p></div><span class="hh-cookie-source-badge">{{ cfg.cookie_source === 'manual' ? '手动 Cookie' : '平台同步' }}</span></header>

      <div class="hh-cookie-source-grid" role="radiogroup" aria-label="Cookie 来源">
        <label :class="{ selected: cfg.cookie_source === 'platform' }"><input v-model="cfg.cookie_source" type="radio" value="platform"><span class="hh-cookie-radio-dot" /><span><b>从平台读取</b><small>使用 AWBotHub 已同步的 hhanclub.net Cookie</small></span></label>
        <label :class="{ selected: cfg.cookie_source === 'manual' }"><input v-model="cfg.cookie_source" type="radio" value="manual"><span class="hh-cookie-radio-dot" /><span><b>手动填写</b><small>使用下方保存的 Cookie，适合平台同步不可用时</small></span></label>
      </div>

      <section class="hh-cookie-card" :class="{ inactive: cfg.cookie_source !== 'manual' }">
        <div class="hh-cookie-card-head"><div><h3>手动 Cookie</h3><p>从浏览器开发者工具复制完整 Cookie 值，不需要填写“Cookie:”前缀。</p></div><button class="hh-cookie-text-danger" :disabled="!hasManual" @click="clearManual">清空</button></div>
        <div class="hh-cookie-secret-field"><input v-model="cfg.manual_cookie" :type="cookieVisible ? 'text' : 'password'" autocomplete="off" spellcheck="false" placeholder="name=value; name2=value2" :disabled="cfg.cookie_source !== 'manual'"><button type="button" :disabled="!hasManual" :aria-label="cookieVisible ? '隐藏 Cookie' : '显示 Cookie'" @click="cookieVisible = !cookieVisible"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div>
        <p class="hh-cookie-security">Cookie 相当于账号登录凭证。请勿发送给他人，建议定期更新。</p>
      </section>

      <div v-if="checked" class="hh-cookie-result" :class="checked.ok ? 'hh-cookie-success' : 'hh-cookie-danger'"><b>{{ checked.ok ? '连接正常' : '连接失败' }}</b><span>{{ checked.message }}</span></div>
      <footer><button class="hh-cookie-primary" :disabled="saving || checking" @click="save()">{{ saving ? '保存中…' : '保存设置' }}</button><button class="hh-cookie-secondary" :disabled="saving || checking" @click="check">{{ checking ? '检查中…' : '保存并检查连接' }}</button></footer>
    </template>
  </section>
</template>

<style scoped>

.hh-cookie { color: var(--ios-text); container-type: inline-size; }
.hh-cookie header, .hh-cookie-section-head, .hh-cookie-card-head { display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.hh-cookie header { align-items: flex-start; margin-bottom: 24px; }
.hh-cookie h2 { margin: 2px 0 7px; color: var(--ios-text); font-size: 22px; line-height: 1.4; font-weight: 650; letter-spacing: -.035em; }
.hh-cookie h3 { margin: 0 0 5px; color: var(--ios-text); font-size: 14px; line-height: 1.5; font-weight: 650; }
.hh-cookie header p, .hh-cookie-section-head p, .hh-cookie-card-head p { margin: 0; color: var(--ios-secondary); font-size: 12px; line-height: 1.75; overflow-wrap: anywhere; }
.hh-cookie p.hh-cookie-eyebrow { margin-bottom: 4px; color: var(--ios-secondary); font-size: 10px; font-weight: 600; letter-spacing: .12em; }
.hh-cookie-layout { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(0, .85fr); align-items: start; gap: 18px; }
.hh-cookie-settings, .hh-cookie-card, .hh-cookie-guide { min-width: 0; padding: 22px; border: 1px solid var(--ios-line); border-radius: 24px; background: var(--ios-surface); }
.hh-cookie-section-head { padding-bottom: 8px; }
.hh-cookie button { flex-shrink: 0; min-height: 40px; padding: 9px 15px; border: 1px solid var(--ios-line); border-radius: 13px; background: var(--ios-control); color: var(--ios-text); font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; transition: border-color var(--ios-fast) ease, background var(--ios-fast) ease, color var(--ios-fast) ease; }
.hh-cookie button:hover:not(:disabled) { color: var(--ios-accent-text); border-color: color-mix(in srgb, var(--ios-accent) 30%, var(--ios-line)); }
.hh-cookie button.hh-cookie-primary, .hh-cookie button.hh-cookie-primary:hover:not(:disabled) { color: #fff; background: var(--ios-accent); border-color: transparent; }
.hh-cookie button:disabled { opacity: .45; cursor: not-allowed; }
.hh-cookie-loading { padding: 46px 20px; color: var(--ios-secondary); text-align: center; font-size: 12px; }
.hh-cookie-status, .hh-cookie-badge, .hh-cookie-source-badge { display: inline-flex; align-items: center; flex: 0 0 auto; gap: 8px; max-width: 100%; padding: 7px 12px; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 11px; line-height: 1.5; }
.hh-cookie-status.on, .hh-cookie-badge.on { color: var(--success, #28a56a); border-color: color-mix(in srgb, var(--success, #28a56a) 20%, transparent); background: color-mix(in srgb, var(--success, #28a56a) 8%, transparent); }
.hh-cookie-badge i { width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
.hh-cookie-switch-row { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 18px; min-height: 78px; padding: 16px 0; border-bottom: 1px solid var(--ios-line); cursor: pointer; }
.hh-cookie-switch-row > span:first-child { display: grid; min-width: 0; gap: 4px; }
.hh-cookie-switch-row b { color: var(--ios-text); font-size: 13px; line-height: 1.5; font-weight: 600; }
.hh-cookie-switch-row small { color: var(--ios-secondary); font-size: 11px; line-height: 1.65; overflow-wrap: anywhere; }
.hh-cookie-switch-row > input { position: absolute; inset-inline-end: 0; width: 50px; height: 30px; margin: 0; opacity: 0; z-index: 2; cursor: pointer; }
.hh-cookie-track { position: relative; flex: 0 0 50px; width: 50px; height: 30px; padding: 3px; border: 1px solid color-mix(in srgb, var(--ios-text) 5%, transparent); border-radius: 20px; background: color-mix(in srgb, var(--ios-text) 18%, transparent); transition: background var(--ios-duration) var(--ios-ease); }
.hh-cookie-track > span { display: block; width: 24px; height: 24px; margin: -1px; border-radius: 50%; background: #fff; box-shadow: 0 2px 5px #0002; transition: transform var(--ios-duration) var(--ios-ease); }
.hh-cookie-switch-row > input:checked + .hh-cookie-track { background: var(--ios-accent); }
.hh-cookie-switch-row > input:checked + .hh-cookie-track > span { transform: translateX(20px); }
.hh-cookie-switch-row > input:focus-visible + .hh-cookie-track { outline: 3px solid var(--ios-accent-text); outline-offset: 3px; }
.hh-cookie-fields, .hh-cookie-delay-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 17px 14px; padding-top: 20px; }
.hh-cookie-fields label, .hh-cookie-delay-fields label { display: grid; min-width: 0; gap: 8px; color: var(--ios-secondary); font-size: 12px; line-height: 1.5; }
.hh-cookie-fields label > div, .hh-cookie-delay-fields label > div { display: flex; align-items: center; }
.hh-cookie input[type='text'], .hh-cookie input[type='number'] { width: 100%; min-width: 0; min-height: 42px; padding: 10px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-control); color: var(--ios-text); font: inherit; font-size: 13px; }
.hh-cookie input[type='number'] { padding-right: 38px; font-variant-numeric: tabular-nums; }
.hh-cookie em { margin-left: -29px; color: var(--ios-secondary); font-size: 11px; font-style: normal; pointer-events: none; }
.hh-cookie-guide ul { margin: 18px 0; padding-inline-start: 17px; color: var(--ios-secondary); font-size: 12px; line-height: 1.9; }
.hh-cookie-guide li + li { margin-top: 6px; }
.hh-cookie-note { margin: 0; padding: 13px; border: 1px solid var(--ios-line); border-radius: 13px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 11px; line-height: 1.8; }
:global(html[data-theme='transparent'] .hh-cookie-settings),
:global(html[data-theme='transparent'] .hh-cookie-card),
:global(html[data-theme='transparent'] .hh-cookie-guide) { box-shadow: inset 0 1px 0 color-mix(in srgb, var(--ios-text) 5%, transparent); }
@container (max-width: 740px) {
 .hh-cookie-layout { grid-template-columns: minmax(0, 1fr); }
 .hh-cookie header { flex-wrap: wrap; gap: 13px; }
 .hh-cookie-settings, .hh-cookie-card, .hh-cookie-guide { padding: 18px; border-radius: 21px; }
}
@container (max-width: 390px) {
 .hh-cookie-fields, .hh-cookie-delay-fields { grid-template-columns: minmax(0, 1fr); }
 .hh-cookie-section-head { align-items: flex-start; flex-wrap: wrap; }
 .hh-cookie h2 { font-size: 20px; }
}

.hh-cookie-source-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 13px; margin-bottom: 18px; }
.hh-cookie-source-grid label { position: relative; display: flex; align-items: center; gap: 13px; min-width: 0; min-height: 100px; padding: 18px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); cursor: pointer; transition: border-color var(--ios-duration) ease, background var(--ios-duration) ease; }
.hh-cookie-source-grid label.selected { border-color: color-mix(in srgb, var(--ios-accent) 50%, var(--ios-line)); background: color-mix(in srgb, var(--ios-accent) 7%, transparent); }
.hh-cookie-source-grid label:has(input:focus-visible) { outline: 3px solid var(--ios-accent-text); outline-offset: 3px; }
.hh-cookie-source-grid input { position: absolute; inset: 0; width: 100%; height: 100%; margin: 0; opacity: 0; cursor: pointer; }
.hh-cookie-radio-dot { flex: 0 0 19px; width: 19px; height: 19px; border: 1.5px solid var(--ios-line); border-radius: 50%; background: var(--ios-control); transition: border-width var(--ios-duration) var(--ios-ease), border-color var(--ios-duration) ease; }
.selected .hh-cookie-radio-dot { border: 6px solid var(--ios-accent); background: #fff; }
.hh-cookie-source-grid label > span:last-child { display: grid; min-width: 0; gap: 5px; }
.hh-cookie-source-grid b { color: var(--ios-text); font-size: 13px; line-height: 1.5; font-weight: 600; }
.hh-cookie-source-grid small { color: var(--ios-secondary); font-size: 11px; line-height: 1.7; }
.hh-cookie-card.inactive { background: var(--ios-inset); }
.hh-cookie-card.inactive .hh-cookie-secret-field { opacity: .65; }
.hh-cookie button.hh-cookie-text-danger { background: transparent; border-color: transparent; color: var(--danger, #d94a53); min-height: 36px; padding-inline: 9px; }
.hh-cookie-secret-field { position: relative; margin-top: 17px; }
.hh-cookie-secret-field input { width: 100%; min-width: 0; min-height: 44px; padding: 11px 48px 11px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-control); color: var(--ios-text); font: 12px/1.6 ui-monospace, SFMono-Regular, Consolas, monospace; }
.hh-cookie-secret-field input:disabled { cursor: not-allowed; }
.hh-cookie-secret-field button { position: absolute; inset: 4px 4px 4px auto; width: 36px; min-height: 36px; display: grid; place-items: center; padding: 0; border: 0; border-radius: 9px; background: transparent; color: var(--ios-secondary); }
.hh-cookie-secret-field button:hover:not(:disabled) { background: color-mix(in srgb, var(--ios-accent) 9%, transparent); }
.hh-cookie-secret-field svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.8; }
.hh-cookie-security { margin: 12px 0 0; color: var(--ios-secondary); font-size: 11px; line-height: 1.7; }
.hh-cookie-result { display: grid; gap: 5px; margin-top: 18px; padding: 15px 17px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-inset); font-size: 12px; line-height: 1.7; overflow-wrap: anywhere; }
.hh-cookie-result.hh-cookie-success { color: var(--success, #28a56a); border-color: color-mix(in srgb, var(--success, #28a56a) 20%, transparent); background: color-mix(in srgb, var(--success, #28a56a) 7%, transparent); }
.hh-cookie-result.hh-cookie-danger { color: var(--danger, #d94a53); border-color: color-mix(in srgb, var(--danger, #d94a53) 20%, transparent); background: color-mix(in srgb, var(--danger, #d94a53) 7%, transparent); }
.hh-cookie footer { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
@container (max-width: 590px) {
 .hh-cookie-source-grid { grid-template-columns: minmax(0, 1fr); }
 .hh-cookie-source-grid label { min-height: 86px; }
 .hh-cookie-card-head { align-items: flex-start; gap: 9px; }
 .hh-cookie footer button { flex: 1; }
}

</style>
