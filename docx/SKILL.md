---
name: docx
description: Make a Word document (.docx) that opens in Word and Pages: reports, minutes, proposals, letters. Use when the user asks for a Word file, a .docx, or a document to send or print. Word 文档、会议纪要、提案、信函、文書、議事録。
allowed-tools: skill_read skill_run workspace_read workspace_write file_open
version: 1.0.0
---
# Word documents

Documents are built from a description by `scripts/document.py`, run with skill_run. The look is fixed: clear headings in the app's indigo, readable body text, tables with a shaded header. Do not try to style the document yourself.

## Make a document

1. Write the description with workspace_write, as JSON, for example `复盘/doc.json`:

   ```json
   {"title": "Q4 发布会复盘", "subtitle": "2026 年 11 月", "blocks": [
     {"type": "heading", "level": 1, "text": "结论"},
     {"type": "paragraph", "text": "…"}
   ]}
   ```

2. Run `scripts/document.py` with `build --spec 复盘/doc.json --out 复盘/复盘.docx`.
3. Tell the user the file's name; open it with file_open if they want to see it.

To change a document you made, change its description and build it again. To see what an existing document holds, run `scripts/document.py` with `outline --file 复盘/复盘.docx`.

## Blocks

- `heading`: `level` 1, 2 or 3, and `text`.
- `paragraph`: `text`.
- `bullets` and `numbered`: `items`, a list of lines.
- `table`: `header`, a list of column names, and `rows`, each with one cell per column.
- `image`: `path` of a picture in the project, `width_cm` (15 by default), optional `caption`.
- `quote`: `text`.
- `page-break`.

## When it fails

The script exits with a message naming the block and what to change. Fix the description and run it again.
