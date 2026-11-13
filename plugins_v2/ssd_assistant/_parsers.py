"""SSD 消息的只读解析；调用方必须先核实官方发送者和群组。"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re


BOT_ID = 752250569
GROUPS = (-1002014253433, -1001173590111)
_NUMBER = r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?"
_IDENTITIES = {"MessageEntityMentionName", "InputMessageEntityMentionName",
               "MessageEntityTextUrl", "MessageEntityMention"}


def raw_text(message) -> str:
    for name in ("raw_text", "message", "text", "caption"):
        value = getattr(message, name, None)
        if isinstance(value, str) and value:
            return value
    return ""


@dataclass(frozen=True)
class Lottery:
    lottery_id: str
    code: str


def parse_lottery(message) -> Lottery | None:
    text = raw_text(message)
    if not text or len(text) > 16000:
        return None
    if not re.search(r"^\s*🎁\ufe0f?\s*[^\r\n]+的抽奖\s*$", text, re.M):
        return None
    if any(marker in text for marker in (
        "已开奖", "开奖完成", "中奖名单", "抽奖结束", "已取消", "活动结束",
    )):
        return None
    if not all(re.search(r"^\s*" + title + r"\s*$", text, re.M)
               for title in ("奖品", "开奖", "参与")):
        return None
    ids = re.findall(r"^\s*ID\s*[:：]\s*([A-Fa-f0-9]{8})\s*$", text, re.M)
    codes = re.findall(
        r'^\s*发送口令\s*(?:「([^\r\n]{1,128})」|“([^\r\n]{1,128})”|"([^\r\n]{1,128})")\s*参与[。.]?\s*$',
        text, re.M,
    )
    if len(ids) != 1 or len(codes) != 1:
        return None
    if not re.search(r"^\s*已参与\s*[0-9]+\s*人\s*$", text, re.M):
        return None
    code = next((part for part in codes[0] if part), "")
    # 不改写口令来规避命令：带斜杠或控制字符的口令保守跳过。
    candidate = code.lstrip(" \t\u200b\u200c\u200d\u2060\ufeff")
    if (not code.strip() or candidate.startswith(("/", "／"))
            or re.fullmatch(r"\+\s*[0-9]+(?:\.[0-9]+)?(?:\s*-\s*[0-9]+(?:\.[0-9]+)?)?", candidate.strip())
            or any(ord(char) < 32 or ord(char) == 127 for char in code)):
        return None
    return Lottery(ids[0].upper(), code)


def transfer_request(message) -> tuple[Decimal, Decimal] | None:
    text = raw_text(message).strip()
    if len(text) > 180:
        return None
    match = re.fullmatch(r"\+\s*([0-9]+(?:\.[0-9]+)?)(?:\s*-\s*([0-9]+(?:\.[0-9]+)?))?", text)
    if match is None:
        return None
    try:
        lower = Decimal(match[1])
        upper = Decimal(match[2] or match[1])
        return (lower, upper) if lower.is_finite() and upper.is_finite() and 0 < lower <= upper else None
    except InvalidOperation:
        return None


def keyboard(message) -> list[list]:
    markup = getattr(message, "reply_markup", None)
    if markup is None:
        return []
    rows = getattr(markup, "inline_keyboard", None)
    if rows is None:
        rows = [getattr(row, "buttons", ()) for row in getattr(markup, "rows", ()) or ()]
    return [list(row or ()) for row in rows or ()]


def confirmation_button(message, mode: str) -> tuple[int, int] | None:
    if mode not in ("once", "5min"):
        return None
    found = []
    for row_index, row in enumerate(keyboard(message)):
        for col_index, button in enumerate(row):
            label = re.sub(r"\s+", "", str(getattr(button, "text", "") or "")).lower()
            data = getattr(button, "data", None)
            if (not isinstance(data, bytes) or not 1 <= len(data) <= 64
                    or getattr(button, "url", None)
                    or any(word in label for word in (
                        "取消", "返回", "拒绝", "不确认", "不确定", "暂不", "放弃", "cancel",
                    ))):
                continue
            five = any(word in label for word in ("5分钟", "五分钟", "5min"))
            confirm = any(word in label for word in ("确认", "确定", "confirm"))
            once = label in ("确认", "确定", "确认转账", "确定转账") or any(
                word in label for word in ("仅此", "本次", "一次", "单次")
            )
            if confirm and ((mode == "5min" and five) or (mode == "once" and once and not five)):
                found.append((row_index, col_index))
    return found[0] if len(found) == 1 else None


def confirmation_pending(message) -> bool:
    text = raw_text(message)
    if text.lstrip().startswith("💸") or any(word in text for word in (
        "失败", "错误", "余额不足", "已取消", "取消成功", "转账成功", "转赠成功",
        "转账完成", "转赠完成", "已成功",
    )):
        return False
    return any(word in text for word in (
        "请确认转账", "请确认你的转账", "确认你的转账", "转账金额过大", "转账金额较大",
    )) or any(confirmation_button(message, mode) is not None for mode in ("once", "5min"))


def confirmation_amount(message) -> Decimal | None:
    """只取唯一的“转出金额”字段，不误用税费、到账额或昵称数字。"""
    text = raw_text(message)
    fields = [line for line in re.finditer(r"[^\r\n]+", text)
              if re.match(r"[ \t]*转出金额(?=[:：\s]|$)", line.group())]
    if len(fields) != 1:
        return None
    field = fields[0]
    match = re.fullmatch(r"[ \t]*转出金额[ \t]*[:：][ \t]*(" + _NUMBER
                         + r")[ \t]+茉莉[。.]?[ \t]*", field.group())
    if match is None:
        return None
    start = len(text[:field.start()].encode("utf-16-le")) // 2
    end = start + len(field.group().encode("utf-16-le")) // 2
    for entity in getattr(message, "entities", None) or ():
        if type(entity).__name__ not in _IDENTITIES:
            continue
        offset, length = getattr(entity, "offset", None), getattr(entity, "length", None)
        if (type(offset) is not int or type(length) is not int or offset < 0 or length <= 0
                or offset < end and start < offset + length):
            return None
    try:
        amount = Decimal(match[1].replace(",", ""))
        return amount if amount.is_finite() and amount > 0 else None
    except InvalidOperation:
        return None
