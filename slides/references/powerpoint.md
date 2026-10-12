# Two ways out: PDF and PowerPoint

| | Slides as a web page (this skill) | PowerPoint file (`pptx` skill) |
| --- | --- | --- |
| Opens in | the app's preview; full-screen present with the arrow keys | PowerPoint, Keynote |
| Handed on as | PDF, exact copy of what the preview shows | a .pptx file the recipient can edit |
| Look | this skill's layouts and the deck's colours and font | the pptx skill's fixed look: white slides, dark text, one indigo accent |
| Charts | drawn from the data | native charts that stay editable |
| Retyping | in the preview, text by text | in PowerPoint |
| Changes later | only the slide that changed is rewritten here | edits made in PowerPoint do not come back here |

Offer the PDF when someone only needs to read or print it, and the PowerPoint file when the recipient must edit or present it from their own tools. They can have both from the same content.

## PDF

The preview has the export button for PDF and the full-screen present button. Nothing to run. The PDF has one slide per page, as shown.

## PowerPoint from the same slides

1. Build the deck first, so the check has passed (`scripts/build.mjs`).
2. Run this skill's `scripts/to-pptx-outline.mjs` with the deck folder as argument. It writes `<deck folder>/outline.json` for the pptx skill: cover, section, closing, bullets, two columns, stats, chart, image and quote slides map one to one; speaker notes come along. A slide that fits none of them is simplified to bullets, and the script says which, so look at those after.
3. Read the pptx skill (skill_read `pptx`) and run its `scripts/deck.py` with `build --spec <deck folder>/outline.json --out <deck folder>/<name>.pptx`.
4. Tell the user the file's name, and that its look is the PowerPoint skill's own (not the deck's colours and font), and that edits made in PowerPoint stay there.

## One slide changed afterwards

Change the slide's file here and build again. If the PowerPoint file already exists and the user may have edited it, do not rebuild it: run the outline script, take that slide's object from `outline.json`, write it to its own file and let the pptx skill's `edit --slide <number>` replace just that slide; the others stay as they are.
