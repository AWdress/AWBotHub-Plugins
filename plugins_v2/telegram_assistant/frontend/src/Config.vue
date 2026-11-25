<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

const props = defineProps({
  pluginId: {type: String, required: true},
  host: {type: Object, required: true},
})

const TABS = [
  {key: 'forward', label: '消息转发'},
  {key: 'tools', label: '消息工具'},
  {key: 'avatar', label: '自动头像'},
  {key: 'nickname', label: '报时昵称'},
]
const MESSAGE_TYPES = [
  {value: 'text', label: '文本'},
  {value: 'link', label: '链接'},
  {value: 'photo', label: '图片'},
  {value: 'video', label: '视频'},
  {value: 'document', label: '文件'},
  {value: 'audio', label: '音频'},
]

function defaults() {
  return {
    forward_enable: false,
    forward_album: false,
    forward_backfill_limit: 50,
    forward_auto_backfill: false,
    forward_backfill_interval_min: 60,
    forward_repeat_enabled: false,
    forward_repeat_command: '.zf',
    forward_repeat_mode: false,
    forward_repeat_interval: 0.3,
    forward_repeat_max_times: 50,
    forward_rules: [],
    forward_resolved_chat_names: '',
    delete_enabled: false,
    delete_command: '.dme',
    delete_tip_seconds: 2,
    id_enabled: false,
    id_delete_command: false,
    id_command: '.id',
    id_auto_delete: 20,
    getmsg_enabled: false,
    getmsg_delete_command: false,
    getmsg_command: '.getmsg',
    sticker_enabled: false,
    sticker_command: '.贴图',
    sticker_delete_command: false,
    avatar_enabled: false,
    avatar_delete_old: false,
    avatar_interval_min: 60,
    avatar_add_command: '.avataradd',
    avatar_list_command: '.avatarlist',
    avatar_clear_command: '.avatarclear',
    nickname_enabled: false,
    nickname_interval_min: 5,
    nickname_name_format: '{boldH}:{boldM} {weather_icon} {temp}°C',
    nickname_name_field: 'last_name',
    nickname_location: 'Guangzhou',
    nickname_weather_interval: 30,
  }
}

const form = reactive(defaults())
const activeTab = ref('forward')
const loading = ref(true)
const saving = ref(false)
const backfilling = ref(false)
const startingHistory = ref(false)
const loadError = ref('')
const savedSnapshot = ref('')

function toast(type, message) {
  props.host.toast?.[type]?.(message)
}

function normalizeRule(rule = {}) {
  const interval = Number(rule.history_interval_sec ?? 3)
  return {
    source: String(rule.source || ''),
    targets: String(rule.targets || ''),
    types: Array.isArray(rule.types) ? rule.types.filter((value) => MESSAGE_TYPES.some((item) => item.value === value)) : [],
    kw: String(rule.kw || ''),
    nkw: String(rule.nkw || ''),
    sender: String(rule.sender || ''),
    copy: Boolean(rule.copy),
    pin: Boolean(rule.pin),
    history_enabled: Boolean(rule.history_enabled),
    history_interval_sec: Number.isFinite(interval) ? Math.min(3600, Math.max(1, interval)) : 3,
  }
}

function snapshot() {
  return JSON.stringify(form)
}

const dirty = computed(() => !loading.value && snapshot() !== savedSnapshot.value)
const enabledCount = computed(() => [
  form.forward_enable,
  form.forward_repeat_enabled,
  form.delete_enabled,
  form.id_enabled,
  form.getmsg_enabled,
  form.sticker_enabled,
  form.avatar_enabled,
  form.nickname_enabled,
].filter(Boolean).length)

function tabEnabled(key) {
  if (key === 'forward') return form.forward_enable || form.forward_repeat_enabled
  if (key === 'tools') return form.delete_enabled || form.id_enabled || form.getmsg_enabled || form.sticker_enabled
  if (key === 'avatar') return form.avatar_enabled
  return form.nickname_enabled
}

function addRule() {
  form.forward_rules.push(normalizeRule())
}

function removeRule(index) {
  form.forward_rules.splice(index, 1)
}

function validate() {
  if (form.forward_enable) {
    if (!form.forward_rules.length) {
      toast('error', '启用规则转发后至少需要一条转发规则')
      activeTab.value = 'forward'
      return false
    }
    const incomplete = form.forward_rules.findIndex((rule) => !rule.source.trim() || !rule.targets.trim())
    if (incomplete >= 0) {
      toast('error', `转发规则 ${incomplete + 1} 的来源或目标未填写`)
      activeTab.value = 'forward'
      return false
    }
  }
  const requiredCommands = [
    ['delete_enabled', 'delete_command', '删除消息'],
    ['id_enabled', 'id_command', '查 ID'],
    ['getmsg_enabled', 'getmsg_command', '消息结构'],
    ['sticker_enabled', 'sticker_command', '消息贴图'],
  ]
  for (const [enabled, command, label] of requiredCommands) {
    if (form[enabled] && !String(form[command] || '').trim()) {
      toast('error', `${label}命令不能为空`)
      activeTab.value = 'tools'
      return false
    }
  }
  if (form.avatar_enabled && [form.avatar_add_command, form.avatar_list_command, form.avatar_clear_command].some((value) => !String(value || '').trim())) {
    toast('error', '自动头像的图片池命令不能为空')
    activeTab.value = 'avatar'
    return false
  }
  if (form.nickname_enabled && (!String(form.nickname_name_format || '').trim() || !String(form.nickname_location || '').trim())) {
    toast('error', '报时昵称模板和天气城市不能为空')
    activeTab.value = 'nickname'
    return false
  }
  return true
}

function normalizeNumbers(payload) {
  const ranges = {
    forward_backfill_limit: [1, 500],
    forward_backfill_interval_min: [1, 1440],
    forward_repeat_interval: [0, 5],
    forward_repeat_max_times: [1, 500],
    delete_tip_seconds: [0, 10],
    id_auto_delete: [0, 120],
    avatar_interval_min: [10, 1440],
    nickname_interval_min: [1, 60],
    nickname_weather_interval: [10, 120],
  }
  for (const [key, [min, max]] of Object.entries(ranges)) {
    const value = Number(payload[key])
    payload[key] = Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : defaults()[key]
  }
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const saved = await props.host.getConfig()
    const initial = defaults()
    Object.assign(form, initial)
    for (const key of Object.keys(initial)) {
      if (saved && Object.hasOwn(saved, key)) form[key] = saved[key]
    }
    form.forward_rules = Array.isArray(saved?.forward_rules) ? saved.forward_rules.map(normalizeRule) : []
    savedSnapshot.value = snapshot()
  } catch (error) {
    loadError.value = `读取配置失败：${error.message || error}`
  } finally {
    loading.value = false
  }
}

async function save() {
  if (loadError.value) {
    toast('error', '配置尚未成功读取，请刷新后重试')
    return
  }
  if (!validate()) return
  saving.value = true
  try {
    const payload = JSON.parse(JSON.stringify(form))
    payload.forward_rules = payload.forward_rules.map(normalizeRule)
    normalizeNumbers(payload)
    await props.host.saveConfig(payload)
    Object.assign(form, payload)
    savedSnapshot.value = snapshot()
    toast('success', 'Telegram 助手配置已保存并应用')
  } catch (error) {
    toast('error', `保存失败：${error.message || error}`)
  } finally {
    saving.value = false
  }
}

async function runBackfill() {
  if (dirty.value) {
    toast('error', '请先保存当前修改，再立即检查遗漏')
    return
  }
  if (!form.forward_enable || !form.forward_rules.length || backfilling.value) return
  backfilling.value = true
  try {
    const result = await props.host.callApi('/backfill', {method: 'POST', body: {}})
    toast(result?.ok === false ? 'error' : 'success', result?.message || '遗漏检查已启动')
  } catch (error) {
    toast('error', `启动遗漏检查失败：${error.message || error}`)
  } finally {
    backfilling.value = false
  }
}

async function runHistory() {
  if (dirty.value) {
    toast('error', '请先保存当前修改，再继续全量转发')
    return
  }
  startingHistory.value = true
  try {
    const result = await props.host.callApi('/history', {method: 'POST', body: {}})
    toast(result?.ok === false ? 'error' : 'success', result?.message || '全量转发已启动')
  } catch (error) {
    toast('error', `启动全量转发失败：${error.message || error}`)
  } finally {
    startingHistory.value = false
  }
}

onMounted(load)
</script>

<template>
  <IosSettings>
  <main class="tga-shell">
    <header class="tga-page-head">
      <div>
        <h2>Telegram 助手</h2>
        <p>{{ enabledCount }} 个功能已启用</p>
      </div>
      <span v-if="!loading && !loadError" class="tga-save-state" :class="{changed: dirty}">{{ dirty ? '有未保存修改' : '配置已同步' }}</span>
    </header>

    <p v-if="loadError" class="tga-alert" role="alert">{{ loadError }}</p>
    <div v-if="loading" class="tga-loading" role="status">正在读取 Telegram 助手配置…</div>

    <div v-else class="tga-workspace">
      <nav class="tga-section-nav" :style="{ '--tga-tab-index': TABS.findIndex(item => item.key === activeTab) }" role="tablist" aria-label="Telegram 助手配置分组">
        <button
          v-for="item in TABS"
          :key="item.key"
          type="button"
          role="tab"
          :id="'tga-tab-' + item.key"
          :aria-controls="'tga-panel-' + item.key"
          :aria-selected="activeTab === item.key"
          :class="{active: activeTab === item.key}"
          @click="activeTab = item.key"
        >
          <span>{{ item.label }}</span>
          <i :class="{on: tabEnabled(item.key)}" aria-hidden="true"></i>
        </button>
      </nav>

      <section class="tga-panel" :id="'tga-panel-' + activeTab" role="tabpanel" :aria-labelledby="'tga-tab-' + activeTab">
        <template v-if="activeTab === 'forward'">
          <div class="tga-panel-head">
            <div><h3>消息转发</h3><p>规则转发和回复复读分别控制。</p></div>
          </div>

          <div class="tga-switch-grid">
            <label class="tga-switch"><span><b>规则转发</b><small>按来源、类型和关键词匹配消息</small></span><input v-model="form.forward_enable" type="checkbox" role="switch"><i aria-hidden="true"></i></label>
            <label class="tga-switch"><span><b>整组转发相册</b><small>相册消息保持为同一组</small></span><input v-model="form.forward_album" type="checkbox" role="switch"><i aria-hidden="true"></i></label>
            <label class="tga-switch"><span><b>自动检查遗漏</b><small>按设定间隔回查来源消息</small></span><input v-model="form.forward_auto_backfill" type="checkbox" role="switch"><i aria-hidden="true"></i></label>
            <label class="tga-switch"><span><b>回复复读</b><small>回复消息后按命令重复发送</small></span><input v-model="form.forward_repeat_enabled" type="checkbox" role="switch"><i aria-hidden="true"></i></label>
          </div>

          <div class="tga-subsection">
            <div class="tga-subsection-head">
              <div><h4>转发规则</h4><span>{{ form.forward_rules.length }} 条</span></div>
              <div class="tga-rule-actions"><button class="tga-secondary" type="button" :disabled="!form.forward_enable || !form.forward_rules.some(rule => rule.history_enabled) || startingHistory" @click="runHistory">{{ startingHistory ? '正在启动…' : '继续全量转发' }}</button><button class="tga-secondary" type="button" @click="addRule">添加规则</button></div>
            </div>
            <div v-if="!form.forward_rules.length" class="tga-empty">尚未添加转发规则</div>
            <div v-else class="tga-rule-list">
              <article v-for="(rule, index) in form.forward_rules" :key="index" class="tga-rule-item">
                <div class="tga-rule-head"><b>规则 {{ index + 1 }}</b><button class="tga-text-danger" type="button" @click="removeRule(index)">删除</button></div>
                <div class="tga-form-grid">
                  <label><span>来源会话</span><input v-model.trim="rule.source" placeholder="群组/频道 ID 或 @用户名"></label>
                  <label><span>转发目标</span><input v-model.trim="rule.targets" placeholder="用户、Bot、群组或频道，逗号分隔"></label>
                  <label><span>包含关键词</span><input v-model.trim="rule.kw" placeholder="留空为不限"></label>
                  <label><span>排除关键词</span><input v-model.trim="rule.nkw" placeholder="留空为不限"></label>
                  <label><span>限定发送者</span><input v-model.trim="rule.sender" placeholder="用户 ID 或用户名"></label>
                  <label class="tga-inline-check"><input v-model="rule.copy" type="checkbox" role="switch"><span>复制搬运，不显示转发来源</span></label>
                  <label class="tga-inline-check"><input v-model="rule.pin" type="checkbox" role="switch"><span>自动置顶</span></label>
                  <label class="tga-inline-check"><input v-model="rule.history_enabled" type="checkbox" role="switch"><span>全量转发历史消息</span></label>
                  <label><span>全量发送间隔（秒）</span><input v-model.number="rule.history_interval_sec" type="number" min="1" max="3600" step="1" :disabled="!rule.history_enabled"></label>
                  <p class="tga-rule-help tga-wide">自动置顶默认关闭。群组/频道需当前账号为管理员或创建者且有置顶权限；用户或 Bot 私聊仅置顶自己这一侧。相册只置顶第一条。</p>
                  <p class="tga-rule-help tga-wide">全量转发默认关闭，间隔默认 3 秒（1～3600 秒）。开启并保存后，从旧到新转发当时的历史，遵守本规则筛选；已转发内容跳过，重启后续传，完成后不重跑。关闭并保存可暂停；失败后点“继续全量转发”。Telegram 限速时会延长等待。</p>
                </div>
                <fieldset class="tga-type-field"><legend>消息类型</legend><label v-for="type in MESSAGE_TYPES" :key="type.value"><input v-model="rule.types" type="checkbox" :value="type.value"><span>{{ type.label }}</span></label></fieldset>
              </article>
            </div>
          </div>

          <div class="tga-subsection">
            <div class="tga-subsection-head"><div><h4>遗漏检查</h4></div><button class="tga-secondary" type="button" :disabled="!form.forward_enable || !form.forward_rules.length || backfilling" @click="runBackfill">{{ backfilling ? '正在启动…' : '立即检查遗漏' }}</button></div>
            <div class="tga-form-grid tga-three">
              <label><span>每次回查条数</span><input v-model.number="form.forward_backfill_limit" type="number" min="1" max="500"></label>
              <label><span>自动检查间隔（分钟）</span><input v-model.number="form.forward_backfill_interval_min" type="number" min="1" max="1440"></label>
              <label class="tga-wide"><span>已识别会话</span><input :value="form.forward_resolved_chat_names || '尚未识别'" readonly></label>
            </div>
          </div>

          <div class="tga-subsection">
            <div class="tga-subsection-head"><div><h4>回复复读</h4></div></div>
            <div class="tga-form-grid tga-three">
              <label><span>复读命令</span><input v-model.trim="form.forward_repeat_command"></label>
              <label><span>间隔（秒）</span><input v-model.number="form.forward_repeat_interval" type="number" min="0" max="5" step="0.1"></label>
              <label><span>最多次数</span><input v-model.number="form.forward_repeat_max_times" type="number" min="1" max="500"></label>
              <label class="tga-inline-check"><input v-model="form.forward_repeat_mode" type="checkbox" role="switch"><span>复制重发，不显示转发来源</span></label>
            </div>
          </div>
        </template>

        <template v-else-if="activeTab === 'tools'">
          <div class="tga-panel-head"><div><h3>消息工具</h3><p>每项工具独立启用和配置。</p></div></div>

          <div class="tga-feature-group">
            <label class="tga-feature-switch"><span><b>删除消息</b><small>删除当前会话中自己最近发送的消息</small></span><input v-model="form.delete_enabled" type="checkbox" role="switch"><i aria-hidden="true"></i></label>
            <div class="tga-form-grid">
              <label><span>删除命令</span><input v-model.trim="form.delete_command"></label>
              <label><span>提示停留（秒）</span><input v-model.number="form.delete_tip_seconds" type="number" min="0" max="10"></label>
            </div>
          </div>

          <div class="tga-feature-group">
            <label class="tga-feature-switch"><span><b>查 ID</b><small>查询当前会话、用户或回复消息的 ID</small></span><input v-model="form.id_enabled" type="checkbox" role="switch"><i aria-hidden="true"></i></label>
            <div class="tga-form-grid">
              <label><span>查询命令</span><input v-model.trim="form.id_command"></label>
              <label><span>结果自动删除（秒）</span><input v-model.number="form.id_auto_delete" type="number" min="0" max="120"></label>
              <label class="tga-inline-check"><input v-model="form.id_delete_command" type="checkbox" role="switch"><span>查询后删除命令消息</span></label>
            </div>
          </div>

          <div class="tga-feature-group">
            <label class="tga-feature-switch"><span><b>消息结构</b><small>将回复消息的 Telethon 结构导出到收藏夹</small></span><input v-model="form.getmsg_enabled" type="checkbox" role="switch"><i aria-hidden="true"></i></label>
            <div class="tga-form-grid">
              <label><span>导出命令</span><input v-model.trim="form.getmsg_command"></label>
              <label class="tga-inline-check"><input v-model="form.getmsg_delete_command" type="checkbox" role="switch"><span>导出后删除命令消息</span></label>
            </div>
          </div>

          <div class="tga-feature-group">
            <label class="tga-feature-switch"><span><b>消息贴图</b><small>把回复消息渲染为 Telegram 原生贴纸</small></span><input v-model="form.sticker_enabled" type="checkbox" role="switch"><i aria-hidden="true"></i></label>
            <div class="tga-form-grid">
              <label><span>贴图命令</span><input v-model.trim="form.sticker_command"></label>
              <label class="tga-inline-check"><input v-model="form.sticker_delete_command" type="checkbox" role="switch"><span>发送成功后删除命令</span></label>
            </div>
          </div>
        </template>

        <template v-else-if="activeTab === 'avatar'">
          <div class="tga-panel-head"><div><h3>自动头像</h3><p>管理头像图片池与轮换计划。</p></div></div>
          <label class="tga-feature-switch tga-primary-switch"><span><b>启用自动换头像</b><small>定时从当前账号的图片池随机更换头像</small></span><input v-model="form.avatar_enabled" type="checkbox" role="switch"><i aria-hidden="true"></i></label>
          <div class="tga-form-grid tga-avatar-grid">
            <label><span>换头像间隔（分钟）</span><input v-model.number="form.avatar_interval_min" type="number" min="10" max="1440" step="10"></label>
            <label class="tga-inline-check"><input v-model="form.avatar_delete_old" type="checkbox" role="switch"><span>更换后删除上一个插件头像</span></label>
            <label><span>添加图片命令</span><input v-model.trim="form.avatar_add_command"></label>
            <label><span>查看图片池命令</span><input v-model.trim="form.avatar_list_command"></label>
            <label><span>清空图片池命令</span><input v-model.trim="form.avatar_clear_command"></label>
          </div>
        </template>

        <template v-else>
          <div class="tga-panel-head"><div><h3>报时昵称</h3><p>按时间和天气更新 Telegram 姓名。</p></div></div>
          <label class="tga-feature-switch tga-primary-switch"><span><b>启用报时昵称</b><small>按设定间隔更新选定的姓名字段</small></span><input v-model="form.nickname_enabled" type="checkbox" role="switch"><i aria-hidden="true"></i></label>
          <div class="tga-form-grid tga-nickname-grid">
            <label class="tga-wide"><span>昵称模板</span><input v-model="form.nickname_name_format"></label>
            <label><span>修改字段</span><select v-model="form.nickname_name_field"><option value="last_name">姓</option><option value="first_name">名</option><option value="both">姓和名</option></select></label>
            <label><span>更新时间（分钟）</span><input v-model.number="form.nickname_interval_min" type="number" min="1" max="60"></label>
            <label><span>天气城市（英文）</span><input v-model.trim="form.nickname_location" placeholder="Guangzhou"></label>
            <label><span>天气刷新（分钟）</span><input v-model.number="form.nickname_weather_interval" type="number" min="10" max="120" step="5"></label>
            <p class="tga-template-help tga-wide">可用占位符：{boldH}、{boldM}、{H}、{M}、{weather_icon}、{temp}、{emoji}、{date}、{week}</p>
          </div>
        </template>
      </section>
    </div>

    <footer v-if="!loading" class="tga-save-bar">
      <span>{{ loadError ? '配置未读取成功，暂不可保存' : dirty ? '修改尚未保存' : '当前配置已保存' }}</span>
      <button class="tga-primary" type="button" :disabled="saving || !!loadError || !dirty" @click="save">{{ saving ? '正在保存…' : '保存配置' }}</button>
    </footer>
  </main>
  </IosSettings>
</template>

<style scoped>
/* iOS grouped settings. Shared IosSettings owns light/dark/glass tokens and motion.
   The original Telegram Assistant state, validation, API calls and bindings remain intact. */
.tga-shell { min-width: 0; color: var(--ios-text); font-size: 14px; line-height: 1.6; }
.tga-shell h2, .tga-shell h3, .tga-shell h4, .tga-shell p { margin: 0; }
.tga-page-head { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 4px 0 22px; }
.tga-page-head h2 { font-size: 22px; font-weight: 650; line-height: 1.4; letter-spacing: -.025em; }
.tga-page-head p, .tga-panel-head p { margin-top: 5px; color: var(--ios-secondary); font-size: 13px; }
.tga-save-state { flex: 0 0 auto; padding: 5px 9px; border-radius: 8px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 12px; }
.tga-save-state.changed { color: var(--warning, #946200); background: color-mix(in srgb, var(--warning, #946200) 10%, transparent); }
.tga-alert { margin-bottom: 20px !important; padding: 14px 18px; border: 1px solid var(--ios-line); border-radius: 16px; color: var(--danger, #bd2733); background: var(--ios-surface); font-size: 13px; overflow-wrap: anywhere; }
.tga-loading { padding: 40px 20px; text-align: center; color: var(--ios-secondary); font-size: 13px; }
.tga-workspace { display: flex; flex-direction: column; align-items: stretch; gap: 24px; min-width: 0; }
.tga-section-nav { position: relative; isolation: isolate; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 4px; width: 100%; max-width: 680px; padding: 4px; border-radius: 16px; background: var(--ios-inset); }
.tga-section-nav::before { content: ''; position: absolute; inset: 4px auto 4px 4px; width: calc((100% - 20px) / 4); border-radius: 12px; background: var(--ios-control); box-shadow: 0 2px 5px rgb(0 0 0 / .08); transform: translateX(calc(var(--tga-tab-index) * (100% + 4px))); transition: transform var(--ios-duration) var(--ios-ease); pointer-events: none; z-index: -1; }
.tga-section-nav button { display: inline-flex; align-items: center; justify-content: center; gap: 9px; min-width: 0; min-height: 44px; padding: 9px 12px; border: 0; border-radius: 12px; background: transparent; color: var(--ios-secondary); font-weight: 500; white-space: nowrap; cursor: pointer; }
.tga-section-nav button.active { color: var(--ios-text); font-weight: 650; }
.tga-section-nav button:hover { color: var(--ios-text); }
.tga-section-nav i { flex: 0 0 6px; width: 6px; height: 6px; border-radius: 50%; background: var(--ios-secondary); opacity: .45; }
.tga-section-nav i.on { background: var(--success, #087758); opacity: 1; }
.tga-panel { min-width: 0; }
.tga-panel-head { padding: 0 4px 16px; }
.tga-panel-head h3 { font-size: 16px; font-weight: 650; letter-spacing: -.015em; }
.tga-switch-grid { display: grid; grid-template-columns: minmax(0, 1fr); padding: 0 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.tga-switch, .tga-feature-switch { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 20px; min-width: 0; min-height: 76px; padding: 15px 0; cursor: pointer; }
.tga-switch + .tga-switch { border-top: 1px solid var(--ios-line); }
.tga-switch > span, .tga-feature-switch > span { flex: 1; min-width: 0; }
.tga-switch b, .tga-switch small, .tga-feature-switch b, .tga-feature-switch small { display: block; }
.tga-switch b, .tga-feature-switch b { font-size: 14px; font-weight: 600; }
.tga-switch small, .tga-feature-switch small { margin-top: 4px; color: var(--ios-secondary); font-size: 12px; line-height: 1.6; }
.tga-shell .tga-switch input[type='checkbox'], .tga-shell .tga-feature-switch input[type='checkbox'] { position: absolute; width: 1px; height: 1px; margin: 0; padding: 0; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.tga-switch > i, .tga-feature-switch > i { position: relative; display: block; flex: 0 0 50px; width: 50px; height: 30px; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); transition: background-color var(--ios-fast) ease, border-color var(--ios-fast) ease; }
.tga-switch > i::after, .tga-feature-switch > i::after { content: ''; position: absolute; top: 2px; left: 2px; width: 24px; height: 24px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .18); transition: transform var(--ios-duration) var(--ios-ease); }
.tga-switch input:checked + i, .tga-feature-switch input:checked + i { border-color: transparent; background: var(--ios-accent); }
.tga-switch input:checked + i::after, .tga-feature-switch input:checked + i::after { transform: translateX(20px); }
.tga-switch:active > i::after, .tga-feature-switch:active > i::after { transform: scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.tga-switch:active input:checked + i::after, .tga-feature-switch:active input:checked + i::after { transform: translateX(20px) scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.tga-switch input:focus-visible + i, .tga-feature-switch input:focus-visible + i { outline: 3px solid var(--accent, #0063dc); outline-offset: 3px; }
.tga-subsection { margin-top: 28px; }
.tga-subsection-head, .tga-rule-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px 16px; }
.tga-subsection-head { margin: 0 4px 14px; }
.tga-subsection-head > div { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; min-width: 0; }
.tga-subsection-head h4 { font-size: 15px; font-weight: 650; }
.tga-subsection-head span { color: var(--ios-secondary); font-size: 12px; }
.tga-rule-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.tga-primary, .tga-secondary, .tga-text-danger { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; padding: 9px 16px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font-weight: 500; cursor: pointer; }
.tga-secondary:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.tga-primary { min-width: 132px; background: var(--ios-accent); border-color: transparent; color: #fff; font-weight: 600; }
.tga-primary:hover:not(:disabled) { filter: brightness(1.08); }
.tga-text-danger { padding-inline: 12px; background: transparent; border-color: transparent; color: var(--danger, #bd2733); }
.tga-text-danger:hover { background: color-mix(in srgb, var(--danger, #bd2733) 8%, transparent); }
.tga-shell button:disabled, .tga-shell input:disabled { opacity: .5; cursor: not-allowed; }
.tga-empty { padding: 36px 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); color: var(--ios-secondary); font-size: 13px; text-align: center; }
.tga-rule-list { display: flex; flex-direction: column; gap: 16px; }
.tga-rule-item { min-width: 0; padding: 18px 20px 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.tga-rule-head { margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--ios-line); }
.tga-rule-head b { font-size: 14px; font-weight: 650; }
.tga-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px 20px; min-width: 0; }
.tga-form-grid.tga-three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.tga-form-grid > label { min-width: 0; }
.tga-form-grid > label > span, .tga-type-field legend { display: block; margin-bottom: 7px; color: var(--ios-secondary); font-size: 12px; line-height: 1.5; }
.tga-shell input:not([type='checkbox']), .tga-shell select { display: block; min-width: 0; width: 100%; min-height: 44px; padding: 10px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-text); transition: border-color var(--ios-fast) ease; }
.tga-shell input:not([type='checkbox']):focus, .tga-shell select:focus { border-color: var(--accent, #0063dc); }
.tga-shell input[readonly] { color: var(--ios-secondary); background: var(--ios-control); }
.tga-shell select { cursor: pointer; }
.tga-inline-check { display: flex; align-items: center; flex-direction: row-reverse; justify-content: space-between; gap: 16px; min-height: 64px; margin: 0; cursor: pointer; }
.tga-form-grid > label.tga-inline-check > span { flex: 1; min-width: 0; margin: 0; color: var(--ios-text); font-size: 13px; line-height: 1.6; }
.tga-shell .tga-inline-check input[type='checkbox'] { appearance: none; -webkit-appearance: none; position: relative; display: block; flex: 0 0 50px; width: 50px; height: 30px; margin: 0; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); cursor: pointer; transition: background-color var(--ios-fast) ease, border-color var(--ios-fast) ease; }
.tga-shell .tga-inline-check input::before { content: ''; position: absolute; top: 2px; left: 2px; width: 24px; height: 24px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .18); transition: transform var(--ios-duration) var(--ios-ease); }
.tga-shell .tga-inline-check input:checked { border-color: transparent; background: var(--ios-accent); }
.tga-shell .tga-inline-check input:checked::before { transform: translateX(20px); }
.tga-inline-check:active input:not(:disabled)::before { transform: scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.tga-inline-check:active input:checked:not(:disabled)::before { transform: translateX(20px) scaleX(calc(1 + .08 * var(--glass-custom-motion, 1))); }
.tga-type-field { display: flex; align-items: center; flex-wrap: wrap; gap: 10px 20px; min-width: 0; margin: 20px 0 0; padding: 14px 0 0; border: 0; border-top: 1px solid var(--ios-line); }
.tga-type-field legend { padding-right: 8px; margin: 0; }
.tga-type-field label { display: flex; align-items: center; gap: 8px; min-height: 36px; cursor: pointer; }
.tga-type-field input { flex: 0 0 auto; width: 18px; height: 18px; margin: 0; accent-color: var(--ios-accent); }
.tga-type-field span { font-size: 13px; }
.tga-wide { grid-column: 1 / -1; }
.tga-rule-help, .tga-template-help { max-width: 74ch; color: var(--ios-secondary); font-size: 12px; line-height: 1.75; overflow-wrap: anywhere; }
.tga-feature-group { padding: 0 20px 20px; margin-top: 16px; background: var(--ios-surface); border: 1px solid var(--ios-line); border-radius: 20px; }
.tga-feature-group .tga-feature-switch { margin-bottom: 18px; border-bottom: 1px solid var(--ios-line); }
.tga-primary-switch { padding: 16px 20px; margin-bottom: 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.tga-avatar-grid, .tga-nickname-grid { padding: 0 4px; align-items: end; }
.tga-template-help { padding: 12px 14px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); }
.tga-save-bar { position: sticky; z-index: 3; bottom: 0; display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-top: 24px; padding: 12px 16px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); }
.tga-save-bar span { min-width: 0; color: var(--ios-secondary); font-size: 12px; }
:global(html[data-theme='transparent'] .tga-switch-grid),
:global(html[data-theme='transparent'] .tga-feature-group),
:global(html[data-theme='transparent'] .tga-rule-item),
:global(html[data-theme='transparent'] .tga-primary-switch),
:global(html[data-theme='transparent'] .tga-alert),
:global(html[data-theme='transparent'] .tga-empty),
:global(html[data-theme='transparent'] .tga-save-bar) { backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); -webkit-backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); }
@container (max-width: 620px) {
  .tga-workspace { gap: 20px; }
  .tga-page-head { align-items: flex-start; gap: 12px; }
  .tga-page-head h2 { font-size: 20px; }
  .tga-save-state { max-width: 120px; text-align: center; }
  .tga-section-nav button { gap: 6px; padding-inline: 8px; font-size: 13px; }
  .tga-form-grid.tga-three { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .tga-rule-actions { justify-content: flex-start; }
  .tga-rule-item, .tga-feature-group { padding-inline: 16px; }
  .tga-switch-grid { padding-inline: 16px; }
  .tga-primary-switch { padding-inline: 16px; }
  .tga-shell input:not([type='checkbox']), .tga-shell select { font-size: 16px; }
}
@container (max-width: 480px) {
  .tga-form-grid, .tga-form-grid.tga-three { grid-template-columns: minmax(0, 1fr); }
  .tga-section-nav { gap: 2px; }
  .tga-section-nav::before { width: calc((100% - 14px) / 4); transform: translateX(calc(var(--tga-tab-index) * (100% + 2px))); }
  .tga-section-nav button { gap: 5px; padding: 9px 6px; font-size: 12px; }
  .tga-section-nav i { flex-basis: 5px; width: 5px; height: 5px; }
  .tga-inline-check { min-height: 52px; }
  .tga-subsection-head { align-items: flex-start; }
  .tga-rule-actions { width: 100%; }
  .tga-rule-actions .tga-secondary { flex: 1; padding-inline: 10px; }
  .tga-primary-switch, .tga-feature-switch { gap: 14px; }
  .tga-save-bar { flex-wrap: wrap; gap: 10px; padding: 14px; }
  .tga-save-bar span { flex: 1 1 100%; }
  .tga-save-bar .tga-primary { width: 100%; }
}
@container (max-width: 340px) {
  .tga-section-nav i { display: none; }
  .tga-page-head { flex-wrap: wrap; }
  .tga-page-head > div { flex: 1 1 100%; }
  .tga-save-state { max-width: none; }
}
@media (forced-colors: active) {
  .tga-switch > i, .tga-feature-switch > i { display: none; }
  .tga-shell .tga-switch input[type='checkbox'], .tga-shell .tga-feature-switch input[type='checkbox'] { position: static; flex: 0 0 24px; width: 24px; height: 24px; clip-path: none; }
  .tga-shell .tga-inline-check input[type='checkbox'] { appearance: auto; -webkit-appearance: auto; }
  .tga-shell .tga-inline-check input::before { display: none; }
  .tga-section-nav::before { border: 2px solid Highlight; }
}
</style>
