---
name: design
description: Design a poster, flyer, social image, app or web screen mockup, infographic, flow diagram or prototype as HTML pages in the project, previewed beside the conversation, with text the user can change. Use when the user asks for a visual design, 海报, 宣传图, 界面稿, 原型, 信息图, 示意图 or 流程图. Not for slide presentations (use the slides skill), editable PowerPoint (use the pptx skill) or a working website.
allowed-tools: skill_read skill_copy workspace_read workspace_write page_check image_generate
version: 1.0.0
---
# Design

A design is a folder. Each artboard (one poster, one screen, one diagram) is one HTML file of a fixed size; the colours, fonts and spacing are shared in one `tokens.css`. The app shows each artboard in the preview. Everything is plain files: no network, no libraries, no build step.

```
spring-menu-poster/
  tokens.css      colours, fonts, spacing, type sizes for this design
  poster.html     one artboard (more: home.html, detail.html …)
  images/         pictures, only if used
  lib/            base.css and check.js, copied from this skill
```

Use the user's language for every word in the design and for the folder names, unless they ask otherwise. Name the folder short and concrete, in the language of the request, with no generic parent folder such as `design/` or `设计/`: an English request gets `spring-menu-poster`, a Chinese request gets `春季菜单海报`. A new folder per design; never overwrite another design.

## Steps

1. **Ask only what changes the result**, in one short message, each question with your suggested answer: what it is for and where it will be seen, who looks at it, the size or format, the look (or a brand: colours, logo, mood), the words and facts it must contain. Skip what the request already says. If nobody can answer (a scheduled task) or the user says "just do it", decide, and tell them what you assumed. Questions to draw on: `references/questions.md`.
2. **Read** `references/principles.md`, then the file for the kind of work: `sizes.md` always; `color-and-type.md` always; `diagrams.md` for infographics, flows and maps; `accessibility.md` for screens.
3. **Set up**: skill_copy this skill's `assets` with `to` the whole path from the project root, e.g. `spring-menu-poster/lib` (or `春季菜单海报/lib` for a Chinese request). Check that the artboard files and `lib` end up in the same folder. Then write `tokens.css`: decide the colours and the fonts first, then the type sizes and spacing for the artboard's size.
4. **Write each artboard** with workspace_write, as below. One strong idea per artboard: a clear first thing to look at, then the rest in order.
5. **Check** with page_check on every artboard. It loads the page and reports errors: text without `data-edit`, text outside the artboard, text cut off or overflowing its box; and warnings: low contrast, text too small, text on top of text, empty space at the bottom or top. Look at the screenshot too: is the first thing you notice the right one, does the content fill the artboard from top to bottom (the closing line at the bottom, not floating in the middle), is anything uneven? **The work is not done until page_check reports nothing on every artboard: no errors and no warnings, overflow ones included.** Each report line starts with `design-check:` and names the elements (for example `text cut off or overflowing its box (1): footer`). If it names one, fix it and run page_check again. Call the design finished only when no line is left; if checks run out first, say plainly which line is left. To fix overflow: shorten the text; reduce the font size (through a token in `tokens.css`); allow the text to wrap (remove `white-space:nowrap`, widen the box, or give it `flex:1; min-width:0`); reduce the padding, gaps or the number of rows above it; if the content is simply too much for the artboard, split it across two artboards. Never hide it with `overflow:hidden` or by moving it outside the artboard. If it says `lib/check.js did not load` or `lib/base.css did not load`, `lib` is in the wrong place: fix that first. Checks are limited per message; fix everything you can see before the next one.
6. **Tell the user** in two or three plain sentences what you made, in which file, and what you assumed (size, look, wording you invented). Offer the next step in their words ("want the colours warmer?", "I can make the story size too"). See "Words for the user".

## An artboard

```html
<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>春季菜单海报</title>
<link rel="stylesheet" href="lib/base.css">
<link rel="stylesheet" href="tokens.css">
</head>
<body>
<main class="artboard" style="--w:1080px;--h:1440px">
  <h1 class="t-display" data-edit="title">春日菜单</h1>
  <p class="t-lead" data-edit="subtitle">三月限定 · 六道时令小菜</p>
</main>
<script src="lib/check.js"></script>
<script>window.designCheck||console.error("lib/check.js did not load")</script>
</body>
</html>
```

- Set the size on `.artboard` with `--w` and `--h`. Everything is placed inside it; nothing may depend on the window size. Sizes by purpose: `references/sizes.md`.
- Only `lib/base.css`, `tokens.css` and an inline `<style>` for this artboard's layout. Colours, fonts, sizes and spacing come from tokens through `var(--…)`, never typed in as loose values: when you need another size or colour, add it to `tokens.css` first. Class names and tokens are listed at the top of `lib/base.css` and in `references/color-and-type.md`.
- **Every visible text carries `data-edit="<slug>"`**: lowercase words joined by hyphens (`title`, `price-1`, `step-2-label`), unique within the artboard, describing the role, not the words. Put it on the element that holds the text; do not nest one inside another. Text in SVG gets it too. This is what lets the user change a word by clicking it in the preview.
- Text is real text, not text inside an image. Icons are small inline SVG drawn in `currentColor`, not emoji (emoji look different on every system and count as text). Pictures are files in `images/` with an `alt`; use image_generate only when the user wants a picture drawn (it asks them first and uses their plan's credit); otherwise draw with CSS and SVG.
- Several artboards of one design (a set of screens, a front and back) share one `tokens.css` and look alike.

## Change a design

Read the file with workspace_read, then change only what was asked with workspace_write in edit mode (oldText exact, appearing once). A change in colour or font goes in `tokens.css` so every artboard follows. If the user changed some wording in the preview, keep it. Check again with page_check.

## Words for the user

Write as to someone who has never made a web page. Say "海报", "页面", "文字", "颜色", "字体", "尺寸", "预览"; never artboard, token, data-edit, HTML, CSS, class, check script, hex codes, pixel sizes of fonts. A size is "A4 竖版" or "1080×1440 的竖图", not a style rule. When something cannot be done (a font missing, a picture needed), say what the user sees and what you did instead.
