<script setup>
// 从已发布的 2.0.11 未压缩组件恢复可维护源码，保留现有站点/榜单/延迟/流水功能。
// SSD 确认配置独立交由 SSD 助手，排行榜只监听官方成功回执。
import { ref, reactive, onMounted, computed } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'
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
  <IosSettings>
    <div class="tf">
      <header class="tf-heading">
        <div><h2>多站点转账</h2><p>按站点管理致谢与排行榜，查看官方成功回执记录。</p></div>
      </header>
      <div v-if="loading" class="tf-loading" role="status">加载配置…</div>
      <template v-else>
        <nav class="tf-tabs" :style="{ '--tf-tab-index': tab === 'rank' ? 1 : 0 }" aria-label="多站点转账页面">
          <button type="button" :class="['tf-tab', { on: tab === 'settings' }]" :aria-pressed="tab === 'settings'" @click="switchTab('settings')">配置</button>
          <button type="button" :class="['tf-tab', { on: tab === 'rank' }]" :aria-pressed="tab === 'rank'" @click="switchTab('rank')">排行榜</button>
        </nav>
        <div v-if="loadError" class="tf-load-error" role="alert">
          <p>{{ loadError }}。读取成功前不能保存，以免覆盖原设置。</p>
          <button type="button" class="tf-button" @click="loadConfig">重新读取配置</button>
        </div>
        <div v-show="tab === 'settings'" class="tf-layout">
          <aside class="tf-sidebar" aria-label="设置分组">
            <div class="tf-side-title">设置分组</div>
            <button v-for="item in GROUPS" :key="item.key" type="button" :class="['tf-side-item', { on: group === item.key }]" :aria-pressed="group === item.key" @click="group = item.key">
              {{ item.label }}<svg viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="m6 3 5 5-5 5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
            </button>
          </aside>
          <main class="tf-detail">
            <template v-if="group === 'sites'">
              <div class="tf-section-heading"><h3>站点开关</h3><p class="tf-tip">群组/转账 bot 已内置，这里按站点开关功能：启用=监听记录；群内致谢=收/发后群里回一句；打赏榜/赏赐榜=致谢里附转入/转出排行榜。</p></div>
              <div class="tf-site-list">
                <section v-for="site in SITES" :key="site.key" class="tf-site">
                  <div class="tf-site-head"><h4>{{ site.label }}</h4><span class="tf-site-bonus">{{ site.bonus }}</span><span v-if="site.note" class="tf-site-note">{{ site.note }}</span></div>
                  <div class="tf-site-controls">
                    <label v-for="option in TOGGLES" :key="option.v" :class="['tf-site-option', { on: has(site.key, option.v) }]">
                      <span>{{ option.l }}</span><input type="checkbox" role="switch" :checked="has(site.key, option.v)" :aria-label="site.label + ' · ' + option.l" :disabled="!configReady || saving" @change="toggle(site.key, option.v)" />
                    </label>
                  </div>
                </section>
              </div>
            </template>
            <template v-else-if="group === 'rank'">
              <div class="tf-section-heading"><h3>排行榜</h3></div>
              <section class="tf-group">
                <label class="tf-row"><span>输出形式</span><select v-model="cfg.rank_output" class="tf-input"><option v-for="option in RANK_OUTPUTS" :key="option.v" :value="option.v">{{ option.l }}</option></select></label>
                <p v-if="cfg.rank_output === 'rich_table'" class="tf-tip tf-row-note">仅 Telegram Premium 会员账号可使用原生富文本表格；普通账号或发送失败时，会自动回退为正常文本排行榜。</p>
                <p v-else-if="cfg.rank_output === 'image'" class="tf-tip tf-row-note">图片生成或发送失败时会自动回退为文本排行榜。</p>
                <p v-else class="tf-tip tf-row-note">文本模式兼容所有账号。</p>
                <label class="tf-row tf-row-separated"><span>排行榜人数</span><input v-model.number="cfg.rank_size" class="tf-input tf-small" type="number" min="3" max="30" /></label>
                <label class="tf-row tf-row-separated"><span>命令词</span><input v-model="cfg.rank_command" class="tf-input" /></label>
                <p class="tf-tip tf-row-note">在任意聊天发「.命令词 [站点] [in/out]」拉排行榜，如 .转账排行 hdsky in。</p>
              </section>
            </template>
            <template v-else-if="group === 'delay'">
              <div class="tf-section-heading"><h3>致谢延迟</h3></div>
              <section class="tf-group">
                <p class="tf-tip tf-group-note">记录到转账后等待若干秒再发致谢，模拟人工（0=不等）。</p>
                <div class="tf-range">
                  <label class="tf-row"><span>最小</span><div class="tf-unit"><input v-model.number="cfg.notify_delay_min" class="tf-input tf-small" type="number" min="0" max="300" /><span>秒</span></div></label>
                  <label class="tf-row"><span>最大</span><div class="tf-unit"><input v-model.number="cfg.notify_delay_max" class="tf-input tf-small" type="number" min="0" max="300" /><span>秒</span></div></label>
                </div>
              </section>
            </template>
            <template v-else-if="group === 'adv'">
              <div class="tf-section-heading"><h3>进阶</h3></div>
              <section class="tf-group">
                <p class="tf-tip tf-group-note">SSD 自动确认转账已移到「SSD 助手」，请在新插件中单独开启。本插件不再点击确认，继续依据成功回执记账和发送排行榜。</p>
                <label class="tf-switch-row tf-row-separated"><span>每笔转账推送给平台主人</span><input v-model="cfg.owner_notify" type="checkbox" role="switch" /></label>
              </section>
            </template>
            <footer class="tf-savebar">
              <p>修改后请保存，配置仅在保存后生效。</p>
              <button type="button" class="tf-button tf-primary" :disabled="saving || !configReady" @click="save">{{ saving ? '保存中…' : '保存配置' }}</button>
            </footer>
          </main>
        </div>
        <section v-show="tab === 'rank'" class="tf-pane" aria-label="排行榜与最近流水">
          <div class="tf-toolbar">
            <select v-model="lbSite" class="tf-input tf-site-select" aria-label="排行榜站点" @change="loadLeaderboard"><option v-if="!sites.length" value="">（无数据）</option><option v-for="site in sites" :key="site.name" :value="site.name">{{ site.name }}{{ site.has_data ? '' : '（空）' }}</option></select>
            <div class="tf-direction" :style="{ '--tf-direction-index': lbDir === 'out' ? 1 : 0 }" aria-label="排行榜方向">
              <button type="button" :class="['tf-direction-button', { on: lbDir === 'in' }]" :aria-pressed="lbDir === 'in'" @click="lbDir = 'in'; loadLeaderboard()">打赏榜(转入)</button>
              <button type="button" :class="['tf-direction-button', { on: lbDir === 'out' }]" :aria-pressed="lbDir === 'out'" @click="lbDir = 'out'; loadLeaderboard()">赏赐榜(转出)</button>
            </div>
            <span class="tf-grow"></span>
            <button type="button" class="tf-button" :disabled="lbLoading" @click="loadSites">刷新</button>
            <button type="button" class="tf-button tf-danger" :disabled="!lbSite || lbLoading" @click="resetSite">清空该站</button>
          </div>
          <div v-if="lbLoading" class="tf-loading" role="status">加载中…</div>
          <p v-else-if="rankError" class="tf-field-error" role="alert">{{ rankError }}</p>
          <div v-else-if="!lbRows.length" class="tf-empty">该站点暂无{{ lbDir === 'in' ? '转入' : '转出' }}数据</div>
          <div v-else class="tf-table-wrap"><table class="tf-table"><thead><tr><th>名次</th><th>用户</th><th>累计{{ bonusOf }}</th><th>笔数</th></tr></thead><tbody><tr v-for="item in lbRows" :key="item.rank"><td class="tf-rank">{{ item.rank }}</td><td>{{ item.user_name }}</td><td>{{ item.total }}</td><td class="tf-muted">{{ item.count }}</td></tr></tbody></table></div>
          <div v-if="recent.length" class="tf-history">
            <h3>最近流水<span>{{ recent.length }} 条</span></h3>
            <div class="tf-table-wrap"><table class="tf-table"><thead><tr><th>站点</th><th>方向</th><th>用户</th><th>金额</th><th>时间</th></tr></thead><tbody><tr v-for="(item, index) in recent" :key="index"><td class="tf-muted">{{ item.site }}</td><td>{{ item.direction === 'in' ? '转入' : '转出' }}</td><td>{{ item.user_name }}</td><td>{{ item.amount }}</td><td class="tf-muted tf-time">{{ fmtTime(item.ts) }}</td></tr></tbody></table></div>
          </div>
        </section>
      </template>
    </div>
  </IosSettings>
</template>

<style scoped>
/* The shared iOS Settings shell owns theme tokens and reduced-motion behavior.
   Transfer state, requests, toggles and leaderboard processing are unchanged. */
.tf { display: flex; flex-direction: column; min-width: 0; color: var(--ios-text); }
.tf-heading { padding: 4px 0 22px; }
.tf-heading h2 { margin: 0; font-size: 22px; font-weight: 650; letter-spacing: -.025em; line-height: 1.4; }
.tf-heading p { margin: 5px 0 0; max-width: 70ch; color: var(--ios-secondary); font-size: 13px; }
.tf-tabs { position: relative; isolation: isolate; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px; width: 320px; max-width: 100%; margin-bottom: 24px; padding: 4px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-inset); }
.tf-tabs::before { content: ''; position: absolute; inset: 4px auto 4px 4px; width: calc((100% - 12px) / 2); border-radius: 11px; background: var(--ios-control); box-shadow: 0 2px 5px rgb(0 0 0 / .08); transform: translateX(calc(var(--tf-tab-index) * (100% + 4px))); transition: transform var(--ios-duration) var(--ios-ease); pointer-events: none; z-index: -1; }
.tf-tab { display: inline-flex; align-items: center; justify-content: center; min-height: 42px; padding: 8px 16px; border: 0; border-radius: 11px; background: transparent; color: var(--ios-secondary); font-weight: 500; cursor: pointer; }
.tf-tab.on { color: var(--ios-text); font-weight: 650; }
.tf-layout { display: grid; grid-template-columns: 150px minmax(0, 1fr); gap: 28px; align-items: start; }
.tf-sidebar { min-width: 0; margin: 0; padding: 0; }
.tf-side-title { padding: 0 12px 10px; color: var(--ios-secondary); font-size: 12px; }
.tf-side-item { display: flex; align-items: center; justify-content: space-between; gap: 12px; width: 100%; min-height: 46px; margin-bottom: 4px; padding: 10px 12px; border: 0; border-radius: 12px; background: transparent; color: var(--ios-secondary); text-align: left; font-weight: 500; cursor: pointer; }
.tf-side-item.on { background: var(--ios-control); color: var(--ios-text); font-weight: 600; }
.tf-side-item:hover { color: var(--ios-text); }
.tf-side-item svg { flex: 0 0 14px; width: 14px; height: 14px; color: var(--ios-secondary); }
.tf-detail { min-width: 0; }
.tf-section-heading { margin: 0 4px 14px; }
.tf-section-heading h3 { margin: 0; font-size: 16px; font-weight: 650; letter-spacing: -.015em; }
.tf-section-heading p { margin-top: 6px; }
.tf-tip { margin: 0; max-width: 72ch; color: var(--ios-secondary); font-size: 12px; line-height: 1.7; overflow-wrap: anywhere; }
.tf-site-list, .tf-group { overflow: hidden; background: var(--ios-surface); border: 1px solid var(--ios-line); border-radius: 20px; }
.tf-site { padding: 18px 20px; }
.tf-site + .tf-site { border-top: 1px solid var(--ios-line); }
.tf-site-head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 10px; margin-bottom: 12px; min-width: 0; }
.tf-site-head h4 { margin: 0; font-size: 15px; font-weight: 650; overflow-wrap: anywhere; }
.tf-site-bonus { padding: 2px 7px; background: var(--ios-inset); border-radius: 7px; font-size: 12px; color: var(--ios-secondary); }
.tf-site-note { color: var(--ios-secondary); font-size: 12px; overflow-wrap: anywhere; }
.tf-site-controls { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px 16px; }
.tf-site-option { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-width: 0; min-height: 40px; color: var(--ios-secondary); font-size: 12px; cursor: pointer; }
.tf-site-option.on { color: var(--ios-text); }
.tf .tf-site-option input, .tf .tf-switch-row input { appearance: none; -webkit-appearance: none; position: relative; display: block; flex: 0 0 44px; width: 44px; height: 28px; margin: 0; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); cursor: pointer; transition: background-color var(--ios-fast) ease, border-color var(--ios-fast) ease; }
.tf .tf-site-option input::before, .tf .tf-switch-row input::before { content: ''; position: absolute; top: 2px; left: 2px; width: 22px; height: 22px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .18); transition: transform var(--ios-duration) var(--ios-ease); }
.tf .tf-site-option input:checked, .tf .tf-switch-row input:checked { border-color: transparent; background: var(--ios-accent); }
.tf .tf-site-option input:checked::before, .tf .tf-switch-row input:checked::before { transform: translateX(16px); }
.tf .tf-site-option:active input:not(:disabled)::before, .tf .tf-switch-row:active input:not(:disabled)::before { transform: scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.tf .tf-site-option:active input:checked:not(:disabled)::before, .tf .tf-switch-row:active input:checked:not(:disabled)::before { transform: translateX(16px) scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.tf-row { display: flex; align-items: center; gap: 16px; min-height: 70px; margin: 0 20px; padding: 14px 0; }
.tf-row > span:first-child { flex: 1 0 120px; color: var(--ios-text); font-weight: 500; }
.tf-row-separated { border-top: 1px solid var(--ios-line); }
.tf-row-note { margin: -4px 20px 16px; }
.tf-group-note { padding: 18px 20px 0; }
.tf-input { min-width: 0; min-height: 44px; width: min(100%, 340px); padding: 10px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-text); transition: border-color var(--ios-fast), box-shadow var(--ios-fast); }
.tf-input:focus { border-color: var(--accent, #0063dc); }
.tf-small { width: 100px; text-align: right; }
.tf-range { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.tf-range .tf-row { justify-content: space-between; gap: 12px; }
.tf-range .tf-row > span:first-child { flex: 1; }
.tf-unit { display: inline-flex; align-items: center; gap: 10px; min-width: 0; color: var(--ios-secondary); font-size: 12px; }
.tf-switch-row { display: flex; align-items: center; justify-content: space-between; gap: 20px; min-height: 70px; margin: 16px 20px 0; padding: 14px 0; cursor: pointer; }
.tf-switch-row > span { flex: 1; min-width: 0; }
.tf-savebar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-top: 24px; }
.tf-savebar p { flex: 1; min-width: 0; margin: 0; color: var(--ios-secondary); font-size: 12px; }
.tf-button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; padding: 9px 18px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font-weight: 500; cursor: pointer; }
.tf-button:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.tf-button.tf-primary { min-width: 132px; border-color: transparent; background: var(--ios-accent); color: #fff; font-weight: 600; }
.tf-button.tf-primary:hover:not(:disabled) { filter: brightness(1.08); }
.tf-button.tf-danger { color: var(--danger, #bd2733); }
.tf button:disabled, .tf input:disabled { opacity: .5; cursor: not-allowed; }
.tf-pane { display: flex; flex-direction: column; gap: 18px; min-width: 0; }
.tf-toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
.tf-site-select { flex: 0 1 160px; width: 160px; }
.tf-grow { flex: 1; }
.tf-direction { position: relative; isolation: isolate; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px; padding: 4px; max-width: 100%; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-inset); }
.tf-direction::before { content: ''; position: absolute; inset: 4px auto 4px 4px; width: calc((100% - 12px) / 2); border-radius: 9px; background: var(--ios-control); box-shadow: 0 2px 5px rgb(0 0 0 / .08); transform: translateX(calc(var(--tf-direction-index) * (100% + 4px))); transition: transform var(--ios-duration) var(--ios-ease); pointer-events: none; z-index: -1; }
.tf-direction-button { min-height: 36px; padding: 6px 12px; border: 0; border-radius: 9px; background: transparent; color: var(--ios-secondary); font-size: 12px; white-space: nowrap; cursor: pointer; }
.tf-direction-button.on { color: var(--ios-text); font-weight: 600; }
.tf-table-wrap { width: 100%; max-width: 100%; overflow: auto; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); scrollbar-width: thin; scrollbar-color: var(--ios-line) transparent; }
.tf-table { width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
.tf-table th, .tf-table td { text-align: left; padding: 14px 16px; border-bottom: 1px solid var(--ios-line); overflow-wrap: anywhere; }
.tf-table th { color: var(--ios-secondary); font-weight: 600; white-space: nowrap; }
.tf-table td { color: var(--ios-text); }
.tf-table tbody tr:last-child td { border-bottom: 0; }
.tf-table .tf-muted { color: var(--ios-secondary); }
.tf-rank { width: 60px; font-weight: 600; }
.tf-time { white-space: nowrap; }
.tf-history { min-width: 0; margin-top: 10px; }
.tf-history h3 { display: flex; align-items: baseline; gap: 10px; margin: 0 4px 12px; font-size: 15px; font-weight: 650; }
.tf-history h3 span { color: var(--ios-secondary); font-size: 12px; font-weight: 400; }
.tf-empty { padding: 44px 20px; text-align: center; background: var(--ios-surface); border: 1px solid var(--ios-line); border-radius: 20px; color: var(--ios-secondary); font-size: 13px; }
.tf-muted, .tf-loading { color: var(--ios-secondary); font-size: 12px; }
.tf-loading { padding: 28px 4px; }
.tf-field-error { margin: 0; padding: 16px 20px; background: var(--ios-surface); border: 1px solid var(--ios-line); border-radius: 16px; color: var(--danger, #bd2733); font-size: 12px; overflow-wrap: anywhere; }
.tf-load-error { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-bottom: 20px; padding: 16px 20px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); color: var(--danger, #bd2733); font-size: 12px; }
.tf-load-error p { flex: 1 1 240px; margin: 0; overflow-wrap: anywhere; }
:global(html[data-theme='transparent'] .tf-site-list),
:global(html[data-theme='transparent'] .tf-group),
:global(html[data-theme='transparent'] .tf-table-wrap),
:global(html[data-theme='transparent'] .tf-empty),
:global(html[data-theme='transparent'] .tf-field-error),
:global(html[data-theme='transparent'] .tf-load-error) { backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); -webkit-backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); }
@container (max-width: 680px) {
  .tf-layout { grid-template-columns: 1fr; gap: 20px; }
  .tf-sidebar { display: flex; flex-wrap: wrap; gap: 4px; }
  .tf-side-title, .tf-side-item svg { display: none; }
  .tf-side-item { width: auto; min-height: 44px; margin: 0; padding: 8px 12px; }
  .tf-tabs { margin-bottom: 20px; }
}
@container (max-width: 520px) {
  .tf-heading h2 { font-size: 20px; }
  .tf-heading p { max-width: 42ch; }
  .tf-tabs { width: 100%; }
  .tf-site { padding: 16px; }
  .tf-site-controls { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px 24px; }
  .tf-site-head { gap: 5px 8px; }
  .tf-site-note { flex: 1 1 100%; }
  .tf-row { flex-wrap: wrap; gap: 8px; margin-inline: 16px; padding-block: 14px; }
  .tf-row > span:first-child { flex: 1 1 100%; }
  .tf .tf-input { font-size: 16px; }
  .tf-row > .tf-input { width: 100%; }
  .tf-row > .tf-small { width: 100px; }
  .tf-row-note { margin-inline: 16px; }
  .tf-group-note { padding-inline: 16px; }
  .tf-range { grid-template-columns: 1fr; }
  .tf-range .tf-row { flex-wrap: nowrap; }
  .tf-range .tf-row > span:first-child { flex: 1; }
  .tf-range .tf-row + .tf-row { border-top: 1px solid var(--ios-line); }
  .tf-switch-row { margin-inline: 16px; }
  .tf-savebar p { flex: 1 1 100%; }
  .tf-savebar .tf-primary { width: 100%; }
  .tf-toolbar { gap: 10px; }
  .tf-site-select { flex: 1 1 100%; width: 100%; }
  .tf-direction { flex: 1 1 auto; }
  .tf-grow { display: none; }
  .tf-toolbar > .tf-button { flex: 1; }
  .tf-table th, .tf-table td { padding: 12px; }
}
@container (max-width: 340px) {
  .tf-site-controls { grid-template-columns: 1fr; }
  .tf-site-option { min-height: 44px; font-size: 13px; }
  .tf-direction { flex-basis: 100%; }
}
@media (forced-colors: active) {
  .tf .tf-site-option input, .tf .tf-switch-row input { appearance: auto; -webkit-appearance: auto; }
  .tf .tf-site-option input::before, .tf .tf-switch-row input::before { display: none; }
  .tf-tabs::before, .tf-direction::before { border: 2px solid Highlight; }
}
</style>
