import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import Config from './__federation_expose_Config-C-NQplZq.js';

true              &&(function polyfill() {
  const relList = document.createElement("link").relList;
  if (relList && relList.supports && relList.supports("modulepreload")) {
    return;
  }
  for (const link of document.querySelectorAll('link[rel="modulepreload"]')) {
    processPreload(link);
  }
  new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type !== "childList") {
        continue;
      }
      for (const node of mutation.addedNodes) {
        if (node.tagName === "LINK" && node.rel === "modulepreload")
          processPreload(node);
      }
    }
  }).observe(document, { childList: true, subtree: true });
  function getFetchOpts(link) {
    const fetchOpts = {};
    if (link.integrity) fetchOpts.integrity = link.integrity;
    if (link.referrerPolicy) fetchOpts.referrerPolicy = link.referrerPolicy;
    if (link.crossOrigin === "use-credentials")
      fetchOpts.credentials = "include";
    else if (link.crossOrigin === "anonymous") fetchOpts.credentials = "omit";
    else fetchOpts.credentials = "same-origin";
    return fetchOpts;
  }
  function processPreload(link) {
    if (link.ep)
      return;
    link.ep = true;
    const fetchOpts = getFetchOpts(link);
    fetch(link.href, fetchOpts);
  }
}());

// 离线预览：所有配置与记录均为模拟数据，不调用真实 AI 或 Telegram。
const {createApp,h} = await importShared('vue');

let store = {};
const previewError = new URLSearchParams(location.search).has('config-fail');
const mockHost = {
  async getConfig() {
    if (previewError) throw new Error('模拟网络错误，请刷新后重试')
    return { ...store }
  },
  async saveConfig(values) {
    store = { ...store, ...values };
    document.querySelector('#saved-config').textContent = JSON.stringify(store, null, 2);
  },
  async callApi(path) {
    const url = new URL(path, 'https://preview.invalid');
    if (url.pathname === '/chat_names') return { items: [{ id: -1001234567890, title: '离线演示群' }] }
    if (url.pathname === '/histories') return {
      items: [{ chat_id: -1001234567890, chat_title: '离线演示群', is_private: false, count: 2, last: '这是一条模拟回答。' }],
      proactive_next: '',
    }
    if (url.pathname === '/history') return {
      chat_id: Number(url.searchParams.get('chat_id')),
      messages: [{ role: 'user', content: '这是一条模拟问题。' }, { role: 'assistant', content: '这是一条模拟回答。' }],
    }
    if (url.pathname === '/history/clear') return { ok: true }
    return { ok: false, message: '离线预览未提供此接口' }
  },
  toast: {
    success: message => { document.querySelector('#preview-status').textContent = message; },
    error: message => { document.querySelector('#preview-status').textContent = message; },
  },
};

createApp({
  render: () => h('main', [
    h(Config, { pluginId: 'ai', host: mockHost }),
    h('p', { id: 'preview-status', role: 'status' }),
    h('details', [h('summary', '已保存的模拟配置'), h('pre', { id: 'saved-config', style: 'white-space:pre-wrap;overflow-wrap:anywhere' })]),
  ]),
}).mount('#app');
