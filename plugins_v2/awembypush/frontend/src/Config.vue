<script setup>
// AWEmbyPush · 配置/管理界面（模块联邦暴露为 ./Config）。
// 平台注入 props { pluginId, host }；host: getConfig/saveConfig/callApi/toast/token。
// 两个页签：配置（左侧 6 分组 + 右侧明细）/ 最近推送（战绩 + 测试推送）。
// 注：Webhook 入站地址由平台在配置弹窗底部独立展示，不在本组件内。
import { ref, reactive, onMounted } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

const props = defineProps({
  pluginId: { type: String, required: true },
  host: { type: Object, required: true },
})

const DEFAULTS = {
  enable_tmdb: true, tmdb_api_key: '', tmdb_api_domain: 'api.themoviedb.org',
  tmdb_image_domain: 'image.tmdb.org', emby_server_url: '',
  dedup_window: 60, episode_cache_timeout: 30,
  enable_watch_link: false, watch_link_type: 'server', link_redirect_prefix: '',
  tg_bot_token: '', tg_chat_id: '', tg_api_host: '',
  wx_corp_id: '', wx_corp_secret: '', wx_agent_id: '', wx_user_id: '@all',
  wx_msg_type: 'news_notice', wx_proxy_url: '', wx_no_proxy: true,
  bark_server: 'https://api.day.app', bark_keys: '',
  enable_custom_template: false, tg_template: '', wx_title_template: '',
  wx_body_template: '', bark_title_template: '', bark_body_template: '',
}

const GROUPS = [
  { key: 'base', label: '基础' },
  { key: 'watch', label: '观看链接', en: 'enable_watch_link' },
  { key: 'tg', label: 'Telegram' },
  { key: 'wx', label: '企业微信' },
  { key: 'bark', label: 'Bark' },
  { key: 'tpl', label: '自定义模板', en: 'enable_custom_template' },
]
const WATCH_TYPES = [
  { v: 'server', l: 'server（Emby/Jellyfin 直链）' },
  { v: 'forward', l: 'forward（Forward App）' },
  { v: 'infuse', l: 'infuse（Infuse）' },
]
const WX_MSG_TYPES = [
  { v: 'news_notice', l: 'news_notice（卡片）' },
  { v: 'news', l: 'news（图文）' },
]
// 模板可用变量说明（含双大括号，放 JS 常量里避免被 Vue 模板编译器当插值解析）。
const TPL_VARS = '{{server_name}} {{status_text}} {{item_name}} {{episode_text}} {{genres}} {{cast}} {{rating}} {{release_date}} {{overview}} {{play_url}} {{tmdb_url}}'

const tab = ref('settings')
const group = ref('base')
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)
const cfg = reactive({ ...DEFAULTS })
const secretVisible = reactive({ tmdb_api_key: false, tg_bot_token: false, wx_corp_secret: false })
const tgChatName = ref('')

const recent = ref([])
const recentLoading = ref(false)
const webhookUrl = ref('')
const webhookExact = ref(false)

async function platformJson(path, options = {}) {
  const headers = {'Content-Type': 'application/json'}
  if (props.host.token) headers.Authorization = `Bearer ${props.host.token}`
  const response = await fetch(path, {...options, headers: {...headers, ...(options.headers || {})}})
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

async function loadWebhookUrl() {
  const origin = window.location.origin.replace(/\/$/, '')
  let path = `/api/plugin/${props.pluginId}/receive`
  try {
    const meta = await platformJson(`/api/plugins/${props.pluginId}/webhook`)
    const routes = Array.isArray(meta.webhooks) ? meta.webhooks.map(String) : []
    const route = routes.includes('receive') ? 'receive' : (routes[0] || 'receive')
    path = `${String(meta.base_url || `/api/plugin/${props.pluginId}/`).replace(/\/$/, '')}/${route.replace(/^\//, '')}`
  } catch (_) { /* 使用插件声明的固定公开路径 */ }
  try {
    const secret = await platformJson('/api/settings/reveal-secret', {
      method: 'POST',
      body: JSON.stringify({kind: 'system', field: 'WEBHOOK_SECRET', id: ''}),
    })
    if (secret?.value) {
      webhookUrl.value = `${origin}${path}?apikey=${encodeURIComponent(secret.value)}`
      webhookExact.value = true
      return
    }
  } catch (_) { /* 未设置密钥时显示可填写模板 */ }
  webhookUrl.value = `${origin}${path}?apikey=<平台 Webhook 密钥>`
  webhookExact.value = false
}

async function copyWebhookUrl() {
  try {
    if (!navigator.clipboard?.writeText) throw new Error('clipboard unavailable')
    await navigator.clipboard.writeText(webhookUrl.value)
    props.host.toast.success(webhookExact.value ? 'Webhook 地址已复制' : 'Webhook 地址格式已复制')
  } catch (_) {
    const field = document.createElement('textarea')
    field.value = webhookUrl.value
    field.style.position = 'fixed'
    field.style.opacity = '0'
    document.body.appendChild(field)
    field.select()
    const copied = document.execCommand('copy')
    field.remove()
    if (copied) props.host.toast.success(webhookExact.value ? 'Webhook 地址已复制' : 'Webhook 地址格式已复制')
    else props.host.toast.error('复制失败，请手动选择地址复制')
  }
}

onMounted(async () => {
  try {
    const saved = await props.host.getConfig()
    for (const field of Object.keys(secretVisible)) {
      if (saved?.[field] === '********') saved[field] = await props.host.revealSecret(field)
    }
    Object.assign(cfg, DEFAULTS, saved || {})
    await loadChatName()
    await loadWebhookUrl()
  } catch (e) {
    props.host.toast.error('读取配置失败：' + (e.message || e))
  } finally {
    loading.value = false
  }
})

async function save() {
  saving.value = true
  try {
    await props.host.saveConfig({ ...cfg })
    await loadChatName()
    props.host.toast.success('配置已保存')
  } catch (e) {
    props.host.toast.error('保存失败：' + (e.message || e))
  } finally {
    saving.value = false
  }
}

async function loadChatName() {
  tgChatName.value = ''
  if (!cfg.tg_bot_token || !cfg.tg_chat_id) return
  try {
    const r = await props.host.callApi('/chat_name')
    if (r.ok && r.title) tgChatName.value = `${r.title} (${r.id})`
  } catch (_) { /* 名称解析失败时继续保留原 Chat ID */ }
}

async function testPush() {
  testing.value = true
  try {
    const r = await props.host.callApi('/test', { method: 'POST', body: {} })
    if (r.ok) props.host.toast.success(r.message || '已发送测试通知')
    else props.host.toast.error(r.message || '测试失败')
  } catch (e) { props.host.toast.error('测试失败：' + (e.message || e)) }
  finally { testing.value = false }
}

async function loadRecent() {
  recentLoading.value = true
  try {
    const r = await props.host.callApi('/recent')
    recent.value = r.items || []
  } catch (e) { props.host.toast.error('读取推送记录失败：' + (e.message || e)) }
  finally { recentLoading.value = false }
}
async function clearRecent() {
  if (!confirm('清空最近推送记录？')) return
  try {
    await props.host.callApi('/clear', { method: 'POST', body: {} })
    recent.value = []
    props.host.toast.success('已清空')
  } catch (e) { props.host.toast.error('清空失败：' + (e.message || e)) }
}

function switchTab(t) {
  tab.value = t
  if (t === 'recent' && !recent.value.length) loadRecent()
}
</script>

<template>
  <IosSettings>
  <div class="ep-ios-ep">
    <div v-if="loading" class="ep-ios-muted">加载配置…</div>
    <template v-else>
      <div class="ep-ios-tabs">
        <button :class="['ep-ios-tab', { on: tab === 'settings' }]" @click="switchTab('settings')">配置</button>
        <button :class="['ep-ios-tab', { on: tab === 'recent' }]" @click="switchTab('recent')">最近推送</button>
      </div>

      <!-- ============ 配置 ============ -->
      <div v-show="tab === 'settings'" class="ep-ios-layout">
        <aside class="ep-ios-sidebar">
          <div class="ep-ios-side-title">设置分组</div>
          <button v-for="g in GROUPS" :key="g.key"
                  :class="['ep-ios-side-item', { on: group === g.key }]" @click="group = g.key">
            <span>{{ g.label }}</span>
            <span v-if="g.en && cfg[g.en]" class="ep-ios-dot"></span>
          </button>
        </aside>

        <div class="ep-ios-detail">
          <!-- 基础 -->
          <template v-if="group === 'base'">
            <h3 class="ep-ios-det-title">基础</h3>
            <section class="ep-ios-card">
              <div class="ep-ios-webhook-block">
                <div class="ep-ios-webhook-head"><span>Emby / Jellyfin Webhook 地址</span><button type="button" class="ep-ios-btn" @click="copyWebhookUrl">复制</button></div>
                <div class="ep-ios-webhook-url">{{ webhookUrl }}</div>
                <p class="ep-ios-tip">请求方式为 POST，内容类型为 application/json。<template v-if="!webhookExact">请先在“系统设置 → 通知渠道 → Webhook”生成平台密钥。</template></p>
              </div>
              <label class="ep-ios-row ep-ios-switch"><input v-model="cfg.enable_tmdb" type="checkbox" /><span class="ep-ios-track" aria-hidden="true"><span></span></span><span>TMDB 元数据增强</span></label>
              <template v-if="cfg.enable_tmdb">
                <label class="ep-ios-row"><span>TMDB API Key</span><div class="ep-ios-secret-field"><input v-model="cfg.tmdb_api_key" class="ep-ios-inp" :type="secretVisible.tmdb_api_key ? 'text' : 'password'" placeholder="留空则不做 TMDB 增强" /><button type="button" aria-label="显示或隐藏 TMDB API Key" @click="secretVisible.tmdb_api_key = !secretVisible.tmdb_api_key"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div></label>
                <div class="ep-ios-grid">
                  <label class="ep-ios-row"><span>API 域名</span><input v-model="cfg.tmdb_api_domain" class="ep-ios-inp" /></label>
                  <label class="ep-ios-row"><span>图片域名</span><input v-model="cfg.tmdb_image_domain" class="ep-ios-inp" /></label>
                </div>
              </template>
              <label class="ep-ios-row"><span>Emby 地址</span><input v-model="cfg.emby_server_url" class="ep-ios-inp" placeholder="https://your-emby.com（生成播放链接/图片降级）" /></label>
              <div class="ep-ios-grid">
                <label class="ep-ios-row"><span>去重窗口</span><input v-model.number="cfg.dedup_window" class="ep-ios-inp ep-ios-sm" type="number" /><span class="ep-ios-hint">秒</span></label>
                <label class="ep-ios-row"><span>剧集合并等待</span><input v-model.number="cfg.episode_cache_timeout" class="ep-ios-inp ep-ios-sm" type="number" /><span class="ep-ios-hint">秒</span></label>
              </div>
            </section>
          </template>

          <!-- 观看链接 -->
          <template v-else-if="group === 'watch'">
            <h3 class="ep-ios-det-title">观看链接</h3>
            <section class="ep-ios-card">
              <label class="ep-ios-row ep-ios-switch"><input v-model="cfg.enable_watch_link" type="checkbox" /><span class="ep-ios-track" aria-hidden="true"><span></span></span><span>生成观看按钮/链接</span></label>
              <template v-if="cfg.enable_watch_link">
                <label class="ep-ios-row"><span>播放链接类型</span><select v-model="cfg.watch_link_type" class="ep-ios-inp"><option v-for="o in WATCH_TYPES" :key="o.v" :value="o.v">{{ o.l }}</option></select></label>
                <label class="ep-ios-row ep-ios-top"><span>非HTTP中转前缀</span><textarea v-model="cfg.link_redirect_prefix" class="ep-ios-inp" rows="2" placeholder="把 infuse:// 等包装成 http 按钮，支持 {url} 占位"></textarea></label>
              </template>
            </section>
          </template>

          <!-- Telegram -->
          <template v-else-if="group === 'tg'">
            <h3 class="ep-ios-det-title">Telegram</h3>
            <section class="ep-ios-card">
              <div v-if="tgChatName" class="ep-ios-chat-names">已识别：{{ tgChatName }}</div>
              <label class="ep-ios-row"><span>Bot Token</span><div class="ep-ios-secret-field"><input v-model="cfg.tg_bot_token" class="ep-ios-inp" :type="secretVisible.tg_bot_token ? 'text' : 'password'" placeholder="@BotFather 获取，可填平台机器人 token" /><button type="button" aria-label="显示或隐藏 Bot Token" @click="secretVisible.tg_bot_token = !secretVisible.tg_bot_token"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div></label>
              <label class="ep-ios-row"><span>Chat ID</span><input v-model="cfg.tg_chat_id" class="ep-ios-inp" placeholder="目标用户或群组 ID" /></label>
              <label class="ep-ios-row"><span>API Host</span><input v-model="cfg.tg_api_host" class="ep-ios-inp" placeholder="留空=官方；自建反代可改" /></label>
            </section>
          </template>

          <!-- 企业微信 -->
          <template v-else-if="group === 'wx'">
            <h3 class="ep-ios-det-title">企业微信</h3>
            <section class="ep-ios-card">
              <label class="ep-ios-row"><span>Corp ID</span><input v-model="cfg.wx_corp_id" class="ep-ios-inp" /></label>
              <label class="ep-ios-row"><span>Corp Secret</span><div class="ep-ios-secret-field"><input v-model="cfg.wx_corp_secret" class="ep-ios-inp" :type="secretVisible.wx_corp_secret ? 'text' : 'password'" /><button type="button" aria-label="显示或隐藏 Corp Secret" @click="secretVisible.wx_corp_secret = !secretVisible.wx_corp_secret"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div></label>
              <div class="ep-ios-grid">
                <label class="ep-ios-row"><span>Agent ID</span><input v-model="cfg.wx_agent_id" class="ep-ios-inp" /></label>
                <label class="ep-ios-row"><span>接收用户</span><input v-model="cfg.wx_user_id" class="ep-ios-inp" placeholder="@all" /></label>
              </div>
              <label class="ep-ios-row"><span>消息类型</span><select v-model="cfg.wx_msg_type" class="ep-ios-inp"><option v-for="o in WX_MSG_TYPES" :key="o.v" :value="o.v">{{ o.l }}</option></select></label>
              <label class="ep-ios-row"><span>API 地址</span><input v-model="cfg.wx_proxy_url" class="ep-ios-inp" placeholder="留空=官方；可直接填 wx.example.com，自动补 https://" /></label>
              <label class="ep-ios-row ep-ios-switch"><input v-model="cfg.wx_no_proxy" type="checkbox" /><span class="ep-ios-track" aria-hidden="true"><span></span></span><span>企微请求不走代理</span></label>
            </section>
          </template>

          <!-- Bark -->
          <template v-else-if="group === 'bark'">
            <h3 class="ep-ios-det-title">Bark</h3>
            <section class="ep-ios-card">
              <label class="ep-ios-row"><span>Bark 服务器</span><input v-model="cfg.bark_server" class="ep-ios-inp" /></label>
              <label class="ep-ios-row ep-ios-top"><span>设备 Key</span><textarea v-model="cfg.bark_keys" class="ep-ios-inp" rows="2" placeholder="多个 Key 用英文逗号分隔；留空不启用 Bark"></textarea></label>
            </section>
          </template>

          <!-- 自定义模板 -->
          <template v-else-if="group === 'tpl'">
            <h3 class="ep-ios-det-title">自定义推送模板（测试）</h3>
            <section class="ep-ios-card">
              <label class="ep-ios-row ep-ios-switch"><input v-model="cfg.enable_custom_template" type="checkbox" /><span class="ep-ios-track" aria-hidden="true"><span></span></span><span>启用自定义推送模板（测试中，不建议生产）</span></label>
              <template v-if="cfg.enable_custom_template">
                <p class="ep-ios-tip">变量：{{ TPL_VARS }}；留空用默认。</p>
                <label class="ep-ios-row ep-ios-top"><span>TG 模板(HTML)</span><textarea v-model="cfg.tg_template" class="ep-ios-inp" rows="4"></textarea></label>
                <label class="ep-ios-row ep-ios-top"><span>企微标题</span><textarea v-model="cfg.wx_title_template" class="ep-ios-inp" rows="2"></textarea></label>
                <label class="ep-ios-row ep-ios-top"><span>企微正文</span><textarea v-model="cfg.wx_body_template" class="ep-ios-inp" rows="3"></textarea></label>
                <label class="ep-ios-row ep-ios-top"><span>Bark 标题</span><textarea v-model="cfg.bark_title_template" class="ep-ios-inp" rows="2"></textarea></label>
                <label class="ep-ios-row ep-ios-top"><span>Bark 正文</span><textarea v-model="cfg.bark_body_template" class="ep-ios-inp" rows="3"></textarea></label>
              </template>
            </section>
          </template>

          <div class="ep-ios-savebar">
            <button class="ep-ios-btn" :disabled="testing" @click="testPush">{{ testing ? '发送中…' : '测试推送' }}</button>
            <button class="ep-ios-btn ep-ios-primary ep-ios-lg" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存配置' }}</button>
          </div>
        </div>
      </div>

      <!-- ============ 最近推送 ============ -->
      <div v-show="tab === 'recent'" class="ep-ios-pane">
        <div class="ep-ios-toolbar">
          <span class="ep-ios-muted">最近 {{ recent.length }} 条推送</span>
          <span class="ep-ios-grow"></span>
          <button class="ep-ios-btn" :disabled="testing" @click="testPush">{{ testing ? '发送中…' : '测试推送' }}</button>
          <button class="ep-ios-btn" @click="loadRecent">刷新</button>
          <button class="ep-ios-btn ep-ios-danger" :disabled="!recent.length" @click="clearRecent">清空</button>
        </div>
        <div v-if="recentLoading" class="ep-ios-muted">加载中…</div>
        <div v-else-if="!recent.length" class="ep-ios-empty">暂无推送记录<br><span class="ep-ios-muted">Emby/Jellyfin 入库并成功推送后，这里会显示最近 10 条</span></div>
        <div v-else class="ep-ios-cards">
          <div v-for="(r, i) in recent" :key="i" class="ep-ios-rcard">
            <div class="ep-ios-rimg" :style="r.image_url ? { backgroundImage: `url(${r.image_url})` } : {}">
              <span v-if="!r.image_url" class="ep-ios-rimg-ph">{{ r.item_type === 'TV' ? '📺' : '🎬' }}</span>
            </div>
            <div class="ep-ios-rbody">
              <div class="ep-ios-rname">{{ r.item_name }}</div>
              <div v-if="r.episode_text" class="ep-ios-rep">{{ r.episode_text }}</div>
              <div class="ep-ios-rmeta">
                <span class="ep-ios-rtag">{{ r.item_type === 'TV' ? '剧集' : '电影' }}</span>
                <span class="ep-ios-rch">{{ r.channels || '—' }}</span>
              </div>
              <div class="ep-ios-rtime">{{ r.time }}</div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>

  </IosSettings>
</template>

<style scoped>
.ep-ios-ep { display: flex; flex-direction: column; gap: 24px; container-type: inline-size; color: var(--ios-text); }
.ep-ios-tabs { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px; width: min(100%, 360px); padding: 4px; border: 1px solid var(--ios-line); border-radius: 17px; background: var(--ios-inset); }
.ep-ios-tab { min-height: 38px; padding: 8px 16px; border: 1px solid transparent; border-radius: 13px; background: transparent; color: var(--ios-secondary); font: inherit; font-size: 13px; font-weight: 600; cursor: pointer; transition: background var(--ios-duration) var(--ios-ease), color var(--ios-fast) ease, box-shadow var(--ios-duration) ease; }
.ep-ios-tab.on { background: var(--ios-surface); color: var(--ios-text); border-color: var(--ios-line); box-shadow: 0 2px 6px color-mix(in srgb, var(--ios-text) 6%, transparent); }
.ep-ios-layout { display: grid; grid-template-columns: 154px minmax(0, 1fr); gap: 28px; align-items: start; }
.ep-ios-sidebar { display: flex; flex-direction: column; gap: 4px; padding: 8px; border: 1px solid var(--ios-line); border-radius: 22px; background: var(--ios-inset); }
.ep-ios-side-title { padding: 8px 10px; font-size: 11px; font-weight: 600; letter-spacing: .04em; color: var(--ios-secondary); }
.ep-ios-side-item { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; min-height: 44px; padding: 10px 12px; border: 1px solid transparent; border-radius: 14px; text-align: left; font: inherit; font-size: 13px; color: var(--ios-secondary); background: transparent; cursor: pointer; transition: background var(--ios-duration) var(--ios-ease), color var(--ios-fast) ease; }
.ep-ios-side-item:hover { background: var(--ios-control); color: var(--ios-text); }
.ep-ios-side-item.on { background: var(--ios-surface); border-color: var(--ios-line); color: var(--ios-text); font-weight: 600; box-shadow: 0 2px 8px color-mix(in srgb, var(--ios-text) 4%, transparent); }
.ep-ios-dot { flex: 0 0 6px; width: 6px; height: 6px; border-radius: 50%; background: var(--success, #28a56a); }
.ep-ios-detail { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.ep-ios-det-title { margin: 0; padding: 2px 4px; color: var(--ios-text); font-size: 19px; line-height: 1.4; font-weight: 650; letter-spacing: -.025em; }
.ep-ios-card { display: flex; flex-direction: column; gap: 0; min-width: 0; padding: 0 20px; border: 1px solid var(--ios-line); border-radius: 24px; background: var(--ios-surface); overflow: hidden; }
.ep-ios-row { display: flex; align-items: center; gap: 14px; min-width: 0; min-height: 72px; padding: 14px 0; border-top: 1px solid var(--ios-line); }
.ep-ios-card > .ep-ios-row:first-child { border-top: 0; }
.ep-ios-row > span:first-child { flex: 0 0 110px; font-size: 13px; line-height: 1.55; color: var(--ios-text); }
.ep-ios-row.ep-ios-top { display: grid; grid-template-columns: minmax(0, 1fr); gap: 9px; }
.ep-ios-row.ep-ios-top > span:first-child { flex-basis: auto; }
.ep-ios-inp { flex: 1; min-width: 0; width: 100%; min-height: 42px; padding: 10px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-control); color: var(--ios-text); font: inherit; font-size: 13px; transition: border-color var(--ios-fast) ease, box-shadow var(--ios-fast) ease; }
.ep-ios-inp::placeholder { color: var(--ios-secondary); opacity: .8; }
.ep-ios-inp.ep-ios-sm { flex: 0 1 100px; width: 100px; font-variant-numeric: tabular-nums; }
textarea.ep-ios-inp { min-height: 82px; resize: vertical; line-height: 1.65; }
select.ep-ios-inp { cursor: pointer; padding-right: 28px; }
.ep-ios-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 22px; }
.ep-ios-grid .ep-ios-row { flex-wrap: wrap; gap: 8px; }
.ep-ios-grid .ep-ios-row > span:first-child { flex: 1 0 100%; }
.ep-ios-hint { flex: 0 0 auto; font-size: 12px; color: var(--ios-secondary); }
.ep-ios-secret-field { position: relative; flex: 1; min-width: 0; }
.ep-ios-secret-field .ep-ios-inp { padding-right: 46px; }
.ep-ios-secret-field button { position: absolute; inset: 4px 4px 4px auto; width: 34px; min-height: 34px; display: grid; place-items: center; border: 0; border-radius: 9px; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.ep-ios-secret-field button:hover { color: var(--accent, #0063dc); background: color-mix(in srgb, var(--ios-accent) 9%, transparent); }
.ep-ios-secret-field svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.8; }
.ep-ios-switch { position: relative; justify-content: space-between; min-height: 66px; }
.ep-ios-switch > input { position: absolute; inset-inline-end: 0; width: 50px; height: 30px; margin: 0; opacity: 0; z-index: 2; cursor: pointer; }
.ep-ios-switch > span:last-child { order: -1; flex: 1; min-width: 0; font-size: 13px; line-height: 1.55; }
.ep-ios-track { position: relative; flex: 0 0 50px; width: 50px; height: 30px; padding: 3px; border: 1px solid color-mix(in srgb, var(--ios-text) 5%, transparent); border-radius: 20px; background: color-mix(in srgb, var(--ios-text) 18%, transparent); transition: background var(--ios-duration) var(--ios-ease); }
.ep-ios-track > span { display: block; width: 24px; height: 24px; margin: -1px; border-radius: 50%; background: #fff; box-shadow: 0 2px 5px #0002; transition: transform var(--ios-duration) var(--ios-ease); }
.ep-ios-switch > input:checked + .ep-ios-track { background: var(--ios-accent); }
.ep-ios-switch > input:checked + .ep-ios-track > span { transform: translateX(20px); }
.ep-ios-switch > input:focus-visible + .ep-ios-track { outline: 3px solid var(--accent, #0063dc); outline-offset: 3px; }
.ep-ios-webhook-block { display: grid; gap: 10px; margin: 18px 0 4px; padding: 16px; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-inset); }
.ep-ios-webhook-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; color: var(--ios-text); font-size: 13px; font-weight: 600; }
.ep-ios-webhook-url { padding: 12px; border: 1px solid var(--ios-line); border-radius: 11px; background: var(--ios-control); color: var(--ios-text); font: 12px/1.7 ui-monospace, SFMono-Regular, Consolas, monospace; overflow-wrap: anywhere; user-select: all; }
.ep-ios-tip { margin: 0; padding: 13px 0; font-size: 12px; line-height: 1.7; color: var(--ios-secondary); overflow-wrap: anywhere; }
.ep-ios-webhook-block .ep-ios-tip { padding: 0; }
.ep-ios-chat-names { padding: 14px 0; color: var(--accent, #0063dc); font-size: 12px; line-height: 1.6; overflow-wrap: anywhere; }
.ep-ios-savebar { position: sticky; bottom: 0; display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 10px; padding: 14px 0 3px; background: var(--ios-inset); border-radius: 0 0 16px 16px; }
.ep-ios-btn { min-height: 40px; padding: 9px 16px; border: 1px solid var(--ios-line); border-radius: 13px; background: var(--ios-control); color: var(--ios-text); font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; transition: background var(--ios-fast) ease, color var(--ios-fast) ease, opacity var(--ios-fast) ease; }
.ep-ios-btn:hover { color: var(--accent, #0063dc); border-color: color-mix(in srgb, var(--ios-accent) 35%, var(--ios-line)); }
.ep-ios-btn.ep-ios-primary { min-width: 122px; background: var(--ios-accent); border-color: transparent; color: #fff; }
.ep-ios-btn.ep-ios-danger { color: var(--danger, #d94a53); }
.ep-ios-btn:disabled { opacity: .45; cursor: not-allowed; }
.ep-ios-pane { display: flex; flex-direction: column; gap: 20px; }
.ep-ios-toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; padding-bottom: 2px; }
.ep-ios-grow { flex: 1; }
.ep-ios-muted { color: var(--ios-secondary); font-size: 12px; line-height: 1.65; }
.ep-ios-empty { display: grid; justify-items: center; gap: 9px; padding: 56px 20px; border: 1px dashed var(--ios-line); border-radius: 24px; background: var(--ios-inset); color: var(--ios-text); text-align: center; font-size: 15px; line-height: 1.6; }
.ep-ios-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr)); gap: 14px; }
.ep-ios-rcard { display: flex; gap: 15px; padding: 16px; min-width: 0; border: 1px solid var(--ios-line); border-radius: 22px; background: var(--ios-surface); transition: border-color var(--ios-duration) ease, transform var(--ios-duration) var(--ios-ease); }
.ep-ios-rcard:hover { border-color: color-mix(in srgb, var(--ios-accent) 25%, var(--ios-line)); transform: translateY(calc(-2px * var(--glass-custom-motion, 1))); }
.ep-ios-rimg { display: grid; place-items: center; flex: 0 0 64px; width: 64px; height: 96px; border: 1px solid var(--ios-line); border-radius: 11px; background: var(--ios-inset); background-position: center; background-size: cover; background-repeat: no-repeat; }
.ep-ios-rimg-ph { font-size: 24px; opacity: .7; }
.ep-ios-rbody { display: flex; flex-direction: column; gap: 6px; flex: 1; min-width: 0; }
.ep-ios-rname { font-size: 14px; font-weight: 650; line-height: 1.5; color: var(--ios-text); overflow-wrap: anywhere; }
.ep-ios-rep { font-size: 12px; line-height: 1.5; color: var(--ios-secondary); overflow-wrap: anywhere; }
.ep-ios-rmeta { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.ep-ios-rtag { padding: 3px 8px; border-radius: 7px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 10px; line-height: 1.4; }
.ep-ios-rch { color: var(--accent, #0063dc); font-size: 11px; line-height: 1.4; overflow-wrap: anywhere; }
.ep-ios-rtime { margin-top: auto; padding-top: 5px; color: var(--ios-secondary); font-size: 10px; font-variant-numeric: tabular-nums; }
:global(html[data-theme='transparent'] .ep-ios-card),
:global(html[data-theme='transparent'] .ep-ios-rcard) { box-shadow: inset 0 1px 0 color-mix(in srgb, var(--ios-text) 5%, transparent); }
@container (max-width: 620px) {
  .ep-ios-layout { grid-template-columns: minmax(0, 1fr); gap: 22px; }
  .ep-ios-sidebar { flex-direction: row; flex-wrap: wrap; gap: 5px; padding: 6px; border-radius: 18px; }
  .ep-ios-side-title { display: none; }
  .ep-ios-side-item { flex: 1 0 auto; width: auto; min-height: 38px; padding: 8px 11px; justify-content: center; font-size: 12px; }
  .ep-ios-card { padding: 0 16px; border-radius: 20px; }
  .ep-ios-row { align-items: stretch; flex-wrap: wrap; gap: 9px; }
  .ep-ios-row > span:first-child { flex: 1 0 100%; }
  .ep-ios-grid { grid-template-columns: minmax(0, 1fr); }
  .ep-ios-grid .ep-ios-row { align-items: center; }
  .ep-ios-switch { flex-wrap: nowrap; align-items: center; }
  .ep-ios-switch > span:last-child { flex-basis: auto; }
  .ep-ios-webhook-head { flex-wrap: wrap; }
  .ep-ios-webhook-head > .ep-ios-btn { margin-left: auto; }
  .ep-ios-savebar { padding-top: 9px; }
  .ep-ios-toolbar > .ep-ios-muted { flex: 1 0 100%; padding: 0 2px 6px; }
  .ep-ios-toolbar .ep-ios-grow { display: none; }
}
@container (max-width: 380px) {
  .ep-ios-tabs { width: 100%; }
  .ep-ios-savebar .ep-ios-btn { flex: 1; min-width: 0; }
  .ep-ios-rcard { padding: 13px; gap: 12px; }
}
</style>
