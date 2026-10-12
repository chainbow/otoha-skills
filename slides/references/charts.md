# Charts

A chart is data inside the slide, drawn by the deck when it is shown (and when it is printed to PDF), so it needs no picture and no network.

```html
<figure class="chart">
  <script type="application/json">{"type": "line", "categories": ["7 月", "8 月", "9 月"], "series": [{"name": "预约（万）", "values": [3.2, 5.8, 9.1]}]}</script>
  <figcaption data-edit="source">数据截至 9 月 25 日，来源：预约后台</figcaption>
</figure>
```

## Choosing

| To show | Use |
| --- | --- |
| Compare a few things (up to 8) | `column`; `bar` when the names are long |
| A change over time | `line` |
| Parts of a whole that adds to 100% (up to 5 parts) | `pie` |
| Parts of a whole across several groups | `stacked` |

Prefer one message per chart: the title says it ("预约量持续上升"), the chart shows it. Two series at most are easy to read; five is the limit.

## Data

- `type` is one of `column`, `bar`, `line`, `pie`, `stacked`.
- `categories` is a list of names, `series` a list of `{"name": "…", "values": [...]}`; every series has exactly one number for each category. A `pie` has one series, numbers of 0 or more.
- Put the unit in the series name ("预约（万）", "Revenue ($M)"). The value axis starts at zero; the deck draws it.
- Numbers are numbers (`9.1`), not text (`"9.1万"`).
- Category names are short: 2 to 6 Chinese characters.

If the data does not fit, the build says so and names the slide, and the chart would show a red message instead of a drawing.

## Editing a chart

Change the numbers or names inside the `<script type="application/json">` of that slide's file. The chart has no `data-edit`; only its `figcaption` is retyped in the preview.

## Colours

The series use the deck's accent first and then a fixed set of teal, amber, red and grey. A deck's `theme.chart` replaces them (up to 5 colours); keep them far enough apart to tell in a PDF printed in grey: vary dark and light, not only hue.
