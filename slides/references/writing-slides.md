# Writing slides

## Before the first slide

Settle these before writing, from the request; ask the user only what you cannot work out and would change the result (who the audience is, how long the talk is, a brand's colours). With nobody to answer, choose the usual and say what you assumed in your last message.

- **The point**: one sentence for what the audience should remember or decide.
- **The outline**: a title for every slide, each stating its point, in order; 8 to 12 slides for a 10 minute talk, about one slide per minute. A cover first, a closing last, a section slide to open each part when there are three or more parts.
- **The look**: the built-in look unless the user gave a brand or a design exists in the project (`design-tokens.md`).
- **The language**: the user's. Chinese in, Chinese out; keep names, units and terms spelled the same way on every slide.

## Naming the slides

The `id` is what the slide is about, in lowercase English words with hyphens: `why-now`, `booking-growth`, `price-plans`. Never a number (`slide-3`): slides get added and moved, and a number would then lie. The file is `slides/<id>.html`. Rename a slide's id only if its meaning changed, in `deck.json`, in the file name and in the `<section id>` together.

## One slide

- **The title says the point**: "预约量持续上升", not "预约量". A reader who reads only the titles should get the story.
- **One idea per slide.** If a slide needs "and also", make two.
- **At most 5 bullets, 3 reads best.** Each is a short line, not a paragraph: under about 20 Chinese characters or 12 English words, no full stop.
- **Numbers belong in a `stats` slide or a chart**, not in a sentence.
- **Lines that are parallel are phrased in parallel** (all start with a verb, or all are nouns).
- **Say it once.** The title and the first bullet should not repeat each other.

## Numbers and sources

Never make up facts, figures or quotes. Use what the user gave, or what you found and can name. When the user gave none and a chart or a number is needed to make the slide work, use plausible example values, label the chart's `figcaption` "示例数据" (or "Sample data"), and say so in your last message so the user can replace them. A chart with real data names its source and date in the `figcaption`.

## Text that can be retyped

Every text element carries `data-edit` (see `layouts.md`). Names describe the role (`title`, `lead`, `point-2`, `caption`), not the wording. The check refuses a slide where a name repeats or text has no name, and tells you the line.

## Speaker notes

Add an `<aside class="notes" data-edit="notes">` when the user will present it or asks for a script: two or three sentences saying what to say, not a copy of the slide.

## Changing a deck

- A change to one slide's words, layout or chart: read that slide's file with workspace_read, change it with workspace_write in edit mode (oldText is the exact passage, newText what replaces it), and build again. Nothing else is touched, and `deck.json` stays as it is.
- A slide added, removed or moved: write or delete its file and change the list in `deck.json`.
- A change to the look: `theme` in `deck.json`.
- Feedback by position ("第 3 页"): find the id at that position in the `slides` list of `deck.json`; do not guess from the files' order.
- Never change `index.html` by hand: the next build replaces it.
