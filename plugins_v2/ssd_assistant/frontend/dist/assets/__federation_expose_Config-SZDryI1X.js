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

const {createElementVNode:_createElementVNode,openBlock:_openBlock,createElementBlock:_createElementBlock,createTextVNode:_createTextVNode,normalizeClass:_normalizeClass,normalizeStyle:_normalizeStyle,createCommentVNode:_createCommentVNode,toDisplayString:_toDisplayString,vModelCheckbox:_vModelCheckbox,withDirectives:_withDirectives,vModelText:_vModelText,renderList:_renderList,Fragment:_Fragment,vModelSelect:_vModelSelect,withModifiers:_withModifiers,withCtx:_withCtx,createBlock:_createBlock} = await importShared('vue');


const _hoisted_1 = { class: "ssd" };
const _hoisted_2 = ["aria-pressed"];
const _hoisted_3 = ["aria-pressed"];
const _hoisted_4 = {
  key: 0,
  class: "ssd-settings"
};
const _hoisted_5 = {
  key: 0,
  class: "ssd-loading",
  role: "status"
};
const _hoisted_6 = {
  key: 1,
  class: "ssd-error-box",
  role: "alert"
};
const _hoisted_7 = ["disabled"];
const _hoisted_8 = {
  class: "ssd-section",
  "aria-labelledby": "ssd-lottery-title"
};
const _hoisted_9 = { class: "ssd-section-head" };
const _hoisted_10 = { class: "ssd-lottery-toggle" };
const _hoisted_11 = { class: "ssd-lottery-toggle-state" };
const _hoisted_12 = {
  class: "ssd-field ssd-range-field",
  role: "group",
  "aria-labelledby": "ssd-lottery-delay-label"
};
const _hoisted_13 = { class: "ssd-number-field" };
const _hoisted_14 = {
  class: "ssd-section",
  "aria-labelledby": "ssd-transfer-title"
};
const _hoisted_15 = { class: "ssd-section-head" };
const _hoisted_16 = {
  class: "ssd-field",
  for: "ssd-transfer-mode"
};
const _hoisted_17 = ["value"];
const _hoisted_18 = {
  class: "ssd-field",
  for: "ssd-confirm-delay"
};
const _hoisted_19 = { class: "ssd-number-field" };
const _hoisted_20 = {
  key: 0,
  class: "ssd-warning",
  role: "note"
};
const _hoisted_21 = { class: "ssd-savebar" };
const _hoisted_22 = {
  key: 0,
  class: "ssd-error",
  role: "alert"
};
const _hoisted_23 = {
  key: 1,
  class: "ssd-save-result",
  role: "status"
};
const _hoisted_24 = ["disabled"];
const _hoisted_25 = {
  key: 1,
  class: "ssd-history-pane"
};
const _hoisted_26 = { class: "ssd-toolbar" };
const _hoisted_27 = {
  class: "ssd-filter",
  for: "ssd-history-filter"
};
const _hoisted_28 = ["disabled"];
const _hoisted_29 = { class: "ssd-history-notes" };
const _hoisted_30 = {
  key: 0,
  class: "ssd-tip"
};
const _hoisted_31 = {
  key: 0,
  class: "ssd-loading",
  role: "status"
};
const _hoisted_32 = {
  key: 1,
  class: "ssd-error-box",
  role: "alert"
};
const _hoisted_33 = {
  key: 2,
  class: "ssd-empty"
};
const _hoisted_34 = {
  key: 3,
  class: "ssd-records"
};
const _hoisted_35 = { class: "ssd-record-head" };
const _hoisted_36 = {
  key: 0,
  class: "ssd-lottery-id"
};
const _hoisted_37 = { class: "ssd-record-detail" };
const _hoisted_38 = { class: "ssd-record-meta" };

const {computed,onMounted,reactive,ref,watch} = await importShared('vue');


const _sfc_main = {
  __name: 'Config',
  props: {
  pluginId: { type: String, required: true },
  host: { type: Object, required: true },
},
  setup(__props) {

const props = __props;
const DEFAULTS = {
  lottery_enabled: false,
  lottery_delay_min_seconds: 2,
  lottery_delay_max_seconds: 5,
  ssd_click_mode: 'off',
  confirm_delay_seconds: 0.5,
};
const MODES = [
  { value: 'off', label: '关闭（默认）' },
  { value: 'once', label: '单次确认' },
  { value: '5min', label: '5 分钟免确认' },
];
const cfg = reactive({ ...DEFAULTS });
const tab = ref('settings');
const loading = ref(true);
const ready = ref(false);
const saving = ref(false);
const loadError = ref('');
const saveResult = ref('');
watch(cfg, () => { saveResult.value = ''; }, { deep: true, flush: 'sync' });
const historyLoading = ref(false);
const historyLoaded = ref(false);
const historyError = ref('');
const history = ref([]);
const historyFilter = ref('all');
const runtime = ref(null);
const visibleHistory = computed(() => history.value.filter(item => historyFilter.value === 'all' || item.kind === historyFilter.value));
const formError = computed(() => {
  const lotteryMin = Number(cfg.lottery_delay_min_seconds);
  const lotteryMax = Number(cfg.lottery_delay_max_seconds);
  const confirm = Number(cfg.confirm_delay_seconds);
  if ([cfg.lottery_delay_min_seconds, cfg.lottery_delay_max_seconds].some(value => value == null || String(value).trim() === '' || !Number.isFinite(Number(value)) || Number(value) < 0 || Number(value) > 60)) return '最短和最长等待请填写 0～60 秒。'
  if (lotteryMin > lotteryMax) return '最短等待不能大于最长等待。'
  if (cfg.confirm_delay_seconds === '' || !Number.isFinite(confirm) || confirm < 0 || confirm > 10) return '确认等待时间请填写 0～10 秒。'
  if (!MODES.some(item => item.value === cfg.ssd_click_mode)) return '请选择有效的自动确认方式。'
  return ''
});
function errorText(error) { return String(error?.message || error || '未知错误') }
function asBoolean(value) { return value === true || value === 1 || typeof value === 'string' && value.trim().toLowerCase() === 'true' }

async function loadConfig() {
  if (saving.value) return
  loading.value = true;
  ready.value = false;
  loadError.value = '';
  try {
    const saved = await props.host.getConfig();
    if (saved != null && (typeof saved !== 'object' || Array.isArray(saved))) throw new Error('配置格式不正确')
    Object.assign(cfg, DEFAULTS, saved || {});
    if (saved && Object.hasOwn(saved, 'lottery_delay_seconds') && !Object.hasOwn(saved, 'lottery_delay_min_seconds') && !Object.hasOwn(saved, 'lottery_delay_max_seconds')) {
      cfg.lottery_delay_min_seconds = saved.lottery_delay_seconds;
      cfg.lottery_delay_max_seconds = saved.lottery_delay_seconds;
    }
    delete cfg.lottery_delay_seconds;
    cfg.lottery_enabled = asBoolean(cfg.lottery_enabled);
    ready.value = true;
  } catch (error) {
    loadError.value = '读取配置失败：' + errorText(error);
    props.host.toast.error(loadError.value);
  } finally { loading.value = false; }
}
async function save() {
  if (!ready.value || saving.value) return
  saveResult.value = '';
  if (formError.value) { props.host.toast.error(formError.value); return }
  saving.value = true;
  try {
    const values = {
      lottery_enabled: cfg.lottery_enabled,
      lottery_delay_min_seconds: Number(cfg.lottery_delay_min_seconds),
      lottery_delay_max_seconds: Number(cfg.lottery_delay_max_seconds),
      ssd_click_mode: cfg.ssd_click_mode,
      confirm_delay_seconds: Number(cfg.confirm_delay_seconds),
    };
    await props.host.saveConfig(values);
    saveResult.value = '配置已保存';
    props.host.toast.success(saveResult.value);
  } catch (error) {
    saveResult.value = '保存失败：' + errorText(error);
    props.host.toast.error(saveResult.value);
  } finally { saving.value = false; }
}
async function loadHistory() {
  if (historyLoading.value) return
  historyLoading.value = true;
  historyError.value = '';
  try {
    const result = await props.host.callApi('/history');
    if (!Array.isArray(result?.items)) throw new Error('记录格式不正确')
    history.value = result.items.slice(0, 100);
    historyLoaded.value = true;
    try { runtime.value = await props.host.callApi('/status'); } catch { runtime.value = null; }
  } catch (error) {
    historyError.value = '读取记录失败：' + errorText(error) + '。请点击“刷新记录”重试。';
    props.host.toast.error(historyError.value);
  } finally { historyLoading.value = false; }
}
function switchTab(value) {
  tab.value = value;
  if (value === 'history' && !historyLoaded.value) loadHistory();
}
function statusText(item) {
  const names = { prepared: '已登记，待核对', sent: '口令已发送', clicked: '确认已点击', uncertain: '结果待核对', failed: '执行失败', skipped: '已跳过' };
  return names[item.status] || String(item.status || '未知状态')
}
function formatTime(value) {
  if (!value) return '时间未知'
  const date = typeof value === 'number' ? new Date(value < 1e12 ? value * 1000 : value) : new Date(value);
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('zh-CN', { hour12: false })
}
onMounted(loadConfig);

return (_ctx, _cache) => {
  return (_openBlock(), _createBlock(IosSettings, null, {
    default: _withCtx(() => [
      _createElementVNode("div", _hoisted_1, [
        _createElementVNode("div", {
          class: "ssd-tabs",
          style: _normalizeStyle({ '--ssd-tab-index': tab.value === 'settings' ? 0 : 1 }),
          "aria-label": "SSD 助手页面"
        }, [
          _createElementVNode("button", {
            type: "button",
            class: _normalizeClass(['ssd-tab', { on: tab.value === 'settings' }]),
            "aria-pressed": tab.value === 'settings',
            onClick: _cache[0] || (_cache[0] = $event => (switchTab('settings')))
          }, [...(_cache[8] || (_cache[8] = [
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
          ]))], 10, _hoisted_2),
          _createElementVNode("button", {
            type: "button",
            class: _normalizeClass(['ssd-tab', { on: tab.value === 'history' }]),
            "aria-pressed": tab.value === 'history',
            onClick: _cache[1] || (_cache[1] = $event => (switchTab('history')))
          }, [...(_cache[9] || (_cache[9] = [
            _createElementVNode("svg", {
              viewBox: "0 0 24 24",
              "aria-hidden": "true"
            }, [
              _createElementVNode("path", { d: "M5 5h14v15H5zM9 3v4m6-4v4M9 11h6m-6 4h4" })
            ], -1),
            _createTextVNode("执行记录", -1)
          ]))], 10, _hoisted_3)
        ], 4),
        (tab.value === 'settings')
          ? (_openBlock(), _createElementBlock("div", _hoisted_4, [
              (loading.value)
                ? (_openBlock(), _createElementBlock("p", _hoisted_5, "正在读取配置…"))
                : (loadError.value)
                  ? (_openBlock(), _createElementBlock("div", _hoisted_6, [
                      _createElementVNode("p", null, _toDisplayString(loadError.value) + "。为保护原设置，读取成功前不能保存。", 1),
                      _createElementVNode("button", {
                        type: "button",
                        class: "ssd-button",
                        onClick: loadConfig
                      }, "重新读取配置")
                    ]))
                  : (_openBlock(), _createElementBlock("form", {
                      key: 2,
                      onSubmit: _withModifiers(save, ["prevent"])
                    }, [
                      _createElementVNode("fieldset", {
                        disabled: !ready.value || saving.value
                      }, [
                        _createElementVNode("section", _hoisted_8, [
                          _createElementVNode("div", _hoisted_9, [
                            _cache[11] || (_cache[11] = _createElementVNode("div", null, [
                              _createElementVNode("h3", { id: "ssd-lottery-title" }, "自动参与抽奖"),
                              _createElementVNode("p", {
                                id: "ssd-lottery-help",
                                class: "ssd-tip"
                              }, "发送一次参与口令，发完即结束。")
                            ], -1)),
                            _createElementVNode("label", _hoisted_10, [
                              _withDirectives(_createElementVNode("input", {
                                "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((cfg.lottery_enabled) = $event)),
                                class: "ssd-lottery-toggle-input",
                                type: "checkbox",
                                role: "switch",
                                "aria-label": "开启自动参与抽奖"
                              }, null, 512), [
                                [_vModelCheckbox, cfg.lottery_enabled]
                              ]),
                              _cache[10] || (_cache[10] = _createElementVNode("span", {
                                class: "ssd-lottery-toggle-track",
                                "aria-hidden": "true"
                              }, null, -1)),
                              _createElementVNode("span", _hoisted_11, _toDisplayString(cfg.lottery_enabled ? '开启' : '关闭'), 1)
                            ])
                          ]),
                          _createElementVNode("div", _hoisted_12, [
                            _cache[14] || (_cache[14] = _createElementVNode("div", { class: "ssd-field-label" }, [
                              _createElementVNode("span", { id: "ssd-lottery-delay-label" }, "参与前随机等待"),
                              _createElementVNode("span", { class: "ssd-field-note" }, "默认 2～5 秒，最多 60 秒")
                            ], -1)),
                            _createElementVNode("span", _hoisted_13, [
                              _withDirectives(_createElementVNode("input", {
                                "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((cfg.lottery_delay_min_seconds) = $event)),
                                type: "number",
                                min: "0",
                                max: "60",
                                step: "0.1",
                                "aria-label": "最短等待",
                                "aria-describedby": "ssd-lottery-help"
                              }, null, 512), [
                                [
                                  _vModelText,
                                  cfg.lottery_delay_min_seconds,
                                  void 0,
                                  { number: true }
                                ]
                              ]),
                              _cache[12] || (_cache[12] = _createElementVNode("span", null, "～", -1)),
                              _withDirectives(_createElementVNode("input", {
                                "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((cfg.lottery_delay_max_seconds) = $event)),
                                type: "number",
                                min: "0",
                                max: "60",
                                step: "0.1",
                                "aria-label": "最长等待",
                                "aria-describedby": "ssd-lottery-help"
                              }, null, 512), [
                                [
                                  _vModelText,
                                  cfg.lottery_delay_max_seconds,
                                  void 0,
                                  { number: true }
                                ]
                              ]),
                              _cache[13] || (_cache[13] = _createElementVNode("span", null, "秒", -1))
                            ])
                          ])
                        ]),
                        _createElementVNode("section", _hoisted_14, [
                          _createElementVNode("div", _hoisted_15, [
                            _cache[15] || (_cache[15] = _createElementVNode("div", null, [
                              _createElementVNode("h3", { id: "ssd-transfer-title" }, "自动确认转账"),
                              _createElementVNode("p", {
                                id: "ssd-transfer-help",
                                class: "ssd-tip"
                              }, "只确认本人转账，不发起转账。")
                            ], -1)),
                            _createElementVNode("span", {
                              class: _normalizeClass(["ssd-mode-state", { on: cfg.ssd_click_mode !== 'off' }])
                            }, _toDisplayString(cfg.ssd_click_mode === 'off' ? '已关闭' : '已开启'), 3)
                          ]),
                          _createElementVNode("label", _hoisted_16, [
                            _cache[16] || (_cache[16] = _createElementVNode("span", { class: "ssd-field-label" }, "确认方式", -1)),
                            _withDirectives(_createElementVNode("select", {
                              id: "ssd-transfer-mode",
                              "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((cfg.ssd_click_mode) = $event)),
                              "aria-describedby": "ssd-transfer-help"
                            }, [
                              (_openBlock(), _createElementBlock(_Fragment, null, _renderList(MODES, (mode) => {
                                return _createElementVNode("option", {
                                  key: mode.value,
                                  value: mode.value
                                }, _toDisplayString(mode.label), 9, _hoisted_17)
                              }), 64))
                            ], 512), [
                              [_vModelSelect, cfg.ssd_click_mode]
                            ])
                          ]),
                          _createElementVNode("label", _hoisted_18, [
                            _cache[18] || (_cache[18] = _createElementVNode("span", { class: "ssd-field-label" }, [
                              _createTextVNode("点击前等待"),
                              _createElementVNode("span", { class: "ssd-field-note" }, "默认 0.5 秒，最多 10 秒")
                            ], -1)),
                            _createElementVNode("span", _hoisted_19, [
                              _withDirectives(_createElementVNode("input", {
                                id: "ssd-confirm-delay",
                                "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((cfg.confirm_delay_seconds) = $event)),
                                type: "number",
                                min: "0",
                                max: "10",
                                step: "0.1",
                                "aria-describedby": "ssd-transfer-help"
                              }, null, 512), [
                                [
                                  _vModelText,
                                  cfg.confirm_delay_seconds,
                                  void 0,
                                  { number: true }
                                ]
                              ]),
                              _cache[17] || (_cache[17] = _createElementVNode("span", null, "秒", -1))
                            ])
                          ]),
                          (cfg.ssd_click_mode === '5min')
                            ? (_openBlock(), _createElementBlock("p", _hoisted_20, "后续 5 分钟转账可能不再提示确认。"))
                            : _createCommentVNode("", true)
                        ])
                      ], 8, _hoisted_7),
                      _cache[19] || (_cache[19] = _createElementVNode("details", { class: "ssd-help" }, [
                        _createElementVNode("summary", null, [
                          _createElementVNode("span", null, "使用说明"),
                          _createElementVNode("svg", {
                            viewBox: "0 0 24 24",
                            "aria-hidden": "true"
                          }, [
                            _createElementVNode("path", { d: "m9 5 7 7-7 7" })
                          ])
                        ]),
                        _createElementVNode("div", { class: "ssd-help-content" }, [
                          _createElementVNode("p", null, "使用平台已登录的 Telegram 用户账号，不是 Bot。仅监听 SSD 两个内置群（-1002014253433、-1001173590111）的官方机器人（752250569），无需填写凭据。"),
                          _createElementVNode("p", null, "两个功能默认关闭，不自动迁移旧开关。多站点转账保留成功回执记账和排行榜，不再自动确认。"),
                          _createElementVNode("p", null, "抽奖原文口令不加零宽字符。为避免误触发命令或转账，跳过 / 开头、+固定金额、+随机金额范围的口令。"),
                          _createElementVNode("p", null, "不跟踪开奖或中奖，不自动领奖；保留防重记录。同一抽奖及转账确认不会重复执行；发送或点击结果不明确时不自动重试。转账结果以官方机器人回执为准。"),
                          _createElementVNode("p", null, "参与前默认随机等待 2～5 秒（范围 0～60 秒）；确认等待默认 0.5 秒（0～10 秒）。")
                        ])
                      ], -1)),
                      _createElementVNode("div", _hoisted_21, [
                        (formError.value)
                          ? (_openBlock(), _createElementBlock("p", _hoisted_22, _toDisplayString(formError.value), 1))
                          : (_openBlock(), _createElementBlock("p", _hoisted_23, _toDisplayString(saveResult.value), 1)),
                        _createElementVNode("button", {
                          type: "submit",
                          class: "ssd-button ssd-primary",
                          disabled: saving.value || !ready.value || !!formError.value
                        }, _toDisplayString(saving.value ? '正在保存…' : '保存配置'), 9, _hoisted_24)
                      ])
                    ], 32))
            ]))
          : (_openBlock(), _createElementBlock("div", _hoisted_25, [
              _createElementVNode("div", _hoisted_26, [
                _createElementVNode("label", _hoisted_27, [
                  _cache[21] || (_cache[21] = _createElementVNode("span", null, "记录类型", -1)),
                  _withDirectives(_createElementVNode("select", {
                    id: "ssd-history-filter",
                    "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => ((historyFilter).value = $event))
                  }, [...(_cache[20] || (_cache[20] = [
                    _createElementVNode("option", { value: "all" }, "全部", -1),
                    _createElementVNode("option", { value: "lottery" }, "自动参与抽奖", -1),
                    _createElementVNode("option", { value: "transfer" }, "自动确认转账", -1)
                  ]))], 512), [
                    [_vModelSelect, historyFilter.value]
                  ])
                ]),
                _createElementVNode("button", {
                  type: "button",
                  class: "ssd-button",
                  disabled: historyLoading.value,
                  onClick: loadHistory
                }, [
                  _cache[22] || (_cache[22] = _createElementVNode("svg", {
                    viewBox: "0 0 24 24",
                    "aria-hidden": "true"
                  }, [
                    _createElementVNode("path", { d: "M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 11.5-2L20 8M4 16l2.5 3A7 7 0 0 0 18 17" })
                  ], -1)),
                  _createTextVNode(_toDisplayString(historyLoading.value ? '读取中…' : '刷新记录'), 1)
                ], 8, _hoisted_28)
              ]),
              _createElementVNode("div", _hoisted_29, [
                _cache[23] || (_cache[23] = _createElementVNode("p", { class: "ssd-tip" }, "最近 100 条；结果以官方机器人为准。", -1)),
                (runtime.value)
                  ? (_openBlock(), _createElementBlock("p", _hoisted_30, "运行中：抽奖" + _toDisplayString(runtime.value.lottery_enabled ? '开启' : '关闭') + " · 转账" + _toDisplayString(runtime.value.ssd_click_mode === 'off' ? '关闭' : MODES.find(item => item.value === runtime.value.ssd_click_mode)?.label || '未知'), 1))
                  : _createCommentVNode("", true)
              ]),
              (historyLoading.value)
                ? (_openBlock(), _createElementBlock("p", _hoisted_31, "正在读取执行记录…"))
                : (historyError.value)
                  ? (_openBlock(), _createElementBlock("p", _hoisted_32, _toDisplayString(historyError.value), 1))
                  : (!visibleHistory.value.length)
                    ? (_openBlock(), _createElementBlock("div", _hoisted_33, [
                        _cache[24] || (_cache[24] = _createElementVNode("svg", {
                          viewBox: "0 0 24 24",
                          "aria-hidden": "true"
                        }, [
                          _createElementVNode("path", { d: "M7 3h8l4 4v14H5V3zM15 3v5h4M9 12h6m-6 4h4" })
                        ], -1)),
                        _createElementVNode("h3", null, _toDisplayString(history.value.length ? '此类型暂无记录' : '暂无执行记录'), 1),
                        _createElementVNode("p", null, _toDisplayString(history.value.length ? '可切换记录类型查看其他操作。' : '开启功能并收到符合条件的新消息后，执行过程会显示在这里。'), 1)
                      ]))
                    : (_openBlock(), _createElementBlock("ol", _hoisted_34, [
                        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(visibleHistory.value, (item, index) => {
                          return (_openBlock(), _createElementBlock("li", {
                            key: item.key || `${item.kind}-${item.chat_id}-${item.message_id}-${index}`,
                            class: "ssd-record"
                          }, [
                            _createElementVNode("div", _hoisted_35, [
                              _createElementVNode("strong", null, [
                                _createTextVNode(_toDisplayString(item.kind === 'lottery' ? '自动参与抽奖' : '自动确认转账'), 1),
                                (item.lottery_id)
                                  ? (_openBlock(), _createElementBlock("span", _hoisted_36, " · " + _toDisplayString(item.lottery_id), 1))
                                  : _createCommentVNode("", true)
                              ]),
                              _createElementVNode("span", {
                                class: _normalizeClass(['ssd-record-status', { 'ssd-status-warning': ['uncertain', 'failed'].includes(item.status) }])
                              }, _toDisplayString(statusText(item)), 3)
                            ]),
                            _createElementVNode("p", _hoisted_37, _toDisplayString(item.detail || '暂无补充说明'), 1),
                            _createElementVNode("div", _hoisted_38, [
                              _createElementVNode("span", null, "群 " + _toDisplayString(item.chat_id) + " · 消息 " + _toDisplayString(item.message_id), 1),
                              _createElementVNode("time", null, _toDisplayString(formatTime(item.updated_at || item.created_at)), 1)
                            ])
                          ]))
                        }), 128))
                      ]))
            ]))
      ])
    ]),
    _: 1
  }))
}
}

};
const Config = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-7faf7ac4"]]);

export { Config as default };
