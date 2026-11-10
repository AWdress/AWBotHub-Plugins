import { importShared } from './__federation_fn_import-JrT3xvdd.js';

const _export_sfc = (sfc, props) => {
  const target = sfc.__vccOpts || sfc;
  for (const [key, val] of props) {
    target[key] = val;
  }
  return target;
};

const {createElementVNode:_createElementVNode,openBlock:_openBlock,createElementBlock:_createElementBlock,toDisplayString:_toDisplayString,createTextVNode:_createTextVNode,normalizeClass:_normalizeClass,renderList:_renderList,Fragment:_Fragment,vModelCheckbox:_vModelCheckbox,withDirectives:_withDirectives,createCommentVNode:_createCommentVNode,vModelText:_vModelText,vModelSelect:_vModelSelect,resolveDynamicComponent:_resolveDynamicComponent,createBlock:_createBlock,vModelDynamic:_vModelDynamic,createStaticVNode:_createStaticVNode} = await importShared('vue');


const _hoisted_1 = { class: "shell" };
const _hoisted_2 = { class: "hero" };
const _hoisted_3 = { class: "hero-actions" };
const _hoisted_4 = ["disabled"];
const _hoisted_5 = ["disabled"];
const _hoisted_6 = { class: "tabs" };
const _hoisted_7 = ["onClick"];
const _hoisted_8 = {
  key: 0,
  class: "console"
};
const _hoisted_9 = { class: "rail panel" };
const _hoisted_10 = { class: "section-head" };
const _hoisted_11 = ["onClick"];
const _hoisted_12 = { class: "workspace panel" };
const _hoisted_13 = { class: "workspace-top" };
const _hoisted_14 = { class: "switch" };
const _hoisted_15 = { class: "scope" };
const _hoisted_16 = { key: 0 };
const _hoisted_17 = {
  key: 0,
  class: "two"
};
const _hoisted_18 = {
  key: 1,
  class: "cover-options"
};
const _hoisted_19 = {
  key: 2,
  class: "field"
};
const _hoisted_20 = { class: "range" };
const _hoisted_21 = {
  key: 3,
  class: "note"
};
const _hoisted_22 = { class: "workspace-bottom" };
const _hoisted_23 = { class: "check" };
const _hoisted_24 = ["checked"];
const _hoisted_25 = ["disabled"];
const _hoisted_26 = ["disabled"];
const _hoisted_27 = { class: "plan panel" };
const _hoisted_28 = { class: "switch-row" };
const _hoisted_29 = { class: "switch" };
const _hoisted_30 = { class: "field" };
const _hoisted_31 = { class: "queue" };
const _hoisted_32 = ["disabled"];
const _hoisted_33 = {
  key: 1,
  class: "settings panel"
};
const _hoisted_34 = { class: "form-grid" };
const _hoisted_35 = { class: "span2" };
const _hoisted_36 = { class: "secret" };
const _hoisted_37 = ["type"];
const _hoisted_38 = ["aria-label"];
const _hoisted_39 = { class: "secret" };
const _hoisted_40 = ["type"];
const _hoisted_41 = ["aria-label"];
const _hoisted_42 = { class: "span2" };
const _hoisted_43 = { class: "strategy" };
const _hoisted_44 = { class: "check" };
const _hoisted_45 = { class: "check" };
const _hoisted_46 = {
  key: 2,
  class: "settings panel lock-repair"
};
const _hoisted_47 = {
  class: "field",
  for: "emby-lock-repair-ids"
};
const _hoisted_48 = ["disabled"];
const _hoisted_49 = {
  id: "emby-lock-repair-help",
  class: "repair-help"
};
const _hoisted_50 = { class: "check" };
const _hoisted_51 = ["disabled"];
const _hoisted_52 = { class: "repair-actions" };
const _hoisted_53 = ["disabled"];
const _hoisted_54 = ["disabled"];
const _hoisted_55 = {
  key: 0,
  class: "repair-error",
  role: "alert"
};
const _hoisted_56 = {
  key: 1,
  class: "hint",
  role: "status"
};
const _hoisted_57 = {
  key: 2,
  class: "repair-result",
  "aria-live": "polite"
};
const _hoisted_58 = {
  key: 1,
  class: "repair-items"
};
const _hoisted_59 = { key: 0 };
const _hoisted_60 = {
  key: 2,
  class: "repair-help"
};
const _hoisted_61 = { class: "check repair-confirm" };
const _hoisted_62 = ["disabled"];
const _hoisted_63 = ["disabled"];
const _hoisted_64 = {
  key: 3,
  class: "history panel"
};
const _hoisted_65 = { class: "section-head" };
const _hoisted_66 = {
  key: 0,
  class: "empty"
};
const _hoisted_67 = { class: "run" };

const {computed,onBeforeUnmount,onMounted,reactive,ref,watch} = await importShared('vue');


const _sfc_main = {
  __name: 'Config',
  props: {pluginId:{type:String,required:true},host:{type:Object,required:true}},
  setup(__props) {

const props=__props;
const CronInput=computed(()=>props.host.ui.CronInput);
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
];
const DEFAULTS={emby_server:'',api_key:'',user_id:'',tmdb_key:'',library_names:'',lock_modified_fields:true,max_output:50,genre_mapping_json:'{\n  "Sci-Fi & Fantasy": "科幻",\n  "War & Politics": "战争"\n}',genre_remove_list:'',add_hant_title:true,strm_delay:3,enable_episode_fix:true,enable_delete_episode_genre:false,enable_genre_mapper:false,enable_season_renamer:false,enable_country_scraper:false,enable_alt_renamer:false,enable_strm_mediainfo:false,enable_damaged_check:false,enable_category_covers:false,category_cover_types:'genre,tag',enable_auto_schedule:false,schedule_cron:'0 3 * * *',schedule_functions:[]};
const form=reactive({...DEFAULTS}),status=reactive({running:false,task:'',scheduled:false,schedule:'',history:[]});
const tab=ref('console'),selected=ref('episode_fix'),loading=ref(true),saving=ref(false),testing=ref(false),busy=ref('');
const secretVisible=reactive({api_key:false,tmdb_key:false});
const rawIds=ref(''),includeChildren=ref(false),repairConfirmed=ref(false),previewToken=ref(''),previewRequest=ref(null),repairError=ref('');
let timer;
const current=computed(()=>FEATURES.find(x=>x.key===selected.value)||FEATURES[0]);
const enabledCount=computed(()=>FEATURES.filter(x=>form['enable_'+x.key]).length);
const libraries=computed(()=>form.library_names.split(/[\n,]/).map(x=>x.trim()).filter(Boolean));
const operationBlocked=computed(()=>loading.value||status.running||Boolean(busy.value)||saving.value||testing.value);
const lockRepair=computed(()=>status.lock_repair||{});
const repairIds=computed(()=>[...new Set(rawIds.value.split(/[,，\s]+/).filter(Boolean))]);
const repairSignature=computed(()=>JSON.stringify([rawIds.value,includeChildren.value]));
const repairInputError=computed(()=>!repairIds.value.length?'请先填写已核对的条目 ID。':repairIds.value.length>500?'一次最多填写 500 个不同的条目 ID，请分批操作。':'');
const previewItems=computed(()=>Array.isArray(lockRepair.value.items)?lockRepair.value.items.slice(0,100):[]);
const canApplyRepair=computed(()=>!operationBlocked.value&&repairConfirmed.value&&Boolean(previewToken.value)&&previewToken.value===lockRepair.value.token&&lockRepair.value.ok&&Number(lockRepair.value.count)>0);
const notify=(type,msg)=>props.host.toast?.[type]?.(msg);
async function refresh(){try{Object.assign(status,await props.host.callApi('/status'));const pending=previewRequest.value;if(pending&&pending.signature===repairSignature.value&&!status.running&&lockRepair.value.ok&&lockRepair.value.token&&lockRepair.value.token!==pending.previousToken){previewToken.value=lockRepair.value.token;previewRequest.value=null;}}catch{}finally{loading.value=false;}}
async function load(){try{const saved={...await props.host.getConfig()};for(const field of Object.keys(secretVisible)){if(saved?.[field]==='********')saved[field]=await props.host.revealSecret(field);}if(typeof saved.lock_modified_fields!=='boolean'&&typeof saved.fix_lock_data==='boolean')saved.lock_modified_fields=saved.fix_lock_data;delete saved.fix_lock_data;Object.assign(form,DEFAULTS,saved);}catch(e){notify('error','读取配置失败：'+e.message);}await refresh();timer=setInterval(refresh,2500);}
async function save(){if(operationBlocked.value)return;saving.value=true;try{const payload=JSON.parse(JSON.stringify(form));delete payload.fix_lock_data;await props.host.saveConfig(payload);notify('success','配置已保存并应用');}catch(e){notify('error','保存失败：'+e.message);}finally{saving.value=false;}}
async function test(){if(operationBlocked.value)return;testing.value=true;try{const r=await props.host.callApi('/test',{method:'POST'});notify(r.ok?'success':'error',r.message);}catch(e){notify('error','测试失败：'+e.message);}finally{testing.value=false;}}
async function run(action){if(operationBlocked.value)return;const f=FEATURES.find(x=>x.key===action);if(f?.danger&&!confirm(`“${f.title}”会修改 Emby 数据，确定继续？`))return;busy.value=action;try{const r=await props.host.callApi('/run',{method:'POST',body:{action}});notify(r.ok?'success':'error',r.message);await refresh();}catch(e){notify('error','启动失败：'+e.message);}finally{busy.value='';}}
function toggleSchedule(key){const i=form.schedule_functions.indexOf(key);i<0?form.schedule_functions.push(key):form.schedule_functions.splice(i,1);}
watch([rawIds,includeChildren],()=>{previewToken.value='';previewRequest.value=null;repairConfirmed.value=false;repairError.value='';}, {flush:'sync'});
async function previewLocks(){
  if(operationBlocked.value)return
  repairConfirmed.value=false;previewToken.value='';previewRequest.value=null;repairError.value='';
  if(repairInputError.value){repairError.value=repairInputError.value;return}
  const request={signature:repairSignature.value,previousToken:lockRepair.value.token};
  busy.value='locks-preview';
  try{const r=await props.host.callApi('/locks/preview',{method:'POST',body:{item_ids:rawIds.value,include_children:includeChildren.value}});if(r.ok&&r.started){previewRequest.value=request;notify('success',r.message||'预览已在后台开始，请等待结果。');await refresh();}else {repairError.value=r.message||'预览未能启动，请检查配置后重试';notify('error',repairError.value);}}catch(e){repairError.value='预览启动失败：'+e.message;notify('error',repairError.value);}finally{busy.value='';}
}
async function applyLocks(){
  if(!canApplyRepair.value)return
  if(!confirm(`将先备份，再解除预览中的 ${lockRepair.value.count} 个条目的整体锁。原有字段锁会保留；其中也可能有人工设置的整体锁。确定已逐项核对并继续？`))return
  const token=previewToken.value;previewToken.value='';repairConfirmed.value=false;repairError.value='';busy.value='locks-apply';
  try{const r=await props.host.callApi('/locks/apply',{method:'POST',body:{token,confirmed:true}});if(r.ok&&r.started){notify('success',r.message||'修复已在后台开始，请等待执行结果。');await refresh();}else {repairError.value=r.message||'修复未能启动，请重新预览后重试';notify('error',repairError.value);}}catch(e){repairError.value='修复请求未能确认：'+e.message+'。请先查看后台结果，不要重复提交。';notify('error',repairError.value);}finally{busy.value='';}
}
async function downloadLockBackup(){
  if(operationBlocked.value)return
  busy.value='locks-backup';repairError.value='';
  try{const r=await props.host.callApi('/locks/backup');if(!r.ok||!r.backup)throw new Error(r.message||'还没有可下载的修复备份');const url=URL.createObjectURL(new Blob([JSON.stringify(r.backup,null,2)],{type:'application/json;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download='emby-lock-repair-backup.json';document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);notify('success','备份下载已开始，请妥善保存');}catch(e){repairError.value='下载备份失败：'+e.message;notify('error',repairError.value);}finally{busy.value='';}
}
onMounted(load);onBeforeUnmount(()=>clearInterval(timer));

return (_ctx, _cache) => {
  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createElementVNode("header", _hoisted_2, [
      _cache[25] || (_cache[25] = _createStaticVNode("<div class=\"brand\" data-v-ab3072f8><div class=\"mark\" data-v-ab3072f8><svg viewBox=\"0 0 32 32\" data-v-ab3072f8><path d=\"M8 5h11a6 6 0 0 1 0 12H8zM8 17h13a5 5 0 0 1 0 10H8z\" data-v-ab3072f8></path></svg></div><div data-v-ab3072f8><span class=\"eyebrow\" data-v-ab3072f8>MEDIA OPERATIONS</span><h1 data-v-ab3072f8>Emby 工具箱</h1><p data-v-ab3072f8>把扫描、修复和刮削收进一个可观测的维护工作台。</p></div></div>", 1)),
      _createElementVNode("div", _hoisted_3, [
        _createElementVNode("span", {
          class: _normalizeClass(["state", {live:status.running}])
        }, [
          _cache[24] || (_cache[24] = _createElementVNode("i", null, null, -1)),
          _createTextVNode(_toDisplayString(status.running?status.task:'就绪'), 1)
        ], 2),
        _createElementVNode("button", {
          class: "ghost",
          disabled: operationBlocked.value,
          onClick: test
        }, _toDisplayString(testing.value?'正在连接…':'测试 Emby'), 9, _hoisted_4),
        _createElementVNode("button", {
          class: "primary",
          disabled: operationBlocked.value,
          onClick: save
        }, _toDisplayString(saving.value?'保存中…':'保存并应用'), 9, _hoisted_5)
      ])
    ]),
    _createElementVNode("nav", _hoisted_6, [
      (_openBlock(), _createElementBlock(_Fragment, null, _renderList([['console','维护台'],['connection','连接与策略'],['locks','误锁修复'],['history','运行记录']], (x) => {
        return _createElementVNode("button", {
          class: _normalizeClass({active:tab.value===x[0]}),
          onClick: $event => (tab.value=x[0])
        }, _toDisplayString(x[1]), 11, _hoisted_7)
      }), 64))
    ]),
    (tab.value==='console')
      ? (_openBlock(), _createElementBlock("main", _hoisted_8, [
          _createElementVNode("section", _hoisted_9, [
            _createElementVNode("div", _hoisted_10, [
              _cache[26] || (_cache[26] = _createElementVNode("div", null, [
                _createElementVNode("span", { class: "kicker" }, "MODULES"),
                _createElementVNode("h2", null, "维护模块")
              ], -1)),
              _createElementVNode("b", null, _toDisplayString(enabledCount.value) + " / " + _toDisplayString(FEATURES.length), 1)
            ]),
            (_openBlock(), _createElementBlock(_Fragment, null, _renderList(FEATURES, (f) => {
              return _createElementVNode("button", {
                class: _normalizeClass(["feature", [{active:selected.value===f.key},f.tone]]),
                onClick: $event => (selected.value=f.key)
              }, [
                _cache[27] || (_cache[27] = _createElementVNode("i", null, null, -1)),
                _createElementVNode("span", null, [
                  _createElementVNode("strong", null, _toDisplayString(f.title), 1),
                  _createElementVNode("small", null, _toDisplayString(form['enable_'+f.key]?'已启用':'未启用'), 1)
                ]),
                _cache[28] || (_cache[28] = _createElementVNode("em", null, "›", -1))
              ], 10, _hoisted_11)
            }), 64))
          ]),
          _createElementVNode("section", _hoisted_12, [
            _createElementVNode("div", _hoisted_13, [
              _createElementVNode("div", null, [
                _cache[29] || (_cache[29] = _createElementVNode("span", { class: "kicker" }, "ACTIVE MODULE", -1)),
                _createElementVNode("h2", null, _toDisplayString(current.value.title), 1),
                _createElementVNode("p", null, _toDisplayString(current.value.desc), 1)
              ]),
              _createElementVNode("label", _hoisted_14, [
                _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((form['enable_'+current.value.key]) = $event)),
                  type: "checkbox"
                }, null, 512), [
                  [_vModelCheckbox, form['enable_'+current.value.key]]
                ]),
                _cache[30] || (_cache[30] = _createElementVNode("span", null, null, -1))
              ])
            ]),
            _createElementVNode("div", _hoisted_15, [
              _cache[31] || (_cache[31] = _createElementVNode("span", null, "作用范围", -1)),
              _createElementVNode("strong", null, _toDisplayString(libraries.value.length?`${libraries.value.length} 个指定媒体库`:'全部媒体库'), 1),
              (current.value.tmdb)
                ? (_openBlock(), _createElementBlock("small", _hoisted_16, "TMDB 密钥必需"))
                : _createCommentVNode("", true)
            ]),
            (current.value.key==='genre_mapper')
              ? (_openBlock(), _createElementBlock("div", _hoisted_17, [
                  _createElementVNode("label", null, [
                    _cache[32] || (_cache[32] = _createTextVNode("Genre 映射 JSON", -1)),
                    _withDirectives(_createElementVNode("textarea", {
                      "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((form.genre_mapping_json) = $event)),
                      rows: "7",
                      spellcheck: "false"
                    }, null, 512), [
                      [_vModelText, form.genre_mapping_json]
                    ])
                  ]),
                  _createElementVNode("label", null, [
                    _cache[33] || (_cache[33] = _createTextVNode("要删除的 Genre", -1)),
                    _withDirectives(_createElementVNode("textarea", {
                      "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((form.genre_remove_list) = $event)),
                      rows: "7",
                      placeholder: "每行一个"
                    }, null, 512), [
                      [_vModelText, form.genre_remove_list]
                    ])
                  ])
                ]))
              : (current.value.key==='category_covers')
                ? (_openBlock(), _createElementBlock("div", _hoisted_18, [
                    _createElementVNode("label", null, [
                      _cache[35] || (_cache[35] = _createTextVNode("生成范围", -1)),
                      _withDirectives(_createElementVNode("select", {
                        "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((form.category_cover_types) = $event))
                      }, [...(_cache[34] || (_cache[34] = [
                        _createElementVNode("option", { value: "genre,tag" }, "Genre 与 Tag", -1),
                        _createElementVNode("option", { value: "genre" }, "仅 Genre", -1),
                        _createElementVNode("option", { value: "tag" }, "仅 Tag", -1)
                      ]))], 512), [
                        [_vModelSelect, form.category_cover_types]
                      ])
                    ]),
                    _cache[36] || (_cache[36] = _createElementVNode("p", { class: "hint" }, "图片由插件本地模板渲染，不调用 AI；会覆盖分类当前 Primary 封面。", -1))
                  ]))
                : (current.value.key==='strm_mediainfo')
                  ? (_openBlock(), _createElementBlock("div", _hoisted_19, [
                      _cache[37] || (_cache[37] = _createElementVNode("label", null, "STRM 请求间隔", -1)),
                      _createElementVNode("div", _hoisted_20, [
                        _withDirectives(_createElementVNode("input", {
                          "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((form.strm_delay) = $event)),
                          type: "range",
                          min: "0",
                          max: "30"
                        }, null, 512), [
                          [
                            _vModelText,
                            form.strm_delay,
                            void 0,
                            { number: true }
                          ]
                        ]),
                        _createElementVNode("output", null, _toDisplayString(form.strm_delay) + " 秒", 1)
                      ])
                    ]))
                  : (_openBlock(), _createElementBlock("div", _hoisted_21, [
                      _cache[38] || (_cache[38] = _createElementVNode("svg", { viewBox: "0 0 24 24" }, [
                        _createElementVNode("path", { d: "M12 3v18M3 12h18" })
                      ], -1)),
                      _createElementVNode("p", null, _toDisplayString(current.value.key==='damaged_check'?'只读检查，不会修改媒体库。':'启用后可单独运行，也可纳入定时维护计划。'), 1)
                    ])),
            _createElementVNode("div", _hoisted_22, [
              _createElementVNode("label", _hoisted_23, [
                _createElementVNode("input", {
                  type: "checkbox",
                  checked: form.schedule_functions.includes(current.value.key),
                  onChange: _cache[5] || (_cache[5] = $event => (toggleSchedule(current.value.key)))
                }, null, 40, _hoisted_24),
                _cache[39] || (_cache[39] = _createElementVNode("span", null, "加入定时计划", -1))
              ]),
              _createElementVNode("div", null, [
                (current.value.key==='episode_fix')
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 0,
                      class: "ghost",
                      disabled: operationBlocked.value,
                      onClick: _cache[6] || (_cache[6] = $event => (run('scan_episode_mismatch')))
                    }, "先扫描", 8, _hoisted_25))
                  : _createCommentVNode("", true),
                _createElementVNode("button", {
                  class: "primary",
                  disabled: operationBlocked.value,
                  onClick: _cache[7] || (_cache[7] = $event => (run(current.value.key)))
                }, _toDisplayString(busy.value===current.value.key?'启动中…':'立即执行'), 9, _hoisted_26)
              ])
            ])
          ]),
          _createElementVNode("aside", _hoisted_27, [
            _cache[44] || (_cache[44] = _createElementVNode("span", { class: "kicker" }, "AUTOMATION", -1)),
            _cache[45] || (_cache[45] = _createElementVNode("h2", null, "维护计划", -1)),
            _createElementVNode("label", _hoisted_28, [
              _createElementVNode("span", null, [
                _cache[40] || (_cache[40] = _createElementVNode("strong", null, "定时执行", -1)),
                _createElementVNode("small", null, _toDisplayString(status.scheduled?'已注册到平台':'未注册'), 1)
              ]),
              _createElementVNode("label", _hoisted_29, [
                _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => ((form.enable_auto_schedule) = $event)),
                  type: "checkbox"
                }, null, 512), [
                  [_vModelCheckbox, form.enable_auto_schedule]
                ]),
                _cache[41] || (_cache[41] = _createElementVNode("span", null, null, -1))
              ])
            ]),
            _createElementVNode("label", _hoisted_30, [
              _cache[42] || (_cache[42] = _createTextVNode("五段 Cron", -1)),
              (_openBlock(), _createBlock(_resolveDynamicComponent(CronInput.value), {
                modelValue: form.schedule_cron,
                "onUpdate:modelValue": _cache[9] || (_cache[9] = $event => ((form.schedule_cron) = $event))
              }, null, 8, ["modelValue"]))
            ]),
            _createElementVNode("div", _hoisted_31, [
              _cache[43] || (_cache[43] = _createElementVNode("span", null, "待执行模块", -1)),
              _createElementVNode("b", null, _toDisplayString(form.schedule_functions.length), 1)
            ]),
            _createElementVNode("button", {
              class: "wide",
              disabled: operationBlocked.value||!form.schedule_functions.length,
              onClick: _cache[10] || (_cache[10] = $event => (run('scheduled')))
            }, "立即运行当前计划", 8, _hoisted_32)
          ])
        ]))
      : (tab.value==='connection')
        ? (_openBlock(), _createElementBlock("main", _hoisted_33, [
            _cache[56] || (_cache[56] = _createElementVNode("div", { class: "settings-title" }, [
              _createElementVNode("span", { class: "kicker" }, "CONNECTION"),
              _createElementVNode("h2", null, "Emby 与 TMDB"),
              _createElementVNode("p", null, "敏感数据仅保存在平台插件配置中。")
            ], -1)),
            _createElementVNode("div", _hoisted_34, [
              _createElementVNode("label", _hoisted_35, [
                _cache[46] || (_cache[46] = _createTextVNode("Emby 地址", -1)),
                _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": _cache[11] || (_cache[11] = $event => ((form.emby_server) = $event)),
                  placeholder: "https://emby.example.com"
                }, null, 512), [
                  [
                    _vModelText,
                    form.emby_server,
                    void 0,
                    { trim: true }
                  ]
                ])
              ]),
              _createElementVNode("label", null, [
                _cache[48] || (_cache[48] = _createTextVNode("API Key", -1)),
                _createElementVNode("div", _hoisted_36, [
                  _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": _cache[12] || (_cache[12] = $event => ((form.api_key) = $event)),
                    type: secretVisible.api_key?'text':'password'
                  }, null, 8, _hoisted_37), [
                    [_vModelDynamic, form.api_key]
                  ]),
                  _createElementVNode("button", {
                    type: "button",
                    "aria-label": secretVisible.api_key?'隐藏 API Key':'显示 API Key',
                    onClick: _cache[13] || (_cache[13] = $event => (secretVisible.api_key=!secretVisible.api_key))
                  }, [...(_cache[47] || (_cache[47] = [
                    _createElementVNode("svg", {
                      viewBox: "0 0 24 24",
                      "aria-hidden": "true"
                    }, [
                      _createElementVNode("path", { d: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" }),
                      _createElementVNode("circle", {
                        cx: "12",
                        cy: "12",
                        r: "3"
                      })
                    ], -1)
                  ]))], 8, _hoisted_38)
                ])
              ]),
              _createElementVNode("label", null, [
                _cache[49] || (_cache[49] = _createTextVNode("用户 ID ", -1)),
                _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": _cache[14] || (_cache[14] = $event => ((form.user_id) = $event)),
                  placeholder: "留空自动获取"
                }, null, 512), [
                  [
                    _vModelText,
                    form.user_id,
                    void 0,
                    { trim: true }
                  ]
                ])
              ]),
              _createElementVNode("label", null, [
                _cache[51] || (_cache[51] = _createTextVNode("TMDB API Key", -1)),
                _createElementVNode("div", _hoisted_39, [
                  _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": _cache[15] || (_cache[15] = $event => ((form.tmdb_key) = $event)),
                    type: secretVisible.tmdb_key?'text':'password'
                  }, null, 8, _hoisted_40), [
                    [_vModelDynamic, form.tmdb_key]
                  ]),
                  _createElementVNode("button", {
                    type: "button",
                    "aria-label": secretVisible.tmdb_key?'隐藏 TMDB API Key':'显示 TMDB API Key',
                    onClick: _cache[16] || (_cache[16] = $event => (secretVisible.tmdb_key=!secretVisible.tmdb_key))
                  }, [...(_cache[50] || (_cache[50] = [
                    _createElementVNode("svg", {
                      viewBox: "0 0 24 24",
                      "aria-hidden": "true"
                    }, [
                      _createElementVNode("path", { d: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" }),
                      _createElementVNode("circle", {
                        cx: "12",
                        cy: "12",
                        r: "3"
                      })
                    ], -1)
                  ]))], 8, _hoisted_41)
                ])
              ]),
              _createElementVNode("label", _hoisted_42, [
                _cache[52] || (_cache[52] = _createTextVNode("媒体库名称", -1)),
                _withDirectives(_createElementVNode("textarea", {
                  "onUpdate:modelValue": _cache[17] || (_cache[17] = $event => ((form.library_names) = $event)),
                  rows: "5",
                  placeholder: "每行一个；留空处理全部"
                }, null, 512), [
                  [_vModelText, form.library_names]
                ])
              ])
            ]),
            _cache[57] || (_cache[57] = _createElementVNode("hr", null, null, -1)),
            _createElementVNode("div", _hoisted_43, [
              _createElementVNode("label", _hoisted_44, [
                _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": _cache[18] || (_cache[18] = $event => ((form.lock_modified_fields) = $event)),
                  type: "checkbox"
                }, null, 512), [
                  [_vModelCheckbox, form.lock_modified_fields]
                ]),
                _cache[53] || (_cache[53] = _createElementVNode("span", null, "仅锁定本次修改的字段", -1))
              ]),
              _createElementVNode("label", _hoisted_45, [
                _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": _cache[19] || (_cache[19] = $event => ((form.add_hant_title) = $event)),
                  type: "checkbox"
                }, null, 512), [
                  [_vModelCheckbox, form.add_hant_title]
                ]),
                _cache[54] || (_cache[54] = _createElementVNode("span", null, "别名包含繁中标题", -1))
              ]),
              _createElementVNode("label", null, [
                _cache[55] || (_cache[55] = _createTextVNode("输出条目上限", -1)),
                _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": _cache[20] || (_cache[20] = $event => ((form.max_output) = $event)),
                  type: "number",
                  min: "5",
                  max: "200"
                }, null, 512), [
                  [
                    _vModelText,
                    form.max_output,
                    void 0,
                    { number: true }
                  ]
                ])
              ])
            ]),
            _cache[58] || (_cache[58] = _createElementVNode("p", { class: "hint lock-policy" }, "只维护 LockedFields，不新增条目整体锁；保留用户已有的整体锁。旧版造成的误锁不会自动解除，请在“误锁修复”中先核对、预览。", -1))
          ]))
        : (tab.value==='locks')
          ? (_openBlock(), _createElementBlock("main", _hoisted_46, [
              _cache[64] || (_cache[64] = _createElementVNode("div", { class: "settings-title" }, [
                _createElementVNode("h2", null, "历史误锁修复"),
                _createElementVNode("p", null, "只处理你明确指定并确认的条目，不会自动全库解锁。")
              ], -1)),
              _cache[65] || (_cache[65] = _createElementVNode("div", { class: "repair-warning" }, [
                _createElementVNode("strong", null, "先核对来源，再解除整体锁"),
                _createElementVNode("p", null, "历史整体锁的来源无法自动判定。请只填写你已确认被旧版工具箱影响的条目 ID；手动设置的整体锁也可能被解除，必须逐项核对。"),
                _createElementVNode("p", null, "修复保留 LockedFields 字段锁，不主动刷新元数据，也不直接修改磁盘 NFO；Emby 自身是否同步保存 NFO 由其保存器设置决定。旧 NFO 中仍有 lockdata 时，后续重新导入可能再次锁定。")
              ], -1)),
              _createElementVNode("label", _hoisted_47, [
                _cache[59] || (_cache[59] = _createTextVNode("已确认需要修复的条目 ID", -1)),
                _withDirectives(_createElementVNode("textarea", {
                  id: "emby-lock-repair-ids",
                  "onUpdate:modelValue": _cache[21] || (_cache[21] = $event => ((rawIds).value = $event)),
                  rows: "5",
                  maxlength: "50000",
                  disabled: operationBlocked.value,
                  spellcheck: "false",
                  placeholder: "例如：268389, 268390；也可每行一个 ID",
                  "aria-describedby": "emby-lock-repair-help"
                }, null, 8, _hoisted_48), [
                  [_vModelText, rawIds.value]
                ])
              ]),
              _createElementVNode("p", _hoisted_49, "用逗号、空格或换行分隔，每次最多 500 个不同 ID。当前填写 " + _toDisplayString(repairIds.value.length) + " 个；此操作不使用“媒体库名称”筛选。", 1),
              _createElementVNode("label", _hoisted_50, [
                _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": _cache[22] || (_cache[22] = $event => ((includeChildren).value = $event)),
                  type: "checkbox",
                  disabled: operationBlocked.value
                }, null, 8, _hoisted_51), [
                  [_vModelCheckbox, includeChildren.value]
                ]),
                _cache[60] || (_cache[60] = _createElementVNode("span", null, "同时检查指定剧集或季下，字段锁为空的季 / 单集（默认不勾选）", -1))
              ]),
              _createElementVNode("div", _hoisted_52, [
                _createElementVNode("button", {
                  class: "ghost",
                  disabled: operationBlocked.value||Boolean(repairInputError.value),
                  onClick: previewLocks
                }, _toDisplayString(busy.value==='locks-preview'?'正在启动预览…':'只预览，不修改'), 9, _hoisted_53),
                _createElementVNode("button", {
                  class: "ghost",
                  disabled: operationBlocked.value,
                  onClick: downloadLockBackup
                }, _toDisplayString(busy.value==='locks-backup'?'准备下载…':'下载最近一次备份'), 9, _hoisted_54)
              ]),
              (repairError.value)
                ? (_openBlock(), _createElementBlock("p", _hoisted_55, _toDisplayString(repairError.value), 1))
                : _createCommentVNode("", true),
              (status.running)
                ? (_openBlock(), _createElementBlock("p", _hoisted_56, "后台任务进行中：" + _toDisplayString(status.task||'请等待') + "。提交成功不代表已经完成，最终结果会在下方自动更新。", 1))
                : _createCommentVNode("", true),
              (lockRepair.value.message||lockRepair.value.token)
                ? (_openBlock(), _createElementBlock("section", _hoisted_57, [
                    _cache[63] || (_cache[63] = _createElementVNode("h3", null, "预览与执行结果", -1)),
                    _createElementVNode("p", null, _toDisplayString(lockRepair.value.message), 1),
                    (lockRepair.value.token)
                      ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
                          _createElementVNode("p", null, "候选条目 " + _toDisplayString(lockRepair.value.count||0) + " 项：指定条目 " + _toDisplayString(lockRepair.value.root_count||0) + " 项，下级条目 " + _toDisplayString(lockRepair.value.child_count||0) + " 项。", 1),
                          _cache[61] || (_cache[61] = _createElementVNode("p", { class: "repair-help" }, "列表仅展示前 100 项，不代表完整清单。预览有有效期；任何输入变化后都必须重新预览。", -1))
                        ], 64))
                      : _createCommentVNode("", true),
                    (previewItems.value.length)
                      ? (_openBlock(), _createElementBlock("ul", _hoisted_58, [
                          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(previewItems.value, (item) => {
                            return (_openBlock(), _createElementBlock("li", {
                              key: item.id
                            }, [
                              _createElementVNode("div", null, [
                                _createElementVNode("strong", null, _toDisplayString(item.name||'未命名条目'), 1),
                                _createElementVNode("span", null, _toDisplayString(item.type) + " · ID " + _toDisplayString(item.id), 1)
                              ]),
                              _createElementVNode("p", null, "保留字段锁：" + _toDisplayString(Array.isArray(item.fields)&&item.fields.length?item.fields.join('、'):'无'), 1),
                              (item.reason)
                                ? (_openBlock(), _createElementBlock("p", _hoisted_59, _toDisplayString(item.reason), 1))
                                : _createCommentVNode("", true)
                            ]))
                          }), 128))
                        ]))
                      : _createCommentVNode("", true),
                    (lockRepair.value.token&&!previewToken.value&&!status.running)
                      ? (_openBlock(), _createElementBlock("p", _hoisted_60, "此预览不能直接执行。请按当前输入重新预览，再确认修复。"))
                      : _createCommentVNode("", true),
                    _createElementVNode("label", _hoisted_61, [
                      _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": _cache[23] || (_cache[23] = $event => ((repairConfirmed).value = $event)),
                        type: "checkbox",
                        disabled: operationBlocked.value||!previewToken.value
                      }, null, 8, _hoisted_62), [
                        [_vModelCheckbox, repairConfirmed.value]
                      ]),
                      _cache[62] || (_cache[62] = _createElementVNode("span", null, "我已逐项核对，确认这些整体锁属于误锁，并理解手动锁也可能被解除。", -1))
                    ]),
                    _createElementVNode("button", {
                      class: "primary",
                      disabled: !canApplyRepair.value,
                      onClick: applyLocks
                    }, _toDisplayString(busy.value==='locks-apply'?'正在启动修复…':'备份并解除这些整体锁'), 9, _hoisted_63)
                  ]))
                : _createCommentVNode("", true),
              _cache[66] || (_cache[66] = _createElementVNode("p", { class: "repair-help" }, "执行前会先将锁状态备份保存于平台插件存储，备份失败则不会写入 Emby。平台仅保留最近一批，请下载另存后再修复下一批；此文件供核对锁状态，不是媒体库备份或自动回滚文件。所有修复任务均为手动操作，不加入定时计划。", -1))
            ]))
          : (_openBlock(), _createElementBlock("main", _hoisted_64, [
              _createElementVNode("div", _hoisted_65, [
                _cache[68] || (_cache[68] = _createElementVNode("div", null, [
                  _createElementVNode("span", { class: "kicker" }, "ACTIVITY"),
                  _createElementVNode("h2", null, "运行记录")
                ], -1)),
                _createElementVNode("span", {
                  class: _normalizeClass(["state", {live:status.running}])
                }, [
                  _cache[67] || (_cache[67] = _createElementVNode("i", null, null, -1)),
                  _createTextVNode(_toDisplayString(status.running?'运行中':'自动刷新'), 1)
                ], 2)
              ]),
              (!status.history?.length)
                ? (_openBlock(), _createElementBlock("div", _hoisted_66, "还没有维护记录。运行一次任务后，结果会留在这里。"))
                : _createCommentVNode("", true),
              (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(status.history, (row) => {
                return (_openBlock(), _createElementBlock("article", _hoisted_67, [
                  _createElementVNode("i", {
                    class: _normalizeClass(row.ok?'ok':'bad')
                  }, null, 2),
                  _createElementVNode("div", null, [
                    _createElementVNode("strong", null, _toDisplayString(row.task), 1),
                    _createElementVNode("span", null, _toDisplayString(row.source) + " · " + _toDisplayString(row.time), 1),
                    _createElementVNode("pre", null, _toDisplayString(row.summary), 1)
                  ])
                ]))
              }), 256))
            ]))
  ]))
}
}

};
const Config = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-ab3072f8"]]);

export { Config as default };
