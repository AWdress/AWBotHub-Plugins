<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

const props = defineProps({
  pluginId: { type: String, required: true },
  host: { type: Object, required: true },
})

const DEFAULTS = {
  enabled: false,
  trigger_keywords: '验证码,发送图中字符,识别上方,幸运红包',
  target_senders: '', target_groups: [],
  ocr_enabled: true, copy_fallback: true,
  code_min_len: 4, code_max_len: 8, join_delay: 2,
  slash_command_protection: true, slash_min_total: 0,
  success_markers: '抢到,恭喜', transfer_prefix: '+',
  activity_ttl_minutes: 30, notify_owner: true,
}
const GROUPS = [
  { key: 'main', label: '总开关' }, { key: 'scope', label: '识别范围' },
  { key: 'recognize', label: '口令识别' }, { key: 'behavior', label: '参与行为' },
  { key: 'general', label: '通用' },
]

const cfg = reactive({ ...DEFAULTS })
const tab = ref('settings')
const group = ref('main')
const loading = ref(true)
const configReady = ref(false)
const saving = ref(false)
const historyLoading = ref(false)
const clearing = ref(false)
const clearConfirm = ref(false)
const saveMessage = ref('')
const saveError = ref(false)
const history = ref([])
const chatNames = ref([])
const status = ref({ ocr_available: false, active_count: 0 })
const groupsText = computed({
  get: () => Array.isArray(cfg.target_groups) ? cfg.target_groups.join('\n') : String(cfg.target_groups || ''),
  set: value => { cfg.target_groups = value.split(/[\s,]+/).map(x => x.trim()).filter(Boolean) },
})

onMounted(async () => {
  try {
    Object.assign(cfg, DEFAULTS, await props.host.getConfig() || {})
    configReady.value = true
  } catch (e) {
    props.host.toast.error('读取配置失败：' + (e.message || e))
  } finally { loading.value = false }
  try { status.value = await props.host.callApi('/status') }
  catch (e) { props.host.toast.error('读取运行状态失败：' + (e.message || e)) }
  await loadChatNames()
})

async function save() {
  if (!configReady.value || saving.value) {
    if (!configReady.value) props.host.toast.error('配置未成功读取，请重新打开配置页后再保存')
    return
  }
  saving.value = true
  saveMessage.value = ''
  saveError.value = false
  try {
    if (typeof cfg.slash_min_total !== 'number' || !Number.isFinite(cfg.slash_min_total) || cfg.slash_min_total < 0) {
      throw new Error('斜杠红包最低总额请填写大于或等于 0 的有效数字，0 表示不限制')
    }
    await props.host.saveConfig({ ...cfg })
    await loadChatNames()
    props.host.toast.success('配置已保存')
    saveMessage.value = '配置已保存'
  } catch (e) {
    saveError.value = true
    saveMessage.value = '保存失败：' + (e.message || e)
    props.host.toast.error(saveMessage.value)
  }
  finally { saving.value = false }
}
async function switchTab(value) {
  tab.value = value
  if (value === 'history') await loadHistory()
}
async function loadHistory() {
  if (historyLoading.value || clearing.value) return
  historyLoading.value = true
  try {
    const [h, s] = await Promise.all([
      props.host.callApi('/history'), props.host.callApi('/status'),
    ])
    history.value = h.items || []
    status.value = s
    await loadChatNames()
  } catch (e) { props.host.toast.error('读取记录失败：' + (e.message || e)) }
  finally { historyLoading.value = false }
}
async function clearHistory() {
  if (clearing.value || historyLoading.value) return
  clearing.value = true
  try {
    await props.host.callApi('/history/clear', { method: 'POST', body: {} })
    history.value = []
    clearConfirm.value = false
    props.host.toast.success('记录已清空')
  } catch (e) { props.host.toast.error('清空失败：' + (e.message || e)) }
  finally { clearing.value = false }
}
function timeText(ts) {
  if (!ts) return '—'
  return new Date(Number(ts) * 1000).toLocaleString()
}

async function loadChatNames() {
  try {
    const r = await props.host.callApi('/chat_names')
    chatNames.value = r.items || []
  } catch {}
}

function nameOf(id) {
  const item = chatNames.value.find(x => String(x.id) === String(id))
  return item ? item.title : String(id)
}
</script>

<template>
  <IosSettings>
  <div class="rpg" @input="saveMessage = ''" @change="saveMessage = ''">
    <header class="rpg-heading"><div><h2>自动抢红包</h2><p>设置参与范围、口令识别与抢包方式。</p></div><span class="rpg-state">{{ cfg.enabled ? '配置已开启' : '配置已关闭' }}</span></header>
    <div v-if="loading" class="muted loading">加载配置…</div>
    <template v-else>
      <p v-if="!configReady" class="tip error" role="alert">配置读取失败，已禁止保存以保护已有配置。请重新打开配置页重试。</p>
      <div class="rpg-tabs" aria-label="页面切换">
        <span class="rpg-segment" :class="{ history: tab === 'history' }" aria-hidden="true" />
        <button :class="['rpg-tab', { on: tab === 'settings' }]" :aria-pressed="tab === 'settings'" @click="switchTab('settings')">配置</button>
        <button :class="['rpg-tab', { on: tab === 'history' }]" :aria-pressed="tab === 'history'" @click="switchTab('history')">抢包记录</button>
      </div>

      <div v-show="tab === 'settings'" class="layout">
        <aside class="rpg-sidebar" aria-label="设置分组">
          <div class="side-title">设置分组</div>
          <button v-for="g in GROUPS" :key="g.key" :class="['side-item', { on: group === g.key }]" :aria-pressed="group === g.key" @click="group = g.key">{{ g.label }}<span aria-hidden="true">›</span></button>
        </aside>
        <main class="detail">
          <template v-if="group === 'main'">
            <h3>总开关</h3><section class="rpg-card">
              <label class="rpg-switch"><input v-model="cfg.enabled" type="checkbox" role="switch"><span>启用自动抢红包</span></label>
              <p class="tip">处理群内正文口令、图片财富密码和验证码口令红包，不会响应自己发出的红包。</p>
            </section>
          </template>
          <template v-else-if="group === 'scope'">
            <h3>识别范围</h3><section class="rpg-card">
              <label class="rpg-row top"><span>触发关键词</span><textarea v-model="cfg.trigger_keywords" class="inp" rows="3" /></label>
              <p class="tip indent">验证码图片说明含任一关键词才尝试参与；正文拼手气红包按固定格式自动识别。</p>
              <label class="rpg-row top"><span>发包人白名单</span><textarea v-model="cfg.target_senders" class="inp" rows="4" placeholder="一行一个：用户ID 备注；留空不限" /></label>
              <label class="rpg-row top"><span>群组白名单</span><textarea v-model="groupsText" class="inp" rows="4" placeholder="一行一个群ID；留空不限" /></label>
              <div v-if="chatNames.length" class="chat-names"><span class="chat-label">已识别：</span><span v-for="item in chatNames" :key="item.id" class="chat-name">{{ item.title }} ({{ item.id }})</span></div>
            </section>
          </template>
          <template v-else-if="group === 'recognize'">
            <h3>口令识别</h3><section class="rpg-card">
              <div class="rpg-badge ok">支持正文直接口令</div>
              <p class="tip">识别“发送下方口令领取：”后的文字；新消息和后续编辑都会检查。</p>
              <div class="rpg-badge ok">支持动态财富密码</div>
              <p class="tip">自动 OCR“财富密码见图片”的红包；图片更新后可重新识别，红包领完后停止。</p>
              <label class="rpg-switch"><input v-model="cfg.ocr_enabled" type="checkbox" role="switch"><span>启用 OCR 识别验证码</span></label>
              <div :class="['rpg-badge', status.ocr_available ? 'ok' : 'warn']">{{ status.ocr_available ? 'ddddocr 可用' : 'ddddocr 不可用，将使用复制兜底' }}</div>
              <label class="rpg-switch"><input v-model="cfg.copy_fallback" type="checkbox" role="switch"><span>启用复制兜底</span></label>
              <p class="tip">监听他人的中奖确认，支持独立发送或回复红包的口令；缓存漏记时会现场回查原消息。</p>
              <div class="grid"><label class="rpg-row"><span>最短位数</span><input v-model.number="cfg.code_min_len" class="inp sm" type="number" min="1" max="12"></label>
              <label class="rpg-row"><span>最长位数</span><input v-model.number="cfg.code_max_len" class="inp sm" type="number" min="1" max="30"></label></div>
            </section>
          </template>
          <template v-else-if="group === 'behavior'">
            <h3>参与行为</h3><section class="rpg-card">
              <label class="rpg-row"><span>参与延迟</span><input v-model.number="cfg.join_delay" class="inp sm" type="number" min="0" max="60" step="0.5"><span class="hint">秒</span></label>
              <label class="rpg-switch"><input v-model="cfg.slash_command_protection" type="checkbox" role="switch" aria-describedby="slash-protection-tip"><span>斜杠口令防误触保护</span></label>
              <p id="slash-protection-tip" class="tip">仅保护 / 开头的口令：在 / 后插入零宽空格，显示不变，但实际发送文本会变化。严格匹配原口令的红包可能拒收；会移除零宽字符的机器人仍可能识别为命令。</p>
              <label class="rpg-row"><span>斜杠红包最低总额</span><input v-model.number="cfg.slash_min_total" class="inp sm" type="number" min="0" step="any" inputmode="decimal" aria-describedby="slash-min-total-tip"></label>
              <p id="slash-min-total-tip" class="tip">只筛选 / 开头的口令，红包总额低于此值就跳过；0 表示不限制。设置大于 0 时，总额无法识别的红包也会跳过，普通口令不受影响。</p>
              <label class="rpg-row"><span>中奖关键词</span><input v-model="cfg.success_markers" class="inp"></label>
              <label class="rpg-row"><span>金额前缀</span><input v-model="cfg.transfer_prefix" class="inp sm"></label>
            </section>
          </template>
          <template v-else>
            <h3>通用</h3><section class="rpg-card">
              <label class="rpg-row"><span>监听时长</span><input v-model.number="cfg.activity_ttl_minutes" class="inp sm" type="number" min="1" max="240"><span class="hint">分钟</span></label>
              <label class="rpg-switch"><input v-model="cfg.notify_owner" type="checkbox" role="switch"><span>发送口令和中奖时通知我</span></label>
            </section>
          </template>
          <div class="savebar"><span :class="['rpg-save-result', { error: saveError }]" role="status">{{ saveMessage || '修改后请保存，已有设置不会重置。' }}</span><button class="rpg-button rpg-primary" :disabled="saving || !configReady" @click="save">{{ saving ? '保存中…' : '保存配置' }}</button></div>
        </main>
      </div>

      <div v-show="tab === 'history'" class="pane">
        <div class="summary"><div><b>{{ status.active_count || 0 }}</b><span>监听中</span></div><div><b>{{ history.length }}</b><span>中奖记录</span></div><div><b>{{ status.ocr_available ? '可用' : '不可用' }}</b><span>OCR</span></div></div>
        <div class="toolbar"><span class="muted">仅成功确认中奖后写入记录</span><span class="grow"/><button class="rpg-button" :disabled="historyLoading || clearing" @click="loadHistory">{{ historyLoading ? '刷新中…' : '刷新' }}</button><button class="rpg-button rpg-danger" :disabled="clearing || historyLoading || !history.length" @click="clearConfirm = true">清空记录</button></div>
        <div v-if="clearConfirm" class="rpg-confirm" role="alert"><span>清空后无法恢复，确定删除所有抢包记录？</span><button class="rpg-button" :disabled="clearing" @click="clearConfirm = false">保留记录</button><button class="rpg-button rpg-danger" :disabled="clearing" @click="clearHistory">{{ clearing ? '清空中…' : '确定清空' }}</button></div>
        <div class="table-wrap"><table><thead><tr><th>时间</th><th>群组</th><th>发包人</th><th>口令</th><th>方式</th><th>结果</th></tr></thead>
          <tbody><tr v-for="(item, i) in history" :key="i"><td>{{ timeText(item.ts) }}</td><td>{{ nameOf(item.group_id) }} ({{ item.group_id }})</td><td>{{ item.sender || '—' }}</td><td class="code">{{ item.code || '—' }}</td><td><span class="rpg-badge ok">{{ item.mode || '—' }}</span></td><td class="success">{{ item.ok ? '成功' : '失败' }}</td></tr>
          <tr v-if="!historyLoading && !history.length"><td colspan="6" class="empty">暂无抢包记录</td></tr><tr v-if="historyLoading"><td colspan="6" class="empty">加载中…</td></tr></tbody></table></div>
      </div>
    </template>
  </div>
  </IosSettings>
</template>

<style scoped>
/* iOS Settings / Liquid Glass, user-pinned direction, seed 972a7fca.
   Task-first grouped rows; platform tokens own color and transparency.
   Signature: the segmented selection glides while forms remain immediately usable.
   Desktop: 150px section rail beside the settings list; mobile: horizontal rail.
   FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance */
.rpg { min-width: 0; color: var(--ios-text); font-size: 14px; }
.rpg-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 4px 0 22px; }
.rpg-heading h2 { margin: 0; font-size: 22px; font-weight: 650; letter-spacing: -.025em; }
.rpg-heading p { margin: 5px 0 0; color: var(--ios-secondary); font-size: 13px; }
.rpg-state { flex-shrink: 0; color: var(--ios-secondary); font-size: 12px; }
.rpg-tabs { position: relative; isolation: isolate; display: grid; grid-template-columns: 1fr 1fr; padding: 4px; max-width: 320px; border-radius: 16px; background: var(--ios-inset); margin-bottom: 24px; }
.rpg-segment { position: absolute; inset: 4px auto 4px 4px; width: calc(50% - 4px); border-radius: 12px; background: var(--ios-control); box-shadow: 0 2px 5px rgb(0 0 0 / .08); transition: transform var(--ios-duration) var(--ios-ease); pointer-events: none; }
.rpg-segment.history { transform: translateX(100%); }
.rpg-tab { position: relative; min-height: 40px; background: none; border: 0; color: var(--ios-secondary); cursor: pointer; font-weight: 500; border-radius: 12px; }
.rpg-tab.on { color: var(--ios-text); font-weight: 650; }
.layout { display: grid; grid-template-columns: 150px minmax(0, 1fr); gap: 28px; align-items: start; min-height: 380px; }
.rpg-sidebar { padding: 0; min-width: 0; }
.side-title { margin: 0 12px 10px; font-size: 12px; color: var(--ios-secondary); }
.side-item { display: flex; width: 100%; align-items: center; justify-content: space-between; gap: 12px; min-height: 46px; padding: 10px 12px; margin-bottom: 4px; border: 0; border-radius: 12px; text-align: left; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.side-item.on { background: var(--ios-control); color: var(--ios-text); font-weight: 600; }
.side-item span { color: var(--ios-secondary); font-size: 21px; line-height: 1; }
.detail { min-width: 0; }
.detail h3 { margin: 0 0 12px 4px; font-size: 15px; font-weight: 650; }
.rpg .rpg-card { padding: 6px 20px; background: var(--ios-surface); border: 1px solid var(--ios-line); border-radius: 20px; box-shadow: none; }
.rpg .rpg-row { display: flex; align-items: center; flex-wrap: wrap; gap: 10px 16px; margin: 0; padding: 16px 0; min-height: 60px; }
.rpg-row > span:first-child { flex: 0 0 130px; color: var(--ios-text); }
.rpg .rpg-row.top { align-items: flex-start; flex-direction: column; gap: 8px; }
.rpg-row.top > span:first-child { flex: none; }
.rpg .rpg-switch { display: flex; align-items: center; flex-direction: row-reverse; justify-content: space-between; gap: 20px; min-height: 60px; margin: 0; padding: 12px 0; cursor: pointer; }
.rpg-switch span { flex: 1; }
.rpg .rpg-switch input { appearance: none; -webkit-appearance: none; display: block; flex: 0 0 50px; width: 50px; height: 30px; position: relative; margin: 0; border: 1px solid var(--border-light, #c4c8cf); border-radius: 20px; background: var(--ios-inset); cursor: pointer; transition: background-color var(--ios-fast) ease; }
.rpg .rpg-switch input::before { content: ''; position: absolute; top: 3px; left: 3px; width: 22px; height: 22px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .18); transition: transform var(--ios-duration) var(--ios-ease); }
.rpg .rpg-switch input:checked { background: var(--ios-accent); border-color: transparent; }
.rpg .rpg-switch input:checked::before { transform: translateX(20px); }
.rpg .rpg-switch input:active::before { transform: scaleX(1.08); }
.rpg .rpg-switch input:checked:active::before { transform: translateX(19px) scaleX(1.08); }
.rpg .inp { box-sizing: border-box; flex: 1; min-width: 0; width: 100%; min-height: 44px; border: 1px solid var(--ios-line); border-radius: 12px; padding: 10px 12px; background: var(--ios-inset); color: var(--ios-text); transition: border-color var(--ios-fast) ease; }
.rpg .inp.sm { flex: 0 1 130px; max-width: 150px; width: 130px; text-align: right; }
.rpg textarea.inp { resize: vertical; line-height: 1.6; }
.tip, .hint, .muted { color: var(--ios-secondary); }
.tip { margin: 0 0 16px; max-width: 72ch; font-size: 12px; line-height: 1.7; overflow-wrap: anywhere; }
.tip.error, .rpg-save-result.error { color: var(--danger, #b42338); }
.tip.indent { margin-left: 0; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.grid .rpg-row { justify-content: space-between; }
.grid .rpg-row > span:first-child { flex: 1; }
.grid .inp.sm { flex-basis: 90px; width: 90px; }
.savebar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-top: 24px; padding-top: 16px; }
.rpg-save-result { color: var(--ios-secondary); font-size: 12px; flex: 1; min-width: 150px; overflow-wrap: anywhere; }
.rpg-button { min-height: 44px; padding: 10px 18px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font-weight: 600; cursor: pointer; }
.rpg-primary { background: var(--ios-accent); color: #fff; border-color: transparent; }
.rpg-danger { color: var(--danger, #b42338); }
.rpg-button:disabled { opacity: .5; }
.rpg-button:hover:not(:disabled) { box-shadow: 0 3px 10px rgb(0 0 0 / .1); }
.rpg-badge { display: inline-flex; padding: 3px 9px; border-radius: 8px; font-size: 12px; margin: 10px 0; background: var(--ios-inset); }
.rpg-badge.ok { color: var(--ios-text); background: var(--ios-inset); }
.rpg-badge.warn { color: var(--warning, #805000); background: var(--ios-inset); }
.chat-names { display: flex; flex-wrap: wrap; gap: 6px 12px; padding-bottom: 16px; font-size: 12px; color: var(--ios-secondary); overflow-wrap: anywhere; }
.pane { padding-top: 0; }
.summary { display: flex; flex-wrap: wrap; gap: 16px 28px; border-bottom: 1px solid var(--ios-line); padding: 0 4px 18px; margin-bottom: 18px; }
.summary > div { display: flex; gap: 8px; align-items: baseline; }
.summary b { font-size: 15px; font-weight: 650; }
.summary span { color: var(--ios-secondary); font-size: 12px; }
.toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 16px; }
.grow { flex: 1; }
.table-wrap { overflow: auto; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 14px 16px; border-bottom: 1px solid var(--ios-line); text-align: left; white-space: nowrap; }
th { font-weight: 600; color: var(--ios-secondary); }
tbody tr:last-child td { border-bottom: 0; }
.code { font-family: var(--font-mono, ui-monospace, monospace); }
.success { color: var(--success, #16734e); }
.empty { text-align: center; padding: 40px 16px; color: var(--ios-secondary); }
.rpg-confirm { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-bottom: 16px; padding: 16px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-inset); }
.rpg-confirm > span { flex: 1 1 240px; }
.loading { padding: 28px 4px; color: var(--ios-secondary); }
@container (max-width: 620px) {
  .layout { grid-template-columns: 1fr; gap: 20px; min-height: 0; }
  .rpg-sidebar { display: flex; flex-wrap: wrap; gap: 4px; }
  .side-title, .side-item span { display: none; }
  .side-item { width: auto; padding: 8px 12px; min-height: 44px; margin: 0; }
  .rpg-heading { align-items: flex-start; }
  .rpg-heading h2 { font-size: 20px; }
  .rpg-state { padding-top: 4px; }
  .rpg .rpg-card { padding: 6px 16px; }
  .rpg-row > span:first-child { flex-basis: 110px; }
  .grid { grid-template-columns: 1fr; gap: 0; }
  .rpg .inp { font-size: 16px; }
  .rpg-tabs { max-width: none; margin-bottom: 16px; }
  .toolbar .muted { flex: 1 1 100%; font-size: 12px; }
}
@media (forced-colors: active) { .rpg .rpg-switch input { appearance: auto; } .rpg .rpg-switch input::before { display: none; } }
</style>
