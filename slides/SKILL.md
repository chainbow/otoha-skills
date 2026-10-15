---
name: slides
description: Create a presentation with content, design and a web preview, then export an editable PowerPoint file through pptx when requested. Use for new PPT, presentations, decks, slides, 新建 PPT、演示稿、幻灯片、スライド、プレゼン, and changes to a web presentation. A request to create a PPT starts here, previews the deck and continues to PPT export without asking the user to choose a format. Existing .ppt/.pptx files and changes after export go to pptx.
allowed-tools: skill_read skill_copy skill_run workspace_read workspace_write page_check file_open
hands-off-to: pptx
version: 1.1.0
---
# Slides

A deck is a folder. `deck.json` holds the title, the order of the slides and the look; each slide is its own file in `slides/`; this skill's script puts them together as `index.html`, which the app shows beside the conversation, presents full screen and exports to PDF. Changing one slide rewrites only that slide's file. Do not write styles or scripts of your own, and do not load anything from the internet.

```
launch-deck/
  deck.json            title, language, look, the slides in order
  slides/cover.html    one file per slide, named for what it says
  slides/why-now.html
  images/              pictures, if any
  lib/                 deck.css and deck.js, copied from this skill
  index.html           made by the script; never edit it
```

For a new presentation, own the content and design here. When the user asks for a PPT, make and check the web preview first, then continue to the editable PowerPoint export in the same task; do not ask whether they want web, PDF or PPT. If they ask only for a presentation, deliver the preview; an explicit later “导出 PPT” / “Export PPT” / “PPT に書き出して” continues the export immediately. Use PDF as an alternative when an exact visual copy is needed or editable export cannot preserve a necessary feature.

For an existing .ppt/.pptx file, or a presentation already exported to PowerPoint, read the pptx skill and edit that file as the source of truth. Do not replace it with a newly built deck. See `references/powerpoint.md`.

Name the deck's folder short and concrete, in the language of the request, with no generic parent folder: an English request gets `launch-deck`, a Chinese request gets `发布会演示`. A new folder per deck; never overwrite another deck.

## Make a deck

1. **Plan.** Settle the point, the outline (a title that states the point for every slide) and the look before writing. `references/writing-slides.md` has how; read it first. Follow a design in the project or a brand the user named: `references/design-tokens.md`.
2. **Set up.** Copy this skill's `assets` folder into the deck's folder as `lib` with skill_copy (for example to `launch-deck/lib`).
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

   `id` says what the slide is about, in lowercase English words with hyphens, never a number. `theme` is optional (colours and font; see `references/design-tokens.md`); `"mode": "dark"` gives dark slides and is carried into the PowerPoint theme along with the effective colours and font. `section` on a slide names the part of the talk it begins; it is shown small at the foot of that slide and the ones after it.
4. **Write each slide** to `slides/<id>.html` with workspace_write. One `<section class="slide …" id="<id>">` per file, every file, with the `id` there and equal to the one in `deck.json` (the commonest slip is a slide without it, such as a two-column one); the layouts, with their HTML, are in `references/layouts.md`: read it before writing. Every piece of text carries a `data-edit="name"` that is unique in its slide, so the user can retype it in the preview.
5. **Build.** Call skill_run with skill `slides`, script `scripts/build.mjs` (the whole path, `scripts/` included) and arguments `["build", "launch-deck"]`. It checks the deck and writes `index.html`. It lists every problem with the slide's id and the line; fix each in its slide file and run it again. Warnings (more than 5 bullets, no title, a pale accent) are worth fixing but do not stop the build.
6. **Look at it.** Run page_check on `launch-deck/index.html`, fix what it reports (errors, text running off a slide), and build again after each fix.
7. **Deliver.** If the request includes a PPT, continue with the PowerPoint export below before finishing. Tell the user in a few plain lines what was made, where to preview it and where the PPT file is, the assumptions you took (audience, length, any example numbers that need real ones), and any simplified pages or font substitutions. The preview also supports full-screen presentation and PDF export. Do not claim PowerPoint/Keynote viewing was verified unless it was actually checked.

Charts: `references/charts.md`.

## Change one slide

First check whether a PPT was already exported or supplied. If so, use pptx to read and change the current PPT file, preserving edits made in PowerPoint/Keynote. For a web-only deck, the user's feedback names a slide ("第 3 页", "the pricing slide"). Find its id in the `slides` list of `deck.json`, read only that slide's file, change it with workspace_write in edit mode (oldText is the exact passage from the file, newText what replaces it), and build again. Do not touch the other slide files, `deck.json` or `index.html` unless the change needs them: adding, removing or moving a slide changes the list in `deck.json`; a new look changes `theme`. Tell the user which slide changed.

## Export

- **PDF**: the preview has the export button; it is an exact copy of the slides as shown, one per page. Nothing to run.
- **PowerPoint (editable)**: build the deck, call skill_run with skill `slides`, script `scripts/to-pptx-outline.mjs` and the deck folder as the only argument, then follow the pptx skill with the outline it wrote. If the project does not have the pptx skill yet, find it with skill_find and add it with skill_add (this skill hands off to it, and asking for it is enough; the user is asked only if adding it needs their yes), read it with skill_read, and carry on; do not stop to ask the user to add it. The outline carries the deck's effective theme and mapped layouts; read and report conversion notes instead of silently changing the design. Later edits use the PPT file as the source of truth. `references/powerpoint.md` has the steps; the shared contract for future presentation skills is `pptx`'s `references/presentation-handoff.md`.

## When something fails

The script exits with a message naming the slide and what to change. Fix that slide's file, not `index.html`, and run the script again. If `lib` is missing the message says to copy the assets; if the script cannot run at all, tell the user plainly that the deck could not be put together here and why, and do not write `index.html` by hand.
