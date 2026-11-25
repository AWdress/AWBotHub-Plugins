<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import IosSettings from '../../../_frontend/IosSettings.vue'
const props=defineProps({pluginId:{type:String,required:true},host:{type:Object,required:true}})
const CronInput=computed(()=>props.host.ui.CronInput)
const FEATURES=[
  {key:'episode_fix',title:'剧集季集',desc:'扫描 SxxExx 文件名，校正 Emby 识别错误',tone:'mint'},
  {key:'delete_episode_genre',title:'单集 Genre',desc:'清理剧集单集上冗余的 Genre',tone:'amber',danger:true},
  {key:'genre_mapper',title:'Genre 映射',desc:'批量替换或删除指定类型',tone:'blue'},
  {key:'season_renamer',title:'季名刮削',desc:'从 TMDB 获取季名并写入 Emby',tone:'violet',tmdb:true},
  {key:'country_scraper',title:'国家与语言',desc:'从 TMDB 获取信息并转换为标签',tone:'cyan',tmdb:true},
  {key:'alt_renamer',title:'中文别名',desc:'将 TMDB 中文别名写入 SortName',tone:'rose',tmdb:true},
  {key:'strm_mediainfo',title:'STRM 刷新',desc:'重新提取 STRM 文件媒体信息',tone:'lime'},
  {key:'damaged_check',title:'健康检查',desc:'检测缺少简介、年份等关键元数据',tone:'slate'},
  {key:'category_covers',title:'分类封面',desc:'用本地固定模板生成 Genre / Tag 封面并上传到 Emby',tone:'rose'},
]
const DEFAULTS={emby_server:'',api_key:'',user_id:'',tmdb_key:'',library_names:'',lock_modified_fields:true,max_output:50,genre_mapping_json:'{\n  "Sci-Fi & Fantasy": "科幻",\n  "War & Politics": "战争"\n}',genre_remove_list:'',add_hant_title:true,strm_delay:3,enable_episode_fix:true,enable_delete_episode_genre:false,enable_genre_mapper:false,enable_season_renamer:false,enable_country_scraper:false,enable_alt_renamer:false,enable_strm_mediainfo:false,enable_damaged_check:false,enable_category_covers:false,category_cover_types:'genre,tag',enable_auto_schedule:false,schedule_cron:'0 3 * * *',schedule_functions:[]}
const form=reactive({...DEFAULTS}),status=reactive({running:false,task:'',scheduled:false,schedule:'',history:[]})
const tab=ref('console'),selected=ref('episode_fix'),loading=ref(true),saving=ref(false),testing=ref(false),busy=ref('')
const secretVisible=reactive({api_key:false,tmdb_key:false})
const rawIds=ref(''),includeChildren=ref(false),repairConfirmed=ref(false),previewToken=ref(''),previewRequest=ref(null),repairError=ref('')
let timer
const current=computed(()=>FEATURES.find(x=>x.key===selected.value)||FEATURES[0])
const enabledCount=computed(()=>FEATURES.filter(x=>form['enable_'+x.key]).length)
const libraries=computed(()=>form.library_names.split(/[\n,]/).map(x=>x.trim()).filter(Boolean))
const operationBlocked=computed(()=>loading.value||status.running||Boolean(busy.value)||saving.value||testing.value)
const lockRepair=computed(()=>status.lock_repair||{})
const repairIds=computed(()=>[...new Set(rawIds.value.split(/[,，\s]+/).filter(Boolean))])
const repairSignature=computed(()=>JSON.stringify([rawIds.value,includeChildren.value]))
const repairInputError=computed(()=>!repairIds.value.length?'请先填写已核对的条目 ID。':repairIds.value.length>500?'一次最多填写 500 个不同的条目 ID，请分批操作。':'')
const previewItems=computed(()=>Array.isArray(lockRepair.value.items)?lockRepair.value.items.slice(0,100):[])
const canApplyRepair=computed(()=>!operationBlocked.value&&repairConfirmed.value&&Boolean(previewToken.value)&&previewToken.value===lockRepair.value.token&&lockRepair.value.ok&&Number(lockRepair.value.count)>0)
const notify=(type,msg)=>props.host.toast?.[type]?.(msg)
async function refresh(){try{Object.assign(status,await props.host.callApi('/status'));const pending=previewRequest.value;if(pending&&pending.signature===repairSignature.value&&!status.running&&lockRepair.value.ok&&lockRepair.value.token&&lockRepair.value.token!==pending.previousToken){previewToken.value=lockRepair.value.token;previewRequest.value=null}}catch{}finally{loading.value=false}}
async function load(){try{const saved={...await props.host.getConfig()};for(const field of Object.keys(secretVisible)){if(saved?.[field]==='********')saved[field]=await props.host.revealSecret(field)}if(typeof saved.lock_modified_fields!=='boolean'&&typeof saved.fix_lock_data==='boolean')saved.lock_modified_fields=saved.fix_lock_data;delete saved.fix_lock_data;Object.assign(form,DEFAULTS,saved)}catch(e){notify('error','读取配置失败：'+e.message)}await refresh();timer=setInterval(refresh,2500)}
async function save(){if(operationBlocked.value)return;saving.value=true;try{const payload=JSON.parse(JSON.stringify(form));delete payload.fix_lock_data;await props.host.saveConfig(payload);notify('success','配置已保存并应用')}catch(e){notify('error','保存失败：'+e.message)}finally{saving.value=false}}
async function test(){if(operationBlocked.value)return;testing.value=true;try{const r=await props.host.callApi('/test',{method:'POST'});notify(r.ok?'success':'error',r.message)}catch(e){notify('error','测试失败：'+e.message)}finally{testing.value=false}}
async function run(action){if(operationBlocked.value)return;const f=FEATURES.find(x=>x.key===action);if(f?.danger&&!confirm(`“${f.title}”会修改 Emby 数据，确定继续？`))return;busy.value=action;try{const r=await props.host.callApi('/run',{method:'POST',body:{action}});notify(r.ok?'success':'error',r.message);await refresh()}catch(e){notify('error','启动失败：'+e.message)}finally{busy.value=''}}
function toggleSchedule(key){const i=form.schedule_functions.indexOf(key);i<0?form.schedule_functions.push(key):form.schedule_functions.splice(i,1)}
watch([rawIds,includeChildren],()=>{previewToken.value='';previewRequest.value=null;repairConfirmed.value=false;repairError.value=''}, {flush:'sync'})
async function previewLocks(){
  if(operationBlocked.value)return
  repairConfirmed.value=false;previewToken.value='';previewRequest.value=null;repairError.value=''
  if(repairInputError.value){repairError.value=repairInputError.value;return}
  const request={signature:repairSignature.value,previousToken:lockRepair.value.token}
  busy.value='locks-preview'
  try{const r=await props.host.callApi('/locks/preview',{method:'POST',body:{item_ids:rawIds.value,include_children:includeChildren.value}});if(r.ok&&r.started){previewRequest.value=request;notify('success',r.message||'预览已在后台开始，请等待结果。');await refresh()}else{repairError.value=r.message||'预览未能启动，请检查配置后重试';notify('error',repairError.value)}}catch(e){repairError.value='预览启动失败：'+e.message;notify('error',repairError.value)}finally{busy.value=''}
}
async function applyLocks(){
  if(!canApplyRepair.value)return
  if(!confirm(`将先备份，再解除预览中的 ${lockRepair.value.count} 个条目的整体锁。原有字段锁会保留；其中也可能有人工设置的整体锁。确定已逐项核对并继续？`))return
  const token=previewToken.value;previewToken.value='';repairConfirmed.value=false;repairError.value='';busy.value='locks-apply'
  try{const r=await props.host.callApi('/locks/apply',{method:'POST',body:{token,confirmed:true}});if(r.ok&&r.started){notify('success',r.message||'修复已在后台开始，请等待执行结果。');await refresh()}else{repairError.value=r.message||'修复未能启动，请重新预览后重试';notify('error',repairError.value)}}catch(e){repairError.value='修复请求未能确认：'+e.message+'。请先查看后台结果，不要重复提交。';notify('error',repairError.value)}finally{busy.value=''}
}
async function downloadLockBackup(){
  if(operationBlocked.value)return
  busy.value='locks-backup';repairError.value=''
  try{const r=await props.host.callApi('/locks/backup');if(!r.ok||!r.backup)throw new Error(r.message||'还没有可下载的修复备份');const url=URL.createObjectURL(new Blob([JSON.stringify(r.backup,null,2)],{type:'application/json;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download='emby-lock-repair-backup.json';document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);notify('success','备份下载已开始，请妥善保存')}catch(e){repairError.value='下载备份失败：'+e.message;notify('error',repairError.value)}finally{busy.value=''}
}
onMounted(load);onBeforeUnmount(()=>clearInterval(timer))
</script>

<template><IosSettings><div class="etb-shell">
  <header class="etb-hero">
    <div class="etb-brand"><div class="etb-mark"><svg viewBox="0 0 32 32"><path d="M8 5h11a6 6 0 0 1 0 12H8zM8 17h13a5 5 0 0 1 0 10H8z"/></svg></div><div><h1>Emby 工具箱</h1><p>把扫描、修复和刮削收进一个可观测的维护工作台。</p></div></div>
    <div class="etb-hero-actions"><span class="etb-state" :class="{live:status.running}"><i></i>{{status.running?status.task:'就绪'}}</span><button class="etb-ghost" :disabled="operationBlocked" @click="test">{{testing?'正在连接…':'测试 Emby'}}</button><button class="etb-primary" :disabled="operationBlocked" @click="save">{{saving?'保存中…':'保存并应用'}}</button></div>
  </header>
  <nav class="etb-tabs" :style="{ '--etb-tab-index': ['console','connection','locks','history'].indexOf(tab) }" aria-label="工具箱配置分组"><button v-for="x in [['console','维护台'],['connection','连接与策略'],['locks','误锁修复'],['history','运行记录']]" :class="{active:tab===x[0]}" @click="tab=x[0]">{{x[1]}}</button></nav>
  <main v-if="tab==='console'" class="etb-console">
    <section class="etb-rail etb-panel"><div class="etb-section-head"><div><h2>维护模块</h2></div><b>{{enabledCount}} / {{FEATURES.length}}</b></div>
      <button v-for="f in FEATURES" class="etb-feature" :class="[{active:selected===f.key},f.tone]" @click="selected=f.key"><i></i><span><strong>{{f.title}}</strong><small>{{form['enable_'+f.key]?'已启用':'未启用'}}</small></span><em>›</em></button>
    </section>
    <section class="etb-workspace etb-panel"><div class="etb-workspace-top"><div><h2>{{current.title}}</h2><p>{{current.desc}}</p></div><label class="etb-switch"><input v-model="form['enable_'+current.key]" type="checkbox" role="switch"><span></span></label></div>
      <div class="etb-scope"><span>作用范围</span><strong>{{libraries.length?`${libraries.length} 个指定媒体库`:'全部媒体库'}}</strong><small v-if="current.tmdb">TMDB 密钥必需</small></div>
      <div v-if="current.key==='genre_mapper'" class="etb-two"><label>Genre 映射 JSON<textarea v-model="form.genre_mapping_json" rows="7" spellcheck="false"/></label><label>要删除的 Genre<textarea v-model="form.genre_remove_list" rows="7" placeholder="每行一个"/></label></div>
      <div v-else-if="current.key==='category_covers'" class="etb-cover-options"><label>生成范围<select v-model="form.category_cover_types"><option value="genre,tag">Genre 与 Tag</option><option value="genre">仅 Genre</option><option value="tag">仅 Tag</option></select></label><p class="etb-hint">图片由插件本地模板渲染，不调用 AI；会覆盖分类当前 Primary 封面。</p></div>
      <div v-else-if="current.key==='strm_mediainfo'" class="etb-field"><label>STRM 请求间隔</label><div class="etb-range"><input v-model.number="form.strm_delay" type="range" min="0" max="30"><output>{{form.strm_delay}} 秒</output></div></div>
      <div v-else class="etb-note"><svg viewBox="0 0 24 24"><path d="M12 3v18M3 12h18"/></svg><p>{{current.key==='damaged_check'?'只读检查，不会修改媒体库。':'启用后可单独运行，也可纳入定时维护计划。'}}</p></div>
      <div class="etb-workspace-bottom"><label class="etb-check"><input type="checkbox" :checked="form.schedule_functions.includes(current.key)" @change="toggleSchedule(current.key)"><span>加入定时计划</span></label><div><button v-if="current.key==='episode_fix'" class="etb-ghost" :disabled="operationBlocked" @click="run('scan_episode_mismatch')">先扫描</button><button class="etb-primary" :disabled="operationBlocked" @click="run(current.key)">{{busy===current.key?'启动中…':'立即执行'}}</button></div></div>
    </section>
    <aside class="etb-plan etb-panel"><h2>维护计划</h2><label class="etb-switch-row"><span><strong>定时执行</strong><small>{{status.scheduled?'已注册到平台':'未注册'}}</small></span><label class="etb-switch"><input v-model="form.enable_auto_schedule" type="checkbox" role="switch"><span></span></label></label><label class="etb-field">五段 Cron<component :is="CronInput" v-model="form.schedule_cron" /></label><div class="etb-queue"><span>待执行模块</span><b>{{form.schedule_functions.length}}</b></div><button class="etb-wide" :disabled="operationBlocked||!form.schedule_functions.length" @click="run('scheduled')">立即运行当前计划</button></aside>
  </main>
  <main v-else-if="tab==='connection'" class="etb-settings etb-panel"><div class="etb-settings-title"><h2>Emby 与 TMDB</h2><p>敏感数据仅保存在平台插件配置中。</p></div><div class="etb-form-grid"><label class="etb-span2">Emby 地址<input v-model.trim="form.emby_server" placeholder="https://emby.example.com"></label><label>API Key<div class="etb-secret"><input v-model="form.api_key" :type="secretVisible.api_key?'text':'password'"><button type="button" :aria-label="secretVisible.api_key?'隐藏 API Key':'显示 API Key'" @click="secretVisible.api_key=!secretVisible.api_key"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div></label><label>用户 ID <input v-model.trim="form.user_id" placeholder="留空自动获取"></label><label>TMDB API Key<div class="etb-secret"><input v-model="form.tmdb_key" :type="secretVisible.tmdb_key?'text':'password'"><button type="button" :aria-label="secretVisible.tmdb_key?'隐藏 TMDB API Key':'显示 TMDB API Key'" @click="secretVisible.tmdb_key=!secretVisible.tmdb_key"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div></label><label class="etb-span2">媒体库名称<textarea v-model="form.library_names" rows="5" placeholder="每行一个；留空处理全部"/></label></div><hr><div class="etb-strategy"><label class="etb-check"><input v-model="form.lock_modified_fields" type="checkbox"><span>仅锁定本次修改的字段</span></label><label class="etb-check"><input v-model="form.add_hant_title" type="checkbox"><span>别名包含繁中标题</span></label><label>输出条目上限<input v-model.number="form.max_output" type="number" min="5" max="200"></label></div><p class="etb-hint etb-lock-policy">只维护 LockedFields，不新增条目整体锁；保留用户已有的整体锁。旧版造成的误锁不会自动解除，请在“误锁修复”中先核对、预览。</p></main>
  <main v-else-if="tab==='locks'" class="etb-settings etb-panel etb-lock-repair">
    <div class="etb-settings-title"><h2>历史误锁修复</h2><p>只处理你明确指定并确认的条目，不会自动全库解锁。</p></div>
    <div class="etb-repair-warning"><strong>先核对来源，再解除整体锁</strong><p>历史整体锁的来源无法自动判定。请只填写你已确认被旧版工具箱影响的条目 ID；手动设置的整体锁也可能被解除，必须逐项核对。</p><p>修复保留 LockedFields 字段锁，不主动刷新元数据，也不直接修改磁盘 NFO；Emby 自身是否同步保存 NFO 由其保存器设置决定。旧 NFO 中仍有 lockdata 时，后续重新导入可能再次锁定。</p></div>
    <label class="etb-field" for="emby-lock-repair-ids">已确认需要修复的条目 ID<textarea id="emby-lock-repair-ids" v-model="rawIds" rows="5" maxlength="50000" :disabled="operationBlocked" spellcheck="false" placeholder="例如：268389, 268390；也可每行一个 ID" aria-describedby="emby-lock-repair-help"/></label>
    <p id="emby-lock-repair-help" class="etb-repair-help">用逗号、空格或换行分隔，每次最多 500 个不同 ID。当前填写 {{repairIds.length}} 个；此操作不使用“媒体库名称”筛选。</p>
    <label class="etb-check"><input v-model="includeChildren" type="checkbox" :disabled="operationBlocked"><span>同时检查指定剧集或季下，字段锁为空的季 / 单集（默认不勾选）</span></label>
    <div class="etb-repair-actions"><button class="etb-ghost" :disabled="operationBlocked||Boolean(repairInputError)" @click="previewLocks">{{busy==='locks-preview'?'正在启动预览…':'只预览，不修改'}}</button><button class="etb-ghost" :disabled="operationBlocked" @click="downloadLockBackup">{{busy==='locks-backup'?'准备下载…':'下载最近一次备份'}}</button></div>
    <p v-if="repairError" class="etb-repair-error" role="alert">{{repairError}}</p>
    <p v-if="status.running" class="etb-hint" role="status">后台任务进行中：{{status.task||'请等待'}}。提交成功不代表已经完成，最终结果会在下方自动更新。</p>
    <section v-if="lockRepair.message||lockRepair.token" class="etb-repair-result" aria-live="polite">
      <h3>预览与执行结果</h3><p>{{lockRepair.message}}</p>
      <template v-if="lockRepair.token"><p>候选条目 {{lockRepair.count||0}} 项：指定条目 {{lockRepair.root_count||0}} 项，下级条目 {{lockRepair.child_count||0}} 项。</p><p class="etb-repair-help">列表仅展示前 100 项，不代表完整清单。预览有有效期；任何输入变化后都必须重新预览。</p></template>
      <ul v-if="previewItems.length" class="etb-repair-items"><li v-for="item in previewItems" :key="item.id"><div><strong>{{item.name||'未命名条目'}}</strong><span>{{item.type}} · ID {{item.id}}</span></div><p>保留字段锁：{{Array.isArray(item.fields)&&item.fields.length?item.fields.join('、'):'无'}}</p><p v-if="item.reason">{{item.reason}}</p></li></ul>
      <p v-if="lockRepair.token&&!previewToken&&!status.running" class="etb-repair-help">此预览不能直接执行。请按当前输入重新预览，再确认修复。</p>
      <label class="etb-check etb-repair-confirm"><input v-model="repairConfirmed" type="checkbox" :disabled="operationBlocked||!previewToken"><span>我已逐项核对，确认这些整体锁属于误锁，并理解手动锁也可能被解除。</span></label>
      <button class="etb-primary" :disabled="!canApplyRepair" @click="applyLocks">{{busy==='locks-apply'?'正在启动修复…':'备份并解除这些整体锁'}}</button>
    </section>
    <p class="etb-repair-help">执行前会先将锁状态备份保存于平台插件存储，备份失败则不会写入 Emby。平台仅保留最近一批，请下载另存后再修复下一批；此文件供核对锁状态，不是媒体库备份或自动回滚文件。所有修复任务均为手动操作，不加入定时计划。</p>
  </main>
  <main v-else class="etb-history etb-panel"><div class="etb-section-head"><div><h2>运行记录</h2></div><span class="etb-state" :class="{live:status.running}"><i></i>{{status.running?'运行中':'自动刷新'}}</span></div><div v-if="!status.history?.length" class="etb-empty">还没有维护记录。运行一次任务后，结果会留在这里。</div><article v-for="row in status.history" class="etb-run"><i :class="row.ok?'ok':'bad'"></i><div><strong>{{row.task}}</strong><span>{{row.source}} · {{row.time}}</span><pre>{{row.summary}}</pre></div></article></main>
</div></IosSettings></template>

<style scoped>
.etb-shell { color:var(--ios-text); min-width:0; padding:4px 0 0; }
h1,h2,h3,p { margin:0; }
h1 { font-size:27px; line-height:1.25; font-weight:720; letter-spacing:-.025em; }
h2 { font-size:18px; font-weight:670; line-height:1.4; }
h3 { font-size:16px; font-weight:650; }
.etb-hero { display:flex; align-items:center; justify-content:space-between; gap:24px; margin:0 2px 24px; }
.etb-brand { display:flex; align-items:center; gap:13px; min-width:0; }
.etb-mark { flex:none; width:44px; height:44px; border-radius:12px; background:var(--accent-dim,var(--ios-inset)); color:var(--ios-accent-text); display:grid; place-items:center; }
.etb-mark svg { width:25px; fill:currentColor; }
.etb-hero p,.etb-workspace-top p,.etb-settings-title p { margin-top:5px; color:var(--ios-secondary); font-size:13px; }
.etb-hero-actions { display:flex; align-items:center; flex-wrap:wrap; justify-content:flex-end; gap:9px; }
.etb-state { display:inline-flex; align-items:center; gap:7px; padding:6px 10px; border-radius:9px; background:var(--ios-inset); color:var(--ios-secondary); font-size:12px; max-width:200px; overflow-wrap:anywhere; }
.etb-state i { flex:none; width:6px; height:6px; border-radius:50%; background:var(--ios-secondary); }
.etb-state.live { color:var(--ios-accent-text); }
.etb-state.live i { background:var(--ios-accent-text); }
.etb-tabs { position:relative; isolation:isolate; display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:3px; padding:4px; border-radius:15px; margin-bottom:24px; background:var(--ios-inset); }
.etb-tabs::before { content:""; position:absolute; z-index:-1; inset:4px auto 4px 4px; width:calc((100% - 11px)/4); border-radius:11px; background:var(--ios-control); box-shadow:0 2px 6px var(--shadow-sm,rgba(0,0,0,.09)); transform:translateX(calc(var(--etb-tab-index,0)*100% + var(--etb-tab-index,0)*3px)); transition:transform var(--ios-duration) var(--ios-ease); }
.etb-tabs button { min-height:40px; border:0; background:transparent; color:var(--ios-secondary); padding:8px 10px; border-radius:11px; cursor:pointer; }
.etb-tabs button.active { color:var(--ios-text); font-weight:650; }
.etb-tabs button:hover:not(.active) { background:var(--hover-bg,var(--ios-surface)); color:var(--ios-text); }
.etb-primary,.etb-ghost,.etb-wide { display:inline-flex; align-items:center; justify-content:center; gap:8px; min-height:44px; padding:10px 16px; border:0; border-radius:12px; font-weight:620; cursor:pointer; }
.etb-primary { background:var(--ios-accent); color:var(--btn-primary-text,#fff); }
.etb-primary:hover:not(:disabled) { filter:brightness(1.08); }
.etb-ghost,.etb-wide { color:var(--ios-accent-text); background:var(--accent-dim,var(--ios-inset)); }
.etb-ghost:hover:not(:disabled),.etb-wide:hover:not(:disabled) { background:var(--hover-bg,var(--ios-inset)); }
button:disabled { opacity:.48; cursor:not-allowed; }
.etb-console { display:grid; grid-template-columns:210px minmax(0,1fr); align-items:start; gap:18px; }
.etb-panel { min-width:0; background:var(--ios-surface); border-radius:16px; }
.etb-rail { padding:18px 8px 8px; }
.etb-workspace,.etb-plan { padding:20px; }
.etb-section-head,.etb-workspace-top { display:flex; align-items:flex-start; justify-content:space-between; gap:16px; }
.etb-section-head h2 { margin-bottom:15px; }
.etb-rail .etb-section-head { padding-inline:8px; }
.etb-section-head b { font-size:12px; font-weight:600; color:var(--ios-secondary); font-variant-numeric:tabular-nums; padding-top:3px; }
.etb-feature { width:100%; min-height:58px; display:flex; align-items:center; gap:10px; border:0; border-radius:10px; background:transparent; color:var(--ios-text); padding:10px; text-align:left; cursor:pointer; }
.etb-feature+.etb-feature { margin-top:2px; }
.etb-feature>i { width:6px; height:6px; border-radius:50%; background:var(--ios-line); flex:none; }
.etb-feature span { display:flex; flex:1; min-width:0; flex-direction:column; }
.etb-feature strong { font-size:13px; font-weight:600; }
.etb-feature small { color:var(--ios-secondary); font-size:11px; margin-top:1px; }
.etb-feature em { font-size:21px; font-style:normal; color:var(--ios-secondary); }
.etb-feature:hover { background:var(--hover-bg,var(--ios-inset)); }
.etb-feature.active { background:var(--accent-dim,var(--ios-inset)); color:var(--ios-accent-text); }
.etb-feature.active>i { background:var(--ios-accent-text); }
.etb-workspace { min-height:430px; display:flex; flex-direction:column; }
.etb-workspace-top h2 { font-size:23px; font-weight:690; letter-spacing:-.015em; }
.etb-workspace-top p { max-width:50ch; }
.etb-scope { display:flex; flex-wrap:wrap; align-items:center; gap:7px 12px; margin:22px 0; padding:12px 0; border-top:1px solid var(--ios-line); border-bottom:1px solid var(--ios-line); font-size:13px; }
.etb-scope>span { color:var(--ios-secondary); }
.etb-scope strong { font-weight:600; }
.etb-scope small { margin-inline-start:auto; color:var(--warning,#986015); }
.etb-note { display:flex; align-items:center; gap:12px; min-height:130px; color:var(--ios-secondary); font-size:13px; }
.etb-note svg { flex:none; width:24px; height:24px; stroke:var(--ios-accent-text); fill:none; stroke-width:1.5; }
.etb-workspace-bottom { margin-top:auto; padding-top:20px; border-top:1px solid var(--ios-line); display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:16px; }
.etb-workspace-bottom>div { display:flex; flex-wrap:wrap; gap:8px; }
.etb-switch { position:relative; display:inline-flex; flex:none; cursor:pointer; }
.etb-switch input { position:absolute; width:1px; height:1px; margin:-1px; padding:0; border:0; overflow:hidden; clip-path:inset(50%); white-space:nowrap; }
.etb-switch>span { display:block; width:50px; height:30px; border-radius:15px; background:var(--switch-bg,var(--ios-line)); position:relative; transition:background-color var(--ios-fast) ease; }
.etb-switch>span::after { content:""; position:absolute; inset-inline-start:3px; top:3px; width:24px; height:24px; border-radius:50%; background:var(--switch-thumb,#fff); box-shadow:0 2px 4px rgba(0,0,0,.15); transition:transform var(--ios-duration) var(--ios-ease); }
.etb-switch input:checked+span { background:var(--success,#178a45); }
.etb-switch input:checked+span::after { transform:translateX(20px); }
.etb-switch input:focus-visible+span { outline:3px solid var(--ios-accent-text); outline-offset:3px; }
.etb-check { display:flex; align-items:center; gap:10px; cursor:pointer; font-size:13px; }
.etb-check input { flex:none; width:20px; height:20px; margin:0; accent-color:var(--ios-accent); cursor:inherit; }
.etb-check span { min-width:0; overflow-wrap:anywhere; }
.etb-plan { grid-column:1/-1; display:grid; grid-template-columns:1fr 1fr; gap:0 24px; }
.etb-plan>h2 { grid-column:1/-1; margin-bottom:3px; }
.etb-switch-row { display:flex; justify-content:space-between; align-items:center; gap:16px; padding:16px 0; }
.etb-switch-row>span { display:flex; flex-direction:column; }
.etb-switch-row strong { font-size:14px; font-weight:600; }
.etb-switch-row small { color:var(--ios-secondary); font-size:12px; margin-top:3px; }
.etb-field { display:flex; flex-direction:column; gap:8px; font-size:13px; font-weight:600; margin:16px 0; }
input:not([type=checkbox]):not([type=range]),textarea,select { width:100%; min-height:44px; border:1px solid transparent; border-radius:11px; background:var(--ios-inset); color:var(--ios-text); padding:11px 12px; outline:none; transition:background-color var(--ios-fast),border-color var(--ios-fast); }
input:not([type=checkbox]):not([type=range]):focus,textarea:focus,select:focus { border-color:var(--ios-accent-text); background:var(--ios-control); }
textarea { resize:vertical; line-height:1.6; }
.etb-queue { display:flex; align-items:center; justify-content:space-between; color:var(--ios-secondary); font-size:13px; padding:12px 0; }
.etb-queue b { color:var(--ios-text); font-weight:650; }
.etb-wide { width:100%; align-self:center; }
.etb-two { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px; }
.etb-two label { display:flex; flex-direction:column; gap:8px; font-size:13px; font-weight:600; }
.etb-range { display:flex; align-items:center; gap:12px; }
.etb-range input { flex:1; min-width:0; accent-color:var(--ios-accent); }
.etb-range output { min-width:52px; color:var(--ios-text); font-variant-numeric:tabular-nums; }
.etb-settings,.etb-history { padding:24px; }
.etb-settings-title { margin-bottom:22px; }
.etb-form-grid { display:grid; grid-template-columns:1fr 1fr; gap:18px 20px; }
.etb-form-grid label { display:flex; min-width:0; flex-direction:column; gap:8px; font-size:13px; font-weight:600; }
.etb-span2 { grid-column:span 2; }
.etb-secret { display:flex; position:relative; }
.etb-secret input:not([type=checkbox]):not([type=range]) { padding-inline-end:48px; }
.etb-secret button { position:absolute; inset-inline-end:0; top:0; width:44px; height:44px; display:grid; place-items:center; border:0; border-radius:11px; background:transparent; color:var(--ios-secondary); cursor:pointer; }
.etb-secret button:hover { color:var(--ios-accent-text); }
.etb-secret svg { width:20px; fill:none; stroke:currentColor; stroke-width:1.8; }
.etb-settings hr { border:0; border-top:1px solid var(--ios-line); margin:24px 0; }
.etb-strategy { display:grid; grid-template-columns:1fr 1fr 180px; gap:20px; align-items:center; }
.etb-strategy>label:last-child { font-size:13px; font-weight:600; }
.etb-strategy>label:last-child input { margin-top:8px; }
.etb-history { min-height:300px; }
.etb-empty { display:grid; place-items:center; min-height:220px; color:var(--ios-secondary); text-align:center; padding:20px; }
.etb-run { display:grid; grid-template-columns:7px minmax(0,1fr); gap:12px; padding:18px 0; border-top:1px solid var(--ios-line); }
.etb-run>i { width:6px; height:6px; border-radius:50%; margin-top:8px; }
.etb-run>i.ok { background:var(--success,#178a45); }
.etb-run>i.bad { background:var(--danger,#c73036); }
.etb-run>div { display:grid; grid-template-columns:1fr auto; gap:5px 16px; min-width:0; }
.etb-run strong { font-size:14px; font-weight:600; }
.etb-run span { color:var(--ios-secondary); font-size:12px; }
.etb-run pre { grid-column:1/-1; white-space:pre-wrap; overflow-wrap:anywhere; color:var(--ios-secondary); font:12px/1.65 ui-monospace,monospace; max-height:180px; overflow:auto; margin:4px 0 0; }
.etb-cover-options { display:flex; flex-direction:column; gap:16px; margin-top:4px; margin-bottom:20px; }
.etb-cover-options label { display:flex; flex-direction:column; gap:8px; font-size:13px; font-weight:600; }
.etb-hint { margin:0; color:var(--ios-secondary); font-size:12px; line-height:1.65; }
.etb-lock-policy { margin-top:20px; padding-top:16px; border-top:1px solid var(--ios-line); }
.etb-lock-repair p { overflow-wrap:anywhere; }
.etb-repair-warning { margin:22px 0; padding:16px; border-radius:12px; color:var(--warning,#986015); background:var(--warning-bg,var(--ios-inset)); font-size:13px; }
.etb-repair-warning p { margin:8px 0 0; max-width:75ch; }
.etb-repair-help { font-size:12px; color:var(--ios-secondary); margin:10px 0 18px; max-width:80ch; line-height:1.7; }
.etb-repair-actions { display:flex; flex-wrap:wrap; gap:10px; margin:20px 0; }
.etb-repair-result { margin-top:24px; padding-top:20px; border-top:1px solid var(--ios-line); }
.etb-repair-result h3 { margin:0 0 12px; }
.etb-repair-result>p { margin:8px 0; font-size:13px; }
.etb-repair-error { color:var(--danger,#c73036); font-size:13px; margin-top:12px; }
.etb-repair-items { list-style:none; padding:0; margin:18px 0; max-height:390px; overflow:auto; scrollbar-width:thin; scrollbar-color:var(--ios-line) transparent; }
.etb-repair-items li { padding:14px 0; border-bottom:1px solid var(--ios-line); }
.etb-repair-items li>div { display:flex; justify-content:space-between; flex-wrap:wrap; gap:6px 18px; }
.etb-repair-items strong { font-size:13px; font-weight:600; overflow-wrap:anywhere; min-width:0; }
.etb-repair-items span,.etb-repair-items p { color:var(--ios-secondary); overflow-wrap:anywhere; font-size:12px; }
.etb-repair-items p { margin:4px 0; }
.etb-repair-confirm { align-items:flex-start; margin:20px 0 16px; max-width:80ch; }
.etb-lock-repair textarea:disabled { opacity:.48; }
.etb-lock-repair .etb-check input:disabled+span { opacity:.48; cursor:not-allowed; }
@container(max-width:900px) {
  .etb-hero { align-items:flex-start; flex-direction:column; gap:16px; }
  .etb-hero-actions { justify-content:flex-start; }
  .etb-strategy { grid-template-columns:1fr 1fr; }
  .etb-strategy>label:last-child { grid-column:1/-1; max-width:240px; }
}
@container(max-width:600px) {
  h1 { font-size:24px; }
  .etb-mark { display:none; }
  .etb-hero-actions { width:100%; }
  .etb-hero-actions button { flex:1; }
  .etb-state { max-width:none; }
  .etb-console { grid-template-columns:1fr; gap:16px; }
  .etb-rail { display:grid; grid-template-columns:1fr 1fr; gap:3px; }
  .etb-rail .etb-section-head { grid-column:1/-1; }
  .etb-feature { min-width:0; padding:9px; }
  .etb-workspace,.etb-plan,.etb-settings,.etb-history { padding:18px 16px; }
  .etb-workspace { min-height:360px; }
  .etb-workspace-bottom { align-items:flex-start; flex-direction:column; }
  .etb-workspace-bottom>div { width:100%; }
  .etb-workspace-bottom button { flex:1; }
  .etb-tabs button { font-size:12px; padding:9px 3px; }
  .etb-form-grid,.etb-strategy,.etb-two,.etb-plan { grid-template-columns:1fr; }
  .etb-span2 { grid-column:auto; }
  .etb-run>div { grid-template-columns:1fr; }
  .etb-run span { grid-column:1; }
  .etb-hero p { max-width:35ch; }
  .etb-repair-actions>button { flex:1; min-width:140px; }
  .etb-repair-result>.etb-primary { width:100%; }
}
@media(forced-colors:active) {
  .etb-panel,.etb-tabs::before,input,textarea,select,button { border:1px solid CanvasText; }
  .etb-feature.active { outline:1px solid Highlight; }
  .etb-switch input { position:static; width:24px; height:24px; clip-path:none; margin:0; }
  .etb-switch>span { display:none; }
  .etb-state i,.etb-feature>i,.etb-run>i { background:CanvasText; }
}
</style>
