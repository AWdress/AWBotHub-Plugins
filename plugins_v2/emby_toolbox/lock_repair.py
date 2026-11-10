"""Explicit, opt-in repair of Emby whole-item locks.

This module deliberately does not infer who created an existing lock.  Callers
must explain that risk and ask the user to select the root item IDs.  Preview is
read-only; applying a short-lived, one-use plan first requires durable storage
of the original lock states.  No credentials or complete metadata are saved.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import inspect
import json
import re
import secrets
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple


_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_TYPES = frozenset(("Movie", "Series", "Season", "Episode"))
_ORDER = {"Series": 0, "Movie": 1, "Season": 2, "Episode": 3}
_MAX_ROOTS = 500
_MAX_SAMPLES = 100
_MAX_CANDIDATES = 200000
_PLAN_SECONDS = 30 * 60


def whole_locked(item: Dict[str, Any]) -> bool:
    """Return the explicit whole-item lock, rejecting absent/ambiguous data.

    ``LockData`` is the writable DTO field.  Some read endpoints instead expose
    ``IsLocked``; accepting that alias must never turn a missing field, null,
    numeric value, or contradictory response into an assumed unlocked state.
    """
    if not isinstance(item, dict):
        raise ValueError("Emby 条目不是有效对象")
    values = [item[key] for key in ("LockData", "IsLocked") if key in item]
    if not values or any(type(value) is not bool for value in values):
        raise ValueError("Emby 未返回明确的条目整体锁定状态")
    if any(value != values[0] for value in values[1:]):
        raise ValueError("Emby 返回的条目整体锁定状态相互冲突")
    return values[0]


def locked_fields(item: Dict[str, Any]) -> List[str]:
    """Copy a valid field-lock list; missing/null mean an empty list."""
    if not isinstance(item, dict):
        raise ValueError("Emby 条目不是有效对象")
    value = item.get("LockedFields")
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(part, str) for part in value):
        raise ValueError("Emby 返回的字段锁不是有效的字符串列表")
    return list(value)


def _id(value: Any) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError("Emby 条目 ID 格式不正确")
    return value


def _relation(item: Dict[str, Any], key: str) -> str:
    value = item.get(key)
    return "" if value in (None, "") else _id(value)


def _stamp(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class _Snapshot:
    item_id: str
    item_type: str
    name: str
    fields: Tuple[str, ...]
    locked: bool
    lock_data: Optional[bool]
    is_locked: Optional[bool]
    parent_id: str
    series_id: str

    def matches(self, other: "_Snapshot", *, expected_lock: Optional[bool] = None) -> bool:
        return (
            self.item_id == other.item_id
            and self.item_type == other.item_type
            and set(self.fields) == set(other.fields)
            and self.parent_id == other.parent_id
            and self.series_id == other.series_id
            and other.locked == (self.locked if expected_lock is None else expected_lock)
        )

    def backup(self) -> Dict[str, Any]:
        result = {
            "id": self.item_id,
            "type": self.item_type,
            "name": self.name,
            "LockedFields": list(self.fields),
        }
        if self.lock_data is not None:
            result["LockData"] = self.lock_data
        if self.is_locked is not None:
            result["IsLocked"] = self.is_locked
        return result


def _snapshot(item: Dict[str, Any], expected_id: Optional[str] = None) -> _Snapshot:
    if not isinstance(item, dict):
        raise ValueError("Emby 条目不是有效对象")
    item_id = _id(item.get("Id"))
    if expected_id is not None and item_id != expected_id:
        raise ValueError("Emby 返回的条目与请求 ID 不一致")
    item_type = item.get("Type")
    if item_type not in _TYPES:
        raise ValueError("只支持电影、剧集、季和单集条目")
    locked = whole_locked(item)
    return _Snapshot(
        item_id=item_id,
        item_type=item_type,
        name=item.get("Name", "")[:200] if isinstance(item.get("Name"), str) else "",
        fields=tuple(locked_fields(item)),
        locked=locked,
        lock_data=item.get("LockData") if "LockData" in item else None,
        is_locked=item.get("IsLocked") if "IsLocked" in item else None,
        parent_id=_relation(item, "ParentId"),
        series_id=_relation(item, "SeriesId"),
    )


@dataclass
class _Entry:
    snapshot: _Snapshot
    explicit_root: bool = False
    # Ancestors are kept as small lock snapshots, never complete metadata.
    paths: List[Tuple[_Snapshot, ...]] = field(default_factory=list)


@dataclass
class _Plan:
    token: str
    binding: str
    preview_epoch: float
    expires_epoch: float
    entries: Dict[str, _Entry]
    root_count: int
    child_count: int
    requested_count: int


class _Cancelled(Exception):
    pass


class _ReadFailure(Exception):
    pass


class LockRepair:
    """Manual repair controller with read-only preview and one-use apply.

    Callbacks are synchronous. ``get_children`` must either return a complete
    list of full descendant DTOs for the given root or raise; partial lists
    cannot be detected here and must not be returned by its adapter.
    ``save_backup`` must return only after the backup has durably persisted.
    """

    def __init__(
        self,
        get_item: Callable[[Dict[str, Any], str], Dict[str, Any]],
        update_item: Callable[[Dict[str, Any], Dict[str, Any]], None],
        get_children: Callable[[Dict[str, Any], str], List[Dict[str, Any]]],
        save_backup: Callable[[Dict[str, Any]], None],
        log=None,
    ):
        if not all(callable(callback) for callback in (get_item, update_item, get_children, save_backup)):
            raise TypeError("修复工具的读取、更新、子项读取和备份回调必须可调用")
        self._get_item = get_item
        self._update_item = update_item
        self._get_children = get_children
        self._save_backup = save_backup
        self._logger = log
        self._operation_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._cancelled = threading.Event()
        self._plan: Optional[_Plan] = None
        self._public = self._empty("尚未预览；请先明确选择需要解除整体锁的条目 ID。", phase="idle")

    @staticmethod
    def _empty(message: str, *, ok: bool = False, phase: str = "failed") -> Dict[str, Any]:
        return {
            "ok": ok, "message": message, "phase": phase, "token": "",
            "items": [], "count": 0, "root_count": 0, "child_count": 0,
            "requested_count": 0, "skipped_count": 0, "expires_at": "",
        }

    def _publish(self, result: Dict[str, Any]) -> Dict[str, Any]:
        with self._state_lock:
            self._public = copy.deepcopy(result)
        return copy.deepcopy(result)

    def view(self) -> Dict[str, Any]:
        """Return a detached copy of the last public preview/result."""
        with self._state_lock:
            return copy.deepcopy(self._public)

    def cancel(self) -> None:
        """Invalidate any token and prevent further writes after an active call."""
        self._cancelled.set()
        with self._state_lock:
            self._plan = None
            self._public = {
                **self._public, "ok": False, "phase": "cancelled", "token": "",
                "message": "修复任务已取消；不会继续解除其它条目的整体锁。",
            }

    def _check_cancel(self) -> None:
        if self._cancelled.is_set():
            raise _Cancelled()

    def _log(self, level: str, message: str) -> None:
        try:
            callback = getattr(self._logger, level, None)
            if callable(callback):
                callback(message)
            elif callable(self._logger):
                self._logger(message)
        except Exception:
            # Logging must never change lock/backup semantics.
            pass

    @staticmethod
    def _binding(cfg: Dict[str, Any]) -> str:
        values = [str(cfg.get(key) or "") for key in ("emby_server", "api_key", "user_id")]
        value = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _parse_ids(raw_ids: str) -> List[str]:
        if not isinstance(raw_ids, str):
            raise ValueError("请输入需要修复的条目 ID")
        if len(raw_ids) > 65536:
            raise ValueError("条目 ID 输入过长，请分批预览")
        result: List[str] = []
        seen = set()
        for value in re.split(r"[\s,，]+", raw_ids.strip()):
            if not value:
                continue
            value = _id(value)
            if value not in seen:
                result.append(value)
                seen.add(value)
                if len(result) > _MAX_ROOTS:
                    raise ValueError("每次最多指定 500 个不同的根条目 ID")
        if not result:
            raise ValueError("请先填写需要解除整体锁的条目 ID")
        return result

    def _read(self, cfg: Dict[str, Any], item_id: str) -> Tuple[Dict[str, Any], _Snapshot]:
        try:
            item = self._get_item(cfg, item_id)
        except Exception:
            # Exception strings can contain authentication query parameters.
            raise _ReadFailure() from None
        return item, _snapshot(item, item_id)

    @staticmethod
    def _observe(observed: Dict[str, _Snapshot], snapshot: _Snapshot) -> None:
        previous = observed.get(snapshot.item_id)
        if previous is not None and not previous.matches(snapshot):
            raise ValueError("预览过程中条目的锁或所属关系发生变化，请重新预览")
        observed[snapshot.item_id] = snapshot

    def _descendants(
        self, cfg: Dict[str, Any], root: _Snapshot, observed: Dict[str, _Snapshot]
    ) -> List[Tuple[_Snapshot, Tuple[_Snapshot, ...]]]:
        self._check_cancel()
        try:
            raw = self._get_children(cfg, root.item_id)
        except Exception:
            raise _ReadFailure() from None
        self._check_cancel()
        if not isinstance(raw, list):
            raise ValueError("子项读取未返回完整条目列表，已中止预览")
        nodes: Dict[str, Dict[str, Any]] = {}
        for item in raw:
            self._check_cancel()
            if not isinstance(item, dict):
                raise ValueError("子项列表中存在无效条目，已中止预览")
            item_id = _id(item.get("Id"))
            item_type = item.get("Type")
            if item_id == root.item_id:
                duplicate = _snapshot(item, root.item_id)
                self._observe(observed, duplicate)
                continue
            if item_type not in ("Season", "Episode"):
                continue
            # Parse relations before using them to build a reachable tree.
            _relation(item, "ParentId")
            _relation(item, "SeriesId")
            if item_id in nodes:
                first = _snapshot(nodes[item_id], item_id)
                duplicate = _snapshot(item, item_id)
                if not first.matches(duplicate):
                    raise ValueError("子项列表包含相互冲突的重复条目，已中止预览")
                continue
            nodes[item_id] = item

        if root.item_type == "Series":
            series_id = root.item_id
        else:
            if root.series_id and root.parent_id and root.series_id != root.parent_id:
                raise ValueError("所选季的剧集归属相互冲突，已中止子项预览")
            series_id = root.series_id or root.parent_id

        # ParentId is mandatory for inherited candidates.  A SeriesId alone
        # cannot prove that a loose/foreign result belongs below the root.
        paths: Dict[str, Tuple[_Snapshot, ...]] = {root.item_id: (root,)}
        result: List[Tuple[_Snapshot, Tuple[_Snapshot, ...]]] = []
        if root.item_type == "Series":
            for item_id, item in nodes.items():
                self._check_cancel()
                if item.get("Type") != "Season" or _relation(item, "ParentId") != root.item_id:
                    continue
                child_series = _relation(item, "SeriesId")
                if child_series and child_series != series_id:
                    continue
                season = _snapshot(item, item_id)
                self._observe(observed, season)
                paths[item_id] = (root, season)
                if season.locked and not season.fields:
                    result.append((season, (root,)))

        for item_id, item in nodes.items():
            self._check_cancel()
            if item.get("Type") != "Episode":
                continue
            ancestry = paths.get(_relation(item, "ParentId"))
            if ancestry is None:
                continue
            child_series = _relation(item, "SeriesId")
            if child_series and (not series_id or child_series != series_id):
                continue
            episode = _snapshot(item, item_id)
            self._observe(observed, episode)
            if episode.locked and not episode.fields:
                result.append((episode, ancestry))
        return result

    def preview(self, cfg: Dict[str, Any], raw_ids: str, include_children: bool = False) -> Dict[str, Any]:
        if not self._operation_lock.acquire(blocking=False):
            return self._empty("已有锁修复检查或执行正在运行，请稍后重试。", phase="busy")
        try:
            self._cancelled.clear()
            with self._state_lock:
                self._plan = None
            roots = self._parse_ids(raw_ids)
            if type(include_children) is not bool:
                raise ValueError("是否包含子项必须是明确的开关值")
            binding = self._binding(cfg)
            entries: Dict[str, _Entry] = {}
            observed: Dict[str, _Snapshot] = {}
            root_snapshots: List[_Snapshot] = []
            for item_id in roots:
                self._check_cancel()
                _, snapshot = self._read(cfg, item_id)
                self._observe(observed, snapshot)
                root_snapshots.append(snapshot)
                if snapshot.locked:
                    entries[item_id] = _Entry(snapshot=snapshot, explicit_root=True)
            root_count = len(entries)
            if include_children:
                for root in root_snapshots:
                    self._check_cancel()
                    if root.item_type not in ("Series", "Season"):
                        continue
                    for snapshot, ancestry in self._descendants(cfg, root, observed):
                        entry = entries.get(snapshot.item_id)
                        if entry is None:
                            if len(entries) >= _MAX_CANDIDATES:
                                raise ValueError("候选条目超过 200000 个，请分批预览")
                            entry = _Entry(snapshot=snapshot)
                            entries[snapshot.item_id] = entry
                        if not entry.explicit_root and ancestry not in entry.paths:
                            entry.paths.append(ancestry)
            self._check_cancel()
            now = time.time()
            count = len(entries)
            child_count = count - root_count
            result = {
                "ok": True, "phase": "preview", "token": "", "items": [],
                "count": count, "root_count": root_count, "child_count": child_count,
                "requested_count": len(roots), "skipped_count": len(roots) - root_count,
                "sample_count": min(count, _MAX_SAMPLES), "expires_at": "",
                "message": (
                    f"只读预览完成：明确指定的整体锁条目 {root_count} 个，"
                    f"符合条件的空字段锁子项 {child_count} 个。尚未修改 Emby。"
                    if count else "所选条目均未整体锁定，没有需要解除整体锁的条目；未修改 Emby。"
                ),
            }
            ordered = dict(sorted(entries.items(), key=lambda pair: _ORDER[pair[1].snapshot.item_type]))
            for entry in list(ordered.values())[:_MAX_SAMPLES]:
                snapshot = entry.snapshot
                result["items"].append({
                    "id": snapshot.item_id, "name": snapshot.name,
                    "type": snapshot.item_type, "fields": list(snapshot.fields),
                    "reason": "用户明确指定的整体锁条目" if entry.explicit_root else "所选剧集或季下字段锁为空的整体锁子项",
                })
            if count:
                plan = _Plan(
                    token=secrets.token_urlsafe(32), binding=binding,
                    preview_epoch=now, expires_epoch=now + _PLAN_SECONDS,
                    entries=ordered, root_count=root_count, child_count=child_count,
                    requested_count=len(roots),
                )
                result["token"] = plan.token
                result["expires_at"] = _stamp(plan.expires_epoch)
                result["expires_in_seconds"] = _PLAN_SECONDS
                with self._state_lock:
                    if self._cancelled.is_set():
                        raise _Cancelled()
                    self._plan = plan
                    self._public = copy.deepcopy(result)
                return copy.deepcopy(result)
            return self._publish(result)
        except _Cancelled:
            return self._publish(self._empty("锁修复预览已取消，未修改 Emby。", phase="cancelled"))
        except _ReadFailure:
            return self._publish(self._empty("Emby 条目或子项读取失败，预览已全部作废；未修改 Emby。"))
        except ValueError as exc:
            return self._publish(self._empty(str(exc) + "；未修改 Emby。"))
        except Exception:
            return self._publish(self._empty("锁修复预览未完成，预览已全部作废；未修改 Emby。"))
        finally:
            self._operation_lock.release()

    def _valid_ancestry(
        self, cfg: Dict[str, Any], entry: _Entry, plan: _Plan, outcomes: Dict[str, str]
    ) -> bool:
        if entry.explicit_root:
            return True
        for path in entry.paths:
            valid = True
            for original in path:
                self._check_cancel()
                if original.item_id in plan.entries:
                    if outcomes.get(original.item_id) != "updated":
                        valid = False
                        break
                    expected_lock = False
                else:
                    expected_lock = original.locked
                try:
                    _, current = self._read(cfg, original.item_id)
                except ValueError:
                    valid = False
                    break
                if not original.matches(current, expected_lock=expected_lock):
                    valid = False
                    break
            if valid:
                return True
        return False

    @staticmethod
    def _result(
        plan: _Plan, *, updated: int = 0, skipped: int = 0, failed: int = 0,
        backed_up: bool = False, cancelled: bool = False, message: str = "", phase: str = "complete",
    ) -> Dict[str, Any]:
        pending = len(plan.entries) - updated - skipped - failed
        return {
            "ok": failed == 0 and not cancelled and backed_up,
            "phase": "cancelled" if cancelled else phase,
            "message": message or (
                f"整体锁修复{'已取消' if cancelled else '完成'}："
                f"确认解除 {updated} 个，状态变化跳过 {skipped} 个，失败 {failed} 个，未处理 {pending} 个。"
                "原字段锁保持不变，未触发元数据刷新。"
            ),
            "token": "", "items": [], "count": len(plan.entries),
            "root_count": plan.root_count, "child_count": plan.child_count,
            "requested_count": plan.requested_count, "expires_at": "",
            "updated_count": updated, "skipped_count": skipped, "failed_count": failed,
            "updated": updated, "skipped": skipped, "failed": failed,
            "pending_count": pending, "backed_up": backed_up,
        }

    def apply(self, cfg: Dict[str, Any], token: str, confirmed: bool = False) -> Dict[str, Any]:
        if not self._operation_lock.acquire(blocking=False):
            return self._empty("已有锁修复检查或执行正在运行，请稍后重试。", phase="busy")
        try:
            if self._cancelled.is_set():
                return self._publish(self._empty("锁修复已取消，请重新预览。", phase="cancelled"))
            with self._state_lock:
                plan = self._plan
            if plan is None:
                return self._publish(self._empty("没有可执行的预览，或该预览已使用；请重新预览。"))
            if not isinstance(token, str):
                return self._publish(self._empty("预览凭证不匹配，请使用最新预览。"))
            try:
                matches = hmac.compare_digest(plan.token, token)
            except TypeError:
                matches = False
            if not matches:
                return self._publish(self._empty("预览凭证不匹配，请使用最新预览。"))
            if time.time() >= plan.expires_epoch or self._binding(cfg) != plan.binding:
                with self._state_lock:
                    self._plan = None
                return self._publish(self._empty("预览已过期或 Emby 连接配置已变化，请重新预览。"))
            if confirmed is not True:
                return self._publish(self._empty("请先确认这些条目需要解除整体锁，再执行修复。"))
            # Consume before any backup or write.  A failed/uncertain operation
            # must never be retried merely by submitting the same token.
            with self._state_lock:
                self._plan = None
            self._check_cancel()
            self._publish(self._result(plan, phase="applying", message="正在保存原锁状态备份，尚未修改 Emby。"))
            backup = {
                "preview_time": _stamp(plan.preview_epoch),
                "items": [entry.snapshot.backup() for entry in plan.entries.values()],
            }
            try:
                saved = self._save_backup(backup)
                if inspect.isawaitable(saved) or isinstance(saved, Future):
                    # A mistakenly asynchronous adapter has not persisted
                    # anything merely by returning its coroutine object.
                    if inspect.iscoroutine(saved):
                        saved.close()
                    raise RuntimeError("备份回调未同步完成")
                if saved is False:
                    raise RuntimeError("备份回调报告失败")
            except Exception:
                return self._publish(self._result(
                    plan, phase="failed", message="原锁状态备份未能持久化，已停止修复；未修改 Emby。",
                ))
            updated = skipped = failed = 0
            outcomes: Dict[str, str] = {}
            cancelled = False
            self._log("info", f"[emby_toolbox] 整体锁修复备份已保存，待处理 {len(plan.entries)} 个条目")
            for item_id, entry in plan.entries.items():
                try:
                    self._check_cancel()
                    try:
                        item, current = self._read(cfg, item_id)
                    except ValueError:
                        skipped += 1
                        outcomes[item_id] = "skipped"
                        continue
                    if not entry.snapshot.matches(current) or not current.locked:
                        skipped += 1
                        outcomes[item_id] = "skipped"
                        continue
                    if not self._valid_ancestry(cfg, entry, plan, outcomes):
                        skipped += 1
                        outcomes[item_id] = "skipped"
                        continue
                    change = copy.deepcopy(item)
                    change["LockData"] = False
                    change.pop("IsLocked", None)
                    self._check_cancel()
                    self._update_item(cfg, change)
                    # Finish verifying this one in-flight write even if stop
                    # was requested; no additional writes are started after it.
                    _, verify = self._read(cfg, item_id)
                    if not entry.snapshot.matches(verify, expected_lock=False):
                        raise ValueError("锁状态回读未确认")
                    updated += 1
                    outcomes[item_id] = "updated"
                except _Cancelled:
                    cancelled = True
                    break
                except Exception:
                    failed += 1
                    outcomes[item_id] = "failed"
                    self._log("warning", f"[emby_toolbox] 条目 {item_id} 的整体锁修复未确认，未重试")
                finally:
                    completed = updated + skipped + failed
                    if completed and completed % 50 == 0:
                        self._log("info", f"[emby_toolbox] 整体锁修复进度 {completed}/{len(plan.entries)}：解除 {updated}，跳过 {skipped}，失败 {failed}")
            cancelled = cancelled or self._cancelled.is_set()
            return self._publish(self._result(
                plan, updated=updated, skipped=skipped, failed=failed,
                backed_up=True, cancelled=cancelled,
            ))
        except _Cancelled:
            return self._publish(self._empty("锁修复已取消，未开始修改 Emby。", phase="cancelled"))
        except Exception:
            with self._state_lock:
                self._plan = None
            return self._publish(self._empty("锁修复未完成，凭证已作废；请重新预览并核对 Emby 状态。"))
        finally:
            self._operation_lock.release()
