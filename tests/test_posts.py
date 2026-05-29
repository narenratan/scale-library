"""Tests for mailing-list post body cleaning."""

import re

import pytest

from scale_library.website.posts import _clean_body, _strip_html_tags

# Regex that matches any remaining *known* HTML tag in cleaned output.
# Entity-decoded angle brackets like <formula> are expected text, not tags.
_TAG_RE = re.compile(
    r"</?(?:html|head|body|div|span|p|br|a|b|i|u|em|strong|pre|code"
    r"|ul|ol|li|table|tr|td|th|h[1-6]|blockquote|font|style|script"
    r"|big|small|sub|sup|strike|ins|del|q)\b",
    re.IGNORECASE,
)


def _has_tags(text: str) -> bool:
    return bool(_TAG_RE.search(text))


# --- _strip_html_tags ---


def test_strip_tags_plain_text_preserved():
    assert _strip_html_tags("<p>Hello world</p>") == "Hello world"


def test_strip_tags_nested_inline():
    assert _strip_html_tags("<p><b>bold</b> and <i>italic</i></p>") == "bold and italic"


def test_strip_tags_entities_decoded():
    # &amp; should decode to & in the output.
    result = _strip_html_tags("<p>a &amp; b</p>")
    assert result == "a & b"


def test_strip_tags_lt_gt_entities_preserved_as_text():
    # &lt;b&gt; in text content must NOT be treated as a tag — regression for
    # the pre-unescape bug where html.unescape() was called before HTMLParser.
    result = _strip_html_tags("<p>Use &lt;b&gt; for bold</p>")
    assert "<b>" in result
    assert "Use" in result
    assert "for bold" in result


def test_strip_tags_no_tags_in_output():
    html = "<div><p>Some <b>text</b> with a &lt;formula&gt;</p></div>"
    result = _strip_html_tags(html)
    assert not _has_tags(result)
    assert "<formula>" in result  # decoded entity survives as text


def test_strip_tags_ygroups_quoted_dropped():
    html = (
        '<p>My reply.</p>'
        '<div class="ygrp-quoted"><p>Original message here.</p></div>'
        '<p>After quote.</p>'
    )
    result = _strip_html_tags(html)
    assert "My reply." in result
    assert "Original message here." not in result
    assert "After quote." in result


def test_strip_tags_ygroups_quoted_nested_divs():
    # Nested divs inside the skip zone must not prematurely end skipping.
    html = (
        '<p>Before.</p>'
        '<div class="ygrp-quoted">'
        '  <div><div>Deep nested.</div></div>'
        '  <p>Also quoted.</p>'
        '</div>'
        '<p>After.</p>'
    )
    result = _strip_html_tags(html)
    assert "Before." in result
    assert "Deep nested." not in result
    assert "Also quoted." not in result
    assert "After." in result


def test_strip_tags_blank_line_collapse():
    # Many block tags should not produce more than one blank line.
    html = "<p>A</p><p></p><p></p><p>B</p>"
    result = _strip_html_tags(html)
    assert "\n\n\n" not in result


# --- _clean_body ---


def test_clean_body_plain_text_untouched():
    text = "This is a plain text email.\nWith two lines."
    assert _clean_body(text) == text


def test_clean_body_plain_text_with_html_examples_stripped():
    # Plain-text email discussing HTML syntax: tags stripped, text preserved.
    text = 'Use <A HREF="x.htm">link</A> for hyperlinks.'
    result = _clean_body(text)
    assert "link" in result
    assert not _has_tags(result)


def test_clean_body_strips_html():
    result = _clean_body("<p>Hello <b>world</b></p>")
    assert result == "Hello world"
    assert not _has_tags(result)


def test_clean_body_lt_gt_in_html_text():
    # Core regression: &lt;/&gt; in HTML body must survive as literal text.
    result = _clean_body("<p>The formula x &lt; y &amp; z &gt; 0</p>")
    assert "x < y" in result
    assert "z > 0" in result
    assert not _has_tags(result)


def test_clean_body_no_tags_in_output_html():
    body = (
        "<html><body>"
        "<p>See &lt;section 3&gt; for details.</p>"
        "<p>More text with <a href='#'>a link</a>.</p>"
        "</body></html>"
    )
    result = _clean_body(body)
    assert not _has_tags(result)
    assert "<section 3>" in result
    assert "More text with" in result
    assert "a link" in result
