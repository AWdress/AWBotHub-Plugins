// 离线预览：所有配置与记录均为模拟数据，不调用真实 AI 或 Telegram。
import { createApp, h } from 'vue'
import Config from './Config.vue'

let store = {}
const previewError = new URLSearchParams(location.search).has('config-fail')
const mockHost = {
  async getConfig() {
    if (previewError) throw new Error('模拟网络错误，请刷新后重试')
    return { ...store }
  },
  async saveConfig(values) {
    store = { ...store, ...values }
    document.querySelector('#saved-config').textContent = JSON.stringify(store, null, 2)
  },
  async callApi(path) {
    const url = new URL(path, 'https://preview.invalid')
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
    success: message => { document.querySelector('#preview-status').textContent = message },
    error: message => { document.querySelector('#preview-status').textContent = message },
  },
}

createApp({
  render: () => h('main', [
    h(Config, { pluginId: 'ai', host: mockHost }),
    h('p', { id: 'preview-status', role: 'status' }),
    h('details', [h('summary', '已保存的模拟配置'), h('pre', { id: 'saved-config', style: 'white-space:pre-wrap;overflow-wrap:anywhere' })]),
  ]),
}).mount('#app')
