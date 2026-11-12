"""Safe Markdown replies and account-local Rich Message delivery.

No model output is trusted as HTML.  The small Markdown renderer deliberately
uses only the standard library and emits a bounded set of Telegram tags.
"""
from __future__ import annotations

import html
import inspect
import re
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit


DEFAULT_REPLY_TEMPLATE = "{answer}"
DEFAULT_EXPLAIN_REPLY_TEMPLATE = "**问题**\n> {question}\n\n**回答**\n{answer}"
# Count the serialized HTML, not just visible characters.  This leaves margin
# below Telegram's 4096 UTF-16-unit text limit even after entity expansion.
MAX_MESSAGE_UNITS = 3500
_PLACEHOLDER = re.compile(r"\{(answer|question|sources)\}")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})([^\n]*)$")
_QUOTE = re.compile(r"^ {0,3}> ?(.*)$")
_HEADING = re.compile(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$")
_LIST = re.compile(r"^\s{0,3}(?:([-+*])|(\d{1,9})[.)])\s+(.+)$")
_FORMAT_ERROR_NAMES = {
    "EntityBoundsInvalidError", "EntitiesTooLongError", "EntityMentionUserInvalidError",
    "EntityTypeInvalidError", "MessageEntityInvalidError", "MessageParseError",
}


@dataclass(frozen=True)
class _Block:
    html: str
    standard: str
    plain: str
    # A native table can be divided by rows without turning it into code/text.
    table_header: str = ""
    table_rows: tuple[str, ...] = ()


@dataclass(frozen=True)
class RenderedReply:
    html: str
    plain: str
    _blocks: tuple[_Block, ...] = field(repr=False, compare=False)


def _text(value: Any) -> str:
    """Keep Unicode content, replacing only invalid standalone surrogates."""
    text = str(value if value is not None else "")
    return text.encode("utf-8", "surrogatepass").decode("utf-8", "replace") if any(
        0xD800 <= ord(char) <= 0xDFFF for char in text
    ) else text


def _units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _safe_url(raw: str) -> bool:
    if any(ord(char) < 32 or char.isspace() for char in raw):
        return False
    try:
        parsed = urlsplit(raw)
        return parsed.scheme.lower() in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False


def _delimiter_end(text: str, start: int, marker: str) -> int:
    """Locate a closing marker, ignoring escaped and inline-code content."""
    index = start
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == "`" and not marker.startswith("`"):
            run = len(text[index:]) - len(text[index:].lstrip("`"))
            end = text.find("`" * run, index + run)
            if end >= 0:
                index = end + run
                continue
        if text.startswith(marker, index):
            return index
        index += 1
    return -1


def _link(text: str, start: int):
    """Parse balanced [label](URL), including parentheses in URLs."""
    index, depth = start + 1, 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == "[":
            depth += 1
        elif text[index] == "]":
            depth -= 1
            if not depth:
                break
        index += 1
    if depth or text[index:index + 2] != "](" or index - start > 10000:
        return None
    label_end, cursor, depth = index, index + 2, 1
    while cursor < len(text):
        if text[cursor] == "\\":
            cursor += 2
            continue
        if text[cursor] == "(":
            depth += 1
        elif text[cursor] == ")":
            depth -= 1
            if not depth:
                break
        cursor += 1
    if depth:
        return None
    raw = text[index + 2:cursor].strip()
    # Markdown's optional link title is presentation-only, not the URL.
    match = re.fullmatch(r'(.+?)\s+(?:"[^"\n]*"|\'[^\'\n]*\')', raw)
    if match:
        raw = match.group(1).strip()
    if raw.startswith("<") and raw.endswith(">"):
        raw = raw[1:-1]
    raw = re.sub(r"\\([()\\])", r"\1", raw)
    return text[start + 1:label_end], raw, cursor + 1


def _inline(text: str, depth: int = 0) -> tuple[str, str]:
    """Return safe HTML and readable text; raw HTML is always escaped."""
    if depth > 12:
        return html.escape(text), text
    out, plain, index = [], [], 0
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text) and text[index + 1] in r"\`*_{}[]()#+-.!>|~":
            index += 1
            out.append(html.escape(text[index]))
            plain.append(text[index])
            index += 1
            continue
        if char == "`":
            length = len(text[index:]) - len(text[index:].lstrip("`"))
            marker = "`" * length
            end = text.find(marker, index + length)
            if end >= 0:
                value = text[index + length:end]
                out.append("<code>" + html.escape(value) + "</code>")
                plain.append(value)
                index = end + length
                continue
        if char == "[":
            match = _link(text, index)
            if match:
                label, url, end = match
                label_html, label_plain = _inline(label, depth + 1)
                # The platform's native sanitizer removes anchors.  Always
                # retain the complete URL visibly, so downgrade never loses it.
                same = label_plain == url
                shown = label_plain if same else f"{label_plain} ({url})"
                if _safe_url(url) and _units(url) <= 1024:
                    anchor = f'<a href="{html.escape(url, quote=True)}">{label_html}</a>'
                    out.append(anchor if same else anchor + " (" + html.escape(url) + ")")
                else:
                    out.append(html.escape(shown))
                plain.append(shown)
                index = end
                continue
        if char == "{":
            # Unknown format-style fields are literal text, not an opportunity
            # to evaluate Python attributes (or Markdown inside a field name).
            literal = re.match(r"\{[A-Za-z_][A-Za-z0-9_.:\[\]-]*\}", text[index:])
            if literal:
                out.append(html.escape(literal.group()))
                plain.append(literal.group())
                index += len(literal.group())
                continue
        matched = False
        for marker, tag in (("**", "b"), ("__", "b"), ("~~", "s"), ("*", "i"), ("_", "i")):
            if not text.startswith(marker, index):
                continue
            if marker.startswith("_") and index and text[index - 1].isalnum():
                continue
            end = _delimiter_end(text, index + len(marker), marker)
            inside = text[index + len(marker):end] if end >= 0 else ""
            if not inside or inside[0].isspace() or inside[-1].isspace():
                continue
            if marker.startswith("_") and end + len(marker) < len(text) and text[end + len(marker)].isalnum():
                continue
            rendered, readable = _inline(inside, depth + 1)
            out.append(f"<{tag}>{rendered}</{tag}>")
            plain.append(readable)
            index = end + len(marker)
            matched = True
            break
        if matched:
            continue
        out.append(html.escape(char))
        plain.append(char)
        index += 1
    return "".join(out), "".join(plain)


def _cells(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    values, current, index, code = [], [], 0, 0
    while index < len(line):
        char = line[index]
        if char == "\\" and index + 1 < len(line):
            current.extend(line[index:index + 2])
            index += 2
            continue
        if char == "`":
            length = len(line[index:]) - len(line[index:].lstrip("`"))
            code = 0 if code == length else (length if not code else code)
            current.append("`" * length)
            index += length
            continue
        if char == "|" and not code:
            values.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        index += 1
    values.append("".join(current).strip())
    return values


def _table_separator(line: str) -> bool:
    return "|" in line and all(re.fullmatch(r":?-{3,}:?", cell) for cell in _cells(line))


def _table(header: list[str], rows: list[list[str]]) -> _Block:
    width = max([len(header), *(len(row) for row in rows)])
    headers = header + [f"列 {index + 1}" for index in range(len(header), width)]
    h_values = [_inline(cell) for cell in headers]
    head = "<tr>" + "".join("<th>" + cell[0] + "</th>" for cell in h_values) + "</tr>"
    native_rows, standard_rows, plain_rows = [], [], []
    for row in rows:
        values = [_inline(cell) for cell in row + [""] * (width - len(row))]
        native_rows.append("<tr>" + "".join("<td>" + cell[0] + "</td>" for cell in values) + "</tr>")
        standard_rows.append("\n".join(
            f"<b>{h_values[index][0]}：</b> {cell[0]}" for index, cell in enumerate(values)
        ))
        plain_rows.append("\n".join(
            f"{h_values[index][1]}： {cell[1]}" for index, cell in enumerate(values)
        ))
    if not rows:
        standard_rows = [" ｜ ".join(cell[0] for cell in h_values)]
        plain_rows = [" ｜ ".join(cell[1] for cell in h_values)]
        # Native ordinary-account conversion omits header-only tables entirely.
        # A header without data is therefore a readable heading, not a table.
        return _Block(standard_rows[0], standard_rows[0], plain_rows[0])
    opening = "<table bordered striped>"
    return _Block(
        opening + head + "".join(native_rows) + "</table>",
        "\n\n".join(standard_rows), "\n\n".join(plain_rows), head, tuple(native_rows),
    )


def _blocks(text: str, depth: int = 0) -> tuple[_Block, ...]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    result, index = [], 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        fence = _FENCE.match(line)
        if fence:
            marker, language = fence.groups()
            code, index = [], index + 1
            closing = re.compile(r"^ {0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}\s*$")
            while index < len(lines) and not closing.match(lines[index]):
                code.append(lines[index])
                index += 1
            value = "\n".join(code)
            attr = f' class="language-{html.escape(language.strip(), quote=True)}"' if re.fullmatch(
                r"[\w.+-]{1,32}", language.strip(), re.ASCII
            ) else ""
            rendered = "<pre><code" + attr + ">" + html.escape(value) + "</code></pre>"
            result.append(_Block(rendered, rendered, value))
            index += 1 if index < len(lines) else 0
            continue
        if _QUOTE.match(line) and depth < 8:
            quoted = []
            while index < len(lines) and (match := _QUOTE.match(lines[index])):
                quoted.append(match.group(1))
                index += 1
            children = _blocks("\n".join(quoted), depth + 1)
            # Nested tables are represented as labelled values inside a quote.
            # Otherwise a long header could be separated from its data while
            # splitting the surrounding quote, and native downgrade would drop
            # a header-only table fragment.
            native = "<br><br>".join(child.standard if child.table_header else child.html for child in children)
            standard = "\n\n".join(child.standard for child in children)
            plain = "\n\n".join(child.plain for child in children)
            result.append(_Block("<blockquote>" + native + "</blockquote>",
                                 "<blockquote>" + standard + "</blockquote>",
                                 "\n".join("> " + part for part in plain.split("\n"))))
            continue
        if index + 1 < len(lines) and "|" in line and _table_separator(lines[index + 1]):
            header, rows, index = _cells(line), [], index + 2
            while index < len(lines) and lines[index].strip() and "|" in lines[index]:
                if _FENCE.match(lines[index]) or _QUOTE.match(lines[index]):
                    break
                rows.append(_cells(lines[index]))
                index += 1
            result.append(_table(header, rows))
            continue
        heading = _HEADING.match(line)
        if heading:
            rendered, plain = _inline(heading.group(1))
            result.append(_Block("<b>" + rendered + "</b>", "<b>" + rendered + "</b>", plain))
            index += 1
            continue
        listed = _LIST.match(line)
        if listed:
            bullet = f"{listed.group(2)}. " if listed.group(2) else "• "
            rendered, plain = _inline(listed.group(3))
            result.append(_Block(bullet + rendered, bullet + rendered, bullet + plain))
            index += 1
            continue
        paragraph = [line]
        index += 1
        while index < len(lines) and lines[index].strip():
            if _FENCE.match(lines[index]) or _QUOTE.match(lines[index]) or _HEADING.match(lines[index]) or _LIST.match(lines[index]):
                break
            if index + 1 < len(lines) and "|" in lines[index] and _table_separator(lines[index + 1]):
                break
            paragraph.append(lines[index])
            index += 1
        rendered = [_inline(part) for part in paragraph]
        result.append(_Block("<br>".join(part[0] for part in rendered),
                             "\n".join(part[0] for part in rendered),
                             "\n".join(part[1] for part in rendered)))
    return tuple(result)


def _sources_text(sources) -> str:
    values = []
    for source in sources or ():
        if isinstance(source, dict):
            url = _text(source.get("url", "")).strip()
            title = _text(source.get("title", "")).strip()
        else:
            url, title = _text(source).strip(), ""
        if not url or not _safe_url(url):
            continue
        value = f"- {title}：{url}" if title else f"- {url}"
        if value not in values:
            values.append(value)
    return "\n".join(values)


def build_reply(answer, question="", template=DEFAULT_REPLY_TEMPLATE, sources=()) -> RenderedReply:
    """Render a Markdown template without interpreting HTML or Python format fields.

    Placeholder replacement is one pass: literal ``{question}`` in an answer is
    never expanded.  A multiline value inside a quote remains entirely quoted.
    """
    answer = _text(answer)
    if not answer.strip():
        raise ValueError("AI 未返回可发送的回复")
    template = _text(template) if template is not None else DEFAULT_REPLY_TEMPLATE
    if "{answer}" not in template:
        template = (template.rstrip() + "\n\n" if template.strip() else "") + "{answer}"
    values = {"answer": answer, "question": _text(question), "sources": _sources_text(sources)}

    def replace(match):
        value = values[match.group(1)]
        line_prefix = template[template.rfind("\n", 0, match.start()) + 1:match.start()]
        quote_prefix = re.match(r"^ {0,3}(?:> ?)+", line_prefix)
        if quote_prefix:
            value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\n" + quote_prefix.group())
        return value

    blocks = _blocks(_PLACEHOLDER.sub(replace, template))
    return RenderedReply("<br><br>".join(block.html for block in blocks),
                         "\n\n".join(block.plain for block in blocks), blocks)


def _graphemes(text: str):
    """Keep common emoji/combining sequences intact while splitting UTF-16 safely."""
    cluster, regional = "", 0
    for char in text:
        code = ord(char)
        modifier = bool(unicodedata.combining(char)) or 0xFE00 <= code <= 0xFE0F or 0x1F3FB <= code <= 0x1F3FF
        is_regional = 0x1F1E6 <= code <= 0x1F1FF
        joined = cluster.endswith("\u200d") or char == "\u200d"
        if cluster and not (modifier or joined or (is_regional and regional == 1) or cluster == "\r" and char == "\n"):
            yield cluster
            cluster, regional = "", 0
        cluster += char
        regional = regional + 1 if is_regional else 0
        # An adversarial sequence of combining marks cannot exceed a message.
        if _units(cluster) > 256:
            for scalar in cluster:
                yield scalar
            cluster, regional = "", 0
    if cluster:
        yield cluster


class _HTMLTokens(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.tokens = []

    def handle_starttag(self, tag, attrs):
        self.tokens.append(("void" if tag == "br" else "start", tag, self.get_starttag_text()))

    def handle_endtag(self, tag):
        self.tokens.append(("end", tag, f"</{tag}>"))

    def handle_data(self, data):
        for part in _graphemes(data):
            self.tokens.append(("data", "", part))

    def handle_entityref(self, name):
        self.tokens.append(("data", "", f"&{name};"))

    def handle_charref(self, name):
        self.tokens.append(("data", "", f"&#{name};"))


def _split_html(content: str, limit=MAX_MESSAGE_UNITS) -> list[str]:
    if not content:
        return []
    if _units(content) <= limit:
        return [content]
    parser = _HTMLTokens()
    parser.feed(content)
    parser.close()
    chunks, parts, stack, size, visible = [], [], [], 0, False

    def closing(frames):
        return "".join(f"</{name}>" for name, _ in reversed(frames))

    for kind, name, value in parser.tokens:
        new_stack = stack + [(name, value)] if kind == "start" else stack[:-1] if kind == "end" else stack
        required = size + _units(value) + _units(closing(new_stack))
        if required > limit and visible:
            chunks.append("".join(parts) + closing(stack))
            parts = [raw for _, raw in stack]
            size = _units("".join(parts))
            visible = False
            required = size + _units(value) + _units(closing(new_stack))
        if required > limit:
            raise ValueError("单个格式片段过长，无法安全发送；请简化模板的嵌套格式")
        parts.append(value)
        size += _units(value)
        stack = new_stack
        visible = visible or kind == "data" and bool(value)
    if parts and visible:
        chunks.append("".join(parts) + closing(stack))
    return chunks


class _DeliveryPlain(HTMLParser):
    """Conservative native-to-text length estimate, including repeated labels.

    Ordinary accounts receive labelled table rows, not the raw HTML.  A short
    table with long column names can therefore grow considerably on downgrade.
    This mirrors the public downgrade shape without importing platform internals.
    """
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.rows, self.row, self.cell = [], None, None, None
        self.header = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.rows = []
        elif self.rows is not None:
            if tag == "tr":
                self.row = []
            elif tag in {"th", "td"}:
                self.cell, self.header = [], tag == "th"
        elif tag == "br":
            self.parts.append("\n")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)
        elif self.rows is None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if self.rows is not None:
            if tag in {"th", "td"} and self.cell is not None:
                value = " ".join(" ".join(self.cell).split())
                if self.row is not None:
                    self.row.append((self.header, value))
                self.cell = None
            elif tag == "tr" and self.row is not None:
                self.rows.append(self.row)
                self.row = None
            elif tag == "table":
                rows = self.rows
                if rows:
                    first = rows[0]
                    if any(header for header, _ in first) and len(rows) > 1:
                        labels = [value for _, value in first]
                        for row in rows[1:]:
                            for index, (_, value) in enumerate(row):
                                label = labels[index] if index < len(labels) else ""
                                self.parts.append(f"● {label}：{value}\n")
                            self.parts.append("\n")
                    else:
                        for row in rows:
                            self.parts.append("• " + " ｜ ".join(value for _, value in row) + "\n")
                self.rows = None
        elif tag in {"p", "div", "section", "article", "pre", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")


def _delivery_units(content: str) -> int:
    parser = _DeliveryPlain()
    parser.feed(content)
    parser.close()
    return max(_units(content), _units("".join(parser.parts)))


def _native_content(content: str) -> str:
    # Native sanitization drops anchors anyway.  Visible URLs are already in
    # the body, and removing attributes avoids unsplittable long URL tokens.
    return re.sub(r"</?a(?:\s[^>]*)?>", "", content)


def _fit_native_piece(piece: str) -> list[str]:
    if _delivery_units(piece) <= MAX_MESSAGE_UNITS:
        return [piece]
    fallback_size = _delivery_units(piece)
    limit = max(128, min(MAX_MESSAGE_UNITS - 1, int(_units(piece) * MAX_MESSAGE_UNITS / fallback_size * .85)))
    smaller = _split_html(piece, limit)
    if len(smaller) == 1:
        raise ValueError("回复表格无法安全分段，请简化过长的表头")
    return [fitted for part in smaller for fitted in _fit_native_piece(part)]


def _native_table_chunks(block: _Block) -> list[str]:
    opening, closing = "<table bordered striped>", "</table>"
    head = _native_content(block.table_header)
    chunks, rows = [], []
    if any(_delivery_units(opening + head + _native_content(row) + closing) > MAX_MESSAGE_UNITS for row in block.table_rows):
        # A cell/header that alone exceeds Telegram's limit cannot remain one
        # native table row.  Preserve every value using the readable labelled
        # representation instead of producing header-only fragments (which
        # ordinary-account downgrade would discard).
        return [fitted for part in _split_html(_native_content(block.standard)) for fitted in _fit_native_piece(part)]
    for raw_row in block.table_rows:
        row = _native_content(raw_row)
        candidate = opening + head + "".join(rows) + row + closing
        if _delivery_units(candidate) <= MAX_MESSAGE_UNITS:
            rows.append(row)
            continue
        if rows:
            chunks.append(opening + head + "".join(rows) + closing)
            rows = []
        rows = [row]
    if rows:
        chunks.append(opening + head + "".join(rows) + closing)
    return chunks or [fitted for part in _split_html(_native_content(block.html)) for fitted in _fit_native_piece(part)]


def _chunks(rendered: RenderedReply, native: bool) -> list[str]:
    chunks, current = [], ""
    separator = "<br><br>" if native else "\n\n"
    for block in rendered._blocks:
        if native:
            pieces = _native_table_chunks(block) if block.table_rows else [
                fitted for part in _split_html(_native_content(block.html)) for fitted in _fit_native_piece(part)
            ]
        else:
            pieces = _split_html(block.standard)
        for piece in pieces:
            candidate = current + separator + piece if current else piece
            if (_delivery_units(candidate) if native else _units(candidate)) <= MAX_MESSAGE_UNITS:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = piece
    if current:
        chunks.append(current)
    return [part for chunk in chunks for part in _visible_chunks(chunk, native)]


def _visible_chunks(piece: str, native: bool) -> list[str]:
    if _to_plain(piece).strip():
        return [piece]
    # Long spaces/indentation can occupy a whole chunk.  Telegram rejects an
    # empty/whitespace-only message, and the native plain downgrade strips its
    # edges.  Visible markers on both sides retain the original code/text
    # whitespace and allow subsequent chunks to be delivered without loss.
    newline = "<br>" if native else "\n"
    prefix = "<i>空白续段</i>" + newline
    suffix = newline + "<i>续段结束</i>"
    budget = MAX_MESSAGE_UNITS - _units(prefix + suffix) - 16
    return [prefix + part + suffix for part in _split_html(piece, budget)]


class _PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.parts.append("\n")


def _to_plain(content: str) -> str:
    parser = _PlainHTML()
    parser.feed(content)
    parser.close()
    return "".join(parser.parts)


@dataclass(frozen=True)
class _DeliveredMessage:
    id: int
    _client: Any = field(repr=False)
    _chat_id: Any = field(repr=False)

    async def delete(self):
        return await self._client.delete_messages(self._chat_id, [self.id])


def _peer_id(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value) if re.fullmatch(r"-?\d+", value) else None
    try:
        from telethon.utils import get_peer_id
        return get_peer_id(value)
    except (ImportError, TypeError, ValueError, AttributeError):
        return None


def _message_results(result, client, chat_id) -> list:
    """Flatten normal Messages and raw Updates; never return an Updates envelope."""
    if result is None:
        return []
    if isinstance(result, (list, tuple)):
        return [message for item in result for message in _message_results(item, client, chat_id)]
    if getattr(result, "out", None) is False:
        return []
    peer = getattr(result, "chat_id", None)
    if peer is None:
        peer = getattr(result, "peer_id", None)
    if peer is not None:
        actual, expected = _peer_id(peer), _peer_id(chat_id)
        if actual is None or expected is None or actual != expected:
            # Raw Updates can contain unrelated messages.  Never schedule
            # cleanup for a different chat (or an unverifiable target).
            return []
    if hasattr(result, "id") and (callable(getattr(result, "delete", None)) or callable(getattr(result, "edit", None))):
        if hasattr(result, "_client") and result._client is None:
            return [_DeliveredMessage(result.id, client, chat_id)]
        return [result]
    if type(result).__name__ == "UpdateShortSentMessage" and isinstance(getattr(result, "id", None), int):
        return [_DeliveredMessage(result.id, client, chat_id)]
    updates = getattr(result, "updates", None)
    if isinstance(updates, (list, tuple)):
        return [message for update in updates for message in _message_results(getattr(update, "message", None), client, chat_id)]
    return []


def _format_error(exc: Exception) -> bool:
    if type(exc).__name__ in _FORMAT_ERROR_NAMES:
        return True
    # Some Telegram wrappers expose Bot API BadRequest rather than typed errors.
    return type(exc).__name__ in {"BadRequest", "BadRequestError"} and bool(re.search(
        r"can't parse entities|cannot parse entities|unsupported start tag|unclosed start tag|entity bounds", str(exc), re.I
    ))


async def send_reply(client, chat_id, rendered: RenderedReply, rich=True, reply_to=None, *, on_sent=None) -> list:
    """Send in order without truncation, retrying only explicit format rejection.

    ``send_rich`` performs Premium capability checks and its own safe downgrade.
    A timeout/network exception is never retried as another message, because
    the first request may already have reached Telegram.
    """
    if not rendered.plain.strip():
        raise ValueError("AI 未返回可发送的回复")
    native = bool(rich and callable(getattr(client, "send_rich", None)))
    sent = []
    for piece in _chunks(rendered, native):
        if native:
            options = {"reply_to_message_id": reply_to} if reply_to is not None else {}
            result = await client.send_rich(chat_id, piece, format="html", **options)
        else:
            options = {"reply_to": reply_to} if reply_to is not None else {}
            try:
                result = await client.send_message(chat_id, piece, parse_mode="html", **options)
            except Exception as exc:
                if not _format_error(exc):
                    raise
                result = await client.send_message(chat_id, _to_plain(piece), parse_mode=None, **options)
        for message in _message_results(result, client, chat_id):
            sent.append(message)
            if on_sent is not None:
                callback_result = on_sent(message)
                # A synchronous callback may return a scheduled Task (e.g.
                # delayed cleanup).  Do not wait for that background task.
                if inspect.iscoroutine(callback_result):
                    await callback_result
    return sent
