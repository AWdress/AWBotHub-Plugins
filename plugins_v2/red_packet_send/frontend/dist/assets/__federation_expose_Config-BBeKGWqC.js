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

const {openBlock:_openBlock,createElementBlock:_createElementBlock,createCommentVNode:_createCommentVNode,createElementVNode:_createElementVNode,createTextVNode:_createTextVNode,normalizeClass:_normalizeClass,normalizeStyle:_normalizeStyle,toDisplayString:_toDisplayString,renderList:_renderList,Fragment:_Fragment,vModelCheckbox:_vModelCheckbox,withDirectives:_withDirectives,vModelText:_vModelText,vShow:_vShow,withCtx:_withCtx,createBlock:_createBlock} = await importShared('vue');


const _hoisted_1 = { class: "rp-send" };
const _hoisted_2 = {
  key: 0,
  class: "rp-send-loading",
  role: "status"
};
const _hoisted_3 = ["aria-pressed"];
const _hoisted_4 = ["aria-pressed"];
const _hoisted_5 = {
  key: 0,
  class: "rp-send-load-error",
  role: "alert"
};
const _hoisted_6 = { class: "rp-send-layout" };
const _hoisted_7 = {
  class: "rp-send-sidebar",
  "aria-label": "设置分组"
};
const _hoisted_8 = ["aria-pressed", "onClick"];
const _hoisted_9 = { class: "rp-send-detail" };
const _hoisted_10 = { class: "rp-send-group" };
const _hoisted_11 = { class: "rp-send-switch-row" };
const _hoisted_12 = { class: "rp-send-switch" };
const _hoisted_13 = { class: "rp-send-group" };
const _hoisted_14 = { class: "rp-send-row" };
const _hoisted_15 = { class: "rp-send-row" };
const _hoisted_16 = { class: "rp-send-row" };
const _hoisted_17 = { class: "rp-send-tip" };
const _hoisted_18 = { class: "rp-send-group" };
const _hoisted_19 = { class: "rp-send-switch-row" };
const _hoisted_20 = { class: "rp-send-switch" };
const _hoisted_21 = { class: "rp-send-switch-row" };
const _hoisted_22 = { class: "rp-send-switch" };
const _hoisted_23 = { class: "rp-send-row" };
const _hoisted_24 = { class: "rp-send-group" };
const _hoisted_25 = { class: "rp-send-row" };
const _hoisted_26 = { class: "rp-send-row" };
const _hoisted_27 = { class: "rp-send-row" };
const _hoisted_28 = { class: "rp-send-row" };
const _hoisted_29 = { class: "rp-send-group" };
const _hoisted_30 = { class: "rp-send-row" };
const _hoisted_31 = { class: "rp-send-row rp-send-stacked" };
const _hoisted_32 = { class: "rp-send-group" };
const _hoisted_33 = { class: "rp-send-row rp-send-stacked" };
const _hoisted_34 = { class: "rp-send-savebar" };
const _hoisted_35 = ["disabled"];
const _hoisted_36 = { class: "rp-send-pane" };
const _hoisted_37 = { class: "rp-send-toolbar" };
const _hoisted_38 = { class: "rp-send-title" };
const _hoisted_39 = { class: "rp-send-count" };
const _hoisted_40 = {
  key: 0,
  class: "rp-send-loading",
  role: "status"
};
const _hoisted_41 = {
  key: 0,
  class: "rp-send-empty"
};
const _hoisted_42 = {
  key: 1,
  class: "rp-send-table-wrap",
  tabindex: "0",
  role: "region",
  "aria-label": "进行中的红包列表"
};
const _hoisted_43 = { class: "rp-send-table" };
const _hoisted_44 = { class: "rp-send-mono" };
const _hoisted_45 = { class: "rp-send-muted" };
const _hoisted_46 = { class: "rp-send-mono" };
const _hoisted_47 = ["disabled", "onClick"];
const _hoisted_48 = {
  key: 2,
  class: "rp-send-history"
};
const _hoisted_49 = { class: "rp-send-title" };
const _hoisted_50 = { class: "rp-send-note" };
const _hoisted_51 = {
  class: "rp-send-table-wrap",
  tabindex: "0",
  role: "region",
  "aria-label": "红包历史战绩"
};
const _hoisted_52 = { class: "rp-send-table" };
const _hoisted_53 = { class: "rp-send-mono" };
const _hoisted_54 = { class: "rp-send-muted" };
const _hoisted_55 = { class: "rp-send-success" };
const _hoisted_56 = { class: "rp-send-muted" };

const {ref,reactive,onMounted} = await importShared('vue');


const _sfc_main = {
  __name: 'Config',
  props: {
  pluginId: { type: String, required: true },
  host: { type: Object, required: true },
},
  setup(__props) {

// 发红包 · 配置/管理界面（模块联邦暴露为 ./Config）。
// 平台注入 props { pluginId, host }；host: getConfig/saveConfig/callApi/toast/token。
// 两个页签：配置（左侧分组 + 右侧明细）/ 红包监控（进行中活动、可手动结束、战绩历史）。
const props = __props;

const DEFAULTS = {
  enabled: true, create_word: '创建红包', status_word: '红包状态', end_word: '结束红包',
  code_length: 4, text_mode: false, rotate_code: false,
  max_amount: 0, max_count: 0, activity_timeout_minutes: 30, end_delete_delay: 10,
  transfer_prefix: '+', congrats_text: '恭喜 {name} 抢到 {amount} 魔力！',
  blacklist_ids: '',
};

const GROUPS = [
  { key: 'main', label: '总开关' },
  { key: 'command', label: '命令' },
  { key: 'captcha', label: '口令与验证码' },
  { key: 'limit', label: '限制' },
  { key: 'send', label: '发放与文案' },
  { key: 'block', label: '屏蔽' },
];

const tab = ref('settings');
const group = ref('main');
const loading = ref(true);
const configReady = ref(false);
const loadError = ref('');
const saving = ref(false);
const cfg = reactive({ ...DEFAULTS });

// 红包监控
const activities = ref([]);
const history = ref([]);
const monLoading = ref(false);
const ending = ref('');

onMounted(loadConfig);
async function loadConfig() {
  if (saving.value) return
  loading.value = true;
  configReady.value = false;
  loadError.value = '';
  try {
    const saved = await props.host.getConfig();
    if (saved != null && (typeof saved !== 'object' || Array.isArray(saved))) throw new Error('配置格式不正确')
    Object.assign(cfg, DEFAULTS, saved || {});
    configReady.value = true;
  } catch (e) {
    loadError.value = '读取配置失败：' + (e.message || e);
    props.host.toast.error(loadError.value);
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!configReady.value || saving.value) return
  saving.value = true;
  try {
    await props.host.saveConfig({ ...cfg });
    props.host.toast.success('配置已保存');
  } catch (e) {
    props.host.toast.error('保存失败：' + (e.message || e));
  } finally {
    saving.value = false;
  }
}

// ── 监控 ──
async function loadMonitor() {
  monLoading.value = true;
  try {
    const a = await props.host.callApi('/activities');
    activities.value = a.items || [];
    const h = await props.host.callApi('/history');
    history.value = h.items || [];
  } catch (e) {
    props.host.toast.error('读取红包活动失败：' + (e.message || e));
  } finally {
    monLoading.value = false;
  }
}
async function endOne(item) {
  if (!confirm(`提前结束红包 #${item.rp_id}？剩余 ${item.remaining_count} 个未抢的将不再发放。`)) return
  ending.value = item.key;
  try {
    const r = await props.host.callApi('/end', { method: 'POST', body: { key: item.key } });
    if (r.ok) { props.host.toast.success(r.message || '已结束'); await loadMonitor(); }
    else props.host.toast.error(r.message || '结束失败');
  } catch (e) { props.host.toast.error('结束失败：' + (e.message || e)); }
  finally { ending.value = ''; }
}

function switchTab(t) {
  tab.value = t;
  if (t === 'monitor') loadMonitor();
}

return (_ctx, _cache) => {
  return (_openBlock(), _createBlock(IosSettings, null, {
    default: _withCtx(() => [
      _createElementVNode("div", _hoisted_1, [
        (loading.value)
          ? (_openBlock(), _createElementBlock("div", _hoisted_2, "加载配置…"))
          : (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
              _createElementVNode("div", {
                class: "rp-send-tabs",
                style: _normalizeStyle({ '--rp-send-tab-index': tab.value === 'settings' ? 0 : 1 }),
                "aria-label": "发红包页面"
              }, [
                _createElementVNode("button", {
                  type: "button",
                  class: _normalizeClass(['rp-send-tab', { on: tab.value === 'settings' }]),
                  "aria-pressed": tab.value === 'settings',
                  onClick: _cache[0] || (_cache[0] = $event => (switchTab('settings')))
                }, [...(_cache[16] || (_cache[16] = [
                  _createElementVNode("svg", {
                    viewBox: "0 0 24 24",
                    "aria-hidden": "true"
                  }, [
                    _createElementVNode("path", { d: "M4 7h9m4 0h3M4 17h3m4 0h9" }),
                    _createElementVNode("circle", {
                      cx: "15",
                      cy: "7",
                      r: "2"
                    }),
                    _createElementVNode("circle", {
                      cx: "9",
                      cy: "17",
                      r: "2"
                    })
                  ], -1),
                  _createTextVNode("功能设置", -1)
                ]))], 10, _hoisted_3),
                _createElementVNode("button", {
                  type: "button",
                  class: _normalizeClass(['rp-send-tab', { on: tab.value === 'monitor' }]),
                  "aria-pressed": tab.value === 'monitor',
                  onClick: _cache[1] || (_cache[1] = $event => (switchTab('monitor')))
                }, [...(_cache[17] || (_cache[17] = [
                  _createElementVNode("svg", {
                    viewBox: "0 0 24 24",
                    "aria-hidden": "true"
                  }, [
                    _createElementVNode("path", { d: "M4 5h16v12H4zM8 21h8m-4-4v4M7 12l3-3 3 3 4-5" })
                  ], -1),
                  _createTextVNode("红包监控", -1)
                ]))], 10, _hoisted_4)
              ], 4),
              (loadError.value)
                ? (_openBlock(), _createElementBlock("div", _hoisted_5, [
                    _createElementVNode("p", null, _toDisplayString(loadError.value) + "。请重新读取，成功前不能保存，以免覆盖原设置。", 1),
                    _createElementVNode("button", {
                      type: "button",
                      class: "rp-send-button",
                      onClick: loadConfig
                    }, "重新读取配置")
                  ]))
                : _createCommentVNode("", true),
              _withDirectives(_createElementVNode("div", _hoisted_6, [
                _createElementVNode("aside", _hoisted_7, [
                  (_openBlock(), _createElementBlock(_Fragment, null, _renderList(GROUPS, (g) => {
                    return _createElementVNode("button", {
                      key: g.key,
                      type: "button",
                      class: _normalizeClass(['rp-send-side-item', { on: group.value === g.key }]),
                      "aria-pressed": group.value === g.key,
                      onClick: $event => (group.value = g.key)
                    }, [
                      _createElementVNode("span", null, _toDisplayString(g.label), 1),
                      _cache[18] || (_cache[18] = _createElementVNode("svg", {
                        viewBox: "0 0 24 24",
                        "aria-hidden": "true"
                      }, [
                        _createElementVNode("path", { d: "m9 5 7 7-7 7" })
                      ], -1))
                    ], 10, _hoisted_8)
                  }), 64))
                ]),
                _createElementVNode("div", _hoisted_9, [
                  (group.value === 'main')
                    ? (_openBlock(), _createElementBlock(_Fragment, { key: 0 }, [
                        _cache[21] || (_cache[21] = _createElementVNode("h3", { class: "rp-send-title" }, "总开关", -1)),
                        _createElementVNode("section", _hoisted_10, [
                          _createElementVNode("label", _hoisted_11, [
                            _cache[20] || (_cache[20] = _createElementVNode("span", { class: "rp-send-label" }, [
                              _createTextVNode("启用发红包"),
                              _createElementVNode("span", { class: "rp-send-note" }, "关闭后不响应发红包命令")
                            ], -1)),
                            _createElementVNode("span", _hoisted_12, [
                              _withDirectives(_createElementVNode("input", {
                                "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((cfg.enabled) = $event)),
                                type: "checkbox",
                                role: "switch"
                              }, null, 512), [
                                [_vModelCheckbox, cfg.enabled]
                              ]),
                              _cache[19] || (_cache[19] = _createElementVNode("span", {
                                class: "rp-send-switch-track",
                                "aria-hidden": "true"
                              }, null, -1))
                            ])
                          ])
                        ])
                      ], 64))
                    : (group.value === 'command')
                      ? (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
                          _cache[27] || (_cache[27] = _createElementVNode("h3", { class: "rp-send-title" }, "命令词", -1)),
                          _createElementVNode("section", _hoisted_13, [
                            _createElementVNode("label", _hoisted_14, [
                              _cache[22] || (_cache[22] = _createElementVNode("span", { class: "rp-send-label" }, "创建命令词", -1)),
                              _withDirectives(_createElementVNode("input", {
                                "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((cfg.create_word) = $event)),
                                class: "rp-send-input",
                                placeholder: "默认：创建红包"
                              }, null, 512), [
                                [_vModelText, cfg.create_word]
                              ])
                            ]),
                            _createElementVNode("label", _hoisted_15, [
                              _cache[23] || (_cache[23] = _createElementVNode("span", { class: "rp-send-label" }, "查看状态词", -1)),
                              _withDirectives(_createElementVNode("input", {
                                "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((cfg.status_word) = $event)),
                                class: "rp-send-input",
                                placeholder: "默认：红包状态"
                              }, null, 512), [
                                [_vModelText, cfg.status_word]
                              ])
                            ]),
                            _createElementVNode("label", _hoisted_16, [
                              _cache[24] || (_cache[24] = _createElementVNode("span", { class: "rp-send-label" }, "结束命令词", -1)),
                              _withDirectives(_createElementVNode("input", {
                                "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((cfg.end_word) = $event)),
                                class: "rp-send-input",
                                placeholder: "默认：结束红包"
                              }, null, 512), [
                                [_vModelText, cfg.end_word]
                              ])
                            ])
                          ]),
                          _createElementVNode("p", _hoisted_17, [
                            _cache[25] || (_cache[25] = _createTextVNode("格式：", -1)),
                            _createElementVNode("code", null, _toDisplayString(cfg.create_word) + " 总额 个数 [自定义口令]", 1),
                            _cache[26] || (_cache[26] = _createTextVNode("。自定义口令后会加上随机验证码，按“口令与验证码”设置显示图片或可复制文字。创建命令发送后会自动删除。", -1))
                          ])
                        ], 64))
                      : (group.value === 'captcha')
                        ? (_openBlock(), _createElementBlock(_Fragment, { key: 2 }, [
                            _cache[33] || (_cache[33] = _createElementVNode("h3", { class: "rp-send-title" }, "口令与验证码", -1)),
                            _createElementVNode("section", _hoisted_18, [
                              _createElementVNode("label", _hoisted_19, [
                                _cache[29] || (_cache[29] = _createElementVNode("span", { class: "rp-send-label" }, [
                                  _createTextVNode("文字口令（不用图片）"),
                                  _createElementVNode("span", {
                                    id: "text-mode-help",
                                    class: "rp-send-note"
                                  }, "默认关闭，使用验证码图片。开启后直接公布完整口令，点击或长按口令复制，再发到群里参与；文字模式不防复制脚本。")
                                ], -1)),
                                _createElementVNode("span", _hoisted_20, [
                                  _withDirectives(_createElementVNode("input", {
                                    "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((cfg.text_mode) = $event)),
                                    type: "checkbox",
                                    role: "switch",
                                    "aria-describedby": "text-mode-help"
                                  }, null, 512), [
                                    [_vModelCheckbox, cfg.text_mode]
                                  ]),
                                  _cache[28] || (_cache[28] = _createElementVNode("span", {
                                    class: "rp-send-switch-track",
                                    "aria-hidden": "true"
                                  }, null, -1))
                                ])
                              ]),
                              _createElementVNode("label", _hoisted_21, [
                                _cache[31] || (_cache[31] = _createElementVNode("span", { class: "rp-send-label" }, [
                                  _createTextVNode("口令一次性有效"),
                                  _createElementVNode("span", {
                                    id: "rotate-code-help",
                                    class: "rp-send-note"
                                  }, "默认关闭，同一口令可供多人领取。开启后，每领取一份就换新口令，旧口令立即失效；图片、文字模式都适用。无论是否开启，每人都只能领一次。")
                                ], -1)),
                                _createElementVNode("span", _hoisted_22, [
                                  _withDirectives(_createElementVNode("input", {
                                    "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => ((cfg.rotate_code) = $event)),
                                    type: "checkbox",
                                    role: "switch",
                                    "aria-describedby": "rotate-code-help"
                                  }, null, 512), [
                                    [_vModelCheckbox, cfg.rotate_code]
                                  ]),
                                  _cache[30] || (_cache[30] = _createElementVNode("span", {
                                    class: "rp-send-switch-track",
                                    "aria-hidden": "true"
                                  }, null, -1))
                                ])
                              ]),
                              _createElementVNode("label", _hoisted_23, [
                                _cache[32] || (_cache[32] = _createElementVNode("span", { class: "rp-send-label" }, [
                                  _createTextVNode("验证码位数"),
                                  _createElementVNode("span", { class: "rp-send-note" }, "4–8 位，默认 4 位，不区分大小写")
                                ], -1)),
                                _withDirectives(_createElementVNode("input", {
                                  "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => ((cfg.code_length) = $event)),
                                  class: "rp-send-input rp-send-small",
                                  type: "number",
                                  min: "4",
                                  max: "8"
                                }, null, 512), [
                                  [
                                    _vModelText,
                                    cfg.code_length,
                                    void 0,
                                    { number: true }
                                  ]
                                ])
                              ])
                            ]),
                            _cache[34] || (_cache[34] = _createElementVNode("p", { class: "rp-send-tip rp-send-warning" }, "请在当前红包结束后保存。保存会重载插件，新设置用于之后创建的红包。", -1))
                          ], 64))
                        : (group.value === 'limit')
                          ? (_openBlock(), _createElementBlock(_Fragment, { key: 3 }, [
                              _cache[39] || (_cache[39] = _createElementVNode("h3", { class: "rp-send-title" }, "限制", -1)),
                              _createElementVNode("section", _hoisted_24, [
                                _createElementVNode("label", _hoisted_25, [
                                  _cache[35] || (_cache[35] = _createElementVNode("span", { class: "rp-send-label" }, [
                                    _createTextVNode("总额上限"),
                                    _createElementVNode("span", { class: "rp-send-note" }, "单位：魔力，0 表示不限")
                                  ], -1)),
                                  _withDirectives(_createElementVNode("input", {
                                    "onUpdate:modelValue": _cache[9] || (_cache[9] = $event => ((cfg.max_amount) = $event)),
                                    class: "rp-send-input rp-send-small",
                                    type: "number",
                                    min: "0"
                                  }, null, 512), [
                                    [
                                      _vModelText,
                                      cfg.max_amount,
                                      void 0,
                                      { number: true }
                                    ]
                                  ])
                                ]),
                                _createElementVNode("label", _hoisted_26, [
                                  _cache[36] || (_cache[36] = _createElementVNode("span", { class: "rp-send-label" }, [
                                    _createTextVNode("个数上限"),
                                    _createElementVNode("span", { class: "rp-send-note" }, "0 表示不限")
                                  ], -1)),
                                  _withDirectives(_createElementVNode("input", {
                                    "onUpdate:modelValue": _cache[10] || (_cache[10] = $event => ((cfg.max_count) = $event)),
                                    class: "rp-send-input rp-send-small",
                                    type: "number",
                                    min: "0"
                                  }, null, 512), [
                                    [
                                      _vModelText,
                                      cfg.max_count,
                                      void 0,
                                      { number: true }
                                    ]
                                  ])
                                ]),
                                _createElementVNode("label", _hoisted_27, [
                                  _cache[37] || (_cache[37] = _createElementVNode("span", { class: "rp-send-label" }, [
                                    _createTextVNode("活动超时"),
                                    _createElementVNode("span", { class: "rp-send-note" }, "单位：分钟，无人抢完则自动结算")
                                  ], -1)),
                                  _withDirectives(_createElementVNode("input", {
                                    "onUpdate:modelValue": _cache[11] || (_cache[11] = $event => ((cfg.activity_timeout_minutes) = $event)),
                                    class: "rp-send-input rp-send-small",
                                    type: "number",
                                    min: "1",
                                    max: "240"
                                  }, null, 512), [
                                    [
                                      _vModelText,
                                      cfg.activity_timeout_minutes,
                                      void 0,
                                      { number: true }
                                    ]
                                  ])
                                ]),
                                _createElementVNode("label", _hoisted_28, [
                                  _cache[38] || (_cache[38] = _createElementVNode("span", { class: "rp-send-label" }, [
                                    _createTextVNode("结束后删消息"),
                                    _createElementVNode("span", { class: "rp-send-note" }, "单位：秒，0 表示不删")
                                  ], -1)),
                                  _withDirectives(_createElementVNode("input", {
                                    "onUpdate:modelValue": _cache[12] || (_cache[12] = $event => ((cfg.end_delete_delay) = $event)),
                                    class: "rp-send-input rp-send-small",
                                    type: "number",
                                    min: "0",
                                    max: "600"
                                  }, null, 512), [
                                    [
                                      _vModelText,
                                      cfg.end_delete_delay,
                                      void 0,
                                      { number: true }
                                    ]
                                  ])
                                ])
                              ])
                            ], 64))
                          : (group.value === 'send')
                            ? (_openBlock(), _createElementBlock(_Fragment, { key: 4 }, [
                                _cache[42] || (_cache[42] = _createElementVNode("h3", { class: "rp-send-title" }, "发放与文案", -1)),
                                _createElementVNode("section", _hoisted_29, [
                                  _createElementVNode("label", _hoisted_30, [
                                    _cache[40] || (_cache[40] = _createElementVNode("span", { class: "rp-send-label" }, [
                                      _createTextVNode("转账金额前缀"),
                                      _createElementVNode("span", { class: "rp-send-note" }, "群转账 Bot 据此打款，默认 +")
                                    ], -1)),
                                    _withDirectives(_createElementVNode("input", {
                                      "onUpdate:modelValue": _cache[13] || (_cache[13] = $event => ((cfg.transfer_prefix) = $event)),
                                      class: "rp-send-input rp-send-small"
                                    }, null, 512), [
                                      [_vModelText, cfg.transfer_prefix]
                                    ])
                                  ]),
                                  _createElementVNode("label", _hoisted_31, [
                                    _cache[41] || (_cache[41] = _createElementVNode("span", { class: "rp-send-label" }, [
                                      _createTextVNode("祝贺文案"),
                                      _createElementVNode("span", { class: "rp-send-note" }, "可用 {name}、{amount}、{id} 占位")
                                    ], -1)),
                                    _withDirectives(_createElementVNode("textarea", {
                                      "onUpdate:modelValue": _cache[14] || (_cache[14] = $event => ((cfg.congrats_text) = $event)),
                                      class: "rp-send-input",
                                      rows: "3",
                                      placeholder: "可用 {name} {amount} {id} 占位"
                                    }, null, 512), [
                                      [_vModelText, cfg.congrats_text]
                                    ])
                                  ])
                                ])
                              ], 64))
                            : (group.value === 'block')
                              ? (_openBlock(), _createElementBlock(_Fragment, { key: 5 }, [
                                  _cache[44] || (_cache[44] = _createElementVNode("h3", { class: "rp-send-title" }, "屏蔽", -1)),
                                  _createElementVNode("section", _hoisted_32, [
                                    _createElementVNode("label", _hoisted_33, [
                                      _cache[43] || (_cache[43] = _createElementVNode("span", { class: "rp-send-label" }, [
                                        _createTextVNode("屏蔽用户 ID"),
                                        _createElementVNode("span", { class: "rp-send-note" }, "一行一个或用逗号分隔；这些用户不计入参与，也不发放红包。")
                                      ], -1)),
                                      _withDirectives(_createElementVNode("textarea", {
                                        "onUpdate:modelValue": _cache[15] || (_cache[15] = $event => ((cfg.blacklist_ids) = $event)),
                                        class: "rp-send-input",
                                        rows: "4",
                                        placeholder: "一行一个或逗号分隔的用户ID，这些用户参与不计入、不发放"
                                      }, null, 512), [
                                        [_vModelText, cfg.blacklist_ids]
                                      ])
                                    ])
                                  ])
                                ], 64))
                              : _createCommentVNode("", true),
                  _createElementVNode("div", _hoisted_34, [
                    _createElementVNode("button", {
                      type: "button",
                      class: "rp-send-button rp-send-primary",
                      disabled: saving.value || !configReady.value,
                      onClick: save
                    }, _toDisplayString(saving.value ? '保存中…' : '保存配置'), 9, _hoisted_35)
                  ])
                ])
              ], 512), [
                [_vShow, tab.value === 'settings']
              ]),
              _withDirectives(_createElementVNode("div", _hoisted_36, [
                _createElementVNode("div", _hoisted_37, [
                  _createElementVNode("h3", _hoisted_38, [
                    _cache[45] || (_cache[45] = _createTextVNode("进行中的红包 ", -1)),
                    _createElementVNode("span", _hoisted_39, _toDisplayString(activities.value.length), 1)
                  ]),
                  _createElementVNode("button", {
                    type: "button",
                    class: "rp-send-button",
                    onClick: loadMonitor
                  }, [...(_cache[46] || (_cache[46] = [
                    _createElementVNode("svg", {
                      viewBox: "0 0 24 24",
                      "aria-hidden": "true"
                    }, [
                      _createElementVNode("path", { d: "M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 11.5-2L20 8M4 16l2.5 3A7 7 0 0 0 18 17" })
                    ], -1),
                    _createTextVNode("刷新", -1)
                  ]))])
                ]),
                (monLoading.value)
                  ? (_openBlock(), _createElementBlock("div", _hoisted_40, "加载中…"))
                  : (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
                      (!activities.value.length)
                        ? (_openBlock(), _createElementBlock("div", _hoisted_41, [...(_cache[47] || (_cache[47] = [
                            _createElementVNode("svg", {
                              viewBox: "0 0 24 24",
                              "aria-hidden": "true"
                            }, [
                              _createElementVNode("path", { d: "M4 8h16v13H4zM3 4h18v4H3zM12 4v17M12 4C6-2 3 3 7 4m5 0c6-6 9-1 5 0" })
                            ], -1),
                            _createElementVNode("h3", null, "当前没有进行中的红包", -1),
                            _createElementVNode("p", null, "在群里用创建命令词发红包后会显示在这里", -1)
                          ]))]))
                        : (_openBlock(), _createElementBlock("div", _hoisted_42, [
                            _createElementVNode("table", _hoisted_43, [
                              _cache[48] || (_cache[48] = _createElementVNode("thead", null, [
                                _createElementVNode("tr", null, [
                                  _createElementVNode("th", null, "编号"),
                                  _createElementVNode("th", null, "群"),
                                  _createElementVNode("th", null, "总额"),
                                  _createElementVNode("th", null, "进度"),
                                  _createElementVNode("th", null, "剩余金额"),
                                  _createElementVNode("th", null, "已参与"),
                                  _createElementVNode("th", null, "口令"),
                                  _createElementVNode("th")
                                ])
                              ], -1)),
                              _createElementVNode("tbody", null, [
                                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(activities.value, (a) => {
                                  return (_openBlock(), _createElementBlock("tr", {
                                    key: a.key
                                  }, [
                                    _createElementVNode("td", _hoisted_44, "#" + _toDisplayString(a.rp_id), 1),
                                    _createElementVNode("td", null, _toDisplayString(a.chat_title || a.chat_id), 1),
                                    _createElementVNode("td", null, _toDisplayString(a.total_amount), 1),
                                    _createElementVNode("td", null, _toDisplayString(a.packet_count - a.remaining_count) + "/" + _toDisplayString(a.packet_count), 1),
                                    _createElementVNode("td", _hoisted_45, _toDisplayString(a.remaining_amount), 1),
                                    _createElementVNode("td", null, _toDisplayString(a.participants), 1),
                                    _createElementVNode("td", _hoisted_46, _toDisplayString(a.keyword), 1),
                                    _createElementVNode("td", null, [
                                      _createElementVNode("button", {
                                        type: "button",
                                        class: "rp-send-button rp-send-danger",
                                        disabled: ending.value,
                                        onClick: $event => (endOne(a))
                                      }, _toDisplayString(ending.value === a.key ? '结束中…' : '结束'), 9, _hoisted_47)
                                    ])
                                  ]))
                                }), 128))
                              ])
                            ])
                          ])),
                      (history.value.length)
                        ? (_openBlock(), _createElementBlock("div", _hoisted_48, [
                            _createElementVNode("h3", _hoisted_49, [
                              _cache[49] || (_cache[49] = _createTextVNode("红包战绩 ", -1)),
                              _createElementVNode("span", _hoisted_50, "最近 " + _toDisplayString(history.value.length) + " 条", 1)
                            ]),
                            _createElementVNode("div", _hoisted_51, [
                              _createElementVNode("table", _hoisted_52, [
                                _cache[50] || (_cache[50] = _createElementVNode("thead", null, [
                                  _createElementVNode("tr", null, [
                                    _createElementVNode("th", null, "编号"),
                                    _createElementVNode("th", null, "群"),
                                    _createElementVNode("th", null, "总额"),
                                    _createElementVNode("th", null, "个数"),
                                    _createElementVNode("th", null, "参与"),
                                    _createElementVNode("th", null, "发放"),
                                    _createElementVNode("th", null, "时间")
                                  ])
                                ], -1)),
                                _createElementVNode("tbody", null, [
                                  (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(history.value, (h, i) => {
                                    return (_openBlock(), _createElementBlock("tr", { key: i }, [
                                      _createElementVNode("td", _hoisted_53, "#" + _toDisplayString(h.rp_id), 1),
                                      _createElementVNode("td", null, [
                                        _createTextVNode(_toDisplayString(h.chat_title || h.chat_id) + " ", 1),
                                        _createElementVNode("span", _hoisted_54, "(" + _toDisplayString(h.chat_id) + ")", 1)
                                      ]),
                                      _createElementVNode("td", null, _toDisplayString(h.total_amount), 1),
                                      _createElementVNode("td", null, _toDisplayString(h.packet_count), 1),
                                      _createElementVNode("td", null, _toDisplayString(h.participants), 1),
                                      _createElementVNode("td", _hoisted_55, _toDisplayString(h.distributed), 1),
                                      _createElementVNode("td", _hoisted_56, _toDisplayString(h.time || '—'), 1)
                                    ]))
                                  }), 128))
                                ])
                              ])
                            ])
                          ]))
                        : _createCommentVNode("", true)
                    ], 64))
              ], 512), [
                [_vShow, tab.value === 'monitor']
              ])
            ], 64))
      ])
    ]),
    _: 1
  }))
}
}

};
const Config = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-923f93ad"]]);

export { Config as default };
