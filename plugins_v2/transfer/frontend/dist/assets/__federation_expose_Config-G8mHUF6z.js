import { importShared } from './__federation_fn_import-JrT3xvdd.js';

const _export_sfc = (sfc, props) => {
  const target = sfc.__vccOpts || sfc;
  for (const [key, val] of props) {
    target[key] = val;
  }
  return target;
};

const {renderSlot:_renderSlot,openBlock:_openBlock$1,createElementBlock:_createElementBlock$1} = await importShared('vue');


const _hoisted_1$1 = { class: "aw-ios-settings" };


const _sfc_main$1 = {
  __name: 'IosSettings',
  setup(__props) {

// Shared presentation only. The plugin retains its own state, APIs and actions.

return (_ctx, _cache) => {
  return (_openBlock$1(), _createElementBlock$1("div", _hoisted_1$1, [
    _renderSlot(_ctx.$slots, "default", {}, undefined, true)
  ]))
}
}

};
const IosSettings = /*#__PURE__*/_export_sfc(_sfc_main$1, [['__scopeId',"data-v-3b88f062"]]);

const {createElementVNode:_createElementVNode,openBlock:_openBlock,createElementBlock:_createElementBlock,createCommentVNode:_createCommentVNode,normalizeClass:_normalizeClass,normalizeStyle:_normalizeStyle,toDisplayString:_toDisplayString,renderList:_renderList,Fragment:_Fragment,createTextVNode:_createTextVNode,vModelSelect:_vModelSelect,withDirectives:_withDirectives,vModelText:_vModelText,vModelCheckbox:_vModelCheckbox,vShow:_vShow,withCtx:_withCtx,createBlock:_createBlock} = await importShared('vue');


const _hoisted_1 = { class: "tf" };
const _hoisted_2 = {
  key: 0,
  class: "tf-loading",
  role: "status"
};
const _hoisted_3 = ["aria-pressed"];
const _hoisted_4 = ["aria-pressed"];
const _hoisted_5 = {
  key: 0,
  class: "tf-load-error",
  role: "alert"
};
const _hoisted_6 = { class: "tf-layout" };
const _hoisted_7 = {
  class: "tf-sidebar",
  "aria-label": "设置分组"
};
const _hoisted_8 = ["aria-pressed", "onClick"];
const _hoisted_9 = { class: "tf-detail" };
const _hoisted_10 = { class: "tf-site-list" };
const _hoisted_11 = { class: "tf-site-head" };
const _hoisted_12 = { class: "tf-site-bonus" };
const _hoisted_13 = {
  key: 0,
  class: "tf-site-note"
};
const _hoisted_14 = { class: "tf-site-controls" };
const _hoisted_15 = ["checked", "aria-label", "disabled", "onChange"];
const _hoisted_16 = { class: "tf-group" };
const _hoisted_17 = { class: "tf-row" };
const _hoisted_18 = ["value"];
const _hoisted_19 = {
  key: 0,
  class: "tf-tip tf-row-note"
};
const _hoisted_20 = {
  key: 1,
  class: "tf-tip tf-row-note"
};
const _hoisted_21 = {
  key: 2,
  class: "tf-tip tf-row-note"
};
const _hoisted_22 = { class: "tf-row tf-row-separated" };
const _hoisted_23 = { class: "tf-row tf-row-separated" };
const _hoisted_24 = { class: "tf-group" };
const _hoisted_25 = { class: "tf-range" };
const _hoisted_26 = { class: "tf-row" };
const _hoisted_27 = { class: "tf-unit" };
const _hoisted_28 = { class: "tf-row" };
const _hoisted_29 = { class: "tf-unit" };
const _hoisted_30 = { class: "tf-group" };
const _hoisted_31 = { class: "tf-switch-row tf-row-separated" };
const _hoisted_32 = { class: "tf-savebar" };
const _hoisted_33 = ["disabled"];
const _hoisted_34 = {
  class: "tf-pane",
  "aria-label": "排行榜与最近流水"
};
const _hoisted_35 = { class: "tf-toolbar" };
const _hoisted_36 = {
  key: 0,
  value: ""
};
const _hoisted_37 = ["value"];
const _hoisted_38 = ["aria-pressed"];
const _hoisted_39 = ["aria-pressed"];
const _hoisted_40 = ["disabled"];
const _hoisted_41 = ["disabled"];
const _hoisted_42 = {
  key: 0,
  class: "tf-loading",
  role: "status"
};
const _hoisted_43 = {
  key: 1,
  class: "tf-field-error",
  role: "alert"
};
const _hoisted_44 = {
  key: 2,
  class: "tf-empty"
};
const _hoisted_45 = {
  key: 3,
  class: "tf-table-wrap"
};
const _hoisted_46 = { class: "tf-table" };
const _hoisted_47 = { class: "tf-rank" };
const _hoisted_48 = { class: "tf-muted" };
const _hoisted_49 = {
  key: 4,
  class: "tf-history"
};
const _hoisted_50 = { class: "tf-table-wrap" };
const _hoisted_51 = { class: "tf-table" };
const _hoisted_52 = { class: "tf-muted" };
const _hoisted_53 = { class: "tf-muted tf-time" };

const {ref,reactive,onMounted,computed} = await importShared('vue');

const _sfc_main = {
  __name: 'Config',
  props: { pluginId: { type: String, required: true }, host: { type: Object, required: true } },
  setup(__props) {

// 从已发布的 2.0.11 未压缩组件恢复可维护源码，保留现有站点/榜单/延迟/流水功能。
// SSD 确认配置独立交由 SSD 助手，排行榜只监听官方成功回执。
const props = __props;
const SITES = [
  { key: 'site_audiences', label: 'Audiences', bonus: '爆米花' },
  { key: 'site_hddolby', label: 'HDDolby', bonus: '鲸币' },
  { key: 'site_azusa', label: 'Azusa', bonus: '魔力值' },
  { key: 'site_zm', label: 'ZmPT', bonus: '电力', note: '致谢/榜单自动延后约11秒发出' },
  { key: 'site_springsunday', label: 'SpringSunday', bonus: '茉莉', note: '含两个群' },
  { key: 'site_hdsky', label: 'HDSky', bonus: '银元' },
  { key: 'site_hhanclub', label: 'HHanClub', bonus: '憨豆', note: '仅记录官方机器人确认成功的赠送' },
  { key: 'site_mocktest', label: 'MockTest', bonus: '测试', note: '默认关' },
];
const TOGGLES = [{ v: 'on', l: '启用' }, { v: 'notify', l: '群内致谢' }, { v: 'lb_in', l: '打赏榜' }, { v: 'lb_out', l: '赏赐榜' }];
const RANK_OUTPUTS = [{ v: 'image', l: '图片（默认）' }, { v: 'rich_table', l: '富文本表格（Premium）' }, { v: 'text', l: '文本' }];
const DEFAULTS = {
  site_audiences: ['on', 'notify', 'lb_in', 'lb_out'], site_hddolby: ['on', 'notify', 'lb_in', 'lb_out'],
  site_azusa: ['on', 'notify', 'lb_in', 'lb_out'], site_zm: ['on', 'notify', 'lb_in', 'lb_out'],
  site_springsunday: ['on', 'notify', 'lb_in', 'lb_out'], site_hdsky: ['on', 'notify', 'lb_in', 'lb_out'],
  site_hhanclub: ['on', 'notify', 'lb_in', 'lb_out'], site_mocktest: [],
  rank_output: 'image', rank_size: 10, rank_command: '转账排行', notify_delay_min: 0, notify_delay_max: 0, owner_notify: false,
};
const GROUPS = [{ key: 'sites', label: '站点' }, { key: 'rank', label: '排行榜' }, { key: 'delay', label: '致谢延迟' }, { key: 'adv', label: '进阶' }];
const tab = ref('settings');
const group = ref('sites');
const loading = ref(true);
const configReady = ref(false);
const loadError = ref('');
const saving = ref(false);
const cfg = reactive({ ...DEFAULTS });
const sites = ref([]);
const lbSite = ref('');
const lbDir = ref('in');
const lbRows = ref([]);
const lbLoading = ref(false);
const recent = ref([]);
const rankError = ref('');
let rankRequest = 0;
const bonusOf = computed(() => sites.value.find(item => item.name === lbSite.value)?.bonus || '');
function errorText(error) { return String(error?.message || error || '未知错误') }
async function loadConfig() {
  if (saving.value) return
  loading.value = true;
  configReady.value = false;
  loadError.value = '';
  try {
    const saved = await props.host.getConfig();
    if (saved != null && (typeof saved !== 'object' || Array.isArray(saved))) throw new Error('配置格式不正确')
    Object.assign(cfg, DEFAULTS, saved || {});
    // 不再把已迁走的自动确认字段写回排行榜配置。
    delete cfg['ssd_click_mode'];
    if (!RANK_OUTPUTS.some(item => item.v === cfg.rank_output)) cfg.rank_output = 'text';
    for (const site of SITES) if (!Array.isArray(cfg[site.key])) cfg[site.key] = [];
    configReady.value = true;
  } catch (error) {
    loadError.value = '读取配置失败：' + errorText(error);
    props.host.toast.error(loadError.value);
  } finally { loading.value = false; }
}
onMounted(loadConfig);
function has(key, value) { return (cfg[key] || []).includes(value) }
function toggle(key, value) {
  const values = (cfg[key] || []).slice();
  const index = values.indexOf(value);
  if (index >= 0) values.splice(index, 1);
  else values.push(value);
  cfg[key] = values;
}
async function save() {
  if (!configReady.value || saving.value) return
  saving.value = true;
  try { await props.host.saveConfig({ ...cfg }); props.host.toast.success('配置已保存'); }
  catch (error) { props.host.toast.error('保存失败：' + errorText(error)); }
  finally { saving.value = false; }
}
async function loadSites() {
  try {
    const result = await props.host.callApi('/sites');
    sites.value = Array.isArray(result?.sites) ? result.sites : [];
    if (!lbSite.value && sites.value.length) lbSite.value = (sites.value.find(item => item.has_data) || sites.value[0]).name;
    await Promise.all([loadLeaderboard(), loadRecent()]);
  } catch (error) { rankError.value = '读取站点失败：' + errorText(error); props.host.toast.error(rankError.value); }
}
async function loadLeaderboard() {
  const request = ++rankRequest;
  if (!lbSite.value) { lbRows.value = []; return }
  lbLoading.value = true;
  rankError.value = '';
  try {
    const result = await props.host.callApi(`/leaderboard?site=${encodeURIComponent(lbSite.value)}&dir=${lbDir.value}&limit=${cfg.rank_size || 10}`);
    if (request === rankRequest) lbRows.value = Array.isArray(result?.items) ? result.items : [];
  } catch (error) {
    if (request === rankRequest) { rankError.value = '读取排行榜失败：' + errorText(error); props.host.toast.error(rankError.value); }
  } finally { if (request === rankRequest) lbLoading.value = false; }
}
async function loadRecent() {
  try { const result = await props.host.callApi('/recent'); recent.value = Array.isArray(result?.items) ? result.items : []; }
  catch { /* 流水拉取失败不妨碍查看排行榜。 */ }
}
async function resetSite() {
  if (!lbSite.value || !confirm(`清空站点「${lbSite.value}」的全部转账记录与排行榜？此操作不可恢复。`)) return
  try {
    await props.host.callApi('/reset', { method: 'POST', body: { site: lbSite.value } });
    lbRows.value = [];
    props.host.toast.success('已清空');
    await loadSites();
  } catch (error) { props.host.toast.error('清空失败：' + errorText(error)); }
}
function fmtTime(value) { return String(value || '').replace('T', ' ').slice(0, 16) }
function switchTab(value) { tab.value = value; if (value === 'rank' && !sites.value.length) loadSites(); }

return (_ctx, _cache) => {
  return (_openBlock(), _createBlock(IosSettings, null, {
    default: _withCtx(() => [
      _createElementVNode("div", _hoisted_1, [
        _cache[35] || (_cache[35] = _createElementVNode("header", { class: "tf-heading" }, [
          _createElementVNode("div", null, [
            _createElementVNode("h2", null, "多站点转账"),
            _createElementVNode("p", null, "按站点管理致谢与排行榜，查看官方成功回执记录。")
          ])
        ], -1)),
        (loading.value)
          ? (_openBlock(), _createElementBlock("div", _hoisted_2, "加载配置…"))
          : (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
              _createElementVNode("nav", {
                class: "tf-tabs",
                style: _normalizeStyle({ '--tf-tab-index': tab.value === 'rank' ? 1 : 0 }),
                "aria-label": "多站点转账页面"
              }, [
                _createElementVNode("button", {
                  type: "button",
                  class: _normalizeClass(['tf-tab', { on: tab.value === 'settings' }]),
                  "aria-pressed": tab.value === 'settings',
                  onClick: _cache[0] || (_cache[0] = $event => (switchTab('settings')))
                }, "配置", 10, _hoisted_3),
                _createElementVNode("button", {
                  type: "button",
                  class: _normalizeClass(['tf-tab', { on: tab.value === 'rank' }]),
                  "aria-pressed": tab.value === 'rank',
                  onClick: _cache[1] || (_cache[1] = $event => (switchTab('rank')))
                }, "排行榜", 10, _hoisted_4)
              ], 4),
              (loadError.value)
                ? (_openBlock(), _createElementBlock("div", _hoisted_5, [
                    _createElementVNode("p", null, _toDisplayString(loadError.value) + "。读取成功前不能保存，以免覆盖原设置。", 1),
                    _createElementVNode("button", {
                      type: "button",
                      class: "tf-button",
                      onClick: loadConfig
                    }, "重新读取配置")
                  ]))
                : _createCommentVNode("", true),
              _withDirectives(_createElementVNode("div", _hoisted_6, [
                _createElementVNode("aside", _hoisted_7, [
                  _cache[12] || (_cache[12] = _createElementVNode("div", { class: "tf-side-title" }, "设置分组", -1)),
                  (_openBlock(), _createElementBlock(_Fragment, null, _renderList(GROUPS, (item) => {
                    return _createElementVNode("button", {
                      key: item.key,
                      type: "button",
                      class: _normalizeClass(['tf-side-item', { on: group.value === item.key }]),
                      "aria-pressed": group.value === item.key,
                      onClick: $event => (group.value = item.key)
                    }, [
                      _createTextVNode(_toDisplayString(item.label), 1),
                      _cache[11] || (_cache[11] = _createElementVNode("svg", {
                        viewBox: "0 0 16 16",
                        fill: "none",
                        "aria-hidden": "true"
                      }, [
                        _createElementVNode("path", {
                          d: "m6 3 5 5-5 5",
                          stroke: "currentColor",
                          "stroke-width": "1.6",
                          "stroke-linecap": "round",
                          "stroke-linejoin": "round"
                        })
                      ], -1))
                    ], 10, _hoisted_8)
                  }), 64))
                ]),
                _createElementVNode("main", _hoisted_9, [
                  (group.value === 'sites')
                    ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
                        _cache[13] || (_cache[13] = _createElementVNode("div", { class: "tf-section-heading" }, [
                          _createElementVNode("h3", null, "站点开关"),
                          _createElementVNode("p", { class: "tf-tip" }, "群组/转账 bot 已内置，这里按站点开关功能：启用=监听记录；群内致谢=收/发后群里回一句；打赏榜/赏赐榜=致谢里附转入/转出排行榜。")
                        ], -1)),
                        _createElementVNode("div", _hoisted_10, [
                          (_openBlock(), _createElementBlock(_Fragment, null, _renderList(SITES, (site) => {
                            return _createElementVNode("section", {
                              key: site.key,
                              class: "tf-site"
                            }, [
                              _createElementVNode("div", _hoisted_11, [
                                _createElementVNode("h4", null, _toDisplayString(site.label), 1),
                                _createElementVNode("span", _hoisted_12, _toDisplayString(site.bonus), 1),
                                (site.note)
                                  ? (_openBlock(), _createElementBlock("span", _hoisted_13, _toDisplayString(site.note), 1))
                                  : _createCommentVNode("", true)
                              ]),
                              _createElementVNode("div", _hoisted_14, [
                                (_openBlock(), _createElementBlock(_Fragment, null, _renderList(TOGGLES, (option) => {
                                  return _createElementVNode("label", {
                                    key: option.v,
                                    class: _normalizeClass(['tf-site-option', { on: has(site.key, option.v) }])
                                  }, [
                                    _createElementVNode("span", null, _toDisplayString(option.l), 1),
                                    _createElementVNode("input", {
                                      type: "checkbox",
                                      role: "switch",
                                      checked: has(site.key, option.v),
                                      "aria-label": site.label + ' · ' + option.l,
                                      disabled: !configReady.value || saving.value,
                                      onChange: $event => (toggle(site.key, option.v))
                                    }, null, 40, _hoisted_15)
                                  ], 2)
                                }), 64))
                              ])
                            ])
                          }), 64))
                        ])
                      ], 64))
                    : (group.value === 'rank')
                      ? (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
                          _cache[18] || (_cache[18] = _createElementVNode("div", { class: "tf-section-heading" }, [
                            _createElementVNode("h3", null, "排行榜")
                          ], -1)),
                          _createElementVNode("section", _hoisted_16, [
                            _createElementVNode("label", _hoisted_17, [
                              _cache[14] || (_cache[14] = _createElementVNode("span", null, "输出形式", -1)),
                              _withDirectives(_createElementVNode("select", {
                                "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((cfg.rank_output) = $event)),
                                class: "tf-input"
                              }, [
                                (_openBlock(), _createElementBlock(_Fragment, null, _renderList(RANK_OUTPUTS, (option) => {
                                  return _createElementVNode("option", {
                                    key: option.v,
                                    value: option.v
                                  }, _toDisplayString(option.l), 9, _hoisted_18)
                                }), 64))
                              ], 512), [
                                [_vModelSelect, cfg.rank_output]
                              ])
                            ]),
                            (cfg.rank_output === 'rich_table')
                              ? (_openBlock(), _createElementBlock("p", _hoisted_19, "仅 Telegram Premium 会员账号可使用原生富文本表格；普通账号或发送失败时，会自动回退为正常文本排行榜。"))
                              : (cfg.rank_output === 'image')
                                ? (_openBlock(), _createElementBlock("p", _hoisted_20, "图片生成或发送失败时会自动回退为文本排行榜。"))
                                : (_openBlock(), _createElementBlock("p", _hoisted_21, "文本模式兼容所有账号。")),
                            _createElementVNode("label", _hoisted_22, [
                              _cache[15] || (_cache[15] = _createElementVNode("span", null, "排行榜人数", -1)),
                              _withDirectives(_createElementVNode("input", {
                                "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((cfg.rank_size) = $event)),
                                class: "tf-input tf-small",
                                type: "number",
                                min: "3",
                                max: "30"
                              }, null, 512), [
                                [
                                  _vModelText,
                                  cfg.rank_size,
                                  void 0,
                                  { number: true }
                                ]
                              ])
                            ]),
                            _createElementVNode("label", _hoisted_23, [
                              _cache[16] || (_cache[16] = _createElementVNode("span", null, "命令词", -1)),
                              _withDirectives(_createElementVNode("input", {
                                "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((cfg.rank_command) = $event)),
                                class: "tf-input"
                              }, null, 512), [
                                [_vModelText, cfg.rank_command]
                              ])
                            ]),
                            _cache[17] || (_cache[17] = _createElementVNode("p", { class: "tf-tip tf-row-note" }, "在任意聊天发「.命令词 [站点] [in/out]」拉排行榜，如 .转账排行 hdsky in。", -1))
                          ])
                        ], 64))
                      : (group.value === 'delay')
                        ? (_openBlock(), _createElementBlock(_Fragment, { key: 2 }, [
                            _cache[24] || (_cache[24] = _createElementVNode("div", { class: "tf-section-heading" }, [
                              _createElementVNode("h3", null, "致谢延迟")
                            ], -1)),
                            _createElementVNode("section", _hoisted_24, [
                              _cache[23] || (_cache[23] = _createElementVNode("p", { class: "tf-tip tf-group-note" }, "记录到转账后等待若干秒再发致谢，模拟人工（0=不等）。", -1)),
                              _createElementVNode("div", _hoisted_25, [
                                _createElementVNode("label", _hoisted_26, [
                                  _cache[20] || (_cache[20] = _createElementVNode("span", null, "最小", -1)),
                                  _createElementVNode("div", _hoisted_27, [
                                    _withDirectives(_createElementVNode("input", {
                                      "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((cfg.notify_delay_min) = $event)),
                                      class: "tf-input tf-small",
                                      type: "number",
                                      min: "0",
                                      max: "300"
                                    }, null, 512), [
                                      [
                                        _vModelText,
                                        cfg.notify_delay_min,
                                        void 0,
                                        { number: true }
                                      ]
                                    ]),
                                    _cache[19] || (_cache[19] = _createElementVNode("span", null, "秒", -1))
                                  ])
                                ]),
                                _createElementVNode("label", _hoisted_28, [
                                  _cache[22] || (_cache[22] = _createElementVNode("span", null, "最大", -1)),
                                  _createElementVNode("div", _hoisted_29, [
                                    _withDirectives(_createElementVNode("input", {
                                      "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((cfg.notify_delay_max) = $event)),
                                      class: "tf-input tf-small",
                                      type: "number",
                                      min: "0",
                                      max: "300"
                                    }, null, 512), [
                                      [
                                        _vModelText,
                                        cfg.notify_delay_max,
                                        void 0,
                                        { number: true }
                                      ]
                                    ]),
                                    _cache[21] || (_cache[21] = _createElementVNode("span", null, "秒", -1))
                                  ])
                                ])
                              ])
                            ])
                          ], 64))
                        : (group.value === 'adv')
                          ? (_openBlock(), _createElementBlock(_Fragment, { key: 3 }, [
                              _cache[27] || (_cache[27] = _createElementVNode("div", { class: "tf-section-heading" }, [
                                _createElementVNode("h3", null, "进阶")
                              ], -1)),
                              _createElementVNode("section", _hoisted_30, [
                                _cache[26] || (_cache[26] = _createElementVNode("p", { class: "tf-tip tf-group-note" }, "SSD 自动确认转账已移到「SSD 助手」，请在新插件中单独开启。本插件不再点击确认，继续依据成功回执记账和发送排行榜。", -1)),
                                _createElementVNode("label", _hoisted_31, [
                                  _cache[25] || (_cache[25] = _createElementVNode("span", null, "每笔转账推送给平台主人", -1)),
                                  _withDirectives(_createElementVNode("input", {
                                    "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => ((cfg.owner_notify) = $event)),
                                    type: "checkbox",
                                    role: "switch"
                                  }, null, 512), [
                                    [_vModelCheckbox, cfg.owner_notify]
                                  ])
                                ])
                              ])
                            ], 64))
                          : _createCommentVNode("", true),
                  _createElementVNode("footer", _hoisted_32, [
                    _cache[28] || (_cache[28] = _createElementVNode("p", null, "修改后请保存，配置仅在保存后生效。", -1)),
                    _createElementVNode("button", {
                      type: "button",
                      class: "tf-button tf-primary",
                      disabled: saving.value || !configReady.value,
                      onClick: save
                    }, _toDisplayString(saving.value ? '保存中…' : '保存配置'), 9, _hoisted_33)
                  ])
                ])
              ], 512), [
                [_vShow, tab.value === 'settings']
              ]),
              _withDirectives(_createElementVNode("section", _hoisted_34, [
                _createElementVNode("div", _hoisted_35, [
                  _withDirectives(_createElementVNode("select", {
                    "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => ((lbSite).value = $event)),
                    class: "tf-input tf-site-select",
                    "aria-label": "排行榜站点",
                    onChange: loadLeaderboard
                  }, [
                    (!sites.value.length)
                      ? (_openBlock(), _createElementBlock("option", _hoisted_36, "（无数据）"))
                      : _createCommentVNode("", true),
                    (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(sites.value, (site) => {
                      return (_openBlock(), _createElementBlock("option", {
                        key: site.name,
                        value: site.name
                      }, _toDisplayString(site.name) + _toDisplayString(site.has_data ? '' : '（空）'), 9, _hoisted_37))
                    }), 128))
                  ], 544), [
                    [_vModelSelect, lbSite.value]
                  ]),
                  _createElementVNode("div", {
                    class: "tf-direction",
                    style: _normalizeStyle({ '--tf-direction-index': lbDir.value === 'out' ? 1 : 0 }),
                    "aria-label": "排行榜方向"
                  }, [
                    _createElementVNode("button", {
                      type: "button",
                      class: _normalizeClass(['tf-direction-button', { on: lbDir.value === 'in' }]),
                      "aria-pressed": lbDir.value === 'in',
                      onClick: _cache[9] || (_cache[9] = $event => {lbDir.value = 'in'; loadLeaderboard();})
                    }, "打赏榜(转入)", 10, _hoisted_38),
                    _createElementVNode("button", {
                      type: "button",
                      class: _normalizeClass(['tf-direction-button', { on: lbDir.value === 'out' }]),
                      "aria-pressed": lbDir.value === 'out',
                      onClick: _cache[10] || (_cache[10] = $event => {lbDir.value = 'out'; loadLeaderboard();})
                    }, "赏赐榜(转出)", 10, _hoisted_39)
                  ], 4),
                  _cache[29] || (_cache[29] = _createElementVNode("span", { class: "tf-grow" }, null, -1)),
                  _createElementVNode("button", {
                    type: "button",
                    class: "tf-button",
                    disabled: lbLoading.value,
                    onClick: loadSites
                  }, "刷新", 8, _hoisted_40),
                  _createElementVNode("button", {
                    type: "button",
                    class: "tf-button tf-danger",
                    disabled: !lbSite.value || lbLoading.value,
                    onClick: resetSite
                  }, "清空该站", 8, _hoisted_41)
                ]),
                (lbLoading.value)
                  ? (_openBlock(), _createElementBlock("div", _hoisted_42, "加载中…"))
                  : (rankError.value)
                    ? (_openBlock(), _createElementBlock("p", _hoisted_43, _toDisplayString(rankError.value), 1))
                    : (!lbRows.value.length)
                      ? (_openBlock(), _createElementBlock("div", _hoisted_44, "该站点暂无" + _toDisplayString(lbDir.value === 'in' ? '转入' : '转出') + "数据", 1))
                      : (_openBlock(), _createElementBlock("div", _hoisted_45, [
                          _createElementVNode("table", _hoisted_46, [
                            _createElementVNode("thead", null, [
                              _createElementVNode("tr", null, [
                                _cache[30] || (_cache[30] = _createElementVNode("th", null, "名次", -1)),
                                _cache[31] || (_cache[31] = _createElementVNode("th", null, "用户", -1)),
                                _createElementVNode("th", null, "累计" + _toDisplayString(bonusOf.value), 1),
                                _cache[32] || (_cache[32] = _createElementVNode("th", null, "笔数", -1))
                              ])
                            ]),
                            _createElementVNode("tbody", null, [
                              (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(lbRows.value, (item) => {
                                return (_openBlock(), _createElementBlock("tr", {
                                  key: item.rank
                                }, [
                                  _createElementVNode("td", _hoisted_47, _toDisplayString(item.rank), 1),
                                  _createElementVNode("td", null, _toDisplayString(item.user_name), 1),
                                  _createElementVNode("td", null, _toDisplayString(item.total), 1),
                                  _createElementVNode("td", _hoisted_48, _toDisplayString(item.count), 1)
                                ]))
                              }), 128))
                            ])
                          ])
                        ])),
                (recent.value.length)
                  ? (_openBlock(), _createElementBlock("div", _hoisted_49, [
                      _createElementVNode("h3", null, [
                        _cache[33] || (_cache[33] = _createTextVNode("最近流水", -1)),
                        _createElementVNode("span", null, _toDisplayString(recent.value.length) + " 条", 1)
                      ]),
                      _createElementVNode("div", _hoisted_50, [
                        _createElementVNode("table", _hoisted_51, [
                          _cache[34] || (_cache[34] = _createElementVNode("thead", null, [
                            _createElementVNode("tr", null, [
                              _createElementVNode("th", null, "站点"),
                              _createElementVNode("th", null, "方向"),
                              _createElementVNode("th", null, "用户"),
                              _createElementVNode("th", null, "金额"),
                              _createElementVNode("th", null, "时间")
                            ])
                          ], -1)),
                          _createElementVNode("tbody", null, [
                            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(recent.value, (item, index) => {
                              return (_openBlock(), _createElementBlock("tr", { key: index }, [
                                _createElementVNode("td", _hoisted_52, _toDisplayString(item.site), 1),
                                _createElementVNode("td", null, _toDisplayString(item.direction === 'in' ? '转入' : '转出'), 1),
                                _createElementVNode("td", null, _toDisplayString(item.user_name), 1),
                                _createElementVNode("td", null, _toDisplayString(item.amount), 1),
                                _createElementVNode("td", _hoisted_53, _toDisplayString(fmtTime(item.ts)), 1)
                              ]))
                            }), 128))
                          ])
                        ])
                      ])
                    ]))
                  : _createCommentVNode("", true)
              ], 512), [
                [_vShow, tab.value === 'rank']
              ])
            ], 64))
      ])
    ]),
    _: 1
  }))
}
}

};
const Config = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-bab5d6ad"]]);

export { Config as default };
