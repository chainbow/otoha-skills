---
name: pptx
description: Export an editable PowerPoint from a finished presentation, or change a given .pptx: text, links, animations, media, transitions, slide order. PPT、PPTX、Keynote、动画、パワーポイント。New decks first use a presentation-making skill for content, design and preview, then return to export without a format question.
metadata:
  otoha-title-zh: PPT 文件
  otoha-title-en: PowerPoint files
  otoha-title-ja: PowerPoint ファイル
  otoha-summary-zh: 把做好的演示稿导出成可以编辑的 PPT，或修改你给的 PPT。
  otoha-summary-en: "Turns a finished presentation into an editable PowerPoint file, or changes one you give."
  otoha-summary-ja: 仕上がったプレゼンを編集できる PowerPoint に書き出したり、渡されたファイルを直したりします。
allowed-tools: skill_read skill_run workspace_read workspace_write file_open
hands-off-to: slides
version: 1.2.1
---
# PPT files

Use this skill for the file: export a finished presentation as an editable PPT, or edit a file the user already has. New presentation requests first use a presentation-making skill, currently slides, for content, design and a checked web preview. Read that skill and continue; if missing, use skill_find and skill_add. A request for a new PPT includes export after preview, without a format question. Return here with its outline. Keep the two skills separate; the shared contract for any presentation-making skill is `references/presentation-handoff.md`.

For an uploaded or previously exported PPT, work directly on the current file. The script edits .pptx; if a legacy .ppt cannot be read, explain that it needs conversion to .pptx and do not pretend it was edited or silently recreate its contents. Its contents, including user changes made in PowerPoint or Keynote, take precedence over an older web deck or outline. Read `references/writing-slides.md` when changing the story, titles or content; do not route an existing file through a new-deck workflow. Formatting, links, animations, media, transitions and slide order change with `change`; a new look for the whole deck with a theme-only `edit`; one page's content with `edit --slide`. Each is described below.

Decks are built from an outline by `scripts/deck.py`, run with skill_run. Without a theme, the default look is white slides, dark text and an indigo accent. Native text and charts stay editable. When the user asks for a different style, or another skill supplies design rules, translate those rules into the outline’s theme instead of refusing or keeping the default. The style skill supplies rules; this skill applies them to the file. Preserve facts, slide count and editability.

## Export a finished presentation

Read `references/presentation-handoff.md`. Keep the theme and conversion notes supplied by the presentation-making skill. Do not discard the theme or invent a second design.

1. Use its outline, or write the agreed content and design as an outline with workspace_write, as JSON, for example `.tmp/发布会/outline.json`. Working files such as this one go in the project's `.tmp/` folder, never beside the result: the folder the user gets holds only what they asked for.

   ```json
   {"title": "让家，更懂你", "slides": [
     {"layout": "cover", "title": "让家，更懂你", "subtitle": "2026 秋季新品发布会"},
     {"layout": "bullets", "title": "为什么是现在", "bullets": ["…", "…", "…"], "notes": "讲稿"}
   ]}
   ```

2. Run `scripts/deck.py` with the arguments `build --spec .tmp/发布会/outline.json --out 发布会/发布会.pptx`.
3. Tell the user the file's name and any simplified pages or font substitutions from the handoff. If they want to see it, open it with file_open when that is authorized. Do not claim PowerPoint/Keynote viewing was checked unless it was.

## Apply a style

Use an optional `theme` next to `title` and `slides` in the outline. For Japanese minimal design with off-white, charcoal and soft teal:

```json
{"theme": {"background": "#F7F5EF", "text": "#28302F", "accent": "#3C706B", "headingFont": "Hiragino Sans", "bodyFont": "sans-serif", "density": "airy"}, "slides": [{"layout": "cover", "title": "减少食品浪费", "subtitle": "从一个品类开始"}]}
```

- `mode` is `light` or `dark`; when omitted, existing theme behaviour is preserved. Choose matching foreground and background colours. `muted`, `line`, `soft` and a `chart` palette (up to five colours) can carry the preview's secondary text, dividers, tinted panels and chart series.
- Colours are exactly six hexadecimal digits, optionally prefixed by `#`. With an explicit `mode`, cover pages use the accent background and quote pages use the soft tint; other pages use the chosen background. Cover text uses white or dark ink for readability. Themes without `mode` keep the previous uniform-background behaviour. Shape fills, accents, chart series and text follow the palette; pictures, movie bytes and supplied posters retain their original colours.
- `headingFont` and `bodyFont` each name a supported face: Helvetica Neue, Arial, Aptos, Calibri, Georgia, Times New Roman, Courier New, PingFang SC, Hiragino Sans, Yu Gothic, Noto Sans CJK SC, Noto Sans JP or Noto Serif JP. Prefer faces available on the user's computer. If a guide names another font, use `sans-serif`, `serif` or `monospace` instead; these select Arial/PingFang SC, Georgia/Songti SC or Courier New/PingFang SC. East Asian text always has an explicit CJK face; fonts are not downloaded or embedded.
- `density` is `compact`, `normal` or `airy`. Airy gives more outer whitespace by fitting content into a smaller footprint; compact uses a larger footprint. Text size and point spacing scale with the footprint; media keep their aspect ratios. Omitted fields keep the default values. Omitting theme altogether preserves the old file and style exactly.

For an existing deck, do **not** reconstruct its outline just to change style: that could lose user edits or media. Write a file such as `.tmp/发布会/style.json` containing only `{"theme": {...}}`, then run `scripts/deck.py` with `edit --file 发布会/发布会.pptx --spec .tmp/发布会/style.json`, without `--slide`. This applies the theme to every slide while keeping text, tables, charts, speaker notes, images and video. The deck remembers the theme, so later single-slide replacements use it too. Applying the same theme again does not keep shrinking or enlarging the content. To also replace one slide and theme the whole deck, include `theme` in that slide object and pass `--slide`.

This changes the existing file. If the user asks to keep the original, use `edit --file 发布会/发布会.pptx --spec .tmp/发布会/style.json --out 发布会/日式简约.pptx` to save the changed copy, without a separate copy command. Tell the user what changed in everyday words; do not show theme fields or command arguments as the explanation. Inspect the file's contents; actual layout and playback in PowerPoint/Keynote need authorized viewing, and remain unverified when apps cannot be opened.

## Change one slide

1. Run `scripts/deck.py` with `outline --file 发布会/发布会.pptx` to read the current file and find the requested page. This also applies after a web presentation was exported: do not rebuild from its old outline.
2. Write the new slide, one slide object as below, to a file such as `.tmp/发布会/slide3.json`.
3. Run `scripts/deck.py` with `edit --file 发布会/发布会.pptx --slide 3 --spec .tmp/发布会/slide3.json`. Only that slide changes; the others stay exactly as they are, edits made in PowerPoint or Keynote included.

## Change formatting, links, animations, media and transitions

For requests about what is already in a deck, use `change`; it keeps every slide's content, layout and the user's edits, and changes only what is named. Do not rebuild the deck or edit its XML by hand.

1. Run `scripts/deck.py` with `inspect --file 发布会/发布会.pptx` (or `--slide 3`). It lists each slide's shapes by number with name, placeholder, position, text, fonts and links, and the slide's transition, animations in playing order, and media.
2. Write the changes with workspace_write, in `.tmp/` too, for example `.tmp/发布会/changes.json`:

   ```json
   {"changes": [
     {"slide": 1, "shape": {"placeholder": "title"}, "font": {"eastAsia": "黑体", "latin": "Arial", "size": 40, "bold": true}, "paragraph": {"align": "center"}},
     {"slide": 2, "shape": {"placeholder": "body"}, "only": "第三部分", "hyperlink": {"slide": 6}},
     {"slide": 2, "shape": {"placeholder": "title"}, "animation": {"effect": "fade", "start": "click"}},
     {"slide": 2, "shape": {"placeholder": "body"}, "animation": {"effect": "fly-in", "direction": "left", "start": "after-previous", "delay": 0.5}},
     {"slide": 1, "insert": "media", "path": "发布会/bgm.mp3", "start": "auto", "loop": true, "acrossSlides": true, "hidden": true},
     {"slide": "all", "transition": {"type": "fade", "duration": 0.7}}
   ]}
   ```

3. Run `change --file 发布会/发布会.pptx --spec .tmp/发布会/changes.json`, adding `--out 交付/发布会.pptx` to keep the original. Changes apply in order; if one cannot be made, nothing is saved and the message names it.
4. Run `inspect` on the result and check each requirement against it. Playback itself, such as timing as seen in a slideshow, still needs the file opened in PowerPoint or Keynote; say so when it was not.

Each change names `slide` (a number from 1, a list, a range like `"2-5"`, or `"all"`), except `{"move": 5, "to": 2}`, which moves a slide; later changes count slides in the new order. Then:

- `shape`: its number from inspect, its name, or `{"placeholder": "title" | "subtitle" | "body" | …}`, `{"contains": "…"}`, `{"id": 4}`. With it:
  - `font`: `name` (both faces), `latin`, `eastAsia`, `size` (points or a Chinese named size such as `"小四"`), `bold`, `italic`, `underline`, `strike`, `color`. Chinese text uses `eastAsia`, so set it whenever a Chinese font is asked for.
  - `paragraph`: `align` (left, center, right, justify, distribute), `lineSpacing` (1.2, or `"28pt"`), `spaceBefore`, `spaceAfter`.
  - `only`: the text inside the shape that the font or link applies to; the rest is left alone.
  - `hyperlink`: `{"url": "https://…"}`, `{"slide": 4}`, `{"action": "next" | "previous" | "first" | "last" | "end"}`, or `null` to remove it. It goes on the text, or on the whole shape when the shape has no text or `"on": "shape"` is given.
  - `animation`: one effect or a list, added after the slide's existing ones. `type` is `entrance` (the default; effects `appear`, `fade`, `fly-in`, `wipe`, `zoom`), `emphasis` (`spin`, `grow` with `scale`) or `exit` (`disappear`, `fade`, `fly-out`, `wipe`, `zoom`). `start` is `click`, `with-previous` or `after-previous`; `delay` and `duration` are seconds; `direction` (left, right, top, bottom: where it comes from) is for fly and wipe; `repeat` counts plays. The order of the changes is the playing order.
  - `position`: `left`, `top`, `width`, `height`, such as `"2cm"`.
- `"animations": "clear"` removes the slide's animation sequence, media starts included, before new effects are added.
- `transition`: `{"type": "fade" | "push" | "wipe" | "split" | "cover" | "pull" | "cut" | "dissolve" | "zoom" | …, "direction": "right", "duration": 0.7, "advanceOnClick": true, "advanceAfter": 5}`, or `"none"`. `direction`, where the next slide comes from, applies to push, wipe, cover and pull.
- `"insert": "media"` with `path` (MP3, WAV, M4A sounds; MP4, MOV videos), optional `position` and, for video, `poster`. `start` is `on-media-click` (the default, when its icon or frame is clicked), `click` (the next click in the sequence), `with-previous`, `after-previous` or `auto` (by itself, after the previous effect), with `delay`. Sounds also take `loop`, `acrossSlides` (keeps playing on later slides) and `hidden` (no icon in the slideshow).

## Put an animated video or GIF on a chosen slide

1. Have the animation skill (for example HyperFrames or huashu-art-motion) export an MP4 or animated GIF into this project's folder, such as `发布会/demo.mp4`. Use the finished file, not a link to it. For broad playback compatibility, ask for H.264 video in an MP4; embedding does not convert codecs.
2. Read the deck's outline, then write one slide object to `.tmp/发布会/slide3.json`. For video:

   ```json
   {"layout": "video", "title": "一句话，让家动起来", "video": "发布会/demo.mp4", "poster": "发布会/demo-cover.png", "caption": "点击播放演示"}
   ```

   The optional `poster` is a PNG or JPEG with the same aspect ratio as the video. If omitted, the script tries to extract the first frame with ffmpeg. When ffmpeg is unavailable or extraction fails, it draws a plain play placeholder. In that case, set `aspectRatio` to the video's display width divided by height (for example `0.5625` for 9:16); the default is 16:9. Ask the animation skill for the dimensions if needed. The video is embedded either way; ffmpeg is not required to embed it.

   For an animated GIF, use `{"layout": "image", "title": "一句话，让家动起来", "image": "发布会/demo.gif"}`. The original GIF, including its animation frames, is embedded without conversion. Both layouts fit the content area without cropping and leave room for an optional caption.
3. Run `scripts/deck.py` with `edit --file 发布会/发布会.pptx --slide 3 --spec .tmp/发布会/slide3.json`. Slide numbers start at 1. To make a new deck, put the same slide object at the chosen position in the outline's `slides` list and use `build` instead.
4. Tell the user which page changed. Check playback in slideshow mode in PowerPoint or Keynote when opening the file is authorized; click the video to play it. A static preview may show only the poster or the GIF's first frame, so it does not prove playback works. If playback cannot be checked, say so.

## Layouts

Every slide has `layout` and `title`; `notes` (speaker notes) is optional.

- `cover`: `subtitle`. The first slide.
- `section`: `subtitle`. Opens a part of the talk.
- `bullets`: `bullets`, 2 to 5 short lines; 3 reads best.
- `two-column`: `left` and `right`, each `{"heading": "…", "bullets": ["…"]}`. For before and after, or two options.
- `stats`: `stats`, 1 to 4 of `{"value": "0.3 秒", "label": "唤醒"}`.
- `chart`: `chart` = `{"type": "column" | "bar" | "line" | "pie" | "stacked", "categories": ["Q1", "Q2"], "series": [{"name": "销量", "values": [120, 180]}]}`, and an optional `caption` naming the data's source. Each series has one value per category.
- `image`: `image`, a PNG, JPEG or GIF in the project (animated GIFs keep their frames); optional `caption`.
- `video`: `video`, an MP4 in the project; optional `poster`, `aspectRatio` (for the drawn fallback poster, between 0.01 and 100) and `caption`. See the animated video steps above.
- `quote`: the `title` is the quote; `subtitle` names who said it.
- `closing`: `subtitle`. The last slide.

Keep one idea per slide and titles that say the point ("预约量持续上升"), not the topic ("预约量").

## When it fails

The script exits with a message naming the slide and what to change, such as a layout name that does not exist or values that do not match the categories. Fix the outline and run it again.
