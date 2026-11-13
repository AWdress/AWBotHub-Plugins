"""SSD 官方抽奖参与与本人转账确认，不发起转账、不记账。"""
from __future__ import annotations

import asyncio
import math
import random
import re
import time

from ._parsers import (
    BOT_ID, GROUPS, parse_lottery, transfer_request, confirmation_pending,
    confirmation_amount, confirmation_button, raw_text,
)
from ._state import ActionJournal


DEFAULTS = {
    "lottery_enabled": False,
    "lottery_delay_min_seconds": 2,
    "lottery_delay_max_seconds": 5,
    "ssd_click_mode": "off",
    "confirm_delay_seconds": 0.5,
}


def _enabled(value):
    return (value is True or type(value) is int and value == 1
            or isinstance(value, str) and value.lower().strip() == "true")


def _delay(value, default, maximum):
    try:
        result = float(value)
        return min(maximum, max(0, result)) if math.isfinite(result) else default
    except (ValueError, TypeError, OverflowError):
        return default


def _id(value):
    return value if type(value) is int and value > 0 else None


def lottery_delay(config):
    if ("lottery_delay_min_seconds" not in config and "lottery_delay_max_seconds" not in config
            and "lottery_delay_seconds" in config):
        # 保留早期已保存的固定等待；新配置统一使用随机范围。
        return _delay(config["lottery_delay_seconds"], 2, 60)
    lower = _delay(config.get("lottery_delay_min_seconds", 2), 2, 60)
    upper = _delay(config.get("lottery_delay_max_seconds", 5), 5, 60)
    if lower > upper:
        raise ValueError("抽奖最短等待不能大于最长等待")
    return random.uniform(lower, upper)


def _fresh(message, maximum_age):
    date = getattr(message, "date", None)
    if date is None:
        return True
    try:
        age = time.time() - date.timestamp()
        return math.isfinite(age) and -60 <= age <= maximum_age
    except (AttributeError, TypeError, ValueError, OverflowError, OSError):
        return False


class SSDAssistant:
    def __init__(self, ctx):
        self.ctx = ctx
        self.journal = ActionJournal(ctx.storage)
        self.closed = False
        self.accounts = {}
        self.current = {}  # 编辑到达后替换快照；延迟结束时不使用过期口令/按钮。

    def stop(self):
        self.closed = True
        self.current.clear()

    def mode(self):
        value = self.ctx.config.get("ssd_click_mode", "off")
        return value if value in ("off", "once", "5min") else "off"

    async def own_id(self, client):
        key = id(client)
        if key not in self.accounts or self.accounts[key][0] is not client:
            user = await asyncio.wait_for(client.get_me(), timeout=10)
            uid = _id(getattr(user, "id", None))
            if not uid:
                raise ValueError("无法核实当前 Telegram 账号")
            self.accounts[key] = (client, uid)
        return self.accounts[key][1]

    @staticmethod
    def trusted(message, chat_id):
        message_chat = getattr(message, "chat_id", chat_id)
        return (chat_id in GROUPS and message_chat == chat_id
                and getattr(message, "sender_id", None) == BOT_ID
                and not getattr(message, "out", False)
                and not getattr(message, "fwd_from", None))

    async def handle(self, event):
        if self.closed:
            return
        message, client, chat_id = event.message, event.client, event.chat_id
        if not self.trusted(message, chat_id) or not _id(getattr(message, "id", None)):
            return
        account_id = await self.own_id(client)
        self.current[(account_id, chat_id, message.id)] = message
        # 仅保留近期消息快照，不创建轮询任务。
        while len(self.current) > 256:
            self.current.pop(next(iter(self.current)))
        try:
            if _enabled(self.ctx.config.get("lottery_enabled", False)):
                lottery = parse_lottery(message)
                if lottery is not None:
                    await self.join(client, message, chat_id, account_id, lottery)
                    return
            if self.mode() != "off" and confirmation_pending(message):
                await self.confirm(client, message, chat_id, account_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.ctx.log.exception("SSD 助手处理失败（群 %s，消息 %s），未自动补发或重试", chat_id, message.id)

    async def _finish(self, key, status, detail, **values):
        try:
            await self.journal.finish(key, status, detail, **values)
        except Exception:
            self.ctx.log.exception("SSD 助手保存操作结果失败，保留防重占位，请核对群内结果")

    async def _latest(self, client, message, chat_id):
        """排队中的编辑回调可能尚未运行，操作前从 Telegram 重读当前消息。"""
        try:
            latest = await asyncio.wait_for(client.get_messages(chat_id, ids=message.id), timeout=10)
            if (latest is not None and getattr(latest, "id", None) == message.id
                    and self.trusted(latest, chat_id)):
                return latest
        except Exception as exc:
            self.ctx.log.warning("SSD 操作前无法复核最新消息（%s），本次跳过", type(exc).__name__)
        return None

    async def join(self, client, message, chat_id, account_id, lottery):
        delay = lottery_delay(self.ctx.config)
        key = f"lottery:{account_id}:{chat_id}:{lottery.lottery_id}"
        if not await self.journal.reserve(
            key, kind="lottery", chat_id=chat_id, message_id=message.id,
            lottery_id=lottery.lottery_id, detail="已登记，等待发送抽奖口令",
        ):
            return
        try:
            await asyncio.sleep(delay)
            snapshot = self.current.get((account_id, chat_id, message.id))
            if self.closed or snapshot is None:
                await self._finish(key, "skipped", "插件已停用或消息快照失效，本次未发送")
                return
            latest = await self._latest(client, message, chat_id)
            current = parse_lottery(latest)
            if (self.closed or not _enabled(self.ctx.config.get("lottery_enabled", False))
                    or not self.trusted(latest, chat_id) or current != lottery):
                await self._finish(key, "skipped", "抽奖状态或口令已变化，或功能已关闭，本次未发送")
                return
            if not _fresh(latest, 72 * 3600):
                await self._finish(key, "skipped", "抽奖消息发布超过 72 小时，本次未发送")
                return
            observed = self.current.get((account_id, chat_id, message.id))
            if (self.closed or not _enabled(self.ctx.config.get("lottery_enabled", False))
                    or not self.trusted(observed, chat_id) or parse_lottery(observed) != lottery):
                await self._finish(key, "skipped", "复核期间抽奖状态或设置已变化，本次未发送")
                return
            # 独立发送原始口令；不加零宽字符，不附加格式，不发起任何 +转账请求。
            sent = await asyncio.wait_for(client.send_message(chat_id, lottery.code, parse_mode=None), timeout=20)
            await self._finish(key, "sent", "参与口令已发送；是否参与成功以 SSD 官方机器人为准",
                               sent_message_id=getattr(sent, "id", None))
            self.ctx.log.info("SSD 抽奖 %s：参与口令已发送（群 %s）", lottery.lottery_id, chat_id)
        except asyncio.CancelledError:
            # 发送可能已经到达 Telegram，持久占位保持不重试。
            raise
        except Exception as exc:
            await self._finish(key, "uncertain", "口令发送异常，结果未确认；请到群内核对，不自动补发")
            self.ctx.log.warning("SSD 抽奖 %s 发送异常（%s），未补发", lottery.lottery_id, type(exc).__name__)

    async def _request(self, client, message, chat_id, account_id):
        if getattr(getattr(message, "reply_to", None), "reply_to_peer_id", None) is not None:
            return None
        reply_id = _id(getattr(message, "reply_to_msg_id", None))
        if reply_id is None:
            return None
        command = await asyncio.wait_for(message.get_reply_message(), timeout=10)
        if (command is None or getattr(command, "id", None) != reply_id
                or getattr(command, "sender_id", None) != account_id
                or getattr(command, "chat_id", None) != chat_id
                or getattr(command, "fwd_from", None)
                or not _fresh(command, 30 * 60) or not _fresh(message, 30 * 60)):
            return None
        bounds = transfer_request(command)
        if bounds is None:
            return None
        if getattr(getattr(command, "reply_to", None), "reply_to_peer_id", None) is not None:
            return None
        target_id = _id(getattr(command, "reply_to_msg_id", None))
        if target_id is None or target_id >= command.id or command.id >= message.id:
            return None
        target = await asyncio.wait_for(command.get_reply_message(), timeout=10)
        recipient = _id(getattr(target, "sender_id", None))
        if (target is None or getattr(target, "id", None) != target_id
                or getattr(target, "chat_id", None) != chat_id
                or recipient is None or recipient == account_id):
            return None
        amount = confirmation_amount(message)
        if amount is None and re.search(r"^\s*转出金额", raw_text(message), re.M):
            return None  # 明确字段畸形/重复时不能按固定金额兜底。
        # 随机金额必须有官方实际额；固定金额兼容旧版只展示确认按钮的提示。
        if amount is None and bounds[0] != bounds[1]:
            return None
        if amount is not None and not bounds[0] <= amount <= bounds[1]:
            return None
        return command.id, str(amount if amount is not None else bounds[0]), recipient

    async def confirm(self, client, message, chat_id, account_id):
        mode = self.mode()
        position = confirmation_button(message, mode)
        if position is None:
            return
        request = await self._request(client, message, chat_id, account_id)
        if request is None:
            self.ctx.log.warning("SSD 转账确认未通过本人请求/目标/金额核对，未点击（消息 %s）", message.id)
            return
        command_id, amount, recipient = request
        key = f"transfer:{account_id}:{chat_id}:{command_id}"
        if not await self.journal.reserve(
            key, kind="transfer", chat_id=chat_id, message_id=message.id,
            command_id=command_id, recipient_id=recipient, amount=amount,
            detail="已核实本人转账请求，等待点击确认",
        ):
            return
        try:
            await asyncio.sleep(_delay(self.ctx.config.get("confirm_delay_seconds", 0.5), 0.5, 10))
            snapshot = self.current.get((account_id, chat_id, message.id))
            if self.closed or snapshot is None:
                await self._finish(key, "skipped", "插件已停用或消息快照失效，本次未点击")
                return
            latest = await self._latest(client, message, chat_id)
            if (self.closed or latest is None or self.mode() != mode or not self.trusted(latest, chat_id)
                    or not confirmation_pending(latest)
                    or confirmation_button(latest, mode) != position
                    or await self._request(client, latest, chat_id, account_id) != request):
                await self._finish(key, "skipped", "确认状态、金额或设置已变化，本次未点击")
                return
            if (self.closed or self.mode() != mode
                    or self.current.get((account_id, chat_id, message.id)) is not snapshot):
                await self._finish(key, "skipped", "确认核对期间状态或设置已变化，本次未点击")
                return
            row, col = position
            await asyncio.wait_for(latest.click(i=row, j=col), timeout=10)
            await self._finish(key, "clicked", "已点击官方确认按钮；是否转账成功以机器人最终回执为准")
            self.ctx.log.info("SSD 已点击转账确认（原请求 %s，金额 %s 茉莉），等待官方回执", command_id, amount)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self._finish(key, "uncertain", "转账确认异常，结果未确认；请核对官方回执，不自动重复点击")
            self.ctx.log.warning("SSD 转账确认异常（%s），原请求 %s 未重复点击", type(exc).__name__, command_id)


async def setup(ctx):
    assistant = SSDAssistant(ctx)
    await assistant.journal.initialize()
    ctx.add_cleanup(assistant.stop)

    @ctx.on_edited_message(chats=list(GROUPS))
    @ctx.on_message(incoming=True, chats=list(GROUPS))
    async def on_ssd_message(event):
        await assistant.handle(event)

    @ctx.on_api("/history", methods=["GET"])
    async def history(_request):
        return {"items": assistant.journal.history()}

    @ctx.on_api("/status", methods=["GET"])
    async def status(_request):
        return {"lottery_enabled": _enabled(ctx.config.get("lottery_enabled", False)),
                "ssd_click_mode": assistant.mode(), "bot_id": BOT_ID, "groups": list(GROUPS),
                "history_count": len(assistant.journal.items)}

    ctx.log.info("SSD 助手已加载；抽奖与转账确认独立开关，不创建定时轮询任务")


async def teardown(ctx):
    ctx.log.info("SSD 助手已停用")
