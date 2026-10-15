# Handoff from a presentation-making skill

This is the shared contract for any skill that creates presentation content, design and a preview. The making skill keeps those responsibilities. This pptx skill owns editable PowerPoint export and changes to existing PPT files. Do not merge the skills or ask the user to choose between them.

## Route by the user's task

- A new presentation, including “新建一个 PPT”, “Create a PPT” or “PPT を新規作成”: use a presentation-making skill first, currently slides. Build and check its web preview. When the request includes PPT, continue exporting in the same task; do not wait for a separate format choice or export confirmation unless the user explicitly requested a review first.
- “导出 PPT”, “Export PPT” or “PPT に書き出して” for a finished presentation: use its content and design to export now.
- An uploaded or already exported PPT: inspect and edit the current file directly here. A page change replaces only that page; a global style change applies a theme without rebuilding its content. Preserve user edits in the other pages.

The making skill declares `hands-off-to: pptx` in its front matter. Read this skill with skill_read; if it is missing from the project, find it with skill_find and add it with skill_add, then continue. Do not ask the user to perform the handoff manually.

## Outline

Write JSON in the project, with ordered `slides`, a `title` and the effective `theme`. Every slide has `layout` and `title`; keep `notes` when provided. File paths for images and videos are relative to the project, not the skill bundle. Keep the original content files and preview alongside the export.

```json
{
  "title": "A smaller first step",
  "theme": {
    "mode": "light",
    "background": "#F7F5EF",
    "text": "#28302F",
    "accent": "#3C706B",
    "muted": "#65716F",
    "line": "#DADFD9",
    "soft": "#E8EFEB",
    "chart": ["#3C706B", "#B48C5A"],
    "headingFont": "Hiragino Sans",
    "bodyFont": "Hiragino Sans",
    "density": "airy"
  },
  "slides": [
    {"layout": "cover", "title": "A smaller first step", "subtitle": "Pilot proposal"},
    {"layout": "bullets", "title": "Start with one category", "bullets": ["Measure the baseline", "Run a small pilot"], "notes": "Explain how the pilot will be measured."}
  ]
}
```

Then run pptx's `scripts/deck.py` with `build --spec <outline>.json --out <name>.pptx`. Pass the theme through; do not let the default replace a design the user has already seen.

## Carry the effective theme

Resolve the preview's defaults as well as explicit values, so an omitted theme in a source deck still has a complete export theme. Colours use six hexadecimal digits with an optional `#`. `mode` is `light` or `dark`; carry dark-mode background and foreground values together. Dark mode must remain readable after export.

For the current slides skill, `scripts/to-pptx-outline.mjs` resolves the effective web theme and writes these mappings:

| Web theme | PPT outline theme |
| --- | --- |
| `accent` | `accent` |
| `paper` | `background` |
| `ink` | `text` |
| `muted` | `muted` |
| `line` | `line` |
| `accentSoft` | `soft` |
| `chart` | `chart` |
| `mode`, or the effective default | `mode` |
| `font` stack | `headingFont` and `bodyFont` |

Use supported font names listed in `SKILL.md`. For a CSS stack, choose the first supported face; otherwise choose its generic `sans-serif`, `serif` or `monospace` family and record the substitution. Fonts are not downloaded or embedded. Do not promise identical letter shapes on a computer without the same installed fonts. `density` is optional (`compact`, `normal` or `airy`); it adjusts content spacing and is not a substitute for the source layout.

Future making skills may use a different theme schema, but must map their effective colours, heading/body font choice and light/dark mode to these fields before handoff. Keep conversion notes outside the outline or in a companion report; do not invent unsupported outline fields.

## Map layouts to editable elements

| Presentation content | PPT `layout` | Fields |
| --- | --- | --- |
| Opening / cover | `cover` | `title`, optional `subtitle` |
| Section divider | `section` | `title`, optional `subtitle` |
| Closing | `closing` | `title`, optional `subtitle` |
| Bullet list | `bullets` | `title`, `bullets` |
| Two columns / comparison | `two-column` | `title`, `left` and `right`, each with `heading` and `bullets` |
| Key figures | `stats` | `title`, `stats` entries with `value` and `label` |
| Data chart | `chart` | `title`, `chart` data, optional `caption` |
| Image | `image` | `title`, project-relative `image`, optional `caption` |
| Video | `video` | `title`, project-relative `video`, optional `poster`, `aspectRatio`, `caption` |
| Quotation | `quote` | quoted text as `title`, source as `subtitle` |

Read the field limits and chart types in `SKILL.md`. Preserve ordering, facts, captions, source information and speaker notes. The current slides converter maps its cover, section, closing, bullet, two-column, stats, chart, image and quote layouts to these counterparts. A future making skill can supply any supported layout, including video.

A source page without a matching layout needs a deliberate fallback, usually `bullets`. Preserve the meaning and all essential content; never silently drop a diagram, image or data. Emit a conversion note naming the source slide ID or page number, the replacement layout and what was simplified. If essential visual content cannot be represented as editable elements, explain the limitation and offer the preview/PDF as an additional visual copy. A screenshot alone does not satisfy an editable PPT request.

Review the export notes and tell the user which pages were simplified and which fonts changed. Keep the note concrete, for example “Page 4's timeline became a bullet list; dates and order are preserved.” The editable PPT follows the source theme and layout mapping; exact geometry and browser-only effects can differ.

## Continue editing the delivered file

After export, the current PPT is authoritative. Inspect it with `outline --file <name>.pptx` before editing. For a page change, write one slide object and run `edit --file <name>.pptx --slide <number> --spec <slide>.json`. The saved PPT theme is reused. Do not rebuild the full file from the old preview or outline. For a global style change, pass a spec containing only `theme` to `edit` without `--slide`.

Inspect the produced file for slide count, titles, theme and editable content. Record whether actual viewing in PowerPoint/Keynote was checked; if those apps could not be used, say that visual viewing remains pending. A successful export is not proof of visual layout or media playback in those apps.

Mixed pages may have body text alongside a chart, image, key figures or comparison. The current converter keeps the editable layout and moves additional body text into speaker notes, with a conversion note naming the page. Tell the user which pages need that text reviewed before presenting.
