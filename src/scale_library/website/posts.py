"""
Mailing list post loader.

Reads from the local YahooTuningGroupsUltimateBackup submodule.
Builds a msg_id index on first call, then caches per list name.
"""

import datetime
import email as email_lib
import html
import json
import re
from functools import lru_cache
from html.parser import HTMLParser

from scale_library.website.data import REPO_ROOT

BACKUP_DIR = REPO_ROOT / "sources" / "YahooTuningGroupsUltimateBackup" / "src"


@lru_cache(maxsize=None)
def _build_index(list_name: str) -> dict[int, dict]:
    """Return msg_id → message dict for a given list. Cached per list."""
    messages_dir = BACKUP_DIR / list_name / "messages"
    if not messages_dir.exists():
        return {}
    index: dict[int, dict] = {}
    for path in sorted(messages_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            continue
        for msg in data:
            mid = msg.get("msgId")
            if mid is not None:
                index[mid] = msg
    return index


def _decode(s: str) -> str:
    """Unescape HTML entities and strip trailing whitespace."""
    return html.unescape(s).strip()


def _strip_html_tags(text: str) -> str:
    """Strip HTML tags from text, preserving content and converting block tags to newlines.

    The ygroups-quoted div (inline quoted replies) is dropped entirely since the
    thread is shown separately and the quoted content just adds noise and blank lines.
    """

    class _Stripper(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts: list[str] = []
            # When >0 we are inside a ygroups-quoted div; track nesting
            self._skip_depth = 0
            # Nesting depth of all divs while inside the skipped section
            self._div_depth = 0

        def handle_starttag(self, tag: str, attrs) -> None:
            attr_dict = dict(attrs)
            cls = attr_dict.get("class") or ""
            if self._skip_depth:
                if tag == "div":
                    self._div_depth += 1
                return
            if "ygroups-quoted" in cls or "ygrp-quoted" in cls:
                self._skip_depth = 1
                self._div_depth = 1
                return
            if tag in ("br", "p", "div", "li", "tr"):
                self.parts.append("\n")

        def handle_endtag(self, tag: str) -> None:
            if self._skip_depth and tag == "div":
                self._div_depth -= 1
                if self._div_depth == 0:
                    self._skip_depth = 0

        def handle_data(self, data: str) -> None:
            if not self._skip_depth:
                self.parts.append(data)

    stripper = _Stripper()
    stripper.feed(text)
    result = "".join(stripper.parts)
    # Strip lines that are only whitespace
    result = "\n".join(line if line.strip() else "" for line in result.splitlines())
    # Collapse runs of 3+ newlines (2+ blank lines) to one blank line
    return re.sub(r"\n{3,}", "\n\n", result).strip()


_HTML_TAG_RE = re.compile(
    r"</[a-zA-Z]"  # any closing tag — almost never in plain text
    r"|<(?:html|body|p|br|div|span|a|table"
    r"|font|b|i|u|em|strong|pre|code|big|small"
    r"|ul|ol|li|h[1-6]|blockquote|strike|s|sub|sup"
    r"|td|tr|th|ins|del|q)\b",
    re.IGNORECASE,
)


def _clean_body(body: str) -> str:
    """Strip HTML markup from email body if any HTML tags are detected."""
    body = body.strip()
    if _HTML_TAG_RE.search(body):
        body = _strip_html_tags(body)
    return body.strip()


def get_post(list_name: str, msg_id: int) -> dict | None:
    """
    Return a dict with cleaned fields for a single post, or None if not found.

    Keys: subject, author, date_ts, body, url
    """
    index = _build_index(list_name)
    msg = index.get(msg_id)
    if msg is None:
        return None
    return _clean_msg(list_name, msg)


def get_thread(list_name: str, topic_id: int, start_msg_id: int) -> list[dict]:
    """
    Return a list of cleaned post dicts for the thread containing start_msg_id,
    starting from start_msg_id and following nextInTopic links up to THREAD_CAP.
    """
    index = _build_index(list_name)
    results = []
    msg_id = start_msg_id
    seen: set[int] = set()
    while msg_id and msg_id not in seen:
        msg = index.get(msg_id)
        if msg is None:
            break
        # Only include messages from same topic
        if msg.get("topicId") != topic_id:
            break
        seen.add(msg_id)
        results.append(_clean_msg(list_name, msg))
        msg_id = msg.get("nextInTopic")
    return results


def get_topic_subject(list_name: str, topic_id: int) -> str | None:
    """Return the subject of the first message in a topic, or None if not found."""
    index = _build_index(list_name)
    msgs = [msg for msg in index.values() if msg.get("topicId") == topic_id]
    if not msgs:
        return None
    first = min(msgs, key=lambda m: m.get("msgId", float("inf")))
    return _decode(first.get("subject", ""))


def _clean_msg(list_name: str, msg: dict) -> dict:
    raw_email = html.unescape(msg.get("rawEmail", "")).strip()

    # Use the email library to decode Content-Transfer-Encoding (e.g. quoted-printable)
    parsed = email_lib.message_from_string(raw_email)

    body = None
    if parsed.is_multipart():
        # Prefer the text/plain part; fall back to text/html (stripped).
        for part in parsed.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload is not None:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        body = payload.decode(charset, errors="replace").strip()
                    except LookupError:
                        body = payload.decode("latin-1", errors="replace").strip()
                    break
            elif ct == "text/html" and body is None:
                payload = part.get_payload(decode=True)
                if payload is not None:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        body = payload.decode(charset, errors="replace").strip()
                    except LookupError:
                        body = payload.decode("latin-1", errors="replace").strip()

    if body is None:
        payload = parsed.get_payload(decode=True)
        if payload is not None:
            charset = parsed.get_content_charset() or "utf-8"
            try:
                body = payload.decode(charset, errors="replace").strip()
            except LookupError:
                body = payload.decode("latin-1", errors="replace").strip()
        else:
            # Fallback for unparseable messages: use regex heuristic.
            parts = raw_email.split("\n\n", 1)
            body = parts[1].strip() if len(parts) > 1 else raw_email

    body = _clean_body(body)

    mid = msg.get("msgId", 0)
    if _HTML_TAG_RE.search(body):
        raise ValueError(
            f"HTML tags remain in body of {list_name} msg {mid}"
        )
    topic_id = msg.get("topicId", 0)
    url = (
        f"https://yahootuninggroupsultimatebackup.github.io"
        f"/{list_name}/topicId_{topic_id}.html#{mid}"
    )

    # Format date from Unix timestamp

    ts = msg.get("postDate")
    date_str = (
        datetime.datetime.fromtimestamp(int(ts), tz=datetime.timezone.utc).strftime(
            "%Y-%m-%d"
        )
        if ts
        else ""
    )

    return {
        "msg_id": mid,
        "topic_id": topic_id,
        "subject": _decode(msg.get("subject", "")),
        "author": _decode(msg.get("authorName", "")),
        "date_ts": ts,
        "date": date_str,
        "body": body,
        "url": url,
    }
