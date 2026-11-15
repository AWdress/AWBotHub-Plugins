"""Read public Maoyan web rankings inside one host-owned browser session."""

from __future__ import annotations

import asyncio
from datetime import datetime
import re
from urllib.parse import parse_qs, urlsplit

from ._base import RankProvider
from ._maoyan import (MAOYAN_URL, MEDIA_LABELS, PLATFORM_LABELS, PLATFORM_TYPE,
                     SERIES_TYPE, validate_web_payload)


MAOYAN_WEB_URL = f"{MAOYAN_URL}/dashboard/web-heat"
_WEB_PATH = "/i/api/encrypt/dashboard/webHeatData"
_INITIALIZE_TIMEOUT_SECONDS = 20.0
_REQUEST_TIMEOUT_SECONDS = 12.0
_SERIES_LABELS = {SERIES_TYPE[key]: value for key, value in MEDIA_LABELS.items()}
_PLATFORM_LABELS = {PLATFORM_TYPE[key]: value for key, value in PLATFORM_LABELS.items()}


class _BoardError(RuntimeError):
    """Controlled public-data error, never a raw browser exception."""


def ranking_keys(options):
    """Keep the existing media/platform selection semantics and stable keys."""
    options = options or {}
    platforms = RankProvider.as_list(options.get("web_platforms", options.get("maoyan_web_platforms")))
    media_types = RankProvider.as_list(options.get("web_types", options.get("maoyan_web_types")))
    return dict.fromkeys(f"{SERIES_TYPE[media]}|{PLATFORM_TYPE[platform]}"
                         for platform in platforms if platform in PLATFORM_TYPE
                         for media in media_types if media in SERIES_TYPE)


def collection_timeout(options):
    """Budget serial native selections, including each media's default board."""
    keys = ranking_keys(options)
    media_count = len({key.split("|", 1)[0] for key in keys})
    return max(45.0, _INITIALIZE_TIMEOUT_SECONDS + (len(keys) + media_count) * (_REQUEST_TIMEOUT_SECONDS + 1) + 5)


def _is_web_response(response):
    try:
        parsed = urlsplit(response.url)
        return parsed.scheme == "https" and parsed.hostname == "piaofang.maoyan.com" and parsed.path == _WEB_PATH
    except (AttributeError, TypeError, ValueError):
        return False


def _show_date(url):
    values = parse_qs(urlsplit(url).query).get("showDate", [])
    if len(values) != 1 or len(values[0]) != 8 or not values[0].isdigit():
        raise _BoardError("猫眼网播页面未提供有效榜单日期")
    try:
        parsed = datetime.strptime(values[0], "%Y%m%d")
    except ValueError:
        raise _BoardError("猫眼网播页面榜单日期格式无效") from None
    if parsed.strftime("%Y%m%d") != values[0]:
        raise _BoardError("猫眼网播页面榜单日期格式无效")
    return values[0]


def _response_key(url):
    """The native default omits seriesType (4) and platformType (all)."""
    query = parse_qs(urlsplit(url).query, keep_blank_values=True)
    series = query.get("seriesType", ["4"])
    platform = query.get("platformType", [""])
    if (len(series) != 1 or series[0] not in _SERIES_LABELS
            or len(platform) != 1 or platform[0] not in _PLATFORM_LABELS):
        raise _BoardError("猫眼网播响应的榜单类型或平台无效")
    return f"{series[0]}|{platform[0]}"


def _matches_board(response, key, show_date):
    if not _is_web_response(response):
        return False
    try:
        return _response_key(response.url) == key and _show_date(response.url) == show_date
    except (RuntimeError, TypeError, ValueError):
        return False


async def _read_payload(response):
    if response.status != 200:
        raise _BoardError(f"猫眼网播请求失败（HTTP {response.status}）")
    try:
        payload = await response.json()
    except asyncio.CancelledError:
        raise
    except Exception:
        raise _BoardError("猫眼网播未返回有效 JSON") from None
    try:
        return validate_web_payload(payload)
    except RuntimeError as exc:
        raise _BoardError(str(exc)) from None


async def _selected_key(page):
    series = (await page.locator(".plat-choice.active:not(.plat-select)").inner_text(timeout=3000)).strip()
    platform = (await page.locator(".plat-select").inner_text(timeout=3000)).strip()
    series_type = next((key for key, label in _SERIES_LABELS.items() if label == series), None)
    platform_type = next((key for key, label in _PLATFORM_LABELS.items() if label == platform), None)
    if series_type is None or platform_type is None:
        raise _BoardError("猫眼官网筛选控件已变化，无法确认当前榜单")
    return f"{series_type}|{platform_type}"


async def _select_series(page, series_type):
    await page.locator(".plat-choice").filter(
        has_text=re.compile(r"^" + re.escape(_SERIES_LABELS[series_type]) + r"$")
    ).click(timeout=3000)


async def _select_platform(page, platform_type):
    await page.locator(".plat-select").click(timeout=3000)
    await page.locator(".option-item").filter(
        has_text=re.compile(r"^" + re.escape(_PLATFORM_LABELS[platform_type]) + r"$")
    ).click(timeout=3000)


async def collect_web_rankings(page, options, *, timeout_seconds=None, checkpoint=None):
    """Return JSON-only rankings/errors/cookies without owning the browser.

    The caller opens ``MAOYAN_WEB_URL`` with its configured ``ctx.browser`` and
    gives the whole browser stage a bounded deadline. Completed combinations
    survive this helper's timeout; cancellation propagates to SDK cleanup.
    """
    keys = ranking_keys(options)
    # The caller owns this checkpoint too: SDK/outer timeouts must not erase
    # combinations already validated before browser cleanup started.
    result = checkpoint if checkpoint is not None else {"web_data": {}, "web_errors": {}, "cookies": {}}
    if not keys:
        return result
    if timeout_seconds is None:
        timeout_seconds = collection_timeout(options)
    try:
        async with asyncio.timeout(timeout_seconds):
            try:
                # SDK navigates before the async callback. Reload once with a
                # response waiter already installed, so startup cannot miss the
                # page's first successful normal signed API request.
                async with page.expect_response(_is_web_response,
                                                timeout=min(timeout_seconds, _INITIALIZE_TIMEOUT_SECONDS) * 1000) as waiting:
                    await page.reload(wait_until="domcontentloaded",
                                      timeout=min(timeout_seconds, _INITIALIZE_TIMEOUT_SECONDS) * 1000)
                initial = await waiting.value
                show_date = _show_date(initial.url)
                initial_key = _response_key(initial.url)
                payload = await _read_payload(initial)
                observed = {initial_key: payload}
                if initial_key in keys:
                    result["web_data"][initial_key] = payload
                    result["web_errors"].pop(initial_key, None)
            except asyncio.CancelledError:
                raise
            except _BoardError as exc:
                result["web_errors"].update(dict.fromkeys(keys, str(exc)))
                return result
            except Exception:
                result["web_errors"].update(dict.fromkeys(keys, "猫眼网播初始化失败（页面未完成验证、响应无效或加载超时）"))
                return result

            try:
                result["cookies"] = {cookie["name"]: cookie["value"] for cookie in await page.context.cookies()
                                     if isinstance(cookie, dict) and isinstance(cookie.get("name"), str)
                                     and isinstance(cookie.get("value"), str)}
            except asyncio.CancelledError:
                raise
            except Exception:
                pass  # Movie box is independently readable without cookies.

            async def switch(key, action):
                try:
                    # Only official filter clicks make requests. Arbitrary
                    # window.fetch is not signed by the current site (418).
                    # Never export, forge or replay its security parameters.
                    async with asyncio.timeout(_REQUEST_TIMEOUT_SECONDS):
                        async with page.expect_response(
                                lambda response: _matches_board(response, key, show_date),
                                timeout=_REQUEST_TIMEOUT_SECONDS * 1000) as waiting:
                            await action()
                        payload = await _read_payload(await waiting.value)
                        observed[key] = payload
                        if key in keys:
                            result["web_data"][key] = payload
                            result["web_errors"].pop(key, None)
                except asyncio.CancelledError:
                    raise
                except TimeoutError:
                    if key in keys:
                        result["web_errors"][key] = "猫眼网播官网筛选超时"
                except _BoardError as exc:
                    if key in keys:
                        result["web_errors"][key] = str(exc)
                except Exception:
                    # Browser exceptions can contain URLs/security parameters.
                    if key in keys:
                        result["web_errors"][key] = "猫眼网播官网筛选失败或超时"

            # Changing media resets the website's platform to all. Group by
            # media so we never race multiple selections in the same page.
            media_types = list(dict.fromkeys(key.split("|", 1)[0] for key in keys))
            initial_media = initial_key.split("|", 1)[0]
            if initial_media in media_types:
                media_types.remove(initial_media)
                media_types.insert(0, initial_media)
            for series_type in media_types:
                if all(key in result["web_data"] or key in result["web_errors"]
                       for key in keys if key.split("|", 1)[0] == series_type):
                    continue
                if (await _selected_key(page)).split("|", 1)[0] != series_type:
                    await switch(f"{series_type}|", lambda: _select_series(page, series_type))
                for key in keys:
                    if key.split("|", 1)[0] != series_type or key in result["web_data"] or key in result["web_errors"]:
                        continue
                    current_key = await _selected_key(page)
                    if current_key.split("|", 1)[0] != series_type:
                        result["web_errors"][key] = "猫眼官网未切换到所选媒体类型"
                    elif current_key == key:
                        if key in observed:
                            result["web_data"][key] = observed[key]
                        else:
                            result["web_errors"][key] = "猫眼官网未返回所选榜单的有效响应"
                    else:
                        await switch(key, lambda: _select_platform(page, key.split("|", 1)[1]))
    except TimeoutError:
        for key in keys:
            if key not in result["web_data"] and key not in result["web_errors"]:
                result["web_errors"][key] = "猫眼网播读取达到时间上限"
    except asyncio.CancelledError:
        raise
    except Exception:
        for key in keys:
            if key not in result["web_data"] and key not in result["web_errors"]:
                result["web_errors"][key] = "猫眼官网筛选控件不可用或已变化"
    return result
