<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

const props = defineProps({ pluginId: String, host: { type: Object, required: true } })
const cfg = reactive({ enabled: true, notify_result: true, notify_cookie_error: true, lottery_mode: 'fixed', lottery_count: 10, interval_seconds: 7, reserve_beans: 0, sync_every_draws: 20, auto_clean_lottery_mail: false, prize_notify_enabled: true, prize_notify_vip: true, prize_notify_invite: true, prize_notify_big_beans: true, prize_notify_keywords: '', prize_notify_cooldown: 300, stop_on_prize: false, stop_on_vip: true, stop_on_invite: true, stop_on_big_beans: true, big_bean_threshold: 500000, stop_prize_keywords: '', scheduled_stop_enabled: false, scheduled_stop_at: '' })
const status = ref({ running: false, completed: 0, target: 0, detail: '', last_prize: '', last_result: '', current_stats: {}, cumulative_stats: {} })
const busy = ref('')
const saving = ref(false)
const apiError = ref('')
let timer

const progress = computed(() => status.value.target ? Math.min(100, Math.round(status.value.completed / status.value.target * 100)) : 0)
const stateText = computed(() => apiError.value ? '状态连接失败' : (status.value.running ? `正在抽奖 ${status.value.completed}/${status.value.target}` : (status.value.detail || '等待开始')))
const currentStats = computed(() => status.value.current_stats || {})
const cumulativeStats = computed(() => status.value.cumulative_stats || {})
const formatNumber = value => new Intl.NumberFormat('zh-CN').format(Number(value) || 0)
const formatSigned = value => `${Number(value) > 0 ? '+' : ''}${formatNumber(value)}`
const profitTone = value => Number(value) > 0 ? 'positive' : Number(value) < 0 ? 'negative' : 'neutral'
const prizeRows = value => Object.entries(value?.prizes || {}).sort((a, b) => Number(b[1]) - Number(a[1])).slice(0, 20)

async function refresh() {
  try {
    const result = await props.host.callApi('/lottery/status', { method: 'POST', body: {} })
    if (!result || typeof result !== 'object' || !Object.hasOwn(result, 'running') || !Object.hasOwn(result, 'current_stats')) throw new Error('状态接口响应缺少运行字段')
    status.value = result
    apiError.value = String(result.setup_error || '')
  } catch (error) {
    apiError.value = error?.message || String(error)
  }
}
async function save(showToast = true) {
  if (saving.value) return
  saving.value = true
  try {
    cfg.lottery_mode = ['fixed', 'balance', 'reserve'].includes(cfg.lottery_mode) ? cfg.lottery_mode : 'fixed'
    cfg.lottery_count = Math.max(1, Math.trunc(Number(cfg.lottery_count) || 10))
    cfg.interval_seconds = Math.max(3, Math.min(Number(cfg.interval_seconds) || 7, 30))
    cfg.reserve_beans = Math.max(0, Math.trunc(Number(cfg.reserve_beans) || 0))
    cfg.sync_every_draws = Math.max(1, Math.min(200, Math.trunc(Number(cfg.sync_every_draws) || 20)))
    cfg.big_bean_threshold = Math.max(1, Math.trunc(Number(cfg.big_bean_threshold) || 500000))
    cfg.prize_notify_cooldown = Math.max(0, Math.min(86400, Math.trunc(Number(cfg.prize_notify_cooldown) || 300)))
    cfg.scheduled_stop_at = String(cfg.scheduled_stop_at || '')
    await props.host.saveConfig({ ...cfg })
    if (showToast) props.host.toast.success('转盘配置已保存')
  } catch (error) {
    if (showToast) props.host.toast.error(error.message || String(error))
    throw error
  } finally {
    saving.value = false
  }
}
async function action(name, path, method = 'POST') {
  busy.value = name
  try {
    if (name === 'run') await save(false)
    const result = await props.host.callApi(path, { method, body: method === 'POST' ? {} : undefined })
    ;(result.ok ? props.host.toast.success : props.host.toast.error)(result.message || '操作完成')
    await refresh()
  } catch (error) { props.host.toast.error(error.message || String(error)) }
  finally { busy.value = '' }
}

onMounted(async () => {
  Object.assign(cfg, await props.host.getConfig())
  await refresh()
  timer = setInterval(refresh, 1500)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <section class="hh-lottery">
    <header>
      <div><p class="hh-lottery-eyebrow">HHANCLUB</p><h2>幸运转盘</h2><p class="hh-lottery-sub">可指定任意正整数次数，或按当前余额自动抽完。</p></div>
      <span class="hh-lottery-state" :class="{ live: status.running }"><i />{{ stateText }}</span>
    </header>

    <p v-if="apiError" class="hh-lottery-api-error">无法读取转盘状态：{{ apiError }}。请检查插件后端启动日志或重新加载插件。</p>

    <div class="hh-lottery-progress-card">
      <div class="hh-lottery-progress-top"><strong>{{ status.completed }} <small>/ {{ status.target || (cfg.lottery_mode === 'balance' ? '待计算' : cfg.lottery_count) }} 次</small></strong><span>{{ progress }}%</span></div>
      <div class="hh-lottery-track"><i :style="{ width: progress + '%' }" /></div>
      <p>{{ status.last_prize ? `最近奖品：${status.last_prize}` : '开始后这里会实时显示进度与最近奖品。' }}</p>
      <div class="hh-lottery-live-stats">
        <section>
          <div class="hh-lottery-stats-head"><h3>当前任务</h3><span>{{ formatNumber(currentStats.count) }} 次 · 消耗 {{ formatNumber(currentStats.cost) }}</span></div>
          <div class="hh-lottery-balance-line"><span>憨豆奖品 {{ formatNumber(currentStats.beans) }}</span><b class="hh-lottery-profit" :class="profitTone(currentStats.profit)">净盈亏 {{ formatSigned(currentStats.profit) }}</b></div>
          <ul v-if="prizeRows(currentStats).length"><li v-for="([name, count]) in prizeRows(currentStats)" :key="name"><span>{{ name }}</span><b>× {{ formatNumber(count) }}</b></li></ul>
          <p v-else class="hh-lottery-empty-stat">本轮奖品将在这里实时累积。</p>
        </section>
        <section>
          <div class="hh-lottery-stats-head"><h3>累计奖品</h3><span>{{ formatNumber(cumulativeStats.count) }} 次 · 消耗 {{ formatNumber(cumulativeStats.cost) }}</span></div>
          <div class="hh-lottery-balance-line"><span>憨豆奖品 {{ formatNumber(cumulativeStats.beans) }}</span><b class="hh-lottery-profit" :class="profitTone(cumulativeStats.profit)">净盈亏 {{ formatSigned(cumulativeStats.profit) }}</b></div>
          <ul v-if="prizeRows(cumulativeStats).length"><li v-for="([name, count]) in prizeRows(cumulativeStats)" :key="name"><span>{{ name }}</span><b>× {{ formatNumber(count) }}</b></li></ul>
          <p v-else class="hh-lottery-empty-stat">完成第一次抽奖后显示累计记录。</p>
        </section>
      </div>
    </div>

    <div class="hh-lottery-grid">
      <div class="hh-lottery-card hh-lottery-settings">
        <div class="hh-lottery-card-heading">
          <div><h3>抽奖设置</h3><p>配置抽取策略、停止条件与结果通知。</p></div>
          <label class="hh-lottery-toggle-row hh-lottery-switch"><span><b>启用转盘</b><small>允许启动新任务</small></span><input v-model="cfg.enabled" type="checkbox"><span class="hh-lottery-switch-track" aria-hidden="true"><span></span></span></label>
        </div>

        <div class="hh-lottery-settings-columns">
          <section class="hh-lottery-setting-group">
            <h4>抽取与计划</h4>
            <label><span>抽奖方式</span><select v-model="cfg.lottery_mode"><option value="fixed">指定次数</option><option value="balance">按余额抽完</option><option value="reserve">保留余额抽取</option></select></label>
            <label v-if="cfg.lottery_mode === 'fixed'"><span>抽奖次数</span><input v-model.number="cfg.lottery_count" type="number" min="1" step="1"></label>
            <label v-else-if="cfg.lottery_mode === 'reserve'"><span>保留憨豆</span><input v-model.number="cfg.reserve_beans" type="number" min="0" step="1000"></label>
            <p v-else class="hh-lottery-mode-note">启动时读取余额与单次消耗，自动计算本次可抽次数。</p>
            <label><span>抽奖间隔（秒）</span><input v-model.number="cfg.interval_seconds" type="number" min="3" max="30"></label>
            <label><span>余额校准间隔</span><input v-model.number="cfg.sync_every_draws" type="number" min="1" max="200"></label>
            <label class="hh-lottery-switch"><input v-model="cfg.auto_clean_lottery_mail" type="checkbox"><span class="hh-lottery-switch-track" aria-hidden="true"><span></span></span><span>校准时清理转盘通知</span></label>
            <div class="hh-lottery-group-divider"></div>
            <label class="hh-lottery-switch"><input v-model="cfg.scheduled_stop_enabled" type="checkbox"><span class="hh-lottery-switch-track" aria-hidden="true"><span></span></span><span>到指定日期时间自动停止</span></label>
            <label v-if="cfg.scheduled_stop_enabled" class="hh-lottery-stacked-field"><span>停止日期时间</span><input v-model="cfg.scheduled_stop_at" type="datetime-local"></label>
            <p v-if="cfg.scheduled_stop_enabled" class="hh-lottery-mode-note">计划会持久化，平台重启后继续剩余任务，并按时停止。</p>
          </section>

          <section class="hh-lottery-setting-group">
            <h4>大奖与通知</h4>
            <label class="hh-lottery-feature-toggle hh-lottery-switch"><span><b>实时大奖通知</b><small>命中后立即推送富文本表格</small></span><input v-model="cfg.prize_notify_enabled" type="checkbox"><span class="hh-lottery-switch-track" aria-hidden="true"><span></span></span></label>
            <div v-if="cfg.prize_notify_enabled" class="hh-lottery-stop-box hh-lottery-prize-notice-box">
              <div class="hh-lottery-prize-options">
                <label class="hh-lottery-check"><input v-model="cfg.prize_notify_vip" type="checkbox"> VIP</label>
                <label class="hh-lottery-check"><input v-model="cfg.prize_notify_invite" type="checkbox"> 邀请</label>
                <label class="hh-lottery-check"><input v-model="cfg.prize_notify_big_beans" type="checkbox"> 大额憨豆</label>
              </div>
              <label><span>大额门槛</span><input v-model.number="cfg.big_bean_threshold" type="number" min="1" step="10000"></label>
              <label><span>通知关键词</span><input v-model="cfg.prize_notify_keywords" type="text" placeholder="逗号分隔"></label>
              <label><span>相同奖品冷却</span><div class="hh-lottery-input-unit"><input v-model.number="cfg.prize_notify_cooldown" type="number" min="0" max="86400"><em>秒</em></div></label>
            </div>
            <label class="hh-lottery-feature-toggle hh-lottery-switch"><span><b>命中大奖后自动停止</b><small>关闭时只通知，不中断任务</small></span><input v-model="cfg.stop_on_prize" type="checkbox"><span class="hh-lottery-switch-track" aria-hidden="true"><span></span></span></label>
            <div v-if="cfg.stop_on_prize" class="hh-lottery-stop-box">
              <div class="hh-lottery-prize-options">
                <label class="hh-lottery-check"><input v-model="cfg.stop_on_vip" type="checkbox"> VIP</label>
                <label class="hh-lottery-check"><input v-model="cfg.stop_on_invite" type="checkbox"> 邀请</label>
                <label class="hh-lottery-check"><input v-model="cfg.stop_on_big_beans" type="checkbox"> 大额憨豆</label>
              </div>
              <label><span>大额门槛</span><input v-model.number="cfg.big_bean_threshold" type="number" min="1" step="10000"></label>
              <label><span>自定义关键词</span><input v-model="cfg.stop_prize_keywords" type="text" placeholder="逗号分隔"></label>
            </div>
            <div class="hh-lottery-notification-options">
              <label class="hh-lottery-switch"><input v-model="cfg.notify_result" type="checkbox"><span class="hh-lottery-switch-track" aria-hidden="true"><span></span></span><span>完成结果</span></label>
              <label class="hh-lottery-switch"><input v-model="cfg.notify_cookie_error" type="checkbox"><span class="hh-lottery-switch-track" aria-hidden="true"><span></span></span><span>Cookie 异常</span></label>
            </div>
          </section>
        </div>

        <div class="hh-lottery-settings-actions"><button class="hh-lottery-secondary" :disabled="saving" @click="save()">{{ saving ? '保存中…' : '保存设置' }}</button></div>
      </div>
      <div class="hh-lottery-card hh-lottery-result">
        <div class="hh-lottery-result-heading"><h3>最近结果</h3><span>自动刷新</span></div>
        <pre>{{ status.last_result || '还没有抽奖记录。' }}</pre>
      </div>
    </div>

    <footer>
      <button class="hh-lottery-primary" :disabled="busy || status.running || !cfg.enabled" @click="action('run', '/lottery/run')">{{ busy === 'run' ? '正在启动…' : '开始抽奖' }}</button>
      <button class="hh-lottery-danger" :disabled="busy || !status.running" @click="action('stop', '/lottery/stop')">停止抽奖</button>
      <button class="hh-lottery-secondary" :disabled="busy" @click="action('cookie', '/lottery/cookie/check', 'GET')">检查 Cookie 与余额</button>
      <button class="hh-lottery-secondary" :disabled="busy || status.running" @click="action('mail', '/lottery/mail/clean')">清理转盘通知</button>
    </footer>
  </section>
</template>

<style scoped>

.hh-lottery { color: var(--ios-text); container-type: inline-size; }
.hh-lottery header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 24px; }
.hh-lottery h2 { margin: 2px 0 7px; color: var(--ios-text); font-size: 22px; line-height: 1.4; font-weight: 650; letter-spacing: -.035em; }
.hh-lottery h3 { margin: 0; color: var(--ios-text); font-size: 14px; line-height: 1.5; font-weight: 650; }
.hh-lottery-eyebrow { margin: 0 0 4px; color: var(--ios-secondary); font-size: 10px; font-weight: 600; letter-spacing: .12em; }
.hh-lottery-sub { margin: 0; color: var(--ios-secondary); font-size: 12px; line-height: 1.75; }
.hh-lottery-state { display: inline-flex; align-items: center; flex: 0 0 auto; gap: 8px; max-width: 280px; padding: 7px 12px; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 11px; line-height: 1.5; overflow-wrap: anywhere; }
.hh-lottery-state i { flex: 0 0 5px; width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
.hh-lottery-state.live { color: var(--success, #28a56a); border-color: color-mix(in srgb, var(--success, #28a56a) 20%, transparent); background: color-mix(in srgb, var(--success, #28a56a) 8%, transparent); }
.hh-lottery-api-error { margin: 0 0 18px; padding: 14px 16px; border: 1px solid color-mix(in srgb, var(--danger, #d94a53) 20%, transparent); border-radius: 15px; background: color-mix(in srgb, var(--danger, #d94a53) 7%, transparent); color: var(--danger, #d94a53); font-size: 12px; line-height: 1.75; overflow-wrap: anywhere; }
.hh-lottery-progress-card, .hh-lottery-card { min-width: 0; padding: 22px; border: 1px solid var(--ios-line); border-radius: 24px; background: var(--ios-surface); }
.hh-lottery-progress-card { margin-bottom: 18px; }
.hh-lottery-progress-top { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; color: var(--ios-accent-text); font-size: 12px; font-variant-numeric: tabular-nums; }
.hh-lottery-progress-top strong { color: var(--ios-text); font-size: 30px; font-weight: 650; letter-spacing: -.035em; }
.hh-lottery-progress-top small { color: var(--ios-secondary); font-size: 12px; font-weight: 400; letter-spacing: 0; }
.hh-lottery-track { height: 6px; margin: 16px 0 12px; overflow: hidden; border-radius: 999px; background: color-mix(in srgb, var(--ios-text) 9%, transparent); }
.hh-lottery-track i { display: block; height: 100%; border-radius: inherit; background: var(--ios-accent); transition: width var(--ios-duration) var(--ios-ease); }
.hh-lottery-progress-card p { margin: 0; color: var(--ios-secondary); font-size: 12px; line-height: 1.7; overflow-wrap: anywhere; }
.hh-lottery-live-stats { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--ios-line); }
.hh-lottery-live-stats > section { min-width: 0; }
.hh-lottery-live-stats > section + section { padding-left: 20px; border-left: 1px solid var(--ios-line); }
.hh-lottery-stats-head { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 6px 12px; margin-bottom: 10px; }
.hh-lottery-stats-head h3 { font-size: 13px; }
.hh-lottery-stats-head > span { color: var(--ios-secondary); font-size: 10px; line-height: 1.5; font-variant-numeric: tabular-nums; }
.hh-lottery-balance-line { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 6px 12px; margin-bottom: 13px; color: var(--ios-secondary); font-size: 11px; line-height: 1.5; font-variant-numeric: tabular-nums; }
.hh-lottery-profit { font-weight: 600; }
.hh-lottery-profit.positive { color: var(--success, #28a56a); }
.hh-lottery-profit.negative { color: var(--danger, #d94a53); }
.hh-lottery-profit.neutral { color: var(--ios-secondary); }
.hh-lottery-live-stats ul { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 15px; max-height: 180px; overflow-y: auto; overscroll-behavior: contain; margin: 0; padding: 0; list-style: none; }
.hh-lottery-live-stats li { display: flex; justify-content: space-between; gap: 10px; min-width: 0; color: var(--ios-text); font-size: 11px; line-height: 1.65; }
.hh-lottery-live-stats li > span { min-width: 0; overflow-wrap: anywhere; }
.hh-lottery-live-stats li b { flex-shrink: 0; color: var(--ios-accent-text); font-weight: 500; font-variant-numeric: tabular-nums; }
.hh-lottery-progress-card .hh-lottery-empty-stat { padding: 12px 0; color: var(--ios-secondary); font-size: 11px; }
.hh-lottery-grid { display: grid; grid-template-columns: minmax(0, 1fr); align-items: start; gap: 18px; }
.hh-lottery-card-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding-bottom: 18px; border-bottom: 1px solid var(--ios-line); }
.hh-lottery-card-heading p { margin: 5px 0 0; color: var(--ios-secondary); font-size: 12px; line-height: 1.7; }
.hh-lottery-settings-columns { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 28px; padding-top: 20px; }
.hh-lottery-setting-group { min-width: 0; }
.hh-lottery-setting-group + .hh-lottery-setting-group { padding-left: 28px; border-left: 1px solid var(--ios-line); }
.hh-lottery-setting-group h4 { margin: 0 0 17px; color: var(--ios-secondary); font-size: 12px; line-height: 1.5; font-weight: 600; }
.hh-lottery-settings label:not(.hh-lottery-check, .hh-lottery-switch) { display: grid; grid-template-columns: minmax(80px, .8fr) minmax(0, 1.2fr); align-items: center; gap: 12px; margin: 14px 0; color: var(--ios-text); font-size: 12px; line-height: 1.6; }
.hh-lottery input[type='number'], .hh-lottery input[type='datetime-local'], .hh-lottery input[type='text'], .hh-lottery select { width: 100%; min-width: 0; min-height: 42px; padding: 10px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-control); color: var(--ios-text); font: inherit; font-size: 12px; font-variant-numeric: tabular-nums; }
.hh-lottery select { cursor: pointer; padding-right: 26px; }
.hh-lottery input::placeholder { color: var(--ios-secondary); }
.hh-lottery-mode-note { margin: 10px 0 15px; padding: 13px; border: 1px solid var(--ios-line); border-radius: 13px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 11px; line-height: 1.8; }
.hh-lottery-group-divider { height: 1px; margin: 20px 0 13px; background: var(--ios-line); }
.hh-lottery-switch { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 16px; min-height: 58px; padding: 8px 0; color: var(--ios-text); font-size: 12px; line-height: 1.6; cursor: pointer; }
.hh-lottery-switch > span:not(.hh-lottery-switch-track) { display: grid; order: -1; flex: 1; min-width: 0; gap: 4px; }
.hh-lottery-switch b { color: var(--ios-text); font-size: 12px; line-height: 1.6; font-weight: 600; }
.hh-lottery-switch small { color: var(--ios-secondary); font-size: 10px; line-height: 1.7; }
.hh-lottery-switch > input { position: absolute; inset-inline-end: 0; width: 50px; height: 30px; margin: 0; opacity: 0; z-index: 2; cursor: pointer; }
.hh-lottery-switch-track { position: relative; flex: 0 0 50px; width: 50px; height: 30px; padding: 3px; border: 1px solid color-mix(in srgb, var(--ios-text) 5%, transparent); border-radius: 20px; background: color-mix(in srgb, var(--ios-text) 18%, transparent); transition: background var(--ios-duration) var(--ios-ease); }
.hh-lottery-switch-track > span { display: block; width: 24px; height: 24px; margin: -1px; border-radius: 50%; background: #fff; box-shadow: 0 2px 5px #0002; transition: transform var(--ios-duration) var(--ios-ease); }
.hh-lottery-switch > input:checked + .hh-lottery-switch-track { background: var(--ios-accent); }
.hh-lottery-switch > input:checked + .hh-lottery-switch-track > span { transform: translateX(20px); }
.hh-lottery-switch > input:focus-visible + .hh-lottery-switch-track { outline: 3px solid var(--ios-accent-text); outline-offset: 3px; }
.hh-lottery-toggle-row { flex: 0 0 auto; padding: 0; }
.hh-lottery-feature-toggle + .hh-lottery-feature-toggle { border-top: 1px solid var(--ios-line); }
.hh-lottery-check { display: inline-flex; align-items: center; gap: 7px; margin: 5px 0; color: var(--ios-secondary); font-size: 12px; line-height: 1.5; cursor: pointer; }
.hh-lottery-check input { width: 15px; height: 15px; margin: 0; accent-color: var(--ios-accent-text); cursor: pointer; }
.hh-lottery-stop-box { margin: 8px 0 15px; padding: 15px; border: 1px solid var(--ios-line); border-radius: 17px; background: var(--ios-inset); }
.hh-lottery-prize-options { display: flex; flex-wrap: wrap; gap: 6px 15px; padding-bottom: 10px; border-bottom: 1px solid var(--ios-line); }
.hh-lottery-settings .hh-lottery-stop-box label:not(.hh-lottery-check, .hh-lottery-switch) { grid-template-columns: minmax(0, 1fr); gap: 7px; margin: 12px 0; }
.hh-lottery-notification-options { display: grid; grid-template-columns: minmax(0, 1fr); margin-top: 14px; padding-top: 10px; border-top: 1px solid var(--ios-line); }
.hh-lottery-input-unit { display: flex; align-items: center; min-width: 0; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-control); }
.hh-lottery-input-unit:focus-within { outline: 3px solid var(--ios-accent-text); border-color: var(--ios-accent-text); }
.hh-lottery-input-unit input { min-width: 0; border: 0; background: transparent; }
.hh-lottery-input-unit em { padding-right: 12px; color: var(--ios-secondary); font-size: 11px; font-style: normal; }
.hh-lottery-settings-actions { display: flex; justify-content: flex-end; margin-top: 20px; padding-top: 17px; border-top: 1px solid var(--ios-line); }
.hh-lottery-result-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 15px; }
.hh-lottery-result-heading > span { color: var(--ios-secondary); font-size: 10px; }
.hh-lottery-result pre { min-height: 110px; max-height: 340px; overflow-y: auto; overscroll-behavior: contain; white-space: pre-wrap; overflow-wrap: anywhere; margin: 0; padding: 16px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-inset); color: var(--ios-secondary); font: 12px/1.85 ui-monospace, SFMono-Regular, Consolas, monospace; }
.hh-lottery footer { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
.hh-lottery button { min-height: 40px; padding: 9px 16px; border: 1px solid var(--ios-line); border-radius: 13px; background: var(--ios-control); color: var(--ios-text); font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; transition: border-color var(--ios-fast) ease, color var(--ios-fast) ease, background var(--ios-fast) ease; }
.hh-lottery button:hover:not(:disabled) { color: var(--ios-accent-text); border-color: color-mix(in srgb, var(--ios-accent) 30%, var(--ios-line)); }
.hh-lottery button.hh-lottery-primary, .hh-lottery button.hh-lottery-primary:hover:not(:disabled) { color: #fff; background: var(--ios-accent); border-color: transparent; }
.hh-lottery button.hh-lottery-danger { color: var(--danger, #d94a53); border-color: color-mix(in srgb, var(--danger, #d94a53) 25%, var(--ios-line)); background: color-mix(in srgb, var(--danger, #d94a53) 7%, transparent); }
.hh-lottery button:disabled { opacity: .45; cursor: not-allowed; }
:global(html[data-theme='transparent'] .hh-lottery-progress-card),
:global(html[data-theme='transparent'] .hh-lottery-card) { box-shadow: inset 0 1px 0 color-mix(in srgb, var(--ios-text) 5%, transparent); }
@container (max-width: 760px) {
 .hh-lottery-settings-columns, .hh-lottery-live-stats { grid-template-columns: minmax(0, 1fr); }
 .hh-lottery-setting-group + .hh-lottery-setting-group { padding: 22px 0 0; border-left: 0; border-top: 1px solid var(--ios-line); }
 .hh-lottery-live-stats > section + section { padding: 20px 0 0; border-left: 0; border-top: 1px solid var(--ios-line); }
 .hh-lottery-progress-card, .hh-lottery-card { padding: 18px; border-radius: 21px; }
 .hh-lottery-card-heading { flex-wrap: wrap; gap: 14px; }
 .hh-lottery-toggle-row { width: 100%; }
}
@container (max-width: 460px) {
 .hh-lottery header { flex-wrap: wrap; gap: 13px; }
 .hh-lottery-state { max-width: 100%; }
 .hh-lottery-settings label:not(.hh-lottery-check, .hh-lottery-switch) { grid-template-columns: minmax(0, 1fr); gap: 8px; }
 .hh-lottery-live-stats ul { grid-template-columns: minmax(0, 1fr); }
 .hh-lottery footer button { flex: 1 1 40%; }
 .hh-lottery h2 { font-size: 20px; }
}

</style>
