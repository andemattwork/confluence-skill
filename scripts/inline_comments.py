"""Inline comment detection and backup for Confluence pages.

Confluence anchors inline comments to page text via storage-format markers:
    <ac:inline-comment-marker ac:ref="UUID">anchored text</ac:inline-comment-marker>
A full-body page update that drops these markers orphans the comments, and
version-restore does NOT re-anchor them. These helpers detect markers, back
them up to JSON, and gate full-body uploads.
"""

from __future__ import annotations

import re

# One inline-comment-marker element. ac:ref may not be the first attribute, and
# the inner body may contain nested tags.
_MARKER_RE = re.compile(
    r'<ac:inline-comment-marker\b[^>]*?\bac:ref="([^"]+)"[^>]*?>(.*?)</ac:inline-comment-marker>',
    re.DOTALL,
)
_TAG_RE = re.compile(r'<[^>]+>')


def extract_inline_markers(storage_xml: str) -> list:
    """Return one entry per DISTINCT marker ref, anchor text joined in order.

    A single comment's marker can repeat across element boundaries with the same
    ref; those fragments are concatenated in document order.
    """
    if not storage_xml:
        return []
    grouped = {}
    order = []
    for match in _MARKER_RE.finditer(storage_xml):
        ref = match.group(1)
        inner = _TAG_RE.sub('', match.group(2))
        if ref not in grouped:
            grouped[ref] = []
            order.append(ref)
        grouped[ref].append(inner)
    return [{"ref": ref, "anchored_text": "".join(grouped[ref])} for ref in order]


def count_inline_markers(storage_xml: str) -> int:
    """Number of distinct inline-comment anchors in the storage body."""
    return len(extract_inline_markers(storage_xml))
