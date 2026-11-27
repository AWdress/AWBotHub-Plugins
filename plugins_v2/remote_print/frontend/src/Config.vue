<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import schema from './schema.json'
import { apiError, configPayload, configValues, isVisible, validateConfig } from './config.js'
import ToolResult from './ToolResult.vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

const props = defineProps({ host: { type: Object, required: true } })
const values = ref({})
const baseline = ref({})
const loaded = ref(false)
const loading = ref(false)
const saving = ref(false)
const acting = ref('')
const revealing = ref('')
const visibleSecrets = ref({})
const secretSyncRequired = ref(false)
const secretSyncError = ref('')
const errors = ref({})
const loadError = ref('')
const saveNotice = ref('')
const saveFailed = ref(false)
const result = ref(null)
const confirmation = ref('')
let mounted = true
onBeforeUnmount(() => { mounted = false })

const busy = computed(() => loading.value || saving.value || !!acting.value || !!revealing.value)
const dirty = computed(() => loaded.value && JSON.stringify(configPayload(schema, values.value)) !== JSON.stringify(baseline.value))
const tabs = [
  { id: 'print', label: '打印设置', title: '连接打印机', note: '先设置连接，再保存并检查。打印机地址不是管理网页地址。' },
  { id: 'family', label: '家人权限', title: '允许谁打印', note: '机器人与企业微信应用从平台读取，这里只设置允许使用的家人。' },
  { id: 'tools', label: '任务与工具', title: '任务与连接', note: '点击后才查询，不会自动打印。工具使用已保存的设置。' },
  { id: 'help', label: '使用帮助', title: '怎么开始使用', note: 'Telegram 直接发文件；企微／微信发照片，文档先回复“打印文件”。详细说明按需展开。' },
]
const activeTab = ref('print')
const formElement = ref(null)
const tabButtons = []
const groupDefinitions = [
  { id: 'connection', tab: 'print', title: '' },
  { id: 'reception', tab: 'print', title: '收件与确认' },
  { id: 'advanced', tab: 'print', title: '高级设置' },
  { id: 'people', tab: 'family', title: '' },
  { id: 'wecom', tab: 'family', title: '企业微信接收' },
  { id: 'status', tab: 'tools', title: '' },
  { id: 'maintenance', tab: 'tools', title: '任务维护', danger: true },
  { id: 'guides', tab: 'help', title: '' },
]

function groupFor(key, spec) {
  if (spec.type === 'info') return 'guides'
  if (['cleanup_files', 'archive_unknown'].includes(key)) return 'maintenance'
  if (spec.section === '允许谁打印') return 'people'
  if (spec.section === '企业微信接收设置') return 'wecom'
  if (spec.section === '开始接收') return 'reception'
  if (spec.section === '高级设置') return 'advanced'
  if (spec.section === '查看打印状态') return 'status'
  return 'connection'
}
function tabFor(key) {
  const group = groupFor(key, schema[key] || {})
  return groupDefinitions.find((item) => item.id === group)?.tab || 'print'
}
const resultTab = computed(() => result.value?.key ? tabFor(result.value.key) : activeTab.value)
const sections = computed(() => groupDefinitions.map((group) => ({
  ...group,
  fields: Object.entries(schema)
    .filter(([key, spec]) => key !== 'show_advanced' && groupFor(key, spec) === group.id
      && (spec.type === 'info' || group.id === 'maintenance' || isVisible(spec, values.value)))
    .map(([key, spec]) => ({ key, spec }))
    .sort((a, b) => (a.spec.order ?? 9999) - (b.spec.order ?? 9999)),
})).filter((group) => group.fields.length || group.id === 'advanced'))

function chooseTab(id) {
  activeTab.value = id
  confirmation.value = ''
}
function tabKey(event, index) {
  const positions = { ArrowRight: (index + 1) % tabs.length, ArrowDown: (index + 1) % tabs.length,
    ArrowLeft: (index + tabs.length - 1) % tabs.length, ArrowUp: (index + tabs.length - 1) % tabs.length,
    Home: 0, End: tabs.length - 1 }
  if (!(event.key in positions)) return
  event.preventDefault()
  const next = positions[event.key]
  chooseTab(tabs[next].id)
  tabButtons[next]?.focus()
}

const shortLabels = {
  print_mode: '连接方式', ipp_url: '打印机访问地址', device_id: '电脑端设备名称',
  print_color_mode: '打印颜色', wecom_reply_mode: '企微／微信确认方式',
  printer_name: 'Windows 打印机名称', telegram_users: 'Telegram 用户 ID',
  wecom_users: '企业微信成员账号', public_base_url: '平台访问地址',
  auto_print: '收到文件直接打印', ipp_printer_uri: '打印机内部地址',
  ipp_timeout_seconds: '连接超时（秒）', default_copies: '默认份数', max_copies: '最多份数',
  max_pages: '最多页数', max_file_mb: '文件上限（MB）', max_queue: '未结束任务上限',
  max_storage_mb: '缓存上限（MB）', retention_hours: '文件保留（小时）',
}
const shortHints = {
  print_mode: '支持 IPP 的网络打印机选直连；USB 打印机等通过 Windows 电脑打印。',
  print_color_mode: '默认跟随打印机。选黑白后，新文件按黑白打印；已收到的文件不变。设备不支持时会提示。',
  wecom_reply_mode: '默认文字指令。企微 App 可切换按钮卡片；微信插件／微工作台请保留文字，避免看不到按钮。',
  ipp_url: '填写平台能够访问的 IPP 地址。同一局域网不需要 FRP。',
  device_id: '与电脑端 device_id 一致。', device_token: '留空时先生成密钥，再点眼睛查看，复制到电脑端。',
  printer_name: '留空使用电脑端默认打印机。', telegram_users: '数字 ID，每行一个；留空不允许任何人。',
  wecom_users: '通讯录 UserID，每行一个；同一成员也须在平台回调名单中授权。',
  public_base_url: '企微／微信上传 PDF 必填。填写手机能访问的平台 HTTPS 地址，有部署子路径也要带上；不是打印机地址。',
  enabled: '默认关闭。连接和家人名单设置完成后再开启。',
  auto_print: '默认关闭。保持关闭时，家人回复“打印”后才开始，避免误打。',
  ipp_printer_uri: '通常留空，由打印机自动提供。', ipp_timeout_seconds: '默认 30 秒，范围 5–120 秒。',
  default_copies: '默认 1 份。', max_copies: '默认 3 份，最多 5 份。',
  max_pages: '默认 50 页，超限拒绝整份文件。', max_file_mb: '默认 20 MB；企微最高 20 MB。',
  max_queue: '默认 30 个，包含待核查任务。', max_storage_mb: '默认 200 MB。',
  retention_hours: '默认 24 小时，不会自动重打。',
}
function fieldLabel(key, spec) { return shortLabels[key] || spec.label || key }
function actionHint(key, spec) {
  return { test_ipp: '只检查连接和格式，不会用纸。', generate_device_token: '已有密钥会失效，必须同步更新电脑端。',
    show_wecom_setup: '查看关联应用的完整回调地址和填写步骤。',
    show_connection: '查询当前打印方式、打印机状态和接收地址。',
    show_jobs: '查询最近任务与失败原因。已提交不代表已经出纸。',
    cleanup_files: '仅清理已到期的结束任务文件，不清理未结束任务。',
    archive_unknown: '仅归档已核查的待核查任务，不重新打印。执行前请确认是否已出纸。' }[key] || spec.help
}

async function load() {
  if (busy.value) return
  if (dirty.value) {
    saveFailed.value = true
    saveNotice.value = '你有尚未保存的修改，请先保存，再重新读取。'
    return
  }
  loading.value = true
  loaded.value = false
  loadError.value = ''
  try {
    const saved = configValues(schema, await props.host.getConfig())
    if (!mounted) return
    values.value = saved
    baseline.value = configPayload(schema, saved)
    visibleSecrets.value = {}
    secretSyncRequired.value = false
    secretSyncError.value = ''
    errors.value = {}
    confirmation.value = ''
    loaded.value = true
  } catch (error) {
    if (mounted) loadError.value = apiError(error, '读取配置') + '\n未读取成功前不能保存，也不会执行任何工具。'
  } finally {
    if (mounted) loading.value = false
  }
}

function update(key, value) {
  values.value[key] = value
  if (errors.value[key]) delete errors.value[key]
  saveNotice.value = ''
  confirmation.value = ''
}

async function save() {
  if (!loaded.value || busy.value) return
  if (secretSyncRequired.value) {
    saveFailed.value = true
    saveNotice.value = '未保存：连接密钥的更新结果尚未确认，请先点击“重新读取连接密钥”。其他填写内容已保留。'
    return
  }
  errors.value = validateConfig(schema, values.value)
  if (Object.keys(errors.value).length) {
    saveNotice.value = '未保存：请检查标红的设置。'
    saveFailed.value = true
    const first = Object.keys(errors.value)[0]
    activeTab.value = tabFor(first)
    await nextTick()
    formElement.value?.querySelector(`#rp-${first}`)?.focus()
    return
  }
  saving.value = true
  saveNotice.value = ''
  const payload = configPayload(schema, values.value)
  try {
    const response = await props.host.saveConfig(payload)
    if (!mounted) return
    if (response?.ok === false) throw new Error(response.message || '平台拒绝保存配置。')
    baseline.value = payload
    saveFailed.value = false
    saveNotice.value = '配置已保存。'
    confirmation.value = ''
  } catch (error) {
    if (mounted) {
      saveFailed.value = true
      saveNotice.value = apiError(error, '保存配置') + ' 你的填写内容已保留。'
    }
  } finally {
    if (mounted) saving.value = false
  }
}

async function toggleSecret(key) {
  if (!loaded.value || busy.value) return
  if (key === 'device_token' && secretSyncRequired.value) return
  if (visibleSecrets.value[key]) {
    visibleSecrets.value[key] = false
    return
  }
  if (values.value[key] !== '********') {
    visibleSecrets.value[key] = true
    return
  }
  revealing.value = key
  const current = values.value[key]
  try {
    const value = await props.host.revealSecret(key)
    if (!mounted || values.value[key] !== current) return
    if (value === '********' || value === undefined) throw new Error('平台未返回可查看的密钥，请重试。')
    values.value[key] = value
    // Viewing a secret is not an edit and must not make an action silently save it.
    if (baseline.value[key] === current) baseline.value[key] = value
    visibleSecrets.value[key] = true
  } catch (error) {
    if (mounted) showResult('查看密钥', apiError(error, '读取密钥'), false)
  } finally {
    if (mounted) revealing.value = ''
  }
}

function showResult(title, message, ok, key = '') {
  result.value = { title, message: String(message), ok, key }
}

function readyForAction(spec) {
  if (!loaded.value || busy.value) return false
  if (secretSyncRequired.value) {
    showResult(spec.label, '连接密钥的更新结果尚未确认，请先点击“重新读取连接密钥”。未执行此操作。', false, spec.action)
    return false
  }
  if (dirty.value) {
    confirmation.value = ''
    showResult(spec.label, '尚有未保存的设置。请先点击“保存配置”，再执行此操作。', false, spec.action)
    return false
  }
  return true
}

function requestAction(key, spec) {
  if (!readyForAction(spec)) return
  if (spec.danger) confirmation.value = key
  else runAction(key, spec)
}

async function runAction(key, spec) {
  if (!readyForAction(spec)) return
  if (spec.danger && confirmation.value !== key) return
  confirmation.value = ''
  acting.value = key
  showResult(spec.label, '正在执行，请稍候…', true, key)
  if (key === 'generate_device_token') {
    // A server-side rotation may succeed even when its response is lost. Drop
    // the old revealed value before the request, and lock saving until a read
    // confirms the current stored mask (or empty value).
    secretSyncRequired.value = true
    visibleSecrets.value.device_token = false
    values.value.device_token = '********'
    baseline.value.device_token = '********'
  }
  try {
    const body = { action: spec.action || key }
    if (spec.danger) body.confirmed = true
    const response = await props.host.callApi('/tools', { method: 'POST', body })
    if (!mounted) return
    if (!response || typeof response.ok !== 'boolean' || typeof response.message !== 'string') {
      throw new Error('平台未返回工具结果，请更新插件后重试。')
    }
    showResult(spec.label, response.message, response.ok, key)
  } catch (error) {
    if (mounted) showResult(spec.label, apiError(error, spec.label), false, key)
  } finally {
    if (mounted && key === 'generate_device_token') await syncDeviceToken(true)
    if (mounted) acting.value = ''
  }
}

async function syncDeviceToken(duringAction = false) {
  if (!mounted || !loaded.value || (!duringAction && busy.value)) return false
  revealing.value = 'device_token'
  secretSyncError.value = ''
  try {
    const saved = configValues(schema, await props.host.getConfig())
    if (!mounted) return false
    const token = saved.device_token
    if (token !== '********' && token !== '' && token !== null) {
      throw new Error('平台未返回有效的连接密钥状态。')
    }
    // Never replace other fields: the user may edit them before retrying this
    // read. An unchanged mask lets the platform preserve the newest key on PUT.
    values.value.device_token = token
    baseline.value.device_token = token
    visibleSecrets.value.device_token = false
    secretSyncRequired.value = false
    secretSyncError.value = ''
    saveNotice.value = ''
    return true
  } catch (error) {
    if (mounted) {
      secretSyncRequired.value = true
      secretSyncError.value = apiError(error, '重新读取连接密钥')
        + '\n为避免写回旧密钥，保存和管理工具已暂停。请点击下方按钮重新读取；其他填写内容不会被覆盖。'
    }
    return false
  } finally {
    if (mounted) revealing.value = ''
  }
}

function colSpan(spec, key) {
  return spec.type === 'number' || spec.type === 'text' || ['print_mode', 'ipp_url'].includes(key) ? 6 : 12
}

function options(spec) {
  return (spec.options || []).map((option) => typeof option === 'object'
    ? { value: option.value, label: option.label ?? option.value }
    : { value: option, label: option })
}

function emptySelect(key, spec) {
  return !options(spec).some((option) => option.value === values.value[key])
}

function selectChange(key, spec, event) {
  const index = event.target.selectedIndex - (emptySelect(key, spec) ? 1 : 0)
  const option = options(spec)[index]
  if (option) update(key, option.value)
}

onMounted(load)
</script>

<template>
  <IosSettings>
  <div class="print-config">
    <p v-if="loading" class="state" role="status">正在读取配置…</p>
    <div v-else-if="loadError" class="state error" role="alert">
      <p>{{ loadError }}</p>
      <button type="button" class="button" @click="load">重新读取配置</button>
    </div>
    <form v-else-if="loaded" ref="formElement" @submit.prevent="save">
      <div class="tabs" :style="{ '--rp-tab-index': tabs.findIndex(item => item.id === activeTab) }" role="tablist" aria-label="远程打印设置分类">
        <button v-for="(tab, index) in tabs" :id="`rp-tab-${tab.id}`" :key="tab.id"
          :ref="(el) => tabButtons[index] = el" type="button" role="tab" :data-tab="tab.id"
          :aria-selected="activeTab === tab.id" :aria-controls="`rp-panel-${tab.id}`"
          :tabindex="activeTab === tab.id ? 0 : -1" @click="chooseTab(tab.id)" @keydown="tabKey($event, index)">
          {{ tab.label }}
        </button>
      </div>

      <div v-if="secretSyncRequired" class="state error" role="alert">
        <p>{{ secretSyncError || '正在确认平台已保存的连接密钥，确认完成前不能保存。' }}</p>
        <button type="button" class="button" :disabled="busy" @click="syncDeviceToken()">{{ revealing === 'device_token' ? '正在读取…' : '重新读取连接密钥' }}</button>
      </div>

      <div v-for="tab in tabs" v-show="activeTab === tab.id" :id="`rp-panel-${tab.id}`" :key="tab.id"
        class="tab-panel" role="tabpanel" :aria-labelledby="`rp-tab-${tab.id}`" tabindex="0">
        <header class="page-heading">
          <h3>{{ tab.title }}</h3>
          <p>{{ tab.note }}</p>
        </header>

        <template v-for="section in sections.filter((item) => item.tab === tab.id)" :key="section.id">
        <section
          class="section" :class="{ maintenance: section.danger, advanced: section.id === 'advanced' }"
          :aria-label="section.title || tab.title">
          <template v-if="section.id === 'advanced'">
            <label class="advanced-toggle" for="rp-show_advanced" data-field="show_advanced">
              <span><strong>高级设置</strong><small>份数、文件限制与保留时间，通常保持默认即可。</small></span>
              <input id="rp-show_advanced" type="checkbox" role="switch" :checked="values.show_advanced === true"
                :disabled="busy" aria-label="显示高级设置" @change="update('show_advanced', $event.target.checked)">
            </label>
          </template>
          <h4 v-else-if="section.title" class="group-title">{{ section.title }}</h4>
          <p v-if="section.danger" class="maintenance-note">先核查任务，再按需处理。以下操作不重打，也不取消打印机里的任务。</p>
          <div v-show="section.id !== 'advanced' || values.show_advanced === true" class="fields">
            <div v-for="{ key, spec } in section.fields" :key="key" class="field"
              :class="{ 'tool-row': spec.type === 'action' }"
              :style="{ gridColumn: `span ${colSpan(spec, key)}` }" :data-field="key">
              <template v-if="spec.type === 'info'">
                <details class="guide" :open="key === 'usage'">
                  <summary>{{ spec.label || key }}</summary>
                  <p class="info">{{ spec.text ?? '' }}</p>
                </details>
              </template>
              <template v-else-if="spec.type === 'action'">
                <div class="tool-main">
                  <button type="button" class="button" :class="{ danger: spec.danger }" :disabled="busy"
                    @click="requestAction(key, spec)">{{ acting === key ? '正在执行…' : spec.label || key }}</button>
                  <p class="help">{{ actionHint(key, spec) }}</p>
                </div>
                <div v-if="confirmation === key" class="confirm" role="alert">
                  <strong>确认执行“{{ spec.label }}”？</strong>
                  <p>{{ spec.help }}</p>
                  <div class="button-row">
                    <button type="button" class="button danger" :disabled="busy" @click="runAction(key, spec)">确认执行</button>
                    <button type="button" class="button" @click="confirmation = ''">取消</button>
                  </div>
                </div>
              </template>
              <template v-else-if="spec.type === 'boolean'">
                <label class="switch-row" :for="`rp-${key}`">
                  <span><strong>{{ fieldLabel(key, spec) }}</strong><small>{{ shortHints[key] || spec.help }}</small></span>
                  <input :id="`rp-${key}`" type="checkbox" role="switch" :checked="values[key] === true"
                    :disabled="busy" :aria-label="spec.label" @change="update(key, $event.target.checked)">
                </label>
              </template>
              <template v-else>
                <label :for="`rp-${key}`">{{ fieldLabel(key, spec) }}<span v-if="spec.required" class="required">（必填）</span></label>
                <div v-if="spec.type === 'password' || spec.secret" class="secret-input">
                  <input :id="`rp-${key}`" :type="visibleSecrets[key] ? 'text' : 'password'" :value="values[key] ?? ''"
                    :disabled="busy || (key === 'device_token' && secretSyncRequired)" autocomplete="off"
                    :aria-label="spec.label" :aria-describedby="`rp-help-${key}`" @input="update(key, $event.target.value)">
                  <button type="button" class="eye" :disabled="busy || (key === 'device_token' && secretSyncRequired)"
                    :aria-label="`${visibleSecrets[key] ? '隐藏' : '查看'}${spec.label}`" :aria-pressed="!!visibleSecrets[key]" @click="toggleSecret(key)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/><path v-if="visibleSecrets[key]" d="m3 3 18 18"/>
                    </svg>
                  </button>
                </div>
                <textarea v-else-if="spec.type === 'text'" :id="`rp-${key}`" rows="3" :value="values[key] ?? ''"
                  :disabled="busy" :aria-label="spec.label" :aria-describedby="`rp-help-${key}`" @input="update(key, $event.target.value)" />
                <select v-else-if="spec.type === 'select'" :id="`rp-${key}`" :value="values[key]" :disabled="busy"
                  :aria-label="spec.label" :aria-describedby="`rp-help-${key}`" :aria-invalid="!!errors[key]" @change="selectChange(key, spec, $event)">
                  <option v-if="emptySelect(key, spec)" :value="values[key]" disabled>请选择{{ fieldLabel(key, spec) }}</option>
                  <option v-for="option in options(spec)" :key="String(option.value)" :value="option.value">{{ option.label }}</option>
                </select>
                <input v-else-if="spec.type === 'number'" :id="`rp-${key}`" type="number" :min="spec.min" :max="spec.max"
                  :step="spec.step ?? 1" :value="values[key] ?? ''" :disabled="busy" :aria-label="spec.label"
                  :aria-describedby="`rp-help-${key}`" :aria-invalid="!!errors[key]"
                  @input="update(key, $event.target.value === '' ? '' : Number($event.target.value))">
                <input v-else :id="`rp-${key}`" type="text" :value="values[key] ?? ''" :disabled="busy"
                  :aria-label="spec.label" :aria-describedby="`rp-help-${key}`" :aria-invalid="!!errors[key]"
                  @input="update(key, $event.target.value)">
                <p v-if="shortHints[key]" :id="`rp-help-${key}`" class="help">{{ shortHints[key] }}</p>
                <details v-if="spec.help" class="field-help">
                  <summary>详细说明</summary>
                  <p :id="shortHints[key] ? undefined : `rp-help-${key}`">{{ spec.help }}</p>
                </details>
                <p v-if="errors[key]" class="field-error" role="alert">{{ errors[key] }}</p>
              </template>
            </div>
          </div>
        </section>
        <ToolResult v-if="section.id === 'status' && result && resultTab === tab.id"
          :key="`${tab.id}-${result.message}`" :result="result" :busy="!!acting" />
        </template>
        <ToolResult v-if="tab.id !== 'tools' && result && resultTab === tab.id"
          :key="`${tab.id}-${result.message}`" :result="result" :busy="!!acting" />
      </div>

      <footer class="savebar">
        <p :class="{ error: saveFailed && saveNotice, changed: dirty && !saveNotice }" role="status">
          {{ saveNotice || (dirty ? '有未保存的更改' : '设置已读取') }}
          <small v-if="!saveNotice">{{ dirty ? '切换分类不会丢失填写，保存后才生效。' : '保存不会发送打印任务。' }}</small>
        </p>
        <button type="submit" class="button primary" :disabled="busy || secretSyncRequired">{{ saving ? '正在保存…' : '保存配置' }}</button>
      </footer>
    </form>
  </div>
</IosSettings>
</template>

<style scoped>
/* User-pinned iOS Settings / platform Liquid Glass.
   THESIS: connect a printer and manage family printing through grouped settings.
   OWN-WORLD: shared iOS tokens, quiet grouped surfaces, native form semantics.
   STORY: connect, allow family members, save, then explicitly run a tool.
   FIRST VIEWPORT: four sliding segments above connection fields; save follows content.
   FORM: user's established iOS grouped settings; no new visual-world selection.
   FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance */
.print-config { --rp-space-sm: 8px; --rp-space-md: 16px; --rp-space-lg: 24px; --rp-space-section: 24px; min-width: 0; color: var(--ios-text); }
.print-config form, .tab-panel { display: flex; flex-direction: column; gap: var(--rp-space-section); min-width: 0; }
.print-config p, .print-config h3, .print-config h4 { margin: 0; }
.tabs { position: relative; isolation: isolate; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 4px; padding: 4px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-inset); }
.tabs::before { content: ''; position: absolute; inset: 4px auto 4px 4px; width: calc((100% - 20px) / 4); border-radius: 11px; background: var(--ios-control); box-shadow: 0 2px 5px rgb(0 0 0 / .08); transform: translateX(calc(var(--rp-tab-index) * (100% + 4px))); transition: transform var(--ios-duration) var(--ios-ease); z-index: -1; }
.tabs button { min-width: 0; min-height: 44px; padding: 9px 8px; border: 0; border-radius: 11px; background: transparent; color: var(--ios-secondary); font-weight: 500; cursor: pointer; }
.tabs button:hover { color: var(--ios-text); }
.tabs button[aria-selected=true] { color: var(--ios-text); font-weight: 650; }
.page-heading h3 { font-size: 20px; font-weight: 650; line-height: 1.4; letter-spacing: -.02em; text-wrap: balance; }
.page-heading p { margin-top: 6px; max-width: 72ch; color: var(--ios-secondary); font-size: 13px; line-height: 1.75; }
.section { min-width: 0; padding: 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.group-title { margin-bottom: 20px !important; font-size: 15px; font-weight: 650; }
.fields { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 22px 20px; align-items: start; }
.field { min-width: 0; }
.field > label:not(.switch-row) { display: block; margin-bottom: 8px; font-weight: 500; }
.help, .field-help, .switch-row small, .advanced-toggle small { color: var(--ios-secondary); font-size: 12px; font-weight: 400; line-height: 1.75; }
.help { margin-top: 8px !important; max-width: 72ch; overflow-wrap: anywhere; }
.field-help { margin-top: 4px; }
.field-help summary { display: inline-list-item; width: fit-content; min-height: 32px; padding: 5px 0; cursor: pointer; }
.field-help p { max-width: 72ch; padding-top: 8px; white-space: pre-wrap; overflow-wrap: anywhere; }
input:not([type=checkbox]), textarea, select { width: 100%; min-width: 0; min-height: 44px; padding: 10px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-text); transition: border-color var(--ios-fast) ease; }
textarea { resize: vertical; line-height: 1.7; }
input:not([type=checkbox]):focus, textarea:focus, select:focus { border-color: var(--accent, #0063dc); }
select { cursor: pointer; }
.button { flex-shrink: 0; max-width: 100%; min-height: 44px; padding: 10px 18px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font-weight: 500; cursor: pointer; }
.button:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.primary { min-width: 132px; border-color: transparent; background: var(--ios-accent); color: #fff; font-weight: 600; }
.primary:hover:not(:disabled) { filter: brightness(1.08); }
.danger { color: var(--danger, #bd2733); }
button:disabled, input:disabled, select:disabled, textarea:disabled { opacity: .55; cursor: not-allowed; }
.tab-panel:focus-visible { outline: 3px solid var(--accent, #0063dc); outline-offset: 3px; border-radius: 12px; }
.switch-row, .advanced-toggle { display: flex; align-items: center; justify-content: space-between; gap: 24px; min-height: 44px; cursor: pointer; }
.switch-row > span, .advanced-toggle > span { min-width: 0; }
.switch-row strong, .advanced-toggle strong { display: block; font-size: 14px; font-weight: 500; }
.switch-row small, .advanced-toggle small { display: block; margin-top: 4px; max-width: 72ch; }
input[type=checkbox] { appearance: none; -webkit-appearance: none; position: relative; flex: 0 0 50px; width: 50px; height: 30px; margin: 0; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); cursor: pointer; transition: background-color var(--ios-fast) ease; }
input[type=checkbox]::before { content: ''; position: absolute; top: 2px; left: 2px; width: 24px; height: 24px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .2); transition: transform var(--ios-duration) var(--ios-ease); }
input[type=checkbox]:checked { border-color: transparent; background: var(--ios-accent); }
input[type=checkbox]:checked::before { transform: translateX(20px); }
.secret-input { position: relative; }
.secret-input input { padding-inline-end: 52px; }
.eye { position: absolute; top: 1px; inset-inline-end: 1px; display: grid; place-items: center; width: 44px; height: calc(100% - 2px); border: 0; border-radius: 11px; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.eye svg { width: 21px; height: 21px; }
.eye:hover:not(:disabled) { color: var(--ios-text); }
.advanced .fields { margin-top: 24px; }
.tool-main { display: flex; align-items: center; gap: 16px; }
.tool-main .help { margin: 0 !important; }
.maintenance-note { max-width: 72ch; margin-bottom: 22px !important; color: var(--ios-secondary); font-size: 12px; line-height: 1.75; }
.state, .confirm { display: flex; flex-direction: column; align-items: flex-start; gap: 12px; padding: 20px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); white-space: pre-wrap; overflow-wrap: anywhere; }
.confirm { margin-top: 16px; background: var(--ios-inset); }
.button-row { display: flex; flex-wrap: wrap; gap: 8px; }
.guide + .guide { border-top: 1px solid var(--ios-line); }
.guide summary { min-height: 48px; padding: 11px 0; font-size: 14px; font-weight: 500; cursor: pointer; }
.info { max-width: 72ch; padding: 4px 0 12px; color: var(--ios-secondary); font-size: 13px; line-height: 1.8; white-space: pre-wrap; overflow-wrap: anywhere; }
.savebar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px; padding-top: 8px; }
.savebar p { flex: 1; min-width: 180px; font-size: 12px; color: var(--ios-secondary); overflow-wrap: anywhere; white-space: pre-wrap; }
.savebar small { display: block; margin-top: 3px; font-size: 12px; }
.savebar p.changed { color: var(--warning, #926100); }
.error, .field-error, .required, .savebar p.error { color: var(--danger, #bd2733); }
.field-error { margin-top: 8px !important; font-size: 12px; }
[aria-invalid=true] { border-color: var(--danger, #bd2733) !important; }
:global(html[data-theme='transparent'] .print-config .section),
:global(html[data-theme='transparent'] .print-config .state) { backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); -webkit-backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); }
@container (max-width: 600px) {
  .tab-panel { gap: 20px; }
  .tabs button { padding-inline: 4px; font-size: 12px; }
  .page-heading h3 { font-size: 18px; }
  .section { padding: 16px; }
  .fields { grid-template-columns: minmax(0, 1fr); gap: 20px; }
  .field { grid-column: 1 / -1 !important; }
  .tool-main { flex-direction: column; align-items: flex-start; gap: 8px; }
  .savebar { gap: 14px; }
  .savebar p { flex-basis: 100%; min-width: 0; }
  .savebar .primary { width: 100%; }
  input:not([type=checkbox]), textarea, select { font-size: 16px; }
}
@media (forced-colors: active) {
  input[type=checkbox] { appearance: auto !important; }
  input[type=checkbox]::before { display: none; }
  .tabs::before { border: 2px solid Highlight; }
}
</style>
