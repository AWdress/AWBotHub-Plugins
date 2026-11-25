<script setup>
// 自动订阅助手 · 配置/管理界面（模块联邦暴露为 ./Config）。
// 平台注入 props { pluginId, host }；host: getConfig/saveConfig/callApi/toast/token。
// 三个页签：配置（左侧分组 + 右侧明细，宽屏 master-detail）/ 历史 / 订阅。
import { ref, reactive, onMounted, computed, nextTick } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

const props = defineProps({
  pluginId: { type: String, required: true },
  host: { type: Object, required: true },
})
const CronInput = computed(() => props.host.ui.CronInput)

// ── 静态选项（与后端取值一一对应）──
const DOUBAN_RANKS = [
  { v: 'movie-hot-gaia', l: '热门电影' }, { v: 'tv-hot', l: '热门电视剧' },
  { v: 'movie-real-time', l: '实时热门电影' }, { v: 'show-domestic', l: '热门综艺' },
  { v: 'movie-weekly', l: '一周口碑电影榜' }, { v: 'movie-ustop', l: '电影北美票房榜' },
  { v: 'movie-top250', l: '电影TOP250' },
]
const MEDIA_TYPES = [{ v: 'all', l: '全部' }, { v: 'movie', l: '仅电影' }, { v: 'tv', l: '仅剧集' }]
const MIKAN_SEASONS = [
  { v: '当前', l: '当前季度(自动)' }, { v: '冬', l: '冬季' }, { v: '春', l: '春季' },
  { v: '夏', l: '夏季' }, { v: '秋', l: '秋季' },
]
const NF_DATASETS = [{ v: 'all-weeks-global', l: '最新周榜' }, { v: 'most-popular', l: '史上最热(不分周)' }]
const NF_CATS = [
  { v: 'Films (English)', l: '英语电影' }, { v: 'Films (Non-English)', l: '非英语电影' },
  { v: 'TV (English)', l: '英语剧集' }, { v: 'TV (Non-English)', l: '非英语剧集' },
]
const NF_COUNTRY_TYPES = [{ v: 'Films', l: '电影' }, { v: 'TV', l: '剧集' }]
const MY_PLATFORMS = [
  { v: 'all', l: '全网' }, { v: 'tx', l: '腾讯视频' }, { v: 'iqiyi', l: '爱奇艺' },
  { v: 'youku', l: '优酷' }, { v: 'mgtv', l: '芒果TV' }, { v: 'letv', l: '乐视' },
  { v: 'pptv', l: 'PPTV' }, { v: 'sohu', l: '搜狐' },
]
const MY_TYPES = [
  { v: 'series', l: '电视剧+网络剧' }, { v: 'tv', l: '电视剧' },
  { v: 'web', l: '网络剧' }, { v: 'variety', l: '综艺' },
]
const STATUS_LABELS = {
  subscribed: '新增订阅', exists: '已订阅', in_library: '库中已有',
  unrecognized: '未识别', filtered: '已过滤', already_handled: '已处理', duplicate: '重复已合并', error: '失败',
}
const STATUS_COLORS = {
  subscribed: '#6ee7a8', exists: '#6ea8fe', in_library: '#b9c0cc',
  unrecognized: '#e0b34d', filtered: '#7a8291', already_handled: '#7a8291', duplicate: '#7a8291', error: '#ff6b6b',
}
// 历史顶部统计卡顺序。
const STAT_CARDS = ['subscribed', 'in_library', 'exists', 'filtered', 'unrecognized', 'error']

// 配置分组（左侧导航）。en=对应启用开关键（有则显示启用小圆点）。
const GROUPS = [
  { key: 'global', label: '全局设置' },
  { key: 'missing', label: '本地缺集', en: 'auto_subscribe_missing' },
  { key: 'moviepilot', label: 'MoviePilot 接口', en: 'mp_api_enabled' },
  { key: 'ranks', label: '影视榜单' },
]
const LEGACY_SOURCES = [
  { id: 'douban', name: '豆瓣' }, { id: 'mikan', name: 'Mikan 新番' },
  { id: 'netflix', name: '奈飞' }, { id: 'maoyan', name: '猫眼' },
]

const DEFAULTS = {
  api_url: '', api_key: '', schedule: '0 8 * * *', notify: true, ai_assist_recognition: false,
  mp_api_enabled: false, mp_api_key: '', mp_whole_series: false,
  auto_fill_missing: false, auto_fill_missing_limit: 20,
  auto_subscribe_missing: false, auto_subscribe_missing_limit: 0,
  emby_server: '', emby_api_key: '', tmdb_key: '', missing_air_delay_days: 1,
  min_year: 0, min_vote: 0, min_popularity: 0, media_type: 'all',
  charts_enabled: false, charts_boards: ['guduo:剧集', 'tmdb:tv'], charts_limit: 20, charts_cache_hours: 6,
  charts_trakt_client_id: '', charts_filter_custom: false, charts_min_year: 0, charts_min_vote: 0, charts_media_type: 'all',
  douban_enabled: false, douban_ranks: ['movie-hot-gaia', 'tv-hot'],
  douban_rsshub: 'https://rsshub.app', douban_rss_custom: '',
  douban_filter_custom: false, douban_min_year: 0, douban_min_vote: 0, douban_media_type: 'all',
  mikan_enabled: false, mikan_season: '当前', mikan_year: 0, mikan_resolve_detail: true,
  mikan_filter_custom: false, mikan_min_year: 0, mikan_min_vote: 0,
  netflix_enabled: false, netflix_global: true, netflix_dataset: 'all-weeks-global',
  netflix_media_types: ['Films (English)', 'Films (Non-English)', 'TV (English)', 'TV (Non-English)'],
  netflix_countries: [], netflix_country_types: ['Films', 'TV'],
  netflix_limit: 10, netflix_rich: true,
  netflix_filter_custom: false, netflix_min_year: 0, netflix_min_vote: 0, netflix_media_type: 'all',
  maoyan_enabled: false, maoyan_movie_box: true, maoyan_web_platforms: [], maoyan_web_types: [],
  maoyan_num: 10, maoyan_filter_custom: false, maoyan_min_year: 0, maoyan_min_vote: 0, maoyan_media_type: 'all',
}

const tab = ref('settings')
const group = ref('global')
const rankSource = ref('douban')
const loading = ref(true)
const configReady = ref(false)
const saving = ref(false)
const running = ref(false)
const testing = ref(false)
const secretVisible = reactive({ api_key: false, emby_api_key: false, tmdb_key: false, mp_api_key: false, charts_trakt_client_id: false })
const secretLoading = reactive({ api_key: false, emby_api_key: false, tmdb_key: false, mp_api_key: false, charts_trakt_client_id: false })
const mpGenerating = ref(false)
const mpBasePath = ref('/api/plugin/auto_subscribe/mp')
const mpUsername = ref('forward')
const mpAddress = computed(() => `${globalThis.location?.origin || ''}${mpBasePath.value}`)
const libraryTesting = ref(false)
const libraryTestOutput = ref('')
const missingStats = ref({})
const cfg = reactive({ ...DEFAULTS, charts_boards: [...DEFAULTS.charts_boards] })
const countries = ref([])
const chartsCatalog = ref([])
const chartsLoading = ref(true)
const chartsLoadError = ref('')
const chartsErrors = ref({})
const chartsErrorSummary = ref(null)
const runOutput = ref('')

const history = ref([])
const lastRun = ref('')
const histStats = ref({})
const historyLoading = ref(false)
const statusFilter = ref('all')
const subs = ref([])
const subsLoading = ref(false)
const subsError = ref('')

const rankSources = computed(() => [
  ...LEGACY_SOURCES,
  ...chartsCatalog.value.filter(source => !LEGACY_SOURCES.some(legacy => legacy.id === source.id)),
])
const currentChartSource = computed(() => chartsCatalog.value.find(source => source.id === rankSource.value))
function sourceEnabled(id) {
  const chart = chartsCatalog.value.find(source => source.id === id)
  return !!cfg[`${id}_enabled`] || !!(cfg.charts_enabled && chart && selectedInSource(chart))
}
const enabledCount = computed(() => rankSources.value.filter(source => sourceEnabled(source.id)).length)
const selectedCharts = computed(() => Array.isArray(cfg.charts_boards) ? cfg.charts_boards : [])
const knownCharts = computed(() => new Set(chartsCatalog.value.flatMap(source => source.boards.map(board => board.id))))
const unknownCharts = computed(() => selectedCharts.value.filter(id => !knownCharts.value.has(id)))
const usesTmdbCharts = computed(() => selectedCharts.value.some(id => String(id).startsWith('tmdb:')))
const usesAnimationCharts = computed(() => selectedCharts.value.some(id =>
  ['bangumi', 'bili', 'mal', 'anilist'].includes(String(id).split(':')[0]) || ['guduo:动漫', 'douban:tv_animation'].includes(id)
))
const needsChartsTmdb = computed(() => usesTmdbCharts.value || usesAnimationCharts.value)
const usesTraktCharts = computed(() => selectedCharts.value.some(id => String(id).startsWith('trakt:')))

onMounted(async () => {
  try {
    const saved = await props.host.getConfig()
    Object.assign(cfg, DEFAULTS, saved || {})
    cfg.charts_boards = Array.isArray(saved?.charts_boards) ? [...saved.charts_boards] : [...DEFAULTS.charts_boards]
    configReady.value = true
  } catch (e) {
    props.host.toast.error('读取配置失败：' + (e.message || e))
  } finally {
    loading.value = false
  }
  await loadMeta()
})

async function loadMeta() {
  if (!chartsLoading.value) chartsLoading.value = true
  chartsLoadError.value = ''
  try {
    const meta = await props.host.callApi('/meta')
    countries.value = meta.countries || []
    mpBasePath.value = meta.mp_base_path || mpBasePath.value
    mpUsername.value = meta.mp_username || mpUsername.value
    const catalog = meta.charts_catalog
    if (!Array.isArray(catalog) || !catalog.length || catalog.some(source =>
      !source || typeof source.id !== 'string' || typeof source.name !== 'string' || !Array.isArray(source.boards) || !source.boards.length ||
      source.boards.some(board => !board || typeof board.id !== 'string' || typeof board.name !== 'string')
    )) throw new Error('未收到有效的榜单目录，请确认插件已更新')
    chartsCatalog.value = catalog
  } catch (e) {
    chartsLoadError.value = '榜单目录读取失败：' + (e.message || e)
  } finally { chartsLoading.value = false }
}

function selectedInSource(source) {
  return source.boards.filter(board => selectedCharts.value.includes(board.id)).length
}

function toggleChart(id) {
  if (!Array.isArray(cfg.charts_boards)) cfg.charts_boards = []
  toggle(cfg.charts_boards, id)
  chartsErrors.value = {}
}

function validateCharts() {
  const errors = {}
  if (cfg.charts_enabled) {
    if (chartsLoading.value || chartsLoadError.value || !chartsCatalog.value.length) errors.catalog = '请先成功读取榜单目录，再启用并保存。'
    else if (unknownCharts.value.length) errors.boards = '有已失效的榜单，请移除后重新选择。'
    if (!selectedCharts.value.length) errors.boards = '请至少选择一个榜单。'
    if (needsChartsTmdb.value && !String(cfg.tmdb_key || '').trim()) errors.tmdb = '所选 TMDB 或动画榜单需要 TMDB 密钥，请填写后保存。'
    if (usesTraktCharts.value && !String(cfg.charts_trakt_client_id || '').trim()) errors.trakt = '选择 Trakt 榜单时，请填写 Trakt Client ID。'
  }
  if (!Number.isInteger(cfg.charts_limit) || cfg.charts_limit < 1 || cfg.charts_limit > 100) errors.limit = '每榜条数请填写 1～100 的整数。'
  if (!Number.isInteger(cfg.charts_cache_hours) || cfg.charts_cache_hours < 1 || cfg.charts_cache_hours > 24) errors.cache = '缓存时间请填写 1～24 的整数。'
  if (cfg.charts_filter_custom) {
    if (!Number.isInteger(cfg.charts_min_year) || cfg.charts_min_year < 0 || cfg.charts_min_year > 9999) errors.year = '最低年份请填写 0～9999 的整数，0 表示不限。'
    if (!Number.isFinite(cfg.charts_min_vote) || cfg.charts_min_vote < 0 || cfg.charts_min_vote > 10) errors.vote = '最低评分请填写 0～10 的数字，0 表示不限。'
    if (!MEDIA_TYPES.some(option => option.v === cfg.charts_media_type)) errors.media = '请选择有效的媒体类型。'
  }
  chartsErrors.value = errors
  return !Object.keys(errors).length
}

function toggle(arr, val) {
  const i = arr.indexOf(val)
  if (i >= 0) arr.splice(i, 1)
  else arr.push(val)
}

async function save() {
  if (!configReady.value || saving.value) {
    if (!configReady.value) props.host.toast.error('配置未成功读取，请重新打开配置页后再保存')
    return
  }
  saving.value = true
  try {
    if (!validateCharts()) {
      tab.value = 'settings'
      group.value = 'ranks'
      await nextTick()
      chartsErrorSummary.value?.focus()
      throw new Error('影视榜单设置有误，请按页面提示修改')
    }
    if (cfg.auto_subscribe_missing && (!String(cfg.emby_server || '').trim() || !String(cfg.emby_api_key || '').trim() || !String(cfg.tmdb_key || '').trim())) {
      throw new Error('请在「本地缺集」填写 Emby 地址、Emby API Key 和 TMDB 密钥')
    }
    if (!Number.isInteger(cfg.missing_air_delay_days) || cfg.missing_air_delay_days < 0 || cfg.missing_air_delay_days > 30) {
      throw new Error('播出缓冲天数请填写 0～30 的整数')
    }
    if (cfg.mp_api_enabled && cfg.mp_api_key !== '********' && !/^[A-Za-z0-9._~-]{32,256}$/.test(cfg.mp_api_key)) {
      throw new Error('请在「MoviePilot 接口」生成专用密码，再保存配置')
    }
    await props.host.saveConfig({ ...cfg })
    props.host.toast.success('配置已保存')
  } catch (e) {
    props.host.toast.error('保存失败：' + (e.message || e))
  } finally {
    saving.value = false
  }
}

async function toggleSecret(key) {
  if (secretLoading[key]) return
  if (secretVisible[key]) { secretVisible[key] = false; return }
  secretLoading[key] = true
  try {
    if (cfg[key] === '********') cfg[key] = await props.host.revealSecret(key)
    secretVisible[key] = true
  } catch (e) {
    props.host.toast.error('读取密钥失败：' + (e.message || e))
  } finally { secretLoading[key] = false }
}

async function generateMpKey() {
  if (mpGenerating.value || !configReady.value) return
  mpGenerating.value = true
  try {
    const result = await props.host.callApi('/mp/key', { method: 'POST', body: {} })
    if (!/^[A-Za-z0-9._~-]{32,256}$/.test(result.key || '')) throw new Error('返回的密码格式无效')
    cfg.mp_api_key = result.key
    secretVisible.mp_api_key = false
    props.host.toast.success('专用密码已生成，请保存配置；更换后需在 Forward 更新密码并重新登录')
  } catch (e) {
    props.host.toast.error('生成密码失败：' + (e.message || e))
  } finally { mpGenerating.value = false }
}

async function testLibrary() {
  libraryTesting.value = true
  libraryTestOutput.value = '正在检查已保存的 Emby 和 TMDB 连接…'
  try {
    const r = await props.host.callApi('/test-library')
    libraryTestOutput.value = r.message || (r.ok ? `连接正常，可读取 ${r.series_count || 0} 部 Emby 剧集` : '连接检查失败')
    if (!r.ok) props.host.toast.error(libraryTestOutput.value)
  } catch (e) {
    libraryTestOutput.value = '连接检查失败：' + (e.message || e)
    props.host.toast.error(libraryTestOutput.value)
  } finally { libraryTesting.value = false }
}

async function testConn() {
  testing.value = true
  try {
    const r = await props.host.callApi('/test')
    if (r.ok) props.host.toast.success('连接正常 ✅ ' + JSON.stringify(r.quota || {}))
    else props.host.toast.error('连接失败：' + (r.message || '未知'))
  } catch (e) {
    props.host.toast.error('连接失败：' + (e.message || e))
  } finally {
    testing.value = false
  }
}

async function runNow() {
  running.value = true
  runOutput.value = '运行中…'
  try {
    const r = await props.host.callApi('/run', { method: 'POST', body: {} })
    runOutput.value = r.summary || r.message || '完成'
    if (r.ok === false) props.host.toast.error('运行失败，详见下方')
    else props.host.toast.success(r.started ? '已在后台开始运行' : '已运行一轮')
  } catch (e) {
    runOutput.value = '运行失败：' + (e.message || e)
    props.host.toast.error('运行失败：' + (e.message || e))
  } finally {
    running.value = false
  }
}

// ── 历史 ──
async function loadHistory() {
  historyLoading.value = true
  try {
    const r = await props.host.callApi('/history')
    history.value = r.items || []
    lastRun.value = r.last_run || ''
    histStats.value = r.stats || {}
    missingStats.value = r.missing || {}
  } catch (e) {
    props.host.toast.error('读取历史失败：' + (e.message || e))
  } finally {
    historyLoading.value = false
  }
}
const filteredHistory = computed(() =>
  statusFilter.value === 'all' ? history.value : history.value.filter(h => h.status === statusFilter.value)
)
function typeOfKey(key) { return String(key || '').startsWith('tv:') ? '剧集' : '电影' }
async function delHistory(key) {
  try {
    const r = await props.host.callApi('/history/delete', { method: 'POST', body: { key } })
    if (r.ok === false) throw new Error(r.message || '历史记录未删除')
    history.value = history.value.filter(h => h.key !== key)
  } catch (e) { props.host.toast.error('删除失败：' + (e.message || e)) }
}
async function clearHistory() {
  if (!confirm('确定清空全部处理历史？(不影响已在 NextFind 的订阅)')) return
  try {
    const r = await props.host.callApi('/history/delete', { method: 'POST', body: { clear: true } })
    if (r.ok === false) throw new Error(r.message || '历史记录未清空')
    history.value = []
    props.host.toast.success('已清空历史')
  } catch (e) { props.host.toast.error('清空失败：' + (e.message || e)) }
}

// ── 订阅 ──
async function loadSubs() {
  subsLoading.value = true
  subsError.value = ''
  try {
    const r = await props.host.callApi('/subscriptions')
    subs.value = r.items || []
    if (r.error) subsError.value = r.error
  } catch (e) {
    subsError.value = e.message || String(e)
  } finally {
    subsLoading.value = false
  }
}
async function removeSub(s) {
  if (!confirm(`取消订阅《${s.title}》？`)) return
  try {
    const r = await props.host.callApi('/subscriptions/remove', {
      method: 'POST', body: { tmdb_id: s.tmdb_id, media_type: s.media_type },
    })
    if (r.ok) {
      subs.value = subs.value.filter(x => !(x.tmdb_id === s.tmdb_id && x.media_type === s.media_type))
      props.host.toast.success('已取消订阅')
    } else props.host.toast.error('取消失败：' + (r.message || ''))
  } catch (e) { props.host.toast.error('取消失败：' + (e.message || e)) }
}

function switchTab(t) {
  tab.value = t
  if (t === 'history' && !history.value.length) loadHistory()
  if (t === 'subs' && !subs.value.length) loadSubs()
}
</script>

<template>
  <IosSettings>
  <div class="as-ios">
    <div v-if="loading" class="as-ios-muted">加载配置…</div>
    <template v-else>
      <div v-if="!configReady" class="as-ios-muted as-ios-err" role="alert">配置读取失败，已禁止保存以保护已有配置。请重新打开配置页重试。</div>
      <div class="as-ios-tabs" :style="{ '--as-ios-tab-index': tab === 'settings' ? 0 : tab === 'history' ? 1 : 2 }" aria-label="NextFind 助手页面">
        <button type="button" :class="['as-ios-tab', { on: tab === 'settings' }]" @click="switchTab('settings')">订阅配置</button>
        <button type="button" :class="['as-ios-tab', { on: tab === 'history' }]" @click="switchTab('history')">订阅历史</button>
        <button type="button" :class="['as-ios-tab', { on: tab === 'subs' }]" @click="switchTab('subs')">订阅管理</button>
      </div>

      <!-- ============ 配置：左分组 + 右明细 ============ -->
      <div v-show="tab === 'settings'" class="as-ios-layout">
        <aside class="as-ios-sidebar">
          <div class="as-ios-side-title">设置分组</div>
          <button type="button" v-for="g in GROUPS" :key="g.key"
                  :class="['as-ios-side-item', { on: group === g.key }]" @click="group = g.key">
            <span>{{ g.label }}</span>
            <span v-if="(g.key === 'ranks' && enabledCount > 0) || (g.en && cfg[g.en])" class="as-ios-dot"></span>
          </button>
          <div class="as-ios-side-foot">启用来源 {{ enabledCount }} / {{ rankSources.length }}</div>
        </aside>

        <div class="as-ios-detail">
          <!-- 全局 -->
          <template v-if="group === 'global'">
            <h3 class="as-ios-det-title">全局设置</h3>
            <section class="as-ios-card">
              <div class="as-ios-card-h">NextFind 连接</div>
              <div class="as-ios-grid">
                <label class="as-ios-row"><span>地址</span>
                  <input v-model="cfg.api_url" class="as-ios-inp" placeholder="https://你的域名/api/openapi" /></label>
                <label class="as-ios-row"><span>密钥</span><div class="as-ios-secret-field">
                  <input v-model="cfg.api_key" class="as-ios-inp" :type="secretVisible.api_key ? 'text' : 'password'" placeholder="X-API-Key" />
                  <button type="button" :disabled="secretLoading.api_key" :aria-label="secretVisible.api_key ? '隐藏密钥' : '显示密钥'" @click="toggleSecret('api_key')">
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>
                  </button></div></label>
              </div>
              <div class="as-ios-row"><button type="button" class="as-ios-btn" :disabled="testing" @click="testConn">{{ testing ? '测试中…' : '测试连接' }}</button></div>
            </section>
            <section class="as-ios-card">
              <div class="as-ios-card-h">运行</div>
              <div class="as-ios-grid">
                <label class="as-ios-row"><span>定时（Cron）</span><component :is="CronInput" v-model="cfg.schedule" /></label>
                <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.notify" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>推送运行结果</span></label>
                <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.ai_assist_recognition" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>平台 AI 辅助识别</span></label>
                <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.auto_fill_missing" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>自动补缺集</span></label>
                <label v-if="cfg.auto_fill_missing" class="as-ios-row"><span>每轮补缺上限</span><input v-model.number="cfg.auto_fill_missing_limit" class="as-ios-inp" type="number" min="1" max="100" /></label>
              </div>
              <div v-if="cfg.ai_assist_recognition" class="as-ios-hint">仅在常规搜索无结果时调用平台 AI 清洗片名、判断电影/剧集及季号；识别结果仍须经 NextFind 核验，平台 AI 不可用时自动降级。</div>
              <div v-if="cfg.auto_fill_missing" class="as-ios-hint as-ios-flow-hint">检查已有剧集订阅的入库进度，将明确缺集的项目加入补缺队列，每轮按补缺上限处理。不新增订阅，也无需启用榜单源。</div>
              <div class="as-ios-hint as-ios-flow-hint">本地缺集自动订阅请在左侧「本地缺集」设置。先保存配置，再测试连接或立即运行。</div>
              <div class="as-ios-row">
                <button type="button" class="as-ios-btn as-ios-primary" :disabled="running" @click="runNow">{{ running ? '运行中…' : '立即运行一次' }}</button>
              </div>
              <pre v-if="runOutput" class="as-ios-output">{{ runOutput }}</pre>
            </section>
            <section class="as-ios-card">
              <div class="as-ios-card-h">全局过滤（各来源默认；可在来源内单独覆盖）</div>
              <div class="as-ios-grid">
                <label class="as-ios-row"><span>年份≥</span><input v-model.number="cfg.min_year" class="as-ios-inp" type="number" /><span class="as-ios-hint">0=不限</span></label>
                <label class="as-ios-row"><span>评分≥</span><input v-model.number="cfg.min_vote" class="as-ios-inp" type="number" min="0" max="10" step="0.5" /><span class="as-ios-hint">0=不限</span></label>
                <label class="as-ios-row"><span>热度≥</span><input v-model.number="cfg.min_popularity" class="as-ios-inp" type="number" /><span class="as-ios-hint">0=不限</span></label>
                <label class="as-ios-row"><span>媒体类型</span>
                  <select v-model="cfg.media_type" class="as-ios-inp"><option v-for="o in MEDIA_TYPES" :key="o.v" :value="o.v">{{ o.l }}</option></select></label>
              </div>
            </section>
          </template>

          <template v-else-if="group === 'missing'">
            <h3 class="as-ios-det-title">本地缺集</h3>
            <section class="as-ios-card">
              <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.auto_subscribe_missing" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>本地缺集自动订阅</span></label>
              <div class="as-ios-hint as-ios-flow-hint">从 Emby 读取本地剧集，按季号和集号对比 TMDB 已播集。一次订阅全部未订阅的缺集剧集；不再使用 NextFind 本地缺集接口，也不调用 AI。</div>
              <div class="as-ios-hint as-ios-flow-hint">已有订阅不会重复新增。需要让 NextFind 搜索补缺时，请在「全局设置」开启「自动补缺集」。</div>
            </section>
            <section class="as-ios-card">
              <div class="as-ios-card-h">Emby 与 TMDB 连接</div>
              <label class="as-ios-fld"><span class="as-ios-lbl">Emby 服务地址</span>
                <input v-model="cfg.emby_server" class="as-ios-inp" placeholder="https://你的Emby域名" />
              </label>
              <div class="as-ios-hint as-ios-flow-hint">填写平台所在服务器能访问的 Emby 地址，支持反代域名和带 /emby 的地址。API Key 需能读取完整剧集库。</div>
              <label class="as-ios-fld"><span class="as-ios-lbl">Emby API Key</span><div class="as-ios-secret-field">
                <input v-model="cfg.emby_api_key" class="as-ios-inp" :type="secretVisible.emby_api_key ? 'text' : 'password'" autocomplete="off" placeholder="在 Emby 控制台 → 高级 → API 密钥中创建" />
                <button type="button" :disabled="secretLoading.emby_api_key" :aria-label="secretVisible.emby_api_key ? '隐藏 Emby API Key' : '显示 Emby API Key'" @click="toggleSecret('emby_api_key')">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>
                </button></div>
              </label>
              <label class="as-ios-fld"><span class="as-ios-lbl">TMDB 密钥</span><div class="as-ios-secret-field">
                <input v-model="cfg.tmdb_key" class="as-ios-inp" :type="secretVisible.tmdb_key ? 'text' : 'password'" autocomplete="off" placeholder="TMDB API Key 或 API Read Access Token" />
                <button type="button" :disabled="secretLoading.tmdb_key" :aria-label="secretVisible.tmdb_key ? '隐藏 TMDB 密钥' : '显示 TMDB 密钥'" @click="toggleSecret('tmdb_key')">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>
                </button></div>
              </label>
              <div class="as-ios-hint as-ios-flow-hint">这些配置仅用于 NextFind 助手，不读取其他插件。仅检查 Emby 已有且带 TMDB ID 的剧集；电影、特别篇和季集号不明的条目不参与。</div>
              <label class="as-ios-row"><span>播出缓冲天数</span><input v-model.number="cfg.missing_air_delay_days" class="as-ios-inp as-ios-sm" type="number" min="0" max="30" /></label>
              <div class="as-ios-hint as-ios-flow-hint">默认 1 天：按北京时间只核对截至昨天已播出的集，避免当天未放送就判缺集。填 0 包含今天；未来集或没有明确播出日期的集不计入。</div>
              <div class="as-ios-hint as-ios-flow-hint">先保存，再测试连接。测试只读取 Emby 和 TMDB，不新增订阅、不补缺，也不修改 Emby。</div>
              <div class="as-ios-row"><button type="button" class="as-ios-btn" :disabled="libraryTesting" @click="testLibrary">{{ libraryTesting ? '检查中…' : '测试 Emby / TMDB 连接' }}</button></div>
              <pre v-if="libraryTestOutput" class="as-ios-output" role="status" aria-live="polite">{{ libraryTestOutput }}</pre>
            </section>
          </template>

          <template v-else-if="group === 'moviepilot'">
            <h3 class="as-ios-det-title">MoviePilot 订阅接口</h3>
            <section class="as-ios-card">
              <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.mp_api_enabled" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>接收第三方订阅，转交 NextFind（默认关闭）</span></label>
              <div class="as-ios-hint as-ios-flow-hint">提供 MoviePilot v2 风格的登录、查询、新增和取消订阅接口。使用上方「全局设置」中已保存的 NextFind 连接；不需要安装 MoviePilot。取消订阅不会删除已入库文件。</div>
              <div class="as-ios-hint as-ios-flow-hint">NextFind 按整部作品订阅，不按季限制。默认拒绝指定季的请求；如果接受追整部剧，请开启下方选项。画质、站点、下载目录等 MoviePilot 专属筛选不支持，不能把它当作完整 MoviePilot 服务。</div>
              <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.mp_whole_series" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>允许指定季的请求按整部剧订阅或取消（默认关闭）</span></label>
              <div class="as-ios-hint as-ios-flow-hint">开启后，Forward 订阅或移除某一季，会对应订阅或取消 NextFind 的整部剧追更。关闭时拒绝单季操作，不会悄悄扩大范围；媒体文件不会删除。</div>
              <label class="as-ios-fld"><span class="as-ios-lbl">接口专用密码 / API Key</span><div class="as-ios-secret-field">
                <input v-model="cfg.mp_api_key" class="as-ios-inp" :type="secretVisible.mp_api_key ? 'text' : 'password'" autocomplete="new-password" placeholder="点击下方按钮生成；不是平台登录密码或 NextFind 密钥" />
                <button type="button" :disabled="secretLoading.mp_api_key" :aria-label="secretVisible.mp_api_key ? '隐藏接口专用密码' : '显示接口专用密码'" @click="toggleSecret('mp_api_key')">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>
                </button></div>
              </label>
              <div class="as-ios-row"><button type="button" class="as-ios-btn" :disabled="mpGenerating || !configReady" @click="generateMpKey">{{ mpGenerating ? '生成中…' : (cfg.mp_api_key ? '生成新的专用密码' : '生成专用密码') }}</button></div>
              <div class="as-ios-hint as-ios-flow-hint">先生成密码，再启用并保存。密码默认隐藏，点眼睛查看和复制。更换后旧登录凭据立即失效，Forward 需要更新密码并重新登录。</div>
            </section>
            <section class="as-ios-card">
              <div class="as-ios-card-h">Forward 怎么填写</div>
              <label class="as-ios-fld"><span class="as-ios-lbl">MoviePilot 服务器地址</span><input class="as-ios-inp" :value="mpAddress" readonly aria-label="Forward MoviePilot 服务器地址" /></label>
              <div class="as-ios-hint as-ios-flow-hint">在 Forward「设置 → 服务 → 服务器订阅」填写这个完整地址，不再追加 /api/v1。请从你服务器的域名打开平台，再复制地址；手机须能访问该地址，外网请使用 HTTPS。</div>
              <label class="as-ios-row"><span>用户名</span><input class="as-ios-inp" :value="mpUsername" readonly aria-label="Forward 用户名" /></label>
              <div class="as-ios-hint as-ios-flow-hint">开启「是否需要登录」，用户名填上面的值，密码填本页的接口专用密码。需要同步取消追更时，可开启 Forward 的「同步移除订阅」；只取消 NextFind 订阅，不删除媒体文件。</div>
              <div class="as-ios-hint as-ios-flow-hint">Forward 带季号的订阅和移除请求，需要上方允许按整部剧处理。取消后会核对 NextFind 列表，确认已移除才返回成功。同一 TMDB 编号同时对应电影和剧集时会拒绝操作，避免误取消。</div>
            </section>
          </template>

          <!-- 所有榜单使用一个入口；豆瓣直采与 RSS 补充归为同一来源。 -->
          <template v-else-if="group === 'ranks'">
            <h3 class="as-ios-det-title">影视榜单</h3>
            <div class="as-ios-hint as-ios-flow-hint">在这里选择来源和分类。同一作品按 TMDB 编号与媒体类型跨榜合并，电影和剧集不会混在一起；原有选择、过滤和开关保持不变。</div>
            <div v-if="Object.keys(chartsErrors).length" ref="chartsErrorSummary" class="as-ios-charts-error" role="alert" tabindex="-1">未保存：请检查下方榜单选择与通用设置。</div>
            <label class="as-ios-row as-ios-rank-picker"><span>榜单来源</span>
              <select v-model="rankSource" class="as-ios-inp" aria-describedby="rank-source-hint">
                <option v-for="source in rankSources" :key="source.id" :value="source.id">{{ source.name }}{{ sourceEnabled(source.id) ? ' · 已启用' : '' }}</option>
              </select>
            </label>
            <div id="rank-source-hint" class="as-ios-hint as-ios-flow-hint">每个来源只显示一个入口。豆瓣直采与 RSS 放在一起；选其他来源可查看各自的榜单。</div>
            <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.charts_enabled" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>启用直采榜单（原「内置影视榜单」）</span></label>
            <div class="as-ios-hint as-ios-flow-hint">默认关闭。开启后只处理勾选的直采分类；RSS、蜜柑、奈飞和猫眼仍使用各自开关。</div>
            <div v-if="chartsLoading" class="as-ios-hint as-ios-flow-hint" role="status">正在读取可选榜单…</div>
            <div v-else-if="chartsLoadError" class="as-ios-charts-load-error" role="alert">
              <div class="as-ios-charts-error">{{ chartsLoadError }}</div>
              <div class="as-ios-hint as-ios-flow-hint">已有选择已保留。请重试读取；其他来源的设置仍可查看。</div>
              <button type="button" class="as-ios-btn" @click="loadMeta">重新读取榜单</button>
            </div>
            <section v-else-if="currentChartSource" class="as-ios-card as-ios-charts-card">
              <div class="as-ios-charts-heading"><h4 class="as-ios-card-h">{{ currentChartSource.name === '豆瓣热榜' ? '豆瓣直采' : currentChartSource.name }}</h4><span class="as-ios-muted">已选 {{ selectedInSource(currentChartSource) }} / {{ currentChartSource.boards.length }}</span></div>
              <div class="as-ios-chips">
                <label v-for="board in currentChartSource.boards" :key="board.id" class="as-ios-chip"><input type="checkbox" :checked="selectedCharts.includes(board.id)" @change="toggleChart(board.id)" />{{ board.name }}</label>
              </div>
              <div v-if="!cfg.charts_enabled && selectedInSource(currentChartSource)" class="as-ios-hint as-ios-flow-hint">已选分类尚未启用，不会运行。</div>
            </section>
            <div v-if="!chartsLoading && !chartsLoadError && unknownCharts.length" class="as-ios-fld">
              <span class="as-ios-charts-error">这些旧选择已失效，请移除后重新选择：</span>
              <div class="as-ios-chips"><button v-for="id in unknownCharts" :key="id" type="button" class="as-ios-btn" @click="toggleChart(id)">移除 {{ id }}</button></div>
            </div>
            <div v-if="chartsErrors.catalog || chartsErrors.boards" class="as-ios-charts-error" role="alert">{{ chartsErrors.catalog || chartsErrors.boards }}</div>

          <!-- 豆瓣 -->
          <template v-if="rankSource === 'douban'">
            <h4 class="as-ios-det-title">豆瓣 RSS 补充</h4>
            <section class="as-ios-card">
              <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.douban_enabled" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>启用豆瓣 RSS 补充</span></label>
              <template v-if="cfg.douban_enabled">
                <div class="as-ios-fld"><span class="as-ios-lbl">订阅榜单</span>
                  <div class="as-ios-chips">
                    <label v-for="o in DOUBAN_RANKS" :key="o.v" class="as-ios-chip"><input type="checkbox" :checked="cfg.douban_ranks.includes(o.v)" @change="toggle(cfg.douban_ranks, o.v)" />{{ o.l }}</label>
                  </div>
                </div>
                <label class="as-ios-row"><span>RSSHub</span><input v-model="cfg.douban_rsshub" class="as-ios-inp" /></label>
                <label class="as-ios-row as-ios-top"><span>自定义RSS</span><textarea v-model="cfg.douban_rss_custom" class="as-ios-inp" rows="2" placeholder="每行一个完整 RSS 地址"></textarea></label>
                <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.douban_filter_custom" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>独立过滤(否则用全局)</span></label>
                <div v-if="cfg.douban_filter_custom" class="as-ios-grid as-ios-subfilter">
                  <label class="as-ios-row"><span>年份≥</span><input v-model.number="cfg.douban_min_year" class="as-ios-inp" type="number" /></label>
                  <label class="as-ios-row"><span>评分≥</span><input v-model.number="cfg.douban_min_vote" class="as-ios-inp" type="number" min="0" max="10" step="0.5" /></label>
                  <label class="as-ios-row"><span>类型</span><select v-model="cfg.douban_media_type" class="as-ios-inp"><option v-for="o in MEDIA_TYPES" :key="o.v" :value="o.v">{{ o.l }}</option></select></label>
                </div>
              </template>
            </section>
          </template>

          <!-- Mikan -->
          <template v-else-if="rankSource === 'mikan'">
            <section class="as-ios-card">
              <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.mikan_enabled" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>启用 Mikan 新番</span></label>
              <template v-if="cfg.mikan_enabled">
                <div class="as-ios-grid">
                  <label class="as-ios-row"><span>季度</span><select v-model="cfg.mikan_season" class="as-ios-inp"><option v-for="o in MIKAN_SEASONS" :key="o.v" :value="o.v">{{ o.l }}</option></select></label>
                  <label class="as-ios-row"><span>年份</span><input v-model.number="cfg.mikan_year" class="as-ios-inp" type="number" /><span class="as-ios-hint">0=当前年</span></label>
                </div>
                <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.mikan_resolve_detail" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>抓详情补放送年(更准更慢)</span></label>
                <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.mikan_filter_custom" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>独立过滤(否则用全局)</span></label>
                <div v-if="cfg.mikan_filter_custom" class="as-ios-grid as-ios-subfilter">
                  <label class="as-ios-row"><span>年份≥</span><input v-model.number="cfg.mikan_min_year" class="as-ios-inp" type="number" /></label>
                  <label class="as-ios-row"><span>评分≥</span><input v-model.number="cfg.mikan_min_vote" class="as-ios-inp" type="number" min="0" max="10" step="0.5" /></label>
                </div>
              </template>
            </section>
          </template>

          <!-- 奈飞 -->
          <template v-else-if="rankSource === 'netflix'">
            <section class="as-ios-card">
              <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.netflix_enabled" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>启用奈飞榜单</span></label>
              <template v-if="cfg.netflix_enabled">
                <div class="as-ios-grid">
                  <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.netflix_global" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>全球榜</span></label>
                  <label class="as-ios-row"><span>数据源</span><select v-model="cfg.netflix_dataset" class="as-ios-inp"><option v-for="o in NF_DATASETS" :key="o.v" :value="o.v">{{ o.l }}</option></select></label>
                  <label class="as-ios-row"><span>每榜前N</span><input v-model.number="cfg.netflix_limit" class="as-ios-inp" type="number" /></label>
                </div>
                <div class="as-ios-fld"><span class="as-ios-lbl">全球类型</span>
                  <div class="as-ios-chips">
                    <label v-for="o in NF_CATS" :key="o.v" class="as-ios-chip"><input type="checkbox" :checked="cfg.netflix_media_types.includes(o.v)" @change="toggle(cfg.netflix_media_types, o.v)" />{{ o.l }}</label>
                  </div>
                </div>
                <div class="as-ios-fld"><span class="as-ios-lbl">国家/地区榜</span>
                  <div class="as-ios-chips as-ios-scroll">
                    <label v-for="o in countries" :key="o.value" class="as-ios-chip"><input type="checkbox" :checked="cfg.netflix_countries.includes(o.value)" @change="toggle(cfg.netflix_countries, o.value)" />{{ o.label }}</label>
                  </div>
                </div>
                <div class="as-ios-fld" v-if="cfg.netflix_countries.length"><span class="as-ios-lbl">国家榜类型</span>
                  <div class="as-ios-chips">
                    <label v-for="o in NF_COUNTRY_TYPES" :key="o.v" class="as-ios-chip"><input type="checkbox" :checked="cfg.netflix_country_types.includes(o.v)" @change="toggle(cfg.netflix_country_types, o.v)" />{{ o.l }}</label>
                  </div>
                </div>
                <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.netflix_rich" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>富元数据(带年份，识别更准 · 推荐)</span></label>
                <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.netflix_filter_custom" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>独立过滤(否则用全局)</span></label>
                <div v-if="cfg.netflix_filter_custom" class="as-ios-grid as-ios-subfilter">
                  <label class="as-ios-row"><span>年份≥</span><input v-model.number="cfg.netflix_min_year" class="as-ios-inp" type="number" /></label>
                  <label class="as-ios-row"><span>评分≥</span><input v-model.number="cfg.netflix_min_vote" class="as-ios-inp" type="number" min="0" max="10" step="0.5" /></label>
                  <label class="as-ios-row"><span>类型</span><select v-model="cfg.netflix_media_type" class="as-ios-inp"><option v-for="o in MEDIA_TYPES" :key="o.v" :value="o.v">{{ o.l }}</option></select></label>
                </div>
              </template>
            </section>
          </template>

          <!-- 猫眼 -->
          <template v-else-if="rankSource === 'maoyan'">
            <section class="as-ios-card">
              <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.maoyan_enabled" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>启用猫眼榜单</span></label>
              <template v-if="cfg.maoyan_enabled">
                <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.maoyan_movie_box" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>电影票房榜</span></label>
                <div class="as-ios-fld"><span class="as-ios-lbl">网播平台</span>
                  <div class="as-ios-chips">
                    <label v-for="o in MY_PLATFORMS" :key="o.v" class="as-ios-chip"><input type="checkbox" :checked="cfg.maoyan_web_platforms.includes(o.v)" @change="toggle(cfg.maoyan_web_platforms, o.v)" />{{ o.l }}</label>
                  </div>
                </div>
                <div class="as-ios-fld"><span class="as-ios-lbl">网播类型</span>
                  <div class="as-ios-chips">
                    <label v-for="o in MY_TYPES" :key="o.v" class="as-ios-chip"><input type="checkbox" :checked="cfg.maoyan_web_types.includes(o.v)" @change="toggle(cfg.maoyan_web_types, o.v)" />{{ o.l }}</label>
                  </div>
                </div>
                <label class="as-ios-row"><span>每榜条数</span><input v-model.number="cfg.maoyan_num" class="as-ios-inp" type="number" /></label>
                <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.maoyan_filter_custom" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>独立过滤(否则用全局)</span></label>
                <div v-if="cfg.maoyan_filter_custom" class="as-ios-grid as-ios-subfilter">
                  <label class="as-ios-row"><span>年份≥</span><input v-model.number="cfg.maoyan_min_year" class="as-ios-inp" type="number" /></label>
                  <label class="as-ios-row"><span>评分≥</span><input v-model.number="cfg.maoyan_min_vote" class="as-ios-inp" type="number" min="0" max="10" step="0.5" /></label>
                  <label class="as-ios-row"><span>类型</span><select v-model="cfg.maoyan_media_type" class="as-ios-inp"><option v-for="o in MEDIA_TYPES" :key="o.v" :value="o.v">{{ o.l }}</option></select></label>
                </div>
              </template>
            </section>
          </template>


            <details class="as-ios-rank-settings" :open="Object.keys(chartsErrors).length > 0">
              <summary>直采榜单通用设置<span class="as-ios-muted">数量、缓存、密钥与过滤</span></summary>
              <div class="as-ios-rank-settings-body">
            <section class="as-ios-card as-ios-charts-card">
              <div class="as-ios-hint as-ios-flow-hint">这些设置用于直采榜单；RSS、蜜柑、奈飞和猫眼的专用设置保留在对应来源内。</div>
              <div class="as-ios-grid as-ios-charts-grid">
                <div class="as-ios-fld">
                  <label class="as-ios-row" for="charts-limit"><span>每榜前几名</span><input id="charts-limit" v-model.number="cfg.charts_limit" class="as-ios-inp" type="number" min="1" max="100" :aria-invalid="!!chartsErrors.limit" aria-describedby="charts-limit-hint" /></label>
                  <div id="charts-limit-hint" class="as-ios-hint as-ios-flow-hint">每个选中分类取前 1～100 名，默认 20 名。</div>
                  <div v-if="chartsErrors.limit" class="as-ios-charts-error" role="alert">{{ chartsErrors.limit }}</div>
                </div>
                <div class="as-ios-fld">
                  <label class="as-ios-row" for="charts-cache"><span>缓存小时</span><input id="charts-cache" v-model.number="cfg.charts_cache_hours" class="as-ios-inp" type="number" min="1" max="24" :aria-invalid="!!chartsErrors.cache" aria-describedby="charts-cache-hint" /></label>
                  <div id="charts-cache-hint" class="as-ios-hint as-ios-flow-hint">1～24 小时，默认 6 小时；期间运行复用缓存。</div>
                  <div v-if="chartsErrors.cache" class="as-ios-charts-error" role="alert">{{ chartsErrors.cache }}</div>
                </div>
              </div>
            </section>
            <section class="as-ios-card as-ios-charts-card">
              <div class="as-ios-card-h">来源密钥</div>
              <label class="as-ios-fld"><span class="as-ios-lbl">TMDB 密钥{{ needsChartsTmdb ? '（所选榜单需要）' : '（当前所选榜单可不填）' }}</span><div class="as-ios-secret-field">
                <input v-model="cfg.tmdb_key" class="as-ios-inp" :type="secretVisible.tmdb_key ? 'text' : 'password'" autocomplete="off" placeholder="与「本地缺集」共用同一个 TMDB 密钥" :aria-invalid="!!chartsErrors.tmdb" />
                <button type="button" :disabled="secretLoading.tmdb_key" :aria-label="secretVisible.tmdb_key ? '隐藏 TMDB 密钥' : '显示 TMDB 密钥'" @click="toggleSecret('tmdb_key')">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>
                </button></div>
              </label>
              <div v-if="chartsErrors.tmdb" class="as-ios-charts-error" role="alert">{{ chartsErrors.tmdb }}</div>
              <div class="as-ios-hint as-ios-flow-hint">TMDB 榜单及动画类榜单需要此密钥；动画类用它核对作品类型，避免误订阅。其他榜单可不填。修改这里也会同步到「本地缺集」。</div>
              <template v-if="usesTraktCharts">
                <label class="as-ios-fld"><span class="as-ios-lbl">Trakt Client ID（所选榜单需要）</span><div class="as-ios-secret-field">
                  <input v-model="cfg.charts_trakt_client_id" class="as-ios-inp" :type="secretVisible.charts_trakt_client_id ? 'text' : 'password'" autocomplete="off" placeholder="Trakt 应用的 Client ID，不是 Client Secret" :aria-invalid="!!chartsErrors.trakt" />
                  <button type="button" :disabled="secretLoading.charts_trakt_client_id" :aria-label="secretVisible.charts_trakt_client_id ? '隐藏 Trakt Client ID' : '显示 Trakt Client ID'" @click="toggleSecret('charts_trakt_client_id')">
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>
                  </button></div>
                </label>
                <div v-if="chartsErrors.trakt" class="as-ios-charts-error" role="alert">{{ chartsErrors.trakt }}</div>
              </template>
            </section>
            <section class="as-ios-card as-ios-charts-card">
              <label class="as-ios-row as-ios-switch"><span class="as-ios-toggle"><input v-model="cfg.charts_filter_custom" type="checkbox" role="switch" /><span class="as-ios-toggle-track" aria-hidden="true"></span></span><span>使用独立过滤（默认关闭，沿用全局过滤）</span></label>
              <div v-if="!cfg.charts_filter_custom" class="as-ios-hint as-ios-flow-hint">年份、评分和类型沿用「全局设置」。开启后可单独设置下方三项；各来源热度单位不同，不使用全局热度阈值。</div>
              <div v-else class="as-ios-grid as-ios-subfilter as-ios-charts-grid">
                <div class="as-ios-fld"><label class="as-ios-row"><span>最低年份</span><input v-model.number="cfg.charts_min_year" class="as-ios-inp" type="number" min="0" max="9999" :aria-invalid="!!chartsErrors.year" /></label><span class="as-ios-hint as-ios-flow-hint">0 表示不限年份</span><span v-if="chartsErrors.year" class="as-ios-charts-error" role="alert">{{ chartsErrors.year }}</span></div>
                <div class="as-ios-fld"><label class="as-ios-row"><span>最低评分</span><input v-model.number="cfg.charts_min_vote" class="as-ios-inp" type="number" min="0" max="10" step="0.5" :aria-invalid="!!chartsErrors.vote" /></label><span class="as-ios-hint as-ios-flow-hint">0 表示不限评分</span><span v-if="chartsErrors.vote" class="as-ios-charts-error" role="alert">{{ chartsErrors.vote }}</span></div>
                <div class="as-ios-fld"><label class="as-ios-row"><span>媒体类型</span><select v-model="cfg.charts_media_type" class="as-ios-inp" :aria-invalid="!!chartsErrors.media"><option v-for="option in MEDIA_TYPES" :key="option.v" :value="option.v">{{ option.l }}</option></select></label><span v-if="chartsErrors.media" class="as-ios-charts-error" role="alert">{{ chartsErrors.media }}</span></div>
              </div>
            </section>

              </div>
            </details>
          </template>

          <div class="as-ios-savebar" :class="{ 'as-ios-charts-savebar': group === 'ranks' }"><button type="button" class="as-ios-btn as-ios-primary as-ios-lg" :disabled="saving || !configReady" @click="save">{{ saving ? '保存中…' : '保存配置' }}</button></div>
        </div>
      </div>

      <!-- ============ 历史 ============ -->
      <div v-show="tab === 'history'" class="as-ios-pane">
        <div v-if="Object.keys(missingStats).length" class="as-ios-output" role="status">
          <div v-if="missingStats.scan_error">上轮本地缺集：已读取 Emby 剧集 {{ missingStats.scanned ?? '—' }} 部。扫描未完成，未执行缺集订阅。</div>
          <div v-else>上轮本地缺集：Emby 剧集 {{ missingStats.scanned ?? '—' }} 部，缺集剧集 {{ missingStats.checked || 0 }} 部，缺 {{ missingStats.missing_episodes || 0 }} 集；新增 {{ missingStats.added || 0 }} 部，已订阅跳过 {{ missingStats.skipped || 0 }} 部，资料不全跳过 {{ missingStats.unknown || 0 }} 部，失败 {{ missingStats.failed || 0 }} 部。</div>
          <div v-if="missingStats.error" class="as-ios-muted as-ios-err">{{ missingStats.error }}</div>
        </div>
        <div class="as-ios-stats">
          <div v-for="k in STAT_CARDS" :key="k" class="as-ios-stat" :style="{ borderColor: STATUS_COLORS[k] + '55' }">
            <div class="as-ios-stat-n" :style="{ color: STATUS_COLORS[k] }">{{ histStats[k] || 0 }}</div>
            <div class="as-ios-stat-l">{{ STATUS_LABELS[k] }}</div>
          </div>
        </div>
        <div class="as-ios-toolbar">
          <span class="as-ios-muted">上次运行：{{ lastRun || '—' }}</span>
          <span class="as-ios-grow"></span>
          <select v-model="statusFilter" class="as-ios-inp as-ios-sm">
            <option value="all">全部状态</option>
            <option v-for="(l, k) in STATUS_LABELS" :key="k" :value="k">{{ l }}</option>
          </select>
          <button type="button" class="as-ios-btn" @click="loadHistory">刷新</button>
          <button type="button" class="as-ios-btn as-ios-danger" @click="clearHistory">清空</button>
        </div>
        <div v-if="historyLoading" class="as-ios-muted">加载中…</div>
        <div v-else-if="!filteredHistory.length" class="as-ios-empty">暂无订阅历史记录<br><span class="as-ios-muted">启用来源并运行后，这里会记录每次订阅结果</span></div>
        <div v-else class="as-ios-table-wrap" tabindex="0" role="region" aria-label="订阅数据表"><table class="as-ios-tbl">
          <thead><tr><th>标题</th><th>类型</th><th>状态</th><th>来源</th><th>时间</th><th></th></tr></thead>
          <tbody>
            <tr v-for="h in filteredHistory" :key="h.key">
              <td>{{ h.title }}</td>
              <td>{{ typeOfKey(h.key) }}</td>
              <td><span :style="{ color: STATUS_COLORS[h.status] || '#b9c0cc' }">{{ STATUS_LABELS[h.status] || h.status }}</span></td>
              <td class="as-ios-muted">{{ h.source || '—' }}</td>
              <td class="as-ios-muted">{{ h.time }}</td>
              <td><button type="button" class="as-ios-btn as-ios-xs" @click="delHistory(h.key)">删除</button></td>
            </tr>
          </tbody>
        </table></div>
      </div>

      <!-- ============ 订阅 ============ -->
      <div v-show="tab === 'subs'" class="as-ios-pane">
        <div class="as-ios-toolbar">
          <span class="as-ios-muted">NextFind 活跃订阅</span>
          <span class="as-ios-grow"></span>
          <button type="button" class="as-ios-btn" @click="loadSubs">刷新</button>
        </div>
        <div v-if="subsLoading" class="as-ios-muted">加载中…</div>
        <div v-else-if="subsError" class="as-ios-muted as-ios-err">读取失败：{{ subsError }}</div>
        <div v-else-if="!subs.length" class="as-ios-empty">暂无本插件创建的订阅<br><span class="as-ios-muted">启用来源运行后，订阅会出现在这里</span></div>
        <div v-else class="as-ios-table-wrap" tabindex="0" role="region" aria-label="订阅数据表"><table class="as-ios-tbl">
          <thead><tr><th>标题</th><th>类型</th><th>年份</th><th>评分</th><th>进度</th><th>状态</th><th></th></tr></thead>
          <tbody>
            <tr v-for="s in subs" :key="s.tmdb_id + s.media_type">
              <td>{{ s.title }}</td>
              <td>{{ s.media_type === 'tv' ? '剧集' : '电影' }}</td>
              <td class="as-ios-muted">{{ s.year || '—' }}</td>
              <td class="as-ios-muted">{{ s.rating || '—' }}</td>
              <td class="as-ios-muted">{{ s.media_type === 'tv' ? `${s.local_episodes || 0}/${s.total_episodes || 0}` : (s.is_in_library ? '已入库' : '—') }}</td>
              <td class="as-ios-muted">{{ s.sub_status || s.status || '—' }}</td>
              <td><button type="button" class="as-ios-btn as-ios-xs as-ios-danger" @click="removeSub(s)">取消</button></td>
            </tr>
          </tbody>
        </table></div>
      </div>
    </template>
  </div>
  </IosSettings>
</template>

<style scoped>
.as-ios { display: flex; flex-direction: column; gap: 24px; min-width: 0; color: var(--ios-text); }
.as-ios *, .as-ios *::before, .as-ios *::after { box-sizing: border-box; }
.as-ios-tabs { position: relative; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; isolation: isolate; padding: 4px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-inset); }
.as-ios-tabs::before { content: ''; position: absolute; inset: 4px auto 4px 4px; width: calc((100% - 16px) / 3); border-radius: 11px; background: var(--ios-control); box-shadow: 0 2px 5px rgb(0 0 0 / .08); transform: translateX(calc(var(--as-ios-tab-index) * (100% + 4px))); transition: transform var(--ios-duration) var(--ios-ease); z-index: -1; }
.as-ios-tab { min-height: 42px; padding: 8px 10px; border: 0; border-radius: 11px; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.as-ios-tab.on { color: var(--ios-text); font-weight: 650; }
.as-ios-layout { display: grid; grid-template-columns: 150px minmax(0, 1fr); align-items: start; gap: 24px; min-width: 0; }
.as-ios-sidebar { display: flex; flex-direction: column; gap: 4px; min-width: 0; padding: 6px; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-inset); }
.as-ios-side-title { padding: 6px 10px; color: var(--ios-secondary); font-size: 12px; }
.as-ios-side-item { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 44px; padding: 9px 12px; border: 0; border-radius: 12px; background: transparent; color: var(--ios-secondary); text-align: left; cursor: pointer; }
.as-ios-side-item:hover, .as-ios-side-item.on { color: var(--ios-text); background: var(--ios-control); }
.as-ios-side-item.on { font-weight: 600; box-shadow: 0 2px 4px rgb(0 0 0 / .06); }
.as-ios-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--success, #087758); flex: none; }
.as-ios-side-foot { margin-top: 4px; padding: 10px; border-top: 1px solid var(--ios-line); color: var(--ios-secondary); font-size: 12px; }
.as-ios-detail, .as-ios-pane { display: flex; flex-direction: column; gap: 18px; min-width: 0; }
.as-ios-det-title { margin: 0; font-size: 16px; font-weight: 650; line-height: 1.5; letter-spacing: -.015em; color: var(--ios-text); }
.as-ios-card { display: flex; flex-direction: column; gap: 16px; min-width: 0; padding: 20px; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-surface); }
.as-ios-card-h { margin: 0; color: var(--ios-text); font-size: 14px; font-weight: 600; }
.as-ios-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(230px, 100%), 1fr)); align-items: start; gap: 16px; }
.as-ios-grid > .as-ios-row { flex-direction: column; align-items: stretch; }
.as-ios-grid > .as-ios-switch { flex-direction: row; align-items: center; }
.as-ios-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 44px; min-width: 0; }
.as-ios-row > span:first-child:not(.as-ios-toggle), .as-ios-lbl { min-width: 64px; color: var(--ios-text); font-size: 14px; }
.as-ios-row.as-ios-top { flex-direction: column; align-items: stretch; gap: 10px; }
.as-ios-row > :not(span):not(button) { min-width: 0; flex: 1; }
.as-ios-switch { cursor: pointer; }
.as-ios-switch > span:not(.as-ios-toggle) { order: 1; flex: 1; min-width: 0; }
.as-ios-switch > .as-ios-toggle { order: 2; }
.as-ios-toggle { position: relative; display: inline-flex; align-items: center; flex: 0 0 50px; width: 50px; min-height: 44px; }
.as-ios-toggle input { position: absolute; width: 1px; height: 1px; margin: 0; padding: 0; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.as-ios-toggle-track { position: relative; display: block; width: 50px; height: 30px; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); transition: background var(--ios-fast) ease, border-color var(--ios-fast) ease; }
.as-ios-toggle-track::after { content: ''; position: absolute; top: 2px; left: 2px; width: 24px; height: 24px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .2); transition: transform var(--ios-duration) var(--ios-ease); }
.as-ios-toggle input:checked + .as-ios-toggle-track { border-color: transparent; background: var(--ios-accent); }
.as-ios-toggle input:checked + .as-ios-toggle-track::after { transform: translateX(20px); }
.as-ios-switch:active .as-ios-toggle-track::after { transform: scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.as-ios-switch:active input:checked + .as-ios-toggle-track::after { transform: translateX(20px) scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.as-ios-toggle input:focus-visible + .as-ios-toggle-track { outline: 3px solid var(--accent, #0063dc); outline-offset: 3px; }
.as-ios-inp { flex: 1; width: 100%; min-width: 0; min-height: 44px; padding: 9px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-text); transition: border-color var(--ios-fast) ease; }
.as-ios-inp:focus { border-color: var(--accent, #0063dc); }
.as-ios-inp.as-ios-sm { flex: 0 0 auto; width: 130px; }
.as-ios textarea { resize: vertical; line-height: 1.75; }
.as-ios-fld { display: flex; flex-direction: column; gap: 9px; min-width: 0; }
.as-ios-hint, .as-ios-muted { min-width: 0; color: var(--ios-secondary); font-size: 12px; line-height: 1.75; overflow-wrap: anywhere; }
.as-ios-flow-hint { white-space: normal; max-width: 75ch; }
.as-ios-secret-field { position: relative; flex: 1; min-width: 0; }
.as-ios-secret-field .as-ios-inp { width: 100%; padding-right: 48px; }
.as-ios-secret-field button { position: absolute; inset: 4px 4px 4px auto; width: 36px; display: grid; place-items: center; border: 0; border-radius: 8px; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.as-ios-secret-field button:hover:not(:disabled) { color: var(--accent, #0063dc); background: var(--accent-dim, #e8f1ff); }
.as-ios-secret-field svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.8; }
.as-ios-chips { display: flex; flex-wrap: wrap; gap: 8px; min-width: 0; }
.as-ios-chips.as-ios-scroll { max-height: 190px; overflow-y: auto; padding: 10px; border: 1px solid var(--ios-line); border-radius: 12px; scrollbar-width: thin; scrollbar-color: var(--border-light, #b9bec9) transparent; }
.as-ios-chip { display: inline-flex; align-items: center; gap: 7px; min-height: 40px; padding: 8px 10px; border: 1px solid var(--ios-line); border-radius: 10px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 12px; line-height: 1.5; cursor: pointer; transition: background var(--ios-fast), border-color var(--ios-fast); }
.as-ios-chip:has(input:checked) { color: var(--ios-text); border-color: var(--accent, #0063dc); background: var(--accent-dim, #e8f1ff); }
.as-ios-chip > input { flex: none; width: 17px; height: 17px; margin: 0; accent-color: var(--ios-accent); }
.as-ios-subfilter { padding: 16px; border: 1px solid var(--ios-line); border-radius: 13px; background: var(--ios-inset); }
.as-ios-charts-heading { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.as-ios-rank-picker { padding: 16px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); }
.as-ios-rank-picker > select { flex: 1; }
.as-ios-rank-settings { border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-inset); }
.as-ios-rank-settings summary { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 14px; min-height: 56px; padding: 15px 18px; color: var(--ios-text); font-size: 14px; cursor: pointer; list-style: none; }
.as-ios-rank-settings summary::-webkit-details-marker { display: none; }
.as-ios-rank-settings summary::after { content: ''; width: 7px; height: 7px; margin-left: auto; border-right: 1px solid var(--ios-secondary); border-bottom: 1px solid var(--ios-secondary); transform: rotate(45deg); transition: transform var(--ios-duration) var(--ios-ease); }
.as-ios-rank-settings[open] summary::after { transform: rotate(225deg); }
.as-ios-rank-settings-body { display: flex; flex-direction: column; gap: 16px; padding: 0 12px 12px; }
.as-ios-rank-settings-body .as-ios-card { padding: 16px; background: transparent; border: 0; border-top: 1px solid var(--ios-line); border-radius: 0; }
.as-ios-charts-error, .as-ios-muted.as-ios-err { color: var(--danger, #bd2733); font-size: 12px; line-height: 1.75; overflow-wrap: anywhere; }
.as-ios-charts-load-error { display: flex; flex-direction: column; align-items: flex-start; gap: 12px; padding: 18px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); }
.as-ios-inp[aria-invalid='true'] { border-color: var(--danger, #bd2733); }
.as-ios-button { display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 9px 18px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font-weight: 500; cursor: pointer; }
.as-ios-button:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.as-ios-btn { display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 9px 18px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font-weight: 500; cursor: pointer; }
.as-ios-btn:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.as-ios-btn.as-ios-primary { min-width: 132px; border-color: transparent; background: var(--ios-accent); color: #fff; font-weight: 600; }
.as-ios-primary:hover:not(:disabled) { filter: brightness(1.08); }
.as-ios-btn.as-ios-danger { color: var(--danger, #bd2733); }
.as-ios-btn.as-ios-danger:hover:not(:disabled) { border-color: var(--danger, #bd2733); }
.as-ios-btn.as-ios-xs { min-height: 36px; padding: 6px 11px; font-size: 12px; }
.as-ios button:disabled { opacity: .5; cursor: not-allowed; }
.as-ios-savebar { display: flex; justify-content: flex-end; padding-top: 6px; }
.as-ios-output { margin: 0; padding: 16px; border: 1px solid var(--ios-line); border-radius: 13px; background: var(--ios-inset); color: var(--ios-text); font: inherit; font-size: 12px; line-height: 1.8; white-space: pre-wrap; overflow-wrap: anywhere; }
.as-ios-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(105px, 1fr)); border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); overflow: hidden; }
.as-ios-stat { padding: 16px 18px; border: 0; border-right: 1px solid var(--ios-line); }
.as-ios-stat:last-child { border-right: 0; }
.as-ios-stat-n { font-size: 23px; font-weight: 650; line-height: 1.3; font-variant-numeric: tabular-nums; }
.as-ios-stat-l { margin-top: 4px; color: var(--ios-secondary); font-size: 12px; }
.as-ios-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.as-ios-grow { flex: 1; }
.as-ios-table-wrap { max-width: 100%; min-width: 0; overflow: auto; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); scrollbar-width: thin; scrollbar-color: var(--border-light, #b9bec9) transparent; }
.as-ios-tbl { width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
.as-ios-tbl th, .as-ios-tbl td { padding: 13px 14px; border-bottom: 1px solid var(--ios-line); white-space: nowrap; text-align: left; }
.as-ios-tbl th { background: var(--ios-inset); color: var(--ios-secondary); font-size: 12px; font-weight: 500; }
.as-ios-tbl td { color: var(--ios-text); }
.as-ios-tbl td:first-child { min-width: 140px; max-width: 280px; white-space: normal; overflow-wrap: anywhere; }
.as-ios-tbl td.as-ios-muted { color: var(--ios-secondary); }
.as-ios-tbl tr:last-child td { border-bottom: 0; }
.as-ios-tbl tbody tr:hover { background: var(--ios-inset); }
.as-ios-empty { padding: 40px 24px; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-surface); text-align: center; color: var(--ios-text); }
.as-ios-empty .as-ios-muted { display: inline-block; margin-top: 7px; }
:global(html[data-theme='transparent'] .as-ios-card),
:global(html[data-theme='transparent'] .as-ios-rank-picker),
:global(html[data-theme='transparent'] .as-ios-charts-load-error),
:global(html[data-theme='transparent'] .as-ios-table-wrap),
:global(html[data-theme='transparent'] .as-ios-stats),
:global(html[data-theme='transparent'] .as-ios-empty) { backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); -webkit-backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); }
@container (max-width: 640px) {
  .as-ios { gap: 20px; }
  .as-ios-layout { grid-template-columns: minmax(0, 1fr); gap: 20px; }
  .as-ios-sidebar { flex-direction: row; flex-wrap: wrap; align-items: center; gap: 4px; padding: 5px; border-radius: 16px; }
  .as-ios-side-title { display: none; }
  .as-ios-side-item { flex: 1 1 auto; justify-content: center; min-height: 40px; padding: 8px 11px; font-size: 13px; }
  .as-ios-side-foot { flex: 1 1 100%; margin: 0; padding: 7px 10px; border-top: 0; }
  .as-ios-card { padding: 16px; gap: 14px; }
  .as-ios-grid { grid-template-columns: minmax(0, 1fr); }
  .as-ios-row:not(.as-ios-switch) { flex-wrap: wrap; gap: 10px; }
  .as-ios-row > .as-ios-inp:not(.as-ios-sm), .as-ios-row > .as-ios-secret-field { flex: 1 1 100%; }
  .as-ios-inp { font-size: 16px; }
  .as-ios-savebar .as-ios-primary { width: 100%; }
  .as-ios-toolbar > .as-ios-muted { flex: 1 1 100%; }
  .as-ios-toolbar > .as-ios-grow { display: none; }
  .as-ios-stats { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .as-ios-stat { border-bottom: 1px solid var(--ios-line); padding: 12px; }
  .as-ios-rank-settings summary { padding-inline: 15px; }
  .as-ios-tbl th, .as-ios-tbl td { padding: 12px; }
}
@container (max-width: 360px) {
  .as-ios-tab { padding-inline: 6px; font-size: 13px; }
  .as-ios-chip { max-width: 100%; overflow-wrap: anywhere; }
  .as-ios-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (forced-colors: active) {
  .as-ios-toggle input { position: static; width: 24px; height: 24px; clip-path: none; }
  .as-ios-toggle-track { display: none; }
  .as-ios-tabs::before { border: 2px solid Highlight; }
}
</style>
