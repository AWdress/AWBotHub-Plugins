<template>
  <IosSettings>
  <div class="movie-monitor-config">
    <div class="tabs" :style="{ '--movie-tab-index': ['settings','status','logs'].indexOf(tab) }" aria-label="影视监控页面">
      <button :class="{ active: tab === 'settings' }" :aria-pressed="tab === 'settings'" @click="tab = 'settings'">功能设置</button>
      <button :class="{ active: tab === 'status' }" :aria-pressed="tab === 'status'" @click="tab = 'status'">运行状态</button>
      <button :class="{ active: tab === 'logs' }" :aria-pressed="tab === 'logs'" @click="tab = 'logs'">处理记录</button>
    </div>

    <div class="tab-content">
      <div v-if="tab === 'settings'" class="settings">
        <div class="section">
          <h3>监控范围</h3>
          <label class="row"><span>监控频道/群组</span><input v-model="cfg.monitor_ids" class="inp" placeholder="留空=监控所有会话，多个 ID 用逗号分隔" /></label>
          <div v-if="chatNames.length" class="chat-names"><span class="chat-label">已识别：</span><span v-for="item in chatNames" :key="item.id" class="chat-name">{{ item.title }} ({{ item.id }})</span></div>
          <div class="fld">
            <span class="lbl">转存类型</span>
            <div class="chips">
              <label class="chip"><input type="checkbox" :checked="mediaTypes.includes('movie')" @change="toggleMedia('movie')" />电影</label>
              <label class="chip"><input type="checkbox" :checked="mediaTypes.includes('tv')" @change="toggleMedia('tv')" />电视剧</label>
            </div>
          </div>
          <label class="row switch"><input v-model="cfg.only_complete_series" type="checkbox" role="switch" /><span>剧集仅转存完结</span></label>
        </div>

        <div class="section">
          <h3>TMDB 配置</h3>
          <label class="row"><span>API Key</span><div class="secret-field"><input v-model="cfg.tmdb_api_key" :type="secretVisible.tmdb_api_key ? 'text' : 'password'" class="inp" placeholder="必填" /><button type="button" aria-label="显示或隐藏 TMDB API Key" @click="secretVisible.tmdb_api_key = !secretVisible.tmdb_api_key"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div></label>
          <label class="row"><span>语言</span><input v-model="cfg.tmdb_language" class="inp" placeholder="zh-CN" /></label>
        </div>

        <div class="section">
          <h3>Emby 配置</h3>
          <label class="row"><span>地址</span><input v-model="cfg.emby_url" class="inp" placeholder="http://emby.local:8096" /></label>
          <label class="row"><span>API Key</span><div class="secret-field"><input v-model="cfg.emby_api_key" :type="secretVisible.emby_api_key ? 'text' : 'password'" class="inp" /><button type="button" aria-label="显示或隐藏 Emby API Key" @click="secretVisible.emby_api_key = !secretVisible.emby_api_key"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div></label>
          <label class="row switch"><input v-model="cfg.skip_emby_check" type="checkbox" role="switch" /><span>跳过 Emby 查重（直接转发所有链接）</span></label>
        </div>

        <div class="section">
          <h3>转发设置</h3>
          <label class="row"><span>CMS Bot 用户名</span><input v-model="cfg.cms_bot_username" class="inp" placeholder="如 @cmsbot" /></label>
          <label class="row"><span>转发标签</span><input v-model="cfg.forward_label" class="inp" placeholder="115 网盘" /></label>
          <label class="row switch"><input v-model="cfg.forward_to_saved" type="checkbox" role="switch" /><span>转发到 Saved Messages（自己的收藏）</span></label>
        </div>

        <div class="section">
          <h3>115 网盘配置</h3>
          <label class="row"><span>Cookie</span><div class="secret-field"><input v-model="cfg.pan115_cookie" :type="secretVisible.pan115_cookie ? 'text' : 'password'" class="inp" placeholder="可选，用于获取文件名" /><button type="button" aria-label="显示或隐藏 115 Cookie" @click="secretVisible.pan115_cookie = !secretVisible.pan115_cookie"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div></label>
        </div>

        <button @click="save" class="btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存配置' }}</button>
      </div>

      <div v-else-if="tab === 'status'" class="status">
        <div class="card">
          <h3>服务状态</h3>
          <div class="kv"><span>TMDB API</span><b :class="status.tmdb_ok ? 'ok' : 'err'">{{ status.tmdb_status || '未测试' }}</b></div>
          <div class="kv"><span>Emby 连接</span><b :class="status.emby_ok ? 'ok' : 'err'">{{ status.emby_status || '未测试' }}</b></div>
          <div class="kv"><span>Emby 库容量</span><b>{{ status.emby_items || 0 }} 项</b></div>
        </div>
        <button @click="testServices" class="btn" :disabled="testing">{{ testing ? '测试中...' : '测试连接' }}</button>
        <p v-if="testResult" class="test-result" :class="testResult.ok ? 'ok' : 'err'">{{ testResult.message }}</p>
      </div>

      <div v-else class="logs">
        <div class="toolbar">
          <button @click="loadLogs" class="btn-sm">刷新</button>
          <span class="muted">最近 {{ logs.length }} 条</span>
        </div>
        <div class="movie-table-wrap" tabindex="0" role="region" aria-label="处理记录列表"><table class="tbl">
          <thead><tr><th>时间</th><th>频道/群组</th><th>标题</th><th>TMDB ID</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="(log, i) in logs" :key="i">
              <td class="muted">{{ log.time }}</td>
              <td>{{ log.chat_title || log.chat_id || '-' }}</td>
              <td>{{ log.title }}</td>
              <td><span class="tmdb-id">{{ log.tmdb_id || '-' }}</span></td>
              <td><span :class="'action-' + log.action">{{ log.action }}</span></td>
            </tr>
            <tr v-if="!logs.length"><td colspan="5" class="empty">暂无处理记录</td></tr>
          </tbody>
        </table></div>
      </div>
    </div>
  </div>
</IosSettings>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

const props = defineProps({ pluginId: { type: String, required: true }, host: { type: Object, required: true } })
const cfg = ref({
  monitor_ids: '', media_types: ['movie', 'tv'], only_complete_series: false,
  tmdb_api_key: '', tmdb_language: 'zh-CN',
  emby_url: '', emby_api_key: '', skip_emby_check: false,
  cms_bot_username: '', forward_label: '115 网盘', forward_to_saved: false,
  pan115_cookie: '',
})
const tab = ref('settings')
const saving = ref(false)
const secretVisible = ref({ tmdb_api_key: false, emby_api_key: false, pan115_cookie: false })
const status = ref({})
const testing = ref(false)
const testResult = ref(null)
const logs = ref([])
const chatNames = ref([])

const mediaTypes = computed({
  get: () => Array.isArray(cfg.value.media_types) ? cfg.value.media_types : [],
  set: (v) => { cfg.value.media_types = v },
})

function toggleMedia(type) {
  const arr = mediaTypes.value
  const i = arr.indexOf(type)
  if (i >= 0) arr.splice(i, 1); else arr.push(type)
}

onMounted(async () => {
  try { const saved = await props.host.getConfig() || {}; for (const field of Object.keys(secretVisible.value)) { if (saved[field] === '********') saved[field] = await props.host.revealSecret(field) } Object.assign(cfg.value, saved) }
  catch (e) { props.host.toast.error('读取配置失败：' + (e.message || e)) }
  await Promise.all([loadStatus(), loadLogs(), loadChatNames()])
})

async function save() {
  saving.value = true
  try {
    // 保留旧版运行开关的兼容值；插件整体启停由平台卡片管理。
    await props.host.saveConfig({ ...cfg.value, shareswitch: true })
    await loadChatNames()
    props.host.toast.success('配置已保存')
  } catch (e) {
    props.host.toast.error('保存失败：' + (e.message || e))
  } finally {
    saving.value = false
  }
}

async function loadChatNames() {
  try {
    const r = await props.host.callApi('/chat_names')
    chatNames.value = r.items || []
  } catch {}
}

async function loadStatus() {
  try {
    const r = await props.host.callApi('/status')
    status.value = r
  } catch {}
}

async function testServices() {
  testing.value = true
  testResult.value = null
  try {
    const r = await props.host.callApi('/test', { method: 'POST' })
    testResult.value = r
    loadStatus()
  } catch (e) {
    testResult.value = { ok: false, message: '测试失败：' + e.message }
  } finally {
    testing.value = false
  }
}

async function loadLogs() {
  try {
    const r = await props.host.callApi('/logs')
    logs.value = r.logs || []
  } catch {}
}
</script>

<style scoped>
/* User-pinned iOS grouped settings; platform tokens own dark and glass materials.
   THESIS: choose the monitored media and its service connections, then inspect results.
   OWN-WORLD: sliding segments, grouped service rows, rounded native controls.
   STORY: configure sources and destinations, save, then test or read processing history.
   FIRST VIEWPORT: three segments above the monitor scope; other services follow in groups.
   FORM: the user's established iOS Settings direction; no new visual-world selection.
   FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance */
.movie-monitor-config { display: flex; flex-direction: column; gap: 24px; min-width: 0; color: var(--ios-text); }
.tabs { position: relative; isolation: isolate; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; padding: 4px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-inset); }
.tabs::before { content: ''; position: absolute; inset: 4px auto 4px 4px; width: calc((100% - 16px) / 3); border-radius: 11px; background: var(--ios-control); box-shadow: 0 2px 5px rgb(0 0 0 / .08); transform: translateX(calc(var(--movie-tab-index) * (100% + 4px))); transition: transform var(--ios-duration) var(--ios-ease); z-index: -1; }
.tabs button { min-width: 0; min-height: 44px; padding: 9px 12px; border: 0; border-radius: 11px; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.tabs button.active { color: var(--ios-text); font-weight: 650; }
.tab-content { min-width: 0; }
.settings { display: flex; flex-direction: column; gap: 20px; }
.section, .card { min-width: 0; padding: 4px 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.section h3, .card h3 { margin: 0; padding: 14px 0 16px; color: var(--ios-text); font-size: 16px; font-weight: 650; letter-spacing: -.015em; }
.row { display: flex; align-items: center; gap: 16px; min-height: 74px; margin: 0; padding: 16px 0; border-top: 1px solid var(--ios-line); }
.row > span:first-child { flex: 0 0 150px; min-width: 0; color: var(--ios-text); }
.chat-names { display: flex; flex-wrap: wrap; gap: 6px 12px; margin: 0 0 16px 166px; color: var(--ios-secondary); font-size: 12px; overflow-wrap: anywhere; }
.chat-name { min-width: 0; }
.row.switch { flex-direction: row-reverse; justify-content: space-between; gap: 20px; cursor: pointer; }
.row.switch span { flex: 1; min-width: 0; line-height: 1.7; }
.secret-field { position: relative; flex: 1; min-width: 0; }
.secret-field .inp { width: 100%; padding-right: 52px; }
.secret-field button { position: absolute; right: 1px; top: 1px; display: grid; place-items: center; width: 44px; height: calc(100% - 2px); border: 0; border-radius: 11px; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.secret-field button:hover { color: var(--ios-text); }
.secret-field svg { width: 20px; fill: none; stroke: currentColor; stroke-width: 1.8; }
.inp { flex: 1; min-width: 0; width: 100%; min-height: 44px; padding: 10px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-text); transition: border-color var(--ios-fast) ease; }
.inp:focus { border-color: var(--accent, #0063dc); }
.fld { display: flex; align-items: center; gap: 16px; min-height: 74px; padding: 16px 0; border-top: 1px solid var(--ios-line); }
.lbl { flex: 0 0 150px; color: var(--ios-text); }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; padding: 9px 14px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-secondary); cursor: pointer; }
.chip:has(input:checked) { border-color: var(--accent, #0063dc); color: var(--ios-text); background: var(--accent-dim, #e8f1ff); }
.chip input { flex: none; width: 18px; height: 18px; margin: 0; accent-color: var(--ios-accent); cursor: pointer; }
.row.switch input { appearance: none; -webkit-appearance: none; position: relative; flex: 0 0 50px; width: 50px; height: 30px; margin: 0; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); cursor: pointer; transition: background-color var(--ios-fast) ease; }
.row.switch input::before { content: ''; position: absolute; top: 2px; left: 2px; width: 24px; height: 24px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .2); transition: transform var(--ios-duration) var(--ios-ease); }
.row.switch input:checked { border-color: transparent; background: var(--ios-accent); }
.row.switch input:checked::before { transform: translateX(20px); }
.btn, .btn-primary, .btn-sm { min-height: 44px; padding: 10px 18px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font-weight: 500; cursor: pointer; }
.btn:hover:not(:disabled), .btn-sm:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.btn-primary { align-self: flex-end; min-width: 132px; margin-top: 4px; border-color: transparent; background: var(--ios-accent); color: #fff; font-weight: 600; }
.btn-primary:hover:not(:disabled) { filter: brightness(1.08); }
.btn:disabled, .btn-primary:disabled, .btn-sm:disabled { opacity: .5; cursor: not-allowed; }
.status { display: flex; flex-direction: column; align-items: flex-start; gap: 20px; }
.status .card { align-self: stretch; }
.kv { display: flex; align-items: center; justify-content: space-between; gap: 20px; min-height: 60px; padding: 14px 0; border-top: 1px solid var(--ios-line); }
.kv span { color: var(--ios-secondary); }
.kv b { min-width: 0; font-weight: 600; text-align: right; overflow-wrap: anywhere; font-variant-numeric: tabular-nums; }
.ok, .kv b.ok { color: var(--success, #087758); }
.err, .kv b.err { color: var(--danger, #bd2733); }
.test-result { align-self: stretch; margin: 0; padding: 16px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-surface); font-size: 13px; line-height: 1.75; overflow-wrap: anywhere; }
.toolbar { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 16px; }
.muted { color: var(--ios-secondary); font-size: 12px; }
.movie-table-wrap { max-width: 100%; min-width: 0; overflow: auto; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); scrollbar-width: thin; scrollbar-color: var(--border-light, #b9bec9) transparent; }
.tbl { width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
.tbl th, .tbl td { padding: 13px 14px; border-bottom: 1px solid var(--ios-line); text-align: left; white-space: nowrap; }
.tbl th { color: var(--ios-secondary); background: var(--ios-inset); font-size: 12px; font-weight: 500; }
.tbl td { color: var(--ios-text); }
.tbl td:nth-child(2), .tbl td:nth-child(3) { min-width: 120px; max-width: 260px; white-space: normal; overflow-wrap: anywhere; }
.tbl tbody tr:last-child td { border-bottom: 0; }
.tbl td.muted { color: var(--ios-secondary); font-size: 12px; }
.tbl td.empty { padding: 40px 20px; color: var(--ios-secondary); text-align: center; }
.tmdb-id { color: var(--accent, #0063dc); font-family: var(--font-mono, ui-monospace, monospace); font-size: 12px; }
.action-转发 { color: var(--success, #087758); }
.action-跳过 { color: var(--warning, #926100); }
.action-失败 { color: var(--danger, #bd2733); }
:global(html[data-theme='transparent'] .movie-monitor-config .section),
:global(html[data-theme='transparent'] .movie-monitor-config .card),
:global(html[data-theme='transparent'] .movie-monitor-config .movie-table-wrap) { backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); -webkit-backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); }
@container (max-width: 600px) {
  .movie-monitor-config { gap: 20px; }
  .tabs button { padding-inline: 5px; font-size: 13px; }
  .section, .card { padding-inline: 16px; }
  .row:not(.switch), .fld { flex-direction: column; align-items: stretch; gap: 8px; }
  .row:not(.switch) > span:first-child, .lbl { flex: none; }
  .secret-field { flex: none; width: 100%; }
  .chat-names { margin-left: 0; }
  .inp { font-size: 16px; }
  .settings .btn-primary { width: 100%; margin-top: 4px; }
  .tbl th, .tbl td { padding: 12px; }
}
@media (forced-colors: active) {
  .row.switch input { appearance: auto !important; }
  .row.switch input::before { display: none; }
  .tabs::before { border: 2px solid Highlight; }
}
</style>
