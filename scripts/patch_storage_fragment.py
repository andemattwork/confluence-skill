#!/usr/bin/env python3
"""Patch one Confluence storage fragment safely.

Default mode is dry-run: it writes before/preview snapshots and validates the
result without updating Confluence. Use --apply to write.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if SCRIPT_DIR.exists():
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from confluence_auth import get_confluence_client
except ImportError:  # pragma: no cover
    get_confluence_client = None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def count_all(body: str, fragments: Iterable[str]) -> dict[str, int]:
    return {fragment: body.count(fragment) for fragment in fragments}


def validate_fragments(body: str, required: list[str], forbidden: list[str]) -> None:
    missing = [fragment for fragment in required if fragment not in body]
    present_forbidden = [fragment for fragment in forbidden if fragment in body]
    if missing or present_forbidden:
        raise SystemExit(
            "Validation failed: "
            f"missing_required={missing}, present_forbidden={present_forbidden}"
        )


def apply_replacement(body: str, old: str | None, new: str, pattern: str | None) -> tuple[str, int]:
    if old is not None:
        matches = body.count(old)
        if matches != 1:
            raise SystemExit(f"Expected exact old fragment once, found {matches}")
        return body.replace(old, new, 1), matches

    if pattern is None:
        raise SystemExit("Either --old-file or --regex must be provided")

    regex = re.compile(pattern, re.DOTALL)
    matches = list(regex.finditer(body))
    if len(matches) != 1:
        raise SystemExit(f"Expected regex to match once, found {len(matches)}")
    return regex.sub(new, body, count=1), len(matches)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Patch one Confluence storage fragment with before/preview/read-back validation"
    )
    parser.add_argument("--page-id", required=True, help="Confluence page ID")
    parser.add_argument("--old-file", type=Path, help="File containing exact old storage fragment")
    parser.add_argument("--new-file", type=Path, required=True, help="File containing replacement storage fragment")
    parser.add_argument("--regex", help="Regex selecting one old storage fragment; ignored when --old-file is set")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for before/preview snapshots")
    parser.add_argument("--require", action="append", default=[], help="Required storage fragment after replacement; repeatable")
    parser.add_argument("--forbid", action="append", default=[], help="Forbidden storage fragment after replacement; repeatable")
    parser.add_argument("--count", action="append", default=[], help="Print count for this storage fragment; repeatable")
    parser.add_argument("--comment", default="Storage fragment patch", help="Confluence version comment")
    parser.add_argument("--apply", action="store_true", help="Apply update. Without this flag, only dry-run preview is created")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if get_confluence_client is None:
        raise SystemExit("Cannot import confluence_auth.get_confluence_client")

    old = read_text(args.old_file) if args.old_file else None
    new = read_text(args.new_file)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    confluence = get_confluence_client()
    page = confluence.get_page_by_id(args.page_id, expand="version,body.storage,ancestors")
    body = page["body"]["storage"]["value"]
    version = page["version"]["number"]
    title = page["title"]
    ancestors = page.get("ancestors") or []
    parent_id = ancestors[-1]["id"] if ancestors else None

    updated, match_count = apply_replacement(body, old, new, args.regex)
    validate_fragments(updated, args.require, args.forbid)

    before_path = args.output_dir / f"confluence-storage-{args.page_id}-v{version}-before.xml"
    preview_path = args.output_dir / f"confluence-storage-{args.page_id}-v{version}-preview.xml"
    before_path.write_text(body, encoding="utf-8")
    preview_path.write_text(updated, encoding="utf-8")

    print(f"page_id={args.page_id}")
    print(f"version={version}")
    print(f"dry_run={not args.apply}")
    print(f"matches={match_count}")
    print(f"before={before_path}")
    print(f"preview={preview_path}")
    for fragment, value in count_all(updated, args.count).items():
        print(f"count[{fragment}]={value}")

    if not args.apply:
        return 0

    result = confluence.update_page(
        page_id=args.page_id,
        title=title,
        body=updated,
        parent_id=parent_id,
        type="page",
        representation="storage",
        minor_edit=False,
        version_comment=args.comment,
        always_update=True,
    )
    verified = confluence.get_page_by_id(args.page_id, expand="version,body.storage")
    new_version = verified["version"]["number"]
    if new_version <= version:
        raise SystemExit(f"Version did not increase: {new_version} <= {version}")
    validate_fragments(verified["body"]["storage"]["value"], args.require, args.forbid)
    print(f"updated_version={new_version}")
    print(f"url={confluence.url}{result['_links']['webui']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
