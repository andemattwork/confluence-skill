---
name: confluence
description: Manage Confluence documentation with downloads, uploads, conversions, and diagrams. Use when asked to "download Confluence pages", "upload to Confluence", "convert Wiki Markup", "sync markdown to Confluence", "create Confluence page", or "handle Confluence images".
---

# Confluence Management Skill

Manage Confluence documentation through Claude Code: download pages to Markdown, upload large documents with images, convert between formats, and integrate Mermaid/PlantUML diagrams.

## Table of Contents

- [Quick Decision Matrix](#quick-decision-matrix)
- [REST Script Workflows](#rest-script-workflows)
- [Prerequisites](#prerequisites)
- [Core Workflows](#core-workflows)
- [Reference Documentation](#reference-documentation)

## Quick Decision Matrix

| Task | Tool | Notes |
|------|------|-------|
| Read pages | `download_confluence.py` | Converts macros, downloads attachments |
| Small text-only uploads (<10KB) | `upload_confluence_v2.py --dry-run` then explicit upload | Preview before write |
| Large documents (>10KB) | `upload_confluence_v2.py` | REST API, no size limits |
| Documents with images | `upload_confluence_v2.py` | Handles attachments automatically |
| Documents with native Confluence diagrams/macros | Storage-safe workflow | Verify the exact macro exists after upload |
| Git-to-Confluence sync | mark CLI | Best for CI/CD workflows |
| Download pages to Markdown | `download_confluence.py` | Converts macros, downloads attachments |

## REST Script Workflows

Use the REST API scripts for Confluence reads and writes. Always run `--dry-run` before writes:

```bash
# Upload large document
python3 scripts/upload_confluence_v2.py \
    document.md --id 780369923

# Dry-run preview
python3 scripts/upload_confluence_v2.py \
    document.md --id 780369923 --dry-run
```

Local Server/Data Center auth supports `CONFLUENCE_PERSONAL_TOKEN`, `CONFLUENCE_AUTH_TYPE=bearer`, and optional `CONFLUENCE_CONTEXT_PATH`. Do not print token values.

## Prerequisites

### Required

- Confluence credentials exported in the environment: `CONFLUENCE_URL`, `CONFLUENCE_USERNAME`, and `CONFLUENCE_PERSONAL_TOKEN` or `CONFLUENCE_API_TOKEN`

### Optional

- **mark CLI**: Git-to-Confluence sync (`brew install kovetskiy/mark/mark`)
- **Mermaid CLI**: Diagram rendering (`npm install -g @mermaid-js/mermaid-cli`)

## Core Workflows

### Download Pages to Markdown

```bash
# Single page
python3 scripts/download_confluence.py 123456789

# With child pages
python3 scripts/download_confluence.py --download-children 123456789

# Custom output directory
python3 scripts/download_confluence.py --output-dir ./docs 123456789
```

See [Downloading Guide](references/conversion_guide.md) for details.

### Upload Pages with Images and Native Diagrams

Do not replace native Confluence diagrams with image fallbacks unless explicitly requested. Markdown code fences do not become Confluence diagram macros by themselves.

For network/component diagrams, prefer the existing native draw.io macro pattern when the target Confluence instance supports it. A working storage example uses `ac:structured-macro ac:name="drawio"` with a `diagramName` parameter and a matching draw.io attachment (`application/vnd.jgraph.mxfile`). The PNG preview attachment belongs to the draw.io macro and is not a replacement `ac:image` workflow.

Native PlantUML component/class/state diagrams require server-side Graphviz `dot`. If Confluence renders `Dot executable does not exist`, `Cannot find Graphviz`, or suggests `@startuml\ntestdot\n@enduml`, the correct fix is Confluence/PlantUML plugin configuration or using the verified native draw.io macro pattern for component diagrams; do not silently replace the diagram with `ac:image`.

1. For ordinary document images, reference images with standard markdown: `![Description](./images/image.png)`.
2. For native diagrams, preserve or create the correct Confluence storage macro (`drawio`, `plantuml`, etc.) rather than raw Markdown fences.
3. Upload via REST API:

```bash
python3 scripts/upload_confluence_v2.py \
    document.md --id PAGE_ID
```

4. Read the page back and verify rendered storage contains the expected native macro (`drawio`, `plantuml`) or `ac:image` only for ordinary images.

Use native PlantUML storage only when the PlantUML macro is available on the target Confluence instance:

```xml
<ac:structured-macro ac:name="plantuml">
  <ac:plain-text-body><![CDATA[
@startuml
component "Frontend\n/app" as UI
component "Backend API\n/service" as API
UI --> API : request\nwith details
@enduml
  ]]></ac:plain-text-body>
</ac:structured-macro>
```

PlantUML labels and relationship descriptions must stay syntactically valid. Do not put physical newlines inside quoted labels or edge labels; use escaped `\n` instead. For example, write `component "Frontend\n/app" as UI`, not a two-line `component "Frontend` label. Write `UI --> API : request\nwith details`, not a multi-line edge description.

After uploading native macros, read the page back and verify the expected `ac:structured-macro ac:name="drawio"`, `ac:structured-macro ac:name="plantuml"`, or ordinary-image `ac:image` exists. Treat empty macros, literal `@startuml` text, unexpected `ac:macro ac:name="mermaid"` output, rendered PlantUML `Syntax Error`, or Graphviz/dot errors as a failed upload/rendering workflow.

See [Image Handling Best Practices](references/image_handling_best_practices.md) for details.

### Search, Create, and Update Pages

Use the REST scripts or the Confluence Python client from `scripts/confluence_auth.py`. Writes require an immediate dry-run/preview and explicit user confirmation.

### Sync from Git (mark CLI)

Add metadata to Markdown files:

```markdown
<!-- Space: DEV -->
<!-- Parent: Documentation -->
<!-- Title: API Guide -->

# API Guide
Content...
```

Sync to Confluence:

```bash
mark -f documentation.md
mark --dry-run -f documentation.md  # Preview first
```

See [mark Tool Guide](references/mark_tool_guide.md) for details.

### Convert Between Formats

See [Conversion Guide](references/conversion_guide.md) for the complete conversion matrix.

Quick reference:

| Markdown | Wiki Markup |
|----------|-------------|
| `# Heading` | `h1. Heading` |
| `**bold**` | `*bold*` |
| `*italic*` | `_italic_` |
| `` `code` `` | `{{code}}` |
| `[text](url)` | `[text\|url]` |

## Reference Documentation

Detailed guides in the `references/` directory:

| Guide | Purpose |
|-------|---------|
| [Wiki Markup Reference](references/wiki_markup_guide.md) | Complete syntax for Confluence Wiki Markup |
| [Conversion Guide](references/conversion_guide.md) | Markdown to Wiki Markup conversion rules |
| [Storage Format](references/confluence_storage_format.md) | Confluence XML storage format details |
| [Image Handling](references/image_handling_best_practices.md) | Workflows for images, Mermaid, PlantUML |
| [mark Tool Guide](references/mark_tool_guide.md) | Git-to-Confluence sync with mark CLI |
| [Troubleshooting](references/troubleshooting_guide.md) | Common errors and solutions |

## Utility Scripts

| Script | Purpose |
|--------|---------|
| `scripts/upload_confluence_v2.py` | Upload large documents with images |
| `scripts/download_confluence.py` | Download pages to Markdown |
| `scripts/convert_markdown_to_wiki.py` | Convert Markdown to Wiki Markup |
| `scripts/convert_wiki_to_markdown.py` | Convert Wiki Markup to Markdown |
| `scripts/render_mermaid.py` | Render Mermaid diagrams |

---

**Version**: 2.1.0 | **Last Updated**: 2025-01-21
