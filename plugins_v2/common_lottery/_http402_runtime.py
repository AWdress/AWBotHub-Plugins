"""可信公告的关键词参与流程；发送前持久占位，异常不补发。"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import math
import time
from random import randint

from telethon import utils

from ._http402 import TARGET_GROUP, _usernames, parse_lottery, trusted_sender


_STORAGE_KEY = "http402:actions:v1"
_RETENTION = 180 * 86400
_LIMIT = 5000


class Http402Lottery:
    def __init__(self, ctx, *, group_allowed, wait_range, check_joined, ensure_joined):
        self.ctx = ctx
        self.group_allowed, self.wait_range = group_allowed, wait_range
        self.check_joined, self.ensure_joined = check_joined, ensure_joined
        self.closed = False
        self.lock = asyncio.Lock()
        self.records = {}
        self.tasks = set()
        self.accounts = {}

    async def initialize(self):
        raw = await self.ctx.storage.get(_STORAGE_KEY, None)
        if raw is None:
            return
        if not isinstance(raw, dict) or raw.get("version") != 1 or not isinstance(raw.get("items"), dict):
            raise ValueError("通用抽奖参与记录格式异常，为防重复参与，请先核对数据")
        for key, row in raw["items"].items():
            if (not isinstance(key, str) or not isinstance(row, dict)
                    or type(row.get("created_at")) not in (int, float)
                    or not math.isfinite(row["created_at"])
                    or row.get("state") not in {"reserved", "sent", "skipped", "uncertain"}):
                raise ValueError("通用抽奖参与记录损坏，为防重复参与，请先核对数据")
            self.records[key] = copy.deepcopy(row)

    def stop(self):
        self.closed = True
        for task in tuple(self.tasks):
            task.cancel()

    async def _save(self):
        await self.ctx.storage.set(_STORAGE_KEY, {"version": 1, "items": copy.deepcopy(self.records)})

    async def _reserve(self, key, source_key):
        async with self.lock:
            if source_key in self.records:
                return False
            if key in self.records:
                # 副本也登记消息身份，之后编辑副本口令不能再变成新活动。
                if len(self.records) < _LIMIT:
                    self.records[source_key] = copy.deepcopy(self.records[key])
                    await self._save()
                return False
            now = time.time()
            self.records = {name: row for name, row in self.records.items()
                            if now - row["created_at"] < _RETENTION}
            if len(self.records) + 2 > _LIMIT:
                raise RuntimeError("通用抽奖防重记录达到安全上限，本次不发送")
            # 写入结果未知时仍保留内存占位，不重复尝试。
            self.records[key] = {"created_at": now, "state": "reserved"}
            self.records[source_key] = copy.deepcopy(self.records[key])
            await self._save()
            return True

    async def _finish(self, key, state):
        async with self.lock:
            self.records[key]["state"] = state
            try:
                await self._save()
            except Exception:
                self.ctx.log.warning("[通用抽奖] 保存参与结果失败，保留防重占位，不自动补发")

    async def _own_id(self, client):
        identity = id(client)
        if identity not in self.accounts or self.accounts[identity][0] is not client:
            account = await asyncio.wait_for(client.get_me(), timeout=10)
            account_id = getattr(account, "id", None)
            if type(account_id) is not int or account_id <= 0:
                raise ValueError("无法确认 Telegram 账号")
            self.accounts[identity] = (client, account_id)
        return self.accounts[identity][1]

    def _allowed(self, source_id, target_id):
        return (not self.closed and (self.group_allowed(self.ctx.config, source_id)
                                    or self.group_allowed(self.ctx.config, target_id)))

    @staticmethod
    def _fresh(message):
        date = getattr(message, "date", None)
        if date is None:
            return True
        try:
            age = time.time() - date.timestamp()
            return math.isfinite(age) and -60 <= age <= 62 * 86400
        except (AttributeError, ValueError, TypeError, OSError, OverflowError):
            return False

    async def handle(self, event):
        if self.closed:
            return
        message, client, source_id = event.message, event.client, event.chat_id
        info = parse_lottery(message)
        if info is None or not self._fresh(message):
            return
        try:
            sender = await asyncio.wait_for(event.get_sender(), timeout=10)
            if not trusted_sender(sender, message):
                return
            # 固定参与目标；不将领奖人、频道页脚或任意外链解析为加群要求。
            target = await asyncio.wait_for(client.get_entity(TARGET_GROUP), timeout=10)
            if (not getattr(target, "megagroup", False) or getattr(target, "broadcast", False)
                    or TARGET_GROUP not in _usernames(target)):
                self.ctx.log.warning("[通用抽奖] 色花堂参与目标不是预期群组，本次不发送")
                return
            target_id = utils.get_peer_id(target)
            if not self._allowed(source_id, target_id):
                return
            account_id = await self._own_id(client)
            identity = json.dumps([account_id, target_id, info["edition"], info["activity"], info["keyword"]],
                                  ensure_ascii=False, separators=(",", ":"))
            key = "campaign:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()
            source = json.dumps([account_id, source_id, message.id], separators=(",", ":"))
            source_key = "message:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
            if not await self._reserve(key, source_key):
                return
            task = self.ctx.create_task(self._participate(
                client, message, source_id, target, target_id, info, key,
            ), name="common-lottery-http402")
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.ctx.log.warning("[通用抽奖] 色花堂抽奖准备失败（%s），未发送口令", type(exc).__name__)

    async def _latest(self, client, message, source_id, info):
        latest = await asyncio.wait_for(client.get_messages(source_id, ids=message.id), timeout=10)
        return (latest is not None and getattr(latest, "id", None) == message.id
                and getattr(latest, "sender_id", None) == getattr(message, "sender_id", None)
                and getattr(latest, "chat_id", source_id) == source_id
                and not getattr(latest, "fwd_from", None) and not getattr(latest, "out", False)
                and self._fresh(latest) and parse_lottery(latest) == info)

    async def _notify(self, client, message, info, status, *, level="info"):
        if not self.ctx.config.get("notify_owner", True):
            return
        try:
            await self.ctx.notify({"状态": status, "活动": info["activity"],
                                   "参与群": "@" + TARGET_GROUP,
                                   "来源": getattr(message, "link", "")},
                                  level=level, category="通用抽奖", account=client)
        except Exception:
            pass

    async def _participate(self, client, message, source_id, target, target_id, info, key):
        attempted = False
        try:
            lower, upper = self.wait_range(self.ctx.config)
            delay = randint(max(0, min(600, lower)), max(0, min(600, upper)))
            self.ctx.log.info("[通用抽奖] 色花堂抽奖将在 %s 秒后向 @%s 发送参与口令", delay, TARGET_GROUP)
            await asyncio.sleep(delay)
            if not self._allowed(source_id, target_id) or not await self._latest(client, message, source_id, info):
                await self._finish(key, "skipped")
                return
            link = "https://t.me/" + TARGET_GROUP
            if not await self.check_joined(client, link, self.ctx.log):
                if not self.ctx.config.get("auto_join", False):
                    await self._finish(key, "skipped")
                    await self._notify(client, message, info, "需手动加入参与群")
                    return
                ok, detail = await self.ensure_joined(client, link)
                self.ctx.log.info("[通用抽奖] %s", detail)
                if not ok:
                    await self._finish(key, "skipped")
                    await self._notify(client, message, info, "加入参与群失败", level="warning")
                    return
                await asyncio.sleep(randint(2, 5))
            # 等待、加群与读取期间可能已经开奖；不发送过时口令。
            if not self._allowed(source_id, target_id) or not await self._latest(client, message, source_id, info):
                await self._finish(key, "skipped")
                return
            attempted = True
            await asyncio.wait_for(client.send_message(
                target, info["keyword"], parse_mode=None, link_preview=False,
            ), timeout=20)
            await self._finish(key, "sent")
            self.ctx.log.info("[通用抽奖] 色花堂参与口令已发送到 @%s", TARGET_GROUP)
            await self._notify(client, message, info, "参与口令已发送", level="success")
        except asyncio.CancelledError:
            # 取消时保留持久占位；可能已送达 Telegram，不追加发送。
            raise
        except Exception as exc:
            await self._finish(key, "uncertain" if attempted else "skipped")
            self.ctx.log.warning("[通用抽奖] 色花堂抽奖未完成（%s），未自动补发", type(exc).__name__)
            await self._notify(client, message, info,
                               "发送结果不明，未自动补发" if attempted else "参与前检查失败，未发送口令",
                               level="warning")
