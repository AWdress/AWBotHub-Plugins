"""多站点 PT 自动签到：平台 CloakBrowser + 平台同步 Cookie。"""

from __future__ import annotations

import asyncio
from datetime import datetime
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import threading
import time
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from telethon import Button

import httpx
from bs4 import BeautifulSoup


_CHANGELOG_V2_0_13 = (
    "v2.0.13 修复 Cloudflare Turnstile 完整流程\n"
    "- 区分自动验证与 Managed 验证，Audiences、OurBits 均可对真实 iframe 执行一次拟人点击\n"
    "- Turnstile 使用有头浏览器、独立 90 秒验证窗口和第三方挑战 Cookie 支持\n"
    "- 记录实际 Chromium 内核版本与授权层级，旧版内核给出明确升级提示\n"
    "- 代理模式完全交给 GeoIP，同步 Cookie 不再覆盖持久 profile 的 Cloudflare 通行状态\n\n"
)


_CHANGELOG_V2_0_14 = (
    "v2.0.14 适配平台 CloakBrowser 统一治理\n"
    "- 移除插件内核预装、独立缓存和代理环境变量修改\n"
    "- 代理、License Key、内核更新及免费会话排队交由平台统一处理\n"
    "- 浏览器上下文继续在每站结束后关闭，避免占用后续插件会话\n\n"
)


_CHANGELOG_V2_0_15 = (
    "v2.0.15 等待依赖就绪后再签到\n"
    "- 每轮签到先核对全部 Python 依赖版本，再准备所需 CloakBrowser 内核\n"
    "- 浏览器准备完成并关闭预检会话后，才开始读取 Cookie 和访问签到站点\n"
    "- 依赖或内核准备失败时直接停止本轮，并在插件状态和日志中显示原因\n\n"
)


_CHANGELOG_V2_0_16 = (
    "v2.0.16 修复 Docker Turnstile 会话复用\n"
    "- Audiences 与 OurBits 改用全新临时 CloakBrowser 上下文，不再复用持久 profile 和旧 Cloudflare 状态\n"
    "- 原生验证长时间未响应时重置官方控件，保留真实 Managed iframe 点击支持\n"
    "- Turnstile 或页面验证超时会按重试配置关闭会话并更换新指纹，不再被误判为不可重试\n\n"
)


_CHANGELOG_V2_5_55 = (
    "v2.5.55 修复版本号倒退并统一插件元数据\n"
    "- 恢复高于历史 v2.5.54 的连续版本号，避免市场把新版本误判为旧版本\n"
    "- 同步入口、核心模块、manifest、README 和前端包版本\n\n"
)


_CHANGELOG_V2_6_0 = (
    "v2.6.0 增强 TJUPT 与 U2 AI 答题\n"
    "- TJUPT AI 输入改为完整验证区域截图，同时识别左侧影视海报与右侧候选项\n"
    "- TJUPT 识别出答案后自动勾选并提交，提交前重新确认题目未变化\n"
    "- U2 优先调用平台 AI 识别正确选项；AI 不可用时保留随机答案兜底并记录原因\n\n"
)


_CHANGELOG_V2_6_1 = (
    "v2.6.1 支持 U2 独立定时\n"
    "- U2 可单独设置签到小时和分钟，默认北京时间 09:00\n"
    "- 其他站点继续使用原有全局定时，避免 U2 站点 9 点前被误触发\n\n"
)


_CHANGELOG_V2_6_2 = (
    "v2.6.2 固定启用 U2 AI 识别\n"
    "- 移除配置页中的 U2 AI 识别开关，U2 自动优先使用平台 AI\n"
    "- AI 服务不可用时保留随机答案兜底，不影响签到流程\n\n"
)


_CHANGELOG_V2_6_3 = (
    "v2.6.3 强化 TJUPT 全自动海报识别\n"
    "- 视觉模型同时接收完整页面和海报裁剪图，避免遗漏左侧影视海报\n"
    "- AI 识别失败不再回退 Telegram 手动模式，改为重试后明确失败并跳过提交\n\n"
)


_CHANGELOG_V2_6_4 = (
    "v2.6.4 优化 AI 识别日志\n"
    "- TJUPT 和 U2 日志明确显示 AI 识别出的候选名称，便于核对实际提交答案\n\n"
)


_CHANGELOG_V2_7_0 = (
    "v2.7.0 增加通用站点签到与中文站点分组\n"
    "- 固定适配站点按 12 大站点、其他站点分组并统一显示中文名称\n"
    "- 移除不支持签到的 M-Team\n"
    "- 新增可添加任意 PT 站点的通用签到配置，Cookie 继续由平台按域名读取\n\n"
 )

_CHANGELOG_V2_7_1 = (
    "v2.7.1 增加红豆饭、织梦、麒麟签到\n"
    "- 新增 HDFans、ZMPT、HDKYL 三个通用 PT 站点适配\n"
    "- Cookie 继续由平台按站点域名读取，使用通用签到结果确认流程\n\n"
)

_CHANGELOG_V2_7_2 = (
    "v2.7.2 增加大青虫签到\n"
    "- 新增 CyanBug（cyanbug.net）通用 PT 签到适配\n\n"
)


_CHANGELOG_V2_7_3 = (
    "v2.7.3 修复 U2 视觉验证识别\n"
    "- U2 签到验证题改为交给视觉模型判断半透明圆点标出的作品，不再用文字模型猜选项\n"
    "- 恢复并增强圆点定位高亮，OpenCV 不可用时安全回退原图\n"
    "- 验证图片按站点模板多种特征定位，日志记录实际使用的来源与图片大小\n"
    "- 视觉模型不可用或识别失败时仍保留随机兜底，不影响签到流程\n\n"
)


_CHANGELOG_V2_7_4 = (
    "v2.7.4 增加失败站点延迟补签\n"
    "- 单站失败后立即记录并继续处理下一站，不中断整轮签到\n"
    "- 首轮结束 30 分钟后仅重试失败站点一次，补签完成后结束且不循环重试\n\n"
    "- U2 自动签到留言统一填写‘一切随缘~’\n\n"
)


_CHANGELOG_V2_7_5 = (
    "v2.7.5 修复定时签到被正在运行的任务跳过\n"
    "- 每日签到与 U2 签到遇到运行中的任务时排队，上一轮结束后自动执行\n"
    "- 定时回调返回真实签到结果，等待超时不再取消已排队的签到\n"
    "- 同类未完成的定时任务不重复创建，停用或重载时统一取消\n\n"
)


_CHANGELOG_V2_7_6 = (
    "v2.7.6 移除观众签到\n"
    "- 观众已关闭官方签到，移除站点选项、默认勾选和 Cookie 域名声明\n"
    "- 自动清理旧配置中的观众勾选，通用签到及失败补签不再访问观众站点\n"
    "- 保留其他站点设置与历史签到记录\n\n"
)


_CHANGELOG_V2_0_12 = (
    "v2.0.12 修复 CloakBrowser 首次安装超时\n"
    "- 启用插件后在后台预装 CloakBrowser 内核，签到时仍会自动补检\n"
    "- 内核下载自动使用平台代理，放宽连接与大文件读取超时并对短暂网络错误重试\n"
    "- 内核缓存改存插件持久数据目录，Docker 更新或重启后无需重新下载\n"
    "- 下载失败改为可操作的站点级提示，不再由子任务输出整段后台异常堆栈\n\n"
)


__plugin__ = {
    "name": "PT站自动签到",
    "id": "pt_multi_checkin",
    "version": "2.7.10",
    "author": "AWdress",
    "description": "多 PT 站自动签到中心，统一使用平台 Cookie 与 CloakBrowser，提供 Vue 管理界面。",
    "icon": "https://raw.githubusercontent.com/AWdress/AWBotNest-Plugins/main/plugins/icons/pt_checkin_v2.svg",
    "changelog": "v2.0.11 对齐 CloakBrowser 官方 Turnstile 流程\n- Audiences 与 OurBits 使用 Preview 持久会话、代理 GeoIP 和原生验证流程\n- 移除固定语言与代理出口不一致、显式重建控件和高频 CDP 等待\n- 清理 V2 前端隐藏文件，修复插件路径安全检查失败\n\nv2.0.10 修复签到参数显示不完整\n- 数字输入框保留稳定宽度，避免浏览器步进控件遮挡数值\n- 重试间隔单位改为独立布局，窄窗口自动换行且不再与数值重叠\n\nv2.0.9 修复 Audiences Docker 自动验证\n- 改用真正的 CloakBrowser 持久 profile 与固定指纹，避免 Cloudflare Cookie 和随机指纹错配\n- Audiences 只等待托管验证自动签发令牌，不再误点空的 Turnstile 外层容器\n- 控件未初始化时重新加载官方 API 并显式渲染，超时日志补充脚本、指纹和控件状态\n\nv2.0.8 修复 OurBits 与 TJUPT CloakBrowser 签到\n- OurBits 适配新的 form#attendance Turnstile，并只接受真实提交回执\n- TJUPT 保留 CloakBrowser 会话，改由已解析 DOM 元素提交表单，避免拟人层重复解析链式选择器\n\nv2.0.7 修复 OurBits、U2 与 Audiences 实际签到\n- OurBits 删除普通首页导航的成功推断，只接受站点明确签到状态或回执\n- U2 不再调用 AI 识图，直接任选一项提交；答错获得 1 UCoin 仍计为签到成功\n- Audiences 浏览器整轮限制为 30 秒，无结果立即跳过并关闭当前上下文\n\nv2.0.6 修复 Audiences 与 U2 签到\n- Audiences 改用真实 CloakBrowser 指纹与持久 storage_state，复用 Cloudflare 验证会话\n- CookieCloud 最新 Cookie 覆盖同名旧值，未同步的 Cloudflare 通行状态由持久上下文保留\n- U2 正确识别“回答错误但获得 1 UCoin”为已完成签到，不再误报失败\n\nv2.0.5 恢复 OurBits 首页签到确认\n- 将 V1 已验证的首页回执判定迁入原生 V2 核心\n- 签到后跳回站点根页且签到入口消失时确认已完成\n- HTTP、CloakBrowser 和结果回查使用同一严格条件，不把登录页或未签到首页误报成功\n\nv2.0.4 TJUPT AI 完全自动化\n- 启用 tjupt_ai_assist 时，AI 识别后直接自动提交答案\n- AI 识别失败时自动回退到 Telegram 手动选择模式\n- 优化 AI prompt，要求直接返回选项序号\n- 增强日志输出，记录 AI 识别过程和结果\n\nv2.0.3 修复 U2 签到提交\n- U2 跳过会被安全策略拒绝的轻量 HTTP 提交，直接使用 CloakBrowser\n- 改用真实浏览器表单按钮提交验证答案，并绕过缓存回查首页状态\n- 补充错误答案与过期验证识别，避免未确认状态重复误报",
    "scope": "standalone",
    "min_platform_version": "1.1.4.0",
    "plugin_api_version": 2,
    "requirements": ["httpx>=0.27", "beautifulsoup4>=4.12", "cloakbrowser>=0.5.10", "geoip2>=4.8", "socksio>=1.0", "packaging>=24.0", "Pillow>=10.0"],
    "cookie_domains": [
        "ourbits.club", "*.ourbits.club",
        "hhanclub.net", "*.hhanclub.net",
        "piggo.me", "*.piggo.me", "tjupt.org", "*.tjupt.org", "52pt.site", "*.52pt.site",
        "pt.btschool.club", "*.pt.btschool.club", "ptchdbits.co", "*.ptchdbits.co",
        "haidan.video", "*.haidan.video", "club.hares.top", "*.club.hares.top",
        "hdarea.club", "*.hdarea.club", "hdchina.org", "*.hdchina.org",
        "hdcity.city", "*.hdcity.city", "hdsky.me", "*.hdsky.me",
        "pt.hdupt.com", "*.pt.hdupt.com", "hdhome.org", "*.hdhome.org",
        "hdfans.org", "*.hdfans.org", "zmpt.cc", "*.zmpt.cc", "hdkyl.in", "*.hdkyl.in",
        "cyanbug.net", "*.cyanbug.net",
        "open.cd", "*.open.cd",
        "pterclub.net", "*.pterclub.net", "pttime.org", "*.pttime.org",
        "totheglory.im", "*.totheglory.im", "u2.dmhy.org", "*.u2.dmhy.org",
        "yemapt.org", "*.yemapt.org", "zhuque.in", "*.zhuque.in",
    ],
    "default_enabled": False,
    "render_mode": "vue",
    "config_schema": {
        "piggo_username": {"type": "string", "default": "", "label": "猪猪用户名"},
        "piggo_password": {
            "type": "password", "secret": True, "default": "", "label": "猪猪密码",
            "help": "每轮使用全新浏览器会话，通过官网原生表单以用户名和密码登录；不复用旧 Token 或锁定会话。遇到验证码或二次验证会提示。",
        },
        # 仅保留旧字段的敏感标记，避免旧配置通过平台 API 回显；运行时不再读取。
        "piggo_token": {
            "type": "password", "secret": True, "default": "", "label": "旧版登录凭证（已停用）",
            "help": "仅用于遮蔽旧版本已保存的敏感值，当前版本不读取、不使用此字段；请填写用户名和密码。",
        },
    },
    "resources": {
        "timeout_seconds": 1800, "max_concurrency": 8, "max_background_tasks": 8,
        "failure_threshold": 3, "recovery_seconds": 120,
    },
}
__plugin__["changelog"] = "v2.7.10 增加猪猪服务器登录超时诊断\n- 超时时自动记录页面类别、表单/日历可见性、会话和账号匹配状态，无需查看浏览器窗口\n- 汇总关键请求的固定网络错误分类，不记录网址、响应正文、密码或 Token\n- 仅增强排查信息，不增加登录/签到点击，不改变成功判定与等待时限\n\nv2.7.9 修复猪猪账号密码签到流程\n- 每轮通过官网表单以账号密码登录，不复用旧 Token、Cookie 或空闲锁定会话\n- 猪猪上下文沿用 CloakBrowser 默认地区、语言和窗口设置，避免重复覆盖\n- 日历加载完成并稳定后才提交，遇明确拒绝且无验证窗口时最多再点击一次\n- 保留官网原生验证与请求重放，严格核对今天的签到标记，不把 HTTP 200 或历史记录当作成功\n- 配置页移除旧 Token 输入，改进登录、公告加载和验证失败诊断，不记录凭据\n\nv2.7.8 修复猪猪自动登录兼容性\n- 登录表单改用拟人浏览器支持的单一 CSS 定位，避免填写或提交失败\n- 等待官网完成 Token 会话恢复，避免用户资料异步加载时重复登录\n- 登录恢复失败时记录官网接口 HTTP 状态，不记录响应正文、密码或 Token\n\nv2.7.7 适配新版猪猪签到与自动登录\n- 猪猪改用新版日历当天签到按钮，严格核对当天记录，不点击补签\n- 支持用户名和密码自动登录，复用登录 Token，失效后自动获取新凭证\n- 密码与 Token 按敏感配置保存；遇验证码或二次验证停止并提示\n\n" + _CHANGELOG_V2_7_6 + _CHANGELOG_V2_7_5 + _CHANGELOG_V2_7_4 + _CHANGELOG_V2_7_3 + _CHANGELOG_V2_7_2 + _CHANGELOG_V2_7_1 + _CHANGELOG_V2_7_0 + _CHANGELOG_V2_6_4 + _CHANGELOG_V2_6_3 + _CHANGELOG_V2_6_2 + _CHANGELOG_V2_6_1 + _CHANGELOG_V2_6_0 + _CHANGELOG_V2_5_55 + _CHANGELOG_V2_0_16 + _CHANGELOG_V2_0_15 + _CHANGELOG_V2_0_14 + _CHANGELOG_V2_0_13 + _CHANGELOG_V2_0_12 + __plugin__["changelog"]

SITES = {
    # PT 社区常用的 12 个站点置于第一组；其余已有适配站点置于第二组。
    "ourbits": {"name": "我堡", "domain": "ourbits.club", "url": "https://ourbits.club/attendance.php", "group": "12大站点"},
    "piggo": {"name": "猪猪", "domain": "piggo.me", "url": "https://piggo.me/calendar", "group": "其他站点"},
    "hhan": {"name": "憨憨", "domain": "hhanclub.net", "url": "https://hhanclub.net/attendance.php", "group": "12大站点"},
    "tjupt": {"name": "北洋园", "domain": "tjupt.org", "url": "https://www.tjupt.org/attendance.php", "group": "其他站点"},
    "chdbits": {"name": "彩虹岛", "domain": "ptchdbits.co", "url": "https://ptchdbits.co/bakatest.php", "mode": "interactive", "group": "12大站点"},
    "opencd": {"name": "皇后", "domain": "open.cd", "url": "https://www.open.cd", "mode": "interactive", "group": "12大站点"},
    "u2": {"name": "幼儿园", "domain": "u2.dmhy.org", "url": "https://u2.dmhy.org/showup.php", "mode": "interactive", "group": "其他站点"},
    "btschool": {"name": "学校", "domain": "pt.btschool.club", "url": "https://pt.btschool.club", "mode": "btschool", "group": "其他站点"},
    "hdsky": {"name": "天空", "domain": "hdsky.me", "url": "https://hdsky.me", "mode": "interactive", "group": "12大站点"},
    "pterclub": {"name": "猫站", "domain": "pterclub.net", "url": "https://pterclub.net/attendance-ajax.php", "mode": "pterclub", "group": "12大站点"},
    "ttg": {"name": "听听歌", "domain": "totheglory.im", "url": "https://totheglory.im", "mode": "ttg", "group": "12大站点"},
    "hdhome": {"name": "家园", "domain": "hdhome.org", "url": "https://hdhome.org/attendance.php", "group": "12大站点"},
    "hdfans": {"name": "红豆饭", "domain": "hdfans.org", "url": "https://hdfans.org/attendance.php", "mode": "generic", "generic": True, "group": "其他站点"},
    "zmpt": {"name": "织梦", "domain": "zmpt.cc", "url": "https://zmpt.cc/attendance.php", "mode": "generic", "generic": True, "group": "其他站点"},
    "hdkyl": {"name": "麒麟", "domain": "hdkyl.in", "url": "https://www.hdkyl.in/attendance.php", "mode": "generic", "generic": True, "group": "其他站点"},
    "cyanbug": {"name": "大青虫", "domain": "cyanbug.net", "url": "https://cyanbug.net/attendance.php", "mode": "generic", "generic": True, "group": "其他站点"},
    "pt52": {"name": "我爱PT", "domain": "52pt.site", "url": "https://52pt.site/bakatest.php", "mode": "interactive", "group": "其他站点"},
    "haidan": {"name": "海胆", "domain": "haidan.video", "url": "https://www.haidan.video/signin.php", "mode": "haidan", "group": "其他站点"},
    "hares": {"name": "白兔", "domain": "club.hares.top", "url": "https://club.hares.top", "mode": "hares", "group": "其他站点"},
    "hdarea": {"name": "好大", "domain": "hdarea.club", "url": "https://www.hdarea.club", "mode": "hdarea", "group": "其他站点"},
    "hdchina": {"name": "高清中国", "domain": "hdchina.org", "url": "https://hdchina.org/index.php", "mode": "hdchina", "group": "其他站点"},
    "hdcity": {"name": "高清城市", "domain": "hdcity.city", "url": "https://hdcity.city/sign", "mode": "direct", "group": "其他站点"},
    "hdupt": {"name": "北邮人", "domain": "pt.hdupt.com", "url": "https://pt.hdupt.com", "mode": "hdupt", "group": "其他站点"},
    "pttime": {"name": "PT时间", "domain": "pttime.org", "url": "https://www.pttime.org/attendance.php", "mode": "pttime", "group": "其他站点"},
    "yema": {"name": "野马", "domain": "yemapt.org", "url": "https://yemapt.org/api/consumer/checkIn", "mode": "yema", "group": "其他站点"},
    "zhuque": {"name": "朱雀", "domain": "zhuque.in", "url": "https://zhuque.in", "mode": "zhuque", "group": "其他站点"},
}


DEFAULTS = {
    "auto_checkin": True, "notify_result": True, "headless": True,
    "checkin_hour": 8, "checkin_minute": 10, "u2_checkin_hour": 9, "u2_checkin_minute": 0,
    "retry_count": 2, "retry_interval": 20,
    "tjupt_ai_assist": True, "tjupt_confirm_timeout": 300,
    "selected_sites": list(SITES.keys()), "custom_sites": [],
    "piggo_username": "", "piggo_password": "",
}


_run_lock: asyncio.Lock | None = None
_active_run_task: asyncio.Task | None = None
_tasks: set[asyncio.Task] = set()
_scheduled_tasks: dict[str, asyncio.Task] = {}
_failed_retry_tasks: dict[str, asyncio.Task] = {}
_HISTORY_KEY = "history"
_LAST_KEY = "last_result"
_tjupt_pending: dict[str, dict] = {}
_browser_cookie_cache: dict[str, str] = {}
_xvfb_lock = threading.Lock()
_xvfb_process: subprocess.Popen | None = None
_xvfb_display = ""
_state = {"running": False, "started_at": "", "finished_at": "", "current": "", "phase": "", "message": "", "completed": 0, "total": 0}
_CHINA_TZ = ZoneInfo("Asia/Shanghai")
_runtime_logs: list[dict[str, str]] = []
_storage_state: dict = {}
_storage_tasks: set[asyncio.Task] = set()

_TURNSTILE_TIMEOUT_SECONDS = 90
_TURNSTILE_AUTO_GRACE_SECONDS = 8
_FAILED_RETRY_DELAY_SECONDS = 30 * 60
_CLOUDFLARE_SESSION_COOKIES = {"cf_clearance", "__cf_bm"}


def _is_cloudflare_session_cookie(name: object) -> bool:
    """Return whether a cookie is bound to Cloudflare's browser challenge session."""
    normalized = str(name or "").strip().lower()
    return normalized in _CLOUDFLARE_SESSION_COOKIES or normalized.startswith("cf_chl_")


def _cloakbrowser_binary_details(cloakbrowser, release_channel: str = "preview") -> dict:
    """Read the binary that will actually launch; wrapper version alone is misleading."""
    try:
        info = cloakbrowser.binary_info(release_channel=release_channel)
    except TypeError:
        info = cloakbrowser.binary_info()
    except Exception as exc:  # noqa: BLE001
        return {"version": "未知", "tier": "未知", "error": type(exc).__name__}
    return dict(info or {})


def _log_cloakbrowser_binary(ctx, cloakbrowser, site_name: str, release_channel: str = "preview") -> None:
    info = _cloakbrowser_binary_details(cloakbrowser, release_channel)
    version = str(info.get("version") or "未知")
    tier = str(info.get("tier") or "未知")
    _runtime_log(ctx, f"实际 CloakBrowser Chromium {version}（{tier}）", site=site_name)
    try:
        major = int(version.split(".", 1)[0])
    except (TypeError, ValueError):
        major = 0
    if major and major < 151:
        _runtime_log(
            ctx,
            "当前为旧版 keyless 内核；官方当前 Turnstile 结果基于 Chromium 151。"
            "请在平台系统设置中启用 CloakBrowser 免费 Key 并填写 Key 后重试",
            level="warning",
            site=site_name,
        )


def _stored(key, default=None):
    return _storage_state.get(key, default)


def _persist(ctx, key, value):
    _storage_state[key] = value
    task = ctx.create_task(ctx.storage.set(key, value), name=f"pt-checkin-storage:{key}")
    _storage_tasks.add(task)
    task.add_done_callback(_storage_tasks.discard)


def _runtime_log(ctx, message: str, *, level: str = "info", site: str = "") -> None:
    _runtime_logs.append({
        "time": datetime.now(_CHINA_TZ).strftime("%H:%M:%S"),
        "level": level,
        "site": site,
        "message": str(message),
    })
    del _runtime_logs[:-200]
    try:
        logger = getattr(ctx, "log", None)
        method = "warning" if level == "warning" else ("error" if level == "error" else "info")
        if logger is not None:
            getattr(logger, method)("%s%s", f"[{site}] " if site else "", message)
    except Exception:
        pass


def _ensure_docker_display(ctx) -> str:
    """确保 Docker 内存在仅供浏览器使用的本地 Xvfb 显示器。"""
    global _xvfb_display, _xvfb_process
    current = str(os.environ.get("DISPLAY") or "").strip()
    if current or not os.path.exists("/.dockerenv"):
        return current
    with _xvfb_lock:
        current = str(os.environ.get("DISPLAY") or "").strip()
        if current:
            return current

        # xvfb-run 可能启动了显示器但调用方清除了 DISPLAY；优先复用现有 socket。
        socket_dir = Path("/tmp/.X11-unix")
        if socket_dir.is_dir():
            for socket_path in sorted(socket_dir.glob("X*")):
                suffix = socket_path.name[1:]
                if suffix.isdigit():
                    current = f":{suffix}"
                    os.environ["DISPLAY"] = current
                    _runtime_log(ctx, f"发现现有 Xvfb 显示器 {current}，已恢复 DISPLAY", site="Audiences")
                    return current

        executable = shutil.which("Xvfb")
        if not executable:
            _runtime_log(
                ctx,
                "容器未安装 Xvfb，无法为 Audiences 启用虚拟有头模式；当前运行的 latest 镜像不包含仓库中的浏览器依赖",
                level="error",
                site="Audiences",
            )
            return ""

        display_number = next(
            (number for number in range(90, 111) if not (socket_dir / f"X{number}").exists()),
            None,
        )
        if display_number is None:
            _runtime_log(ctx, "没有可用的 Xvfb 显示器编号", level="error", site="Audiences")
            return ""
        current = f":{display_number}"
        try:
            process = subprocess.Popen(
                [executable, current, "-screen", "0", "1920x1080x24", "-nolisten", "tcp"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            deadline = time.monotonic() + 5
            socket_path = socket_dir / f"X{display_number}"
            while time.monotonic() < deadline and process.poll() is None and not socket_path.exists():
                time.sleep(0.1)
            if process.poll() is not None or not socket_path.exists():
                if process.poll() is None:
                    process.terminate()
                _runtime_log(ctx, "Xvfb 启动失败，未创建显示器 socket", level="error", site="Audiences")
                return ""
            _xvfb_process = process
            _xvfb_display = current
            os.environ["DISPLAY"] = current
            _runtime_log(ctx, f"插件已启动 Xvfb 虚拟显示器 {current}", site="Audiences")
            return current
        except Exception as exc:  # noqa: BLE001
            _runtime_log(ctx, f"Xvfb 启动异常：{type(exc).__name__}", level="error", site="Audiences")
            return ""


async def _with_heartbeat(awaitable, ctx, site: str, message: str, *, interval: int = 10, max_wait: int = 600):
    """等待长浏览器任务时持续写入插件页与平台日志。"""
    # 这是已由平台托管的签到任务的内部子任务。若再使用
    # ctx.create_task，平台 done callback 会在上层尚未处理异常时
    # 先记录“后台任务执行失败”整段堆栈。
    task = asyncio.create_task(awaitable, name=f"pt-checkin-{site}")
    elapsed = 0
    try:
        while elapsed < max_wait:
            wait_for = min(interval, max_wait - elapsed)
            done, _ = await asyncio.wait({task}, timeout=wait_for)
            if done:
                return task.result()
            elapsed += wait_for
            _runtime_log(ctx, f"{message}，已等待 {elapsed} 秒", level="warning", site=site)
        raise RuntimeError(
            f"CloakBrowser 等待超过 {max_wait} 秒，已终止本轮签到；"
            "若日志曾长时间停在浏览器等待，请重启平台以释放底层浏览器线程"
        )
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


def _prepare_runtime_dependencies(selected_keys: list[str]) -> list[str]:
    """确认平台依赖已完整安装，并通过正常 launch 预备浏览器内核。

    这里只使用平台已经代理和治理过的 CloakBrowser launch 接口，不直接调用
    ensure_binary、不修改缓存目录，也不读取平台 License Key。
    """
    from packaging.requirements import Requirement

    versions: list[str] = []
    import_names = {"beautifulsoup4": "bs4", "pillow": "PIL"}
    for raw in __plugin__["requirements"]:
        requirement = Requirement(raw)
        installed = importlib.metadata.version(requirement.name)
        if requirement.specifier and not requirement.specifier.contains(installed, prereleases=True):
            raise RuntimeError(f"依赖版本不满足：{requirement.name} {installed}，需要 {requirement.specifier}")
        importlib.import_module(import_names.get(requirement.name.lower(), requirement.name.replace("-", "_")))
        versions.append(f"{requirement.name} {installed}")

    import cloakbrowser

    channels: list[str] = []
    if any(key in {"audiences", "ourbits"} for key in selected_keys):
        channels.append("preview")
    if any(key not in {"audiences", "ourbits"} for key in selected_keys):
        channels.append("stable")

    binaries: list[str] = []
    for channel in channels:
        browser = None
        try:
            # 正常 launch 会由平台选择代理、License Key、兼容内核和免费会话队列；
            # 成功返回即表示该通道所需内核已经可以启动。
            browser = cloakbrowser.launch(headless=True, release_channel=channel)
            info = _cloakbrowser_binary_details(cloakbrowser, channel)
            binaries.append(
                f"{channel} Chromium {info.get('version') or '未知'}（{info.get('tier') or '未知'}）"
            )
        finally:
            if browser is not None:
                browser.close()
    return versions + binaries


def _cfg(ctx) -> dict:
    return {**DEFAULTS, **dict(ctx.config or {})}


def _piggo_account(ctx) -> tuple[str, str]:
    cfg = _cfg(ctx)
    username, password = cfg.get("piggo_username"), cfg.get("piggo_password")
    username = username.strip() if isinstance(username, str) else ""
    password = password if isinstance(password, str) and password != "********" else ""
    return username, password


class _PiggoLoginObservation:
    """只读官网登录回执；事件回调不等待 RPC，也不记录任何响应原文。"""

    def __init__(self, page, ctx):
        self.page, self.ctx = page, ctx
        self.latest = self.finished = None
        self.started = 0.0
        self.finished_at = 0.0
        self.closed = False
        self.failure = ""
        self.network_issues = set()
        try:
            page.on("request", self.requested)
            page.on("requestfinished", self.completed)
            page.on("requestfailed", self.network_failed)
            page.on("response", self.network_response)
        except Exception:
            self.close()

    @staticmethod
    def trusted(request):
        try:
            parsed = urlparse(request.url)
            return parsed.scheme == "https" and parsed.hostname in {"piggo.me", "www.piggo.me"} \
                and parsed.port in {None, 443} and parsed.username is None and parsed.password is None \
                and parsed.path in {"/v1/web/auth/srp/login", "/v1/web/login"} and request.method == "POST"
        except Exception:
            return False

    def requested(self, request):
        if not self.closed and self.trusted(request):
            self.latest, self.finished = request, None
            self.started = time.monotonic()
            self.finished_at = 0.0
            self.failure = ""
            label = "SRP 登录" if urlparse(request.url).path == "/v1/web/auth/srp/login" else "原生密码登录"
            _runtime_log(self.ctx, f"官网{label}请求已发出，等待完整回执", site="猪猪")

    def completed(self, request):
        if not self.closed and request is self.latest and self.trusted(request):
            self.finished = request
            self.finished_at = time.monotonic()

    def network_issue(self, request, code):
        if self.closed or len(self.network_issues) >= 6:
            return
        parsed = urlparse(request.url)
        if parsed.scheme != "https" or parsed.hostname not in {"piggo.me", "www.piggo.me"} \
                or parsed.port not in {None, 443} or parsed.username is not None or parsed.password is not None:
            return
        kind = {"document": "网页", "script": "脚本", "stylesheet": "样式",
                "xhr": "站点接口", "fetch": "站点接口"}.get(request.resource_type)
        if kind:
            self.network_issues.add(f"{kind}:{code}")

    def network_failed(self, request):
        try:
            code = {
                "net::ERR_ABORTED": "请求中止", "net::ERR_TIMED_OUT": "请求超时",
                "net::ERR_CONNECTION_TIMED_OUT": "连接超时", "net::ERR_NAME_NOT_RESOLVED": "DNS失败",
                "net::ERR_PROXY_CONNECTION_FAILED": "代理连接失败",
                "net::ERR_TUNNEL_CONNECTION_FAILED": "代理隧道失败",
                "net::ERR_CONNECTION_RESET": "连接重置", "net::ERR_CONNECTION_REFUSED": "连接拒绝",
                "net::ERR_CERT_AUTHORITY_INVALID": "证书异常", "net::ERR_CERT_DATE_INVALID": "证书异常",
                "net::ERR_SSL_PROTOCOL_ERROR": "TLS异常",
            }.get(request.failure, "网络请求失败")
            self.network_issue(request, code)
        except Exception:
            pass  # 不记录 URL、请求正文、网络错误原文或异常原文。

    def network_response(self, response):
        try:
            status = response.status
            if type(status) is int and 400 <= status <= 599:
                self.network_issue(response.request, f"HTTP {status}")
        except Exception:
            pass

    def poll(self):
        request, self.finished = self.finished, None
        if self.closed or request is None or request is not self.latest:
            return
        try:
            response = request.response()
            if self.closed or request is not self.latest or response is None:
                return
            status = int(response.status)
            elapsed_ms = max(0, int((self.finished_at - self.started) * 1000))
            payload = None
            business_rejected = False
            if 200 <= status < 300:
                payload = response.json()
                if self.closed or request is not self.latest:
                    return
                wrapped = isinstance(payload, dict) and "code" in payload
                code = payload.get("code") if wrapped else None
                business_ok = type(code) is int and code == 0
                business_rejected = wrapped and not business_ok
                if not business_rejected:
                    data = payload.get("data") if wrapped else payload
                    data = data if isinstance(data, dict) else {}
                    user = data.get("user")
                    user = user if isinstance(user, dict) else {}
                    token_present = isinstance(data.get("token"), str) and bool(data["token"].strip())
                    user_present = bool(user.get("id"))
                    account_username = _piggo_account(self.ctx)[0] if self.ctx is not None else ""
                    username_matches = bool(account_username) and isinstance(user.get("username"), str) and \
                        user["username"].casefold() == account_username.casefold()
                    proof_present = isinstance(data.get("m2"), str) and bool(data["m2"].strip())
                    self.failure = "HTTP 200，业务结果尚未确认" if not business_ok else ""
                    _runtime_log(
                        self.ctx,
                        f"官网登录完整回执：HTTP {status}，业务成功标记={'有' if business_ok else '无'}，"
                        f"会话字段={'有' if token_present else '无'}，用户资料={'有' if user_present else '无'}，"
                        f"账号匹配={'是' if username_matches else '否'}，服务端证明={'有' if proof_present else '无'}；"
                        "仍需核对页面实际登录状态（不记录正文）",
                        site="猪猪",
                    )
                    return
            elif status < 400:
                return
            category = "官网业务校验未通过" if business_rejected else "未提供可识别的拒绝原因"
            if status == 422 or business_rejected:
                if payload is None:
                    payload = response.json()
                if self.closed or request is not self.latest:
                    return
                if isinstance(payload, dict):
                    data = payload.get("data")
                    marked = payload.get("site_captcha") is True or \
                        (isinstance(data, dict) and data.get("site_captcha") is True)
                    # 与官网的嵌套回执格式一致；仅输出固定分类，绝不输出响应原文。
                    nested = data if isinstance(data, dict) else {}
                    reason = next((value.strip() for value in (
                        nested.get("msg"), nested.get("message"), payload.get("msg"), payload.get("message"),
                    ) if isinstance(value, str) and value.strip()), "")
                    if marked or isinstance(reason, str) and reason in {
                        "请完成人机验证", "人机验证失败", "请重新完成人机验证", "验证码错误", "验证码已过期",
                    }:
                        category = "官网要求登录验证"
                    elif isinstance(reason, str) and reason in {
                        "用户名或密码错误", "账号或密码错误", "密码错误", "账号不存在", "账户已锁定",
                    }:
                        category = "官网拒绝账号认证"
                    elif isinstance(reason, str) and reason in {
                        "会话无效", "会话已过期", "登录会话已过期", "挑战已过期", "挑战无效", "ticket expired",
                    }:
                        category = "官网登录挑战或会话已失效"
                    elif isinstance(payload.get("errors"), (dict, list)):
                        category = "官网返回字段校验错误"
            if self.closed or request is not self.latest:
                return
            self.failure = f"HTTP {status}，{category}"
            _runtime_log(self.ctx, f"官网登录完整回执：{self.failure}；请求耗时 {elapsed_ms}ms（不记录正文）",
                         level="warning", site="猪猪")
        except Exception as exc:
            _runtime_log(self.ctx, f"官网登录回执分类未完成（{type(exc).__name__}），继续等待官网结果",
                         level="warning", site="猪猪")

    def close(self):
        self.closed = True
        self.latest = self.finished = None
        for event, callback in (("request", self.requested), ("requestfinished", self.completed),
                                ("requestfailed", self.network_failed), ("response", self.network_response)):
            try:
                self.page.remove_listener(event, callback)
            except Exception:
                pass


def _piggo_log_login_timeout(page, ctx, username, observation) -> None:
    """超时只记录固定分类与布尔值，不保存页面、截图或凭据，不参与成功判定。"""
    try:
        parsed = urlparse(page.url)
        if parsed.scheme != "https" or parsed.hostname not in {"piggo.me", "www.piggo.me"} \
                or parsed.port not in {None, 443} or parsed.username is not None or parsed.password is not None:
            raise ValueError("untrusted page")
        path = (parsed.path or "/").rstrip("/").lower()
        route = "日历页" if path == "/calendar" else (
            "登录页" if path in {"/login", "/login.php", "/takelogin.php"} else "其他站内页")
        data = page.evaluate("""() => {
            // 只读取当前状态，不调用站点内部函数，不修改存储或发起请求。
            if (location.protocol !== 'https:' || !['piggo.me', 'www.piggo.me'].includes(location.hostname) ||
                !['', '443'].includes(location.port) || location.username || location.password) return null;
            const visible = selector => Array.from(document.querySelectorAll(selector)).some(el => {
                const style = getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden' &&
                    style.visibility !== 'collapse' &&
                    Array.from(el.getClientRects()).some(rect => rect.width > 0 && rect.height > 0);
            });
            let user = null, session = null, userReadable = false;
            try {
                user = JSON.parse(localStorage.getItem('pig_user') || 'null');
                userReadable = user === null || typeof user === 'object' && !Array.isArray(user);
            } catch (_) {}
            try {
                const token = localStorage.getItem('pig_token');
                session = typeof token === 'string' && !!token.trim() && token !== '********';
            } catch (_) {}
            const text = document.body?.innerText || '';
            return {
                ready: document.readyState,
                loginForm: !!document.querySelector('form input#username'),
                loginVisible: visible('form input#username'),
                calendar: !!document.querySelector('.cal-page .cal-att'),
                calendarVisible: visible('.cal-page .cal-att'),
                dialogVisible: visible('[role="dialog"], dialog[open]'),
                captchaVisible: visible('.site-cap[role="dialog"][aria-label="人机验证"], .captcha-row, .site-captcha, input[name="otp"], input[name="totp"]'),
                locked: text.includes('页面已锁定') && text.includes('空闲过久'),
                hasSession: session,
                userReadable: userReadable,
                userPresent: !!(user && typeof user === 'object' && user.id),
                username: user && typeof user.username === 'string' ? user.username : null
            };
        }""")
        current = urlparse(page.url)
        if (current.scheme, current.hostname, current.port, current.username, current.password, current.path) != \
                (parsed.scheme, parsed.hostname, parsed.port, parsed.username, parsed.password, parsed.path):
            raise ValueError("page changed during snapshot")
        if not isinstance(data, dict):
            raise ValueError("unavailable snapshot")
        ready = {"loading": "加载中", "interactive": "DOM就绪", "complete": "加载完成"}.get(data.get("ready"), "未知")

        def flag(key):
            value = data.get(key)
            return "是" if value is True else ("否" if value is False else "未知")

        actual = data.get("username")
        match = "未知" if not isinstance(actual, str) else ("是" if actual.casefold() == username.casefold() else "否")
        _runtime_log(ctx, f"登录超时页面诊断：页面={route}，加载={ready}，登录表单={flag('loginForm')}/可见={flag('loginVisible')}，"
                     f"日历={flag('calendar')}/可见={flag('calendarVisible')}，弹窗={flag('dialogVisible')}，"
                     f"人机验证={flag('captchaVisible')}，空闲锁定={flag('locked')}", level="warning", site="猪猪")
        _runtime_log(ctx, f"登录超时会话诊断：会话字段={flag('hasSession')}，资料可读={flag('userReadable')}，用户资料={flag('userPresent')}，"
                     f"账号匹配={match}；仅用于排查，不代表已登录或已签到", level="warning", site="猪猪")
    except Exception:
        _runtime_log(ctx, "登录超时页面诊断：页面状态读取失败（可能正在跳转或窗口已关闭），不推断登录结果",
                     level="warning", site="猪猪")
    issues = sorted(observation.network_issues)
    _runtime_log(ctx, "登录期间网络诊断：" + ("；".join(issues) if issues else "未捕获关键请求失败") +
                 "（仅作排查，不代表失败根因）", level="warning", site="猪猪")


def _piggo_ensure_login(page, ctx, loop) -> tuple[str, str] | None:
    if ctx is None:
        return
    observation = _PiggoLoginObservation(page, ctx)
    try:
        return _piggo_ensure_login_flow(page, ctx, loop, observation)
    finally:
        observation.close()


def _piggo_ensure_login_flow(page, ctx, loop, observation) -> tuple[str, str] | None:
    """仅通过官网原生登录表单获取凭证，每轮最多提交一次登录。"""
    if ctx is None:
        return
    username, password = _piggo_account(ctx)
    if not username or not password:
        raise RuntimeError("猪猪尚未填写完整的用户名和密码，请在插件配置中填写并保存")
    submitted = False
    calendar_navigated = False
    expected = (username, password)

    def guard():
        if getattr(ctx, "_closed", False) or _piggo_account(ctx) != expected:
            raise RuntimeError("猪猪配置已变更或插件已停用，本轮跳过")
        try:
            parsed = urlparse(page.url)
            valid = parsed.scheme == "https" and parsed.hostname in {"piggo.me", "www.piggo.me"} \
                and parsed.port in {None, 443} and parsed.username is None and parsed.password is None
        except Exception:
            valid = False
        if not valid:
            raise RuntimeError("猪猪登录跳转到了非预期地址，未发送账号密码，本轮跳过")
        return parsed

    # 猪猪使用全新上下文，只以官网原生账号密码登录；不恢复旧 Token 或空闲锁定状态。
    deadline = time.monotonic() + 40
    navigation_logged = False
    for _ in range(320):
        try:
            guard()
            observation.poll()
            parsed = guard()
            if time.monotonic() >= deadline:
                break
            path = (parsed.path or "/").rstrip("/").lower()
            calendar = page.locator(".cal-page .cal-att")
            if path == "/calendar" and calendar.count() and calendar.first.is_visible():
                actual = page.evaluate("""() => {
                    try { return JSON.parse(localStorage.getItem('pig_user') || '{}').username || ''; }
                    catch (_) { return ''; }
                }""")
                # 日历和用户资料异步加载；不把空资料、后台实时连接或隐藏骨架当成登录成功。
                if not isinstance(actual, str) or not actual.strip():
                    page.wait_for_timeout(500)
                    continue
                if actual.casefold() != username.casefold():
                    raise RuntimeError("猪猪当前登录账号与所填用户名不一致，本轮跳过")
                token = page.evaluate("() => localStorage.getItem('pig_token') || ''")
                if not isinstance(token, str) or not token.strip() or token == "********":
                    raise RuntimeError("猪猪登录后未建立有效会话，本轮跳过")
                guard()
                _runtime_log(ctx, "官网账号密码登录成功，仅使用本轮浏览器会话", site="猪猪")
                return expected
            if path in {"/login", "/login.php", "/takelogin.php"}:
                captcha = page.locator(".captcha-row, .site-captcha, input[name='otp'], input[name='totp']")
                if any(captcha.nth(index).is_visible() for index in range(captcha.count())):
                    raise RuntimeError("猪猪登录需要验证码或二次验证，本轮未继续提交；请先在官网确认验证要求")
                text = _page_text(page)
                if submitted and any(marker in text for marker in ("用户名或密码错误", "密码错误", "账号不存在", "登录失败", "账户已锁定")):
                    raise RuntimeError("猪猪自动登录失败，请检查账号密码或网站登录限制，本轮跳过")
                if not submitted:
                    # CloakBrowser humanize 不支持 locator 链产生的 >>，交互使用单一 CSS。
                    form_selector = 'form:has(input#username):has(input#password)'
                    form = page.locator(form_selector)
                    if form.count() == 1:
                        submit = page.locator(f"{form_selector} button.btn").first
                        if submit.count() and submit.is_visible() and submit.is_enabled() \
                                and submit.inner_text().strip() == "登录":
                            try:
                                guard()
                                page.locator(f"{form_selector} input#username").fill(username)
                                guard()
                                page.locator(f"{form_selector} input#password").fill(password)
                                guard()
                                if time.monotonic() >= deadline:
                                    break
                                submitted = True
                                deadline = time.monotonic() + 120
                                _runtime_log(ctx, "正在提交官网登录表单，仅提交一次，提交后最多等待 120 秒", site="猪猪")
                                submit.click(timeout=10_000)
                            except Exception as exc:
                                # Playwright 的原始 fill 错误可能含凭据值，不能向日志透传。
                                if not submitted:
                                    guard()
                                    raise RuntimeError("猪猪登录表单填写失败，本轮跳过") from None
                                _runtime_log(ctx, f"官网登录表单操作未确认（{type(exc).__name__}），等待原生登录结果，不重复提交", level="warning", site="猪猪")
            elif path != "/calendar" and not calendar_navigated:
                # 登录页可能落回首页，而不是遵循 redirect 参数；有凭证后只导航一次。
                token = page.evaluate("() => localStorage.getItem('pig_token') || ''")
                if token:
                    calendar_navigated = True
                    page.goto("https://piggo.me/calendar", wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(500)
        except Exception as exc:
            # 原生登录/路由可能触发整页跳转；只容忍明确的临时导航错误。
            # 不吞掉关闭窗口、身份变更、认证拒绝或填写凭据失败，也不再次提交登录。
            message = str(exc)
            transient = any(marker in message for marker in (
                "Execution context was destroyed", "Cannot find context with specified id",
                "Unable to retrieve content because the page is navigating",
            ))
            if not transient:
                raise
            guard()
            if not navigation_logged:
                _runtime_log(ctx, "官网登录页面正在跳转，等待页面加载后再确认，不重复提交", site="猪猪")
                navigation_logged = True
            if time.monotonic() >= deadline:
                break
            page.wait_for_timeout(500)
    # 日历可能被强制阅读公告或未完成的数据加载阻塞。只改进失败诊断，
    # 不放宽上面的登录确认门槛，更不把会话字段当作签到成功凭据。
    parsed = guard()
    _piggo_log_login_timeout(page, ctx, username, observation)
    parsed = guard()
    if (parsed.path or "/").rstrip("/").lower() == "/calendar":
        try:
            state = page.evaluate("""() => {
                let user = {};
                try { user = JSON.parse(localStorage.getItem('pig_user') || '{}'); } catch (_) {}
                const text = document.body?.innerText || '';
                const token = localStorage.getItem('pig_token');
                return {
                    username: user?.id && typeof user.username === 'string' ? user.username : '',
                    hasSession: typeof token === 'string' && !!token.trim() && token !== '********',
                    locked: text.includes('页面已锁定') && text.includes('空闲过久'),
                    loginForm: !!document.querySelector('form input#username')
                };
            }""")
        except Exception:
            state = None  # 页面已关闭或正在导航时，不凭历史状态推断已认证。
        guard()
        if isinstance(state, dict) and state.get("hasSession") is True \
                and state.get("locked") is False and state.get("loginForm") is False \
                and isinstance(state.get("username"), str) \
                and state["username"].casefold() == username.casefold():
            raise RuntimeError("猪猪账号已登录，但日历页面未加载完成；请在官网检查是否有强制阅读公告并手动确认，本轮未签到")
    detail = f"（{observation.failure}）" if observation.failure else ""
    raise RuntimeError(f"猪猪自动登录未完成{detail}，本轮跳过；未重复提交登录")


def _custom_sites(cfg: dict | None = None) -> dict[str, dict]:
    """Build stable runtime definitions for user-added generic PT sites."""
    raw = (cfg or {}).get("custom_sites", []) if isinstance(cfg, dict) else []
    if not isinstance(raw, list):
        return {}
    result: dict[str, dict] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        raw_url = str(item.get("url") or "").strip()
        if not re.match(r"^https?://", raw_url, re.I):
            continue
        parsed = urlparse(raw_url)
        domain = (parsed.hostname or "").lower().strip(".")
        if domain.startswith("www."):
            domain = domain[4:]
        if not domain or domain == "audiences.me" or domain.endswith(".audiences.me"):
            continue
        # name is intentionally user-controlled (it can be a site name or account label).
        name = str(item.get("name") or item.get("username") or domain).strip()[:80]
        key_seed = f"{name}\x00{raw_url}".encode("utf-8", "ignore")
        key = "custom_" + hashlib.sha1(key_seed).hexdigest()[:12]
        result[key] = {
            "name": name,
            "domain": domain,
            "url": raw_url,
            "mode": "generic",
            "generic": True,
            "group": "通用签到",
        }
    return result


def _configured_sites(cfg: dict | None = None) -> dict[str, dict]:
    configured = dict(SITES)
    configured.update(_custom_sites(cfg))
    return configured


def _task_done(task: asyncio.Task) -> None:
    global _active_run_task
    _tasks.discard(task)
    # 排队任务可能先于上一轮的 done 回调拿到锁，旧回调不能覆盖新一轮状态。
    if _active_run_task is not task:
        return
    _active_run_task = None
    if task.cancelled():
        _state.update({"running": False, "phase": "已取消", "message": "签到任务已取消", "current": ""})
        return
    try:
        error = task.exception()
    except Exception as exc:  # noqa: BLE001
        error = exc
    if error:
        _state.update({"running": False, "phase": "异常", "message": f"后台任务异常：{error}", "current": ""})


async def _run_scheduled(ctx, source: str, selected: list[str]) -> dict:
    """Keep a scheduled run alive if its callback times out while waiting."""
    task = _scheduled_tasks.get(source)
    if task is None or task.done():
        try:
            task = ctx.create_task(
                _run(ctx, source, list(selected), wait_for_lock=True),
                name=f"PT站{source}签到",
            )
        except Exception as exc:  # noqa: BLE001
            message = f"{source}签到任务提交失败：{str(exc).strip() or type(exc).__name__}"
            _runtime_log(ctx, message, level="error")
            return {"ok": False, "message": message}
        _scheduled_tasks[source] = task
        _tasks.add(task)

        def done(finished: asyncio.Task) -> None:
            if _scheduled_tasks.get(source) is finished:
                _scheduled_tasks.pop(source, None)
            _task_done(finished)
            if not finished.cancelled() and finished.exception() is not None:
                error = finished.exception()
                _runtime_log(ctx, f"{source}签到异常：{str(error).strip() or type(error).__name__}", level="error")

        task.add_done_callback(done)
        if _run_lock and _run_lock.locked():
            _runtime_log(ctx, f"{source}签到已到点，已排队，上一轮结束后自动执行")
        else:
            _runtime_log(ctx, f"{source}签到已到点，任务已提交")
    else:
        _runtime_log(ctx, f"{source}签到已有待完成任务，不重复创建，等待同一任务结果")

    # 回调本身仍返回实际结果。平台只取消超时的回调时保留已登记的任务；
    # 停用/重载则由 ctx.create_task 的生命周期托管及 teardown 统一取消。
    return await asyncio.shield(task)


def _schedule_failed_retry(ctx, failed_keys: list[str]) -> bool:
    """Schedule one delayed, single-attempt pass for each failed site."""
    configured = _configured_sites(_cfg(ctx))
    batch = tuple(dict.fromkeys(
        str(key) for key in failed_keys
        if str(key) in configured and not (
            _failed_retry_tasks.get(str(key)) is not None
            and not _failed_retry_tasks[str(key)].done()
        )
    ))
    if not batch:
        _runtime_log(ctx, "没有需要安排补签的有效站点，不重复安排")
        return False

    names = [configured[key]["name"] for key in batch if key in configured]
    label = "、".join(names) or "、".join(batch)

    async def delayed_retry() -> dict:
        _runtime_log(ctx, f"失败站点将在 30 分钟后仅补签一次：{label}", level="warning")
        await asyncio.sleep(_FAILED_RETRY_DELAY_SECONDS)
        _runtime_log(ctx, f"开始失败站点补签，仅处理：{label}")
        result = await _run(
            ctx,
            "失败站点补签",
            list(batch),
            schedule_failed_retry=False,
            wait_for_lock=True,
            retry_count_override=0,
        )
        _runtime_log(
            ctx,
            "失败站点补签已结束，不再继续安排重试",
            level="success" if result.get("ok") else "warning",
        )
        return result

    task = ctx.create_task(delayed_retry(), name="PT站失败站点30分钟补签")
    for key in batch:
        _failed_retry_tasks[key] = task
    _tasks.add(task)

    def done(finished: asyncio.Task) -> None:
        for key in batch:
            if _failed_retry_tasks.get(key) is finished:
                _failed_retry_tasks.pop(key, None)
        _task_done(finished)

    task.add_done_callback(done)
    return True


def _bounded(value, default: int, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


async def _site_cookie(ctx, key: str, site: dict) -> tuple[str, str]:
    piggo = _same_site_domain(site["domain"], "piggo.me")
    if piggo:
        # 账号密码模式不读取平台 Cookie 或旧 Token，避免带入官网的空闲锁定会话。
        return ("", "") if all(_piggo_account(ctx)) else ("", "猪猪尚未填写完整的用户名和密码，请在插件配置中填写并保存")
    cookies = getattr(ctx, "cookies", None)
    if cookies is None or not callable(getattr(cookies, "get", None)):
        return "", "平台 Cookie 同步未启用"
    parsed = urlparse(site["url"])
    path = parsed.path or "/"
    domain = site["domain"].lower()
    url_host = (parsed.hostname or domain).lower()
    hosts = list(dict.fromkeys((url_host, domain, domain[4:] if domain.startswith("www.") else f"www.{domain}")))
    last_error = ""
    auth_cookie_missing = False
    for host in hosts:
        try:
            if key in {"opencd", "ourbits"}:
                try:
                    items = await ctx.cookies.get(host, path=path)
                except TypeError:
                    items = await ctx.cookies.get(host)
                names = {str(item.get("name") or "").lower() for item in items}
                non_login = names and all(
                    name.startswith(("_ga", "_gid", "_gat", "_fbp"))
                    or name in {"cf_clearance", "__cf_bm", "cf_chl_2", "sl-session", "sl-challenge-server"}
                    for name in names
                )
                if non_login:
                    auth_cookie_missing = True
                    continue
            try:
                cookie = await ctx.cookies.header(host, path=path)
            except TypeError:
                cookie = await ctx.cookies.header(host)
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            continue
        if cookie:
            return cookie, ""
    for host in hosts:
        try:
            await ctx.cookies.request_sync(host)
        except Exception:
            continue
    for host in hosts:
        try:
            if key in {"opencd", "ourbits", "piggo"}:
                try:
                    items = await ctx.cookies.get(host, path=path)
                except TypeError:
                    items = await ctx.cookies.get(host)
                names = {str(item.get("name") or "").lower() for item in items}
                non_login = names and all(
                    name.startswith(("_ga", "_gid", "_gat", "_fbp"))
                    or name in {"cf_clearance", "__cf_bm", "cf_chl_2", "sl-session", "sl-challenge-server"}
                    for name in names
                )
                if non_login:
                    auth_cookie_missing = True
                    continue
            try:
                cookie = await ctx.cookies.header(host, path=path)
            except TypeError:
                cookie = await ctx.cookies.header(host)
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            continue
        if cookie:
            return cookie, ""
    if last_error:
        return "", f"读取平台 Cookie 失败：{last_error}"
    if auth_cookie_missing:
        return "", "平台只有该站安全验证/统计 Cookie，没有登录会话；请在 CookieCloud 来源浏览器重新登录网站并同步"
    return "", "平台中没有该站 Cookie，请登录网站并同步"


async def _refresh_site_cookie(ctx, key: str, site: dict) -> tuple[str, str]:
    """要求平台刷新指定站点 Cookie；不在插件配置或存储中保留 Cookie。"""
    parsed = urlparse(site["url"])
    domain = site["domain"].lower()
    url_host = (parsed.hostname or domain).lower()
    hosts = list(dict.fromkeys((url_host, domain, domain[4:] if domain.startswith("www.") else f"www.{domain}")))
    for host in hosts:
        try:
            await ctx.cookies.request_sync(host)
        except Exception:
            continue
    return await _site_cookie(ctx, key, site)


def _page_text(page) -> str:
    try:
        return page.locator("body").inner_text(timeout=10_000)
    except Exception:
        return page.content()


def _html_visible_text(html: str) -> str:
    """提取服务端页面的可见文本，排除脚本中的提示语和翻译文案。"""
    soup = BeautifulSoup(html or "", "html.parser")
    for node in soup.select("script, style, template, noscript"):
        node.decompose()
    for node in soup.find_all(True):
        attrs = node.attrs or {}
        style = str(attrs.get("style") or "").replace(" ", "").lower()
        classes = " ".join(str(value) for value in (attrs.get("class") or []))
        if (
            attrs.get("hidden") is not None
            or str(attrs.get("aria-hidden") or "").lower() == "true"
            or "display:none" in style
            or "visibility:hidden" in style
            or re.search(r"(?:^|\s)(?:hidden|d-none|invisible)(?:\s|$)", classes, re.IGNORECASE)
        ):
            node.decompose()
    return soup.get_text("\n", strip=True)


def _result_state(text: str, *, confirmed: bool = False) -> tuple[str, str] | None:
    """只根据明确的站点反馈判断结果，避免把普通 200 页面误报为成功。"""
    low = (text or "").lower()
    already_markers = (
        "今日已签到", "今天已签到", "今日已经签到", "今天已经签到", "今日签到已完成", "今天签到已完成",
        "already attended", "already signed", "attended today", "already checked in",
    )
    success_markers = [
        "本次签到获得", "此次签到获得", "签到获得", "签到奖励",
        "attend got", "attend get bonus", "attend get bouns",
        "attendance success", "check-in successful", "checked in successfully",
    ]
    if confirmed:
        success_markers.extend(("签到成功", "成功签到"))
    failure_markers = (
        "签到失败", "操作频繁", "验证失败", "请求失败", "稍后再试",
        "attendance failed", "check-in failed", "too many requests", "rate limit",
    )
    if any(marker in low for marker in already_markers):
        return "already", "今天已经签到"
    if any(marker in low for marker in success_markers):
        return "success", "签到成功"
    if any(marker in low for marker in failure_markers):
        return "failed", "网站返回签到失败、验证失败或操作频繁"
    return None


def _nexus_result_state(text: str) -> tuple[str, str] | None:
    """NexusPHP 签到回执不一定包含“签到成功”。"""
    compact = re.sub(r"\s+", "", text or "").lower()
    if any(marker in compact for marker in ("签到失败", "验证失败", "操作频繁", "请稍后再试")):
        return "failed", "网站返回签到失败、验证失败或操作频繁"
    if any(marker in compact for marker in (
        "今日已签到", "今天已签到", "今日已经签到", "今天已经签到",
        "今日已经签到过", "今天已经签到过", "今日不能重复签到", "今天不能重复签到", "请勿重复签到",
    )):
        return "already", "今天已经签到"
    if any(marker in compact for marker in (
        "签到成功", "本次签到获得", "此次签到获得", "签到所得", "今日签到排名",
        "本次签到获得了", "签到已得", "已连续签到",
    )) or re.search(r"这是您的(?:首次|第\d+次)签到", compact):
        return "success", "签到成功"
    return None


def _hhan_result_state(html: str) -> tuple[str, str] | None:
    """HHanClub 会反复展示最近一次奖励，须以当天记录创建时间区分本次与已签到。"""
    today = datetime.now(_CHINA_TZ).strftime("%Y-%m-%d")
    match = re.search(rf'"{re.escape(today)}"\s*:\s*(\{{[^}}]+\}})', html or "")
    if not match:
        return None
    try:
        record = json.loads(match.group(1))
        created = datetime.strptime(str(record.get("created_at") or ""), "%Y-%m-%d %H:%M:%S").replace(tzinfo=_CHINA_TZ)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    age = (datetime.now(_CHINA_TZ) - created).total_seconds()
    if -30 <= age <= 180:
        return "success", "签到成功"
    return "already", "今天已经签到"


def _u2_result_state(text: str, *, submitted: bool = False) -> tuple[str, str] | None:
    """识别 U2 的最终签到状态；不把未签到时的 Show Up 菜单当成成功。"""
    raw = text or ""
    visible = _html_visible_text(raw)
    compact = re.sub(r"\s+", "", visible).lower()
    # U2 的验证题答错仍会完成当日签到并发放 1 UCoin。
    # 必须在 Wrong answer 等通用错误词之前识别这类成功回执。
    challenge_form_present = bool(re.search(r'name\s*=\s*["\']req["\']', raw, re.IGNORECASE))
    award_match = re.search(r"(\d+(?:\.\d+)?)\s*ucoin", compact, re.IGNORECASE)
    correct_answer = bool(re.search(
        r"(?:回答|答案)(?:正确|正確)\s*[!！]", visible, re.IGNORECASE
    ))
    actual_wrong_answer = bool(re.search(
        r"(?:回答|答案)(?:错误|錯誤)(?=\s*(?:[!！,，。:：]|获得|獲得|$))",
        compact,
        re.IGNORECASE,
    )) or any(marker in compact for marker in ("wronganswer", "incorrectanswer"))
    if correct_answer:
        return "success", "签到成功（回答正确）"
    wrong_but_awarded = (
        not challenge_form_present
        and actual_wrong_answer
        and award_match is not None
    )
    if wrong_but_awarded:
        return "success", f"签到成功（回答错误，获得 {award_match.group(1)} UCoin）"
    if submitted and actual_wrong_answer:
        return "success", "签到成功（回答错误，获得 1 UCoin）"
    if any(marker in compact for marker in (
        "签到失败", "簽到失敗", "验证失败", "驗證失敗", "invalidcaptcha", "captchaexpired",
        "请求已过期", "請求已過期", "操作频繁", "操作頻繁", "请稍后再试", "請稍後再試",
    )) or actual_wrong_answer or re.search(r'"status"\s*:\s*"error"', raw, re.IGNORECASE):
        return "failed", "U2 未接受本次签到验证答案"
    if re.search(r"[\[【]\s*(?:已签到|已簽到)\s*[\]】]", visible, re.IGNORECASE) or any(marker in compact for marker in (
        "感谢，今天已签到", "感謝，今天已簽到", "今天已经签到", "今天已經簽到",
        "今日已签到", "今日已簽到", "已完成签到", "已完成簽到",
        "alreadyshoweduptoday", "alreadycheckedintoday", "youhaveshoweduptoday",
    )) or re.search(r'"status"\s*:\s*"already"', raw, re.IGNORECASE):
        return "already", "今天已经签到"
    if any(marker in compact for marker in (
        "签到成功", "簽到成功", "成功签到", "成功簽到", "showupsuccess", "check-insuccess",
        "thankyouforshowingup", "thanksforshowingup",
    )) or re.search(r'"status"\s*:\s*"(?:success|ok)"', raw, re.IGNORECASE) \
            or re.search(r'"success"\s*:\s*true', raw, re.IGNORECASE) \
            or re.search(r"window\.location(?:\.href)?\s*=\s*['\"]showup\.php", raw, re.IGNORECASE):
        return "success", "签到成功"
    return None


def _u2_submit_with_browser(page, submit) -> str:
    """使用真实浏览器表单提交 U2 验证，避免 fetch/XHR 被站点 WAF 拒绝。"""
    submit.evaluate("""element => {
        const form = element.form;
        if (!form) throw new Error('submit control has no form');
        const message = form.querySelector('[name="message"]');
        if (message && !String(message.value || '').trim()) {
            message.value = '一切随缘~';
            message.dispatchEvent(new Event('input', {bubbles: true}));
            message.dispatchEvent(new Event('change', {bubbles: true}));
        }
        if (typeof form.requestSubmit === 'function') {
            form.requestSubmit(element);
            return;
        }
        if (element.name) {
            const hidden = document.createElement('input');
            hidden.type = 'hidden';
            hidden.name = element.name;
            hidden.value = element.value || '';
            form.appendChild(hidden);
        }
        form.submit();
    }""")
    try:
        page.wait_for_load_state("domcontentloaded", timeout=30_000)
    except Exception:
        # 页面可能在原文档内直接渲染结果；继续读取当前 DOM 进行严格判定。
        pass
    page.wait_for_timeout(1_000)
    return page.content()


def _ttg_result_state(text: str) -> tuple[str, str] | None:
    """兼容 TTG HTML、纯文本和 JSON 三类签到回执。"""
    raw = text or ""
    compact = re.sub(r"\s+", "", _html_visible_text(raw)).lower()
    if any(marker in compact for marker in (
        "签到失败", "簽到失敗", "操作频繁", "请稍后再试", "signfailed",
    )):
        return "failed", "网站返回签到失败"
    if re.search(r"\[\s*已签到\s*\]", raw, re.IGNORECASE) or any(marker in compact for marker in (
        "今天已签到过", "今日已签到", "今天已经签到", "alreadysigned",
    )):
        return "already", "今天已经签到"
    if any(marker in compact for marker in (
        "您已连续签到", "签到成功", "簽到成功", "signsuccess", "signedsuccessfully",
    )) or re.search(r'"(?:success|status)"\s*:\s*(?:true|1|200)', raw, re.IGNORECASE) \
            or re.search(r'"code"\s*:\s*(?:0|200)', raw, re.IGNORECASE):
        return "success", "签到成功"
    return None


def _site_result_state(text: str, expected_domain: str = "", *, confirmed: bool = False) -> tuple[str, str] | None:
    if expected_domain.lower() == "piggo.me":
        # 新日历长期展示累计天数和历史记录，不能使用 NexusPHP 的宽泛文字判定。
        return None
    if expected_domain.lower() in {"audiences.me", "ourbits.club", "hhanclub.net"}:
        return _nexus_result_state(text)
    return _result_state(text, confirmed=confirmed)


def _hdsky_already(text: str) -> bool:
    """天空以首页导航的方括号标签表示当天已签到。"""
    return bool(re.search(r"\[\s*(?:已签到|已簽到)\s*\]", text or "", re.IGNORECASE))


def _same_site_domain(current: str, expected: str) -> bool:
    """www 与根域视为同一站点，不放宽到其他子域。"""
    return current.lower().removeprefix("www.") == expected.lower().removeprefix("www.")


def _refreshed_cookie_header(page, expected_domain: str) -> str:
    """读取浏览器刷新后的同站 Cookie；调用方只允许保存在进程内。"""
    expected = expected_domain.lower().lstrip(".").removeprefix("www.")
    try:
        cookies = page.context.cookies()
    except Exception:
        return ""
    pairs = []
    for item in cookies or []:
        domain = str(item.get("domain") or "").lower().lstrip(".").removeprefix("www.")
        name = str(item.get("name") or "")
        if domain == expected and name:
            pairs.append(f"{name}={item.get('value', '')}")
    return "; ".join(pairs)


def _seed_browser_cookie_jar(page, cookie_header: str, url: str) -> None:
    """把平台 Cookie Header 写入浏览器 Cookie Jar，确保安全验证跳转后仍保留登录态。"""
    items = []
    for part in str(cookie_header or "").split(";"):
        name, separator, value = part.strip().partition("=")
        if separator and name:
            items.append({"name": name, "value": value, "url": url})
    if not items:
        return
    page.context.add_cookies(items)
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)


def _captcha_error(text: str) -> str:
    low = (text or "").lower()
    if any(marker in low for marker in (
        "签到验证码", "请选择与左侧图片对应", "回答正确将获得", "回答错误将反向扣除",
    )):
        return "网站要求完成签到图片验证码，需要人工签到，本插件不会自动提交答案"
    if any(marker in low for marker in (
        "turnstile", "hcaptcha", "recaptcha", "交互式验证码",
    )):
        return "网站要求完成交互式验证码，需要人工处理"
    return ""


def _retryable_error(exc: Exception) -> bool:
    text = str(exc).lower()
    permanent = (
        "cookie", "登录页", "人工签到", "人工处理", "验证码", "没有访问权限",
        "非预期域名", "格式不正确", "bot 未连接", "主人 id",
        "等待 telegram", "签到选项", "验证题已变化", "cloakbrowser 等待超过", "本轮跳过",
        "turnstile", "猪猪登录 token", "pig_token",
    )
    return not any(marker in text for marker in permanent)


def _turnstile_session_retryable(key: str, exc: Exception) -> bool:
    """Turnstile 站点可通过关闭当前会话并更换全新指纹恢复的错误。"""
    if key not in {"audiences", "ourbits"}:
        return False
    text = str(exc).lower()
    return any(marker in text for marker in (
        "turnstile",
        "cloakbrowser 60 秒内没有取得页面结果",
        "cloakbrowser 90 秒内没有取得页面结果",
        "cloudflare/雷池验证等待超时",
    ))


def _ai_available(ctx, capability: str) -> bool:
    return bool(ctx.ai.is_available(capability))


def _radio_label(item) -> str:
    """读取单选项可见文案，兼容 label[for]、包裹式 label 和表格布局。"""
    try:
        return str(item.evaluate("""el => {
            const direct = el.labels && el.labels.length ? el.labels[0].innerText : '';
            if (direct.trim()) return direct.trim();
            const wrapped = el.closest('label');
            if (wrapped && wrapped.innerText.trim()) return wrapped.innerText.trim();
            const cell = el.closest('td,li,div');
            return cell ? cell.innerText.trim() : (el.value || '');
        }""") or "").strip()
    except Exception:
        return str(item.get_attribute("value") or "").strip()


async def _send_tjupt_question(ctx, token: str, image_path: Path, options: list[str]) -> None:
    suggestion = "平台未配置视觉模型，请根据海报手动选择。"
    if ctx.config.get("tjupt_ai_assist", True) and _ai_available(ctx, "vision"):
        try:
            suggestion = str(await ctx.ai.vision(
                image=image_path.read_bytes(),
                prompt=(
                    "这是 TJUPT 的影视海报选择题。请观察图片，在下列候选项中给出最可能的一个，"
                    "同时简短说明依据和置信度。不要编造候选项。\n候选项：\n"
                    + "\n".join(f"{index + 1}. {label}" for index, label in enumerate(options))
                ),
                system="你是谨慎的影视海报识别助手。答案不确定时必须明确说明。",
            ) or "AI 未返回建议")
        except Exception as exc:  # noqa: BLE001
            ctx.log.warning("TJUPT AI 识图失败：%r", exc)
            suggestion = f"AI 识图失败：{exc.__class__.__name__}，请手动选择。"

    rows = [[Button.inline(f"{index + 1}. {label}"[:60], f"pttj:{token}:{index}".encode())]
            for index, label in enumerate(options)]
    caption = (
        "🎬 TJUPT 签到验证\n\n"
        f"AI 建议：{suggestion[:700]}\n\n"
        "请核对海报后点击一个候选答案；插件只会提交你点击的选项。"
    )
    owner_id = int(str(getattr(ctx.settings, "default_bot_chat_id", "") or 0))
    if ctx.bot is None or not ctx.bot.is_connected() or not owner_id:
        raise RuntimeError("平台 Bot 未连接或未配置主人 ID，无法发送 TJUPT 确认按钮")
    await ctx.bot.send_file(owner_id, str(image_path), caption=caption, buttons=rows)


def _tjupt_visual_payload(page, image_path: Path) -> list[bytes]:
    """构造 TJUPT 视觉输入：整页 + 最大的影视海报图片。"""
    payload = [image_path.read_bytes()]
    try:
        images = page.locator("img")
        candidates: list[tuple[float, bytes]] = []
        for index in range(min(images.count(), 20)):
            image = images.nth(index)
            box = image.bounding_box()
            if not box or box.get("width", 0) < 160 or box.get("height", 0) < 120:
                continue
            screenshot = image.screenshot()
            if screenshot:
                candidates.append((float(box.get("width", 0) * box.get("height", 0)), screenshot))
        if candidates:
            payload.append(max(candidates, key=lambda item: item[0])[1])
    except Exception:
        # 完整页面截图仍然保留，单独图片裁剪失败不应阻断签到。
        pass
    return payload


def _tjupt_challenge(ctx, page, loop) -> dict:
    radios = page.locator('input[type="radio"]')
    count = min(radios.count(), 12)
    if count < 2:
        raise RuntimeError("识别到 TJUPT 签到验证，但没有解析到候选答案")
    options = [_radio_label(radios.nth(index)) or f"选项 {index + 1}" for index in range(count)]
    token = secrets.token_urlsafe(6)
    image_path = Path(ctx.data_dir) / f"tjupt_{token}.png"
    form = radios.first.locator("xpath=ancestor::form[1]")
    # TJUPT 将影视海报放在表单外侧（候选单选框仍在表单内）。只截表单会
    # 把左侧海报裁掉，AI 只能看到右侧文字而无法完成题目判断；这里发送
    # 完整验证区域/页面截图，确保海报与候选项同时进入视觉模型。
    try:
        page.screenshot(path=str(image_path), full_page=True)
    except Exception:
        form.screenshot(path=str(image_path))

    # TJUPT 必须全自动完成：AI 失败时直接报错，不再发送 Telegram 手动确认。
    if not _ai_available(ctx, "vision"):
        raise RuntimeError("平台未配置视觉 AI，TJUPT 无法自动识别海报，未提交签到")
    _runtime_log(ctx, f"使用 AI 自动识别完整海报与选项，候选项：{options}", level="info", site="TJUPT")
    visual_images = _tjupt_visual_payload(page, image_path)
    choice = None
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            suggestion = str(asyncio.run_coroutine_threadsafe(
                ctx.ai.vision(
                    image=visual_images,
                    prompt=(
                        "这是 TJUPT 的影视海报选择题。请重点查看第一张完整截图左侧的影视海报；"
                        "第二张图片（如果存在）是海报裁剪图。再对照右侧候选文字，判断海报对应的影视名称。"
                        "只允许从候选项中选择一个，必须返回一个 0-based 选项序号。\n候选项：\n"
                        + "\n".join(f"{index}. {label}" for index, label in enumerate(options))
                    ),
                    system="你是影视海报识别助手。必须根据左侧海报选择对应候选项，只返回 0-based 数字，不要返回解释。",
                ),
                loop
            ).result(timeout=60))
            match = re.search(r"(?<!\d)(\d+)(?!\d)", suggestion)
            if match and 0 <= int(match.group(1)) < count:
                choice = int(match.group(1))
                _runtime_log(
                    ctx,
                    f"使用 AI 自动识别完整海报与选项，海报识别名称：{options[choice]}，候选项：{options}",
                    level="info",
                    site="TJUPT",
                )
                _runtime_log(ctx, f"海报识别名称：{options[choice]}（选项 {choice}），自动提交", level="info", site="TJUPT")
                break
            last_error = RuntimeError(f"AI 返回无效选项：{suggestion[:200]}")
        except Exception as exc:
            last_error = exc
        if attempt == 0:
            _runtime_log(ctx, "AI 首次识别未返回有效答案，正在用完整海报重试", level="warning", site="TJUPT")
    if choice is None:
        raise RuntimeError(f"TJUPT AI 未能识别左侧海报，未提交签到：{last_error or '未知错误'}")
    
    # 提交选择的答案
    try:
        current = page.locator('input[type="radio"]')
        if current.count() != count or [_radio_label(current.nth(i)) or f"选项 {i + 1}" for i in range(count)] != options:
            raise RuntimeError("TJUPT 验证题已变化，未提交答案")
        selected = current.nth(choice)
        # CloakBrowser 仍负责真实浏览器会话。0.5.10 的 Locator.check/click
        # 即使传 humanize=False 也仍会进入拟人层，而拟人层不支持这里的
        # nth + ancestor 链式 locator；直接在已解析的 DOM 元素上触发原生
        # 表单事件，避开选择器二次解析。
        selected.evaluate("""element => {
            element.checked = true;
            element.dispatchEvent(new Event('input', {bubbles: true}));
            element.dispatchEvent(new Event('change', {bubbles: true}));
        }""")
        submit = form.locator('button[type="submit"], input[type="submit"], button').first
        if submit.count() < 1:
            raise RuntimeError("没有找到 TJUPT 验证题提交按钮")
        submit.evaluate("""element => {
            const form = element.form || element.closest('form');
            if (!form) throw new Error('TJUPT submit control has no form');
            if (typeof form.requestSubmit === 'function') form.requestSubmit(element);
            else element.click();
        }""")
        page.wait_for_timeout(3_000)
        return _confirm_result(page)
    finally:
        try:
            image_path.unlink(missing_ok=True)
        except Exception:
            pass


def _confirm_result(page, *, attempts: int = 3, expected_domain: str = "") -> dict:
    """刷新确认服务端状态；绝不为确认结果而再次点击签到按钮。"""
    for attempt in range(attempts):
        text = _page_text(page)
        path = (urlparse(page.url).path or "/").lower()
        html = page.content().lower()
        if path.endswith(("/login.php", "/takelogin.php")) or 'name="username"' in html or "name='username'" in html:
            raise RuntimeError("Cookie 已失效：签到后网站跳转到登录页，请在 CookieCloud 来源浏览器重新登录并同步")
        captcha = _captcha_error(text)
        if captcha:
            raise RuntimeError(captcha)
        state = _site_result_state(text, expected_domain, confirmed=True)
        if state:
            status, message = state
            if status == "failed":
                raise RuntimeError(message)
            return {"status": status, "message": message}
        if attempt + 1 < attempts:
            page.wait_for_timeout(2_000 * (attempt + 1))
            page.reload(wait_until="domcontentloaded", timeout=60_000)
    # 部分 NexusPHP 站点的 attendance.php 在验证/跳转后只剩页脚，真实状态显示在首页导航。
    home_url = {
        "audiences.me": "https://audiences.me/",
        "ourbits.club": "https://ourbits.club/",
        "hhanclub.net": "https://hhanclub.net/",
    }.get(expected_domain.lower())
    if home_url:
        page.goto(home_url, wait_until="domcontentloaded", timeout=60_000)
        for _ in range(15):
            home_text = _page_text(page)
            state = _nexus_result_state(home_text)
            if state:
                status, message = state
                if status == "failed":
                    raise RuntimeError(message)
                signed_badge = bool(re.search(r"签到\s*已得\s*[\d,.]+", home_text))
                return {"status": "already" if signed_badge else status, "message": "今天已经签到" if signed_badge else message}
            page.wait_for_timeout(1_000)
    path = urlparse(page.url).path or "/"
    controls = page.locator('a, button, input[type="submit"], input[type="button"]')
    labels: list[str] = []
    for index in range(min(controls.count(), 30)):
        try:
            item = controls.nth(index)
            label = (item.inner_text() or item.get_attribute("value") or item.get_attribute("aria-label") or "").strip()
            label = re.sub(r"\s+", " ", label)[:24]
            if label and label not in labels:
                labels.append(label)
        except Exception:
            continue
    summary = "、".join(labels[:5]) or "无可见操作控件"
    raise RuntimeError(f"签到后未识别到结果（页面 {path}；控件：{summary}）")


def _fetch_same_origin(page, url: str, *, method: str = "GET", data: dict | None = None,
                       json_data: dict | None = None, headers: dict | None = None) -> dict:
    return page.evaluate("""async payload => {
        const options = {method: payload.method, credentials: 'include', headers: payload.headers || {}};
        if (payload.jsonData !== null) {
            options.headers['Content-Type'] = 'application/json; charset=utf-8';
            options.body = JSON.stringify(payload.jsonData);
        } else if (payload.data !== null) {
            options.headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8';
            options.body = new URLSearchParams(payload.data).toString();
        }
        const response = await fetch(payload.url, options);
        return {status: response.status, text: await response.text(), url: response.url};
    }""", {"url": url, "method": method, "data": data, "jsonData": json_data, "headers": headers or {}})


def _response_result(text: str, *, success: tuple[str, ...], already: tuple[str, ...] = ()) -> dict:
    low = (text or "").lower()
    if any(marker.lower() in low for marker in already):
        return {"status": "already", "message": "今天已经签到"}
    if any(marker.lower() in low for marker in success):
        return {"status": "success", "message": "签到成功"}
    raise RuntimeError("签到接口返回未识别结果，未计为成功")


def _ai_call(ctx, loop, capability: str, *, prompt: str, image: bytes | None = None,
             system: str | None = None) -> str:
    if not _ai_available(ctx, capability):
        raise RuntimeError(f"平台未配置可用的 AI {capability} 能力，无法自动识别签到验证")
    if capability == "vision":
        coro = ctx.ai.vision(
            image=image, prompt=prompt,
            system=system or "你是谨慎的验证码识别器，只输出请求的答案，不要解释。",
        )
    else:
        coro = ctx.ai.chat(prompt=prompt, system="你是谨慎的 PT 签到答题助手，只输出答案编号，不要解释。", temperature=0)
    try:
        return str(asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=90) or "").strip()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"AI 识别失败：{exc}") from exc


def _ai_choice(ctx, loop, question: str, options: list[str]) -> int:
    answer = _ai_call(ctx, loop, "text", prompt=(
        "请回答下面的单选题。只输出正确选项编号（从 1 开始）；不确定就输出 0。\n"
        f"问题：{question}\n" + "\n".join(f"{i + 1}. {text}" for i, text in enumerate(options))
    ))
    match = re.search(r"(?<!\d)(\d+)(?!\d)", answer)
    index = int(match.group(1)) - 1 if match else -1
    if index < 0 or index >= len(options):
        raise RuntimeError("AI 未给出可靠的有效选项，未提交签到答案")
    return index


def _ai_ocr(ctx, loop, image: bytes, length: int = 6) -> str:
    last_error: Exception | None = None
    for _ in range(3):
        try:
            answer = _ai_call(ctx, loop, "vision", image=image, prompt=(
                f"读取图片中的 {length} 位验证码。只输出验证码本身；无法确认时输出 UNKNOWN。"
            ))
            candidates = re.findall(rf"(?<![A-Za-z0-9])[A-Za-z0-9]{{{length}}}(?![A-Za-z0-9])", answer)
            if "UNKNOWN" not in answer.upper() and candidates:
                return candidates[0]
            last_error = RuntimeError("模型返回 UNKNOWN 或验证码格式不正确")
        except Exception as exc:  # noqa: BLE001 - 模型上游偶发失败时有限重试
            last_error = exc
    raise RuntimeError("AI 连续 3 次未能可靠识别验证码，未提交签到") from last_error




_U2_CAPTCHA_SELECTORS = (
    'img[src*="image.php"]', 'img[src*="captcha.php"]', 'img[src*="anidb/"]',
    'img[alt="captcha"]', 'img[alt*="验证"]', 'img[alt*="CAPTCHA" i]',
)


def _locate_u2_captcha(form):
    """按站点模板定位验证图片；验证题只以图片承载，表单内不会再有其他图片。"""
    for selector in _U2_CAPTCHA_SELECTORS:
        try:
            node = form.locator(selector).first
            if node.count() > 0:
                return node, selector
        except Exception:
            continue
    # 站点改版换掉类名时，回退到挑战表单内的第一张图片。
    try:
        fallback = form.locator("img").first
        if fallback.count() > 0:
            return fallback, "form img（回退）"
    except Exception:
        pass
    return None, ""


def _highlight_u2_marker(image: bytes) -> tuple[bytes, str]:
    """定位半透明圆点并高亮；OpenCV 不可用或置信度不足时安全回退原图。"""
    try:
        import cv2
        import numpy as np
    except Exception:
        return image, "未能预定位，请直接观察半透明圆点"
    try:
        frame = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return image, "未能预定位，请直接观察半透明圆点"
        gray = cv2.medianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 5)
        height, width = gray.shape[:2]
        shortest = min(height, width)
        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=max(30, shortest // 10),
            param1=80, param2=28,
            minRadius=max(12, int(shortest * 0.035)), maxRadius=max(24, int(shortest * 0.085)),
        )
        if circles is None:
            return image, "未能预定位，请直接观察半透明圆点"
        yy, xx = np.ogrid[:height, :width]
        ranked = []
        for raw_x, raw_y, raw_r in circles[0]:
            mask = (xx - raw_x) ** 2 + (yy - raw_y) ** 2 <= (raw_r * 0.72) ** 2
            ranked.append((float(gray[mask].std()), int(round(raw_x)), int(round(raw_y)), int(round(raw_r))))
        # 只有内部纹理明显被压平（方差足够低）时才视为可信圆点，
        # 避免把错误的红圈画到别的海报上反而误导视觉模型。
        deviation, x, y, radius = min(ranked)
        if deviation > 24:
            return image, "预定位置信度不足，请直接观察半透明圆点"
        cv2.circle(frame, (x, y), radius + 7, (0, 0, 255), 4)
        cv2.line(frame, (max(0, x - radius - 12), y), (min(width - 1, x + radius + 12), y), (0, 0, 255), 2)
        cv2.line(frame, (x, max(0, y - radius - 12)), (x, min(height - 1, y + radius + 12)), (0, 0, 255), 2)
        ok, encoded = cv2.imencode(".png", frame)
        horizontal = "左侧" if x < width * 0.45 else ("右侧" if x > width * 0.55 else "水平中央")
        vertical = "上方" if y < height * 0.4 else ("下方" if y > height * 0.6 else "垂直中央")
        marker = f"圆点中心在整图{horizontal}{vertical}（x={x}/{width}, y={y}/{height}）"
        return (bytes(encoded) if ok else image), marker
    except Exception:
        return image, "未能预定位，请直接观察半透明圆点"


def _u2_vision_prompt(options: list[str], marker: str) -> str:
    return (
        "这是 U2 签到验证图，由两张或多张作品海报组成，半透明圆形斑点是目标标记。"
        "先准确定位圆点覆盖的是哪一张海报，不要被其他海报上更清晰的文字误导；"
        "再根据该海报的角色、机体、构图和标题线索逐项对比候选作品。"
        f"程序预定位结果：{marker}；图上如有红圈和十字，它们精确标出了目标圆点。"
        "可以写简短分析，最后一行必须写 FINAL=编号；无法确认则写 FINAL=0。\n"
        + "\n".join(f"{i + 1}. {item}" for i, item in enumerate(options))
    )


_U2_VISION_SYSTEM = "先做视觉定位和候选作品对比，再在最后一行输出 FINAL=编号。"


def _parse_u2_vision_answer(answer: str, option_count: int) -> int | None:
    match = re.search(r"FINAL\s*[:=]\s*(\d+)", answer or "", re.IGNORECASE)
    if not match:
        return None
    index = int(match.group(1)) - 1
    return index if 0 <= index < option_count else None


def _ai_u2_image_choice(ctx, loop, image: bytes, options: list[str]) -> int:
    """用视觉模型判断圆点标出的作品；文字模型看不到图，因此必须走 vision。"""
    highlighted, marker = _highlight_u2_marker(image)
    prompt = _u2_vision_prompt(options, marker)
    last_error: Exception | None = None
    for _ in range(3):
        try:
            answer = _ai_call(ctx, loop, "vision", image=highlighted, prompt=prompt, system=_U2_VISION_SYSTEM)
            index = _parse_u2_vision_answer(answer, len(options))
            if index is not None:
                return index
            last_error = RuntimeError("模型未返回 FINAL=有效编号")
        except Exception as exc:
            last_error = exc
    raise RuntimeError("AI 连续 3 次未能可靠判断 U2 图片选项，未提交签到") from last_error


def _quiz_checkin(page, site: dict, ctx, loop) -> dict:
    text = _page_text(page)
    if "今天已经签过到了" in text:
        return {"status": "already", "message": "今天已经签到"}
    question_id = page.locator('input[name="questionid"]').get_attribute("value")
    choices = page.locator('input[name="choice[]"]')
    if not question_id or choices.count() < 2:
        raise RuntimeError("未解析到签到问题或候选答案")
    question = text.split("请问：", 1)[1].splitlines()[0].strip() if "请问：" in text else text[:500]
    options = [_radio_label(choices.nth(i)) or str(choices.nth(i).get_attribute("value") or "") for i in range(choices.count())]
    selected = choices.nth(_ai_choice(ctx, loop, question, options)).get_attribute("value")
    result = _fetch_same_origin(page, site["url"], method="POST", data={
        "questionid": question_id, "choice[]": selected, "usercomment": "自动签到", "wantskip": "不会",
    })
    return _response_result(result.get("text", ""), success=("点魔力值",), already=("今天已经签过到了",))


def _special_checkin(page, key: str, site: dict, ctx, loop) -> dict:
    current_domain = (urlparse(page.url).hostname or "").lower()
    expected = site["domain"].lower()
    if not _same_site_domain(current_domain, expected):
        raise RuntimeError(f"站点跳转到了非预期域名：{current_domain or '未知'}")
    text = _page_text(page)
    low = text.lower()
    html = page.content()
    if "login.php" in low or "takelogin.php" in low or 'name="username"' in html.lower():
        raise RuntimeError("Cookie 已失效：站点拒绝当前登录会话，请在 CookieCloud 来源浏览器重新登录并同步")
    mode = site.get("mode")
    if mode == "interactive":
        if key in {"pt52", "chdbits"}:
            return _quiz_checkin(page, site, ctx, loop)
        if key == "hdsky":
            if _hdsky_already(text):
                return {"status": "already", "message": "今天已经签到"}
            code_response = _fetch_same_origin(page, "https://hdsky.me/image_code_ajax.php", method="POST", data={"action": "new"})
            try:
                image_hash = json.loads(code_response.get("text", "")).get("code")
            except (TypeError, ValueError):
                image_hash = None
            if not image_hash:
                raise RuntimeError("天空未返回有效验证码参数")
            page.goto(f"https://hdsky.me/image.php?action=regimage&imagehash={image_hash}", wait_until="load", timeout=60_000)
            captcha = _ai_ocr(ctx, loop, page.screenshot(), 6)
            result = _fetch_same_origin(page, "https://hdsky.me/showup.php", method="POST", data={"action": "showup", "imagehash": image_hash, "imagestring": captcha})
            body = result.get("text", "")
            try:
                return _response_result(body, success=('"success":true', '"success": true'), already=("date_unmatch",))
            except RuntimeError:
                page.goto("https://hdsky.me", wait_until="domcontentloaded", timeout=60_000)
                if _hdsky_already(_page_text(page)):
                    return {"status": "success", "message": "签到成功（首页状态已确认）"}
                raise
        if key == "opencd":
            if "/plugin_sign-in.php?cmd=show-log" in html:
                return {"status": "already", "message": "今天已经签到"}
            page.goto("https://www.open.cd/plugin_sign-in.php", wait_until="domcontentloaded", timeout=60_000)
            form = page.locator("#frmSignin")
            image = form.locator("img").first
            image_hash = form.locator('input[name="imagehash"]').get_attribute("value")
            if not image_hash or image.count() < 1:
                raise RuntimeError("OpenCD 未解析到验证码参数")
            captcha = _ai_ocr(ctx, loop, image.screenshot(), 6)
            result = _fetch_same_origin(page, "https://www.open.cd/plugin_sign-in.php?cmd=signin", method="POST", data={"imagehash": image_hash, "imagestring": captcha})
            return _response_result(result.get("text", ""), success=('"state":"success"', '"state":true'), already=("已签到",))
        if key == "u2":
            initial = _u2_result_state(html)
            if initial and initial[0] != "failed":
                return {"status": initial[0], "message": initial[1]}
            # U2 的权威状态位于首页顶部：[立即签到] 成功后变为 [已签到]。
            # showup.php 本身可能继续显示表单，因此必须先查首页，避免重复提交。
            page.goto("https://u2.dmhy.org/", wait_until="domcontentloaded", timeout=60_000)
            home_state = _u2_result_state(page.content())
            if home_state and home_state[0] != "failed":
                return {"status": "already", "message": "今天已经签到（首页状态已确认）"}
            if datetime.now(_CHINA_TZ).hour < 9:
                raise RuntimeError("U2 站点规则要求 09:00 后签到")
            page.goto(site["url"], wait_until="domcontentloaded", timeout=60_000)
            html = page.content()
            form = page.locator('form:has(input[name="req"])').first
            req = form.locator('input[name="req"]').get_attribute("value")
            hash_value = form.locator('input[name="hash"]').get_attribute("value")
            form_value = form.locator('input[name="form"]').get_attribute("value")
            submits = page.locator('form:has(input[name="req"]) input[type="submit"]')
            if not req or not hash_value or not form_value or submits.count() < 1:
                raise RuntimeError("U2 未解析到签到表单")
            option_count = submits.count()
            options = []
            for index in range(option_count):
                control = submits.nth(index)
                options.append(
                    control.get_attribute("value")
                    or control.get_attribute("title")
                    or f"选项 {index + 1}"
                )
            captcha, captcha_selector = _locate_u2_captcha(form)
            choice = None
            if captcha is None:
                _runtime_log(
                    ctx,
                    "U2 未定位到验证图片，改用随机选项提交",
                    level="warning",
                    site="U2",
                )
            elif not _ai_available(ctx, "vision"):
                _runtime_log(
                    ctx,
                    "平台未配置可用的视觉模型，U2 图片验证改用随机选项提交",
                    level="warning",
                    site="U2",
                )
            else:
                try:
                    shot = captcha.screenshot()
                    _runtime_log(
                        ctx,
                        f"U2 读取验证图片（{captcha_selector}，{len(shot)} 字节），交给视觉模型识别",
                        site="U2",
                    )
                    choice = _ai_u2_image_choice(ctx, loop, shot, options)
                    _runtime_log(
                        ctx,
                        f"U2 AI 识别名称：{options[choice]}（选项 {choice + 1}），自动提交",
                        site="U2",
                    )
                except Exception as exc:
                    _runtime_log(ctx, f"U2 AI 识别失败：{exc}，改用随机选项提交", level="warning", site="U2")
            if choice is None:
                choice = secrets.randbelow(option_count)
            submit = submits.nth(choice)
            _runtime_log(
                ctx,
                f"U2 提交第 {choice + 1}/{option_count} 项；答错仍会完成签到并获得 1 UCoin",
                site="U2",
            )
            body = _u2_submit_with_browser(page, submit)
            posted = _u2_result_state(body, submitted=True)
            if posted:
                if posted[0] == "failed":
                    excerpt = re.sub(r"\s+", " ", _html_visible_text(body)).strip()[:500]
                    _runtime_log(ctx, f"U2 提交回执：{excerpt}", level="warning", site="U2")
                    raise RuntimeError(posted[1])
                return {"status": "success", "message": posted[1]}
            page.goto(
                f"https://u2.dmhy.org/?_awbn_checkin={int(time.time())}",
                wait_until="domcontentloaded", timeout=60_000,
            )
            confirmed = page.content()
            final = _u2_result_state(confirmed)
            if final:
                return {"status": "success", "message": "签到成功（首页状态已确认）"}
            raise RuntimeError("U2 签到提交后仍未确认已签到")
        raise RuntimeError("暂不支持该站点的自动验证")
    if mode == "visit":
        return {"status": "success", "message": "模拟访问成功，已刷新最后访问时间"}
    if mode == "direct":
        return _response_result(text, success=("签到成功", "本次签到获得魅力"), already=("已签到", "已经签到"))
    if mode == "pttime":
        return _response_result(text, success=("签到成功",), already=("今日已签到", "今天已签到"))
    if mode == "btschool":
        if "每日签到" not in text:
            return {"status": "already", "message": "今天已经签到"}
        page.goto("https://pt.btschool.club/index.php?action=addbonus", wait_until="domcontentloaded", timeout=60_000)
        if "每日签到" not in _page_text(page):
            return {"status": "success", "message": "签到成功"}
        raise RuntimeError("签到入口仍然存在")
    if mode == "haidan":
        page.goto("https://www.haidan.video/index.php", wait_until="domcontentloaded", timeout=60_000)
        return _response_result(page.content(), success=("已经打卡",), already=())
    if mode == "hares":
        result = _fetch_same_origin(page, "https://club.hares.top/attendance.php?action=sign")
        return _response_result(result.get("text", ""), success=('"code":0', "签到成功"), already=('"code":1', "已经签到过"))
    if mode == "hdarea":
        result = _fetch_same_origin(page, "https://www.hdarea.club/sign_in.php", method="POST", data={"action": "sign_in"})
        return _response_result(result.get("text", ""), success=("此次签到您获得",), already=("请不要重复签到",))
    if mode == "hdchina":
        csrf = page.locator('meta[name="x-csrf"]').get_attribute("content")
        if not csrf:
            if "已签到" in text:
                return {"status": "already", "message": "今天已经签到"}
            raise RuntimeError("未获取到 HDChina CSRF 参数")
        result = _fetch_same_origin(page, "https://hdchina.org/plugin_sign-in.php?cmd=signin", method="POST", data={"csrf": csrf})
        return _response_result(result.get("text", ""), success=('"state":"success"', '"state":true'), already=("已签到",))
    if mode == "hdupt":
        if "yiqiandao" in html:
            return {"status": "already", "message": "今天已经签到"}
        page.goto("https://pt.hdupt.com/added.php?action=qiandao", wait_until="domcontentloaded", timeout=60_000)
        if any(ch.isdigit() for ch in _page_text(page)):
            return {"status": "success", "message": "签到成功"}
        raise RuntimeError("HDU PT 签到接口返回异常")
    if mode == "pterclub":
        return _response_result(text, success=('"status":"1"', "签到已成功"), already=('"status":"0"', "已经签到过"))
    if mode == "ttg":
        initial = _ttg_result_state(html)
        if initial:
            if initial[0] == "failed":
                raise RuntimeError(initial[1])
            return {"status": initial[0], "message": initial[1]}
        timestamp = re.search(r'signed_timestamp:\s*["\'](\d{10})', html)
        token = re.search(r'signed_token:\s*["\']([^"\']+)', html)
        if not timestamp or not token:
            raise RuntimeError("未获取到 TTG 签到参数")
        result = _fetch_same_origin(page, "https://totheglory.im/signed.php", method="POST", data={"signed_timestamp": timestamp.group(1), "signed_token": token.group(1)})
        posted = _ttg_result_state(result.get("text", ""))
        if posted:
            if posted[0] == "failed":
                raise RuntimeError(posted[1])
            return {"status": posted[0], "message": posted[1]}
        page.goto(site["url"], wait_until="domcontentloaded", timeout=60_000)
        final = _ttg_result_state(page.content())
        if final:
            return {"status": "success", "message": "签到成功（首页状态已确认）"}
        raise RuntimeError("TTG 签到提交后仍未确认已签到")
    if mode == "yema":
        return _response_result(text, success=('"success":true', '"success": true'), already=("already", "已签到"))
    if mode == "zhuque":
        csrf = page.locator('meta[name="x-csrf-token"]').get_attribute("content")
        if not csrf:
            raise RuntimeError("未获取到朱雀 CSRF 参数")
        result = _fetch_same_origin(page, "https://zhuque.in/api/gaming/fireGenshinCharacterMagic", method="POST", json_data={"all": 1, "resetModal": "true"}, headers={"x-csrf-token": csrf})
        return _response_result(result.get("text", ""), success=("FIRE_GENSHIN_CHARACTER_MAGIC_SUCCESS", '"status":200'), already=("already",))
    return _browser_checkin(page, site["domain"], ctx, loop)


def _click_managed_turnstile(page) -> str:
    """Click a real Cloudflare Managed iframe once; never click the empty host widget."""
    frames = [
        frame for frame in page.frames
        if "challenges.cloudflare.com" in str(getattr(frame, "url", "") or "")
    ]
    for frame in frames:
        try:
            checkbox = frame.locator('input[type="checkbox"]').first
            if checkbox.count() and checkbox.is_visible() and checkbox.is_enabled():
                checkbox.click(timeout=3_000)
                return "iframe 内原生 checkbox"
        except Exception:
            continue
    try:
        iframe = page.locator(
            'iframe[src*="challenges.cloudflare.com"], iframe[title*="Cloudflare" i]'
        ).first
        if iframe.count() and iframe.is_visible():
            box = iframe.bounding_box()
            if box and box["width"] >= 80 and box["height"] >= 40:
                page.mouse.click(
                    box["x"] + min(32, box["width"] / 4),
                    box["y"] + box["height"] / 2,
                )
                return f"Cloudflare iframe 坐标，尺寸 {round(box['width'])}x{round(box['height'])}"
    except Exception:
        pass
    return ""


def _reset_turnstile(page) -> str:
    """重置页面原生 Turnstile；不创建站外控件，也不注入站点参数。"""
    try:
        return str(page.evaluate("""() => {
            if (!window.turnstile || typeof window.turnstile.reset !== 'function') return '';
            try {
                window.turnstile.reset();
                return 'Turnstile 原生 reset';
            } catch (error) {
                return 'Turnstile reset 失败: ' + String(error);
            }
        }""") or "")
    except Exception:
        return ""


def _turnstile_checkin(page, expected_domain: str, ctx=None, *, timeout_seconds: int = 30) -> dict:
    """等待 NexusPHP Turnstile 回调提交，只接受明确的服务端结果。"""
    is_audiences = expected_domain.lower() == "audiences.me"
    site_name = "Audiences" if is_audiences else "OurBits"
    form_selector = "#attendance-form" if is_audiences else "#attendance"
    timeout_seconds = max(1, min(120, int(timeout_seconds)))
    deadline = time.monotonic() + timeout_seconds
    started_at = time.monotonic()
    click_count = 0
    token_logged = False
    empty_widget_logged = False
    reset_detail = ""
    # 非交互式验证先获得一个完整的自动签发窗口。只有 Cloudflare 真正生成
    # Managed iframe 后才点击一次，避免误点空的站点外层容器。
    while time.monotonic() < deadline:
        text = _page_text(page)
        state = _nexus_result_state(text)
        if state:
            if state[0] == "failed":
                raise RuntimeError(state[1])
            return {"status": state[0], "message": state[1]}
        form_present = page.locator(form_selector).count() > 0
        turnstile_present = page.locator(f"{form_selector} .cf-turnstile").count() > 0
        if not form_present and not turnstile_present:
            return _confirm_result(page, attempts=2, expected_domain=expected_domain)
        token_info = page.evaluate("""() => {
            const names = ['cf-turnstile-response', 'cf-token'];
            for (const name of names) {
                const input = document.querySelector(`[name="${name}"]`);
                if (input && String(input.value || '').trim()) {
                    return {token: String(input.value).trim(), source: name};
                }
            }
            try {
                if (window.turnstile && typeof window.turnstile.getResponse === 'function') {
                    const response = String(window.turnstile.getResponse() || '').trim();
                    if (response) return {token: response, source: 'turnstile.getResponse'};
                }
            } catch (_) {}
            return {token: '', source: ''};
        }""")
        token = str((token_info or {}).get("token", "")).strip()
        if token:
            if ctx is not None and not token_logged:
                _runtime_log(
                    ctx,
                    f"已取得 Turnstile 验证令牌（来源：{token_info.get('source') or '未知'}），正在提交签到",
                    site=site_name,
                )
                token_logged = True
            page.evaluate(f"""() => {{
                const form = document.querySelector('{form_selector}');
                if (!form || form.dataset.awSubmitted === '1') return;
                form.dataset.awSubmitted = '1';
                if (typeof form.requestSubmit === 'function') form.requestSubmit();
                else form.submit();
            }}""")
            time.sleep(min(2.0, max(0.0, deadline - time.monotonic())))
            continue
        now = time.monotonic()
        elapsed = now - started_at
        if not reset_detail and elapsed >= min(30.0, max(10.0, timeout_seconds / 3.0)):
            reset_detail = _reset_turnstile(page)
            if reset_detail and ctx is not None:
                _runtime_log(
                    ctx,
                    f"原生 Turnstile 长时间未响应，已请求控件重新验证（{reset_detail}）",
                    level="warning",
                    site=site_name,
                )
        challenge_frames = [
            frame for frame in page.frames
            if "challenges.cloudflare.com" in str(getattr(frame, "url", "") or "")
        ]
        # Managed Turnstile 在 Docker/低信誉出口下可能显示可交互复选框。
        # Audiences 与 OurBits 都可能动态切换到 Managed，不能按站点永久禁用点击。
        should_click = (
            click_count == 0
            and elapsed >= _TURNSTILE_AUTO_GRACE_SECONDS
        )
        if should_click:
            click_detail = _click_managed_turnstile(page)
            if click_detail:
                click_count += 1
                if ctx is not None:
                    _runtime_log(
                        ctx,
                        f"已对 Managed Turnstile 单击一次（{click_detail}），等待验证完成",
                        site=site_name,
                    )
            elif ctx is not None and not challenge_frames and not empty_widget_logged:
                _runtime_log(
                    ctx,
                    "Turnstile 外层容器尚未生成 Cloudflare 验证 iframe，不执行无效空容器点击",
                    level="warning",
                    site=site_name,
                )
                empty_widget_logged = True
        wait_seconds = 2.0
        wait_seconds = min(wait_seconds, max(0.0, deadline - time.monotonic()))
        time.sleep(wait_seconds)
    try:
        diagnostics = page.evaluate(f"""() => ({{
            url: location.href,
            title: document.title,
            forms: document.querySelectorAll('{form_selector}').length,
            widgets: Array.from(document.querySelectorAll('.cf-turnstile')).map(widget => ({{
                sitekey: String(widget.dataset.sitekey || '').slice(0, 24),
                children: widget.children.length,
                text: String(widget.textContent || '').trim().slice(0, 120)
            }})),
            turnstileApi: Boolean(window.turnstile),
            turnstileError: String(window.__awTurnstileError || ''),
            scripts: Array.from(document.scripts)
                .map(script => String(script.src || ''))
                .filter(src => src.includes('turnstile') || src.includes('cloudflare'))
                .slice(0, 8),
            navigator: {{
                webdriver: navigator.webdriver,
                platform: navigator.platform,
                userAgent: navigator.userAgent,
                languages: navigator.languages
            }},
            iframes: Array.from(document.querySelectorAll('iframe')).map(frame => ({{
                title: frame.title || '', src: String(frame.src || '').slice(0, 160)
            }}))
        }})""")
    except Exception as exc:
        diagnostics = {"diagnostic_error": str(exc)}
    if ctx is not None:
        _runtime_log(ctx, f"Turnstile 超时诊断：{diagnostics}", level="error", site=site_name)
    raise RuntimeError(f"{site_name} Turnstile 未在 {timeout_seconds} 秒内签发有效验证令牌，本轮已跳过")


def _audiences_turnstile_checkin(page, ctx=None, *, timeout_seconds: int = 30) -> dict:
    """兼容旧测试与内部调用名；实际逻辑由通用 Turnstile 处理器负责。"""
    return _turnstile_checkin(
        page, "audiences.me", ctx, timeout_seconds=timeout_seconds,
    )


def _turnstile_site_cloak_checkin(ctx, key: str, site: dict, cookie: str, headless: bool) -> dict:
    """使用 CloakBrowser 官方推荐参数处理 NexusPHP Turnstile。"""
    import cloakbrowser

    site_name = str(site["name"])
    site_domain = str(site["domain"])
    site_url = str(site["url"])
    version = str(getattr(cloakbrowser, "__version__", "未知"))
    running_mode = "无头" if headless else ("虚拟有头" if os.path.exists("/.dockerenv") else "有头")
    _runtime_log(
        ctx,
        f"启动 CloakBrowser {version} Preview 全新临时上下文（"
        f"{running_mode}模式，新指纹，网络与 GeoIP 跟随平台设置）",
        site=site_name,
    )
    context = page = None
    try:
        # 显式声明通道，让平台能从源码发现所需内核并统一检查更新。
        # 代理和 License Key 仍由平台注入，GeoIP 跟随最终网络出口。
        context = cloakbrowser.launch_context(
            headless=headless,
            release_channel="preview",
            humanize=True,
            human_preset="careful",
            geoip=True,
        )
        # launch 完成后再读取，确保报告的是平台本次实际选择并准备的内核。
        _log_cloakbrowser_binary(ctx, cloakbrowser, site_name, "preview")
        pages = list(getattr(context, "pages", []) or [])
        page = pages[0] if pages else context.new_page()
        page.set_default_timeout(20_000)

        # 只注入平台同步的站点业务 Cookie。与旧浏览器指纹和出口绑定的
        # Cloudflare Cookie 不跨会话复制，由全新上下文自行完成验证。
        items = []
        for part in str(cookie or "").split(";"):
            name, separator, value = part.strip().partition("=")
            if separator and name and not _is_cloudflare_session_cookie(name):
                items.append({"name": name, "value": value, "url": site_url})
        if items:
            context.add_cookies(items)

        try:
            page.goto(
                site_url,
                wait_until="domcontentloaded",
                timeout=60_000,
            )
        except Exception as exc:
            if "timeout" in str(exc).lower():
                raise RuntimeError(f"{site_name} CloakBrowser 60 秒内没有取得页面结果，本轮已跳过") from exc
            raise
        # 浏览器启动和页面导航不再挤占验证时间。
        deadline = time.monotonic() + _TURNSTILE_TIMEOUT_SECONDS
        if key == "audiences":
            _runtime_log(
                ctx,
                "先等待 Turnstile 自动验证；如出现 Managed 复选框，将对真实 iframe 单击一次",
                site=site_name,
            )
            # 原生 sleep 不产生 Playwright waitForTimeout CDP 指令。
            time.sleep(min(8.0, max(0.0, deadline - time.monotonic())))
        return _browser_checkin(page, site_domain, ctx, None, deadline=deadline)
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass


class _PiggoRealtime:
    """仅观察官网原生实时连接；不保存帧正文或发送任何 WebSocket 消息。"""

    def __init__(self, page, ctx=None):
        self.page = page
        self.ctx = ctx
        self.ready = False
        self._current = None
        self._authenticated = False
        self._closed = False
        self._listeners = []
        self._console_codes = set()
        self._network_codes = set()
        try:
            page.on("websocket", self._opened)
            page.on("console", self._console)
            page.on("response", self._network_response)
            page.on("requestfailed", self._network_failed)
        except Exception:
            self.close()
            raise

    def _console(self, message):
        if self._closed:
            return
        try:
            text = message.text
            if not isinstance(text, str) or len(text) > 8_192 or "[Cloudflare Turnstile]" not in text:
                return
            match = re.search(r"\bError:\s*(\d{6})\b", text)
            if match and match[1] not in self._console_codes and len(self._console_codes) < 3:
                self._console_codes.add(match[1])
                _runtime_log(self.ctx, f"官网 Cloudflare 验证错误码 {match[1]}", level="warning", site="猪猪")
        except Exception:
            pass  # 只提取官方固定数字错误码，不记录 console 原文。

    def _network_issue(self, url, code):
        if self._closed or code in self._network_codes or len(self._network_codes) >= 3:
            return
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "challenges.cloudflare.com" \
                or parsed.port not in {None, 443} or parsed.username is not None or parsed.password is not None:
            return
        self._network_codes.add(code)
        _runtime_log(self.ctx, f"官方验证网络状态（{code}，不作为签到结果）", level="warning", site="猪猪")

    def _network_response(self, response):
        try:
            status = int(response.status)
            if 400 <= status <= 599:
                self._network_issue(response.url, f"HTTP {status}")
        except Exception:
            pass

    def _network_failed(self, request):
        try:
            failure = request.failure
            if failure in {
                "net::ERR_ABORTED", "net::ERR_FAILED", "net::ERR_TIMED_OUT",
                "net::ERR_CONNECTION_CLOSED", "net::ERR_CONNECTION_RESET",
                "net::ERR_CONNECTION_REFUSED", "net::ERR_CONNECTION_TIMED_OUT",
                "net::ERR_NAME_NOT_RESOLVED", "net::ERR_INTERNET_DISCONNECTED",
                "net::ERR_PROXY_CONNECTION_FAILED", "net::ERR_TUNNEL_CONNECTION_FAILED",
                "net::ERR_BLOCKED_BY_CLIENT", "net::ERR_CERT_AUTHORITY_INVALID",
                "net::ERR_CERT_DATE_INVALID", "net::ERR_SSL_PROTOCOL_ERROR",
            }:
                self._network_issue(request.url, failure)
        except Exception:
            pass

    def _opened(self, socket):
        try:
            parsed = urlparse(socket.url)
            if parsed.scheme != "wss" or parsed.hostname not in {"piggo.me", "www.piggo.me"} \
                    or parsed.port not in {None, 443} or parsed.username is not None \
                    or parsed.password is not None or parsed.path != "/ws" or self._closed:
                return
        except Exception:
            return
        self._current = socket
        self._authenticated = False
        self.ready = False
        seen = {}

        def frame(payload, *, sent):
            if self._closed or socket is not self._current:
                return
            try:
                if not isinstance(payload, str) or len(payload) > 65_536:
                    return
                message = json.loads(payload)
                event = message.get("event") if isinstance(message, dict) else None
                if sent:
                    if event not in {"ws.auth", "captcha.ask"}:
                        return
                    if event == "ws.auth":
                        self._authenticated = True
                        self.ready = False
                elif event not in {"ws.hello", "ws.ready", "auth.session", "captcha.public"}:
                    return
                elif event in {"ws.ready", "auth.session"} and self._authenticated:
                    self.ready = True
                marker = (sent, event)
                seen[marker] = seen.get(marker, 0) + 1
                limit = 3 if event in {"captcha.ask", "captcha.public"} else 1
                if seen[marker] <= limit:
                    direction = "发出" if sent else "收到"
                    suffix = f"（第 {seen[marker]} 次）" if limit > 1 else ""
                    _runtime_log(self.ctx, f"官网实时通道{direction} {event}{suffix}", site="猪猪")
            except Exception:
                pass  # 不把服务器正文、鉴权字段或解析异常原文写入日志。

        def ended(*_):
            if not self._closed and socket is self._current:
                self._current = None
                self.ready = False
                self._authenticated = False
                _runtime_log(self.ctx, "官网实时通道已断开，等待网站自行恢复", level="warning", site="猪猪")

        for event, callback in (("framesent", lambda payload: frame(payload, sent=True)),
                                ("framereceived", lambda payload: frame(payload, sent=False)),
                                ("close", ended), ("socketerror", ended)):
            try:
                socket.on(event, callback)
                self._listeners.append((socket, event, callback))
            except Exception:
                self._current = None
                self._authenticated = False
                self.ready = False
                break

    def close(self):
        self._closed = True
        self.ready = False
        self._current = None
        for source, event, callback in [(self.page, "websocket", self._opened),
                                        (self.page, "console", self._console),
                                        (self.page, "response", self._network_response),
                                        (self.page, "requestfailed", self._network_failed), *self._listeners]:
            try:
                source.remove_listener(event, callback)
            except Exception:
                pass
        self._listeners.clear()


def _site_cloak_checkin(ctx, key: str, site: dict, cookie: str, headless: bool, loop) -> dict:
    """所有 PT 站浏览器降级统一使用真实 CloakBrowser。"""
    if key in {"audiences", "ourbits"}:
        return _turnstile_site_cloak_checkin(ctx, key, site, cookie, headless)
    piggo = _same_site_domain(site["domain"], "piggo.me")
    if piggo and not all(_piggo_account(ctx)):
        raise RuntimeError("猪猪尚未填写完整的用户名和密码，请在插件配置中填写并保存")

    import cloakbrowser

    state_path = Path(ctx.data_dir) / f"{key}_storage_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    browser = context = page = realtime = None
    try:
        # 与依赖预备保持 Stable 一致，也供平台扫描所需更新通道。
        browser = cloakbrowser.launch(
            headless=headless,
            release_channel="stable",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
            # 交由平台注入代理和 License Key；GeoIP 跟随最终网络出口。
            geoip=True,
            humanize=True,
        )
        # 猪猪沿用 SDK 的上下文默认值：launch 已统一处理地区/语言和
        # 窗口，不再通过 context 层单独覆盖，避免两层设置相互脱节。
        # 其他站点保持原有参数，不扩大本次修改范围。
        context_options = {} if piggo else {
            "viewport": {"width": 1920, "height": 1080},
            "locale": "zh-CN",
            "extra_http_headers": {"Accept-Language": "zh-CN,zh;q=0.9"},
        }
        if not piggo and state_path.exists():
            context_options["storage_state"] = str(state_path)
        try:
            context = browser.new_context(**context_options)
        except Exception as exc:
            if "storage_state" not in context_options:
                raise
            _runtime_log(
                ctx,
                f"已保存的浏览器会话无法读取（{type(exc).__name__}），本轮将重建",
                level="warning",
                site=site["name"],
            )
            context_options.pop("storage_state", None)
            context = browser.new_context(**context_options)
        page = context.new_page()
        if piggo:
            realtime = _PiggoRealtime(page, ctx)
            def log_session_response(response):
                # 只记录认证恢复接口的失败分类，不记录响应正文、URL 参数或凭据。
                try:
                    parsed = urlparse(response.url)
                    path = parsed.path.rstrip("/")
                    if parsed.scheme != "https" or parsed.hostname not in {"piggo.me", "www.piggo.me"} or path not in {
                        "/auth/sign", "/api/auth/sign", "/v1/web/auth/sign", "/me", "/api/me", "/v1/web/me",
                        "/v1/web/login", "/v1/web/auth/srp/challenge", "/v1/web/auth/srp/login",
                        "/v1/web/captcha/fail",
                    }:
                        return
                    status = int(response.status)
                    if path == "/v1/web/captcha/fail":
                        if parsed.path == "/v1/web/captcha/fail" and parsed.port in {None, 443} \
                                and parsed.username is None and parsed.password is None and response.request.method == "POST":
                            _runtime_log(ctx, f"官网验证组件报告失败（原生 /captcha/fail，HTTP {status}）", level="warning", site="猪猪")
                        return
                    is_login = path in {"/v1/web/login", "/v1/web/auth/srp/challenge", "/v1/web/auth/srp/login"}
                    if status < 400 and not is_login:
                        return
                    label = "登录" if is_login else "会话恢复"
                    _runtime_log(ctx, f"官网{label}接口 {path} 返回 HTTP {status}", level="warning" if status >= 400 else "info", site="猪猪")
                except Exception:
                    pass  # 诊断失败不影响原生登录和签到。
            page.on("response", log_session_response)
        page.set_default_timeout(20_000)
        if piggo:
            _runtime_log(ctx, "使用全新浏览器会话，直接通过官网账号密码登录（不复用 Token/Cookie）", site=site["name"])
            page.goto("https://piggo.me/login?redirect=%2Fcalendar", wait_until="domcontentloaded", timeout=60_000)
            return _browser_checkin(page, "piggo.me", ctx, loop, piggo_realtime=realtime)
        _seed_browser_cookie_jar(page, cookie, site["url"])
        if site.get("generic"):
            target_url = site["url"]
            parsed = urlparse(target_url)
            if parsed.path in {"", "/"}:
                target_url = target_url.rstrip("/") + "/attendance.php"
            page.goto(target_url, wait_until="domcontentloaded", timeout=60_000)
            return _browser_checkin(page, site["domain"], ctx, loop)
        if key in {"ourbits", "hhan", "tjupt"}:
            return _browser_checkin(page, site["domain"], ctx, loop)
        return _special_checkin(page, key, site, ctx, loop)
    finally:
        if realtime is not None:
            realtime.close()
        if context is not None and not piggo:
            try:
                context.storage_state(path=str(state_path))
            except Exception as exc:
                _runtime_log(
                    ctx,
                    f"保存浏览器会话失败：{type(exc).__name__}",
                    level="warning",
                    site=site["name"],
                )
        for item in (page, context, browser):
            if item is not None:
                try:
                    item.close()
                except Exception:
                    pass


def _piggo_calendar_guard(page) -> None:
    parsed = urlparse(page.url)
    if parsed.scheme != "https" or parsed.hostname not in {"piggo.me", "www.piggo.me"}:
        raise RuntimeError("猪猪跳转到了非预期域名，未执行签到")
    if (parsed.path or "/").rstrip("/").lower() in {"/login", "/login.php", "/takelogin.php"}:
        raise RuntimeError("猪猪官网登录尚未完成或已退出，本轮未执行签到；请检查账号密码及官网验证提示")


def _piggo_calendar_signed(page) -> bool:
    """只认今天格子的签到徽标，不认历史天数、历史日期和普通提示语。"""
    badges = page.locator(".cal-page .cal-cell.today .cal-badge.att")
    for index in range(badges.count()):
        badge = badges.nth(index)
        if badge.is_visible() and badge.inner_text(timeout=1_000).strip() == "签":
            return True
    return False


def _piggo_turnstile_checkbox_point(image: bytes, width: float, height: float) -> tuple[float, float] | None:
    """只定位已显示的空复选框；加载动画、勾选状态或不明图像不执行点击。"""
    try:
        from io import BytesIO
        from math import isfinite
        from PIL import Image

        if not isinstance(image, bytes) or not image or len(image) > 2_000_000:
            return None
        if isinstance(width, bool) or isinstance(height, bool):
            return None
        width, height = float(width), float(height)
        if not (isfinite(width) and isfinite(height)):
            return None
        if not (250 <= width <= 400 and 50 <= height <= 120):
            return None
        with Image.open(BytesIO(image)) as source:
            pixel_width, pixel_height = source.size
            if (
                source.format != "PNG"
                or pixel_width * pixel_height > 4_000_000
                or max(pixel_width, pixel_height) > 4096
            ):
                return None
            scale_x, scale_y = pixel_width / width, pixel_height / height
            if not (0.75 <= scale_x <= 4.1 and 0.75 <= scale_y <= 4.1):
                return None
            if abs(scale_x - scale_y) > max(scale_x, scale_y) * 0.05:
                return None
            source.load()
            if "A" in source.getbands() and source.getchannel("A").getextrema()[0] < 250:
                return None
            # 在 CSS 像素中判断，避免高 DPI 截图把边框或旋转点误作不同尺寸。
            css_width, css_height = round(width), round(height)
            normalized = source.convert("RGB").resize(
                (css_width, css_height), Image.Resampling.BOX
            )
        pixels = normalized.load()
        tones = {}
        for y in range(css_height):
            for x in range(min(68, css_width)):
                r, g, b = pixels[x, y]
                tones[x, y] = ((r + g + b) / 3, max(r, g, b) - min(r, g, b))

        def outlined(points, inner_tone, polarity):
            return sum(
                tones[p][1] <= 24
                and polarity * (tones[p][0] - inner_tone) >= 40
                for p in points
            ) >= len(points) * 0.9

        background_tone = sorted(
            tones[p][0] for p in ((4, 4), (60, 4), (4, css_height - 5), (60, css_height - 5))
        )[2]
        possible_boxes = set()
        for row in range(7, css_height - 7):
            column = 4
            while column < 63:
                start = column
                while (column < 63 and tones[column, row][1] <= 24
                       and abs(tones[column, row][0] - background_tone) >= 40):
                    column += 1
                length = column - start
                # 只有真正连续的方框横边才进入完整检查；旋转点通常只有2~3像素。
                if 12 <= length <= 28:
                    for size in range(max(18, length - 2), 27):
                        left = round((start + column - size) / 2)
                        for x in range(left - 1, left + 2):
                            for y in range(row - 2, row + 1):
                                if 4 <= x <= 36 and 7 <= y < css_height - size - 6:
                                    possible_boxes.add((size, x, y))
                column += 1

        candidates = []
        for size, x, y in possible_boxes:
            center_tone, center_chroma = tones[x + size // 2, y + size // 2]
            if center_chroma > 16:
                continue
            # 四条边必须都连续可见；排除圆形 spinner 和稀疏旋转点。
            for polarity in (-1, 1):
                top = any(outlined([(xx, yy) for xx in range(x + 3, x + size - 3)], center_tone, polarity)
                          for yy in range(y, y + 3))
                if not top:
                    continue
                bottom = any(outlined([(xx, yy) for xx in range(x + 3, x + size - 3)], center_tone, polarity)
                             for yy in range(y + size - 3, y + size))
                left = any(outlined([(xx, yy) for yy in range(y + 3, y + size - 3)], center_tone, polarity)
                           for xx in range(x, x + 3))
                right = any(outlined([(xx, yy) for yy in range(y + 3, y + size - 3)], center_tone, polarity)
                            for xx in range(x + size - 3, x + size))
                if not (bottom and left and right):
                    continue
                # 空框内部应完全均匀。任何勾、点、色块或动画都保守等待。
                inner = [tones[xx, yy] for yy in range(y + 3, y + size - 3)
                         for xx in range(x + 3, x + size - 3)]
                if any(chroma > 16 or abs(tone - center_tone) > 18 for tone, chroma in inner):
                    continue
                candidates.append((x + size / 2, y + size / 2))
                break
        if not candidates:
            return None
        point_x = sum(point[0] for point in candidates) / len(candidates)
        point_y = sum(point[1] for point in candidates) / len(candidates)
        # 不明确存在多个不同的方框时，不猜测应点击哪个目标。
        if any(abs(x - point_x) > 2 or abs(y - point_y) > 2 for x, y in candidates):
            return None
        return point_x * width / css_width, point_y * height / css_height
    except Exception:
        return None


def _piggo_wait_calendar_ready(page, guard, ctx=None, *, deadline=None, still_eligible=None):
    """等页面加载完成且当天格子、签到按钮连续稳定 5 秒，再返回最新按钮。"""
    _runtime_log(ctx, "等待日历页面加载完成，并连续稳定 5 秒后再签到（最多等待 30 秒）", site="猪猪")
    deadline = min(time.monotonic() + 30, deadline) if deadline is not None else time.monotonic() + 30
    signature = None
    stable_since = None
    for _ in range(61):
        guard()
        if still_eligible is not None and not still_eligible():
            return None
        if time.monotonic() >= deadline:
            break
        button = None
        current = None
        try:
            if _piggo_calendar_signed(page):
                return None
            today = page.locator(".cal-page .cal-cell.today")
            if page.evaluate("() => document.readyState === 'complete'") is True \
                    and today.count() == 1 and today.first.is_visible():
                buttons = page.locator(".cal-page .cal-att button.cal-att-pill.act")
                if buttons.count() == 1:
                    candidate = buttons.first
                    remaining_ms = max(1, min(1_000, int((deadline - time.monotonic()) * 1000)))
                    if candidate.is_visible() and candidate.is_enabled(timeout=remaining_ms):
                        label = re.sub(r"\s+", "", candidate.inner_text(timeout=remaining_ms))
                        if re.fullmatch(r"签到(?:[·•・]\+\d+(?:\.\d+)?)?", label):
                            button = candidate
                            current = (label, today.first.inner_text(timeout=remaining_ms))
        except Exception:
            # SPA 可能刚替换日历节点；只重新等待，不点旧元素、不读取内部状态。
            pass
        now = time.monotonic()
        if current is None or current != signature:
            signature = current
            stable_since = now if current is not None else None
        if now >= deadline:
            break
        if stable_since is not None and now - stable_since >= 5:
            _runtime_log(ctx, "日历页面已加载并稳定 5 秒，准备单次签到", site="猪猪")
            return button
        page.wait_for_timeout(500)
    if still_eligible is not None:
        return None  # 额外点击资格失效或加载超时，不中断官网已有请求的结果回查。
    raise RuntimeError("猪猪日历页面未在 30 秒内加载并稳定，本轮跳过，未点击签到")


def _piggo_calendar_checkin(page, ctx=None, *, expected_session=None, realtime=None) -> dict:
    """通过站点原生日历按钮提交；不猜签名接口，也不消费补签卡。"""
    expected = expected_session
    if expected is None and ctx is not None:
        expected = _piggo_account(ctx)

    def guard() -> None:
        _piggo_calendar_guard(page)
        if ctx is not None and (getattr(ctx, "_closed", False) or
                _piggo_account(ctx) != expected):
            raise RuntimeError("猪猪配置已变更或插件已停用，本轮跳过")

    guard()
    if (urlparse(page.url).path or "/").rstrip("/") != "/calendar":
        page.goto("https://piggo.me/calendar", wait_until="domcontentloaded", timeout=60_000)
    submit = None
    for _ in range(40):
        guard()
        if _piggo_calendar_signed(page):
            return {"status": "already", "message": "今天已经签到"}
        buttons = page.locator(".cal-page .cal-att button.cal-att-pill.act")
        for index in range(buttons.count()):
            button = buttons.nth(index)
            if not button.is_visible() or not button.is_enabled():
                continue
            label = re.sub(r"\s+", "", button.inner_text())
            if re.fullmatch(r"签到(?:[·•・]\+\d+(?:\.\d+)?)?", label):
                submit = button
                break
        if submit is not None:
            break
        page.wait_for_timeout(500)
    if submit is None:
        raise RuntimeError("猪猪日历未找到当天签到按钮或签到记录，本轮跳过（不会点击补签）")

    if realtime is not None:
        # 官网 422 的验证弹窗须经此连接请求配置；页面可用并不代表实时鉴权已完成。
        # 只等原生 ws.auth 后的服务端确认，不发送消息或调用官网内部函数。
        deadline = time.monotonic() + 20
        if not realtime.ready:
            _runtime_log(ctx, "等待官网实时验证通道就绪，最多 20 秒；就绪前不提交签到", site="猪猪")
        for _ in range(40):
            guard()
            if _piggo_calendar_signed(page):
                return {"status": "already", "message": "今天已经签到"}
            if realtime.ready or time.monotonic() >= deadline:
                break
            page.wait_for_timeout(500)
        guard()
        if not realtime.ready:
            raise RuntimeError("猪猪官网实时验证通道未就绪，本轮跳过，未提交签到；请检查官网 /ws 连接")

    submit = _piggo_wait_calendar_ready(page, guard, ctx)
    if submit is None:
        return {"status": "already", "message": "今天已经签到"}

    sent = False
    request_pending = False
    latest_request = None
    finished_request = None
    needs_captcha = False
    failure_hint = ""
    attendance_requests = 0
    rejected_request = None
    retry_not_before = 0.0
    retry_attempted = False

    def attendance_request(request):
        parsed = urlparse(request.url)
        return parsed.scheme == "https" and parsed.hostname in {"piggo.me", "www.piggo.me"} \
            and parsed.port in {None, 443} and parsed.username is None and parsed.password is None \
            and parsed.path == "/v1/web/calendar/attendance" and request.method == "POST"

    def log_request(request):
        nonlocal sent, request_pending, latest_request
        nonlocal needs_captcha, failure_hint
        nonlocal attendance_requests, rejected_request
        try:
            if attendance_request(request):
                sent = True
                request_pending = True
                latest_request = request
                attendance_requests += 1
                rejected_request = None
                needs_captcha = False
                failure_hint = ""
                _runtime_log(ctx, "官网当天签到请求已发出", site="猪猪")
        except Exception:
            pass

    def log_response(response):
        nonlocal needs_captcha, failure_hint
        try:
            if attendance_request(response.request) and response.request is latest_request:
                status = int(response.status)
                _runtime_log(ctx, f"官网当天签到接口返回 HTTP {status}", level="warning" if status >= 400 else "info", site="猪猪")
                # 官网验证成功后会原生重放请求；不能继续沿用上一条 422。
                needs_captcha = False
                failure_hint = ""
                if status >= 400:
                    failure_hint = f"猪猪官网拒绝签到请求（HTTP {status}），本轮跳过，不再追加点击"
        except Exception:
            pass

    def log_finished(request):
        nonlocal finished_request
        try:
            if attendance_request(request) and request is latest_request:
                finished_request = request
        except Exception:
            pass

    def parse_finished():
        nonlocal needs_captcha, failure_hint, request_pending
        nonlocal finished_request
        nonlocal rejected_request, retry_not_before
        request = finished_request
        finished_request = None
        if request is None or request is not latest_request:
            return
        try:
            response = request.response()
            if request is not latest_request:
                return
            request_pending = False
            if response is None or int(response.status) != 422:
                return
            # 事件回调只记录引用；在主流程中读取完整回执，避免回调里等待 RPC。
            payload = response.json()
            if request is not latest_request:
                return
            if isinstance(payload, dict):
                reason = payload.get("msg") or payload.get("message")
                data = payload.get("data")
                marked = payload.get("site_captcha") is True or (isinstance(data, dict) and data.get("site_captcha") is True)
                if marked or reason in ("请完成人机验证", "人机验证失败", "请重新完成人机验证"):
                    needs_captcha = True
                    rejected_request = request
                    retry_not_before = time.monotonic() + 15
                    failure_hint = "猪猪官网要求完成人机验证（HTTP 422），签到尚未完成，本轮跳过，不再追加点击"
                    detail = "已携带官方验证标记" if marked else "响应未携带官方验证标记"
                    _runtime_log(ctx, f"官网要求人机验证（{detail}），先等待原生验证；无弹窗且明确未签到时最多再尝试一次", level="warning", site="猪猪")
        except Exception as exc:
            _runtime_log(ctx, f"官网签到回执解析未完成（{type(exc).__name__}），继续回查当天签到记录", level="warning", site="猪猪")

    def log_failed(request):
        nonlocal request_pending, failure_hint
        try:
            if attendance_request(request) and request is latest_request:
                request_pending = False
                failure_hint = "猪猪官网签到请求未完成，本轮跳过，不再追加点击"
                _runtime_log(ctx, "官网当天签到请求未完成，仅回查签到记录，不重复提交", level="warning", site="猪猪")
        except Exception:
            pass

    def captcha_visible():
        dialogs = page.locator('.site-cap[role="dialog"][aria-label="人机验证"]')
        return any(dialogs.nth(index).is_visible() for index in range(dialogs.count()))

    submission_attempted = False
    try:
        page.on("request", log_request)
        page.on("response", log_response)
        page.on("requestfinished", log_finished)
        page.on("requestfailed", log_failed)
        # 点击超时不构成重试依据；只有完整的、已识别的 422 拒绝回执才允许有限重试。
        guard()
        if realtime is not None and not realtime.ready:
            raise RuntimeError("猪猪官网实时验证通道已断开，本轮跳过，未提交签到")
        _runtime_log(ctx, "正在点击当天签到按钮（首次）", site="猪猪")
        submission_attempted = True
        first_click_confirmed = False
        try:
            submit.click(timeout=10_000)
            first_click_confirmed = True
        except Exception as exc:
            _runtime_log(ctx, f"当天签到按钮点击异常（{type(exc).__name__}），仅回查签到结果，不重复提交", level="warning", site="猪猪")
        captcha_opened = False
        captcha_click_attempted = False
        next_captcha_probe = 0.0
        deadline = time.monotonic() + 120
        for tick in range(240):
            guard()
            if _piggo_calendar_signed(page):
                return {"status": "success", "message": "签到成功"}
            parse_finished()
            visible_now = captcha_visible()
            if not captcha_opened and visible_now:
                captcha_opened = True
                _runtime_log(ctx, "官网人机验证窗口已打开，保留原生会话等待验证（提交后最多等待 120 秒）", site="猪猪")
            if first_click_confirmed and not retry_attempted and attendance_requests == 1 and needs_captcha \
                    and rejected_request is latest_request and not request_pending and not visible_now \
                    and realtime is not None and realtime.ready \
                    and retry_not_before <= time.monotonic() < deadline:
                # 不是超时重发：首条完整回执已明确拒绝，且当前无官网验证弹窗。
                # 自动重放或用户手动再次点击产生的请求同样计数，不能再叠加第三次。
                retry_attempted = True
                rejected = rejected_request
                def retry_eligible():
                    # DOM 查询可能分发原生重放事件，查询结束后才核对最新请求身份。
                    return not captcha_visible() and attendance_requests == 1 and latest_request is rejected \
                        and rejected_request is rejected and needs_captcha and not request_pending \
                        and realtime is not None and realtime.ready \
                        and time.monotonic() < deadline

                _runtime_log(ctx, "首轮签到明确被拒绝且当前无验证弹窗，重新等待页面稳定后最多再点击一次", level="warning", site="猪猪")
                retry_button = _piggo_wait_calendar_ready(page, guard, ctx, deadline=deadline,
                                                          still_eligible=retry_eligible)
                guard()
                if _piggo_calendar_signed(page):
                    return {"status": "success", "message": "签到成功"}
                if retry_button is not None and retry_eligible():
                    _runtime_log(ctx, "正在第二次点击当天签到按钮，本轮不再追加点击", site="猪猪")
                    try:
                        retry_button.click(timeout=max(1, min(10_000, int((deadline - time.monotonic()) * 1000))))
                    except Exception as exc:
                        _runtime_log(ctx, f"第二次签到按钮操作未确认（{type(exc).__name__}），只回查结果，不再点击", level="warning", site="猪猪")
            if captcha_opened and not captcha_click_attempted and time.monotonic() < deadline \
                    and captcha_visible() and page.locator(".site-cap .ts-box").count():
                # 只操作官网已打开控件内的真实复选框；令牌与重放仍由官网生成。
                for frame in getattr(page, "frames", []):
                    try:
                        parsed = urlparse(str(getattr(frame, "url", "") or ""))
                        trusted_frame = parsed.scheme == "https" and parsed.hostname == "challenges.cloudflare.com" \
                            and parsed.port in {None, 443} and parsed.username is None and parsed.password is None
                    except ValueError:
                        trusted_frame = False
                    if not trusted_frame:
                        continue
                    try:
                        checkbox = frame.locator('input[type="checkbox"]').first
                        if not checkbox.count() or not checkbox.is_visible() or not checkbox.is_enabled() \
                                or checkbox.is_checked():
                            continue
                        guard()
                        if _piggo_calendar_signed(page):
                            return {"status": "success", "message": "签到成功"}
                        if not captcha_visible():
                            break
                        if time.monotonic() >= deadline:
                            break
                        captcha_click_attempted = True
                        # check 是幂等操作；官网若刚自行勾选，不会再次切换为空框。
                        checkbox.check(timeout=3_000)
                        _runtime_log(ctx, "已点击官网 Cloudflare 人机验证复选框一次，等待官网自动完成签到", site="猪猪")
                    except Exception as exc:
                        if captcha_click_attempted:
                            _runtime_log(ctx, f"官网验证复选框操作未确认（{type(exc).__name__}），仅等待原生结果，不重复点击", level="warning", site="猪猪")
                    if captcha_click_attempted:
                        break
                if not captcha_click_attempted and next_captcha_probe <= time.monotonic() < deadline:
                    # Turnstile 可把 iframe 放入 closed shadow root，无法用常规
                    # iframe/input 定位。截图只检查空复选框轮廓是否已经出现；
                    # 空壳、自动验证旋转图标和已完成状态均不点击，不读写验证令牌。
                    next_captcha_probe = time.monotonic() + 0.5
                    box = None
                    point = None
                    probe_started = time.monotonic()
                    try:
                        widget = page.locator(".site-cap .ts-box").first
                        candidate = widget.bounding_box(timeout=1_000)
                        if candidate and 280 <= candidate["width"] <= 360 and 60 <= candidate["height"] <= 100 \
                                and page.evaluate("() => typeof window.turnstile?.render === 'function'") is True:
                            point = _piggo_turnstile_checkbox_point(widget.screenshot(timeout=1_000),
                                                                   candidate["width"], candidate["height"])
                            if point is not None:
                                box = widget.bounding_box(timeout=1_000)
                                if not box or abs(box["width"] - candidate["width"]) > 1 \
                                        or abs(box["height"] - candidate["height"]) > 1:
                                    box = None
                    except Exception:
                        pass  # 官网控件可能刚被原生回调关闭；下一轮继续核对当天记录。
                    if box:
                        _runtime_log(ctx, f"官网验证空复选框已出现，本次检查耗时 {int((time.monotonic() - probe_started) * 1000)}ms", site="猪猪")
                        guard()
                        if _piggo_calendar_signed(page):
                            return {"status": "success", "message": "签到成功"}
                        if not captcha_visible():
                            continue
                        if time.monotonic() >= deadline:
                            break
                        captcha_click_attempted = True
                        click_started = time.monotonic()
                        try:
                            page.mouse.click(box["x"] + point[0], box["y"] + point[1])
                            _runtime_log(ctx, f"已点击官网 Cloudflare 原生复选框一次，操作耗时 {int((time.monotonic() - click_started) * 1000)}ms，等待官网自动完成签到", site="猪猪")
                        except Exception as exc:
                            _runtime_log(ctx, f"官网验证控件操作未确认（{type(exc).__name__}），仅等待原生结果，不重复点击", level="warning", site="猪猪")
            if time.monotonic() >= deadline or (tick >= 80 and not retry_attempted and attendance_requests < 2
                                               and not request_pending and not captcha_opened and not needs_captcha):
                break
            page.wait_for_timeout(500)
            if tick == 39:
                visible_now = captcha_visible()
                if not retry_attempted and attendance_requests < 2 and not needs_captcha \
                        and not request_pending and not captcha_opened and not visible_now:
                    page.reload(wait_until="domcontentloaded", timeout=60_000)
        if failure_hint:
            raise RuntimeError(failure_hint)
        if not sent:
            raise RuntimeError("猪猪点击后未检测到官网签到请求，本轮跳过，不再追加点击")
        raise RuntimeError("猪猪提交后未确认当天已签到，本轮跳过，不再追加点击")
    except Exception as exc:
        if submission_attempted and not (isinstance(exc, RuntimeError) and "本轮跳过" in str(exc)):
            _runtime_log(ctx, f"提交后页面确认异常（{type(exc).__name__}），不再追加点击", level="warning", site="猪猪")
            raise RuntimeError("猪猪提交后页面结果无法确认，本轮跳过，不再追加点击") from None
        raise
    finally:
        for event, callback in (("request", log_request), ("response", log_response),
                                ("requestfinished", log_finished), ("requestfailed", log_failed)):
            try:
                page.remove_listener(event, callback)
            except Exception:
                pass


def _browser_checkin(page, expected_domain: str, ctx=None, loop=None, *,
                     deadline: float | None = None, piggo_realtime=None) -> dict:
    """在平台托管的同步 Playwright 页面内完成单站签到。"""
    page.set_default_timeout(20_000)
    challenge_reload_done = False
    piggo_reentries = 0
    challenge_started_at = time.monotonic()
    challenge_click_detail = ""
    for challenge_round in range(100):
        if deadline is not None and time.monotonic() >= deadline:
            raise RuntimeError(
                f"{expected_domain} CloakBrowser {_TURNSTILE_TIMEOUT_SECONDS} 秒内没有取得页面结果，本轮已跳过"
            )
        title = (page.title() or "").lower()
        text = _page_text(page).lower()
        path = urlparse(page.url).path or "/"
        piggo_security_shell = (
            expected_domain.lower() == "piggo.me"
            and path == "/"
            and "cloudflare" in text
            and "privacy" in text
            and not any(marker in text for marker in ("签到", "控制面板", "种子", "论坛", "个人资料"))
        )
        challenged = any(marker in f"{title}\n{text}" for marker in (
            "just a moment", "checking your browser", "cloudflare ray id", "cf-chl-",
            "请完成安全验证", "验证您是否是真人", "验证完成，即将进入网站",
            "雷池 waf", "安全检测能力由 雷池", "verification completed",
            "请耐心等待签到验证程序加载",
        )) or piggo_security_shell
        if not challenged:
            break
        if (
            expected_domain.lower() in {"audiences.me", "ourbits.club"}
            and not challenge_click_detail
            and time.monotonic() - challenge_started_at >= _TURNSTILE_AUTO_GRACE_SECONDS
        ):
            challenge_click_detail = _click_managed_turnstile(page)
            if challenge_click_detail and ctx is not None:
                _runtime_log(
                    ctx,
                    f"已对 Cloudflare 页面 Managed 验证单击一次（{challenge_click_detail}）",
                    site="Audiences" if expected_domain.lower() == "audiences.me" else "OurBits",
                )
        # PigGo 雷池完成验证时可能停在只含 Cloudflare / Privacy 的空壳根页。
        # 给脚本时间写入通行 Cookie，再受控重进签到页，避免把空壳当业务页面。
        if piggo_security_shell and challenge_round in {3, 10, 25}:
            page.goto("https://piggo.me/calendar", wait_until="domcontentloaded", timeout=60_000)
            piggo_reentries += 1
            continue
        # 雷池偶尔已下发通行 Cookie 但前端未完成跳转，受控重载可恢复。
        if not challenge_reload_done and challenge_round >= 10 and any(marker in f"{title}\n{text}" for marker in (
            "验证完成，即将进入网站", "verification completed",
        )):
            page.reload(wait_until="domcontentloaded", timeout=60_000)
            challenge_reload_done = True
            continue
        wait_ms = 3_000
        if deadline is not None:
            wait_ms = min(wait_ms, max(1, int((deadline - time.monotonic()) * 1000)))
        if expected_domain.lower() in {"audiences.me", "ourbits.club"}:
            time.sleep(wait_ms / 1000)
        else:
            page.wait_for_timeout(wait_ms)
    else:
        detail = f"；已重进签到页 {piggo_reentries} 次" if piggo_reentries else ""
        raise RuntimeError(f"Cloudflare/雷池验证等待超时{detail}；若为交互式验证码需要人工处理")

    current_domain = (urlparse(page.url).hostname or "").lower()
    if not _same_site_domain(current_domain, expected_domain):
        raise RuntimeError(f"站点跳转到了非预期域名：{current_domain or '未知'}")
    if expected_domain.lower() == "piggo.me":
        session = _piggo_ensure_login(page, ctx, loop)
        return _piggo_calendar_checkin(page, ctx, expected_session=session, realtime=piggo_realtime)
    text = _page_text(page)
    low = text.lower()
    html = page.content().lower()
    if any(marker in low for marker in (
        "用户名或密码", "please login", "not logged in", "请先登录",
    )) or 'name="username"' in html or "name='username'" in html or urlparse(page.url).path.lower().endswith(("/login.php", "/takelogin.php")):
        raise RuntimeError("Cookie 已失效：站点拒绝当前登录会话，请在 CookieCloud 来源浏览器重新登录并同步")
    if any(marker in low for marker in ("没有权限", "无权访问", "permission denied", "access denied", "page not found", "404 not found")):
        raise RuntimeError("签到页面不可用或当前账号没有访问权限")
    if expected_domain.lower() in {"audiences.me", "ourbits.club"} \
            and page.locator("form .cf-turnstile").count() > 0:
        remaining = _TURNSTILE_TIMEOUT_SECONDS if deadline is None else max(1, int(deadline - time.monotonic()))
        return _turnstile_checkin(page, expected_domain, ctx, timeout_seconds=remaining)
    captcha = _captcha_error(text)
    if captcha:
        if expected_domain == "tjupt.org" and ctx is not None and loop is not None and "签到图片验证码" in captcha:
            return _tjupt_challenge(ctx, page, loop)
        raise RuntimeError(captcha)
    if expected_domain.lower() == "hhanclub.net":
        state = _hhan_result_state(html)
        if state:
            return {"status": state[0], "message": state[1]}
        raise RuntimeError("HHanClub 页面未找到当天签到记录，未计为成功")
    initial_state = _site_result_state(text, expected_domain)
    if initial_state:
        status, message = initial_state
        if status == "failed":
            raise RuntimeError(message)
        return {"status": status, "message": message}

    candidates = page.locator('a, button, input[type="submit"], input[type="button"]')
    for index in range(min(candidates.count(), 80)):
        item = candidates.nth(index)
        try:
            if not item.is_visible() or not item.is_enabled():
                continue
            label = (item.inner_text() or item.get_attribute("value") or "").strip()
            normalized = "".join(label.split()).lower()
            if normalized not in {"签到", "立即签到", "点击签到", "今日未签到", "attend", "checkin", "check-in"}:
                continue
            item.click()
            page.wait_for_timeout(3_000)
            return _confirm_result(page, expected_domain=expected_domain)
        except RuntimeError:
            raise
        except Exception:
            continue

    # 标准 NexusPHP attendance.php 通常由 GET 完成签到；刷新后必须出现明确结果。
    if urlparse(page.url).path.lower().endswith("/attendance.php"):
        return _confirm_result(page, expected_domain=expected_domain)
    raise RuntimeError("没有识别到签到页面或签到按钮，网站结构可能已更新")


class _NeedsBrowser(RuntimeError):
    """HTTP 页面需要浏览器执行挑战或动态脚本。"""


def _http_guard(response: httpx.Response) -> str:
    text = response.text or ""
    low = text.lower()
    # TTG 的正常首页会携带 Cloudflare 相关脚本字样；动态签到参数同时存在时
    # 说明业务页已完整返回，不能仅凭脚本文案误判为挑战页。
    trusted_ttg_page = (
        response.status_code == 200
        and "signed_timestamp" in text
        and "signed_token" in text
    )
    if low.strip() in {"err cookie", "cookie error", "invalid cookie"}:
        raise RuntimeError("Cookie 已失效：网站签到接口拒绝当前登录会话，请在 CookieCloud 来源浏览器重新登录并同步")
    if not trusted_ttg_page and (response.status_code in {403, 429, 468, 503, 521, 522, 525} or any(marker in low for marker in (
        "cf-chl-", "cloudflare ray id", "just a moment", "checking your browser",
        "turnstile", "雷池 waf", "安全检测能力由 雷池", "验证您是否是真人",
        "verification completed", "challenge-platform",
    ))):
        raise _NeedsBrowser(f"HTTP 命中安全验证（{response.status_code}），切换 CloakBrowser")
    if any(marker in low for marker in ('name="username"', "name='username'", "takelogin.php")) or response.url.path.lower().endswith(("/login.php", "/takelogin.php")):
        raise RuntimeError("Cookie 已失效：站点拒绝当前登录会话，请在 CookieCloud 来源浏览器重新登录并同步")
    if response.status_code >= 400:
        raise RuntimeError(f"HTTP 请求失败：{response.status_code}")
    return text


async def _http_ai_choice(ctx, question: str, options: list[str]) -> int:
    if not _ai_available(ctx, "text"):
        raise RuntimeError("平台未配置可用的 AI 文字模型，无法回答签到题")
    answer = str(await ctx.ai.chat(
        prompt="请回答下面的单选题。只输出正确选项编号（从 1 开始）；不确定就输出 0。\n"
               f"问题：{question}\n" + "\n".join(f"{i + 1}. {item}" for i, item in enumerate(options)),
        system="你是谨慎的 PT 签到答题助手，只输出答案编号，不要解释。", temperature=0,
    ) or "").strip()
    match = re.search(r"(?<!\d)(\d+)(?!\d)", answer)
    index = int(match.group(1)) - 1 if match else -1
    if index < 0 or index >= len(options):
        raise RuntimeError("AI 未给出可靠的有效选项，未提交签到答案")
    return index


async def _http_ai_ocr(ctx, image: bytes, length: int = 6) -> str:
    if not _ai_available(ctx, "vision"):
        raise RuntimeError("平台未配置视觉模型，无法识别签到验证码")
    last_error: Exception | None = None
    for _ in range(3):
        try:
            answer = str(await ctx.ai.vision(
                image=image, prompt=f"读取图片中的 {length} 位验证码。只输出验证码本身；无法确认时输出 UNKNOWN。",
                system="你是谨慎的验证码识别器，只输出请求的答案，不要解释。",
            ) or "").strip()
            matches = re.findall(rf"(?<![A-Za-z0-9])[A-Za-z0-9]{{{length}}}(?![A-Za-z0-9])", answer)
            if "UNKNOWN" not in answer.upper() and matches:
                return matches[0]
            last_error = RuntimeError("模型返回 UNKNOWN 或验证码格式不正确")
        except Exception as exc:  # noqa: BLE001 - 模型上游偶发失败时有限重试
            last_error = exc
    raise RuntimeError("AI 连续 3 次未能可靠识别验证码，未提交签到") from last_error




async def _http_ai_u2_image_choice(ctx, image: bytes, options: list[str]) -> int:
    """HTTP 路径同样用视觉模型判断圆点标出的作品。"""
    if not _ai_available(ctx, "vision"):
        raise RuntimeError("平台未配置视觉模型，无法识别 U2 签到验证")
    highlighted, marker = _highlight_u2_marker(image)
    prompt = _u2_vision_prompt(options, marker)
    last_error: Exception | None = None
    for _ in range(3):
        try:
            answer = str(await ctx.ai.vision(
                image=highlighted, prompt=prompt, system=_U2_VISION_SYSTEM,
            ) or "").strip()
            index = _parse_u2_vision_answer(answer, len(options))
            if index is not None:
                return index
            last_error = RuntimeError("模型未返回 FINAL=有效编号")
        except Exception as exc:
            last_error = exc
    raise RuntimeError("AI 连续 3 次未能可靠判断 U2 图片选项，未提交签到") from last_error


def _soup_value(soup: BeautifulSoup, name: str) -> str:
    node = soup.select_one(f'input[name="{name}"]')
    return str(node.get("value") or "") if node else ""


async def _http_checkin(ctx, key: str, site: dict, cookie: str) -> dict:
    """轻量签到；只有安全挑战或必须执行动态脚本时才请求浏览器降级。"""
    if key == "piggo" or _same_site_domain(site["domain"], "piggo.me"):
        raise _NeedsBrowser("猪猪新版日历需要浏览器原生签到，切换 CloakBrowser")
    headers = {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    }
    timeout = httpx.Timeout(35.0, connect=12.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        async def get(url: str) -> tuple[httpx.Response, str]:
            response = await client.get(url)
            return response, _http_guard(response)

        async def post(url: str, *, data=None, json_data=None, extra_headers=None) -> tuple[httpx.Response, str]:
            response = await client.post(url, data=data, json=json_data, headers=extra_headers)
            return response, _http_guard(response)

        mode = site.get("mode")
        request_url = site["url"]
        if site.get("generic"):
            parsed = urlparse(request_url)
            if parsed.path in {"", "/"}:
                request_url = request_url.rstrip("/") + "/attendance.php"
        response, text = await get(request_url)
        visible_text = _html_visible_text(text)
        if key == "hhan":
            state = _hhan_result_state(text)
            if state:
                return {"status": state[0], "message": state[1], "engine": "http"}
            raise _NeedsBrowser("HTTP 未找到 HHanClub 当天签到记录，切换 CloakBrowser 确认")
        if key == "audiences":
            soup = BeautifulSoup(text, "html.parser")
            if soup.select_one("#attendance-form .cf-turnstile"):
                raise _NeedsBrowser("Audiences 需要 Turnstile 人机验证，切换 CloakBrowser 等待自动验证")
        if key in {"audiences", "ourbits", "hhan"}:
            # 标准 attendance.php 通常 GET 即完成；未知页面交给浏览器识别动态按钮。
            state = _site_result_state(visible_text, site["domain"], confirmed=True)
            if state and state[0] != "failed":
                return {"status": state[0], "message": state[1], "engine": "http"}
            if state and state[0] == "failed":
                raise RuntimeError(state[1])
            # Audiences 的 attendance.php 在 Docker/CF 链路中会完成签到后返回无回执的站点模板。
            # 此处仅接受已通过登录与安全页检查的 2xx 同站请求，避免把登录页或挑战页误报为成功。
            response_domain = (urlparse(str(response.url)).hostname or "").lower()
            response_path = urlparse(str(response.url)).path or "/"
            if key == "audiences" and response.status_code < 300 \
                    and _same_site_domain(response_domain, site["domain"]):
                return {"status": "success", "message": "签到请求已完成（站点未返回文字回执）", "engine": "http"}
            raise _NeedsBrowser("HTTP 页面没有明确签到结果，切换 CloakBrowser 确认")

        if mode == "visit":
            return {"status": "success", "message": "轻量访问成功，已刷新最后访问时间", "engine": "http"}
        if mode == "direct":
            result = _response_result(text, success=("签到成功", "本次签到获得魅力"), already=("已签到", "已经签到"))
            return {**result, "engine": "http"}
        if mode == "pttime":
            try:
                result = _response_result(text, success=("签到成功",), already=("今日已签到", "今天已签到"))
            except RuntimeError as exc:
                raise _NeedsBrowser("PTTime HTTP 回执未识别，切换 CloakBrowser 确认") from exc
            return {**result, "engine": "http"}
        if mode == "btschool":
            if "每日签到" not in text:
                return {"status": "already", "message": "今天已经签到", "engine": "http"}
            _, body = await get("https://pt.btschool.club/index.php?action=addbonus")
            if "每日签到" not in body:
                return {"status": "success", "message": "签到成功", "engine": "http"}
            raise RuntimeError("签到入口仍然存在")
        if mode == "haidan":
            _, body = await get("https://www.haidan.video/index.php")
            return {**_response_result(body, success=("已经打卡",)), "engine": "http"}
        if mode == "hares":
            _, body = await get("https://club.hares.top/attendance.php?action=sign")
            return {**_response_result(body, success=('"code":0', "签到成功"), already=('"code":1', "已经签到过")), "engine": "http"}
        if mode == "hdarea":
            _, body = await post("https://www.hdarea.club/sign_in.php", data={"action": "sign_in"})
            return {**_response_result(body, success=("此次签到您获得",), already=("请不要重复签到",)), "engine": "http"}
        if mode == "hdchina":
            soup = BeautifulSoup(text, "html.parser")
            csrf_node = soup.select_one('meta[name="x-csrf"]')
            csrf = str(csrf_node.get("content") or "") if csrf_node else ""
            if not csrf:
                raise _NeedsBrowser("HTTP 未取得 HDChina CSRF，切换 CloakBrowser")
            _, body = await post("https://hdchina.org/plugin_sign-in.php?cmd=signin", data={"csrf": csrf})
            return {**_response_result(body, success=('"state":"success"', '"state":true'), already=("已签到",)), "engine": "http"}
        if mode == "hdupt":
            if "yiqiandao" in text:
                return {"status": "already", "message": "今天已经签到", "engine": "http"}
            _, body = await get("https://pt.hdupt.com/added.php?action=qiandao")
            if any(char.isdigit() for char in BeautifulSoup(body, "html.parser").get_text(" ")):
                return {"status": "success", "message": "签到成功", "engine": "http"}
            raise RuntimeError("HDU PT 签到接口返回异常")
        if mode == "pterclub":
            return {**_response_result(text, success=('"status":"1"', "签到已成功"), already=('"status":"0"', "已经签到过")), "engine": "http"}
        if mode == "ttg":
            initial = _ttg_result_state(text)
            if initial:
                if initial[0] == "failed":
                    raise RuntimeError(initial[1])
                return {"status": initial[0], "message": initial[1], "engine": "http"}
            timestamp = re.search(r'signed_timestamp:\s*["\'](\d{10})', text)
            token = re.search(r'signed_token:\s*["\']([^"\']+)', text)
            if not timestamp or not token:
                raise _NeedsBrowser("HTTP 未取得 TTG 动态参数，切换 CloakBrowser")
            _, body = await post(
                "https://totheglory.im/signed.php",
                data={"signed_timestamp": timestamp.group(1), "signed_token": token.group(1)},
                extra_headers={"Referer": str(response.url), "X-Requested-With": "XMLHttpRequest"},
            )
            posted = _ttg_result_state(body)
            if posted:
                if posted[0] == "failed":
                    raise RuntimeError(posted[1])
                return {"status": posted[0], "message": posted[1], "engine": "http"}
            _, confirmed = await get(site["url"])
            final = _ttg_result_state(confirmed)
            if final:
                return {"status": "success", "message": "签到成功（首页状态已确认）", "engine": "http"}
            raise _NeedsBrowser("TTG HTTP 提交后未确认最终状态，切换 CloakBrowser 回查")
        if mode == "yema":
            return {**_response_result(text, success=('"success":true', '"success": true'), already=("already", "已签到")), "engine": "http"}
        if mode == "zhuque":
            soup = BeautifulSoup(text, "html.parser")
            csrf_node = soup.select_one('meta[name="x-csrf-token"]')
            csrf = str(csrf_node.get("content") or "") if csrf_node else ""
            if not csrf:
                raise _NeedsBrowser("HTTP 未取得朱雀 CSRF，切换 CloakBrowser")
            _, body = await post("https://zhuque.in/api/gaming/fireGenshinCharacterMagic", json_data={"all": 1, "resetModal": "true"}, extra_headers={"x-csrf-token": csrf})
            return {**_response_result(body, success=("FIRE_GENSHIN_CHARACTER_MAGIC_SUCCESS", '"status":200'), already=("already",)), "engine": "http"}
        if key in {"pt52", "chdbits"}:
            if "今天已经签过到了" in text:
                return {"status": "already", "message": "今天已经签到", "engine": "http"}
            soup = BeautifulSoup(text, "html.parser")
            question_id = _soup_value(soup, "questionid")
            nodes = soup.select('input[name="choice[]"]')
            if not question_id or len(nodes) < 2:
                raise _NeedsBrowser("HTTP 未解析到签到题，切换 CloakBrowser")
            question = soup.get_text(" ", strip=True).split("请问：", 1)[-1][:500]
            options = []
            for node in nodes:
                label = soup.select_one(f'label[for="{node.get("id", "")}"]') if node.get("id") else None
                options.append(label.get_text(" ", strip=True) if label else str(node.parent.get_text(" ", strip=True) or node.get("value") or ""))
            selected = str(nodes[await _http_ai_choice(ctx, question, options)].get("value") or "")
            _, body = await post(site["url"], data={"questionid": question_id, "choice[]": selected, "usercomment": "自动签到", "wantskip": "不会"})
            return {**_response_result(body, success=("点魔力值",), already=("今天已经签过到了",)), "engine": "http"}
        if key == "hdsky":
            if _hdsky_already(visible_text):
                return {"status": "already", "message": "今天已经签到", "engine": "http"}
            _, code_body = await post("https://hdsky.me/image_code_ajax.php", data={"action": "new"})
            try:
                image_hash = json.loads(code_body).get("code")
            except (TypeError, ValueError):
                image_hash = None
            if not image_hash:
                raise _NeedsBrowser("HTTP 未取得天空验证码，切换 CloakBrowser")
            image_response = await client.get(f"https://hdsky.me/image.php?action=regimage&imagehash={image_hash}")
            if image_response.status_code >= 400:
                raise RuntimeError(f"下载天空验证码失败：{image_response.status_code}")
            captcha = await _http_ai_ocr(ctx, image_response.content)
            _, body = await post("https://hdsky.me/showup.php", data={"action": "showup", "imagehash": image_hash, "imagestring": captcha})
            try:
                result = _response_result(body, success=('"success":true', '"success": true'), already=("date_unmatch",))
            except RuntimeError:
                _, confirmed = await get("https://hdsky.me")
                if _hdsky_already(_html_visible_text(confirmed)):
                    result = {"status": "success", "message": "签到成功（首页状态已确认）"}
                else:
                    raise
            return {**result, "engine": "http"}
        if key == "opencd":
            if "/plugin_sign-in.php?cmd=show-log" in text:
                return {"status": "already", "message": "今天已经签到", "engine": "http"}
            _, form_body = await get("https://www.open.cd/plugin_sign-in.php")
            soup = BeautifulSoup(form_body, "html.parser")
            form = soup.select_one("#frmSignin")
            image_node = form.select_one("img") if form else None
            hash_node = form.select_one('input[name="imagehash"]') if form else None
            if not image_node or not hash_node:
                raise _NeedsBrowser("HTTP 未解析到 OpenCD 验证码，切换 CloakBrowser")
            image_url = str(response.url.join(str(image_node.get("src") or "")))
            image_response = await client.get(image_url)
            try:
                captcha = await _http_ai_ocr(ctx, image_response.content)
            except RuntimeError as exc:
                raise _NeedsBrowser("OpenCD HTTP 验证码无法确认，切换 CloakBrowser 获取新验证码") from exc
            _, body = await post("https://www.open.cd/plugin_sign-in.php?cmd=signin", data={"imagehash": hash_node.get("value"), "imagestring": captcha})
            return {**_response_result(body, success=('"state":"success"', '"state":true'), already=("已签到",)), "engine": "http"}
        if key == "u2":
            initial = _u2_result_state(text)
            if initial and initial[0] != "failed":
                return {"status": initial[0], "message": initial[1], "engine": "http"}
            # 签到状态只在首页顶部可靠展示；先确认首页再解析/提交表单。
            _, home = await get("https://u2.dmhy.org/")
            home_state = _u2_result_state(home)
            if home_state and home_state[0] != "failed":
                return {"status": "already", "message": "今天已经签到（首页状态已确认）", "engine": "http"}
            if datetime.now(_CHINA_TZ).hour < 9:
                raise RuntimeError("U2 站点规则要求 09:00 后签到")
            soup = BeautifulSoup(text, "html.parser")
            req, hash_value, form_value = (_soup_value(soup, name) for name in ("req", "hash", "form"))
            submits = soup.select('input[type="submit"][name]')
            if not req or not hash_value or not form_value or not submits:
                raise _NeedsBrowser("HTTP 未解析到 U2 签到表单，切换 CloakBrowser")
            captcha_node = None
            challenge_form = soup.select_one('form:has(input[name="req"])')
            for selector in _U2_CAPTCHA_SELECTORS:
                captcha_node = (challenge_form or soup).select_one(selector)
                if captcha_node is not None:
                    break
            if captcha_node is None and challenge_form is not None:
                captcha_node = challenge_form.select_one("img")
            options = [str(item.get("value") or item.get("title") or f"选项 {i + 1}") for i, item in enumerate(submits)]
            choice = None
            if captcha_node is None:
                _runtime_log(ctx, "U2 未定位到验证图片，改用随机选项提交", level="warning", site="U2")
            elif not _ai_available(ctx, "vision"):
                _runtime_log(
                    ctx, "平台未配置可用的视觉模型，U2 图片验证改用随机选项提交",
                    level="warning", site="U2",
                )
            else:
                try:
                    image_url = str(response.url.join(str(captcha_node.get("src") or "")))
                    image_response = await client.get(image_url)
                    if image_response.status_code >= 400:
                        raise RuntimeError(f"下载验证图片失败（HTTP {image_response.status_code}）")
                    _runtime_log(
                        ctx,
                        f"U2 读取验证图片（{len(image_response.content)} 字节），交给视觉模型识别",
                        site="U2",
                    )
                    choice = await _http_ai_u2_image_choice(ctx, image_response.content, options)
                    _runtime_log(ctx, f"U2 AI 识别名称：{options[choice]}（选项 {choice + 1}），自动提交", site="U2")
                except Exception as exc:
                    _runtime_log(ctx, f"U2 AI 识别失败：{exc}，改用随机选项提交", level="warning", site="U2")
            if choice is None:
                choice = secrets.randbelow(len(submits))
            submit = submits[choice]
            post_response, body = await post(
                "https://u2.dmhy.org/showup.php?action=show",
                data={"req": req, "hash": hash_value, "form": form_value, "message": "一切随缘~", submit.get("name"): submit.get("value")},
                extra_headers={"Referer": str(response.url)},
            )
            posted = _u2_result_state(body, submitted=True)
            if posted:
                if posted[0] == "failed":
                    raise RuntimeError(posted[1])
                return {"status": "success", "message": posted[1], "engine": "http"}
            response_path = (urlparse(str(post_response.url)).path or "").lower()
            response_domain = (urlparse(str(post_response.url)).hostname or "").lower()
            if post_response.status_code < 300 and _same_site_domain(response_domain, site["domain"]):
                suffix = "提交后跳转已确认" if response_path not in {"/showup.php", "showup.php"} else "站点接受签到表单"
                return {"status": "success", "message": f"签到成功（{suffix}）", "engine": "http"}
            _, confirmed = await get("https://u2.dmhy.org/")
            final = _u2_result_state(confirmed)
            if final:
                return {"status": "success", "message": "签到成功（首页状态已确认）", "engine": "http"}
            raise _NeedsBrowser("U2 HTTP 提交后未确认最终状态，切换 CloakBrowser 回查")
        if site.get("generic"):
            # 通用模式只接受明确的签到/已签到文案；普通 200 页面交由浏览器
            # 识别按钮并回查结果，避免将首页访问误判为成功。
            state = _site_result_state(visible_text, site["domain"], confirmed=True)
            if state:
                if state[0] == "failed":
                    raise RuntimeError(state[1])
                return {"status": state[0], "message": state[1], "engine": "http"}
            raise _NeedsBrowser("通用站点未返回明确签到结果，切换 CloakBrowser 确认")
        raise _NeedsBrowser("该站点暂无稳定 HTTP 适配，切换 CloakBrowser")


async def _run(
    ctx,
    source: str,
    selected_override: list[str] | None = None,
    *,
    schedule_failed_retry: bool = True,
    wait_for_lock: bool = False,
    retry_count_override: int | None = None,
) -> dict:
    global _run_lock, _active_run_task
    if _run_lock is None:
        _run_lock = asyncio.Lock()
    if _run_lock.locked() and not wait_for_lock:
        return {"ok": False, "message": "签到任务正在运行"}
    async with _run_lock:
        _active_run_task = asyncio.current_task()
        cfg = _cfg(ctx)
        configured = _configured_sites(cfg)
        selected = selected_override if selected_override is not None else cfg.get("selected_sites", list(configured))
        if not isinstance(selected, list):
            selected = list(configured)
        # 新增的通用站点没有旧配置中的 key，首次保存后自动纳入签到；
        # 一旦用户在页面明确勾选/取消，selected_sites 中会保留该 key。
        custom_keys = set(_custom_sites(cfg))
        if selected_override is None and custom_keys and not (custom_keys & {str(key) for key in selected}):
            selected = [*selected, *sorted(custom_keys)]
        enabled = [(str(key), configured[str(key)]) for key in selected if str(key) in configured]
        if not enabled:
            return {"ok": False, "message": "没有启用任何签到站点"}
        _state.update({
            "running": True, "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "finished_at": "", "current": "", "phase": "依赖准备", "message": "正在等待平台依赖和浏览器内核就绪",
            "completed": 0, "total": len(enabled),
        })
        _runtime_log(ctx, "开始检查平台依赖与 CloakBrowser 内核，完成前不会启动签到")
        try:
            prepared = await _with_heartbeat(
                asyncio.to_thread(_prepare_runtime_dependencies, [key for key, _ in enabled]),
                ctx,
                "依赖准备",
                "平台依赖或 CloakBrowser 内核仍在准备",
                interval=30,
                max_wait=900,
            )
        except asyncio.CancelledError:
            _state.update({"running": False, "phase": "已取消", "message": "依赖准备已取消", "current": ""})
            raise
        except Exception as exc:  # noqa: BLE001
            message = f"依赖或 CloakBrowser 内核未准备完成：{exc}"
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _state.update({
                "running": False, "finished_at": stamp, "current": "", "phase": "依赖失败", "message": message,
            })
            _runtime_log(ctx, message, level="error")
            return {"ok": False, "message": message, "results": []}
        _runtime_log(ctx, "依赖准备完成：" + "；".join(prepared), level="success")
        _state.update({"phase": "准备", "message": "依赖已就绪，开始签到"})
        _runtime_log(ctx, f"开始{source}签到，共 {len(enabled)} 个站点")
        results = []
        retries = _bounded(
            cfg.get("retry_count") if retry_count_override is None else retry_count_override,
            2,
            0,
            5,
        )
        interval = _bounded(cfg.get("retry_interval"), 20, 5, 300)
        loop = asyncio.get_running_loop()
        for key, site in enabled:
            piggo = _same_site_domain(site["domain"], "piggo.me")
            credential_label = "检查猪猪用户名和密码" if piggo else "读取平台 Cookie"
            _state.update({"current": site["name"], "phase": "读取凭证" if piggo else "读取 Cookie", "message": f"{site['name']}：{credential_label}"})
            _runtime_log(ctx, credential_label, site=site["name"])
            cookie, error = await _site_cookie(ctx, key, site)
            if error:
                _runtime_log(ctx, error, level="error", site=site["name"])
                _runtime_log(ctx, "本站已记录失败，继续处理下一个站点", level="warning", site=site["name"])
                results.append({"key": key, "site": site["name"], "ok": False, "status": "failed", "message": error})
                _state["completed"] += 1
                continue
            cookie = _browser_cookie_cache.get(key) or cookie
            item = None
            for attempt in range(retries + 1):
                try:
                    outcome = None
                    browser_reason = ""
                    if key not in {"tjupt", "u2"}:
                        _state.update({"phase": "HTTP 请求", "message": f"{site['name']} 正在使用轻量 HTTP 签到"})
                        _runtime_log(ctx, "使用轻量 HTTP 检查签到状态", site=site["name"])
                        try:
                            outcome = await _http_checkin(ctx, key, site, cookie)
                        except _NeedsBrowser as fallback:
                            browser_reason = str(fallback)
                        except httpx.RequestError as fallback:
                            browser_reason = f"HTTP 网络异常（{type(fallback).__name__}），切换 CloakBrowser"
                    elif key == "u2":
                        browser_reason = "U2 使用浏览器原生表单提交，避免站点拦截 HTTP 自动请求"
                    else:
                        browser_reason = "TJUPT 需要页面交互验证"

                    if outcome is None:
                        _state.update({"phase": "浏览器降级", "message": f"{site['name']}：{browser_reason}"})
                        _runtime_log(ctx, browser_reason, level="warning", site=site["name"])

                        if outcome is None:
                            browser_timeout = 720 if key == "tjupt" else (300 if key in {"piggo", "hhan"} else (150 if key in {"audiences", "ourbits"} else 150))
                            browser_headless = bool(cfg.get("headless", True))
                            if key in {"audiences", "ourbits"}:
                                if os.path.exists("/.dockerenv"):
                                    display = _ensure_docker_display(ctx)
                                    if display:
                                        # Docker 中由 Xvfb 承载真实有头窗口，不会显示到用户桌面。
                                        browser_headless = False
                                        _runtime_log(
                                            ctx,
                                            f"Docker 虚拟显示器 {display} 已就绪，使用虚拟有头 CloakBrowser",
                                            site=site["name"],
                                        )
                                    else:
                                        browser_headless = True
                                        _runtime_log(
                                            ctx,
                                            f"Docker 无可用 DISPLAY，{site['name']} 只能回退无头模式",
                                            level="warning",
                                            site=site["name"],
                                        )
                                else:
                                    # 官方针对激进 Turnstile 的推荐配置要求 headed；仅两站覆盖
                                    # 通用“静默运行”开关，避免降低其余站点的后台体验。
                                    browser_headless = False
                                    _runtime_log(
                                        ctx,
                                        "Turnstile 站点强制使用有头 CloakBrowser",
                                        site=site["name"],
                                    )
                            _runtime_log(
                                ctx,
                                "使用真实 CloakBrowser 浏览器会话",
                                site=site["name"],
                            )
                            _state.update({
                                "phase": "浏览器签到",
                                "message": f"{site['name']}：CloakBrowser 正在处理签到",
                            })
                            outcome = await _with_heartbeat(
                                asyncio.to_thread(
                                    _site_cloak_checkin,
                                    ctx,
                                    key,
                                    site,
                                    cookie,
                                    browser_headless,
                                    loop,
                                ),
                                ctx,
                                site["name"],
                                "CloakBrowser 正在等待安全验证或页面结果",
                                max_wait=browser_timeout + 30,
                            )
                    status = str((outcome or {}).get("status") or "success")
                    if status == "failed":
                        raise RuntimeError(str((outcome or {}).get("message") or "网站返回签到失败"))
                    engine = str((outcome or {}).get("engine") or "browser")
                    item = {
                        "key": key, "site": site["name"], "ok": True, "status": status,
                        "engine": engine, "message": str((outcome or {}).get("message") or "签到完成"),
                    }
                    _runtime_log(ctx, item["message"], level="success", site=site["name"])
                    break
                except Exception as exc:  # noqa: BLE001
                    login_expired = "Cookie 已失效" in str(exc) or "网站返回登录页" in str(exc)
                    if attempt < retries and login_expired:
                        _state.update({"phase": "刷新 Cookie", "message": f"{site['name']} 登录状态失效，正在请求平台重新同步"})
                        _browser_cookie_cache.pop(key, None)
                        refreshed, refresh_error = await _refresh_site_cookie(ctx, key, site)
                        if refreshed:
                            cookie = refreshed
                        elif refresh_error:
                            item = {"key": key, "site": site["name"], "ok": False, "status": "failed", "engine": "http/browser", "message": refresh_error}
                            _runtime_log(ctx, refresh_error, level="error", site=site["name"])
                            break
                        await asyncio.sleep(min(interval, 5))
                    elif attempt < retries and _turnstile_session_retryable(key, exc):
                        _runtime_log(
                            ctx,
                            "当前 Turnstile/Cloudflare 会话未完成，已关闭并将在新指纹上下文中重试",
                            level="warning",
                            site=site["name"],
                        )
                        await asyncio.sleep(min(interval, 5))
                    elif attempt < retries and _retryable_error(exc):
                        await asyncio.sleep(interval)
                    else:
                        message = str(exc).strip() or type(exc).__name__
                        item = {"key": key, "site": site["name"], "ok": False, "status": "failed", "engine": "http/browser", "message": message}
                        _runtime_log(ctx, message, level="error", site=site["name"])
                        break
            results.append(item)
            if item and not item["ok"]:
                _runtime_log(ctx, "本站已记录失败，继续处理下一个站点", level="warning", site=site["name"])
            _state["completed"] += 1

        success = sum(1 for item in results if item["ok"])
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary = f"{source}签到完成：成功 {success}/{len(results)}"
        text = summary + "\n" + "\n".join(
            f"{'成功' if item['ok'] else '失败'} · {item['site']}：{item['message']}" for item in results
        )
        record = {"time": stamp, "ok": success == len(results), "summary": summary, "sites": results}
        history = _stored(_HISTORY_KEY, []) or []
        if not isinstance(history, list):
            history = []
        _persist(ctx, _HISTORY_KEY, [record, *history][:30])
        _persist(ctx, _LAST_KEY, text)
        if cfg.get("notify_result", True):
            rows = [
                {
                    "站点": item["site"],
                    "结果": "签到成功" if item["ok"] else "签到失败",
                }
                for item in results
            ]
            try:
                await ctx.notify(rows, level="success" if success == len(results) else "warning", category="PT站签到")
            except Exception as exc:  # noqa: BLE001
                ctx.log.warning("签到结果推送失败：%r", exc)
        failed_keys = [str(item["key"]) for item in results if not item["ok"]]
        retry_scheduled = bool(
            schedule_failed_retry
            and failed_keys
            and _schedule_failed_retry(ctx, failed_keys)
        )
        if retry_scheduled:
            retry_message = f"{summary}；失败站点将在 30 分钟后补签一次"
            _state.update({
                "running": False,
                "finished_at": stamp,
                "current": "",
                "phase": "等待失败站点补签",
                "message": retry_message,
            })
        else:
            _state.update({"running": False, "finished_at": stamp, "current": "", "phase": "完成", "message": summary})
        _runtime_log(ctx, summary, level="success" if success == len(results) else "warning")
        return {
            "ok": success == len(results),
            "message": text,
            "results": results,
            "retry_scheduled": retry_scheduled,
            "failed_keys": failed_keys,
        }


async def setup(ctx):
    global _run_lock, _active_run_task
    selected = (ctx.config or {}).get("selected_sites")
    if isinstance(selected, list) and "audiences" in selected:
        ctx.update_config({"selected_sites": [key for key in selected if key != "audiences"]})
    _run_lock = asyncio.Lock()
    _active_run_task = None
    _scheduled_tasks.clear()
    _failed_retry_tasks.clear()
    _state.update({"running": False, "started_at": "", "finished_at": "", "current": "", "phase": "", "message": "", "completed": 0, "total": 0})
    _runtime_logs.clear()
    _storage_state.clear()
    _storage_state.update(dict(await ctx.storage.items()))
    _runtime_log(ctx, "插件已加载，等待签到任务")
    _runtime_log(ctx, "CloakBrowser 依赖、内核、License Key、代理及免费会话队列由平台统一管理")

    @ctx.on_api("/meta", methods=["GET"])
    async def api_meta(req):
        configured = _configured_sites(_cfg(ctx))
        return {
            "ok": True,
            "sites": [{"key": key, **{field: site[field] for field in ("name", "domain", "group")}, "status": site.get("status", "ready")} for key, site in configured.items()],
            "defaults": {**DEFAULTS, "selected_sites": list(configured)},
        }

    @ctx.on_api("/status", methods=["GET"])
    async def api_status(req):
        return {"ok": True, **_state}

    @ctx.on_api("/run", methods=["POST"])
    async def api_run(req):
        if _run_lock and _run_lock.locked():
            return {"ok": False, "message": "签到任务已经在运行"}
        task = ctx.create_task(_run(ctx, "手动"), name="PT站手动签到")
        _tasks.add(task)
        task.add_done_callback(_task_done)
        return {"ok": True, "message": "签到任务已开始"}

    @ctx.on_api("/history", methods=["GET"])
    async def api_history(req):
        items = _stored(_HISTORY_KEY, []) or []
        return {"ok": True, "items": items if isinstance(items, list) else []}

    @ctx.on_api("/history/clear", methods=["POST"])
    async def api_history_clear(req):
        _persist(ctx, _HISTORY_KEY, [])
        return {"ok": True, "message": "签到记录已清空"}

    @ctx.on_api("/logs", methods=["GET"])
    async def api_logs(req):
        return {"ok": True, "items": list(reversed(_runtime_logs))}

    @ctx.on_api("/logs/clear", methods=["POST"])
    async def api_logs_clear(req):
        _runtime_logs.clear()
        _runtime_log(ctx, "运行日志已清空")
        return {"ok": True, "message": "运行日志已清空"}

    @ctx.on_api("/cookies/check", methods=["POST"])
    async def api_cookies_check(req):
        data = req.json if isinstance(req.json, dict) else {}
        configured = _configured_sites(_cfg(ctx))
        requested = data.get("selected_sites")
        selected = requested if isinstance(requested, list) else _cfg(ctx).get("selected_sites", list(configured))
        selected = list(dict.fromkeys(str(key) for key in selected if str(key) in configured))
        if not selected:
            return {"ok": False, "message": "请至少勾选一个站点", "items": []}
        rows = []
        for key in selected:
            cookie, error = await _site_cookie(ctx, key, configured[key])
            piggo = _same_site_domain(configured[key]["domain"], "piggo.me")
            ok = not error if piggo else bool(cookie)
            message = "猪猪登录凭证已填写，实际有效性将在签到时验证" if piggo and ok else ("平台 Cookie 可用" if cookie else error)
            rows.append({"key": key, "ok": ok, "message": message})
        return {"ok": all(row["ok"] for row in rows), "items": rows}

    @ctx.on_callback(pattern=rb"^pttj:")
    async def tjupt_choice(query):
        data = query.data or b""
        if isinstance(data, (bytes, bytearray)):
            data = bytes(data).decode("utf-8", "replace")
        try:
            _, token, raw_choice = str(data).split(":", 2)
            choice = int(raw_choice)
        except (TypeError, ValueError):
            await query.answer("选项数据无效", show_alert=True)
            return
        sender = await query.get_sender()
        owner_id = int(str(getattr(ctx.settings, "default_bot_chat_id", "") or 0))
        if sender is None or int(sender.id) != owner_id:
            await query.answer("只有平台主人可以确认签到答案", show_alert=True)
            return
        pending = _tjupt_pending.get(token)
        if not pending or pending["event"].is_set():
            await query.answer("这道验证题已失效", show_alert=True)
            return
        pending["choice"] = choice
        pending["event"].set()
        await query.answer("已选择，正在原页面提交")

    @ctx.action("run_now")
    async def run_now():
        if _run_lock and _run_lock.locked():
            return {"ok": True, "message": "签到任务已经在后台运行"}
        task = ctx.create_task(_run(ctx, "手动"), name="PT站手动签到")
        _tasks.add(task)
        task.add_done_callback(_task_done)
        return {"ok": True, "message": "签到任务已开始，完成后会推送汇总结果"}

    @ctx.action("view_result")
    async def view_result():
        text = str(_stored(_LAST_KEY, "") or "")
        return {"ok": bool(text), "message": text or "暂无签到记录"}

    cfg = _cfg(ctx)
    if cfg.get("auto_checkin", True):
        hour = _bounded(cfg.get("checkin_hour"), 8, 0, 23)
        minute = _bounded(cfg.get("checkin_minute"), 10, 0, 59)
        u2_hour = _bounded(cfg.get("u2_checkin_hour"), 9, 9, 23)
        u2_minute = _bounded(cfg.get("u2_checkin_minute"), 0, 0, 59)

        async def scheduled_main():
            configured = _configured_sites(_cfg(ctx))
            selected = _cfg(ctx).get("selected_sites", list(configured))
            if not isinstance(selected, list):
                selected = list(configured)
            non_u2 = [str(key) for key in selected if str(key) in configured and str(key) != "u2"]
            if non_u2:
                return await _run_scheduled(ctx, "定时", non_u2)
            return {"ok": True, "skipped": True, "message": "没有启用非 U2 站点，未执行定时签到"}

        async def scheduled_u2():
            configured = _configured_sites(_cfg(ctx))
            selected = _cfg(ctx).get("selected_sites", list(configured))
            if not isinstance(selected, list) or "u2" in selected:
                return await _run_scheduled(ctx, "定时(U2)", ["u2"])
            return {"ok": True, "skipped": True, "message": "未启用 U2，未执行 U2 定时签到"}

        # U2 站点只允许北京时间 09:00 后签到，单独注册定时任务，
        # 其他站点仍按原有全局时间执行。
        ctx.schedule_cron("PT站每日签到", scheduled_main, hour=hour, minute=minute)
        ctx.schedule_cron("PT站 U2 签到", scheduled_u2, hour=u2_hour, minute=u2_minute)


async def teardown(ctx):
    global _active_run_task, _xvfb_display, _xvfb_process
    _active_run_task = None
    _state.update({"running": False, "current": "", "phase": "", "message": ""})
    for pending in list(_tjupt_pending.values()):
        pending["choice"] = None
        pending["event"].set()
    _tjupt_pending.clear()
    _browser_cookie_cache.clear()
    tasks = list(_tasks)
    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    _tasks.clear()
    _scheduled_tasks.clear()
    _failed_retry_tasks.clear()
    if _storage_tasks:
        await asyncio.gather(*list(_storage_tasks), return_exceptions=True)
    _storage_tasks.clear()
    _storage_state.clear()
    if _xvfb_process is not None and _xvfb_process.poll() is None:
        _xvfb_process.terminate()
        try:
            _xvfb_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _xvfb_process.kill()
    if _xvfb_display and os.environ.get("DISPLAY") == _xvfb_display:
        os.environ.pop("DISPLAY", None)
    _xvfb_process = None
    _xvfb_display = ""
