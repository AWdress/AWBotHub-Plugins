<script setup>
// AWPulse 色花堂助手 · 配置/管理界面（模块联邦暴露为 ./Config）。
// 平台注入 props { pluginId, host }；host: getConfig/saveConfig/callApi/toast/token。
// 页签：运行状态 / 设置(左分组+右明细) / 记录 / Cookie / 日志。
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

const props = defineProps({
  pluginId: { type: String, required: true },
  host: { type: Object, required: true },
})
const CronInput = computed(() => props.host.ui.CronInput)

const LEGACY_AI_KEYS = ['ai_api_type', 'ai_api_url', 'ai_api_key', 'ai_model', 'ai_temperature', 'ai_max_tokens', 'ai_timeout', 'ai_proxy']

// Discuz 论坛固定的安全提问（值为字符串，与后端一致）。
const SECURITY_QUESTIONS = [
  { v: '0', l: '不设置安全提问' },
  { v: '1', l: '母亲的名字' },
  { v: '2', l: '爷爷的名字' },
  { v: '3', l: '父亲出生的城市' },
  { v: '4', l: '您其中一位老师的名字' },
  { v: '5', l: '您个人计算机的型号' },
  { v: '6', l: '您最喜欢的餐馆名称' },
  { v: '7', l: '驾驶执照最后四位数字' },
]

// 配置分组（左侧导航）。en=对应启用开关键（有则显示启用小圆点）。
const GROUPS = [
  { key: 'account', label: '账号' },
  { key: 'features', label: '功能开关' },
  { key: 'reply', label: '回复设置', en: 'enable_auto_reply' },
  { key: 'autopost', label: '自动发帖', en: 'enable_auto_post' },
  { key: 'ai', label: 'AI 设置', en: 'enable_ai_reply' },
  { key: 'schedule', label: '定时/通知' },
  { key: 'net', label: '代理/浏览器' },
]

// 与后端 DEFAULTS 对齐（深合并，含嵌套对象）。
const DEFAULTS = {
  base_url: 'https://sehuatang.org/', username: '', password: '',
  security_question_id: '0', security_answer: '', headless: true,
  enable_auto_reply: true, enable_daily_checkin: true, enable_smart_reply: true,
  enable_ai_reply: false, enable_ai_post_filter: true, enable_auto_post: false,
  enable_random_delay: false,
  enable_test_mode: false, enable_test_checkin: false, enable_test_reply: false, enable_test_post: false,
  skip_admin_posts: true, max_replies_per_day: 3, reply_interval: [60, 120],
  schedule_cron: '', schedule_times: ['03:00', '09:00', '15:00', '21:00'], schedule_time: '03:00',
  notify: true,
  target_forums: ['fid=141'],
  reply_templates: ['谢谢楼主分享！', '感谢分享，收藏了！'],
  skip_keywords: ['公告', '通知', '规则', '版规', '置顶', '热门', '2024年永久访问本站方法', 'APP下载', '白名单', '邀请码', '访问方法', '屏蔽', '封禁', '违规', '删除', '警告', '发布器', '最新方法', '申诉', '二次验证', '禁止申诉', '高薪', '招聘'],
  skip_prefixes: ['【公告】', '【通知】', '【规则】', '【版规】', '公告:', '通知:', '规则:', '版规:'],
  admin_usernames: ['admin', '管理员', '版主'],
  auto_post: {
    enabled: false, target_fid: 139, category_id: null, post_folder: 'novels', posted_folder: 'posted',
    post_interval: 300, max_posts_per_day: 5, content_preview_length: 500, move_after_post: true, skip_posted_files: true,
  },
  ai_system_prompt: '你是一个论坛用户，需要根据帖子标题和内容生成简短的回复。回复要自然、简洁，不超过50字。',
  ai_reply_reject_markers: '',
  proxy: { enabled: false, http_proxy: '', https_proxy: '', no_proxy: 'localhost,127.0.0.1', use_for_browser: false },
  browser_headers: { user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36', accept_language: 'zh-CN,zh;q=0.9,en;q=0.8' },
}

function deepMerge(base, over) {
  const out = Array.isArray(base) ? [...base] : { ...base }
  for (const k in (over || {})) {
    const bv = base ? base[k] : undefined
    const ov = over[k]
    if (ov && typeof ov === 'object' && !Array.isArray(ov) && bv && typeof bv === 'object' && !Array.isArray(bv)) {
      out[k] = deepMerge(bv, ov)
    } else if (ov !== undefined) {
      out[k] = ov
    }
  }
  return out
}

const tab = ref('run')
const group = ref('account')
const loading = ref(true)
const saving = ref(false)
const running = ref(false)
const stopping = ref(false)
const passwordVisible = ref(false)
const cfg = reactive(JSON.parse(JSON.stringify(DEFAULTS)))

// 运行状态
const status = ref({})
let statusTimer = null
// 记录
const recTab = ref('replies')
const posts = ref([])
const replies = ref([])
const messages = ref({ messages: [], total: 0, unread: 0, timestamp: null })
const recLoading = ref(false)
const refreshingMsg = ref(false)
// Cookie
const cookie = ref({})
const cookieImport = ref('')
// 日志
const logs = ref([])
let logTimer = null
// ── 行文本 <-> 数组（每行一项） ──
function lineModel(key) {
  return computed({
    get: () => (cfg[key] || []).join('\n'),
    set: (v) => { cfg[key] = v.split('\n').map(s => s.trim()).filter(Boolean) },
  })
}
const templatesText = lineModel('reply_templates')
const keywordsText = lineModel('skip_keywords')
const prefixesText = lineModel('skip_prefixes')
const adminsText = lineModel('admin_usernames')
const timesText = lineModel('schedule_times')
const replyMin = computed({ get: () => cfg.reply_interval[0], set: v => { cfg.reply_interval[0] = Number(v) } })
const replyMax = computed({ get: () => cfg.reply_interval[1], set: v => { cfg.reply_interval[1] = Number(v) } })

// 目标版块：已知版块用勾选(fid -> 名称)，另留「自定义」文本框补充列表外的 fid。
const knownForums = computed(() => Object.entries(cfg.forum_names || {}).map(([v, l]) => ({ v, l })))
function toggleForum(fid) {
  const arr = cfg.target_forums || (cfg.target_forums = [])
  const i = arr.indexOf(fid)
  if (i >= 0) arr.splice(i, 1); else arr.push(fid)
}
// 只暴露「不在已知列表里」的额外 fid，避免与勾选互相覆盖。
const customForumsText = computed({
  get: () => (cfg.target_forums || []).filter(f => !(f in (cfg.forum_names || {}))).join('\n'),
  set: (v) => {
    const known = (cfg.target_forums || []).filter(f => f in (cfg.forum_names || {}))
    const custom = v.split('\n').map(s => s.trim()).filter(Boolean)
    cfg.target_forums = [...known, ...custom]
  },
})

onMounted(async () => {
  try {
    const saved = await props.host.getConfig()
    if (saved?.password === '********') saved.password = await props.host.revealSecret('password')
    Object.assign(cfg, deepMerge(DEFAULTS, saved || {}))
    LEGACY_AI_KEYS.forEach(key => delete cfg[key])
    if (cfg.proxy) delete cfg.proxy.use_for_ai
    if (!Array.isArray(cfg.reply_interval) || cfg.reply_interval.length < 2) cfg.reply_interval = [60, 120]
  } catch (e) {
    props.host.toast.error('读取配置失败：' + (e.message || e))
  } finally {
    loading.value = false
  }
  loadStatus()
  statusTimer = setInterval(() => { if (tab.value === 'run') loadStatus() }, 5000)
})
onUnmounted(() => { clearInterval(statusTimer); clearInterval(logTimer) })

async function save() {
  saving.value = true
  try {
    const payload = JSON.parse(JSON.stringify(cfg))
    LEGACY_AI_KEYS.forEach(key => delete payload[key])
    if (payload.proxy) delete payload.proxy.use_for_ai
    await props.host.saveConfig(payload)
    props.host.toast.success('配置已保存（定时任务将随之更新）')
  } catch (e) {
    props.host.toast.error('保存失败：' + (e.message || e))
  } finally {
    saving.value = false
  }
}

// ── 运行状态 ──
async function loadStatus() {
  try {
    status.value = await props.host.callApi('/status')
    cookie.value = status.value.cookie || {}
  } catch (e) { /* 静默 */ }
}
async function runNow() {
  running.value = true
  try {
    const r = await props.host.callApi('/run', { method: 'POST', body: {} })
    if (r.ok === false) props.host.toast.error(r.message || '启动失败')
    else props.host.toast.success('已在后台开始运行')
    setTimeout(loadStatus, 800)
  } catch (e) {
    props.host.toast.error('启动失败：' + (e.message || e))
  } finally {
    running.value = false
  }
}
async function stopNow() {
  stopping.value = true
  try {
    const r = await props.host.callApi('/stop', { method: 'POST', body: {} })
    props.host.toast.success(r.message || '已请求停止')
    setTimeout(loadStatus, 800)
  } catch (e) {
    props.host.toast.error('停止失败：' + (e.message || e))
  } finally {
    stopping.value = false
  }
}

// ── 记录 ──
async function loadRecords(which) {
  recLoading.value = true
  try {
    if (which === 'replies') replies.value = (await props.host.callApi('/replies')).items || []
    else if (which === 'posts') posts.value = (await props.host.callApi('/posts')).items || []
    else if (which === 'messages') messages.value = await props.host.callApi('/messages')
  } catch (e) {
    props.host.toast.error('读取失败：' + (e.message || e))
  } finally {
    recLoading.value = false
  }
}
function switchRec(t) { recTab.value = t; loadRecords(t) }
async function refreshMessages() {
  refreshingMsg.value = true
  try {
    const r = await props.host.callApi('/messages/refresh', { method: 'POST', body: {} })
    if (r.ok) { props.host.toast.success(`已刷新，共 ${r.count} 条（未读 ${r.unread}）`); loadRecords('messages') }
    else props.host.toast.error('刷新失败：' + (r.message || ''))
  } catch (e) {
    props.host.toast.error('刷新失败：' + (e.message || e))
  } finally {
    refreshingMsg.value = false
  }
}

// ── Cookie ──
async function checkCookie() {
  try { cookie.value = await props.host.callApi('/cookie/check') } catch (e) { props.host.toast.error('检查失败：' + (e.message || e)) }
}
async function importCookie() {
  if (!cookieImport.value.trim()) return props.host.toast.error('请先粘贴 storage_state JSON')
  try {
    const r = await props.host.callApi('/cookie/import', { method: 'POST', body: { storage_state: cookieImport.value } })
    if (r.ok) { props.host.toast.success(r.message || '已导入'); cookieImport.value = ''; checkCookie() }
    else props.host.toast.error(r.message || '导入失败')
  } catch (e) { props.host.toast.error('导入失败：' + (e.message || e)) }
}
async function deleteCookie() {
  if (!confirm('确定删除已保存的登录状态？下次运行需重新登录。')) return
  try {
    const r = await props.host.callApi('/cookie/delete', { method: 'POST', body: {} })
    props.host.toast.success(r.message || '已删除'); checkCookie()
  } catch (e) { props.host.toast.error('删除失败：' + (e.message || e)) }
}

// ── 日志 ──
async function loadLogs() {
  try { logs.value = (await props.host.callApi('/logs')).lines || [] } catch (e) { /* 静默 */ }
}
async function clearLogs() {
  try { await props.host.callApi('/logs/clear', { method: 'POST', body: {} }); logs.value = [] } catch (e) { /* 静默 */ }
}

function switchTab(t) {
  tab.value = t
  clearInterval(logTimer); logTimer = null
  if (t === 'run') loadStatus()
  if (t === 'records') loadRecords(recTab.value)
  if (t === 'cookie') checkCookie()
  if (t === 'logs') { loadLogs(); logTimer = setInterval(loadLogs, 4000) }
}
</script>

<template>
  <IosSettings>
  <div class="ap-ios-awp">
    <div v-if="loading" class="ap-ios-muted">加载配置…</div>
    <template v-else>
      <div class="ap-ios-tabs">
        <button :class="['ap-ios-tab', { on: tab === 'run' }]" @click="switchTab('run')">运行状态</button>
        <button :class="['ap-ios-tab', { on: tab === 'settings' }]" @click="switchTab('settings')">设置</button>
        <button :class="['ap-ios-tab', { on: tab === 'records' }]" @click="switchTab('records')">记录</button>
        <button :class="['ap-ios-tab', { on: tab === 'cookie' }]" @click="switchTab('cookie')">Cookie</button>
        <button :class="['ap-ios-tab', { on: tab === 'logs' }]" @click="switchTab('logs')">日志</button>
      </div>

      <!-- ============ 运行状态 ============ -->
      <div v-show="tab === 'run'" class="ap-ios-pane">
        <section class="ap-ios-card">
          <div class="ap-ios-card-h">运行</div>
          <div class="ap-ios-run-row">
            <span :class="['ap-ios-badge', status.running ? 'ap-ios-live' : 'ap-ios-idle']">{{ status.running ? '运行中 · ' + (status.task || '') : '空闲' }}</span>
            <span class="ap-ios-grow"></span>
            <button class="ap-ios-btn ap-ios-primary" :disabled="running || status.running" @click="runNow">{{ status.running ? '进行中…' : (running ? '启动中…' : '立即运行一次') }}</button>
            <button class="ap-ios-btn ap-ios-danger" :disabled="stopping || !status.running" @click="stopNow">{{ stopping ? '停止中…' : '停止' }}</button>
            <button class="ap-ios-btn" @click="loadStatus">刷新</button>
          </div>
          <div class="ap-ios-metaline">
            <span class="ap-ios-muted">上次开始：{{ status.started_at || '—' }}</span>
            <span class="ap-ios-muted">上次结束：{{ status.finished_at || '—' }}</span>
            <span class="ap-ios-muted">计划：{{ status.schedule || '未设置' }}</span>
            <span class="ap-ios-muted">下次运行：{{ (status.next_runs || []).join('、') || '未注册' }}</span>
          </div>
          <pre v-if="status.last_result" class="ap-ios-output">{{ status.last_result }}</pre>
        </section>

        <div class="ap-ios-stats">
          <div class="ap-ios-stat"><div class="ap-ios-stat-n">{{ (status.today && status.today.reply_count) || 0 }}</div><div class="ap-ios-stat-l">今日回复</div></div>
          <div class="ap-ios-stat"><div class="ap-ios-stat-n">{{ (status.today && status.today.checkin_success) ? '✓' : '—' }}</div><div class="ap-ios-stat-l">今日签到</div></div>
          <div class="ap-ios-stat"><div class="ap-ios-stat-n">{{ (status.today && status.today.post_count) || 0 }}</div><div class="ap-ios-stat-l">今日发帖</div></div>
          <div class="ap-ios-stat"><div class="ap-ios-stat-n" :style="{ color: cookie.valid ? 'var(--success, #28a56a)' : 'var(--warning, #b58118)' }">{{ cookie.exists ? (cookie.valid ? '有效' : '过期') : '无' }}</div><div class="ap-ios-stat-l">登录状态</div></div>
        </div>

        <section v-if="status.user_info && status.user_info.user_group" class="ap-ios-card">
          <div class="ap-ios-card-h">账号信息</div>
          <div class="ap-ios-metaline">
            <span class="ap-ios-muted">用户组：{{ status.user_info.user_group }}</span>
            <span class="ap-ios-muted">积分：{{ status.user_info.credits }}</span>
            <span class="ap-ios-muted">花币：{{ status.user_info.money }}</span>
          </div>
        </section>
      </div>

      <!-- ============ 设置：左分组 + 右明细 ============ -->
      <div v-show="tab === 'settings'" class="ap-ios-layout">
        <aside class="ap-ios-sidebar">
          <div class="ap-ios-side-title">设置分组</div>
          <button v-for="g in GROUPS" :key="g.key" :class="['ap-ios-side-item', { on: group === g.key }]" @click="group = g.key">
            <span>{{ g.label }}</span>
            <span v-if="g.en && cfg[g.en]" class="ap-ios-dot"></span>
          </button>
        </aside>

        <div class="ap-ios-detail">
          <!-- 账号 -->
          <template v-if="group === 'account'">
            <h3 class="ap-ios-det-title">论坛账号</h3>
            <section class="ap-ios-card">
              <div class="ap-ios-grid">
                <label class="ap-ios-row"><span>站点地址</span><input v-model="cfg.base_url" class="ap-ios-inp" /></label>
                <label class="ap-ios-row"><span>用户名</span><input v-model="cfg.username" class="ap-ios-inp" /></label>
                <label class="ap-ios-row"><span>密码</span><div class="ap-ios-secret-field"><input v-model="cfg.password" class="ap-ios-inp" :type="passwordVisible ? 'text' : 'password'" autocomplete="current-password" /><button type="button" :aria-label="passwordVisible ? '隐藏密码' : '显示密码'" @click="passwordVisible = !passwordVisible"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div></label>
                <label class="ap-ios-row"><span>安全提问</span><select v-model="cfg.security_question_id" class="ap-ios-inp"><option v-for="o in SECURITY_QUESTIONS" :key="o.v" :value="o.v">{{ o.l }}</option></select></label>
                <label class="ap-ios-row"><span>安全答案</span><input v-model="cfg.security_answer" class="ap-ios-inp" type="text" /></label>
              </div>
              <p class="ap-ios-tip">建议先在「Cookie」页导入已登录的 storage_state，可减少触发 Cloudflare 验证。容器内浏览器恒为无头(headless)模式。</p>
            </section>
          </template>

          <!-- 功能开关 -->
          <template v-else-if="group === 'features'">
            <h3 class="ap-ios-det-title">功能开关</h3>
            <section class="ap-ios-card">
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.enable_daily_checkin" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>每日签到</span></label>
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.enable_auto_reply" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>自动回复</span></label>
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.enable_smart_reply" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>智能回复（按帖子特征选模板/规则）</span></label>
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.enable_ai_reply" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>AI 回复（使用平台统一 AI）</span></label>
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.enable_ai_post_filter" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>AI 帖子类型识别/过滤</span></label>
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.enable_auto_post" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>自动发帖</span></label>
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.skip_admin_posts" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>跳过管理员/版主帖子</span></label>
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.enable_random_delay" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>随机延迟（更拟人）</span></label>
            </section>
            <section class="ap-ios-card">
              <div class="ap-ios-card-h">测试模式（只跑单个动作，用于验证浏览器链路）</div>
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.enable_test_mode" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>总测试模式（签到+回复+发帖各测一次）</span></label>
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.enable_test_checkin" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>仅测试签到</span></label>
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.enable_test_reply" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>仅测试回复</span></label>
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.enable_test_post" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>仅测试发帖</span></label>
            </section>
          </template>

          <!-- 回复设置 -->
          <template v-else-if="group === 'reply'">
            <h3 class="ap-ios-det-title">回复设置</h3>
            <section class="ap-ios-card">
              <div class="ap-ios-grid">
                <label class="ap-ios-row"><span>每日上限</span><input v-model.number="cfg.max_replies_per_day" class="ap-ios-inp" type="number" /></label>
                <label class="ap-ios-row"><span>间隔(秒)</span><input v-model="replyMin" class="ap-ios-inp" type="number" /><span class="ap-ios-hint">~</span><input v-model="replyMax" class="ap-ios-inp" type="number" /></label>
              </div>
              <div class="ap-ios-fld"><span class="ap-ios-lbl">目标版块</span>
                <div class="ap-ios-chips">
                  <label v-for="o in knownForums" :key="o.v" class="ap-ios-chip"><input type="checkbox" :checked="(cfg.target_forums || []).includes(o.v)" @change="toggleForum(o.v)" />{{ o.l }}<span class="ap-ios-fid">{{ o.v }}</span></label>
                </div>
              </div>
              <label class="ap-ios-row ap-ios-top"><span>自定义版块</span><textarea v-model="customForumsText" class="ap-ios-inp" rows="2" placeholder="列表外的版块，每行一个，如 fid=999"></textarea></label>
            </section>
            <section class="ap-ios-card">
              <div class="ap-ios-card-h">回复模板（智能/AI 关闭时随机取用）</div>
              <textarea v-model="templatesText" class="ap-ios-inp" rows="6" placeholder="每行一条模板"></textarea>
            </section>
            <section class="ap-ios-card">
              <div class="ap-ios-card-h">过滤</div>
              <label class="ap-ios-row ap-ios-top"><span>跳过关键词</span><textarea v-model="keywordsText" class="ap-ios-inp" rows="4" placeholder="每行一个，标题含则跳过"></textarea></label>
              <label class="ap-ios-row ap-ios-top"><span>跳过前缀</span><textarea v-model="prefixesText" class="ap-ios-inp" rows="2" placeholder="每行一个"></textarea></label>
              <label class="ap-ios-row ap-ios-top"><span>管理员名</span><textarea v-model="adminsText" class="ap-ios-inp" rows="2" placeholder="每行一个用户名"></textarea></label>
            </section>
          </template>

          <!-- 自动发帖 -->
          <template v-else-if="group === 'autopost'">
            <h3 class="ap-ios-det-title">自动发帖</h3>
            <section class="ap-ios-card">
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.auto_post.enabled" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>启用自动发帖（同时需打开「功能开关」里的自动发帖）</span></label>
              <div class="ap-ios-grid">
                <label class="ap-ios-row"><span>目标版块fid</span><input v-model.number="cfg.auto_post.target_fid" class="ap-ios-inp" type="number" /></label>
                <label class="ap-ios-row"><span>分类ID</span><input v-model="cfg.auto_post.category_id" class="ap-ios-inp" placeholder="留空=不选" /></label>
                <label class="ap-ios-row"><span>待发文件夹</span><input v-model="cfg.auto_post.post_folder" class="ap-ios-inp" /></label>
                <label class="ap-ios-row"><span>已发文件夹</span><input v-model="cfg.auto_post.posted_folder" class="ap-ios-inp" /></label>
                <label class="ap-ios-row"><span>发帖间隔(秒)</span><input v-model.number="cfg.auto_post.post_interval" class="ap-ios-inp" type="number" /></label>
                <label class="ap-ios-row"><span>每日上限</span><input v-model.number="cfg.auto_post.max_posts_per_day" class="ap-ios-inp" type="number" /></label>
              </div>
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.auto_post.move_after_post" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>发布后移动到已发文件夹</span></label>
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.auto_post.skip_posted_files" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>跳过已发布过的文件</span></label>
              <p class="ap-ios-tip">待发文件放在插件数据目录的 <code>novels/</code> 下（.txt/.pdf/.doc/.docx/.epub/.mobi）。</p>
            </section>
          </template>

          <!-- AI -->
          <template v-else-if="group === 'ai'">
            <h3 class="ap-ios-det-title">平台 AI</h3>
            <section class="ap-ios-card">
              <p class="ap-ios-tip">AI 服务、模型、密钥、超时和代理统一由平台「系统设置 → AI 服务」管理。本插件只保留业务提示词。</p>
              <label class="ap-ios-row ap-ios-top"><span>系统提示词</span><textarea v-model="cfg.ai_system_prompt" class="ap-ios-inp" rows="4"></textarea></label>
              <label class="ap-ios-row ap-ios-top"><span>自定义回复拦截词</span><textarea v-model="cfg.ai_reply_reject_markers" class="ap-ios-inp" rows="5" placeholder="一行一个或用逗号分隔&#10;例如：无法检索&#10;作为 AI"></textarea></label>
              <p class="ap-ios-tip">命中任意自定义词时，AI 回复不会发送，并自动改用本地规则回复。自定义词会与内置拒答审核规则合并。</p>
            </section>
          </template>

          <!-- 定时/通知 -->
          <template v-else-if="group === 'schedule'">
            <h3 class="ap-ios-det-title">定时与通知</h3>
            <section class="ap-ios-card">
              <label class="ap-ios-row"><span>Cron</span><component :is="CronInput" v-model="cfg.schedule_cron" /></label>
              <label class="ap-ios-row ap-ios-top"><span>每日时刻</span><textarea v-model="timesText" class="ap-ios-inp" rows="4" placeholder="每行一个 HH:MM，如 03:00"></textarea></label>
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.notify" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>运行结果推送通知</span></label>
              <p class="ap-ios-tip">优先使用 Cron；Cron 留空时按「每日时刻」逐个定时。保存后定时任务自动更新。</p>
            </section>
          </template>

          <!-- 代理/浏览器 -->
          <template v-else-if="group === 'net'">
            <h3 class="ap-ios-det-title">代理与浏览器</h3>
            <section class="ap-ios-card">
              <div class="ap-ios-card-h">代理</div>
              <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.proxy.enabled" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>启用自定义代理（关闭则出站默认走平台代理）</span></label>
              <template v-if="cfg.proxy.enabled">
                <div class="ap-ios-grid">
                  <label class="ap-ios-row"><span>HTTP</span><input v-model="cfg.proxy.http_proxy" class="ap-ios-inp" placeholder="http://127.0.0.1:7890" /></label>
                  <label class="ap-ios-row"><span>HTTPS</span><input v-model="cfg.proxy.https_proxy" class="ap-ios-inp" placeholder="http://127.0.0.1:7890" /></label>
                  <label class="ap-ios-row"><span>no_proxy</span><input v-model="cfg.proxy.no_proxy" class="ap-ios-inp" /></label>
                </div>
                <label class="ap-ios-row ap-ios-switch"><input v-model="cfg.proxy.use_for_browser" type="checkbox" /><span class="ap-ios-track" aria-hidden="true"><span></span></span><span>用于浏览器</span></label>
              </template>
            </section>
            <section class="ap-ios-card">
              <div class="ap-ios-card-h">浏览器指纹</div>
              <label class="ap-ios-row ap-ios-top"><span>User-Agent</span><textarea v-model="cfg.browser_headers.user_agent" class="ap-ios-inp" rows="2"></textarea></label>
              <label class="ap-ios-row"><span>Accept-Language</span><input v-model="cfg.browser_headers.accept_language" class="ap-ios-inp" /></label>
            </section>
          </template>

          <div class="ap-ios-savebar"><button class="ap-ios-btn ap-ios-primary ap-ios-lg" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存配置' }}</button></div>
        </div>
      </div>

      <!-- ============ 记录 ============ -->
      <div v-show="tab === 'records'" class="ap-ios-pane">
        <div class="ap-ios-subtabs">
          <button :class="['ap-ios-stab', { on: recTab === 'replies' }]" @click="switchRec('replies')">回复记录</button>
          <button :class="['ap-ios-stab', { on: recTab === 'posts' }]" @click="switchRec('posts')">发帖记录</button>
          <button :class="['ap-ios-stab', { on: recTab === 'messages' }]" @click="switchRec('messages')">论坛消息</button>
        </div>
        <div class="ap-ios-toolbar">
          <span v-if="recTab === 'messages'" class="ap-ios-muted">未读 {{ messages.unread || 0 }} · 共 {{ messages.total || 0 }} · {{ messages.timestamp || '未刷新' }}</span>
          <span class="ap-ios-grow"></span>
          <button class="ap-ios-btn" @click="loadRecords(recTab)">刷新列表</button>
          <button v-if="recTab === 'messages'" class="ap-ios-btn ap-ios-primary" :disabled="refreshingMsg" @click="refreshMessages">{{ refreshingMsg ? '抓取中…' : '登录抓取最新' }}</button>
        </div>
        <div v-if="recLoading" class="ap-ios-muted">加载中…</div>
        <template v-else>
          <div class="ap-ios-table-scroll">
          <table v-if="recTab === 'replies'" class="ap-ios-tbl">
            <thead><tr><th>帖子</th><th>回复内容</th><th>时间</th></tr></thead>
            <tbody>
              <tr v-for="(r, i) in replies" :key="i"><td><a :href="r.url" target="_blank">{{ r.title || '—' }}</a></td><td>{{ r.content }}</td><td class="ap-ios-muted">{{ r.time }}</td></tr>
              <tr v-if="!replies.length"><td colspan="3" class="ap-ios-empty">暂无回复记录</td></tr>
            </tbody>
          </table>
          <table v-else-if="recTab === 'posts'" class="ap-ios-tbl">
            <thead><tr><th>标题</th><th>文件</th><th>时间</th></tr></thead>
            <tbody>
              <tr v-for="(p, i) in posts" :key="i"><td><a :href="p.url" target="_blank">{{ p.title || '—' }}</a></td><td class="ap-ios-muted">{{ p.file }}</td><td class="ap-ios-muted">{{ p.time }}</td></tr>
              <tr v-if="!posts.length"><td colspan="3" class="ap-ios-empty">暂无发帖记录</td></tr>
            </tbody>
          </table>
          <table v-else class="ap-ios-tbl">
            <thead><tr><th>标题</th><th>内容</th><th>时间</th></tr></thead>
            <tbody>
              <tr v-for="(m, i) in messages.messages" :key="i"><td>{{ m.title || '—' }}<span v-if="m.is_read === false" class="ap-ios-dot" style="margin-left:6px"></span></td><td>{{ m.content }}</td><td class="ap-ios-muted">{{ m.time }}</td></tr>
              <tr v-if="!messages.messages.length"><td colspan="3" class="ap-ios-empty">暂无消息（点「登录抓取最新」拉取）</td></tr>
            </tbody>
          </table>
          </div>
        </template>
      </div>

      <!-- ============ Cookie ============ -->
      <div v-show="tab === 'cookie'" class="ap-ios-pane">
        <section class="ap-ios-card">
          <div class="ap-ios-card-h">当前登录状态</div>
          <div class="ap-ios-run-row">
            <span :class="['ap-ios-badge', cookie.valid ? 'ap-ios-live' : 'ap-ios-idle']">{{ cookie.message || '未知' }}</span>
            <span v-if="cookie.cookie_count" class="ap-ios-muted">{{ cookie.cookie_count }} 个 cookie</span>
            <span class="ap-ios-grow"></span>
            <button class="ap-ios-btn" @click="checkCookie">重新检查</button>
            <button class="ap-ios-btn ap-ios-danger" :disabled="!cookie.exists" @click="deleteCookie">删除登录状态</button>
          </div>
        </section>
        <section class="ap-ios-card">
          <div class="ap-ios-card-h">导入 storage_state</div>
          <p class="ap-ios-tip">从本地浏览器/AWPulse 导出的 <code>storage_state.json</code> 全文粘贴到下方导入，可跳过账号登录、降低 Cloudflare 触发。</p>
          <textarea v-model="cookieImport" class="ap-ios-inp ap-ios-json" rows="8" placeholder='粘贴 {"cookies":[...],"origins":[...]} JSON'></textarea>
          <div class="ap-ios-savebar"><button class="ap-ios-btn ap-ios-primary" @click="importCookie">导入</button></div>
        </section>
      </div>

      <!-- ============ 日志 ============ -->
      <div v-show="tab === 'logs'" class="ap-ios-pane">
        <div class="ap-ios-toolbar">
          <span class="ap-ios-muted">实时日志（每 4 秒刷新，最多 800 行）</span>
          <span class="ap-ios-grow"></span>
          <button class="ap-ios-btn" @click="loadLogs">刷新</button>
          <button class="ap-ios-btn ap-ios-danger" @click="clearLogs">清空</button>
        </div>
        <pre class="ap-ios-logbox">{{ logs.length ? logs.join('\n') : '暂无日志' }}</pre>
      </div>
    </template>
  </div>

  </IosSettings>
</template>

<style scoped>
.ap-ios-awp { display: flex; flex-direction: column; gap: 24px; container-type: inline-size; color: var(--ios-text); }
.ap-ios-tabs { display: flex; gap: 4px; padding: 4px; width: fit-content; max-width: 100%; overflow-x: auto; overscroll-behavior-x: contain; scrollbar-width: none; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-inset); }
.ap-ios-tabs::-webkit-scrollbar { display: none; }
.ap-ios-tab { flex: 1 0 auto; min-height: 40px; padding: 9px 18px; border: 1px solid transparent; border-radius: 13px; background: transparent; color: var(--ios-secondary); white-space: nowrap; font: inherit; font-size: 13px; font-weight: 600; cursor: pointer; transition: background var(--ios-duration) var(--ios-ease), color var(--ios-fast) ease, box-shadow var(--ios-duration) ease; }
.ap-ios-tab.on { background: var(--ios-surface); border-color: var(--ios-line); color: var(--ios-text); box-shadow: 0 2px 6px color-mix(in srgb, var(--ios-text) 6%, transparent); }
.ap-ios-pane { display: flex; flex-direction: column; gap: 18px; min-width: 0; }
.ap-ios-card { display: flex; flex-direction: column; gap: 16px; min-width: 0; padding: 20px; border: 1px solid var(--ios-line); border-radius: 24px; background: var(--ios-surface); }
.ap-ios-card-h { color: var(--ios-text); font-size: 13px; font-weight: 650; line-height: 1.55; }
.ap-ios-run-row { display: flex; flex-wrap: wrap; align-items: center; gap: 9px; min-width: 0; }
.ap-ios-badge { display: inline-flex; align-items: center; min-height: 30px; max-width: 100%; padding: 5px 12px; border-radius: 30px; border: 1px solid var(--ios-line); background: var(--ios-inset); color: var(--ios-secondary); font-size: 12px; line-height: 1.5; overflow-wrap: anywhere; }
.ap-ios-badge.ap-ios-live { color: var(--success, #28a56a); border-color: color-mix(in srgb, var(--success, #28a56a) 20%, transparent); background: color-mix(in srgb, var(--success, #28a56a) 8%, transparent); }
.ap-ios-badge.ap-ios-live::before { content: ''; flex: 0 0 5px; width: 5px; height: 5px; margin-right: 7px; border-radius: 50%; background: currentColor; }
.ap-ios-metaline { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 20px; padding-top: 2px; }
.ap-ios-metaline > span { min-width: 0; overflow-wrap: anywhere; }
.ap-ios-output { margin: 0; padding: 15px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-inset); color: var(--ios-text); font: 12px/1.8 ui-monospace, SFMono-Regular, Consolas, monospace; white-space: pre-wrap; overflow-wrap: anywhere; }
.ap-ios-stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.ap-ios-stat { display: flex; flex-direction: column; justify-content: space-between; gap: 13px; min-width: 0; padding: 20px; border: 1px solid var(--ios-line); border-radius: 21px; background: var(--ios-surface); }
.ap-ios-stat-n { color: var(--ios-text); font-size: 29px; line-height: 1.2; font-weight: 650; letter-spacing: -.04em; font-variant-numeric: tabular-nums; }
.ap-ios-stat-l { color: var(--ios-secondary); font-size: 11px; line-height: 1.4; }
.ap-ios-layout { display: grid; grid-template-columns: 158px minmax(0, 1fr); align-items: start; gap: 28px; }
.ap-ios-sidebar { display: flex; flex-direction: column; gap: 4px; padding: 8px; border: 1px solid var(--ios-line); border-radius: 22px; background: var(--ios-inset); }
.ap-ios-side-title { padding: 8px 10px; color: var(--ios-secondary); font-size: 11px; font-weight: 600; letter-spacing: .04em; }
.ap-ios-side-item { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; min-height: 44px; padding: 10px 12px; border: 1px solid transparent; border-radius: 14px; background: transparent; color: var(--ios-secondary); font: inherit; font-size: 13px; text-align: left; cursor: pointer; transition: color var(--ios-fast) ease, background var(--ios-duration) var(--ios-ease); }
.ap-ios-side-item:hover { background: var(--ios-control); color: var(--ios-text); }
.ap-ios-side-item.on { background: var(--ios-surface); border-color: var(--ios-line); color: var(--ios-accent-text); font-weight: 600; box-shadow: 0 2px 8px color-mix(in srgb, var(--ios-text) 4%, transparent); }
.ap-ios-dot { display: inline-block; flex: 0 0 6px; width: 6px; height: 6px; border-radius: 50%; background: var(--success, #28a56a); vertical-align: middle; }
.ap-ios-detail { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.ap-ios-det-title { margin: 0; padding: 2px 4px; color: var(--ios-text); font-size: 19px; line-height: 1.4; font-weight: 650; letter-spacing: -.025em; }
.ap-ios-detail .ap-ios-card { gap: 0; padding: 0 20px; overflow: hidden; }
.ap-ios-detail .ap-ios-card-h { padding: 18px 0 12px; color: var(--ios-secondary); font-size: 12px; }
.ap-ios-row { display: flex; align-items: center; gap: 12px; min-width: 0; min-height: 70px; padding: 14px 0; border-top: 1px solid var(--ios-line); }
.ap-ios-row > span:first-child { flex: 0 0 90px; font-size: 13px; line-height: 1.55; color: var(--ios-text); }
.ap-ios-card > .ap-ios-row:first-child, .ap-ios-card-h + .ap-ios-row { border-top: 0; }
.ap-ios-row.ap-ios-top { display: grid; grid-template-columns: minmax(0, 1fr); gap: 9px; }
.ap-ios-row.ap-ios-top > span:first-child { flex-basis: auto; }
.ap-ios-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 22px; }
.ap-ios-grid .ap-ios-row { flex-wrap: wrap; gap: 8px; }
.ap-ios-grid .ap-ios-row > span:first-child { flex: 1 0 100%; }
.ap-ios-inp { flex: 1; min-width: 0; width: 100%; min-height: 42px; padding: 10px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-control); color: var(--ios-text); font: inherit; font-size: 13px; transition: border-color var(--ios-fast) ease, box-shadow var(--ios-fast) ease; }
.ap-ios-inp::placeholder { color: var(--ios-secondary); opacity: .8; }
textarea.ap-ios-inp { min-height: 82px; resize: vertical; line-height: 1.7; }
select.ap-ios-inp { padding-right: 28px; cursor: pointer; }
.ap-ios-card > textarea.ap-ios-inp { margin-bottom: 18px; }
.ap-ios-card > textarea.ap-ios-inp:last-child { margin-bottom: 0; }
.ap-ios-detail .ap-ios-card > textarea.ap-ios-inp:last-child { margin-bottom: 18px; }
.ap-ios-hint { flex: 0 0 auto; color: var(--ios-secondary); font-size: 12px; }
.ap-ios-secret-field { position: relative; flex: 1; min-width: 0; }
.ap-ios-secret-field .ap-ios-inp { padding-right: 46px; }
.ap-ios-secret-field button { position: absolute; inset: 4px 4px 4px auto; width: 34px; min-height: 34px; display: grid; place-items: center; border: 0; border-radius: 9px; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.ap-ios-secret-field button:hover { color: var(--ios-accent-text); background: color-mix(in srgb, var(--ios-accent) 9%, transparent); }
.ap-ios-secret-field svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.8; }
.ap-ios-switch { position: relative; justify-content: space-between; min-height: 66px; }
.ap-ios-switch > input { position: absolute; inset-inline-end: 0; width: 50px; height: 30px; margin: 0; opacity: 0; z-index: 2; cursor: pointer; }
.ap-ios-switch > span:last-child { order: -1; flex: 1; min-width: 0; color: var(--ios-text); font-size: 13px; line-height: 1.6; }
.ap-ios-track { position: relative; flex: 0 0 50px; width: 50px; height: 30px; padding: 3px; border: 1px solid color-mix(in srgb, var(--ios-text) 5%, transparent); border-radius: 20px; background: color-mix(in srgb, var(--ios-text) 18%, transparent); transition: background var(--ios-duration) var(--ios-ease); }
.ap-ios-track > span { display: block; width: 24px; height: 24px; margin: -1px; border-radius: 50%; background: #fff; box-shadow: 0 2px 5px #0002; transition: transform var(--ios-duration) var(--ios-ease); }
.ap-ios-switch > input:checked + .ap-ios-track { background: var(--ios-accent); }
.ap-ios-switch > input:checked + .ap-ios-track > span { transform: translateX(20px); }
.ap-ios-switch > input:focus-visible + .ap-ios-track { outline: 3px solid var(--ios-accent-text); outline-offset: 3px; }
.ap-ios-fld { display: flex; flex-direction: column; gap: 12px; padding: 15px 0 19px; border-top: 1px solid var(--ios-line); }
.ap-ios-lbl { color: var(--ios-text); font-size: 13px; }
.ap-ios-chips { display: flex; flex-wrap: wrap; gap: 7px; }
.ap-ios-chip { display: inline-flex; align-items: center; flex-wrap: wrap; gap: 7px; min-height: 38px; padding: 8px 10px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-control); color: var(--ios-secondary); font-size: 12px; line-height: 1.4; cursor: pointer; transition: color var(--ios-fast) ease, background var(--ios-fast) ease; }
.ap-ios-chip:has(input:checked) { color: var(--ios-accent-text); border-color: color-mix(in srgb, var(--ios-accent) 24%, var(--ios-line)); background: color-mix(in srgb, var(--ios-accent) 7%, transparent); }
.ap-ios-chip input { width: 15px; height: 15px; margin: 0; accent-color: var(--ios-accent); cursor: pointer; }
.ap-ios-fid { color: var(--ios-secondary); font-size: 10px; font-variant-numeric: tabular-nums; }
.ap-ios-tip { margin: 0; color: var(--ios-secondary); font-size: 12px; line-height: 1.75; overflow-wrap: anywhere; }
.ap-ios-detail .ap-ios-tip { padding: 14px 0 18px; }
.ap-ios-tip code { padding: 2px 5px; border: 1px solid var(--ios-line); border-radius: 5px; background: var(--ios-inset); color: var(--ios-text); font-size: 11px; }
.ap-ios-btn { min-height: 40px; padding: 9px 16px; border: 1px solid var(--ios-line); border-radius: 13px; background: var(--ios-control); color: var(--ios-text); font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; transition: color var(--ios-fast) ease, background var(--ios-fast) ease, opacity var(--ios-fast) ease; }
.ap-ios-btn:hover { color: var(--ios-accent-text); border-color: color-mix(in srgb, var(--ios-accent) 35%, var(--ios-line)); }
.ap-ios-btn.ap-ios-primary { background: var(--ios-accent); border-color: transparent; color: #fff; }
.ap-ios-btn.ap-ios-danger { color: var(--danger, #d94a53); }
.ap-ios-btn.ap-ios-lg { min-width: 136px; }
.ap-ios-btn:disabled { opacity: .45; cursor: not-allowed; }
.ap-ios-savebar { position: sticky; bottom: 0; display: flex; justify-content: flex-end; gap: 10px; padding: 14px 0 3px; border-radius: 0 0 16px 16px; background: var(--ios-inset); }
.ap-ios-card .ap-ios-savebar { position: static; padding: 0; background: transparent; }
.ap-ios-subtabs { display: flex; flex-wrap: wrap; gap: 7px; }
.ap-ios-stab { min-height: 38px; padding: 8px 14px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-control); color: var(--ios-secondary); font: inherit; font-size: 12px; cursor: pointer; transition: background var(--ios-fast) ease, color var(--ios-fast) ease; }
.ap-ios-stab.on { color: var(--ios-accent-text); border-color: color-mix(in srgb, var(--ios-accent) 25%, var(--ios-line)); background: color-mix(in srgb, var(--ios-accent) 8%, transparent); }
.ap-ios-toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 9px; }
.ap-ios-grow { flex: 1; }
.ap-ios-table-scroll { width: 100%; min-width: 0; overflow-x: auto; overscroll-behavior-x: contain; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.ap-ios-tbl { width: 100%; min-width: 550px; table-layout: fixed; border-collapse: collapse; color: var(--ios-text); font-size: 12px; line-height: 1.7; }
.ap-ios-tbl th, .ap-ios-tbl td { padding: 13px 17px; border-bottom: 1px solid var(--ios-line); text-align: left; vertical-align: top; overflow-wrap: anywhere; }
.ap-ios-tbl th { color: var(--ios-secondary); background: var(--ios-inset); font-size: 11px; font-weight: 500; }
.ap-ios-tbl th:first-child { width: 32%; }
.ap-ios-tbl th:last-child { width: 155px; }
.ap-ios-tbl tr:last-child td { border-bottom: 0; }
.ap-ios-tbl a { color: var(--ios-accent-text); text-decoration: none; }
.ap-ios-tbl a:hover { text-decoration: underline; text-underline-offset: 3px; }
.ap-ios-tbl tbody tr:hover { background: color-mix(in srgb, var(--ios-accent) 3%, transparent); }
.ap-ios-tbl td.ap-ios-empty { padding: 42px 18px; color: var(--ios-secondary); text-align: center; }
.ap-ios-muted { color: var(--ios-secondary); font-size: 12px; line-height: 1.65; }
.ap-ios-json { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; }
.ap-ios-logbox { margin: 0; min-height: 200px; max-height: 460px; overflow-y: auto; overscroll-behavior: contain; padding: 18px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-inset); color: var(--ios-text); white-space: pre-wrap; overflow-wrap: anywhere; font: 11px/1.85 ui-monospace, SFMono-Regular, Consolas, monospace; }
:global(html[data-theme='transparent'] .ap-ios-card),
:global(html[data-theme='transparent'] .ap-ios-stat),
:global(html[data-theme='transparent'] .ap-ios-table-scroll) { box-shadow: inset 0 1px 0 color-mix(in srgb, var(--ios-text) 5%, transparent); }
@container (max-width: 660px) {
  .ap-ios-inp { font-size: 16px; }
  .ap-ios-layout { grid-template-columns: minmax(0, 1fr); gap: 22px; }
  .ap-ios-sidebar { flex-direction: row; flex-wrap: wrap; gap: 5px; padding: 6px; border-radius: 18px; }
  .ap-ios-side-title { display: none; }
  .ap-ios-side-item { flex: 1 0 auto; width: auto; justify-content: center; min-height: 38px; padding: 8px 11px; font-size: 12px; }
  .ap-ios-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .ap-ios-metaline { grid-template-columns: minmax(0, 1fr); }
  .ap-ios-row { flex-wrap: wrap; align-items: stretch; gap: 9px; }
  .ap-ios-row > span:first-child { flex: 1 0 100%; }
  .ap-ios-grid { grid-template-columns: minmax(0, 1fr); }
  .ap-ios-switch { flex-wrap: nowrap; align-items: center; }
  .ap-ios-switch > span:last-child { flex-basis: auto; }
  .ap-ios-card, .ap-ios-detail .ap-ios-card { padding-left: 16px; padding-right: 16px; border-radius: 20px; }
  .ap-ios-run-row > .ap-ios-grow { display: none; }
  .ap-ios-run-row > .ap-ios-badge { margin-right: auto; }
  .ap-ios-toolbar > .ap-ios-muted { flex: 1 0 100%; }
}
@container (max-width: 420px) {
  .ap-ios-tab { padding-inline: 13px; font-size: 12px; }
  .ap-ios-stat { padding: 17px; }
  .ap-ios-stat-n { font-size: 26px; }
  .ap-ios-run-row { gap: 7px; }
  .ap-ios-run-row > .ap-ios-badge { flex: 1 0 100%; margin-bottom: 4px; }
  .ap-ios-run-row > .ap-ios-btn { flex: 1; padding-inline: 11px; }
  .ap-ios-toolbar .ap-ios-grow { display: none; }
}
</style>
