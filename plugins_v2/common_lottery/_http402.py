"""色花堂关键词抽奖解析；只读取指定字段，不跟随领奖或推广链接。"""
from __future__ import annotations

import re
from urllib.parse import urlsplit


BOT_NAMES = frozenset({"http_code_402_bot", "sehuatang"})
CHANNEL_NAMES = frozenset({"sehuatang", "sehuatang1"})
TARGET_GROUP = "sehuatang2"
_COPY_NOTE = re.compile(r"\s*[（(](?:单击|点击)复制文本[)）]\s*$")


def raw_text(message):
    value = getattr(message, "raw_text", None) or getattr(message, "text", None) or ""
    return value if isinstance(value, str) else ""


def _usernames(sender):
    names = {str(getattr(sender, "username", "") or "").lower().lstrip("@")}
    names.update(str(getattr(alias, "username", "") or "").lower().lstrip("@")
                 for alias in (getattr(sender, "usernames", None) or [])
                 if getattr(alias, "active", False))
    return names - {""}


def trusted_sender(sender, message):
    """信任真实 Bot/官方频道实体，不接受普通用户复制或转发的公告。"""
    if sender is None or getattr(message, "out", False) or getattr(message, "fwd_from", None):
        return False
    names = _usernames(sender)
    return bool((getattr(sender, "bot", False) and names & BOT_NAMES)
                or (getattr(sender, "broadcast", False) and names & CHANNEL_NAMES))


def _entity_span(text, entity):
    offset, length = getattr(entity, "offset", None), getattr(entity, "length", None)
    if type(offset) is not int or type(length) is not int or offset < 0 or length <= 0:
        return None
    encoded = text.encode("utf-16-le")
    if (offset + length) * 2 > len(encoded):
        return None
    try:
        start = len(encoded[:offset * 2].decode("utf-16-le"))
        value = encoded[offset * 2:(offset + length) * 2].decode("utf-16-le")
        return start, start + len(value), value
    except UnicodeError:
        return None


def _field(text, name, *, required=False):
    matches = list(re.finditer(r"^[ \t]*" + re.escape(name) + r"\s*[:：][ \t]*([^\r\n]*)", text, re.M))
    if len(matches) > 1 or (required and len(matches) != 1):
        raise ValueError("字段缺失或重复")
    return matches[0] if matches else None


def _public_group(url):
    value = str(url).strip()
    if value.startswith("@"):
        value = "https://t.me/" + value[1:]
    elif value.lower().startswith("t.me/"):
        value = "https://" + value
    try:
        parsed = urlsplit(value)
        if (parsed.scheme.lower() not in {"http", "https"} or parsed.hostname != "t.me"
                or parsed.username is not None or parsed.password is not None
                or parsed.port is not None or parsed.query or parsed.fragment):
            raise ValueError
        name = parsed.path.strip("/")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{3,31}", name):
            raise ValueError
        return name.lower()
    except (TypeError, ValueError):
        raise ValueError("参与群链接无效") from None


def _line_targets(message, text, field):
    if field is None:
        return set()
    targets = set()
    for entity in (getattr(message, "entities", None) or []):
        span = _entity_span(text, entity)
        if span is None or not (field.start(1) <= span[0] < span[1] <= field.end(1)):
            continue
        if type(entity).__name__ == "MessageEntityTextUrl":
            targets.add(_public_group(getattr(entity, "url", "")))
        elif type(entity).__name__ == "MessageEntityUrl":
            targets.add(_public_group(span[2]))
    for value in re.findall(r"(?:https?://)?t\.me/[^\s<>）)]+|@[A-Za-z][A-Za-z0-9_]{3,31}", field.group(1)):
        targets.add(_public_group(value))
    return targets


def _keyword(message, text, field):
    plain = _COPY_NOTE.sub("", field.group(1)).strip()
    if not plain or len(plain.encode("utf-16-le")) // 2 > 1024:
        raise ValueError("关键词无效")
    codes = []
    for entity in (getattr(message, "entities", None) or []):
        if type(entity).__name__ not in {"MessageEntityCode", "MessageEntityPre"}:
            continue
        span = _entity_span(text, entity)
        if span and field.start(1) <= span[0] < span[1] <= field.end(1):
            codes.append(span[2])
    if codes:
        if len(codes) != 1 or codes[0] != plain:
            raise ValueError("关键词与复制内容不一致")
        return codes[0]
    return plain


def parse_lottery(message):
    """非活动、已结束、参与目标不明确或字段冲突时不返回可发送口令。"""
    text = raw_text(message)
    if not text or len(text) > 16_384:
        return None
    header = text.lstrip().splitlines()[0].strip()
    if not re.match(r"^(?:🎁\s*)?抽奖活动(?:\s*🎁)?(?:\s|[（(]|$)", header):
        return None
    try:
        activity = _field(text, "活动", required=True).group(1).strip()
        method = _field(text, "开奖方式", required=True).group(1).strip()
        count = _field(text, "开奖人数", required=True).group(1).strip()
        participation = _field(text, "参与方式", required=True)
        keyword = _field(text, "关键词", required=True)
        group = _field(text, "群组")
        status, winners = _field(text, "状态"), _field(text, "中奖用户")
        if (not activity or method != "按人数自动开奖" or not re.fullmatch(r"[1-9]\d{0,8}", count)
                or not re.search(r"群内发送关键词参与抽奖", participation.group(1))):
            return None
        if status and status.group(1).strip() not in {"", "进行中", "未开奖", "待开奖", "报名中", "参与中", "抽奖中"}:
            return None
        if winners and winners.group(1).strip():
            return None
        targets = _line_targets(message, text, group) | _line_targets(message, text, participation)
        if targets != {TARGET_GROUP}:
            return None
        # 日期/月份是活动身份的一部分；同一公告的群/频道副本共享身份。
        edition = re.sub(r"[🎁\s]+", " ", header).strip()
        return {
            "keyword": _keyword(message, text, keyword), "target": int(count),
            "prize": activity, "activity": activity, "edition": edition,
            "target_group": TARGET_GROUP, "draw_time": None,
        }
    except (TypeError, ValueError, UnicodeError):
        return None
