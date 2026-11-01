---
name: xlsx
description: Make an Excel workbook (.xlsx) for Excel and Numbers with formats, totals and charts, or change a given one: formulas, number formats, conditional formatting, charts, widths, frozen panes, protection. Use for a spreadsheet, Excel file or .xlsx. Excel、表格、电子表格、预算、统计、表計算、エクセル。
metadata:
  otoha-title-zh: Excel 表格
  otoha-title-en: Excel spreadsheets
  otoha-title-ja: Excel 表
  otoha-summary-zh: 做带格式、合计和图表的 Excel 表格，或修改你给的表格。
  otoha-summary-en: "Makes Excel spreadsheets with formatting, totals and charts, or changes one you give."
  otoha-summary-ja: 書式・合計・グラフつきの Excel 表を作ったり、渡された表を直したりします。
allowed-tools: skill_read skill_run workspace_read workspace_write file_open
version: 1.1.0
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

To see what a workbook holds, the user's own included, run `scripts/workbook.py` with `read --file 数据/预约.xlsx`. To change a workbook you made, change its description and build it again. To change a workbook the user gave, change that file, as below; do not rebuild it.

## Change an existing workbook

1. Run `inspect --file 原表.xlsx`, adding `--sheet 预约` and `--range A1:H40` for a part. It shows each cell's value or formula, number format, font, fill, alignment and borders, and each sheet's widths, frozen panes, merged cells, filters, conditional formats, charts, validation and protection.
2. Write the changes with workspace_write, for example `changes.json`:

   ```json
   {"changes": [
     {"sheet": "预约", "range": "A1:D1", "font": {"name": "黑体", "bold": true}, "fill": "#DDEBF7", "align": {"horizontal": "center"}, "border": "thin"},
     {"sheet": "预约", "range": "E2:E13", "formula": "=C2*D2", "numberFormat": "currency"},
     {"sheet": "预约", "cells": {"E1": "金额", "E14": {"formula": "=SUM(E2:E13)"}}},
     {"sheet": "预约", "columnWidths": {"A": 12, "B:E": "auto"}, "freeze": "B2"},
     {"sheet": "预约", "conditionalFormat": {"range": "E2:E13", "rule": "greaterThan", "value": 10000, "fill": "#FFC7CE"}},
     {"sheet": "预约", "chart": {"type": "column", "data": "E1:E13", "categories": "A2:A13", "title": "月度金额", "at": "G2"}}
   ]}
   ```

3. Run `change --file 原表.xlsx --spec changes.json --out 交付/新表.xlsx`; without `--out` the file changes in place. Changes apply in order; if one cannot be made, nothing is saved and the message names it.
4. Run `inspect` on the result and check each requirement against it.

Each change names `sheet`, then any of:

- With `range` (`"A1:D9"`, `"B:B"`, `"2:2"`): `numberFormat` (an Excel format such as `"0.00%"` or `"yyyy年m月d日"`, or `text`, `number`, `integer`, `percent`, `currency`, `date`), `font` (`name`, `size`, `bold`, `italic`, `underline`, `strike`, `color`), `fill` (a colour, or `"none"`), `align` (`horizontal`, `vertical`, `wrap`, `indent`, `rotation`, `shrink`), `border` (`"thin"`, or `{"style": "medium", "color": "000000", "edges": "all" | "outline" | "inside" | ["bottom"]}`), `formula` (the first cell's formula, which the rest of the range follows, as Excel's fill does), `locked` and `hidden` (used when the sheet is protected).
- `cells`: values by cell, `{"E1": "金额", "E14": {"formula": "=SUM(E2:E13)"}}`. Text stays text even when it starts with `=`.
- `columnWidths` (characters, or `"auto"`), `rowHeights` (points; `{"1": 24, "2-10": 18}`), `freeze` (the first cell that scrolls, or `null`), `merge`, `unmerge`, `autoFilter` (a range or `null`).
- `conditionalFormat`: one rule or a list, each with `range` and `rule`: `greaterThan`, `lessThan`, `between`, `notBetween`, `equal`, `notEqual`, `greaterThanOrEqual`, `lessThanOrEqual` (with `value`, or two `values`), `formula` (a test written for the range's first cell, like `"$B2>30"`), `top` or `bottom` (`rank`, `percent`), `duplicate`, `unique`, `containsText` (`text`), each with `fill` and `font`; or `colorScale` (`colors`, two or three) and `dataBar` (`color`).
- `chart`: `type` (`column`, `bar`, `line`, `pie`, `area`, `scatter`), `data` (a range whose first row holds the series names), `categories`, `title`, `xTitle`, `yTitle`, `at`, `width` and `height` (centimetres), `stacked`, `legend`.
- `protect`: `{"password": "…", "allow": ["sort", "autoFilter", "formatColumns"]}` lists what people may still do; `false` removes protection.

Formulas, number formats, conditional formats, charts, validation, names and merged cells already in the workbook are kept. Saved formulas have no stored results until the workbook is opened in Excel, which works them out again. If the file holds things this script cannot keep, such as macros, slicers, sparklines or form controls, `change` stops and names them. Tell the user; only if they agree, add `"acceptLosing": true` next to `changes`.

## Sheets

- `name`, at most 31 characters; `[ ] : * ? / \` become `-`.
- `columns`: each a header alone, `"月份"`, or `{"header": "…", "format": …, "decimals": …, "width": …}`. `format` is `text`, `number` (2 decimals, or `decimals` from 0 to 6), `integer`, `percent` (0.12 shows as 12.0%), `currency` or `date`. Without a format the first column is text and the others are numbers.
- `rows`: one value per column. Numbers as numbers, not text; dates as `"2026-10-28"` in a `date` column. Text always stays text, even when it starts with `=`; a formula is written `{"formula": "=B2*C2"}`.
- `totals`: optional; `label` and the columns to `sum`, by header.
- `chart`: optional; `type` is `column`, `bar`, `line` or `pie`, `categories` a column's header, `values` one or more columns' headers.

## When it fails

The script exits with a message naming the sheet and row, or the change, and what to change. Fix the description or the changes and run it again.
