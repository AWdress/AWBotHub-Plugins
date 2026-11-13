<script setup>
// 从已发布的 2.0.11 未压缩组件恢复可维护源码，保留现有站点/榜单/延迟/流水功能。
// SSD 确认配置独立交由 SSD 助手，排行榜只监听官方成功回执。
import { ref, reactive, onMounted, computed } from 'vue'
const props = defineProps({ pluginId: { type: String, required: true }, host: { type: Object, required: true } })
const SITES = [
  { key: 'site_audiences', label: 'Audiences', bonus: '爆米花' },
  { key: 'site_hddolby', label: 'HDDolby', bonus: '鲸币' },
  { key: 'site_azusa', label: 'Azusa', bonus: '魔力值' },
  { key: 'site_zm', label: 'ZmPT', bonus: '电力', note: '致谢/榜单自动延后约11秒发出' },
  { key: 'site_springsunday', label: 'SpringSunday', bonus: '茉莉', note: '含两个群' },
  { key: 'site_hdsky', label: 'HDSky', bonus: '银元' },
  { key: 'site_hhanclub', label: 'HHanClub', bonus: '憨豆', note: '仅记录官方机器人确认成功的赠送' },
  { key: 'site_mocktest', label: 'MockTest', bonus: '测试', note: '默认关' },
]
const TOGGLES = [{ v: 'on', l: '启用' }, { v: 'notify', l: '群内致谢' }, { v: 'lb_in', l: '打赏榜' }, { v: 'lb_out', l: '赏赐榜' }]
const RANK_OUTPUTS = [{ v: 'image', l: '图片（默认）' }, { v: 'rich_table', l: '富文本表格（Premium）' }, { v: 'text', l: '文本' }]
const DEFAULTS = {
  site_audiences: ['on', 'notify', 'lb_in', 'lb_out'], site_hddolby: ['on', 'notify', 'lb_in', 'lb_out'],
  site_azusa: ['on', 'notify', 'lb_in', 'lb_out'], site_zm: ['on', 'notify', 'lb_in', 'lb_out'],
  site_springsunday: ['on', 'notify', 'lb_in', 'lb_out'], site_hdsky: ['on', 'notify', 'lb_in', 'lb_out'],
  site_hhanclub: ['on', 'notify', 'lb_in', 'lb_out'], site_mocktest: [],
  rank_output: 'image', rank_size: 10, rank_command: '转账排行', notify_delay_min: 0, notify_delay_max: 0, owner_notify: false,
}
const GROUPS = [{ key: 'sites', label: '站点' }, { key: 'rank', label: '排行榜' }, { key: 'delay', label: '致谢延迟' }, { key: 'adv', label: '进阶' }]
const tab = ref('settings')
const group = ref('sites')
const loading = ref(true)
const configReady = ref(false)
const loadError = ref('')
const saving = ref(false)
const cfg = reactive({ ...DEFAULTS })
const sites = ref([])
const lbSite = ref('')
const lbDir = ref('in')
const lbRows = ref([])
const lbLoading = ref(false)
const recent = ref([])
const rankError = ref('')
let rankRequest = 0
const bonusOf = computed(() => sites.value.find(item => item.name === lbSite.value)?.bonus || '')
function errorText(error) { return String(error?.message || error || '未知错误') }
async function loadConfig() {
  if (saving.value) return
  loading.value = true
  configReady.value = false
  loadError.value = ''
  try {
    const saved = await props.host.getConfig()
    if (saved != null && (typeof saved !== 'object' || Array.isArray(saved))) throw new Error('配置格式不正确')
    Object.assign(cfg, DEFAULTS, saved || {})
    // 不再把已迁走的自动确认字段写回排行榜配置。
    delete cfg['ssd_click_mode']
    if (!RANK_OUTPUTS.some(item => item.v === cfg.rank_output)) cfg.rank_output = 'text'
    for (const site of SITES) if (!Array.isArray(cfg[site.key])) cfg[site.key] = []
    configReady.value = true
  } catch (error) {
    loadError.value = '读取配置失败：' + errorText(error)
    props.host.toast.error(loadError.value)
  } finally { loading.value = false }
}
onMounted(loadConfig)
function has(key, value) { return (cfg[key] || []).includes(value) }
function toggle(key, value) {
  const values = (cfg[key] || []).slice()
  const index = values.indexOf(value)
  if (index >= 0) values.splice(index, 1)
  else values.push(value)
  cfg[key] = values
}
async function save() {
  if (!configReady.value || saving.value) return
  saving.value = true
  try { await props.host.saveConfig({ ...cfg }); props.host.toast.success('配置已保存') }
  catch (error) { props.host.toast.error('保存失败：' + errorText(error)) }
  finally { saving.value = false }
}
async function loadSites() {
  try {
    const result = await props.host.callApi('/sites')
    sites.value = Array.isArray(result?.sites) ? result.sites : []
    if (!lbSite.value && sites.value.length) lbSite.value = (sites.value.find(item => item.has_data) || sites.value[0]).name
    await Promise.all([loadLeaderboard(), loadRecent()])
  } catch (error) { rankError.value = '读取站点失败：' + errorText(error); props.host.toast.error(rankError.value) }
}
async function loadLeaderboard() {
  const request = ++rankRequest
  if (!lbSite.value) { lbRows.value = []; return }
  lbLoading.value = true
  rankError.value = ''
  try {
    const result = await props.host.callApi(`/leaderboard?site=${encodeURIComponent(lbSite.value)}&dir=${lbDir.value}&limit=${cfg.rank_size || 10}`)
    if (request === rankRequest) lbRows.value = Array.isArray(result?.items) ? result.items : []
  } catch (error) {
    if (request === rankRequest) { rankError.value = '读取排行榜失败：' + errorText(error); props.host.toast.error(rankError.value) }
  } finally { if (request === rankRequest) lbLoading.value = false }
}
async function loadRecent() {
  try { const result = await props.host.callApi('/recent'); recent.value = Array.isArray(result?.items) ? result.items : [] }
  catch { /* 流水拉取失败不妨碍查看排行榜。 */ }
}
async function resetSite() {
  if (!lbSite.value || !confirm(`清空站点「${lbSite.value}」的全部转账记录与排行榜？此操作不可恢复。`)) return
  try {
    await props.host.callApi('/reset', { method: 'POST', body: { site: lbSite.value } })
    lbRows.value = []
    props.host.toast.success('已清空')
    await loadSites()
  } catch (error) { props.host.toast.error('清空失败：' + errorText(error)) }
}
function fmtTime(value) { return String(value || '').replace('T', ' ').slice(0, 16) }
function switchTab(value) { tab.value = value; if (value === 'rank' && !sites.value.length) loadSites() }
</script>

<template>
  <div class="tf">
    <div v-if="loading" class="muted" role="status">加载配置…</div>
    <template v-else>
      <div class="tabs" aria-label="多站点转账页面">
        <button type="button" :class="['tab', { on: tab === 'settings' }]" :aria-pressed="tab === 'settings'" @click="switchTab('settings')">配置</button>
        <button type="button" :class="['tab', { on: tab === 'rank' }]" :aria-pressed="tab === 'rank'" @click="switchTab('rank')">排行榜</button>
      </div>
      <div v-if="loadError" class="load-error" role="alert"><p>{{ loadError }}。读取成功前不能保存，以免覆盖原设置。</p><button type="button" class="btn" @click="loadConfig">重新读取配置</button></div>
      <div v-show="tab === 'settings'" class="layout">
        <aside class="sidebar" aria-label="设置分组"><div class="side-title">设置分组</div><button v-for="item in GROUPS" :key="item.key" type="button" :class="['side-item', { on: group === item.key }]" :aria-pressed="group === item.key" @click="group = item.key">{{ item.label }}</button></aside>
        <div class="detail">
          <template v-if="group === 'sites'">
            <h3 class="det-title">站点开关</h3><p class="tip">群组/转账 bot 已内置，这里按站点开关功能：启用=监听记录；群内致谢=收/发后群里回一句；打赏榜/赏赐榜=致谢里附转入/转出排行榜。</p>
            <section v-for="site in SITES" :key="site.key" class="card site"><div class="site-h"><span class="site-name">{{ site.label }}</span><span class="site-bonus">{{ site.bonus }}</span><span v-if="site.note" class="site-note">{{ site.note }}</span></div><div class="chips"><label v-for="option in TOGGLES" :key="option.v" :class="['chip', { on: has(site.key, option.v) }]"><input type="checkbox" :checked="has(site.key, option.v)" :disabled="!configReady || saving" @change="toggle(site.key, option.v)" />{{ option.l }}</label></div></section>
          </template>
          <template v-else-if="group === 'rank'">
            <h3 class="det-title">排行榜</h3><section class="card">
              <label class="row"><span>输出形式</span><select v-model="cfg.rank_output" class="inp"><option v-for="option in RANK_OUTPUTS" :key="option.v" :value="option.v">{{ option.l }}</option></select></label>
              <p v-if="cfg.rank_output === 'rich_table'" class="tip">仅 Telegram Premium 会员账号可使用原生富文本表格；普通账号或发送失败时，会自动回退为正常文本排行榜。</p><p v-else-if="cfg.rank_output === 'image'" class="tip">图片生成或发送失败时会自动回退为文本排行榜。</p><p v-else class="tip">文本模式兼容所有账号。</p>
              <label class="row"><span>排行榜人数</span><input v-model.number="cfg.rank_size" class="inp sm" type="number" min="3" max="30" /></label>
              <label class="row"><span>命令词</span><input v-model="cfg.rank_command" class="inp" /></label><p class="tip">在任意聊天发「.命令词 [站点] [in/out]」拉排行榜，如 .转账排行 hdsky in。</p>
            </section>
          </template>
          <template v-else-if="group === 'delay'">
            <h3 class="det-title">致谢延迟</h3><section class="card"><p class="tip">记录到转账后等待若干秒再发致谢，模拟人工（0=不等）。</p><div class="grid"><label class="row"><span>最小</span><input v-model.number="cfg.notify_delay_min" class="inp sm" type="number" min="0" max="300" /><span class="hint">秒</span></label><label class="row"><span>最大</span><input v-model.number="cfg.notify_delay_max" class="inp sm" type="number" min="0" max="300" /><span class="hint">秒</span></label></div></section>
          </template>
          <template v-else-if="group === 'adv'">
            <h3 class="det-title">进阶</h3><section class="card"><p class="tip">SSD 自动确认转账已移到「SSD 助手」，请在新插件中单独开启。本插件不再点击确认，继续依据成功回执记账和发送排行榜。</p><label class="row switch"><input v-model="cfg.owner_notify" type="checkbox" /><span>每笔转账推送给平台主人</span></label></section>
          </template>
          <div class="savebar"><button type="button" class="btn primary lg" :disabled="saving || !configReady" @click="save">{{ saving ? '保存中…' : '保存配置' }}</button></div>
        </div>
      </div>
      <div v-show="tab === 'rank'" class="pane">
        <div class="toolbar"><select v-model="lbSite" class="inp sm2" aria-label="排行榜站点" @change="loadLeaderboard"><option v-if="!sites.length" value="">（无数据）</option><option v-for="site in sites" :key="site.name" :value="site.name">{{ site.name }}{{ site.has_data ? '' : '（空）' }}</option></select><div class="seg"><button type="button" :class="['segbtn', { on: lbDir === 'in' }]" :aria-pressed="lbDir === 'in'" @click="lbDir = 'in'; loadLeaderboard()">打赏榜(转入)</button><button type="button" :class="['segbtn', { on: lbDir === 'out' }]" :aria-pressed="lbDir === 'out'" @click="lbDir = 'out'; loadLeaderboard()">赏赐榜(转出)</button></div><span class="grow"></span><button type="button" class="btn" :disabled="lbLoading" @click="loadSites">刷新</button><button type="button" class="btn danger" :disabled="!lbSite || lbLoading" @click="resetSite">清空该站</button></div>
        <div v-if="lbLoading" class="muted" role="status">加载中…</div><p v-else-if="rankError" class="field-error" role="alert">{{ rankError }}</p><div v-else-if="!lbRows.length" class="empty">该站点暂无{{ lbDir === 'in' ? '转入' : '转出' }}数据</div>
        <div v-else class="table-wrap"><table class="tbl"><thead><tr><th>名次</th><th>用户</th><th>累计{{ bonusOf }}</th><th>笔数</th></tr></thead><tbody><tr v-for="item in lbRows" :key="item.rank"><td class="rank">{{ item.rank }}</td><td>{{ item.user_name }}</td><td>{{ item.total }}</td><td class="muted">{{ item.count }}</td></tr></tbody></table></div>
        <div v-if="recent.length" class="hist"><div class="hist-h">最近流水（{{ recent.length }} 条）</div><div class="table-wrap"><table class="tbl"><thead><tr><th>站点</th><th>方向</th><th>用户</th><th>金额</th><th>时间</th></tr></thead><tbody><tr v-for="(item, index) in recent" :key="index"><td class="muted">{{ item.site }}</td><td>{{ item.direction === 'in' ? '转入' : '转出' }}</td><td>{{ item.user_name }}</td><td>{{ item.amount }}</td><td class="muted">{{ fmtTime(item.ts) }}</td></tr></tbody></table></div></div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.tf { display: flex; flex-direction: column; gap: 14px; container-type: inline-size; color: var(--text-primary, #e8ebf0); }
.tf *, .tf *::before, .tf *::after { box-sizing: border-box; }
.tf ::selection { color: var(--text-primary, #e8ebf0); background: var(--accent-dim, #1e3a5f); }
.tabs { display: flex; gap: 6px; border-bottom: 1px solid var(--border-light, #2a2e3a); }
.tab { padding: 8px 16px; background: none; border: none; cursor: pointer; font-size: 13px; color: var(--text-secondary, #b9c0cc); border-bottom: 2px solid transparent; }
.tab.on { color: var(--accent, #6ea8fe); border-bottom-color: var(--accent, #6ea8fe); }
.layout { display: flex; gap: 16px; align-items: flex-start; }
.sidebar { flex: 0 0 130px; display: flex; flex-direction: column; gap: 4px; padding: 10px; border-radius: 10px; background: var(--bg-elevated, #1a1d27); border: 1px solid var(--border-light, #2a2e3a); }
.side-title { font-size: 11px; color: var(--text-muted, #a3acbb); padding: 4px 8px 6px; }
.side-item { display: flex; align-items: center; gap: 8px; padding: 9px 10px; border-radius: 8px; border: none; cursor: pointer; text-align: left; background: none; color: var(--text-secondary, #b9c0cc); font-size: 13px; }
.side-item:hover { background: var(--bg-card, #12141c); }
.side-item.on { background: var(--accent-dim, #1e3a5f); color: var(--accent, #6ea8fe); }
.detail { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 14px; }
.det-title { margin: 0; font-size: 15px; font-weight: 600; color: var(--text-primary, #e8ebf0); }
.pane { display: flex; flex-direction: column; gap: 14px; }
.card { display: flex; flex-direction: column; gap: 10px; padding: 16px; border-radius: 10px; background: var(--bg-elevated, #1a1d27); border: 1px solid var(--border-light, #2a2e3a); }
.card.site { gap: 8px; }
.site-h { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px; }
.site-name { font-size: 14px; font-weight: 600; color: var(--text-primary, #e8ebf0); }
.site-bonus { font-size: 12px; color: var(--accent, #6ea8fe); }
.site-note { font-size: 11px; color: var(--text-muted, #a3acbb); }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(220px, 100%), 1fr)); gap: 10px 20px; }
.row { display: flex; align-items: center; gap: 10px; }
.row > span:first-child { min-width: 108px; font-size: 13px; color: var(--text-secondary, #b9c0cc); }
.row.switch span { min-width: 0; }
input[type='checkbox'] { accent-color: var(--accent, #6ea8fe); }
.hint { min-width: 0 !important; font-size: 12px; color: var(--text-muted, #a3acbb); white-space: nowrap; }
.tip { margin: 0; font-size: 12px; color: var(--text-muted, #a3acbb); line-height: 1.6; overflow-wrap: anywhere; }
.inp { flex: 1; min-width: 0; width: 100%; padding: 8px 10px; border-radius: 6px; font-size: 13px; background: var(--bg-card, #12141c); color: var(--text-primary, #e8ebf0); border: 1px solid var(--border-light, #2a2e3a); caret-color: var(--accent, #6ea8fe); }
.inp.sm { flex: 0 0 auto; width: 90px; }
.inp.sm2 { flex: 0 0 auto; width: 150px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; color: var(--text-secondary, #b9c0cc); cursor: pointer; padding: 4px 10px; border-radius: 6px; background: var(--bg-card, #12141c); border: 1px solid var(--border-light, #2a2e3a); }
.chip.on { border-color: var(--accent, #6ea8fe); color: var(--accent, #6ea8fe); background: var(--accent-dim, #1e3a5f); }
.btn { padding: 7px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; background: var(--bg-card, #12141c); color: var(--text-secondary, #b9c0cc); border: 1px solid var(--border-light, #2a2e3a); }
.btn:hover:not(:disabled) { border-color: var(--accent, #6ea8fe); color: var(--accent, #6ea8fe); }
.btn.primary { background: var(--accent-dim, #1e3a5f); border-color: var(--accent, #6ea8fe); color: var(--accent, #6ea8fe); }
.btn.danger:hover:not(:disabled) { border-color: var(--danger, #ff8585); color: var(--danger, #ff8585); }
.btn.lg { padding: 9px 22px; }
button:disabled, input:disabled { opacity: .5; cursor: not-allowed; }
button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--accent, #6ea8fe); outline-offset: 3px; }
.savebar { position: sticky; bottom: 0; display: flex; justify-content: flex-end; padding-top: 4px; }
.toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.grow { flex: 1; }
.seg { display: inline-flex; border: 1px solid var(--border-light, #2a2e3a); border-radius: 6px; overflow: hidden; }
.segbtn { padding: 6px 12px; background: var(--bg-card, #12141c); border: none; cursor: pointer; font-size: 12px; color: var(--text-secondary, #b9c0cc); }
.segbtn.on { background: var(--accent-dim, #1e3a5f); color: var(--accent, #6ea8fe); }
.table-wrap { width: 100%; max-width: 100%; overflow-x: auto; scrollbar-color: var(--border-light, #2a2e3a) var(--bg-card, #12141c); }
.tbl { width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
.tbl th, .tbl td { text-align: left; padding: 7px 8px; border-bottom: 1px solid var(--border-light, #2a2e3a); overflow-wrap: anywhere; }
.tbl th { color: var(--text-muted, #a3acbb); font-weight: 500; font-size: 12px; }
.tbl td { color: var(--text-primary, #e8ebf0); }
.rank { width: 44px; }
.empty { text-align: center; padding: 40px 0; font-size: 14px; color: var(--text-secondary, #b9c0cc); }
.muted { font-size: 12px; color: var(--text-muted, #a3acbb); }
.hist { display: flex; flex-direction: column; gap: 8px; margin-top: 6px; }
.hist-h { font-size: 13px; font-weight: 600; color: var(--accent, #6ea8fe); }
.field-error { margin: 0; color: var(--danger, #ff8585); font-size: 12px; overflow-wrap: anywhere; }
.load-error { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; color: var(--danger, #ff8585); font-size: 12px; }
.load-error p { flex: 1 1 240px; margin: 0; }
@container (max-width: 640px) { .layout { flex-direction: column; } .sidebar { flex-basis: auto; width: 100%; flex-direction: row; flex-wrap: wrap; align-items: center; gap: 6px; } .side-title { display: none; } .detail { width: 100%; } }
@container (max-width: 380px) { .row:not(.switch) { flex-wrap: wrap; } .row:not(.switch) > span:first-child { min-width: 0; flex: 1 1 100%; } }
</style>
