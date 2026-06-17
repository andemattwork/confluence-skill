"""Inline comment detection and backup for Confluence pages.

Confluence anchors inline comments to page text via storage-format markers:
    <ac:inline-comment-marker ac:ref="UUID">anchored text</ac:inline-comment-marker>
A full-body page update that drops these markers orphans the comments, and
version-restore does NOT re-anchor them. These helpers detect markers, back
them up to JSON, and gate full-body uploads.
"""

from __future__ import annotations

import html
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

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
    # Unescape HTML entities so anchored_text matches the rendered text a human
    # selects when re-creating an orphaned comment (e.g. &quot; -> ").
    return [{"ref": ref, "anchored_text": html.unescape("".join(grouped[ref]))}
            for ref in order]


def count_inline_markers(storage_xml: str) -> int:
    """Number of distinct inline-comment anchors in the storage body."""
    return len(extract_inline_markers(storage_xml))


def get_page(session, api_base: str, page_id: str, expand: str) -> dict:
    """Fetch a page via raw REST. Raises on HTTP error."""
    resp = session.get(f"{api_base}/content/{page_id}", params={"expand": expand})
    resp.raise_for_status()
    return resp.json()


def fetch_inline_comments(session, api_base: str, page_id: str) -> list:
    """Best-effort fetch of inline comments via raw REST. Never raises.

    Returns [] on any non-200 response, network error, or JSON error. Status
    strings are recorded verbatim (DC uses 'closed', not 'resolved').
    """
    url = f"{api_base}/content/{page_id}/child/comment"
    params = {
        "location": "inline",
        "expand": "body.storage,extensions.inlineProperties,extensions.resolution,version",
        "limit": 200,
    }
    try:
        resp = session.get(url, params=params)
        if resp.status_code != 200:
            logger.warning("Inline comment fetch returned %s for page %s",
                           resp.status_code, page_id)
            return []
        data = resp.json()

        out = []
        for item in data.get("results", []):
            ext = item.get("extensions") or {}
            inline_props = ext.get("inlineProperties") or {}
            resolution = ext.get("resolution") or {}
            body_value = ((item.get("body") or {}).get("storage") or {}).get("value", "")
            version = item.get("version") or {}
            out.append({
                "id": item.get("id"),
                "marker_ref": inline_props.get("markerRef"),
                "original_selection": inline_props.get("originalSelection", ""),
                "body_text": _TAG_RE.sub('', body_value).strip(),
                "author": (version.get("by") or {}).get("displayName", ""),
                "created": version.get("when", ""),
                "status": resolution.get("status", ""),
            })
        return out
    except Exception as e:  # network, JSON decode, malformed data, etc.
        logger.warning("Inline comment fetch failed for page %s: %s", page_id, e)
        return []


def correlate(markers: list, comments: list) -> list:
    """Join storage markers with API comments on ref==marker_ref.

    Storage markers (authoritative anchor text) always survive. API comments
    with no matching marker are appended so nothing is dropped.
    """
    by_ref = {c["marker_ref"]: c for c in comments if c.get("marker_ref")}
    matched = set()
    result = []
    for m in markers:
        c = by_ref.get(m["ref"], {})
        if c:
            matched.add(m["ref"])
        result.append({
            "ref": m["ref"],
            "anchored_text": m["anchored_text"],
            "body_text": c.get("body_text", ""),
            "author": c.get("author", ""),
            "created": c.get("created", ""),
            "status": c.get("status", ""),
            "original_selection": c.get("original_selection", ""),
        })
    for c in comments:
        ref = c.get("marker_ref")
        if ref in matched:
            continue
        result.append({
            "ref": ref,
            "anchored_text": "",
            "body_text": c.get("body_text", ""),
            "author": c.get("author", ""),
            "created": c.get("created", ""),
            "status": c.get("status", ""),
            "original_selection": c.get("original_selection", ""),
        })
    return result


def write_backup(page_meta: dict, correlated: list, output_dir) -> Path:
    """Write the authoritative JSON snapshot; return its path."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    fname = f"comments-{page_meta['id']}-v{page_meta['version']}-{ts}.json"
    path = output_dir / fname
    payload = {
        "page": page_meta,
        "comment_count": len(correlated),
        "comments": correlated,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def backup_from_page(session, api_base: str, page: dict, output_dir) -> Path:
    """Build and write a backup from an already-fetched page dict."""
    body = ((page.get("body") or {}).get("storage") or {}).get("value", "")
    markers = extract_inline_markers(body)
    comments = fetch_inline_comments(session, api_base, page["id"])
    correlated = correlate(markers, comments)
    page_meta = {
        "id": page["id"],
        "version": (page.get("version") or {}).get("number"),
        "title": page.get("title", ""),
        "url": (page.get("_links") or {}).get("webui", ""),
        "exported_at": datetime.now().isoformat(timespec="seconds"),
    }
    return write_backup(page_meta, correlated, output_dir)


def preflight_guard(session, api_base: str, page_id: str, *, dry_run: bool,
                    allow_orphan_comments: bool,
                    backup_dir: str = "confluence_comment_backups") -> dict:
    """Detect inline comments before a full-body update.

    Backs up when any exist. Returns {"count", "backup_path", "blocked"};
    the caller is responsible for exiting when blocked is True.
    """
    page = get_page(session, api_base, page_id, "body.storage,version")
    body = ((page.get("body") or {}).get("storage") or {}).get("value", "")
    count = count_inline_markers(body)
    backup_path = None
    blocked = False

    if count > 0:
        backup_path = backup_from_page(session, api_base, page, backup_dir)
        if dry_run:
            print(f"⚠️  Page has {count} inline comment(s). A full-body upload "
                  f"would orphan all of them. Backup written: {backup_path}")
        elif not allow_orphan_comments:
            blocked = True
            print(
                f"❌ Page has {count} inline comment(s). A full-body upload orphans "
                f"all of them, and version-restore will NOT recover them.\n"
                f"   Backup written: {backup_path}\n"
                f"   Use patch_storage_fragment.py for anchor-preserving edits, or "
                f"re-run with --allow-orphan-comments to proceed anyway.",
                file=sys.stderr,
            )
        else:
            print(f"⚠️  Proceeding despite {count} inline comment(s); they will be "
                  f"orphaned. Backup written: {backup_path}")

    return {"count": count, "backup_path": backup_path, "blocked": blocked}


def verify_after_upload(session, api_base: str, page_id: str, before_count: int,
                        backup_path=None) -> int:
    """Re-count markers after an update and report any orphaned comments."""
    page = get_page(session, api_base, page_id, "body.storage")
    body = ((page.get("body") or {}).get("storage") or {}).get("value", "")
    after = count_inline_markers(body)
    print(f"Inline comments: {before_count} -> {after}")
    if after < before_count:
        loc = f" Backup: {backup_path}" if backup_path else ""
        print(f"⚠️  WARNING: {before_count - after} inline comment(s) orphaned.{loc}",
              file=sys.stderr)
    return after
