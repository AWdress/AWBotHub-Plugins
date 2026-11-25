<script setup>
import { onMounted, reactive, ref } from 'vue'

const props = defineProps({ pluginId: String, host: { type: Object, required: true } })
const cfg = reactive({ bonus_enabled: true, auto_confirm_bonus_transfer: false, notify_cookie_error: true, single_command: '.hh', batch_command: '.hhs', cooldown_seconds: 10, result_delete: 90 })
const loading = ref(true)
const saving = ref(false)
const checking = ref(false)

async function save() {
  saving.value = true
  try {
    cfg.single_command = String(cfg.single_command || '.hh').trim() || '.hh'
    cfg.batch_command = String(cfg.batch_command || '.hhs').trim() || '.hhs'
    cfg.cooldown_seconds = Math.max(0, Math.min(Number(cfg.cooldown_seconds) || 0, 600))
    cfg.result_delete = Math.max(10, Math.min(Number(cfg.result_delete) || 90, 600))
    await props.host.saveConfig({ ...cfg })
    props.host.toast.success('赠豆配置已保存')
  } catch (error) { props.host.toast.error('保存失败：' + (error.message || error)) }
  finally { saving.value = false }
}

async function checkCookie() {
  checking.value = true
  try {
    const result = await props.host.callApi('/bonus/cookie/check')
    ;(result.ok ? props.host.toast.success : props.host.toast.error)(result.message)
  } catch (error) { props.host.toast.error('检查失败：' + (error.message || error)) }
  finally { checking.value = false }
}

onMounted(async () => {
  try { Object.assign(cfg, await props.host.getConfig() || {}) }
  catch (error) { props.host.toast.error('读取配置失败：' + (error.message || error)) }
  finally { loading.value = false }
})
</script>

<template>
  <section class="hh-bonus">
    <div v-if="loading" class="hh-bonus-loading">正在读取配置…</div>
    <template v-else>
      <header>
        <div><p class="hh-bonus-eyebrow">HHANCLUB</p><h2>赠豆助手</h2><p>通过自己的用户账号发送命令，支持单人和批量赠送。</p></div>
        <span class="hh-bonus-badge" :class="{ on: cfg.bonus_enabled }"><i />{{ cfg.bonus_enabled ? '命令已启用' : '命令已停用' }}</span>
      </header>

      <div class="hh-bonus-layout">
        <section class="hh-bonus-card">
          <div class="hh-bonus-section-head"><div><h3>命令设置</h3><p>修改后立即保存，下一条消息开始生效。</p></div><button class="hh-bonus-primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存设置' }}</button></div>
          <label class="hh-bonus-switch-row"><span><b>启用赠豆命令</b><small>监听用户账号发出的匹配命令</small></span><input v-model="cfg.bonus_enabled" type="checkbox" role="switch"><span class="hh-bonus-track" aria-hidden="true"><span></span></span></label>
          <label class="hh-bonus-switch-row"><span><b>自动确认憨豆转赠</b><small>仅确认官方机器人 8780479105 对本账号赠豆命令发出的二次确认</small></span><input v-model="cfg.auto_confirm_bonus_transfer" type="checkbox" role="switch"><span class="hh-bonus-track" aria-hidden="true"><span></span></span></label>
          <label class="hh-bonus-switch-row"><span><b>Cookie 异常时通知</b><small>登录态失效时通过平台通知提醒</small></span><input v-model="cfg.notify_cookie_error" type="checkbox" role="switch"><span class="hh-bonus-track" aria-hidden="true"><span></span></span></label>
          <div class="hh-bonus-fields">
            <label><span>单人命令</span><input v-model="cfg.single_command" type="text" placeholder=".hh"></label>
            <label><span>批量命令</span><input v-model="cfg.batch_command" type="text" placeholder=".hhs"></label>
            <label><span>赠送冷却</span><div><input v-model.number="cfg.cooldown_seconds" type="number" min="0" max="600"><em>秒</em></div></label>
            <label><span>结果保留</span><div><input v-model.number="cfg.result_delete" type="number" min="10" max="600"><em>秒</em></div></label>
          </div>
        </section>

        <aside class="hh-bonus-card hh-bonus-guide">
          <h3>命令格式</h3>
          <div class="hh-bonus-example"><span>单人赠送</span><code>{{ cfg.single_command || '.hh' }} Alice 100 感谢分享</code></div>
          <div class="hh-bonus-example"><span>批量赠送</span><code>{{ cfg.batch_command || '.hhs' }} Alice Bob 100 感谢</code></div>
          <ul><li>站点最低赠送 100 憨豆</li><li>批量任务最多 50 位用户</li><li>自动确认只识别官方机器人和“确认赠送”按钮</li></ul>
          <button class="hh-bonus-secondary" :disabled="checking" @click="checkCookie">{{ checking ? '检查中…' : '检查平台 Cookie' }}</button>
        </aside>
      </div>
    </template>
  </section>
</template>

<style scoped>

.hh-bonus { color: var(--ios-text); container-type: inline-size; }
.hh-bonus header, .hh-bonus-section-head, .hh-bonus-card-head { display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.hh-bonus header { align-items: flex-start; margin-bottom: 24px; }
.hh-bonus h2 { margin: 2px 0 7px; color: var(--ios-text); font-size: 22px; line-height: 1.4; font-weight: 650; letter-spacing: -.035em; }
.hh-bonus h3 { margin: 0 0 5px; color: var(--ios-text); font-size: 14px; line-height: 1.5; font-weight: 650; }
.hh-bonus header p, .hh-bonus-section-head p, .hh-bonus-card-head p { margin: 0; color: var(--ios-secondary); font-size: 12px; line-height: 1.75; overflow-wrap: anywhere; }
.hh-bonus p.hh-bonus-eyebrow { margin-bottom: 4px; color: var(--ios-secondary); font-size: 10px; font-weight: 600; letter-spacing: .12em; }
.hh-bonus-layout { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(0, .85fr); align-items: start; gap: 18px; }
.hh-bonus-settings, .hh-bonus-card, .hh-bonus-guide { min-width: 0; padding: 22px; border: 1px solid var(--ios-line); border-radius: 24px; background: var(--ios-surface); }
.hh-bonus-section-head { padding-bottom: 8px; }
.hh-bonus button { flex-shrink: 0; min-height: 40px; padding: 9px 15px; border: 1px solid var(--ios-line); border-radius: 13px; background: var(--ios-control); color: var(--ios-text); font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; transition: border-color var(--ios-fast) ease, background var(--ios-fast) ease, color var(--ios-fast) ease; }
.hh-bonus button:hover:not(:disabled) { color: var(--ios-accent-text); border-color: color-mix(in srgb, var(--ios-accent) 30%, var(--ios-line)); }
.hh-bonus button.hh-bonus-primary, .hh-bonus button.hh-bonus-primary:hover:not(:disabled) { color: #fff; background: var(--ios-accent); border-color: transparent; }
.hh-bonus button:disabled { opacity: .45; cursor: not-allowed; }
.hh-bonus-loading { padding: 46px 20px; color: var(--ios-secondary); text-align: center; font-size: 12px; }
.hh-bonus-status, .hh-bonus-badge, .hh-bonus-source-badge { display: inline-flex; align-items: center; flex: 0 0 auto; gap: 8px; max-width: 100%; padding: 7px 12px; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 11px; line-height: 1.5; }
.hh-bonus-status.on, .hh-bonus-badge.on { color: var(--success, #28a56a); border-color: color-mix(in srgb, var(--success, #28a56a) 20%, transparent); background: color-mix(in srgb, var(--success, #28a56a) 8%, transparent); }
.hh-bonus-badge i { width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
.hh-bonus-switch-row { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 18px; min-height: 78px; padding: 16px 0; border-bottom: 1px solid var(--ios-line); cursor: pointer; }
.hh-bonus-switch-row > span:first-child { display: grid; min-width: 0; gap: 4px; }
.hh-bonus-switch-row b { color: var(--ios-text); font-size: 13px; line-height: 1.5; font-weight: 600; }
.hh-bonus-switch-row small { color: var(--ios-secondary); font-size: 11px; line-height: 1.65; overflow-wrap: anywhere; }
.hh-bonus-switch-row > input { position: absolute; inset-inline-end: 0; width: 50px; height: 30px; margin: 0; opacity: 0; z-index: 2; cursor: pointer; }
.hh-bonus-track { position: relative; flex: 0 0 50px; width: 50px; height: 30px; padding: 3px; border: 1px solid color-mix(in srgb, var(--ios-text) 5%, transparent); border-radius: 20px; background: color-mix(in srgb, var(--ios-text) 18%, transparent); transition: background var(--ios-duration) var(--ios-ease); }
.hh-bonus-track > span { display: block; width: 24px; height: 24px; margin: -1px; border-radius: 50%; background: #fff; box-shadow: 0 2px 5px #0002; transition: transform var(--ios-duration) var(--ios-ease); }
.hh-bonus-switch-row > input:checked + .hh-bonus-track { background: var(--ios-accent); }
.hh-bonus-switch-row > input:checked + .hh-bonus-track > span { transform: translateX(20px); }
.hh-bonus-switch-row > input:focus-visible + .hh-bonus-track { outline: 3px solid var(--ios-accent-text); outline-offset: 3px; }
.hh-bonus-fields, .hh-bonus-delay-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 17px 14px; padding-top: 20px; }
.hh-bonus-fields label, .hh-bonus-delay-fields label { display: grid; min-width: 0; gap: 8px; color: var(--ios-secondary); font-size: 12px; line-height: 1.5; }
.hh-bonus-fields label > div, .hh-bonus-delay-fields label > div { display: flex; align-items: center; }
.hh-bonus input[type='text'], .hh-bonus input[type='number'] { width: 100%; min-width: 0; min-height: 42px; padding: 10px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-control); color: var(--ios-text); font: inherit; font-size: 13px; }
.hh-bonus input[type='number'] { padding-right: 38px; font-variant-numeric: tabular-nums; }
.hh-bonus em { margin-left: -29px; color: var(--ios-secondary); font-size: 11px; font-style: normal; pointer-events: none; }
.hh-bonus-guide ul { margin: 18px 0; padding-inline-start: 17px; color: var(--ios-secondary); font-size: 12px; line-height: 1.9; }
.hh-bonus-guide li + li { margin-top: 6px; }
.hh-bonus-note { margin: 0; padding: 13px; border: 1px solid var(--ios-line); border-radius: 13px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 11px; line-height: 1.8; }
:global(html[data-theme='transparent'] .hh-bonus-settings),
:global(html[data-theme='transparent'] .hh-bonus-card),
:global(html[data-theme='transparent'] .hh-bonus-guide) { box-shadow: inset 0 1px 0 color-mix(in srgb, var(--ios-text) 5%, transparent); }
@container (max-width: 740px) {
 .hh-bonus-layout { grid-template-columns: minmax(0, 1fr); }
 .hh-bonus header { flex-wrap: wrap; gap: 13px; }
 .hh-bonus-settings, .hh-bonus-card, .hh-bonus-guide { padding: 18px; border-radius: 21px; }
}
@container (max-width: 390px) {
 .hh-bonus-fields, .hh-bonus-delay-fields { grid-template-columns: minmax(0, 1fr); }
 .hh-bonus-section-head { align-items: flex-start; flex-wrap: wrap; }
 .hh-bonus h2 { font-size: 20px; }
}

.hh-bonus-example { display: grid; gap: 8px; margin: 18px 0; }
.hh-bonus-example > span { color: var(--ios-secondary); font-size: 11px; }
.hh-bonus-example code { display: block; overflow-wrap: anywhere; padding: 13px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-accent-text); font: 12px/1.8 ui-monospace, SFMono-Regular, Consolas, monospace; }
.hh-bonus-secondary { width: 100%; }
</style>
