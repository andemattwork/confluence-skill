# Confluence Storage Format Reference

Understanding how Confluence stores and renders page content.

## Table of Contents

- [What is Storage Format](#what-is-storage-format)
- [Common Storage Format Elements](#common-storage-format-elements)
- [Confluence Macros](#confluence-macros)
- [Diagram Storage](#diagram-storage)
- [Converting Markdown to Storage Format](#converting-markdown-to-storage-format)
- [HTML Escaping Issues](#html-escaping-issues)
- [REST API Upload](#rest-api-upload)
- [Common Pitfalls](#common-pitfalls)

## What is Storage Format?

Confluence uses a custom XML-like format called "storage format" to store page content. It's similar to HTML but with special Confluence-specific macros.

**Key Point:** When uploading pages via REST API, content MUST be in 'storage' format, NOT HTML or Markdown.

## Common Storage Format Elements

### Text and Formatting

```xml
<p>Regular paragraph text</p>

<p><strong>Bold text</strong></p>

<p><em>Italic text</em></p>

<p><u>Underlined text</u></p>

<p><code>inline code</code></p>
```

### Headings

```xml
<h1>Heading 1</h1>
<h2>Heading 2</h2>
<h3>Heading 3</h3>
```

### Code Blocks

```xml
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">python</ac:parameter>
  <ac:plain-text-body><![CDATA[
def hello():
    print("Hello, World!")
  ]]></ac:plain-text-body>
</ac:structured-macro>
```

### Images

**Attached Image (the most common):**
```xml
<ac:image ac:align="center" ac:width="800">
  <ri:attachment ri:filename="diagram.png"/>
</ac:image>
```

**External Image:**
```xml
<ac:image>
  <ri:url ri:value="https://example.com/image.png"/>
</ac:image>
```

**With Alt Text:**
```xml
<ac:image ac:alt="Architecture Diagram">
  <ri:attachment ri:filename="architecture.png"/>
</ac:image>
```

### Tables

```xml
<table>
  <tbody>
    <tr>
      <th>Header 1</th>
      <th>Header 2</th>
    </tr>
    <tr>
      <td>Cell 1</td>
      <td>Cell 2</td>
    </tr>
  </tbody>
</table>
```

### Lists

**Unordered:**
```xml
<ul>
  <li>Item 1</li>
  <li>Item 2</li>
</ul>
```

**Ordered:**
```xml
<ol>
  <li>First item</li>
  <li>Second item</li>
</ol>
```

### Links

**External Link:**
```xml
<a href="https://example.com">Link Text</a>
```

**Internal Page Link:**
```xml
<ac:link>
  <ri:page ri:content-title="Page Title"/>
  <ac:plain-text-link-body><![CDATA[Link Text]]></ac:plain-text-link-body>
</ac:link>
```

## Common Macros

### Info/Warning/Note Panels

```xml
<ac:structured-macro ac:name="info">
  <ac:rich-text-body>
    <p>This is an info panel</p>
  </ac:rich-text-body>
</ac:structured-macro>

<ac:structured-macro ac:name="warning">
  <ac:rich-text-body>
    <p>This is a warning panel</p>
  </ac:rich-text-body>
</ac:structured-macro>

<ac:structured-macro ac:name="note">
  <ac:rich-text-body>
    <p>This is a note panel</p>
  </ac:rich-text-body>
</ac:structured-macro>
```

### Expand Macro (Collapsible Section)

```xml
<ac:structured-macro ac:name="expand">
  <ac:parameter ac:name="title">Click to expand</ac:parameter>
  <ac:rich-text-body>
    <p>Hidden content here</p>
  </ac:rich-text-body>
</ac:structured-macro>
```

### Table of Contents

```xml
<ac:structured-macro ac:name="toc">
  <ac:parameter ac:name="maxLevel">3</ac:parameter>
</ac:structured-macro>
```

## Diagram Storage

Use one of two explicit diagram workflows. Do not assume Markdown fences like <code>```mermaid</code> or <code>```plantuml</code> become Confluence diagram macros.

### Native draw.io diagrams

Use the native draw.io macro for network/component diagrams when that is the established Confluence pattern. A working page stores the diagram as a draw.io macro with a matching draw.io attachment (`application/vnd.jgraph.mxfile`) and often a PNG preview attachment managed by the macro.

```xml
<ac:structured-macro ac:name="drawio" ac:schema-version="1">
  <ac:parameter ac:name="border">true</ac:parameter>
  <ac:parameter ac:name="diagramName">Component Diagram</ac:parameter>
  <ac:parameter ac:name="simpleViewer">false</ac:parameter>
  <ac:parameter ac:name="links">auto</ac:parameter>
  <ac:parameter ac:name="tbstyle">top</ac:parameter>
  <ac:parameter ac:name="lbox">true</ac:parameter>
  <ac:parameter ac:name="diagramWidth">626</ac:parameter>
  <ac:parameter ac:name="height">311</ac:parameter>
  <ac:parameter ac:name="revision">1</ac:parameter>
</ac:structured-macro>
```

Do not convert an established native draw.io diagram into a plain `ac:image` replacement unless explicitly requested. Preserve the draw.io macro and its mxfile attachment so the diagram stays editable in Confluence.

### Native PlantUML macro

Use native PlantUML storage only when the target Confluence instance has a compatible PlantUML macro installed.

Component, class, state, and many other non-sequence PlantUML diagrams require Graphviz `dot` on the Confluence server. A native macro is not sufficient by itself. If the rendered page shows `Dot executable does not exist`, `Cannot find Graphviz`, or suggests `@startuml\ntestdot\n@enduml`, the server-side PlantUML plugin cannot find Graphviz. The correct fix is to use the established native draw.io macro pattern for component/network diagrams or have an administrator install Graphviz and configure the plugin's `dot` executable path. Do not silently replace native diagrams with `ac:image`.

```xml
<ac:structured-macro ac:name="plantuml">
  <ac:plain-text-body><![CDATA[
@startuml
title Component diagram
component "Frontend\n/app" as UI
component "Backend API\n/service" as API
database "Main DB\npostgres" as DB
UI --> API : command/query\nwith details
API --> DB : read/write
@enduml
  ]]></ac:plain-text-body>
</ac:structured-macro>
```

Component diagrams should show static responsibilities and integrations: UIs, services, databases, queues, and external systems. Sequence diagrams should show one runtime scenario over time with actors, participants, messages, and optional `alt/else/end` blocks.

Keep PlantUML labels on one physical source line. For multi-line visual labels, use escaped `\n` inside the label or edge text:

```plantuml
component "Web UI\n/app" as UI
database "Application DB\nprimary" as DB
UI --> DB : save entity\nwith domain invariants
```

Do not write physical newlines inside quoted labels or relationship descriptions:

```plantuml
' Wrong: breaks parsing in PlantUML macros
component "Web UI
/app" as UI
UI --> DB : save entity
with domain invariants
```

### Mermaid macro caution

Mermaid storage is not portable across Confluence installations. Only use an `ac:structured-macro` or `ac:macro` named `mermaid` after verifying the Mermaid macro exists on the target instance and that read-back storage preserves a non-empty macro body. If the plugin is missing or strips the body, render Mermaid to PNG/SVG and upload it as an image-backed diagram instead.

### Read-back verification

After uploading diagrams, fetch the page with `body.storage` and verify the expected storage shape:

- Native draw.io diagram: storage contains `ac:structured-macro ac:name="drawio"`, the expected `diagramName`, and the matching draw.io attachment remains present.
- Ordinary image: storage contains `<ac:image` and the expected `<ri:attachment ri:filename="..."/>`.
- Native PlantUML diagram: storage contains `ac:structured-macro ac:name="plantuml"` and a non-empty `ac:plain-text-body` with `@startuml` and `@enduml`.
- Mermaid macro: storage contains a non-empty supported Mermaid macro only if the target instance supports it.

Treat these as failures:

- Raw macro XML appears as escaped text such as `&lt;ac:image&gt;`.
- Diagram source appears as ordinary page text instead of macro body.
- Storage contains an empty macro such as a self-closing Mermaid macro.
- Read-back storage does not contain the expected `drawio`, `plantuml`, `ac:image`, or attachment filename.
- Rendered PlantUML output shows `Syntax Error`, often caused by physical newlines inside quoted labels or edge labels instead of escaped `\n`.
- Rendered PlantUML output shows `Dot executable does not exist` or `Cannot find Graphviz`; use the established native draw.io macro pattern for component/network diagrams or fix server-side Graphviz `dot` configuration.

## Converting Markdown to Storage Format

### Using md2cf Library

The `md2cf` library provides `ConfluenceRenderer` which converts Markdown to storage format:

```python
from md2cf.confluence_renderer import ConfluenceRenderer
import mistune

# Create renderer
renderer = ConfluenceRenderer()

# Parse markdown
parser = mistune.Markdown(renderer=renderer)
storage_html = parser(markdown_content)

# Get image paths (if any)
attachments = renderer.attachments  # List of image file paths
```

**How md2cf handles markdown images:**
- Detects: `![Description](./path/to/image.png)`
- Converts to: `<ac:image ac:alt="Description"><ri:attachment ri:filename="image.png"/></ac:image>`
- Adds path to `renderer.attachments` list for uploading

## HTML Escaping Issue (CRITICAL)

**Problem:** If you put raw Confluence XML in markdown, it gets HTML-escaped:

```markdown
# Bad Approach (DON'T DO THIS)

<ac:image><ri:attachment ri:filename="diagram.png"/></ac:image>
```

**Result:** Text appears literally on page:
```
&lt;ac:image&gt;&lt;ri:attachment ri:filename="diagram.png"/&gt;&lt;/ac:image&gt;
```

**Solution:** Use markdown image syntax instead:
```markdown
![Diagram](./diagrams/diagram.png)
```

md2cf will convert it to proper storage format automatically.

## REST API Upload Requirements

When uploading via Confluence REST API (`update_page` or `create_page`):

```python
result = confluence.update_page(
    page_id=page_id,
    title=title,
    body=storage_html,           # Must be storage format
    representation='storage',     # CRITICAL: Specify 'storage'
    minor_edit=False,
    version_comment="Updated via API"
)
```

**Key Requirements:**
1. `body` parameter must contain storage format XML (not HTML or markdown)
2. `representation='storage'` must be specified
3. For updates, must increment version number correctly

## Image Attachment Workflow

**Complete workflow for uploading pages with images:**

1. **Convert diagrams to images** (if using Mermaid/PlantUML):
   ```bash
   mmdc -i diagram.mmd -o diagram.png
   plantuml diagram.puml -tpng
   ```

2. **Reference images in markdown** using standard syntax:
   ```markdown
   ![Architecture](./diagrams/architecture.png)
   ```

3. **Convert markdown to storage format** using md2cf:
   ```python
   renderer = ConfluenceRenderer()
   parser = mistune.Markdown(renderer=renderer)
   storage_html = parser(markdown_content)
   attachments = renderer.attachments
   ```

4. **Upload page content** via REST API:
   ```python
   confluence.update_page(
       page_id=page_id,
       title=title,
       body=storage_html,
       representation='storage'
   )
   ```

5. **Upload image attachments**:
   ```python
   for image_path in attachments:
       confluence.attach_file(
           filename=image_path,
           name=os.path.basename(image_path),
           content_type='image/png',
           page_id=page_id
       )
   ```

## Common Pitfalls

### ❌ Using MCP for Large Pages

**Problem:** MCP has size limits and cannot upload large documents.

**Solution:** Use REST API directly via `atlassian-python-api` library.

### ❌ Using MermaidConfluenceRenderer for Regular Images

**Problem:** `MermaidConfluenceRenderer` overwrites parent's attachment handling, breaking regular markdown images.

**Solution:** Use base `ConfluenceRenderer` for regular images. Convert Mermaid/PlantUML to PNG/SVG first, then reference as regular images.

### ❌ Putting Raw XML in Markdown

**Problem:** Raw XML gets HTML-escaped and appears as literal text.

**Solution:** Always use markdown syntax; let md2cf convert to storage format.

### ❌ Assuming Markdown Diagram Fences Become Macros

**Problem:** Markdown fences such as <code>```mermaid</code> and <code>```plantuml</code> usually become code blocks or text. They do not automatically become Confluence diagram macros.

**Solution:** Use a storage-safe native macro workflow and verify read-back storage after upload. For network/component diagrams, prefer the established draw.io macro pattern where available. Do not silently replace native diagrams with plain image attachments unless explicitly requested.

### ❌ Forgetting `representation='storage'`

**Problem:** API call fails or content doesn't render correctly.

**Solution:** Always specify `representation='storage'` in REST API calls.

## References

- [Confluence Storage Format Documentation](https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html)
- [md2cf GitHub Repository](https://github.com/iamjackg/md2cf)
- [Atlassian Python API](https://atlassian-python-api.readthedocs.io/)
