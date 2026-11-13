"""SSD 助手独立插件入口，不依赖多站点转账插件。"""
from .core import DEFAULTS, setup, teardown


__plugin__ = {
    "id": "ssd_assistant",
    "name": "SSD助手",
    "version": "0.0.2",
    "author": "AWdress",
    "scope": "user",
    "instance_mode": "account",
    "plugin_api_version": 2,
    "render_mode": "vue",
    "default_enabled": False,
    "description": "自动参与 SSD 官方口令抽奖，独立控制本人转账的单次或五分钟确认；持久去重，支持消息编辑，不发起转账。",
    "icon": "https://raw.githubusercontent.com/AWdress/AWBotHub-Plugins/main/plugins_v2/ssd_assistant/icon.png?v=0.0.2",
    "changelog": "v0.0.2\n- 更换为 SpringSunday 图标，更新图标缓存地址\n- 修复开关与平台全局样式冲突，开启/关闭文字不再挤入开关或换行\n\nv0.0.1\n- 新增 SSD 官方口令抽奖自动参与，按抽奖 ID 持久去重\n- 从多站点转账迁入 SSD 自动确认，排行榜仅负责成功记账\n- 单次/五分钟确认、中文分组配置与操作记录；两功能默认关闭\n- 校验官方 Bot、本人原请求和金额，发送/点击结果不明时不自动重试",
    "tags": ["SSD", "SpringSunday", "抽奖", "转账确认"],
    "requirements": [],
    "config_schema": {},
    "resources": {"timeout_seconds": 120, "max_concurrency": 8, "max_background_tasks": 0},
}
