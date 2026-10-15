---
name: pptx
description: Make or change a PowerPoint deck (.pptx) that opens in PowerPoint and Keynote. Use when the user asks for a PPT, PPTX, Keynote-compatible deck or slides as a file, or to change one slide of such a deck. PPT、PPTX、PowerPoint、幻灯片、演示文稿、パワーポイント、スライド。
allowed-tools: skill_read skill_run workspace_read workspace_write file_open
---
# PPTX decks

Decks are built from an outline by `scripts/deck.py`, run with skill_run. Without a theme, the default look is white slides, dark text and an indigo accent. Native text and charts stay editable. When the user asks for a different style, or another skill supplies design rules, translate those rules into the outline’s theme instead of refusing or keeping the default. The style skill supplies rules; this skill applies them to the file. Preserve facts, slide count and editability.

## Make a deck

1. Write the outline with workspace_write, as JSON, next to where the deck goes, for example `发布会/outline.json`:

   ```json
   {"title": "让家，更懂你", "slides": [
     {"layout": "cover", "title": "让家，更懂你", "subtitle": "2026 秋季新品发布会"},
     {"layout": "bullets", "title": "为什么是现在", "bullets": ["…", "…", "…"], "notes": "讲稿"}
   ]}
   ```

2. Run `scripts/deck.py` with the arguments `build --spec 发布会/outline.json --out 发布会/发布会.pptx`.
3. Tell the user the file's name. If they want to see it, open it with file_open.

## Apply a style

Use an optional `theme` next to `title` and `slides` in the outline. For Japanese minimal design with off-white, charcoal and soft teal:

```json
{"theme": {"background": "#F7F5EF", "text": "#28302F", "accent": "#3C706B", "headingFont": "Hiragino Sans", "bodyFont": "sans-serif", "density": "airy"}, "slides": [{"layout": "cover", "title": "减少食品浪费", "subtitle": "从一个品类开始"}]}
```

- Colours are exactly six hexadecimal digits, optionally prefixed by `#`. Every themed slide, including covers, chart and video pages, uses the chosen background. Shape fills, accents, chart series and text follow the palette; pictures, movie bytes and supplied posters retain their original colours.
- `headingFont` and `bodyFont` each name a supported face: Helvetica Neue, Arial, Aptos, Calibri, Georgia, Times New Roman, Courier New, PingFang SC, Hiragino Sans, Yu Gothic, Noto Sans CJK SC, Noto Sans JP or Noto Serif JP. Prefer faces available on the user's computer. If a guide names another font, use `sans-serif`, `serif` or `monospace` instead; these select Arial/PingFang SC, Georgia/Songti SC or Courier New/PingFang SC. East Asian text always has an explicit CJK face; fonts are not downloaded or embedded.
- `density` is `compact`, `normal` or `airy`. Airy gives more outer whitespace by fitting content into a smaller footprint; compact uses a larger footprint. Text size and point spacing scale with the footprint; media keep their aspect ratios. Omitted fields keep the default values. Omitting theme altogether preserves the old file and style exactly.

For an existing deck, do **not** reconstruct its outline just to change style: that could lose user edits or media. Write a file such as `style.json` containing only `{"theme": {...}}`, then run `scripts/deck.py` with `edit --file 发布会/发布会.pptx --spec style.json`, without `--slide`. This applies the theme to every slide while keeping text, tables, charts, speaker notes, images and video. The deck remembers the theme, so later single-slide replacements use it too. Applying the same theme again does not keep shrinking or enlarging the content. To also replace one slide and theme the whole deck, include `theme` in that slide object and pass `--slide`.

This changes the existing file. If the user asks to keep the original, use `edit --file 发布会/发布会.pptx --spec style.json --out 发布会/日式简约.pptx` to save the changed copy, without a separate copy command. Tell the user what changed in everyday words; do not show theme fields or command arguments as the explanation. Inspect the file's contents; actual layout and playback in PowerPoint/Keynote need authorized viewing, and remain unverified when apps cannot be opened.

## Change one slide

1. Run `scripts/deck.py` with `outline --file 发布会/发布会.pptx` to read what each slide holds.
2. Write the new slide, one slide object as below, to a file such as `发布会/slide3.json`.
3. Run `scripts/deck.py` with `edit --file 发布会/发布会.pptx --slide 3 --spec 发布会/slide3.json`. Only that slide changes; the others stay exactly as they are, edits made in PowerPoint or Keynote included.

## Put an animation on a chosen slide

1. Have the animation skill (for example HyperFrames or huashu-art-motion) export an MP4 or animated GIF into this project's folder, such as `发布会/demo.mp4`. Use the finished file, not a link to it. For broad playback compatibility, ask for H.264 video in an MP4; embedding does not convert codecs.
2. Read the deck's outline, then write one slide object to `发布会/slide3.json`. For video:

   ```json
   {"layout": "video", "title": "一句话，让家动起来", "video": "发布会/demo.mp4", "poster": "发布会/demo-cover.png", "caption": "点击播放演示"}
   ```

   The optional `poster` is a PNG or JPEG with the same aspect ratio as the video. If omitted, the script tries to extract the first frame with ffmpeg. When ffmpeg is unavailable or extraction fails, it draws a plain play placeholder. In that case, set `aspectRatio` to the video's display width divided by height (for example `0.5625` for 9:16); the default is 16:9. Ask the animation skill for the dimensions if needed. The video is embedded either way; ffmpeg is not required to embed it.

   For an animated GIF, use `{"layout": "image", "title": "一句话，让家动起来", "image": "发布会/demo.gif"}`. The original GIF, including its animation frames, is embedded without conversion. Both layouts fit the content area without cropping and leave room for an optional caption.
3. Run `scripts/deck.py` with `edit --file 发布会/发布会.pptx --slide 3 --spec 发布会/slide3.json`. Slide numbers start at 1. To make a new deck, put the same slide object at the chosen position in the outline's `slides` list and use `build` instead.
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
- `video`: `video`, an MP4 in the project; optional `poster`, `aspectRatio` (for the drawn fallback poster, between 0.01 and 100) and `caption`. See the animation steps above.
- `quote`: the `title` is the quote; `subtitle` names who said it.
- `closing`: `subtitle`. The last slide.

Keep one idea per slide and titles that say the point ("预约量持续上升"), not the topic ("预约量").

## When it fails

The script exits with a message naming the slide and what to change, such as a layout name that does not exist or values that do not match the categories. Fix the outline and run it again.
