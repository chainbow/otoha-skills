# Writing slides

## Before the first slide

Settle these before writing, from the request; ask the user only what you cannot work out and would change the result (who the audience is, how long the talk is, a brand's colours). With nobody to answer, choose the usual and say what you assumed in your last message.

- **The point**: one sentence for what the audience should remember or decide.
- **The outline**: a title for every slide, each stating its point, in order; 8 to 12 slides for a 10 minute talk, about one slide per minute. A cover first, a closing last, a section slide to open each part when there are three or more parts.
- **The look**: preserve the existing file's style unless the user asks for a new one. Translate a requested style into the PPT theme (`../SKILL.md`).
- **The language**: the user's. Chinese in, Chinese out; keep names, units and terms spelled the same way on every slide.

## One slide

- **The title says the point**: "预约量持续上升", not "预约量". A reader who reads only the titles should get the story.
- **One idea per slide.** If a slide needs "and also", make two.
- **At most 5 bullets, 3 reads best.** Each is a short line, not a paragraph: under about 20 Chinese characters or 12 English words, no full stop.
- **Numbers belong in a `stats` slide or a chart**, not in a sentence.
- **Lines that are parallel are phrased in parallel** (all start with a verb, or all are nouns).
- **Say it once.** The title and the first bullet should not repeat each other.

## Numbers and sources

Never make up facts, figures or quotes. Use what the user gave, or what you found and can name. When the user gave none and a chart or a number is needed to make the slide work, use plausible example values, label the chart's `caption` "示例数据" (or "Sample data"), and say so in your last message so the user can replace them. A chart with real data names its source and date in the `caption`.

## Speaker notes

Keep existing speaker notes. When adding a presentation script, use the slide object's `notes` field: two or three sentences about what to say, rather than a copy of the slide.

## Changing an existing PPT

- Inspect the current file with `outline --file` first; do not assume an old source outline still matches user edits.
- For a single page's words, layout or chart, replace that page only with `edit --slide`; preserve all other pages.
- For a new look, apply a theme directly to the file without rebuilding its content.
- Feedback by position ("第 3 页"): use the order in the current PPT file, starting at 1.
- Preserve facts, slide count, media and editability unless the user asks to change them. If a request conflicts with those limits, explain the specific tradeoff.
