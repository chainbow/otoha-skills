# Preview and editable PowerPoint delivery

A new presentation starts with content, design and the web preview in this skill. A request for a PPT includes the editable file: check the preview and continue exporting in the same task, without asking the user to choose a format. An explicit later export request continues these steps immediately.

## Export the checked deck

1. Build the deck (`scripts/build.mjs`) and check its preview with page_check.
2. Run this skill's `scripts/to-pptx-outline.mjs` with the deck folder as argument. It writes `<deck folder>/outline.json`, including the effective theme, supported layouts and speaker notes. Read every `NOTE` in the result: these identify simplified pages and font substitutions. Use the slide order to name those pages in the delivery message.
3. Read the pptx skill with skill_read. If missing from the project, find it with skill_find and add it with skill_add, then continue. This skill declares the handoff; do not stop to ask the user to install it manually.
4. Run pptx's `scripts/deck.py` with `build --spec <deck folder>/outline.json --out <deck folder>/<name>.pptx`.
5. Deliver the preview and PPT file paths together. Explain any simplified pages or substituted fonts in everyday words. The export keeps editable text and native charts, using the preview's effective colours, light/dark mode and supported font choice. It maps the layout into PowerPoint elements; it is not a pixel-for-pixel copy. Only claim actual viewing in PowerPoint or Keynote when checked there.

The reusable outline and theme contract, including layout mapping and conversion notes, lives in pptx's `references/presentation-handoff.md`. Future presentation-making skills should use that contract too.

## Changes after export

The current PPT file becomes the source of truth: the user may already have edited it in PowerPoint or Keynote. For “再改一下第 2 页”, read the current file with pptx's `outline --file`, write one replacement slide object and use `edit --file <deck>.pptx --slide 2 --spec <slide>.json`. Preserve the other pages and the saved PPT theme. Do not rebuild the entire PPT from the web deck or an old outline.

If a user specifically asks to update the web version too, update its matching slide separately. If converting that updated page for the PPT, take only the matching slide object from the new outline and replace just that PPT page; never overwrite the rest. Changes in PowerPoint are not automatically synchronized back to the web files.

For a global style change, let pptx apply a theme directly to the existing file, without reconstructing the content.

## PDF alternative

The preview's PDF export produces one page per slide, preserving what the preview shows. Offer it when the user needs a visual copy or when a necessary effect cannot remain editable in PPT; explain the limitation before treating PDF as a substitute for a requested PPT. It does not replace the editable export by default.

Mixed pages may have body text alongside a chart, image, key figures or comparison. The current converter keeps the editable layout and moves additional body text into speaker notes, with a conversion note naming the page. Tell the user which pages need that text reviewed before presenting.
