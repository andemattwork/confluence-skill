#!/usr/bin/env python3
"""Replace one Confluence storage macro after a heading with native draw.io.

Creates a draw.io storage macro that references an uploaded `.drawio`
attachment (`application/vnd.jgraph.mxfile`). Default mode is dry-run. Use
--apply to upload the attachment and update the page.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if SCRIPT_DIR.exists():
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from confluence_auth import get_confluence_client
except ImportError:  # pragma: no cover
    get_confluence_client = None


def drawio_macro(diagram_name: str, width: int, height: int, revision: int) -> str:
    return f'''<ac:structured-macro ac:name="drawio" ac:schema-version="1">
<ac:parameter ac:name="border">true</ac:parameter>
<ac:parameter ac:name="diagramName">{diagram_name}</ac:parameter>
<ac:parameter ac:name="simpleViewer">false</ac:parameter>
<ac:parameter ac:name="links">auto</ac:parameter>
<ac:parameter ac:name="tbstyle">top</ac:parameter>
<ac:parameter ac:name="lbox">true</ac:parameter>
<ac:parameter ac:name="diagramWidth">{width}</ac:parameter>
<ac:parameter ac:name="height">{height}</ac:parameter>
<ac:parameter ac:name="revision">{revision}</ac:parameter>
</ac:structured-macro>'''


def replace_macro_after_heading(body: str, heading_html: str, macro_name: str, replacement: str) -> str:
    pattern = re.compile(
        rf"({re.escape(heading_html)}\s*)"
        rf"<ac:structured-macro\s+ac:name=\"{re.escape(macro_name)}\"(?:(?!</ac:structured-macro>).)*</ac:structured-macro>",
        re.DOTALL,
    )
    matches = list(pattern.finditer(body))
    if len(matches) != 1:
        raise SystemExit(f"Expected one {macro_name} macro after heading, found {len(matches)}")
    return pattern.sub(r"\1" + replacement, body, count=1)


def validate(body: str, diagram_name: str, required: list[str], forbidden: list[str]) -> None:
    checks = {
        "drawio_macros": body.count('ac:name="drawio"'),
        "diagram_name": body.count(f'<ac:parameter ac:name="diagramName">{diagram_name}</ac:parameter>'),
    }
    for key, value in checks.items():
        print(f"{key}={value}")
    if checks["drawio_macros"] < 1 or checks["diagram_name"] != 1:
        raise SystemExit(f"Draw.io validation failed: {checks}")
    missing = [fragment for fragment in required if fragment not in body]
    present_forbidden = [fragment for fragment in forbidden if fragment in body]
    if missing or present_forbidden:
        raise SystemExit(
            "Fragment validation failed: "
            f"missing_required={missing}, present_forbidden={present_forbidden}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replace one native macro after a heading with a draw.io macro")
    parser.add_argument("--page-id", required=True, help="Confluence page ID")
    parser.add_argument("--heading-html", required=True, help="Exact heading HTML before target macro, e.g. '<h2>Architecture</h2>'")
    parser.add_argument("--old-macro-name", default="plantuml", help="Macro name to replace after heading")
    parser.add_argument("--drawio-file", type=Path, required=True, help="Local .drawio file to attach")
    parser.add_argument("--diagram-name", help="Attachment/diagram name. Defaults to drawio file basename")
    parser.add_argument("--width", type=int, default=1000, help="draw.io macro diagramWidth")
    parser.add_argument("--height", type=int, default=600, help="draw.io macro height")
    parser.add_argument("--revision", type=int, default=1, help="draw.io macro revision")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for before/preview snapshots")
    parser.add_argument("--require", action="append", default=[], help="Required storage fragment after replacement; repeatable")
    parser.add_argument("--forbid", action="append", default=[], help="Forbidden storage fragment after replacement; repeatable")
    parser.add_argument("--comment", default="Replace macro with native draw.io diagram", help="Confluence version comment")
    parser.add_argument("--apply", action="store_true", help="Apply update. Without this flag, only dry-run preview is created")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if get_confluence_client is None:
        raise SystemExit("Cannot import confluence_auth.get_confluence_client")
    if not args.drawio_file.exists():
        raise SystemExit(f"Missing drawio file: {args.drawio_file}")
    if args.drawio_file.suffix.lower() != ".drawio":
        raise SystemExit("--drawio-file must have .drawio extension")

    diagram_name = args.diagram_name or args.drawio_file.name
    args.output_dir.mkdir(parents=True, exist_ok=True)

    confluence = get_confluence_client()
    page = confluence.get_page_by_id(args.page_id, expand="version,body.storage,ancestors")
    body = page["body"]["storage"]["value"]
    version = page["version"]["number"]
    title = page["title"]
    ancestors = page.get("ancestors") or []
    parent_id = ancestors[-1]["id"] if ancestors else None

    replacement = drawio_macro(diagram_name, args.width, args.height, args.revision)
    updated = replace_macro_after_heading(body, args.heading_html, args.old_macro_name, replacement)
    validate(updated, diagram_name, args.require, args.forbid)

    before_path = args.output_dir / f"confluence-storage-{args.page_id}-v{version}-before-drawio.xml"
    preview_path = args.output_dir / f"confluence-storage-{args.page_id}-v{version}-preview-drawio.xml"
    before_path.write_text(body, encoding="utf-8")
    preview_path.write_text(updated, encoding="utf-8")

    print(f"page_id={args.page_id}")
    print(f"version={version}")
    print(f"dry_run={not args.apply}")
    print(f"drawio_file={args.drawio_file}")
    print(f"diagram_name={diagram_name}")
    print(f"before={before_path}")
    print(f"preview={preview_path}")

    if not args.apply:
        return 0

    confluence.attach_file(
        filename=str(args.drawio_file),
        name=diagram_name,
        content_type="application/vnd.jgraph.mxfile",
        page_id=args.page_id,
        comment="draw.io diagram source",
    )
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
    validate(verified["body"]["storage"]["value"], diagram_name, args.require, args.forbid)
    print(f"updated_version={new_version}")
    print(f"url={confluence.url}{result['_links']['webui']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
