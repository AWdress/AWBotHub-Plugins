<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'

const props = defineProps({
  pluginId: { type: String, required: true },
  host: { type: Object, required: true },
})

const DEFAULTS = {
  enable_image_generation: true,
  image_size: '1024x1024', image_quality: 'auto',
  enable_private_chat: true, enable_group_chat: true, group_chat_ids: '',
  system_prompt: (
    '# Role\n你是一个相处了很久的普通网友。\n\n' +
    '# Rules\n' +
    '1. 语气口语化、随性、接地气，就像在微信或QQ上聊天。\n' +
    '2. 每次回复必须精简，严禁长篇大论。\n' +
    '3. 绝对不能超过 20 个字。\n' +
    '4. 绝对不要在回复中模仿、复述或带入用户的动作动作。\n' +
    '5. 偶尔可以在句末加一个合适的 emoji（如 😂、🤷‍♂️、👀），不要过多。'
  ),
  max_history: 10,
  enable_proactive: false, proactive_chat_ids: '',
  proactive_min_minutes: 60, proactive_max_minutes: 180,
  enable_explain_command: true, enable_explain_prompt: false,
  explain_prompt: (
    '你是一个群聊消息解读助手。请根据用户【回复的消息内容】进行解释与答疑，简明清晰。\n' +
    "输出结构：\n1) 这句话/这段话的主要意思\n2) 语气/态度\n3) 可能的隐含信息（没有就写'无'）\n\n" +
    '需要解释的消息内容：{content}'
  ),
  white_list_chats: '',
  enable_rich_reply: true,
  reply_template: '{answer}',
  explain_reply_template: '**问题**\n> {question}\n\n**回答**\n{answer}',
}

const GROUPS = [
  { key: 'image', label: 'AI 生图', en: 'enable_image_generation' },
  { key: 'human', label: '人形回复', en: 'enable_private_chat' },
  { key: 'proactive', label: '主动搭话', en: 'enable_proactive' },
  { key: 'explain', label: '解释命令', en: 'enable_explain_command' },
  { key: 'reply', label: '回复格式', en: 'enable_rich_reply' },
  { key: 'scope', label: '范围' },
]

const tab = ref('settings')
const group = ref('image')
const loading = ref(true)
const configReady = ref(false)
const loadError = ref('')
const saving = ref(false)
const cfg = reactive({ ...DEFAULTS })
const chatNames = ref([])
const replyInput = ref(null)
const explainReplyInput = ref(null)

function templateError(value) {
  const text = String(value ?? '')
  return text.trim() && !text.includes('{answer}')
    ? '请保留 {answer}，它用于显示 AI 的完整回答；留空可恢复默认模板。'
    : ''
}
const replyError = computed(() => templateError(cfg.reply_template))
const explainReplyError = computed(() => templateError(cfg.explain_reply_template))

const histories = ref([])
const proactiveNext = ref('')
const histLoading = ref(false)
const historyLoaded = ref(false)
const activeChat = ref(null)
const chatMessages = ref([])
const msgLoading = ref(false)
const historyError = ref('')
const messageError = ref('')
const clearing = ref(false)
let historyRequest = 0

function errorText(error) {
  return String(error?.message || error || '未知错误')
}

async function loadConfig() {
  if (saving.value) return
  loading.value = true
  configReady.value = false
  loadError.value = ''
  try {
    const saved = await props.host.getConfig()
    if (saved != null && (typeof saved !== 'object' || Array.isArray(saved))) {
      throw new Error('配置返回格式不正确，请重试')
    }
    Object.assign(cfg, DEFAULTS, saved || {})
    configReady.value = true
    await loadChatNames()
  } catch (error) {
    loadError.value = '读取配置失败：' + errorText(error)
    props.host.toast.error(loadError.value)
  } finally {
    loading.value = false
  }
}
onMounted(loadConfig)

async function loadChatNames() {
  try {
    const result = await props.host.callApi('/chat_names')
    chatNames.value = Array.isArray(result?.items) ? result.items : []
  } catch {
    // 群名仅用于辅助识别，读取失败不妨碍保存已加载的配置。
  }
}

async function save() {
  if (!configReady.value || saving.value) return
  if (replyError.value || explainReplyError.value) {
    group.value = 'reply'
    await nextTick()
    ;(replyError.value ? replyInput.value : explainReplyInput.value)?.focus()
    props.host.toast.error('模板未保存：请保留 {answer}，或留空使用默认模板。')
    return
  }
  saving.value = true
  try {
    const values = {
      ...cfg,
      reply_template: String(cfg.reply_template ?? '').trim() ? cfg.reply_template : DEFAULTS.reply_template,
      explain_reply_template: String(cfg.explain_reply_template ?? '').trim() ? cfg.explain_reply_template : DEFAULTS.explain_reply_template,
    }
    await props.host.saveConfig(values)
    Object.assign(cfg, values)
    await loadChatNames()
    props.host.toast.success('配置已保存')
  } catch (error) {
    props.host.toast.error('保存失败：' + errorText(error))
  } finally {
    saving.value = false
  }
}

async function loadHistories() {
  if (histLoading.value || clearing.value) return
  histLoading.value = true
  historyError.value = ''
  try {
    const result = await props.host.callApi('/histories')
    histories.value = Array.isArray(result?.items) ? result.items : []
    proactiveNext.value = result?.proactive_next || ''
    historyLoaded.value = true
  } catch (error) {
    historyError.value = '读取会话列表失败：' + errorText(error)
    props.host.toast.error(historyError.value)
  } finally {
    histLoading.value = false
  }
}

async function openChat(item) {
  const request = ++historyRequest
  activeChat.value = item
  msgLoading.value = true
  messageError.value = ''
  chatMessages.value = []
  try {
    const result = await props.host.callApi('/history?chat_id=' + encodeURIComponent(item.chat_id))
    if (request === historyRequest) chatMessages.value = Array.isArray(result?.messages) ? result.messages : []
  } catch (error) {
    if (request === historyRequest) {
      messageError.value = '读取会话历史失败：' + errorText(error)
      props.host.toast.error(messageError.value)
    }
  } finally {
    if (request === historyRequest) msgLoading.value = false
  }
}

async function clearChat(item) {
  if (clearing.value || !confirm(`清空会话 ${item.chat_title || item.chat_id} 的对话记忆？`)) return
  clearing.value = true
  try {
    const result = await props.host.callApi('/history/clear', { method: 'POST', body: { chat_id: item.chat_id } })
    if (result?.ok === false) throw new Error(result.message || '未能清空会话')
    histories.value = histories.value.filter(x => x.chat_id !== item.chat_id)
    if (activeChat.value?.chat_id === item.chat_id) {
      historyRequest++
      activeChat.value = null
      chatMessages.value = []
      msgLoading.value = false
    }
    props.host.toast.success('已清空')
  } catch (error) {
    props.host.toast.error('清空失败：' + errorText(error))
  } finally {
    clearing.value = false
  }
}

async function clearAll() {
  if (clearing.value || !confirm('清空全部会话的对话记忆？')) return
  clearing.value = true
  try {
    const result = await props.host.callApi('/history/clear', { method: 'POST', body: { all: true } })
    if (result?.ok === false) throw new Error(result.message || '未能清空会话')
    historyRequest++
    histories.value = []
    activeChat.value = null
    chatMessages.value = []
    msgLoading.value = false
    props.host.toast.success('已清空全部')
  } catch (error) {
    props.host.toast.error('清空失败：' + errorText(error))
  } finally {
    clearing.value = false
  }
}

function switchTab(value) {
  tab.value = value
  if (value === 'memory' && !historyLoaded.value) loadHistories()
}
</script>

<template>
  <div class="ai">
    <div v-if="loading" class="muted" role="status">加载配置…</div>
    <template v-else>
      <div class="tabs" aria-label="AI 助手页面">
        <button type="button" :class="['tab', { on: tab === 'settings' }]" :aria-pressed="tab === 'settings'" @click="switchTab('settings')">⚙ 配置</button>
        <button type="button" :class="['tab', { on: tab === 'memory' }]" :aria-pressed="tab === 'memory'" @click="switchTab('memory')">💬 对话记忆</button>
      </div>
      <div v-if="loadError" class="load-error" role="alert">
        <p>{{ loadError }}。未加载成功前不能保存，以免覆盖原设置。</p>
        <button type="button" class="btn" @click="loadConfig">重新读取配置</button>
      </div>
      <div v-show="tab === 'settings'" class="layout">
        <aside class="sidebar" aria-label="设置分组">
          <div class="side-title">设置分组</div>
          <button v-for="item in GROUPS" :key="item.key" type="button" :class="['side-item', { on: group === item.key }]" :aria-pressed="group === item.key" @click="group = item.key">
            <span>{{ item.label }}</span><span v-if="item.en && cfg[item.en]" class="dot" aria-label="已开启"></span>
          </button>
        </aside>
        <div class="detail">
          <template v-if="group === 'image'">
            <h3 class="det-title">AI 生图</h3>
            <section class="card">
              <label class="row switch"><input v-model="cfg.enable_image_generation" type="checkbox" /><span>启用 AI 生图命令</span></label>
              <p class="tip">发送 /生图 画面描述 或 /draw prompt，生成后会直接把图片发到当前会话（使用平台统一 AI 服务）。</p>
              <template v-if="cfg.enable_image_generation">
                <div class="grid">
                  <label class="row"><span>图片尺寸</span><select v-model="cfg.image_size" class="inp">
                    <option value="1024x1024">1024 × 1024</option><option value="1536x1024">1536 × 1024（横图）</option><option value="1024x1536">1024 × 1536（竖图）</option><option value="1792x1024">1792 × 1024（DALL·E 3 横图）</option><option value="1024x1792">1024 × 1792（DALL·E 3 竖图）</option>
                  </select></label>
                  <label class="row"><span>生成质量</span><select v-model="cfg.image_quality" class="inp">
                    <option value="auto">自动</option><option value="low">低</option><option value="medium">中</option><option value="high">高</option><option value="standard">标准（DALL·E）</option><option value="hd">高清（DALL·E）</option>
                  </select></label>
                </div>
                <p class="tip">不同模型支持的尺寸和质量可能不同；不确定时质量选“自动”、尺寸选 1024 × 1024。</p>
              </template>
            </section>
          </template>
          <template v-else-if="group === 'human'">
            <h3 class="det-title">人形回复</h3>
            <section class="card">
              <label class="row switch"><input v-model="cfg.enable_private_chat" type="checkbox" /><span>私聊回复（私聊里直接对话）</span></label>
              <label class="row switch"><input v-model="cfg.enable_group_chat" type="checkbox" /><span>群聊回复（群里 @你 或回复你的消息时对话）</span></label>
              <label v-if="cfg.enable_group_chat" class="row top"><span>生效群组</span><textarea v-model="cfg.group_chat_ids" class="inp" rows="2" placeholder="群ID逗号分隔，留空=所有群"></textarea></label>
              <div v-if="chatNames.length" class="chat-names">已识别：<span v-for="item in chatNames" :key="item.id">{{ item.title }} ({{ item.id }})</span></div>
              <label class="row top"><span>人设</span><textarea v-model="cfg.system_prompt" class="inp" rows="8" placeholder="系统提示词"></textarea></label>
              <label class="row"><span>记忆条数</span><input v-model.number="cfg.max_history" class="inp sm" type="number" min="0" max="40" /><span class="hint">每会话保留多少条历史，0=不记忆</span></label>
            </section>
          </template>
          <template v-else-if="group === 'proactive'">
            <h3 class="det-title">随机主动搭话</h3>
            <section class="card">
              <label class="row switch"><input v-model="cfg.enable_proactive" type="checkbox" /><span>开启随机主动搭话</span></label>
              <p class="tip">在下方群组里每隔随机时间挑一条群友近期消息主动接话开启话题；群友回复你后走人形对话续聊（需“群聊回复”开着）。开启后请重载或重新启用插件。</p>
              <template v-if="cfg.enable_proactive">
                <label class="row top"><span>搭话群组</span><textarea v-model="cfg.proactive_chat_ids" class="inp" rows="2" placeholder="群ID逗号分隔，必填"></textarea></label>
                <div v-if="chatNames.length" class="chat-names">已识别：<span v-for="item in chatNames" :key="item.id">{{ item.title }} ({{ item.id }})</span></div>
                <div class="grid">
                  <label class="row"><span>间隔最小</span><input v-model.number="cfg.proactive_min_minutes" class="inp sm" type="number" min="5" max="720" /><span class="hint">分钟</span></label>
                  <label class="row"><span>间隔最大</span><input v-model.number="cfg.proactive_max_minutes" class="inp sm" type="number" min="5" max="1440" /><span class="hint">分钟</span></label>
                </div>
              </template>
            </section>
          </template>
          <template v-else-if="group === 'explain'">
            <h3 class="det-title">/ai 解释命令</h3>
            <section class="card">
              <label class="row switch"><input v-model="cfg.enable_explain_command" type="checkbox" /><span>启用 /ai 解释命令</span></label>
              <p class="tip">回复一条消息（或图片）再发 /ai，让 AI 解释/解答（单次，无记忆）。</p>
              <template v-if="cfg.enable_explain_command">
                <label class="row switch"><input v-model="cfg.enable_explain_prompt" type="checkbox" /><span>用解释模板（否则直接把内容交给 AI）</span></label>
                <label v-if="cfg.enable_explain_prompt" class="row top"><span>解释模板</span><textarea v-model="cfg.explain_prompt" class="inp" rows="6" placeholder="用 {content} 占位被解释的内容"></textarea></label>
              </template>
            </section>
          </template>
          <template v-else-if="group === 'reply'">
            <h3 class="det-title">回复格式</h3>
            <section class="card">
              <label class="row switch"><input v-model="cfg.enable_rich_reply" type="checkbox" /><span>优先使用 Telegram 原生富文本</span></label>
              <p class="tip">默认开启。非会员或原生能力不可用时，自动降级为可读的普通格式，保留正文和完整链接；网络发送结果不明确时不自动重发，避免重复消息。</p>
              <p class="tip">模板支持 Markdown 粗体、引用、代码块和表格；关闭原生富文本后仍会使用可读格式。这里控制回答的显示样式，不改变模型人设。</p>
              <label class="template-field" for="ai-reply-template"><span>普通回复模板</span><textarea id="ai-reply-template" ref="replyInput" v-model="cfg.reply_template" class="inp code-input" rows="5" :placeholder="DEFAULTS.reply_template" :aria-invalid="!!replyError" aria-describedby="ai-reply-template-hint ai-reply-template-error"></textarea></label>
              <p id="ai-reply-template-hint" class="tip">用 {answer} 放入完整回答，{question} 放入本次问题；留空使用默认模板。</p>
              <p v-if="replyError" id="ai-reply-template-error" class="field-error" role="alert">{{ replyError }}</p>
              <label class="template-field" for="ai-explain-reply-template"><span>/ai 解释回复模板</span><textarea id="ai-explain-reply-template" ref="explainReplyInput" v-model="cfg.explain_reply_template" class="inp code-input" rows="8" :placeholder="DEFAULTS.explain_reply_template" :aria-invalid="!!explainReplyError" aria-describedby="ai-explain-reply-template-hint ai-explain-reply-template-error"></textarea></label>
              <p id="ai-explain-reply-template-hint" class="tip">用 {question} 引用原消息，{answer} 放入完整回答；留空恢复默认的“问题／回答”排版。</p>
              <p v-if="explainReplyError" id="ai-explain-reply-template-error" class="field-error" role="alert">{{ explainReplyError }}</p>
              <p class="tip">模型回答中的完整网址会保留。链接来自模型文本，不代表插件已联网搜索或核验来源。</p>
            </section>
          </template>
          <template v-else-if="group === 'scope'">
            <h3 class="det-title">生效范围</h3>
            <section class="card">
              <label class="row top"><span>会话白名单</span><textarea v-model="cfg.white_list_chats" class="inp" rows="2" placeholder="会话ID逗号分隔，留空=所有会话"></textarea></label>
              <div v-if="chatNames.length" class="chat-names">已识别：<span v-for="item in chatNames" :key="item.id">{{ item.title }} ({{ item.id }})</span></div>
            </section>
          </template>
          <div class="savebar"><button type="button" class="btn primary lg" :disabled="saving || !configReady" @click="save">{{ saving ? '保存中…' : '保存配置' }}</button></div>
        </div>
      </div>
      <div v-show="tab === 'memory'" class="pane">
        <div class="toolbar"><span class="muted">下次主动搭话：{{ proactiveNext || '—' }}</span><span class="grow"></span><button type="button" class="btn" :disabled="histLoading || clearing" @click="loadHistories">刷新</button><button type="button" class="btn danger" :disabled="!histories.length || clearing || histLoading" @click="clearAll">{{ clearing ? '清空中…' : '全部清空' }}</button></div>
        <div v-if="histLoading" class="muted" role="status">加载中…</div>
        <p v-else-if="historyError" class="field-error" role="alert">{{ historyError }}，请点击“刷新”重试。</p>
        <div v-else-if="!histories.length" class="empty">暂无对话记忆<br /><span class="muted">私聊/群@你对话后会在这里记录会话记忆</span></div>
        <div v-else class="mem-layout">
          <div class="mem-list">
            <div v-for="item in histories" :key="item.chat_id" :class="['mem-item', { on: activeChat?.chat_id === item.chat_id }]">
              <button type="button" class="mem-open" @click="openChat(item)"><span class="mem-h"><span class="mem-type">{{ item.is_private ? '私聊' : '群' }}</span><span class="mem-id">{{ item.chat_title || item.chat_id }} ({{ item.chat_id }})</span></span><span class="mem-last">{{ item.last || '—' }}</span></button>
              <div class="mem-meta">{{ item.count }} 条 · <button type="button" class="lnk" :disabled="clearing" @click="clearChat(item)">清空</button></div>
            </div>
          </div>
          <div class="mem-detail">
            <div v-if="!activeChat" class="muted center">← 选择一个会话查看历史</div>
            <div v-else-if="msgLoading" class="muted" role="status">加载中…</div>
            <p v-else-if="messageError" class="field-error" role="alert">{{ messageError }}</p>
            <div v-else class="chat"><div v-for="(message, index) in chatMessages" :key="index" :class="['bubble', message.role]"><div class="bubble-role">{{ message.role === 'user' ? '对方' : '我' }}</div><div class="bubble-text">{{ message.content }}</div></div></div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ai { display: flex; flex-direction: column; gap: 14px; container-type: inline-size; }
.ai *, .ai *::before, .ai *::after { box-sizing: border-box; }
.tabs { display: flex; gap: 6px; border-bottom: 1px solid var(--border-light, #2a2e3a); }
.tab { padding: 8px 16px; background: none; border: none; cursor: pointer; font-size: 13px; color: var(--text-secondary, #b9c0cc); border-bottom: 2px solid transparent; }
.tab.on { color: var(--accent, #6ea8fe); border-bottom-color: var(--accent, #6ea8fe); }
.layout { display: flex; gap: 16px; align-items: flex-start; }
.sidebar { flex: 0 0 150px; display: flex; flex-direction: column; gap: 4px; padding: 10px; border-radius: 10px; background: var(--bg-elevated, #1a1d27); border: 1px solid var(--border-light, #2a2e3a); }
.side-title { font-size: 11px; color: var(--text-muted, #a3acbb); padding: 4px 8px 6px; }
.side-item { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 9px 10px; border-radius: 8px; border: none; cursor: pointer; text-align: left; background: none; color: var(--text-secondary, #b9c0cc); font-size: 13px; }
.side-item:hover { background: var(--bg-card, #12141c); }
.side-item.on { background: var(--accent-dim, #1e3a5f); color: var(--accent, #6ea8fe); }
.dot { width: 7px; height: 7px; border-radius: 50%; background: #6ee7a8; flex: 0 0 auto; }
.detail { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 14px; }
.det-title { margin: 0; font-size: 15px; font-weight: 600; color: var(--text-primary, #e8ebf0); }
.pane { display: flex; flex-direction: column; gap: 14px; }
.card { display: flex; flex-direction: column; gap: 12px; padding: 16px; border-radius: 10px; background: var(--bg-elevated, #1a1d27); border: 1px solid var(--border-light, #2a2e3a); }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr)); gap: 10px 20px; }
.row { display: flex; align-items: center; gap: 10px; }
.row.top { align-items: flex-start; }
.row > span:first-child { min-width: 72px; font-size: 13px; color: var(--text-secondary, #b9c0cc); }
.row.switch { justify-content: flex-start; }
.row.switch span { min-width: 0; }
.row input[type='checkbox'] { flex: 0 0 auto; accent-color: var(--accent, #6ea8fe); }
.hint { min-width: 0 !important; font-size: 12px; color: var(--text-muted, #a3acbb); }
.tip { margin: 0; font-size: 12px; color: var(--text-muted, #a3acbb); line-height: 1.6; overflow-wrap: anywhere; }
.chat-names { margin: -4px 0 10px 82px; display: flex; flex-wrap: wrap; gap: 6px; font-size: 12px; color: var(--text-primary, #e8ebf0); overflow-wrap: anywhere; }
.inp { flex: 1; min-width: 0; width: 100%; padding: 8px 10px; border-radius: 6px; font-size: 13px; background: var(--bg-card, #12141c); color: var(--text-primary, #e8ebf0); border: 1px solid var(--border-light, #2a2e3a); caret-color: var(--accent, #6ea8fe); }
.inp::placeholder { color: var(--text-muted, #a3acbb); opacity: 1; }
.inp.sm { flex: 0 0 auto; width: 90px; }
textarea.inp { resize: vertical; font-family: inherit; line-height: 1.5; }
.template-field { display: flex; flex-direction: column; gap: 8px; font-size: 13px; color: var(--text-secondary, #b9c0cc); }
.template-field textarea { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
.inp[aria-invalid='true'] { border-color: var(--danger, #ff8585); }
.field-error { margin: 0; font-size: 12px; color: var(--danger, #ff8585); line-height: 1.6; overflow-wrap: anywhere; }
.load-error { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 12px; border: 1px solid var(--danger, #ff8585); border-radius: 8px; }
.load-error p { flex: 1 1 240px; margin: 0; font-size: 13px; line-height: 1.6; overflow-wrap: anywhere; }
.btn { padding: 7px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; background: var(--bg-card, #12141c); color: var(--text-secondary, #b9c0cc); border: 1px solid var(--border-light, #2a2e3a); }
.btn:hover { border-color: var(--accent, #6ea8fe); color: var(--accent, #6ea8fe); }
.btn.primary { background: var(--accent-dim, #1e3a5f); border-color: var(--accent, #6ea8fe); color: var(--accent, #6ea8fe); }
.btn.danger:hover { border-color: var(--danger, #ff8585); color: var(--danger, #ff8585); }
.btn.lg { padding: 9px 22px; }
button:disabled { opacity: 0.5; cursor: not-allowed; }
button:focus-visible, .inp:focus-visible { outline: 2px solid var(--accent, #6ea8fe); outline-offset: 3px; }
.savebar { position: sticky; bottom: 0; display: flex; justify-content: flex-end; padding-top: 4px; }
.toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.grow { flex: 1; }
.muted { font-size: 12px; color: var(--text-muted, #a3acbb); }
.muted.center { text-align: center; padding: 40px 0; }
.empty { text-align: center; padding: 48px 0; font-size: 15px; color: var(--text-secondary, #b9c0cc); }
.mem-layout { display: flex; gap: 14px; align-items: flex-start; }
.mem-list { flex: 0 0 240px; min-width: 0; display: flex; flex-direction: column; gap: 8px; max-height: 460px; overflow-y: auto; }
.mem-item { text-align: left; padding: 10px; border-radius: 8px; background: var(--bg-elevated, #1a1d27); border: 1px solid var(--border-light, #2a2e3a); display: flex; flex-direction: column; gap: 4px; }
.mem-item:hover { border-color: var(--accent, #6ea8fe); }
.mem-item.on { border-color: var(--accent, #6ea8fe); background: var(--accent-dim, #1e3a5f); }
.mem-open { display: flex; flex-direction: column; gap: 4px; width: 100%; min-width: 0; border: 0; padding: 0; background: none; text-align: left; cursor: pointer; }
.mem-h { display: flex; gap: 6px; align-items: center; }
.mem-type { font-size: 11px; padding: 1px 6px; border-radius: 4px; background: var(--bg-card, #12141c); color: var(--text-secondary, #b9c0cc); flex: 0 0 auto; }
.mem-id { font-size: 12px; color: var(--text-primary, #e8ebf0); overflow-wrap: anywhere; }
.mem-last { display: block; max-width: 100%; font-size: 12px; color: var(--text-secondary, #b9c0cc); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mem-meta { font-size: 11px; color: var(--text-muted, #a3acbb); }
.lnk { padding: 0; border: 0; background: none; font: inherit; color: var(--danger, #ff8585); cursor: pointer; text-decoration: underline; text-underline-offset: 3px; }
.mem-detail { flex: 1; min-width: 0; min-height: 200px; padding: 12px; border-radius: 10px; background: var(--bg-elevated, #1a1d27); border: 1px solid var(--border-light, #2a2e3a); }
.chat { display: flex; flex-direction: column; gap: 10px; }
.bubble { max-width: 80%; padding: 8px 12px; border-radius: 10px; }
.bubble.user { align-self: flex-start; background: var(--bg-card, #12141c); }
.bubble.assistant { align-self: flex-end; background: var(--accent-dim, #1e3a5f); }
.bubble-role { font-size: 10px; color: var(--text-muted, #a3acbb); margin-bottom: 3px; }
.bubble-text { font-size: 13px; color: var(--text-primary, #e8ebf0); white-space: pre-wrap; overflow-wrap: anywhere; }
.ai ::selection { background: var(--accent-dim, #1e3a5f); color: var(--text-primary, #e8ebf0); }
@container (max-width: 620px) {
  .layout, .mem-layout { flex-direction: column; }
  .sidebar { flex-basis: auto; width: 100%; flex-direction: row; flex-wrap: wrap; align-items: center; gap: 6px; }
  .side-title { display: none; }
  .mem-list { flex-basis: auto; width: 100%; max-height: 220px; }
  .mem-detail { width: 100%; }
  .inp { font-size: 16px; }
  .row:has(.hint) { flex-wrap: wrap; }
  .chat-names { margin-left: 0; }
  .row.top { flex-direction: column; align-items: stretch; gap: 6px; }
}
</style>
