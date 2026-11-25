<script setup>
// 发红包 · 配置/管理界面（模块联邦暴露为 ./Config）。
// 平台注入 props { pluginId, host }；host: getConfig/saveConfig/callApi/toast/token。
// 两个页签：配置（左侧分组 + 右侧明细）/ 红包监控（进行中活动、可手动结束、战绩历史）。
import { ref, reactive, onMounted } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

const props = defineProps({
  pluginId: { type: String, required: true },
  host: { type: Object, required: true },
})

const DEFAULTS = {
  enabled: true, create_word: '创建红包', status_word: '红包状态', end_word: '结束红包',
  code_length: 4, text_mode: false, rotate_code: false,
  max_amount: 0, max_count: 0, activity_timeout_minutes: 30, end_delete_delay: 10,
  transfer_prefix: '+', congrats_text: '恭喜 {name} 抢到 {amount} 魔力！',
  blacklist_ids: '',
}

const GROUPS = [
  { key: 'main', label: '总开关' },
  { key: 'command', label: '命令' },
  { key: 'captcha', label: '口令与验证码' },
  { key: 'limit', label: '限制' },
  { key: 'send', label: '发放与文案' },
  { key: 'block', label: '屏蔽' },
]

const tab = ref('settings')
const group = ref('main')
const loading = ref(true)
const configReady = ref(false)
const loadError = ref('')
const saving = ref(false)
const cfg = reactive({ ...DEFAULTS })

// 红包监控
const activities = ref([])
const history = ref([])
const monLoading = ref(false)
const ending = ref('')

onMounted(loadConfig)
async function loadConfig() {
  if (saving.value) return
  loading.value = true
  configReady.value = false
  loadError.value = ''
  try {
    const saved = await props.host.getConfig()
    if (saved != null && (typeof saved !== 'object' || Array.isArray(saved))) throw new Error('配置格式不正确')
    Object.assign(cfg, DEFAULTS, saved || {})
    configReady.value = true
  } catch (e) {
    loadError.value = '读取配置失败：' + (e.message || e)
    props.host.toast.error(loadError.value)
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!configReady.value || saving.value) return
  saving.value = true
  try {
    await props.host.saveConfig({ ...cfg })
    props.host.toast.success('配置已保存')
  } catch (e) {
    props.host.toast.error('保存失败：' + (e.message || e))
  } finally {
    saving.value = false
  }
}

// ── 监控 ──
async function loadMonitor() {
  monLoading.value = true
  try {
    const a = await props.host.callApi('/activities')
    activities.value = a.items || []
    const h = await props.host.callApi('/history')
    history.value = h.items || []
  } catch (e) {
    props.host.toast.error('读取红包活动失败：' + (e.message || e))
  } finally {
    monLoading.value = false
  }
}
async function endOne(item) {
  if (!confirm(`提前结束红包 #${item.rp_id}？剩余 ${item.remaining_count} 个未抢的将不再发放。`)) return
  ending.value = item.key
  try {
    const r = await props.host.callApi('/end', { method: 'POST', body: { key: item.key } })
    if (r.ok) { props.host.toast.success(r.message || '已结束'); await loadMonitor() }
    else props.host.toast.error(r.message || '结束失败')
  } catch (e) { props.host.toast.error('结束失败：' + (e.message || e)) }
  finally { ending.value = '' }
}

function switchTab(t) {
  tab.value = t
  if (t === 'monitor') loadMonitor()
}
</script>

<template>
  <IosSettings>
  <div class="rp-send">
    <div v-if="loading" class="rp-send-loading" role="status">加载配置…</div>
    <template v-else>
      <div class="rp-send-tabs" :style="{ '--rp-send-tab-index': tab === 'settings' ? 0 : 1 }" aria-label="发红包页面">
        <button type="button" :class="['rp-send-tab', { on: tab === 'settings' }]" :aria-pressed="tab === 'settings'" @click="switchTab('settings')"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h9m4 0h3M4 17h3m4 0h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/></svg>功能设置</button>
        <button type="button" :class="['rp-send-tab', { on: tab === 'monitor' }]" :aria-pressed="tab === 'monitor'" @click="switchTab('monitor')"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v12H4zM8 21h8m-4-4v4M7 12l3-3 3 3 4-5"/></svg>红包监控</button>
      </div>

      <div v-if="loadError" class="rp-send-load-error" role="alert"><p>{{ loadError }}。请重新读取，成功前不能保存，以免覆盖原设置。</p><button type="button" class="rp-send-button" @click="loadConfig">重新读取配置</button></div>
      <!-- ============ 配置 ============ -->
      <div v-show="tab === 'settings'" class="rp-send-layout">
        <aside class="rp-send-sidebar" aria-label="设置分组">
          <button v-for="g in GROUPS" :key="g.key" type="button"
                  :class="['rp-send-side-item', { on: group === g.key }]" :aria-pressed="group === g.key" @click="group = g.key">
            <span>{{ g.label }}</span>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7"/></svg>
          </button>
        </aside>

        <div class="rp-send-detail">
          <template v-if="group === 'main'">
            <h3 class="rp-send-title">总开关</h3>
            <section class="rp-send-group">
              <label class="rp-send-switch-row"><span class="rp-send-label">启用发红包<span class="rp-send-note">关闭后不响应发红包命令</span></span><span class="rp-send-switch"><input v-model="cfg.enabled" type="checkbox" role="switch" /><span class="rp-send-switch-track" aria-hidden="true"></span></span></label>
            </section>
          </template>

          <template v-else-if="group === 'command'">
            <h3 class="rp-send-title">命令词</h3>
            <section class="rp-send-group">
              <label class="rp-send-row"><span class="rp-send-label">创建命令词</span><input v-model="cfg.create_word" class="rp-send-input" placeholder="默认：创建红包" /></label>
              <label class="rp-send-row"><span class="rp-send-label">查看状态词</span><input v-model="cfg.status_word" class="rp-send-input" placeholder="默认：红包状态" /></label>
              <label class="rp-send-row"><span class="rp-send-label">结束命令词</span><input v-model="cfg.end_word" class="rp-send-input" placeholder="默认：结束红包" /></label>
            </section>
            <p class="rp-send-tip">格式：<code>{{ cfg.create_word }} 总额 个数 [自定义口令]</code>。自定义口令后会加上随机验证码，按“口令与验证码”设置显示图片或可复制文字。创建命令发送后会自动删除。</p>
          </template>

          <template v-else-if="group === 'captcha'">
            <h3 class="rp-send-title">口令与验证码</h3>
            <section class="rp-send-group">
              <label class="rp-send-switch-row"><span class="rp-send-label">文字口令（不用图片）<span id="text-mode-help" class="rp-send-note">默认关闭，使用验证码图片。开启后直接公布完整口令，点击或长按口令复制，再发到群里参与；文字模式不防复制脚本。</span></span><span class="rp-send-switch"><input v-model="cfg.text_mode" type="checkbox" role="switch" aria-describedby="text-mode-help" /><span class="rp-send-switch-track" aria-hidden="true"></span></span></label>
              <label class="rp-send-switch-row"><span class="rp-send-label">口令一次性有效<span id="rotate-code-help" class="rp-send-note">默认关闭，同一口令可供多人领取。开启后，每领取一份就换新口令，旧口令立即失效；图片、文字模式都适用。无论是否开启，每人都只能领一次。</span></span><span class="rp-send-switch"><input v-model="cfg.rotate_code" type="checkbox" role="switch" aria-describedby="rotate-code-help" /><span class="rp-send-switch-track" aria-hidden="true"></span></span></label>
              <label class="rp-send-row"><span class="rp-send-label">验证码位数<span class="rp-send-note">4–8 位，默认 4 位，不区分大小写</span></span>
                <input v-model.number="cfg.code_length" class="rp-send-input rp-send-small" type="number" min="4" max="8" /></label>
            </section>
            <p class="rp-send-tip rp-send-warning">请在当前红包结束后保存。保存会重载插件，新设置用于之后创建的红包。</p>
          </template>

          <template v-else-if="group === 'limit'">
            <h3 class="rp-send-title">限制</h3>
            <section class="rp-send-group">
              <label class="rp-send-row"><span class="rp-send-label">总额上限<span class="rp-send-note">单位：魔力，0 表示不限</span></span><input v-model.number="cfg.max_amount" class="rp-send-input rp-send-small" type="number" min="0" /></label>
              <label class="rp-send-row"><span class="rp-send-label">个数上限<span class="rp-send-note">0 表示不限</span></span><input v-model.number="cfg.max_count" class="rp-send-input rp-send-small" type="number" min="0" /></label>
              <label class="rp-send-row"><span class="rp-send-label">活动超时<span class="rp-send-note">单位：分钟，无人抢完则自动结算</span></span><input v-model.number="cfg.activity_timeout_minutes" class="rp-send-input rp-send-small" type="number" min="1" max="240" /></label>
              <label class="rp-send-row"><span class="rp-send-label">结束后删消息<span class="rp-send-note">单位：秒，0 表示不删</span></span><input v-model.number="cfg.end_delete_delay" class="rp-send-input rp-send-small" type="number" min="0" max="600" /></label>
            </section>
          </template>

          <template v-else-if="group === 'send'">
            <h3 class="rp-send-title">发放与文案</h3>
            <section class="rp-send-group">
              <label class="rp-send-row"><span class="rp-send-label">转账金额前缀<span class="rp-send-note">群转账 Bot 据此打款，默认 +</span></span><input v-model="cfg.transfer_prefix" class="rp-send-input rp-send-small" /></label>
              <label class="rp-send-row rp-send-stacked"><span class="rp-send-label">祝贺文案<span class="rp-send-note">可用 {name}、{amount}、{id} 占位</span></span>
                <textarea v-model="cfg.congrats_text" class="rp-send-input" rows="3" placeholder="可用 {name} {amount} {id} 占位"></textarea></label>
            </section>
          </template>

          <template v-else-if="group === 'block'">
            <h3 class="rp-send-title">屏蔽</h3>
            <section class="rp-send-group">
              <label class="rp-send-row rp-send-stacked"><span class="rp-send-label">屏蔽用户 ID<span class="rp-send-note">一行一个或用逗号分隔；这些用户不计入参与，也不发放红包。</span></span>
                <textarea v-model="cfg.blacklist_ids" class="rp-send-input" rows="4" placeholder="一行一个或逗号分隔的用户ID，这些用户参与不计入、不发放"></textarea></label>
            </section>
          </template>

          <div class="rp-send-savebar"><button type="button" class="rp-send-button rp-send-primary" :disabled="saving || !configReady" @click="save">{{ saving ? '保存中…' : '保存配置' }}</button></div>
        </div>
      </div>

      <!-- ============ 红包监控 ============ -->
      <div v-show="tab === 'monitor'" class="rp-send-pane">
        <div class="rp-send-toolbar">
          <h3 class="rp-send-title">进行中的红包 <span class="rp-send-count">{{ activities.length }}</span></h3>
          <button type="button" class="rp-send-button" @click="loadMonitor"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 11.5-2L20 8M4 16l2.5 3A7 7 0 0 0 18 17"/></svg>刷新</button>
        </div>
        <div v-if="monLoading" class="rp-send-loading" role="status">加载中…</div>
        <template v-else>
          <div v-if="!activities.length" class="rp-send-empty"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h16v13H4zM3 4h18v4H3zM12 4v17M12 4C6-2 3 3 7 4m5 0c6-6 9-1 5 0"/></svg><h3>当前没有进行中的红包</h3><p>在群里用创建命令词发红包后会显示在这里</p></div>
          <div v-else class="rp-send-table-wrap" tabindex="0" role="region" aria-label="进行中的红包列表"><table class="rp-send-table">
            <thead><tr><th>编号</th><th>群</th><th>总额</th><th>进度</th><th>剩余金额</th><th>已参与</th><th>口令</th><th></th></tr></thead>
            <tbody>
              <tr v-for="a in activities" :key="a.key">
                <td class="rp-send-mono">#{{ a.rp_id }}</td>
                <td>{{ a.chat_title || a.chat_id }}</td>
                <td>{{ a.total_amount }}</td>
                <td>{{ a.packet_count - a.remaining_count }}/{{ a.packet_count }}</td>
                <td class="rp-send-muted">{{ a.remaining_amount }}</td>
                <td>{{ a.participants }}</td>
                <td class="rp-send-mono">{{ a.keyword }}</td>
                <td><button type="button" class="rp-send-button rp-send-danger" :disabled="ending" @click="endOne(a)">{{ ending === a.key ? '结束中…' : '结束' }}</button></td>
              </tr>
            </tbody>
          </table></div>

          <div v-if="history.length" class="rp-send-history">
            <h3 class="rp-send-title">红包战绩 <span class="rp-send-note">最近 {{ history.length }} 条</span></h3>
            <div class="rp-send-table-wrap" tabindex="0" role="region" aria-label="红包历史战绩"><table class="rp-send-table">
              <thead><tr><th>编号</th><th>群</th><th>总额</th><th>个数</th><th>参与</th><th>发放</th><th>时间</th></tr></thead>
              <tbody>
                <tr v-for="(h, i) in history" :key="i">
                  <td class="rp-send-mono">#{{ h.rp_id }}</td>
                  <td>{{ h.chat_title || h.chat_id }} <span class="rp-send-muted">({{ h.chat_id }})</span></td>
                  <td>{{ h.total_amount }}</td>
                  <td>{{ h.packet_count }}</td>
                  <td>{{ h.participants }}</td>
                  <td class="rp-send-success">{{ h.distributed }}</td>
                  <td class="rp-send-muted">{{ h.time || '—' }}</td>
                </tr>
              </tbody>
            </table></div>
          </div>
        </template>
      </div>
    </template>
  </div>
  </IosSettings>
</template>

<style scoped>
.rp-send { display: flex; flex-direction: column; gap: 24px; min-width: 0; color: var(--ios-text); }
.rp-send svg { width: 19px; height: 19px; flex: none; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }
.rp-send-tabs { position: relative; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); isolation: isolate; gap: 4px; padding: 4px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-inset); }
.rp-send-tabs::before { content: ''; position: absolute; inset: 4px auto 4px 4px; width: calc((100% - 12px) / 2); border-radius: 11px; background: var(--ios-control); box-shadow: 0 2px 5px rgb(0 0 0 / .08); transform: translateX(calc(var(--rp-send-tab-index) * (100% + 4px))); transition: transform var(--ios-duration) var(--ios-ease); z-index: -1; }
.rp-send-tab { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 42px; padding: 8px 12px; border: 0; border-radius: 11px; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.rp-send-tab.on { color: var(--ios-text); font-weight: 650; }
.rp-send-tab:hover { color: var(--ios-text); }
.rp-send-layout { display: grid; grid-template-columns: 150px minmax(0, 1fr); gap: 24px; align-items: start; min-width: 0; }
.rp-send-sidebar { display: flex; flex-direction: column; gap: 4px; min-width: 0; padding: 6px; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-inset); }
.rp-send-side-item { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 44px; padding: 9px 12px; border: 0; border-radius: 12px; background: transparent; color: var(--ios-secondary); text-align: left; cursor: pointer; }
.rp-send-side-item svg { width: 13px; height: 13px; opacity: .6; }
.rp-send-side-item:hover { color: var(--ios-text); background: var(--ios-control); }
.rp-send-side-item.on { color: var(--ios-text); background: var(--ios-control); font-weight: 600; box-shadow: 0 2px 4px rgb(0 0 0 / .06); }
.rp-send-detail { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.rp-send-title { margin: 0; color: var(--ios-text); font-size: 16px; font-weight: 650; line-height: 1.5; letter-spacing: -.015em; }
.rp-send-group { overflow: hidden; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-surface); }
.rp-send-row, .rp-send-switch-row { display: flex; justify-content: space-between; align-items: center; gap: 18px; min-height: 74px; padding: 17px 20px; }
.rp-send-row + .rp-send-row, .rp-send-switch-row + .rp-send-switch-row, .rp-send-switch-row + .rp-send-row { border-top: 1px solid var(--ios-line); }
.rp-send-label { display: flex; flex-direction: column; gap: 4px; min-width: 0; font-weight: 500; }
.rp-send-note, .rp-send-tip, .rp-send-muted { color: var(--ios-secondary); font-size: 12px; font-weight: 400; line-height: 1.75; overflow-wrap: anywhere; }
.rp-send-note { display: block; }
.rp-send-tip { margin: 0; max-width: 72ch; padding-inline: 3px; }
.rp-send-warning { color: var(--warning, #926100); }
.rp-send-input { flex: 1; width: 100%; min-width: 0; max-width: 240px; min-height: 42px; padding: 9px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-text); transition: border-color var(--ios-fast) ease; }
.rp-send-input:focus { border-color: var(--accent, #0063dc); }
.rp-send-input.rp-send-small { flex: 0 0 96px; width: 96px; max-width: 96px; text-align: center; font-variant-numeric: tabular-nums; }
.rp-send-stacked { flex-direction: column; align-items: stretch; gap: 13px; }
.rp-send-stacked textarea { max-width: none; min-height: 108px; resize: vertical; line-height: 1.7; }
.rp-send-switch-row { cursor: pointer; }
.rp-send-switch { position: relative; display: inline-flex; align-items: center; flex: 0 0 50px; width: 50px; min-height: 44px; }
.rp-send-switch input { position: absolute; width: 1px; height: 1px; margin: 0; padding: 0; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.rp-send-switch-track { position: relative; display: block; width: 50px; height: 30px; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); transition: background var(--ios-fast) ease, border-color var(--ios-fast) ease; }
.rp-send-switch-track::after { content: ''; position: absolute; top: 2px; left: 2px; width: 24px; height: 24px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .2); transition: transform var(--ios-duration) var(--ios-ease); }
.rp-send-switch input:checked + .rp-send-switch-track { border-color: transparent; background: var(--ios-accent); }
.rp-send-switch input:checked + .rp-send-switch-track::after { transform: translateX(20px); }
.rp-send-switch-row:active .rp-send-switch-track::after { transform: scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.rp-send-switch-row:active input:checked + .rp-send-switch-track::after { transform: translateX(20px) scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.rp-send-switch input:focus-visible + .rp-send-switch-track { outline: 3px solid var(--accent, #0063dc); outline-offset: 3px; }
.rp-send-savebar { display: flex; justify-content: flex-end; padding-top: 8px; }
.rp-send-button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; padding: 9px 18px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font-weight: 500; cursor: pointer; }
.rp-send-button:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.rp-send-button:disabled { opacity: .5; }
.rp-send-button.rp-send-primary { min-width: 132px; background: var(--ios-accent); color: #fff; border-color: transparent; font-weight: 600; }
.rp-send-primary:hover:not(:disabled) { filter: brightness(1.08); }
.rp-send-button.rp-send-danger { min-height: 38px; padding: 6px 12px; color: var(--danger, #bd2733); }
.rp-send-button.rp-send-danger:hover:not(:disabled) { border-color: var(--danger, #bd2733); }
.rp-send-pane { display: flex; flex-direction: column; gap: 18px; min-width: 0; }
.rp-send-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.rp-send-count { display: inline-flex; justify-content: center; min-width: 28px; margin-left: 5px; padding: 1px 7px; border-radius: 8px; color: var(--ios-secondary); background: var(--ios-inset); font-size: 13px; font-variant-numeric: tabular-nums; }
.rp-send-empty { padding: 40px 24px; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-surface); text-align: center; color: var(--ios-secondary); }
.rp-send-empty > svg { width: 32px; height: 32px; margin-bottom: 14px; }
.rp-send-empty h3 { margin: 0; color: var(--ios-text); font-size: 15px; font-weight: 600; }
.rp-send-empty p { margin: 7px 0 0; font-size: 12px; }
.rp-send-loading { padding: 36px 20px; color: var(--ios-secondary); text-align: center; }
.rp-send-load-error { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; padding: 16px 20px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); color: var(--danger, #bd2733); }
.rp-send-load-error p { flex: 1 1 240px; margin: 0; overflow-wrap: anywhere; }
.rp-send-table-wrap { min-width: 0; max-width: 100%; overflow: auto; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); scrollbar-width: thin; scrollbar-color: var(--border-light, #b9bec9) transparent; }
.rp-send-table { width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
.rp-send-table th, .rp-send-table td { padding: 13px 14px; text-align: left; white-space: nowrap; border-bottom: 1px solid var(--ios-line); }
.rp-send-table th { background: var(--ios-inset); color: var(--ios-secondary); font-size: 12px; font-weight: 500; }
.rp-send-table td { color: var(--ios-text); }
.rp-send-table td:nth-child(2) { min-width: 120px; max-width: 250px; white-space: normal; overflow-wrap: anywhere; }
.rp-send-table tbody tr:last-child td { border-bottom: 0; }
.rp-send-table tbody tr:hover { background: var(--ios-inset); }
.rp-send-table td.rp-send-muted { color: var(--ios-secondary); }
.rp-send-table td.rp-send-success { color: var(--success, #087758); }
.rp-send-mono, .rp-send code { font-family: var(--font-mono, ui-monospace, monospace); font-size: 12px; }
.rp-send code { padding: 2px 5px; border-radius: 5px; background: var(--ios-inset); overflow-wrap: anywhere; }
.rp-send-history { display: flex; flex-direction: column; gap: 14px; margin-top: 8px; min-width: 0; }
.rp-send-history .rp-send-title { display: flex; align-items: baseline; flex-wrap: wrap; gap: 8px; }
:global(html[data-theme='transparent'] .rp-send-group),
:global(html[data-theme='transparent'] .rp-send-empty),
:global(html[data-theme='transparent'] .rp-send-table-wrap) { backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); -webkit-backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); }
@container (max-width: 640px) {
  .rp-send { gap: 20px; }
  .rp-send-layout { grid-template-columns: minmax(0, 1fr); gap: 20px; }
  .rp-send-sidebar { flex-direction: row; flex-wrap: wrap; gap: 4px; padding: 5px; border-radius: 16px; }
  .rp-send-side-item { flex: 1 1 auto; justify-content: center; min-height: 40px; padding: 8px 11px; font-size: 13px; }
  .rp-send-side-item svg { display: none; }
  .rp-send-row, .rp-send-switch-row { padding: 16px; }
  .rp-send-row:not(.rp-send-stacked) { flex-wrap: wrap; gap: 12px; }
  .rp-send-row > .rp-send-input:not(.rp-send-small) { flex-basis: 100%; max-width: none; }
  .rp-send-row:has(> .rp-send-small) .rp-send-label { flex: 1; }
  .rp-send-savebar .rp-send-primary { width: 100%; }
  .rp-send-table th, .rp-send-table td { padding: 12px; }
}
@container (max-width: 350px) {
  .rp-send-tab { padding-inline: 8px; gap: 6px; }
  .rp-send-toolbar { flex-wrap: wrap; }
  .rp-send-toolbar .rp-send-button { margin-left: auto; }
  .rp-send-switch-row { gap: 12px; }
}
@media (forced-colors: active) {
  .rp-send-switch input { position: static; width: 24px; height: 24px; clip-path: none; }
  .rp-send-switch-track { display: none; }
  .rp-send-tabs::before { border: 2px solid Highlight; }
}
</style>
