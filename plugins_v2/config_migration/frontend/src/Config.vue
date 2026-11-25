<script setup>
import { computed, reactive, ref } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'
const props = defineProps({ host: { type: Object, required: true } })
const form = reactive({ v1_url:'', v1_webhook_secret:'', migration_code:'', system:true, plugins:true, accounts:true, routing:true, enabled:false, overwrite:false })
const secretVisible = reactive({ v1_webhook_secret:false, migration_code:false })
const loading=ref(false), running=ref(false), preview=ref(null), result=ref(null), error=ref('')
const canRead=computed(()=>form.v1_url && form.v1_webhook_secret && form.migration_code.length>=8 && !loading.value)
async function load(){ try{ const c=await props.host.getConfig(); for(const field of Object.keys(secretVisible)){if(c?.[field]==='********')c[field]=await props.host.revealSecret(field)} Object.assign(form,c||{}); const s=await props.host.callApi('/status'); if(s?.ready&&s.preview)preview.value=s.preview }catch{} }
async function inspect(){ loading.value=true; error.value=''; result.value=null; preview.value=null; try{ const r=await props.host.callApi('/preview',{method:'POST',body:{v1_url:form.v1_url,v1_webhook_secret:form.v1_webhook_secret,migration_code:form.migration_code}}); if(!r.ok)throw new Error(r.error); preview.value=r.preview; if(r.next_code)form.migration_code=r.next_code }catch(e){error.value=e.message||String(e)}finally{loading.value=false} }
async function migrate(){ if(!preview.value||!confirm('确认开始迁移？平台会先备份当前配置。'))return; running.value=true;error.value='';try{const r=await props.host.callApi('/migrate',{method:'POST',body:{system:form.system,plugins:form.plugins,accounts:form.accounts,routing:form.routing,enabled:form.enabled,overwrite:form.overwrite}});if(!r.ok)throw new Error(r.error);result.value=r;preview.value=null}catch(e){error.value=e.message||String(e)}finally{running.value=false} }
load()
</script>

<template>
  <IosSettings>
  <main class="migration-shell">
    <header><div><h1>平台迁移助手</h1><p>连接旧平台的迁移插件，先看清差异，再安全导入 AWBotHub。</p></div><span class="mg-secure">安全迁移</span></header>
    <div class="mg-flow"><section class="mg-source"><h2>连接旧平台</h2><label>旧平台地址<input v-model.trim="form.v1_url" placeholder="http://192.168.1.10:18001" /></label><label>旧平台 Webhook 密钥<div class="mg-secret-field"><input v-model="form.v1_webhook_secret" :type="secretVisible.v1_webhook_secret?'text':'password'" autocomplete="off" placeholder="系统设置中的 WEBHOOK_SECRET" /><button type="button" aria-label="显示或隐藏旧平台 Webhook 密钥" @click="secretVisible.v1_webhook_secret=!secretVisible.v1_webhook_secret"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div></label><label>一次性迁移码<div class="mg-secret-field"><input v-model="form.migration_code" :type="secretVisible.migration_code?'text':'password'" autocomplete="one-time-code" placeholder="从旧平台迁移插件的配置页复制" /><button type="button" aria-label="显示或隐藏一次性迁移码" @click="secretVisible.migration_code=!secretVisible.migration_code"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div></label><button class="mg-primary" :disabled="!canRead" @click="inspect">{{loading?'正在读取…':'读取并预览'}}</button><p class="mg-hint">旧平台迁移插件会自动生成迁移码；每次读取成功后旧码立即失效，新码会自动保存到这里，后续无需手动更换。</p></section>
      <section class="mg-plan"><h2>迁移范围</h2><div class="mg-checks"><label><input v-model="form.system" type="checkbox" role="switch"><i aria-hidden="true"></i><b>系统设置</b><span>Telegram、代理、通知渠道和仓库设置</span></label><label><input v-model="form.plugins" type="checkbox" role="switch"><i aria-hidden="true"></i><b>插件配置</b><span>按相同插件 ID 合并业务配置</span></label><label><input v-model="form.accounts" type="checkbox" role="switch"><i aria-hidden="true"></i><b>账号范围</b><span>迁移每个插件绑定的用户账号</span></label><label><input v-model="form.routing" type="checkbox" role="switch"><i aria-hidden="true"></i><b>Bot 路由</b><span>迁移插件使用的通知 Bot</span></label><label><input v-model="form.enabled" type="checkbox" role="switch"><i aria-hidden="true"></i><b>启用状态</b><span>迁移后仍需确认插件已安装</span></label></div><label class="mg-danger"><input v-model="form.overwrite" type="checkbox" role="switch"><i aria-hidden="true"></i><b>覆盖当前平台已有值</b><span>默认关闭；建议仅在全新环境开启</span></label></section>
    </div>
    <p v-if="error" class="mg-alert">{{error}}</p>
    <section v-if="preview" class="mg-preview"><div class="mg-preview-head"><div><h2>迁移预览</h2><p>敏感值已隐藏，实际迁移仍保留原值。</p></div><button class="mg-primary" :disabled="running" @click="migrate">{{running?'正在迁移…':'确认迁移'}}</button></div><dl><div><dt>{{preview.system_fields}}</dt><dd>系统字段</dd></div><div><dt>{{preview.plugin_configs}}</dt><dd>插件配置</dd></div><div><dt>{{preview.enabled_plugins}}</dt><dd>启用插件</dd></div><div><dt>{{preview.account_scopes}}</dt><dd>账号范围</dd></div><div><dt>{{preview.bot_routes}}</dt><dd>Bot 路由</dd></div></dl><div class="mg-plugin-list"><span v-for="id in preview.plugin_ids" :key="id">{{id}}</span><em v-if="!preview.plugin_ids.length">没有发现插件配置</em></div></section>
    <section v-if="result" class="mg-success"><h2>迁移已完成</h2><p>{{result.message}}</p><small>备份位置：{{result.backup}}</small></section>
  </main>
  </IosSettings>
</template>

<style scoped>
.migration-shell { color:var(--ios-text); min-width:0; padding:4px 0 0; }
header { display:flex; justify-content:space-between; align-items:flex-start; gap:20px; margin:0 2px 24px; }
h1 { font-size:27px; font-weight:720; letter-spacing:-.025em; line-height:1.25; margin:0 0 6px; }
h2 { font-size:18px; font-weight:670; line-height:1.4; margin:0 0 18px; }
p { color:var(--ios-secondary); margin:0; font-size:13px; line-height:1.65; }
.mg-secure { flex:none; color:var(--success,#178a45); background:var(--success-bg,var(--ios-inset)); border-radius:9px; padding:6px 10px; font-size:12px; }
.mg-flow { display:grid; grid-template-columns:1.08fr .92fr; align-items:start; gap:20px; }
.mg-source,.mg-plan,.mg-preview,.mg-success { background:var(--ios-surface); border-radius:16px; padding:22px; min-width:0; }
.mg-source>label { display:block; font-size:13px; font-weight:600; margin:18px 0; }
input[type=text],input[type=password],input:not([type]) { width:100%; min-height:44px; margin-top:8px; background:var(--ios-inset); border:1px solid transparent; color:var(--ios-text); border-radius:11px; padding:11px 12px; outline:none; transition:background-color var(--ios-fast),border-color var(--ios-fast); }
input[type=text]:focus,input[type=password]:focus,input:not([type]):focus { border-color:var(--ios-accent-text); background:var(--ios-control); }
.mg-secret-field { position:relative; }
.mg-secret-field input { padding-inline-end:48px; }
.mg-secret-field button { position:absolute; inset-inline-end:0; bottom:0; width:44px; height:44px; display:grid; place-items:center; border:0; border-radius:11px; background:transparent; color:var(--ios-secondary); cursor:pointer; }
.mg-secret-field button:hover { color:var(--ios-accent-text); }
.mg-secret-field svg { width:20px; fill:none; stroke:currentColor; stroke-width:1.8; }
.mg-primary { display:inline-flex; align-items:center; justify-content:center; min-height:44px; background:var(--ios-accent); color:var(--btn-primary-text,#fff); border:0; border-radius:12px; padding:10px 18px; font-weight:620; cursor:pointer; }
.mg-primary:hover:not(:disabled) { filter:brightness(1.08); }
.mg-primary:disabled { opacity:.48; cursor:not-allowed; }
.mg-hint { font-size:12px; margin-top:14px; line-height:1.7; }
.mg-checks label,.mg-danger { position:relative; display:grid; grid-template-columns:minmax(0,1fr) 50px; gap:3px 18px; align-items:center; padding:17px 0; font-size:14px; cursor:pointer; }
.mg-checks label+label { border-top:1px solid var(--ios-line); }
.mg-checks label:first-child { padding-top:0; }
.mg-checks label b,.mg-danger b { grid-column:1; grid-row:1; font-weight:600; line-height:1.5; }
.mg-checks label>span,.mg-danger>span { grid-column:1; grid-row:2; display:block; color:var(--ios-secondary); font-size:12px; line-height:1.6; }
.mg-checks input,.mg-danger input { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip-path:inset(50%); white-space:nowrap; border:0; }
.mg-checks i,.mg-danger i { position:relative; grid-column:2; grid-row:1/3; display:block; width:50px; height:30px; border-radius:15px; background:var(--switch-bg,var(--ios-line)); transition:background-color var(--ios-fast) ease; }
.mg-checks i::after,.mg-danger i::after { content:""; position:absolute; inset-inline-start:3px; top:3px; width:24px; height:24px; border-radius:50%; background:var(--switch-thumb,#fff); box-shadow:0 2px 4px rgba(0,0,0,.15); transition:transform var(--ios-duration) var(--ios-ease); }
.mg-checks input:checked+i { background:var(--success,#178a45); }
.mg-danger input:checked+i { background:var(--danger,#c73036); }
.mg-checks input:checked+i::after,.mg-danger input:checked+i::after { transform:translateX(20px); }
.mg-checks input:focus-visible+i,.mg-danger input:focus-visible+i { outline:3px solid var(--ios-accent-text); outline-offset:3px; }
.mg-danger { margin-top:0; padding:18px 0 0; border-top:1px solid var(--ios-line); color:var(--danger,#c73036); }
.mg-alert { margin-top:20px; padding:14px 16px; background:var(--danger-bg,var(--ios-inset)); color:var(--danger,#c73036); border-radius:12px; overflow-wrap:anywhere; }
.mg-preview { margin-top:20px; }
.mg-preview-head { display:flex; justify-content:space-between; align-items:center; gap:20px; }
.mg-preview-head h2 { margin-bottom:4px; }
.mg-preview-head .mg-primary { flex:none; }
dl { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:16px; margin:22px 0; padding:18px 0; border-block:1px solid var(--ios-line); }
dl>div { min-width:0; }
dt { font-size:20px; line-height:1.4; font-weight:650; font-variant-numeric:tabular-nums; }
dd { margin:4px 0 0; color:var(--ios-secondary); font-size:12px; }
.mg-plugin-list { display:flex; flex-wrap:wrap; gap:7px; }
.mg-plugin-list span { background:var(--accent-dim,var(--ios-inset)); color:var(--ios-accent-text); border-radius:7px; padding:5px 8px; font-size:12px; overflow-wrap:anywhere; }
.mg-plugin-list em { color:var(--ios-secondary); font-size:13px; font-style:normal; }
.mg-success { margin-top:20px; }
.mg-success h2 { color:var(--success,#178a45); margin-bottom:7px; }
.mg-success small { display:block; color:var(--ios-secondary); margin-top:12px; overflow-wrap:anywhere; font-size:12px; }
@container(max-width:760px) {
  .mg-flow { grid-template-columns:1fr; gap:16px; }
  header { gap:12px; }
  h1 { font-size:24px; }
  .mg-source,.mg-plan,.mg-preview,.mg-success { padding:18px 16px; }
  dl { grid-template-columns:repeat(3,minmax(0,1fr)); gap:18px; }
}
@container(max-width:420px) {
  .mg-preview-head { align-items:stretch; flex-direction:column; gap:16px; }
  header { flex-direction:column; gap:10px; }
  dl { grid-template-columns:repeat(2,minmax(0,1fr)); }
}
@media(forced-colors:active) {
  .mg-source,.mg-plan,.mg-preview,.mg-success,input,button,.mg-secure { border:1px solid CanvasText; }
  .mg-checks input,.mg-danger input { position:static; grid-column:2; grid-row:1/3; width:24px; height:24px; clip-path:none; margin:0; }
  .mg-checks i,.mg-danger i { display:none; }
}
</style>

