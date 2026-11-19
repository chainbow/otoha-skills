---
name: docx
description: Make a Word document (.docx) for Word and Pages, or change the formatting of a given one: fonts, sizes, spacing, styles, tables, page setup, headers, footers, page numbers. Use for a Word file, a .docx or a document to send or print. Word 文档、排版、格式修改、会议纪要、信函、文書、書式、議事録。
metadata:
  otoha-title-zh: Word 文档
  otoha-title-en: Word documents
  otoha-title-ja: Word 文書
  otoha-summary-zh: 做新的 Word 文档，或调整你给的文档的字体、段落、表格和页面格式。
  otoha-summary-en: "Makes new Word documents, or changes the fonts, spacing, tables and page layout of one you give."
  otoha-summary-ja: Word 文書を新しく作ったり、渡された文書のフォント・段落・表・ページ設定を整えたりします。
allowed-tools: skill_read skill_run workspace_read workspace_write file_open
version: 1.1.1
---
# Word documents

`scripts/document.py`, run with skill_run, builds new documents from a description and changes the formatting of existing ones. A new document has a fixed look: clear headings in the app's indigo, readable body text, tables with a shaded header. Do not try to style a new document yourself.

When the user gives a document, change that file with `change` (below). Do not rebuild it from a description and do not edit its XML by hand: both lose details.

## Make a document

1. Write the description with workspace_write, as JSON, for example `.tmp/复盘/doc.json`. Working files such as this one go in the project's `.tmp/` folder, never beside the result: the folder the user gets holds only what they asked for.

   ```json
   {"title": "Q4 发布会复盘", "subtitle": "2026 年 11 月", "blocks": [
     {"type": "heading", "level": 1, "text": "结论"},
     {"type": "paragraph", "text": "…"}
   ]}
   ```

2. Run `scripts/document.py` with `build --spec .tmp/复盘/doc.json --out 复盘/复盘.docx`.
3. Tell the user the file's name; open it with file_open if they want to see it.

To change a document you made, change its description in `.tmp/` and build it again; if the description is no longer there, read the document with `outline` and write it again first. To see what an existing document holds, run `scripts/document.py` with `outline --file 复盘/复盘.docx`.

## Blocks

- `heading`: `level` 1, 2 or 3, and `text`.
- `paragraph`: `text`.
- `bullets` and `numbered`: `items`, a list of lines.
- `table`: `header`, a list of column names, and `rows`, each with one cell per column.
- `image`: `path` of a picture in the project, `width_cm` (15 by default), optional `caption`.
- `quote`: `text`.
- `page-break`.

## Change an existing document

1. Read its formatting: `inspect --file 原稿.docx` (add `--paragraphs 81-160` for later parts of a long file). Paragraphs are numbered `n`, table paragraphs included; `textFormats` counts the text in each font and size.
2. Write the changes as JSON with workspace_write, in `.tmp/` too, for example `.tmp/复盘/changes.json`:

   ```json
   {"changes": [
     {"style": "正文", "font": {"eastAsia": "宋体", "latin": "Times New Roman", "size": "小四"}, "paragraph": {"firstLineIndent": "2字符", "lineSpacing": 1.5}},
     {"where": {"in": "document"}, "font": {"eastAsia": "宋体", "latin": "Times New Roman"}},
     {"where": {"style": "标题 1"}, "font": {"eastAsia": "黑体", "size": "三号", "bold": true}, "paragraph": {"align": "center", "firstLineIndent": 0}},
     {"table": "all", "borders": "three-line", "cells": {"font": {"size": "五号"}, "paragraph": {"align": "center", "firstLineIndent": 0}}},
     {"footer": {"text": "第 {PAGE} 页 共 {NUMPAGES} 页", "align": "center"}}
   ]}
   ```

3. Run `change --file 原稿.docx --spec .tmp/复盘/changes.json --out 交付/定稿.docx`. Without `--out` the file changes in place. Changes apply in order. If one cannot be made, for example it matches no paragraph, nothing is saved and the message names it.
4. Run `inspect` on the result and check each requirement against it, one at a time. Say which ones need the page to be seen, such as page count or where pages break.

Each change names one target:

- `where`: paragraphs, with `font`, `paragraph`, or both. `only` formats just that text inside them. `where` combines `in` (`document`, the default: body and tables; or `body`, `tables`, `headers`, `footers`, `textboxes`, `everywhere`), `paragraphs` (numbers from inspect: `[3]`, `"5-9"`, `"all"`), `style`, `contains`, `startsWith`, `regex` and `table` (a table's number).
- `style`: a style's `font` and `paragraph`, by English or Chinese name (`Normal`, `正文`, `Heading 1`, `标题 1`). `"create": {"basedOn": "Normal"}` makes a missing one.
- `table`: a number, a list or `"all"`. `borders` is `all`, `outer`, `inner`, `none`, `three-line`, or `{"preset": "three-line", "size": "1.5pt", "innerSize": "0.75pt"}`, or edges (`top`, `bottom`, `left`, `right`, `insideH`, `insideV`) each `{"style": "single", "size": "0.5pt", "color": "000000"}` or `"none"`. Also `width` (`"100%"`, `"15cm"`), `columnWidths`, `align`, `rowHeight`, `headerRepeat`, `merge` (`[{"from": [1, 1], "to": [1, 3]}]`, row and column from 1) and `cells` (`{"rows": "header" | "all" | "2-5", "columns": [1], "font", "paragraph", "shading": "D9D9D9", "verticalAlign", "borders"}`).
- `page`: `size` (A4, A3, A5, B5, 16K, Letter, Legal, or `{"width", "height"}`), `orientation`, `margins` (`top`, `bottom`, `left`, `right`, `header`, `footer`, `gutter`), `pageNumbers` (`{"start": 1, "format": "upperRoman"}`), `differentFirstPage`, `differentOddEven`, `columns`. `sections` picks sections; all by default.
- `header` and `footer`: `text`, where `{PAGE}`, `{NUMPAGES}` and `{SECTIONPAGES}` become page fields and `\n` starts a new line; `align`, `font`, `paragraph`, `line` (a rule under the header or over the footer), `pages` (`default`, `first`, `even`) and `sections`.
- `insert`: `page-break`, `section-break` (`start`: nextPage, continuous, oddPage, evenPage) or `toc` (`levels` like `"1-3"`, optional `title` and `pageBreakAfter`), with `before` or `after`, a `where`. Give a new section its own footer or page numbers with `sections`.

`font` takes `name` (both faces), `latin`, `eastAsia`, `size`, `bold`, `italic`, `underline` (true, single, double, thick, dotted, dash, wave), `strike`, `color`, `highlight` and `verticalAlign`. `paragraph` takes `style`, `align` (left, center, right, justify, distribute), `firstLineIndent`, `hangingIndent`, `leftIndent`, `rightIndent`, `lineSpacing` (1.5 for a multiple, `"20pt"` for exactly, `{"atLeast": "12pt"}`), `spaceBefore`, `spaceAfter`, `keepWithNext`, `keepTogether`, `pageBreakBefore`, `widowControl` and `outlineLevel`. A length is points as a number, or `"2cm"`, `"5mm"`, `"1in"`, `"12pt"`, `"12磅"`; indents also take characters (`"2字符"`) and spacing lines (`"0.5行"`).

### Chinese fonts and sizes

Named sizes (号数) in points; `size` takes either:

| 初号 | 小初 | 一号 | 小一 | 二号 | 小二 | 三号 | 小三 | 四号 | 小四 | 五号 | 小五 | 六号 | 小六 | 七号 | 八号 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 42 | 36 | 26 | 24 | 22 | 18 | 16 | 15 | 14 | 12 | 10.5 | 9 | 7.5 | 6.5 | 5.5 | 5 |

小四 is 12 pt and 四号 is 14 pt; write the name the requirement uses rather than converting by hand.

Word sets Chinese characters in the East Asian font and Latin letters and digits in the Latin font, so a Chinese font must go in `eastAsia`, and a 西文 or English font in `latin`. Formatting set on the text itself wins over its style, which is the usual reason a style change seems not to work: change the style, then the paragraphs (`where`) too. After the change, every body entry in `textFormats` should show the requested faces and size.

## When it fails

The script exits with a message naming the block or change and what to change. Fix the description or the changes and run it again.
