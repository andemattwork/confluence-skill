#!/usr/bin/env python3
"""Back up a Confluence page's inline comments to JSON (read-only).

Usage:
    python3 backup_inline_comments.py --id 123456789
    python3 backup_inline_comments.py --id 123456789 --output-dir ./backups
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from confluence_auth import get_rest_session
    from inline_comments import get_page, backup_from_page, count_inline_markers
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Back up inline comments for a Confluence page to JSON")
    parser.add_argument("--id", required=True, help="Confluence page ID")
    parser.add_argument("--output-dir", default="confluence_comment_backups",
                        help="Directory for the JSON snapshot")
    parser.add_argument("--env-file", default=None, help="Path to .env file")
    args = parser.parse_args()

    session, api_base, _ = get_rest_session(args.env_file)
    page = get_page(session, api_base, args.id, "body.storage,version")
    body = ((page.get("body") or {}).get("storage") or {}).get("value", "")
    count = count_inline_markers(body)
    path = backup_from_page(session, api_base, page, args.output_dir)

    print(f"Inline comments: {count}")
    print(f"Backup written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
