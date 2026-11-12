"""Bounded, persistent correlation of SSD requests and detached bot receipts.

This cache never infers a transaction from an amount or display name alone.
The caller must first authenticate the official bot and verify success text.
"""
from __future__ import annotations

import asyncio
import copy
import math
import re
import time
from decimal import Decimal, InvalidOperation


_KEY = "ssd:requests"
_VERSION = 1
_TTL = 30 * 60
_MAX_ITEMS = 200
_MAX_ALIASES = 256


def _integer(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return None
    try:
        result = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if result == 0 or (positive and result < 0):
        return None
    return result


def _amount(value):
    if not isinstance(value, str) or len(value) > 80:
        return None
    value = value.strip()
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        return None
    try:
        number = Decimal(value)
    except InvalidOperation:
        return None
    if not number.is_finite() or number <= 0:
        return None
    # Do not use Decimal.normalize(): its context precision can round identities.
    normalized = format(number, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized


def _ids(values, command_id):
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        return None
    result = []
    for value in values[-_MAX_ALIASES:]:
        number = _integer(value, positive=True)
        if number is None or number <= command_id:
            return None
        if number not in result:
            result.append(number)
    return result


def _source(snapshot):
    return snapshot["chat_id"], snapshot["own_id"], snapshot["command_id"]


def _snapshot(value, now):
    if not isinstance(value, dict):
        return None
    result = {}
    for field in ("chat_id", "command_id", "own_id", "sender_id", "recipient_id", "user_id", "target_id"):
        number = _integer(value.get(field), positive=field != "chat_id")
        if number is None:
            return None
        result[field] = number
    direction = value.get("direction")
    if direction not in ("in", "out"):
        return None
    result["direction"] = direction
    own_field, other_field = (("sender_id", "recipient_id") if direction == "out"
                              else ("recipient_id", "sender_id"))
    if (result[own_field] != result["own_id"] or result[other_field] != result["user_id"]
            or result["sender_id"] == result["recipient_id"]):
        return None
    amount = _amount(value.get("amount"))
    if amount is None:
        return None
    result["amount"] = amount
    name = value.get("user_name")
    if not isinstance(name, str):
        return None
    result["user_name"] = name.strip()[:256] or f"用户{result['user_id']}"
    created = value.get("created_at")
    if isinstance(created, bool) or not isinstance(created, (int, float)):
        return None
    try:
        created = float(created)
    except (ValueError, OverflowError):
        return None
    if not math.isfinite(created) or created > now + 60 or now - created >= _TTL:
        return None
    result["created_at"] = created
    for field in ("confirmation_ids", "receipt_ids"):
        aliases = _ids(value.get(field), result["command_id"])
        if aliases is None:
            return None
        result[field] = aliases
    return result


def _same_request(left, right):
    fields = ("chat_id", "command_id", "own_id", "sender_id", "recipient_id", "amount", "direction", "user_id")
    return all(left[field] == right[field] for field in fields)


class SSDRequests:
    """A 30-minute, at-most-200-request cache in plugin-local storage."""

    def __init__(self, ctx):
        self._ctx = ctx
        self._storage = ctx.storage
        self._lock = asyncio.Lock()
        self._items = {}

    async def initialize(self):
        async with self._lock:
            try:
                raw = await self._storage.get(_KEY, None)
            except Exception:
                self._items = {}
                self._warn("SSD 转账关联缓存读取失败，本轮不使用旧关联记录")
                return
            if (not isinstance(raw, dict) or type(raw.get("version")) is not int
                    or raw["version"] != _VERSION or not isinstance(raw.get("items"), list)):
                self._items = {}
                return
            now = time.time()
            restored = {}
            conflicts = set()
            for value in raw["items"][-_MAX_ITEMS:]:
                item = _snapshot(value, now)
                if item is None:
                    continue
                key = _source(item)
                if key in conflicts:
                    continue
                previous = restored.get(key)
                if previous is not None:
                    if not _same_request(previous, item):
                        # A conflicting identity for the same command is not evidence.
                        restored.pop(key, None)
                        conflicts.add(key)
                        continue
                    item = self._merge(previous, item)
                restored[key] = item
            self._items = self._bounded(restored, now)

    async def remember(self, snapshot):
        async with self._lock:
            now = time.time()
            incoming = _snapshot(snapshot, now)
            if incoming is None:
                return None
            items = self._bounded(self._items, now)
            key = _source(incoming)
            previous = items.get(key)
            if previous is not None:
                if not _same_request(previous, incoming):
                    return None
                incoming = self._merge(previous, incoming)
            else:
                # Only bind() may establish a receipt association.
                incoming["receipt_ids"] = []
            items[key] = incoming
            items = self._bounded(items, now)
            await self._save(items)
            return copy.deepcopy(items.get(key))

    async def bind(self, snapshot, receipt_id):
        async with self._lock:
            now = time.time()
            incoming = _snapshot(snapshot, now)
            receipt = _integer(receipt_id, positive=True)
            if incoming is None or receipt is None or receipt <= incoming["command_id"]:
                return None
            items = self._bounded(self._items, now)
            key = _source(incoming)
            previous = items.get(key)
            if previous is None or not _same_request(previous, incoming):
                return None
            if any(_source(item) != key and item["chat_id"] == incoming["chat_id"]
                   and item["own_id"] == incoming["own_id"] and receipt in item["receipt_ids"]
                   for item in items.values()):
                return None
            bound = copy.deepcopy(previous)
            bound["receipt_ids"] = list(dict.fromkeys([*bound["receipt_ids"], receipt]))[-_MAX_ALIASES:]
            items[key] = bound
            await self._save(items)
            return copy.deepcopy(bound)

    def resolve(self, chat_id, own_id, receipt_id, reply_id=None,
                sender_id=None, recipient_id=None, amount=None):
        chat = _integer(chat_id)
        own = _integer(own_id, positive=True)
        receipt = _integer(receipt_id, positive=True)
        reply = _integer(reply_id, positive=True) if reply_id is not None else None
        sender = _integer(sender_id, positive=True) if sender_id is not None else None
        recipient = _integer(recipient_id, positive=True) if recipient_id is not None else None
        normalized_amount = _amount(amount) if amount is not None else None
        if (chat is None or own is None or receipt is None
                or (reply_id is not None and reply is None)
                or (sender_id is not None and sender is None)
                or (recipient_id is not None and recipient is None)
                or (amount is not None and normalized_amount is None)):
            return None
        items = [item for item in self._bounded(self._items, time.time()).values()
                 if item["chat_id"] == chat and item["own_id"] == own
                 and receipt > item["command_id"]]

        def matches(item):
            return ((sender is None or sender == item["sender_id"])
                    and (recipient is None or recipient == item["recipient_id"])
                    and (normalized_amount is None or normalized_amount == item["amount"]))

        bound = [item for item in items if receipt in item["receipt_ids"]]
        if bound:
            return copy.deepcopy(bound[0]) if len(bound) == 1 and matches(bound[0]) else None
        if reply is not None:
            exact = [item for item in items if reply == item["command_id"] or reply in item["confirmation_ids"]]
            return copy.deepcopy(exact[0]) if len(exact) == 1 and matches(exact[0]) else None
        if sender is None or recipient is None or normalized_amount is None:
            return None
        candidates = [item for item in items if matches(item)]
        return copy.deepcopy(candidates[0]) if len(candidates) == 1 else None

    @staticmethod
    def _merge(previous, incoming):
        merged = copy.deepcopy(previous)
        merged["confirmation_ids"] = list(dict.fromkeys(
            [*previous["confirmation_ids"], *incoming["confirmation_ids"]]
        ))[-_MAX_ALIASES:]
        # Never refresh creation time or trust externally supplied receipt aliases.
        return merged

    @staticmethod
    def _bounded(items, now):
        live = [item for item in items.values() if now - item["created_at"] < _TTL
                and item["created_at"] <= now + 60]
        live.sort(key=lambda item: (item["created_at"], item["command_id"]))
        return {_source(item): item for item in live[-_MAX_ITEMS:]}

    async def _save(self, items):
        payload = {"version": _VERSION, "items": copy.deepcopy(list(items.values()))}
        await self._storage.set(_KEY, payload)
        self._items = items

    def _warn(self, text):
        try:
            self._ctx.log.warning(text)
        except Exception:
            pass
