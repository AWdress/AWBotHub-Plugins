<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

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
  <IosSettings>
  <div class="ai-ios">
    <div v-if="loading" class="ai-ios-muted" role="status">加载配置…</div>
    <template v-else>
      <div class="ai-ios-tabs" :style="{ '--ai-ios-tab-index': tab === 'settings' ? 0 : 1 }" aria-label="AI 助手页面">
        <button type="button" :class="['ai-ios-tab', { on: tab === 'settings' }]" :aria-pressed="tab === 'settings'" @click="switchTab('settings')"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h9m4 0h3M4 17h3m4 0h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/></svg>功能设置</button>
        <button type="button" :class="['ai-ios-tab', { on: tab === 'memory' }]" :aria-pressed="tab === 'memory'" @click="switchTab('memory')"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16v12H9l-5 4zM8 8h8m-8 4h5"/></svg>对话记忆</button>
      </div>
      <div v-if="loadError" class="ai-ios-load-error" role="alert">
        <p>{{ loadError }}。未加载成功前不能保存，以免覆盖原设置。</p>
        <button type="button" class="ai-ios-button" @click="loadConfig">重新读取配置</button>
      </div>
      <div v-show="tab === 'settings'" class="ai-ios-layout">
        <aside class="ai-ios-sidebar" aria-label="设置分组">
                    <button v-for="item in GROUPS" :key="item.key" type="button" :class="['ai-ios-side-item', { on: group === item.key }]" :aria-pressed="group === item.key" @click="group = item.key">
            <span>{{ item.label }}</span><span v-if="item.en && cfg[item.en]" class="ai-ios-dot" aria-label="已开启"></span>
          </button>
        </aside>
        <div class="ai-ios-detail">
          <template v-if="group === 'image'">
            <h3 class="ai-ios-title">AI 生图</h3>
            <section class="ai-ios-group">
              <label class="ai-ios-row ai-ios-switch"><span class="ai-ios-toggle"><input v-model="cfg.enable_image_generation" type="checkbox" role="switch" /><span class="ai-ios-toggle-track" aria-hidden="true"></span></span><span>启用 AI 生图命令</span></label>
              <p class="ai-ios-tip">发送 /生图 画面描述 或 /draw prompt，生成后会直接把图片发到当前会话（使用平台统一 AI 服务）。</p>
              <template v-if="cfg.enable_image_generation">
                <div class="ai-ios-grid">
                  <label class="ai-ios-row"><span>图片尺寸</span><select v-model="cfg.image_size" class="ai-ios-input">
                    <option value="1024x1024">1024 × 1024</option><option value="1536x1024">1536 × 1024（横图）</option><option value="1024x1536">1024 × 1536（竖图）</option><option value="1792x1024">1792 × 1024（DALL·E 3 横图）</option><option value="1024x1792">1024 × 1792（DALL·E 3 竖图）</option>
                  </select></label>
                  <label class="ai-ios-row"><span>生成质量</span><select v-model="cfg.image_quality" class="ai-ios-input">
                    <option value="auto">自动</option><option value="low">低</option><option value="medium">中</option><option value="high">高</option><option value="standard">标准（DALL·E）</option><option value="hd">高清（DALL·E）</option>
                  </select></label>
                </div>
                <p class="ai-ios-tip">不同模型支持的尺寸和质量可能不同；不确定时质量选“自动”、尺寸选 1024 × 1024。</p>
              </template>
            </section>
          </template>
          <template v-else-if="group === 'human'">
            <h3 class="ai-ios-title">人形回复</h3>
            <section class="ai-ios-group">
              <label class="ai-ios-row ai-ios-switch"><span class="ai-ios-toggle"><input v-model="cfg.enable_private_chat" type="checkbox" role="switch" /><span class="ai-ios-toggle-track" aria-hidden="true"></span></span><span>私聊回复（私聊里直接对话）</span></label>
              <label class="ai-ios-row ai-ios-switch"><span class="ai-ios-toggle"><input v-model="cfg.enable_group_chat" type="checkbox" role="switch" /><span class="ai-ios-toggle-track" aria-hidden="true"></span></span><span>群聊回复（群里 @你 或回复你的消息时对话）</span></label>
              <label v-if="cfg.enable_group_chat" class="ai-ios-row ai-ios-stacked"><span>生效群组</span><textarea v-model="cfg.group_chat_ids" class="ai-ios-input" rows="2" placeholder="群ID逗号分隔，留空=所有群"></textarea></label>
              <div v-if="chatNames.length" class="ai-ios-chat-names">已识别：<span v-for="item in chatNames" :key="item.id">{{ item.title }} ({{ item.id }})</span></div>
              <label class="ai-ios-row ai-ios-stacked"><span>人设</span><textarea v-model="cfg.system_prompt" class="ai-ios-input" rows="8" placeholder="系统提示词"></textarea></label>
              <label class="ai-ios-row"><span>记忆条数</span><input v-model.number="cfg.max_history" class="ai-ios-input ai-ios-small" type="number" min="0" max="40" /><span class="ai-ios-hint">每会话保留多少条历史，0=不记忆</span></label>
            </section>
          </template>
          <template v-else-if="group === 'proactive'">
            <h3 class="ai-ios-title">随机主动搭话</h3>
            <section class="ai-ios-group">
              <label class="ai-ios-row ai-ios-switch"><span class="ai-ios-toggle"><input v-model="cfg.enable_proactive" type="checkbox" role="switch" /><span class="ai-ios-toggle-track" aria-hidden="true"></span></span><span>开启随机主动搭话</span></label>
              <p class="ai-ios-tip">在下方群组里每隔随机时间挑一条群友近期消息主动接话开启话题；群友回复你后走人形对话续聊（需“群聊回复”开着）。开启后请重载或重新启用插件。</p>
              <template v-if="cfg.enable_proactive">
                <label class="ai-ios-row ai-ios-stacked"><span>搭话群组</span><textarea v-model="cfg.proactive_chat_ids" class="ai-ios-input" rows="2" placeholder="群ID逗号分隔，必填"></textarea></label>
                <div v-if="chatNames.length" class="ai-ios-chat-names">已识别：<span v-for="item in chatNames" :key="item.id">{{ item.title }} ({{ item.id }})</span></div>
                <div class="ai-ios-grid">
                  <label class="ai-ios-row"><span>间隔最小</span><input v-model.number="cfg.proactive_min_minutes" class="ai-ios-input ai-ios-small" type="number" min="5" max="720" /><span class="ai-ios-hint">分钟</span></label>
                  <label class="ai-ios-row"><span>间隔最大</span><input v-model.number="cfg.proactive_max_minutes" class="ai-ios-input ai-ios-small" type="number" min="5" max="1440" /><span class="ai-ios-hint">分钟</span></label>
                </div>
              </template>
            </section>
          </template>
          <template v-else-if="group === 'explain'">
            <h3 class="ai-ios-title">/ai 解释命令</h3>
            <section class="ai-ios-group">
              <label class="ai-ios-row ai-ios-switch"><span class="ai-ios-toggle"><input v-model="cfg.enable_explain_command" type="checkbox" role="switch" /><span class="ai-ios-toggle-track" aria-hidden="true"></span></span><span>启用 /ai 解释命令</span></label>
              <p class="ai-ios-tip">回复一条消息（或图片）再发 /ai，让 AI 解释/解答（单次，无记忆）。</p>
              <template v-if="cfg.enable_explain_command">
                <label class="ai-ios-row ai-ios-switch"><span class="ai-ios-toggle"><input v-model="cfg.enable_explain_prompt" type="checkbox" role="switch" /><span class="ai-ios-toggle-track" aria-hidden="true"></span></span><span>用解释模板（否则直接把内容交给 AI）</span></label>
                <label v-if="cfg.enable_explain_prompt" class="ai-ios-row ai-ios-stacked"><span>解释模板</span><textarea v-model="cfg.explain_prompt" class="ai-ios-input" rows="6" placeholder="用 {content} 占位被解释的内容"></textarea></label>
              </template>
            </section>
          </template>
          <template v-else-if="group === 'reply'">
            <h3 class="ai-ios-title">回复格式</h3>
            <section class="ai-ios-group">
              <label class="ai-ios-row ai-ios-switch"><span class="ai-ios-toggle"><input v-model="cfg.enable_rich_reply" type="checkbox" role="switch" /><span class="ai-ios-toggle-track" aria-hidden="true"></span></span><span>优先使用 Telegram 原生富文本</span></label>
              <p class="ai-ios-tip">默认开启。非会员或原生能力不可用时，自动降级为可读的普通格式，保留正文和完整链接；网络发送结果不明确时不自动重发，避免重复消息。</p>
              <p class="ai-ios-tip">模板支持 Markdown 粗体、引用、代码块和表格；关闭原生富文本后仍会使用可读格式。这里控制回答的显示样式，不改变模型人设。</p>
              <label class="ai-ios-template-field" for="ai-reply-template"><span>普通回复模板</span><textarea id="ai-reply-template" ref="replyInput" v-model="cfg.reply_template" class="ai-ios-input ai-ios-code-input" rows="5" :placeholder="DEFAULTS.reply_template" :aria-invalid="!!replyError" aria-describedby="ai-reply-template-hint ai-reply-template-error"></textarea></label>
              <p id="ai-reply-template-hint" class="ai-ios-tip">用 {answer} 放入完整回答，{question} 放入本次问题；留空使用默认模板。</p>
              <p v-if="replyError" id="ai-reply-template-error" class="ai-ios-field-error" role="alert">{{ replyError }}</p>
              <label class="ai-ios-template-field" for="ai-explain-reply-template"><span>/ai 解释回复模板</span><textarea id="ai-explain-reply-template" ref="explainReplyInput" v-model="cfg.explain_reply_template" class="ai-ios-input ai-ios-code-input" rows="8" :placeholder="DEFAULTS.explain_reply_template" :aria-invalid="!!explainReplyError" aria-describedby="ai-explain-reply-template-hint ai-explain-reply-template-error"></textarea></label>
              <p id="ai-explain-reply-template-hint" class="ai-ios-tip">用 {question} 引用原消息，{answer} 放入完整回答；留空恢复默认的“问题／回答”排版。</p>
              <p v-if="explainReplyError" id="ai-explain-reply-template-error" class="ai-ios-field-error" role="alert">{{ explainReplyError }}</p>
              <p class="ai-ios-tip">模型回答中的完整网址会保留。链接来自模型文本，不代表插件已联网搜索或核验来源。</p>
            </section>
          </template>
          <template v-else-if="group === 'scope'">
            <h3 class="ai-ios-title">生效范围</h3>
            <section class="ai-ios-group">
              <label class="ai-ios-row ai-ios-stacked"><span>会话白名单</span><textarea v-model="cfg.white_list_chats" class="ai-ios-input" rows="2" placeholder="会话ID逗号分隔，留空=所有会话"></textarea></label>
              <div v-if="chatNames.length" class="ai-ios-chat-names">已识别：<span v-for="item in chatNames" :key="item.id">{{ item.title }} ({{ item.id }})</span></div>
            </section>
          </template>
          <div class="ai-ios-savebar"><button type="button" class="ai-ios-button ai-ios-primary ai-ios-large" :disabled="saving || !configReady" @click="save">{{ saving ? '保存中…' : '保存配置' }}</button></div>
        </div>
      </div>
      <div v-show="tab === 'memory'" class="ai-ios-pane">
        <div class="ai-ios-toolbar"><span class="ai-ios-muted">下次主动搭话：{{ proactiveNext || '—' }}</span><span class="ai-ios-grow"></span><button type="button" class="ai-ios-button" :disabled="histLoading || clearing" @click="loadHistories">刷新</button><button type="button" class="ai-ios-button ai-ios-danger" :disabled="!histories.length || clearing || histLoading" @click="clearAll">{{ clearing ? '清空中…' : '全部清空' }}</button></div>
        <div v-if="histLoading" class="ai-ios-muted" role="status">加载中…</div>
        <p v-else-if="historyError" class="ai-ios-field-error" role="alert">{{ historyError }}，请点击“刷新”重试。</p>
        <div v-else-if="!histories.length" class="ai-ios-empty">暂无对话记忆<br /><span class="ai-ios-muted">私聊/群@你对话后会在这里记录会话记忆</span></div>
        <div v-else class="ai-ios-mem-layout">
          <div class="ai-ios-mem-list">
            <div v-for="item in histories" :key="item.chat_id" :class="['ai-ios-mem-item', { on: activeChat?.chat_id === item.chat_id }]">
              <button type="button" class="ai-ios-mem-open" @click="openChat(item)"><span class="ai-ios-mem-h"><span class="ai-ios-mem-type">{{ item.is_private ? '私聊' : '群' }}</span><span class="ai-ios-mem-id">{{ item.chat_title || item.chat_id }} ({{ item.chat_id }})</span></span><span class="ai-ios-mem-last">{{ item.last || '—' }}</span></button>
              <div class="ai-ios-mem-meta">{{ item.count }} 条 · <button type="button" class="ai-ios-link" :disabled="clearing" @click="clearChat(item)">清空</button></div>
            </div>
          </div>
          <div class="ai-ios-mem-detail">
            <div v-if="!activeChat" class="ai-ios-muted ai-ios-center">选择一个会话查看历史</div>
            <div v-else-if="msgLoading" class="ai-ios-muted" role="status">加载中…</div>
            <p v-else-if="messageError" class="ai-ios-field-error" role="alert">{{ messageError }}</p>
            <div v-else class="ai-ios-chat"><div v-for="(message, index) in chatMessages" :key="index" :class="['ai-ios-bubble', message.role]"><div class="ai-ios-bubble-role">{{ message.role === 'user' ? '对方' : '我' }}</div><div class="ai-ios-bubble-text">{{ message.content }}</div></div></div>
          </div>
        </div>
      </div>
    </template>
  </div>
  </IosSettings>
</template>

<style scoped>
.ai-ios { display: flex; flex-direction: column; gap: 24px; min-width: 0; color: var(--ios-text); }
.ai-ios *, .ai-ios *::before, .ai-ios *::after { box-sizing: border-box; }
.ai-ios svg { width: 19px; height: 19px; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; flex: none; }
.ai-ios-tabs { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); position: relative; isolation: isolate; gap: 4px; padding: 4px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-inset); }
.ai-ios-tabs::before { content: ''; position: absolute; inset: 4px auto 4px 4px; width: calc((100% - 12px) / 2); border-radius: 11px; background: var(--ios-control); box-shadow: 0 2px 5px rgb(0 0 0 / .08); transform: translateX(calc(var(--ai-ios-tab-index) * (100% + 4px))); transition: transform var(--ios-duration) var(--ios-ease); z-index: -1; }
.ai-ios-tab { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 42px; padding: 8px 12px; border: 0; border-radius: 11px; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.ai-ios-tab.on { color: var(--ios-text); font-weight: 650; }
.ai-ios-tab:hover { color: var(--ios-text); }
.ai-ios-layout { display: grid; grid-template-columns: 150px minmax(0, 1fr); align-items: start; gap: 24px; min-width: 0; }
.ai-ios-sidebar { display: flex; flex-direction: column; gap: 4px; min-width: 0; padding: 6px; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-inset); }
.ai-ios-side-item { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 44px; padding: 9px 12px; border: 0; border-radius: 12px; background: transparent; color: var(--ios-secondary); text-align: left; cursor: pointer; }
.ai-ios-side-item:hover { color: var(--ios-text); background: var(--ios-control); }
.ai-ios-side-item.on { color: var(--ios-text); background: var(--ios-control); font-weight: 600; box-shadow: 0 2px 4px rgb(0 0 0 / .06); }
.ai-ios-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--success, #087758); flex: none; }
.ai-ios-detail { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.ai-ios-title { margin: 0; font-size: 16px; font-weight: 650; line-height: 1.5; letter-spacing: -.015em; color: var(--ios-text); }
.ai-ios-group { display: flex; flex-direction: column; overflow: hidden; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-surface); }
.ai-ios-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; min-height: 72px; padding: 17px 20px; }
.ai-ios-row + .ai-ios-row, .ai-ios-row + .ai-ios-grid, .ai-ios-grid + .ai-ios-row { border-top: 1px solid var(--ios-line); }
.ai-ios-row > span:first-child:not(.ai-ios-toggle) { min-width: 80px; font-size: 14px; color: var(--ios-text); }
.ai-ios-row > .ai-ios-hint { min-width: 0; }
.ai-ios-row.ai-ios-stacked { flex-direction: column; align-items: stretch; gap: 12px; }
.ai-ios-switch { cursor: pointer; }
.ai-ios-switch > span:not(.ai-ios-toggle) { flex: 1; min-width: 0; order: 1; }
.ai-ios-switch > .ai-ios-toggle { order: 2; }
.ai-ios-toggle { position: relative; display: inline-flex; align-items: center; flex: 0 0 50px; width: 50px; min-height: 44px; }
.ai-ios-toggle input { position: absolute; width: 1px; height: 1px; margin: 0; padding: 0; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.ai-ios-toggle-track { position: relative; display: block; width: 50px; height: 30px; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); transition: background var(--ios-fast) ease, border-color var(--ios-fast) ease; }
.ai-ios-toggle-track::after { content: ''; position: absolute; top: 2px; left: 2px; width: 24px; height: 24px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .2); transition: transform var(--ios-duration) var(--ios-ease); }
.ai-ios-toggle input:checked + .ai-ios-toggle-track { border-color: transparent; background: var(--ios-accent); }
.ai-ios-toggle input:checked + .ai-ios-toggle-track::after { transform: translateX(20px); }
.ai-ios-switch:active .ai-ios-toggle-track::after { transform: scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.ai-ios-switch:active input:checked + .ai-ios-toggle-track::after { transform: translateX(20px) scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.ai-ios-toggle input:focus-visible + .ai-ios-toggle-track { outline: 3px solid var(--accent, #0063dc); outline-offset: 3px; }
.ai-ios-grid { display: grid; grid-template-columns: minmax(0, 1fr); }
.ai-ios-grid > .ai-ios-row + .ai-ios-row { border-top: 1px solid var(--ios-line); }
.ai-ios-input { flex: 1; width: 100%; min-width: 0; max-width: 260px; min-height: 42px; padding: 9px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-text); transition: border-color var(--ios-fast) ease; }
.ai-ios-input:focus { border-color: var(--accent, #0063dc); }
.ai-ios-input.ai-ios-small { flex: 0 0 86px; width: 86px; text-align: center; font-variant-numeric: tabular-nums; }
.ai-ios-input[aria-invalid='true'] { border-color: var(--danger, #bd2733); }
.ai-ios-stacked .ai-ios-input { max-width: none; }
.ai-ios textarea { resize: vertical; line-height: 1.75; }
.ai-ios-hint, .ai-ios-tip, .ai-ios-muted { font-size: 12px; font-weight: 400; color: var(--ios-secondary); line-height: 1.75; overflow-wrap: anywhere; }
.ai-ios-tip { margin: 0; padding: 0 20px 16px; max-width: 75ch; }
.ai-ios-row:has(+ .ai-ios-tip) { padding-bottom: 10px; }
.ai-ios-chat-names { display: flex; flex-wrap: wrap; gap: 6px; margin: 0; padding: 0 20px 16px; font-size: 12px; color: var(--ios-secondary); overflow-wrap: anywhere; }
.ai-ios-chat-names > span { padding: 3px 7px; border-radius: 7px; background: var(--ios-inset); color: var(--ios-text); }
.ai-ios-template-field { display: flex; flex-direction: column; gap: 12px; padding: 18px 20px 12px; border-top: 1px solid var(--ios-line); font-size: 14px; color: var(--ios-text); }
.ai-ios-template-field .ai-ios-input { max-width: none; font-family: var(--font-mono, ui-monospace, monospace); font-size: 13px; }
.ai-ios-field-error { margin: 0; font-size: 12px; line-height: 1.75; color: var(--danger, #bd2733); overflow-wrap: anywhere; }
.ai-ios-group > .ai-ios-field-error { padding: 0 20px 16px; }
.ai-ios-load-error { display: flex; flex-wrap: wrap; align-items: center; gap: 14px; padding: 18px 20px; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-surface); color: var(--danger, #bd2733); }
.ai-ios-load-error p { flex: 1 1 240px; margin: 0; font-size: 13px; line-height: 1.75; overflow-wrap: anywhere; }
.ai-ios-button { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; padding: 9px 18px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font-weight: 500; cursor: pointer; }
.ai-ios-button:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.ai-ios-button.ai-ios-primary { min-width: 132px; border-color: transparent; background: var(--ios-accent); color: #fff; font-weight: 600; }
.ai-ios-primary:hover:not(:disabled) { filter: brightness(1.08); }
.ai-ios-button.ai-ios-danger { color: var(--danger, #bd2733); }
.ai-ios-button.ai-ios-danger:hover:not(:disabled) { border-color: var(--danger, #bd2733); }
.ai-ios button:disabled { opacity: .5; }
.ai-ios-savebar { display: flex; justify-content: flex-end; padding-top: 8px; }
.ai-ios-pane { display: flex; flex-direction: column; gap: 18px; min-width: 0; }
.ai-ios-toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
.ai-ios-grow { flex: 1; }
.ai-ios-empty { padding: 42px 24px; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-surface); text-align: center; color: var(--ios-text); }
.ai-ios-empty .ai-ios-muted { display: inline-block; margin-top: 7px; }
.ai-ios-center { display: grid; place-items: center; min-height: 250px; text-align: center; padding: 20px; }
.ai-ios-mem-layout { display: grid; grid-template-columns: minmax(180px, .8fr) minmax(0, 1.2fr); align-items: start; gap: 18px; min-width: 0; }
.ai-ios-mem-list { display: flex; flex-direction: column; max-height: 520px; overflow-y: auto; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); scrollbar-width: thin; scrollbar-color: var(--border-light, #b9bec9) transparent; }
.ai-ios-mem-item { display: flex; flex-direction: column; gap: 7px; min-width: 0; padding: 15px; }
.ai-ios-mem-item + .ai-ios-mem-item { border-top: 1px solid var(--ios-line); }
.ai-ios-mem-item.on { background: var(--ios-inset); }
.ai-ios-mem-open { display: flex; flex-direction: column; gap: 8px; width: 100%; min-width: 0; padding: 0; border: 0; border-radius: 8px; background: transparent; color: inherit; text-align: left; cursor: pointer; }
.ai-ios-mem-open:hover { color: var(--accent, #0063dc); }
.ai-ios-mem-h { display: flex; align-items: flex-start; gap: 7px; }
.ai-ios-mem-type { flex: none; padding: 2px 6px; border-radius: 6px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 11px; }
.ai-ios-mem-item.on .ai-ios-mem-type { background: var(--ios-control); }
.ai-ios-mem-id { min-width: 0; color: var(--ios-text); font-size: 13px; font-weight: 500; overflow-wrap: anywhere; }
.ai-ios-mem-last { display: block; width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--ios-secondary); font-size: 12px; }
.ai-ios-mem-meta { color: var(--ios-secondary); font-size: 12px; font-variant-numeric: tabular-nums; }
.ai-ios-link { min-height: 30px; padding: 2px 5px; border: 0; border-radius: 6px; background: transparent; color: var(--danger, #bd2733); cursor: pointer; text-decoration: underline; text-underline-offset: 3px; }
.ai-ios-mem-detail { min-width: 0; min-height: 290px; max-height: 620px; overflow-y: auto; padding: 18px; border: 1px solid var(--ios-line); border-radius: 18px; background: var(--ios-inset); scrollbar-width: thin; scrollbar-color: var(--border-light, #b9bec9) transparent; }
.ai-ios-chat { display: flex; flex-direction: column; gap: 16px; }
.ai-ios-bubble { max-width: 90%; padding: 12px 15px; border-radius: 17px; }
.ai-ios-bubble.user { align-self: flex-start; border-bottom-left-radius: 5px; background: var(--ios-control); }
.ai-ios-bubble.assistant { align-self: flex-end; border-bottom-right-radius: 5px; background: var(--accent-dim, #e8f1ff); }
.ai-ios-bubble-role { margin-bottom: 5px; color: var(--ios-secondary); font-size: 11px; }
.ai-ios-bubble-text { color: var(--ios-text); font-size: 13px; line-height: 1.8; white-space: pre-wrap; overflow-wrap: anywhere; }
:global(html[data-theme='transparent'] .ai-ios-group),
:global(html[data-theme='transparent'] .ai-ios-load-error),
:global(html[data-theme='transparent'] .ai-ios-empty),
:global(html[data-theme='transparent'] .ai-ios-mem-list) { backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); -webkit-backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); }
@container (max-width: 620px) {
  .ai-ios { gap: 20px; }
  .ai-ios-layout { grid-template-columns: minmax(0, 1fr); gap: 20px; }
  .ai-ios-sidebar { flex-direction: row; flex-wrap: wrap; gap: 4px; padding: 5px; border-radius: 16px; }
  .ai-ios-side-item { flex: 1 1 auto; justify-content: center; min-height: 40px; padding: 8px 11px; font-size: 13px; }
  .ai-ios-row, .ai-ios-template-field { padding-inline: 16px; }
  .ai-ios-row:not(.ai-ios-switch) { flex-wrap: wrap; gap: 12px; }
  .ai-ios-row > .ai-ios-input:not(.ai-ios-small) { flex-basis: 100%; max-width: none; }
  .ai-ios-row > .ai-ios-hint { flex: 1 1 100%; }
  .ai-ios-chat-names, .ai-ios-tip, .ai-ios-group > .ai-ios-field-error { padding-inline: 16px; }
  .ai-ios-input { font-size: 16px; }
  .ai-ios-savebar .ai-ios-primary { width: 100%; }
  .ai-ios-toolbar > .ai-ios-muted { flex-basis: 100%; }
  .ai-ios-toolbar > .ai-ios-grow { display: none; }
  .ai-ios-mem-layout { grid-template-columns: minmax(0, 1fr); }
  .ai-ios-mem-list { max-height: 240px; }
  .ai-ios-mem-detail { min-height: 250px; max-height: 540px; padding: 15px; }
}
@container (max-width: 350px) {
  .ai-ios-tab { gap: 6px; padding-inline: 8px; }
  .ai-ios-row, .ai-ios-switch { gap: 12px; }
  .ai-ios-toolbar .ai-ios-button { flex: 1; padding-inline: 12px; }
}
@media (forced-colors: active) {
  .ai-ios-toggle input { position: static; width: 24px; height: 24px; clip-path: none; }
  .ai-ios-toggle-track { display: none; }
  .ai-ios-tabs::before { border: 2px solid Highlight; }
}
</style>
