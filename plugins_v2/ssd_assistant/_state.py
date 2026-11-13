"""发送/点击前持久登记；结果不明确时不自动重试，避免重复参与或扣款。"""
from __future__ import annotations

import asyncio
import copy
import math
import time


_KEY = "actions:v1"
_TTL = 90 * 86400
_LIMIT = 5000


class ActionJournal:
    def __init__(self, storage):
        self.storage = storage
        self.lock = asyncio.Lock()
        self.items = {}

    async def initialize(self):
        raw = await self.storage.get(_KEY, None)
        if raw is None:
            return
        if (not isinstance(raw, dict) or raw.get("version") != 1
                or not isinstance(raw.get("items"), list)):
            raise ValueError("SSD 助手操作记录格式异常，为防重复操作，已停止启用")
        for row in raw["items"]:
            if (not isinstance(row, dict) or not isinstance(row.get("key"), str)
                    or row.get("kind") not in ("lottery", "transfer")
                    or row.get("status") not in ("prepared", "sent", "clicked", "uncertain", "failed", "skipped")
                    or type(row.get("created_at")) not in (int, float)
                    or not math.isfinite(row["created_at"])):
                raise ValueError("SSD 助手操作记录损坏，为防重复操作，已停止启用")
            row = copy.deepcopy(row)
            if row["status"] == "prepared":
                row["status"] = "uncertain"
                row["detail"] = "上次操作中断，结果未确认；请到群内核对，不自动补发或重试"
            self.items[row["key"]] = row

    async def reserve(self, key, **values) -> bool:
        async with self.lock:
            if key in self.items:
                return False
            now = time.time()
            retained = {name: row for name, row in self.items.items()
                        if now - row["created_at"] < _TTL}
            if len(retained) >= _LIMIT:
                raise RuntimeError("SSD 助手操作记录已达安全上限，本次不执行，请联系开发者核对")
            retained[key] = {**values, "key": key, "status": "prepared",
                             "created_at": now, "updated_at": now}
            # 写入异常也保留内存占位；不确定是否落盘时绝不重复发送。
            self.items = retained
            await self._save()
            return True

    async def finish(self, key, status, detail, **values):
        async with self.lock:
            self.items[key].update(values, status=status, detail=detail, updated_at=time.time())
            await self._save()

    async def _save(self):
        await self.storage.set(_KEY, {"version": 1, "items": copy.deepcopy(list(self.items.values()))})

    def history(self):
        return copy.deepcopy(sorted(self.items.values(), key=lambda row: row["created_at"], reverse=True)[:100])
