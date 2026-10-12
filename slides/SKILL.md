---
name: slides
description: Make a presentation as slides on a web page, one file per slide, with a consistent look, charts and speaker-ready layouts, that the app previews, presents full screen and exports to PDF; one slide can be changed without touching the others. Use when the user asks for slides, a deck, a presentation or 演示稿, or to change one slide of such a deck. For an editable PowerPoint file, hand the same content to the pptx skill.
allowed-tools: skill_read skill_copy skill_run workspace_read workspace_write page_check file_open
---
# Slides

A deck is a folder. `deck.json` holds the title, the order of the slides and the look; each slide is its own file in `slides/`; this skill's script puts them together as `index.html`, which the app shows beside the conversation, presents full screen and exports to PDF. Changing one slide rewrites only that slide's file. Do not write styles or scripts of your own, and do not load anything from the internet.

```
发布会演示/
  deck.json            title, language, look, the slides in order
  slides/cover.html    one file per slide, named for what it says
  slides/why-now.html
  images/              pictures, if any
  lib/                 deck.css and deck.js, copied from this skill
  index.html           made by the script; never edit it
```

## Make a deck

1. **Plan.** Settle the point, the outline (a title that states the point for every slide) and the look before writing. `references/writing-slides.md` has how; read it first. Follow a design in the project or a brand the user named: `references/design-tokens.md`.
2. **Set up.** Copy this skill's `assets` folder into the deck's folder as `lib` with skill_copy (for example to `发布会演示/lib`).
3. **Write `deck.json`** with workspace_write:

   ```json
   {
     "title": "让家，更懂你",
     "lang": "zh",
     "theme": {"accent": "#0a7d5a"},
     "slides": [
       {"id": "cover", "file": "slides/cover.html"},
       {"id": "why-now", "file": "slides/why-now.html", "section": "背景"},
       {"id": "booking-growth", "file": "slides/booking-growth.html"}
     ]
   }
   ```

   `id` says what the slide is about, in lowercase English words with hyphens, never a number. `theme` is optional (colours and font; see `references/design-tokens.md`); `"mode": "dark"` gives dark slides, but not when the same content also goes to PowerPoint. `section` on a slide names the part of the talk it begins; it is shown small at the foot of that slide and the ones after it.
4. **Write each slide** to `slides/<id>.html` with workspace_write. One `<section class="slide …" id="<id>">` per file; the layouts, with their HTML, are in `references/layouts.md`: read it before writing. Every piece of text carries a `data-edit="name"` that is unique in its slide, so the user can retype it in the preview.
5. **Build.** Call skill_run with skill `slides`, script `scripts/build.mjs` (the whole path, `scripts/` included) and arguments `["build", "发布会演示"]`. It checks the deck and writes `index.html`. It lists every problem with the slide's id and the line; fix each in its slide file and run it again. Warnings (more than 5 bullets, no title, a pale accent) are worth fixing but do not stop the build.
6. **Look at it.** Run page_check on `发布会演示/index.html`, fix what it reports (errors, text running off a slide), and build again after each fix.
7. **Tell the user** in a few plain lines what was made, the assumptions you took (audience, length, any example numbers that need real ones), and that they can present it full screen and export it as PDF from the preview.

Charts: `references/charts.md`.

## Change one slide

The user's feedback names a slide ("第 3 页", "the pricing slide"). Find its id in the `slides` list of `deck.json`, read only that slide's file, change it with workspace_write in edit mode (oldText is the exact passage from the file, newText what replaces it), and build again. Do not touch the other slide files, `deck.json` or `index.html` unless the change needs them: adding, removing or moving a slide changes the list in `deck.json`; a new look changes `theme`. Tell the user which slide changed.

## Export

- **PDF**: the preview has the export button; it is an exact copy of the slides as shown, one per page. Nothing to run.
- **PowerPoint (editable)**: build the deck, call skill_run with skill `slides`, script `scripts/to-pptx-outline.mjs` and the deck folder as the only argument, then follow the pptx skill with the outline it wrote. The PowerPoint keeps the content but has the pptx skill's own look, and later edits in PowerPoint do not come back. `references/powerpoint.md` has the steps and how the two differ; say it in a sentence when the user asks for both.

## When something fails

The script exits with a message naming the slide and what to change. Fix that slide's file, not `index.html`, and run the script again. If `lib` is missing the message says to copy the assets; if the script cannot run at all, tell the user plainly that the deck could not be put together here and why, and do not write `index.html` by hand.
