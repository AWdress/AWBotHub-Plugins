<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

const props = defineProps({ pluginId: String, host: { type: Object, required: true } })
const cfg = reactive({
  auto_grab_random_packet: false,
  auto_join_official_lottery: false,
  random_packet_delay_min: 1,
  random_packet_delay_max: 5,
})
const loading = ref(true)
const saving = ref(false)
const enabledCount = computed(() => Number(cfg.auto_grab_random_packet) + Number(cfg.auto_join_official_lottery))

async function save() {
  saving.value = true
  try {
    cfg.random_packet_delay_min = Math.max(0, Math.min(Number(cfg.random_packet_delay_min) || 0, 3600))
    cfg.random_packet_delay_max = Math.max(0, Math.min(Number(cfg.random_packet_delay_max) || 0, 3600))
    if (cfg.random_packet_delay_min > cfg.random_packet_delay_max) {
      ;[cfg.random_packet_delay_min, cfg.random_packet_delay_max] = [cfg.random_packet_delay_max, cfg.random_packet_delay_min]
    }
    await props.host.saveConfig({ ...cfg })
    props.host.toast.success('红包抽奖配置已保存')
  } catch (error) {
    props.host.toast.error('保存失败：' + (error.message || error))
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    Object.assign(cfg, await props.host.getConfig() || {})
  } catch (error) {
    props.host.toast.error('读取配置失败：' + (error.message || error))
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="hh-activity">
    <div v-if="loading" class="hh-activity-loading" role="status">正在读取配置…</div>
    <template v-else>
      <header>
        <div>
          <h2>抢红包与抽奖</h2>
          <p>自动识别 HHanClub 官方机器人发布的口令活动，并使用当前 Telegram 账号参与。</p>
        </div>
        <span class="hh-activity-status" :class="{ on: enabledCount > 0 }">{{ enabledCount ? `已启用 ${enabledCount} 项` : '全部关闭' }}</span>
      </header>

      <div class="hh-activity-layout">
        <section class="hh-activity-settings">
          <div class="hh-activity-section-head">
            <div><h3>自动参与</h3><p>两个功能相互独立，默认均为关闭。</p></div>
            <button class="hh-activity-primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存设置' }}</button>
          </div>

          <label class="hh-activity-switch-row">
            <span><b>自动抢红包</b><small>支持“普通红包”和“随机红包”，提取完整领取口令后发送</small></span>
            <input v-model="cfg.auto_grab_random_packet" type="checkbox" role="switch"><span class="hh-activity-track" aria-hidden="true"><span></span></span>
          </label>
          <label class="hh-activity-switch-row">
            <span><b>自动参加抽奖</b><small>只参加状态为“进行中”的抽奖，提取活动原始口令后发送</small></span>
            <input v-model="cfg.auto_join_official_lottery" type="checkbox" role="switch"><span class="hh-activity-track" aria-hidden="true"><span></span></span>
          </label>

          <div class="hh-activity-delay-fields">
            <label><span>最短等待</span><div><input v-model.number="cfg.random_packet_delay_min" type="number" min="0" max="3600" step="0.5"><em>秒</em></div></label>
            <label><span>最长等待</span><div><input v-model.number="cfg.random_packet_delay_max" type="number" min="0" max="3600" step="0.5"><em>秒</em></div></label>
          </div>
        </section>

        <aside class="hh-activity-guide">
          <h3>识别规则</h3>
          <ul>
            <li>仅接受官方机器人 8780479105 的直接消息或 Telegram 原生转发消息</li>
            <li>不会根据正文中的机器人名称判断，避免伪造活动误触发</li>
            <li>已领完、已过期红包和非进行中抽奖会自动跳过</li>
            <li>同一账号在同一群的同一活动只参与一次，消息编辑不会重复参与</li>
          </ul>
          <p class="hh-activity-note">等待时间同时用于红包和抽奖。设置为 0 可立即发送口令。</p>
        </aside>
      </div>
    </template>
  </section>
</template>

<style scoped>

.hh-activity { color: var(--ios-text); container-type: inline-size; }
.hh-activity header, .hh-activity-section-head, .hh-activity-card-head { display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.hh-activity header { align-items: flex-start; margin-bottom: 24px; }
.hh-activity h2 { margin: 2px 0 7px; color: var(--ios-text); font-size: 22px; line-height: 1.4; font-weight: 650; letter-spacing: -.035em; }
.hh-activity h3 { margin: 0 0 5px; color: var(--ios-text); font-size: 14px; line-height: 1.5; font-weight: 650; }
.hh-activity header p, .hh-activity-section-head p, .hh-activity-card-head p { margin: 0; color: var(--ios-secondary); font-size: 12px; line-height: 1.75; overflow-wrap: anywhere; }
.hh-activity p.hh-activity-eyebrow { margin-bottom: 4px; color: var(--ios-secondary); font-size: 10px; font-weight: 600; letter-spacing: .12em; }
.hh-activity-layout { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(0, .85fr); align-items: start; gap: 18px; }
.hh-activity-settings, .hh-activity-card, .hh-activity-guide { min-width: 0; padding: 22px; border: 1px solid var(--ios-line); border-radius: 24px; background: var(--ios-surface); }
.hh-activity-section-head { padding-bottom: 8px; }
.hh-activity button { flex-shrink: 0; min-height: 40px; padding: 9px 15px; border: 1px solid var(--ios-line); border-radius: 13px; background: var(--ios-control); color: var(--ios-text); font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; transition: border-color var(--ios-fast) ease, background var(--ios-fast) ease, color var(--ios-fast) ease; }
.hh-activity button:hover:not(:disabled) { color: var(--ios-accent-text); border-color: color-mix(in srgb, var(--ios-accent) 30%, var(--ios-line)); }
.hh-activity button.hh-activity-primary, .hh-activity button.hh-activity-primary:hover:not(:disabled) { color: #fff; background: var(--ios-accent); border-color: transparent; }
.hh-activity button:disabled { opacity: .45; cursor: not-allowed; }
.hh-activity-loading { padding: 46px 20px; color: var(--ios-secondary); text-align: center; font-size: 12px; }
.hh-activity-status, .hh-activity-badge, .hh-activity-source-badge { display: inline-flex; align-items: center; flex: 0 0 auto; gap: 8px; max-width: 100%; padding: 7px 12px; border: 1px solid var(--ios-line); border-radius: 999px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 11px; line-height: 1.5; }
.hh-activity-status.on, .hh-activity-badge.on { color: var(--success, #28a56a); border-color: color-mix(in srgb, var(--success, #28a56a) 20%, transparent); background: color-mix(in srgb, var(--success, #28a56a) 8%, transparent); }
.hh-activity-badge i { width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
.hh-activity-switch-row { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 18px; min-height: 78px; padding: 16px 0; border-bottom: 1px solid var(--ios-line); cursor: pointer; }
.hh-activity-switch-row > span:first-child { display: grid; min-width: 0; gap: 4px; }
.hh-activity-switch-row b { color: var(--ios-text); font-size: 13px; line-height: 1.5; font-weight: 600; }
.hh-activity-switch-row small { color: var(--ios-secondary); font-size: 11px; line-height: 1.65; overflow-wrap: anywhere; }
.hh-activity-switch-row > input { position: absolute; inset-inline-end: 0; width: 50px; height: 30px; margin: 0; opacity: 0; z-index: 2; cursor: pointer; }
.hh-activity-track { position: relative; flex: 0 0 50px; width: 50px; height: 30px; padding: 3px; border: 1px solid color-mix(in srgb, var(--ios-text) 5%, transparent); border-radius: 20px; background: color-mix(in srgb, var(--ios-text) 18%, transparent); transition: background var(--ios-duration) var(--ios-ease); }
.hh-activity-track > span { display: block; width: 24px; height: 24px; margin: -1px; border-radius: 50%; background: #fff; box-shadow: 0 2px 5px #0002; transition: transform var(--ios-duration) var(--ios-ease); }
.hh-activity-switch-row > input:checked + .hh-activity-track { background: var(--ios-accent); }
.hh-activity-switch-row > input:checked + .hh-activity-track > span { transform: translateX(20px); }
.hh-activity-switch-row > input:focus-visible + .hh-activity-track { outline: 3px solid var(--ios-accent-text); outline-offset: 3px; }
.hh-activity-fields, .hh-activity-delay-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 17px 14px; padding-top: 20px; }
.hh-activity-fields label, .hh-activity-delay-fields label { display: grid; min-width: 0; gap: 8px; color: var(--ios-secondary); font-size: 12px; line-height: 1.5; }
.hh-activity-fields label > div, .hh-activity-delay-fields label > div { display: flex; align-items: center; }
.hh-activity input[type='text'], .hh-activity input[type='number'] { width: 100%; min-width: 0; min-height: 42px; padding: 10px 12px; border: 1px solid var(--ios-line); border-radius: 12px; background: var(--ios-control); color: var(--ios-text); font: inherit; font-size: 13px; }
.hh-activity input[type='number'] { padding-right: 38px; font-variant-numeric: tabular-nums; }
.hh-activity em { margin-left: -29px; color: var(--ios-secondary); font-size: 11px; font-style: normal; pointer-events: none; }
.hh-activity-guide ul { margin: 18px 0; padding-inline-start: 17px; color: var(--ios-secondary); font-size: 12px; line-height: 1.9; }
.hh-activity-guide li + li { margin-top: 6px; }
.hh-activity-note { margin: 0; padding: 13px; border: 1px solid var(--ios-line); border-radius: 13px; background: var(--ios-inset); color: var(--ios-secondary); font-size: 11px; line-height: 1.8; }
:global(html[data-theme='transparent'] .hh-activity-settings),
:global(html[data-theme='transparent'] .hh-activity-card),
:global(html[data-theme='transparent'] .hh-activity-guide) { box-shadow: inset 0 1px 0 color-mix(in srgb, var(--ios-text) 5%, transparent); }
@container (max-width: 740px) {
 .hh-activity-layout { grid-template-columns: minmax(0, 1fr); }
 .hh-activity header { flex-wrap: wrap; gap: 13px; }
 .hh-activity-settings, .hh-activity-card, .hh-activity-guide { padding: 18px; border-radius: 21px; }
}
@container (max-width: 390px) {
 .hh-activity-fields, .hh-activity-delay-fields { grid-template-columns: minmax(0, 1fr); }
 .hh-activity-section-head { align-items: flex-start; flex-wrap: wrap; }
 .hh-activity h2 { font-size: 20px; }
}

</style>
