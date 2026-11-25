<template>
  <IosSettings>
  <div class="quiz-game-config">
    <div class="tabs" :style="{ '--quiz-tab-index': tab === 'settings' ? 0 : 1 }" aria-label="群答题页面">
      <button :class="{ active: tab === 'settings' }" :aria-pressed="tab === 'settings'" @click="tab = 'settings'">功能设置</button>
      <button :class="{ active: tab === 'history' }" :aria-pressed="tab === 'history'" @click="tab = 'history'">答题记录</button>
    </div>

    <div class="tab-content">
      <div v-if="tab === 'settings'" class="settings">
        <section class="section command-guide" aria-labelledby="command-guide-title">
          <div class="guide-heading">
            <div>
              <h3 id="command-guide-title">命令与玩法</h3>
              <p>命令仅由插件绑定的本人账号发送，群友只需直接发送答案。</p>
            </div>
            <span class="guide-badge">本人命令</span>
          </div>
          <div class="command-list">
            <div class="command-item">
              <code>开启答题</code>
              <span>按下方设置的题目数量生成题目并开始，也支持“开始答题”。</span>
            </div>
            <div class="command-item">
              <code>结束答题</code>
              <span>立即结束本场，并清理题目、奖励等答题消息。</span>
            </div>
          </div>
          <p class="guide-note">最先答对的群友获奖，答错会收到短暂提示；单题超时会公布答案并继续下一题。完成全部题目或由本人发送结束命令后，系统会清理本场消息。</p>
        </section>

        <div class="section">
          <h3>群组设置</h3>
          <label class="row"><span>允许的群组</span><input v-model="cfg.valid_groups" class="inp" placeholder="留空=不限制，多个 ID 用逗号分隔" /></label>
          <div v-if="chatNames.length" class="chat-names"><span class="chat-label">已识别：</span><span v-for="item in chatNames" :key="item.id" class="chat-name">{{ item.title }} ({{ item.id }})</span></div>
          <label class="row row-top"><span>答题黑名单</span><textarea v-model="cfg.blacklist_users" class="inp textarea" rows="4" placeholder="用户 ID 或 @username，支持逗号或换行分隔" /></label>
          <p class="tip">黑名单用户的答案将被静默忽略，不提示、不计分，也不会发放奖励。</p>
        </div>

        <div class="section">
          <h3>出题源</h3>
          <label class="row"><span>出题方式</span><select v-model="cfg.source" class="inp">
            <option value="ai">AI 模型</option>
            <option value="tianapi">天行数据</option>
          </select></label>

          <template v-if="cfg.source === 'ai'">
            <p class="tip">使用平台统一 AI 服务（在「系统设置→AI 服务」配置）。</p>
            <label class="row switch"><input v-model="cfg.ai_image_enabled" type="checkbox" role="switch" /><span>启用 AI 图文题</span></label>
            <label v-if="cfg.ai_image_enabled" class="row indent"><span>配图题比例</span><div class="range-control"><input v-model.number="cfg.ai_image_ratio" type="range" min="0" max="100" step="10" /><output>{{ cfg.ai_image_ratio }}%</output></div></label>
            <p v-if="cfg.ai_image_enabled" class="tip indent-tip">仅为部分题目生成无文字配图；平台生图不可用或生成失败时自动使用纯文字题。</p>
          </template>

          <template v-if="cfg.source === 'tianapi'">
            <label class="row"><span>天行数据 Key</span><div class="secret-field"><input v-model="cfg.tianapi_key" :type="secretVisible ? 'text' : 'password'" class="inp" /><button type="button" :aria-label="secretVisible ? '隐藏天行数据 Key' : '显示天行数据 Key'" @click="secretVisible = !secretVisible"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div></label>
          </template>
        </div>

        <div class="section">
          <h3>奖励设置</h3>
          <label class="row"><span>基础奖励(魔力)</span><input v-model.number="cfg.base_reward" type="number" class="inp" min="1" /></label>
          <label class="row switch"><input v-model="cfg.streak_enabled" type="checkbox" role="switch" /><span>启用连胜加成</span></label>
          <template v-if="cfg.streak_enabled">
            <label class="row indent"><span>连胜倍率</span><input v-model.number="cfg.streak_multiplier" type="number" class="inp" min="1" step="0.1" /></label>
            <label class="row indent"><span>最大连胜</span><input v-model.number="cfg.max_streak" type="number" class="inp" min="1" /></label>
          </template>
        </div>

        <div class="section">
          <h3>答题规则</h3>
          <label class="row"><span>每场题目数量</span><input v-model.number="cfg.question_count" type="number" class="inp" min="1" max="20" /></label>
          <label class="row"><span>答题超时(秒)</span><input v-model.number="cfg.timeout" type="number" class="inp" min="10" /></label>
          <label class="row"><span>自动删除延迟(秒)</span><input v-model.number="cfg.auto_delete_delay" type="number" class="inp" min="0" /></label>
        </div>

        <button @click="save" class="btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存配置' }}</button>
      </div>

      <div v-else class="history">
        <div class="toolbar">
          <button @click="loadHistory" class="btn-sm">刷新</button>
          <span class="muted">最近 {{ history.length }} 条</span>
        </div>
        <div class="quiz-table-wrap" tabindex="0" role="region" aria-label="答题记录列表"><table class="tbl">
          <thead><tr><th>时间</th><th>群组</th><th>题目</th><th>答案</th><th>回答者</th><th>奖励</th></tr></thead>
          <tbody>
            <tr v-for="(h, i) in history" :key="i">
              <td class="muted">{{ h.time }}</td>
              <td>{{ h.group }}</td>
              <td>{{ h.question }}</td>
              <td><b>{{ h.answer }}</b></td>
              <td>{{ h.player || '-' }}</td>
              <td class="gold">{{ h.reward || 0 }}</td>
            </tr>
            <tr v-if="!history.length"><td colspan="6" class="empty">暂无答题记录</td></tr>
          </tbody>
        </table></div>
      </div>
    </div>
  </div>
</IosSettings>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'

const props = defineProps({
  pluginId: { type: String, required: true },
  host: { type: Object, required: true },
})
const cfg = ref({
  valid_groups: '', blacklist_users: '', source: 'ai',
  tianapi_key: '',
  base_reward: 500, streak_enabled: true, streak_multiplier: 1.5, max_streak: 5,
  question_count: 5, timeout: 60, auto_delete_delay: 30,
  ai_image_enabled: false, ai_image_ratio: 30,
})
const tab = ref('settings')
const saving = ref(false)
const history = ref([])
const chatNames = ref([])
const secretVisible = ref(false)

onMounted(async () => {
  try {
    const saved = await props.host.getConfig() || {}
    if (saved.tianapi_key === '********') saved.tianapi_key = await props.host.revealSecret('tianapi_key')
    Object.assign(cfg.value, saved)
  } catch (e) {
    props.host.toast.error('读取配置失败：' + (e.message || e))
  }
  await Promise.all([loadHistory(), loadChatNames()])
})

async function save() {
  saving.value = true
  try {
    await props.host.saveConfig({ ...cfg.value })
    await loadChatNames()
    props.host.toast.success('配置已保存')
  } catch (e) {
    props.host.toast.error('保存失败：' + (e.message || e))
  } finally {
    saving.value = false
  }
}

async function loadHistory() {
  try {
    const r = await props.host.callApi('/history')
    history.value = r.history || []
  } catch (e) {
    props.host.toast.error('读取答题记录失败：' + (e.message || e))
  }
}

async function loadChatNames() {
  try {
    const r = await props.host.callApi('/chat_names')
    chatNames.value = r.items || []
  } catch (e) {
    props.host.toast.error('读取群组名称失败：' + (e.message || e))
  }
}
</script>

<style scoped>
/* User-pinned iOS grouped settings; platform tokens own theme and transparency.
   THESIS: set a group quiz's source, rewards and rules without changing the game.
   OWN-WORLD: sliding segments, quiet grouped form rows, rounded switches and controls.
   STORY: read the existing commands, configure the game, save, then inspect answers.
   FIRST VIEWPORT: two segments above command help and group settings.
   FORM: the user's established iOS Settings direction; no new visual-world selection.
   FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance */
.quiz-game-config { display: flex; flex-direction: column; gap: 24px; min-width: 0; color: var(--ios-text); }
.tabs { position: relative; isolation: isolate; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px; padding: 4px; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-inset); }
.tabs::before { content: ''; position: absolute; inset: 4px auto 4px 4px; width: calc((100% - 12px) / 2); border-radius: 11px; background: var(--ios-control); box-shadow: 0 2px 5px rgb(0 0 0 / .08); transform: translateX(calc(var(--quiz-tab-index) * (100% + 4px))); transition: transform var(--ios-duration) var(--ios-ease); z-index: -1; }
.tabs button { min-width: 0; min-height: 44px; padding: 9px 12px; border: 0; border-radius: 11px; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.tabs button.active { color: var(--ios-text); font-weight: 650; }
.tab-content { min-width: 0; }
.settings { display: flex; flex-direction: column; gap: 20px; }
.section { min-width: 0; padding: 4px 20px; border: 1px solid var(--ios-line); border-radius: 20px; background: var(--ios-surface); }
.section h3 { margin: 0; padding: 14px 0 16px; color: var(--ios-text); font-size: 16px; font-weight: 650; letter-spacing: -.015em; }
.command-guide { padding: 20px; }
.guide-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.guide-heading > div { min-width: 0; }
.guide-heading h3 { padding: 0; margin-bottom: 5px; }
.guide-heading p, .guide-note { margin: 0; color: var(--ios-secondary); font-size: 12px; line-height: 1.8; overflow-wrap: anywhere; }
.guide-badge { flex: none; padding: 4px 9px; border-radius: 8px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 12px; }
.command-list { margin: 16px 0 12px; border-top: 1px solid var(--ios-line); }
.command-item { display: grid; grid-template-columns: 112px minmax(0, 1fr); gap: 16px; align-items: center; padding: 14px 0; border-bottom: 1px solid var(--ios-line); color: var(--ios-secondary); font-size: 13px; line-height: 1.75; }
.command-item code { width: fit-content; padding: 4px 8px; border-radius: 8px; background: var(--ios-inset); color: var(--ios-text); font: inherit; font-weight: 600; }
.row { display: flex; align-items: center; gap: 16px; min-height: 74px; margin: 0; padding: 16px 0; border-top: 1px solid var(--ios-line); }
.row > span:first-child { flex: 0 0 150px; min-width: 0; color: var(--ios-text); }
.row.switch { flex-direction: row-reverse; justify-content: space-between; gap: 20px; cursor: pointer; }
.row.row-top { align-items: flex-start; }
.row.switch span { flex: 1; min-width: 0; line-height: 1.7; }
.chat-names { display: flex; flex-wrap: wrap; gap: 6px 12px; margin: 0 0 16px 166px; color: var(--ios-secondary); font-size: 12px; overflow-wrap: anywhere; }
.chat-name { min-width: 0; }
.secret-field { position: relative; flex: 1; min-width: 0; }
.secret-field .inp { width: 100%; padding-right: 52px; }
.secret-field button { position: absolute; right: 1px; top: 1px; display: grid; place-items: center; width: 44px; height: calc(100% - 2px); border: 0; border-radius: 11px; background: transparent; color: var(--ios-secondary); cursor: pointer; }
.secret-field button:hover { color: var(--ios-text); }
.secret-field svg { width: 20px; fill: none; stroke: currentColor; stroke-width: 1.8; }
.inp { flex: 1; min-width: 0; width: 100%; min-height: 44px; padding: 10px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-inset); color: var(--ios-text); transition: border-color var(--ios-fast) ease; }
.inp:focus { border-color: var(--accent, #0063dc); }
.inp[type=number] { flex: 0 0 130px; width: 130px; margin-left: auto; text-align: right; }
select.inp { cursor: pointer; }
.textarea { resize: vertical; min-height: 108px; line-height: 1.7; }
.tip { max-width: 72ch; margin: 0 0 16px 166px; color: var(--ios-secondary); font-size: 12px; line-height: 1.75; overflow-wrap: anywhere; }
.range-control { flex: 1; display: grid; grid-template-columns: minmax(0, 1fr) 48px; align-items: center; gap: 16px; min-width: 0; }
.range-control input { width: 100%; min-width: 0; min-height: 44px; margin: 0; accent-color: var(--ios-accent); cursor: pointer; }
.range-control output { color: var(--ios-text); font-variant-numeric: tabular-nums; text-align: right; }
.row.switch input { appearance: none; -webkit-appearance: none; position: relative; flex: 0 0 50px; width: 50px; height: 30px; margin: 0; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); cursor: pointer; transition: background-color var(--ios-fast) ease; }
.row.switch input::before { content: ''; position: absolute; top: 2px; left: 2px; width: 24px; height: 24px; border-radius: 50%; background: #fff; box-shadow: 0 2px 4px rgb(0 0 0 / .2); transition: transform var(--ios-duration) var(--ios-ease); }
.row.switch input:checked { border-color: transparent; background: var(--ios-accent); }
.row.switch input:checked::before { transform: translateX(20px); }
.btn, .btn-primary, .btn-sm { min-height: 44px; padding: 10px 18px; border: 1px solid var(--ios-line); border-radius: 14px; background: var(--ios-control); color: var(--ios-text); font-weight: 500; cursor: pointer; }
.btn:hover:not(:disabled), .btn-sm:hover:not(:disabled) { border-color: var(--accent, #0063dc); }
.btn-primary { align-self: flex-end; min-width: 132px; margin-top: 4px; border-color: transparent; background: var(--ios-accent); color: #fff; font-weight: 600; }
.btn-primary:hover:not(:disabled) { filter: brightness(1.08); }
.btn:disabled, .btn-primary:disabled, .btn-sm:disabled { opacity: .5; cursor: not-allowed; }
.toolbar { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 16px; }
.muted { color: var(--ios-secondary); font-size: 12px; }
.quiz-table-wrap { max-width: 100%; min-width: 0; overflow: auto; border: 1px solid var(--ios-line); border-radius: 16px; background: var(--ios-surface); scrollbar-width: thin; scrollbar-color: var(--border-light, #b9bec9) transparent; }
.tbl { width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
.tbl th, .tbl td { padding: 13px 14px; border-bottom: 1px solid var(--ios-line); text-align: left; white-space: nowrap; }
.tbl th { color: var(--ios-secondary); background: var(--ios-inset); font-size: 12px; font-weight: 500; }
.tbl td { color: var(--ios-text); }
.tbl td:nth-child(2), .tbl td:nth-child(3), .tbl td:nth-child(4) { min-width: 100px; max-width: 300px; white-space: normal; overflow-wrap: anywhere; }
.tbl tbody tr:last-child td { border-bottom: 0; }
.tbl td.muted { color: var(--ios-secondary); font-size: 12px; }
.tbl td.empty { padding: 40px 20px; color: var(--ios-secondary); text-align: center; }
.tbl td.gold { color: var(--success, #087758); font-weight: 600; }
:global(html[data-theme='transparent'] .quiz-game-config .section),
:global(html[data-theme='transparent'] .quiz-game-config .quiz-table-wrap) { backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); -webkit-backdrop-filter: blur(var(--glass-blur, 16px)) saturate(var(--glass-saturation, 155%)); }
@container (max-width: 600px) {
  .quiz-game-config { gap: 20px; }
  .section { padding-inline: 16px; }
  .command-guide { padding: 16px; }
  .guide-heading { gap: 12px; flex-wrap: wrap; }
  .command-item { grid-template-columns: minmax(0, 1fr); gap: 8px; }
  .row:not(.switch) { flex-direction: column; align-items: stretch; gap: 8px; }
  .row:not(.switch) > span:first-child { flex: none; }
  .secret-field { flex: none; width: 100%; }
  .chat-names, .tip { margin-left: 0; }
  .inp { font-size: 16px; }
  .inp[type=number] { flex: none; margin-left: 0; width: 130px; }
  .settings .btn-primary { width: 100%; margin-top: 4px; }
  .range-control { width: 100%; }
  .tbl th, .tbl td { padding: 12px; }
}
@media (forced-colors: active) {
  .row.switch input { appearance: auto !important; }
  .row.switch input::before { display: none; }
  .tabs::before { border: 2px solid Highlight; }
}
</style>
