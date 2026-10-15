---
name: xlsx
description: Make an Excel workbook (.xlsx) that opens in Excel and Numbers: tables of data with formats, totals and charts. Use when the user asks for a spreadsheet, an Excel file, a .xlsx or a table to work on. Excel、表格、电子表格、预算、统计、表計算、エクセル。
allowed-tools: skill_read skill_run workspace_read workspace_write file_open
version: 1.0.0
---
# Excel workbooks

Workbooks are built from a description by `scripts/workbook.py`, run with skill_run. Each sheet gets a header row in the app's indigo, frozen and with filters, formatted columns, an optional totals row with SUM formulas, and an optional chart.

## Make a workbook

1. Write the description with workspace_write, as JSON, for example `数据/book.json`:

   ```json
   {"sheets": [{
     "name": "预约",
     "columns": [{"header": "月份", "format": "text"}, {"header": "预约（台）", "format": "integer"}, {"header": "转化率", "format": "percent"}],
     "rows": [["7 月", 3200, 0.12], ["8 月", 5800, 0.15]],
     "totals": {"label": "合计", "sum": ["预约（台）"]},
     "chart": {"type": "column", "title": "月度预约", "categories": "月份", "values": ["预约（台）"]}
   }]}
   ```

2. Run `scripts/workbook.py` with `build --spec 数据/book.json --out 数据/预约.xlsx`.
3. Tell the user the file's name; open it with file_open if they want to see it.

To see what a workbook holds, the user's own included, run `scripts/workbook.py` with `read --file 数据/预约.xlsx`. To change a workbook you made, change its description and build it again.

## Sheets

- `name`, at most 31 characters; `[ ] : * ? / \` become `-`.
- `columns`: each a header alone, `"月份"`, or `{"header": "…", "format": …, "decimals": …, "width": …}`. `format` is `text`, `number` (2 decimals, or `decimals` from 0 to 6), `integer`, `percent` (0.12 shows as 12.0%), `currency` or `date`. Without a format the first column is text and the others are numbers.
- `rows`: one value per column. Numbers as numbers, not text; dates as `"2026-10-28"` in a `date` column. Text always stays text, even when it starts with `=`; a formula is written `{"formula": "=B2*C2"}`.
- `totals`: optional; `label` and the columns to `sum`, by header.
- `chart`: optional; `type` is `column`, `bar`, `line` or `pie`, `categories` a column's header, `values` one or more columns' headers.

## When it fails

The script exits with a message naming the sheet and row and what to change. Fix the description and run it again.
