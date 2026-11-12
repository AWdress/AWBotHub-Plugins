"""Parse detached SSD success receipts without trusting display names.

Only Telegram entities covering the *whole* payer/payee names are accepted.
Username links remain unresolved here; callers must resolve them to Telegram
users before attributing a payment.  Bot/chat authentication is also a caller
responsibility.  This module never performs network or storage operations.
"""

from decimal import Decimal, InvalidOperation
import re
from urllib.parse import parse_qs, urlsplit


_IDENTITY_ENTITIES = {
    "MessageEntityMentionName", "InputMessageEntityMentionName",
    "MessageEntityTextUrl", "MessageEntityMention",
}
_USERNAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}\Z", re.ASCII)
_RESERVED_LINKS = {
    "a", "addemoji", "addlist", "addstickers", "addtheme", "bg", "boost",
    "c", "confirmphone", "contact", "giftcode", "invoice", "iv", "joinchat",
    "login", "m", "nft", "proxy", "s", "setlanguage", "share", "socks",
}
_HEADER_RE = re.compile(r"\A[ \t\r\n]*💸\ufe0f?[ \t]*转账完成")
_BETWEEN_RE = re.compile(r"[ \t]+向[ \t]+\Z")
_NUMBER_PATTERN = r"(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?"
_AMOUNT_RE = re.compile(
    r"\A[ \t]+转账[ \t]+(?P<amount>" + _NUMBER_PATTERN + r")[ \t]+茉莉[。.]"
)
_TAIL_RE = re.compile(
    r"\A(?:[ \t\r\n]*含税[ \t]*" + _NUMBER_PATTERN + r"[ \t]*茉莉[。.])?"
    r"(?:[ \t\r\n]*接下来(?:五|5)分钟内?的?转账将不再提醒确认[。.])?"
    r"[ \t\r\n]*\Z"
)


def _raw_text(message):
    for field in ("raw_text", "message", "text", "caption"):
        value = getattr(message, field, None)
        if isinstance(value, str):
            return value
    return ""


def _positive_id(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 0 < value < 2**63 else None
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value, re.ASCII):
        # Telegram identifiers are int64; rejecting oversized strings also
        # avoids arbitrary-size integer conversion of untrusted URL values.
        if len(value) <= 19:
            number = int(value)
            return number if 0 < number < 2**63 else None
    return None


def _username(value):
    if not isinstance(value, str) or not _USERNAME_RE.fullmatch(value):
        return None
    return value.lower() if value.lower() not in _RESERVED_LINKS else None


def _url_identity(value):
    if not isinstance(value, str) or any(ord(ch) < 33 for ch in value):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.fragment or parsed.username or parsed.password or parsed.port:
            return None
        scheme, host = parsed.scheme.lower(), parsed.netloc.lower()
        if scheme == "tg" and not parsed.path:
            query = parse_qs(parsed.query, keep_blank_values=True)
            if any(len(values) != 1 for values in query.values()):
                return None
            if host == "user" and set(query) == {"id"}:
                user_id = _positive_id(query["id"][0])
            elif host == "openmessage" and set(query) in (
                    {"user_id"}, {"user_id", "message_id"}):
                if "message_id" in query and not _positive_id(query["message_id"][0]):
                    return None
                user_id = _positive_id(query["user_id"][0])
            else:
                return None
            return {"id": user_id, "username": None} if user_id else None
        if scheme in ("http", "https") and host in ("t.me", "telegram.me"):
            if parsed.query:
                return None
            path = parsed.path
            if path.endswith("/"):
                path = path[:-1]
            if not path.startswith("/"):
                return None
            username = _username(path[1:])
            return {"id": None, "username": username} if username else None
    except (TypeError, ValueError):
        return None
    return None


def _entity_identity(entity, name):
    kind = type(entity).__name__
    if kind in ("MessageEntityMentionName", "InputMessageEntityMentionName"):
        value = getattr(entity, "user_id", None)
        user_id = _positive_id(value)
        if user_id is None and value is not None:
            # Telethon InputMessageEntityMentionName carries InputUser rather
            # than a bare numeric ID.  InputUserSelf cannot establish an ID.
            user_id = _positive_id(getattr(value, "user_id", None))
        identity = {"id": user_id, "username": None} if user_id else None
    elif kind == "MessageEntityTextUrl":
        identity = _url_identity(getattr(entity, "url", None))
    elif kind == "MessageEntityMention" and name.startswith("@"):
        username = _username(name[1:])
        identity = {"id": None, "username": username} if username else None
    else:
        identity = None
    if identity is not None:
        identity["name"] = name
    return identity


def parse_ssd_receipt(message):
    """Return exact payer/payee identities for an explicit SSD completion.

    Return ``None`` for missing, partial, overlapping or untrusted identity
    entities.  Offsets are Telegram UTF-16 code units, not Python characters.
    Names may contain emoji or words such as ``向``; entity boundaries rather
    than a display-name regular expression delimit the two identities.
    """
    text = _raw_text(message)
    header = _HEADER_RE.match(text)
    if not header:
        return None

    boundaries = {0: 0}
    units = 0
    for index, char in enumerate(text):
        units += 2 if ord(char) > 0xFFFF else 1
        boundaries[units] = index + 1

    spans = []
    for entity in getattr(message, "entities", None) or ():
        if type(entity).__name__ not in _IDENTITY_ENTITIES:
            continue
        offset, length = getattr(entity, "offset", None), getattr(entity, "length", None)
        if (not isinstance(offset, int) or isinstance(offset, bool)
                or not isinstance(length, int) or isinstance(length, bool)
                or offset < 0 or length <= 0
                or offset not in boundaries or offset + length not in boundaries):
            return None
        start, end = boundaries[offset], boundaries[offset + length]
        name = text[start:end]
        if not name.strip() or "\n" in name or "\r" in name:
            return None
        spans.append((start, end, entity, name))

    def unambiguous(candidate):
        start, end, _entity, _name = candidate
        return sum(other_start < end and start < other_end
                   for other_start, other_end, _e, _n in spans) == 1

    results = []
    for sender_span in spans:
        start, end, entity, name = sender_span
        separator = text[header.end():start]
        if start <= header.end() or not separator or separator.strip():
            continue
        if not unambiguous(sender_span):
            continue
        sender = _entity_identity(entity, name)
        if sender is None:
            continue
        for recipient_span in spans:
            recipient_start, recipient_end, recipient_entity, recipient_name = recipient_span
            if (recipient_start <= end or not _BETWEEN_RE.fullmatch(text[end:recipient_start])
                    or not unambiguous(recipient_span)):
                continue
            recipient = _entity_identity(recipient_entity, recipient_name)
            if recipient is None:
                continue
            amount_match = _AMOUNT_RE.match(text[recipient_end:])
            if amount_match is None:
                continue
            suffix = text[recipient_end + amount_match.end():]
            if not _TAIL_RE.fullmatch(suffix):
                continue
            try:
                amount = Decimal(amount_match["amount"].replace(",", ""))
                if not amount.is_finite() or amount <= 0:
                    continue
                normalized = format(amount, "f")
                if "." in normalized:
                    normalized = normalized.rstrip("0").rstrip(".")
            except (InvalidOperation, ValueError):
                continue
            results.append({"amount": normalized, "sender": sender, "recipient": recipient})
    return results[0] if len(results) == 1 else None
