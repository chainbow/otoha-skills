---
name: report
description: Research a question on the web and write a report with sources: market or competitor scans, background briefs, fact checks. Use when the user asks for a report, research, 调研 or an overview that needs outside information. 报告、调研、竞品、市场、レポート、調査。
allowed-tools: skill_read browser_search browser_open browser_read browser_click workspace_read workspace_write
---
# Research reports

## Research

1. Restate the question in one sentence, and list the 3 to 6 things the report must answer.
2. For each, search with browser_search, open the most relevant results with browser_click, and read them. Prefer primary sources: official sites, filings, statistics offices, the original article. For several pages of one site, read its llms.txt first when it has one.
3. Note for every fact the page it came from (title and address) and its date. A fact without a source does not go into the report; say what could not be confirmed instead.
4. Keep the project's own private things (client names, amounts, file contents) out of searches.

## Write

Write the report with workspace_write as Markdown, following `references/template.md`, into the project, for example `调研/智能家居中枢竞品.md`. To change a report later, use workspace_write in edit mode on the passages that change rather than writing it again. Numbers go in tables. Every fact carries its source as a numbered link, [1], listed under 来源 at the end.

If the user wants it as Word or slides, use the docx, slides or pptx skill with the report's content.
