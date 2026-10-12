# Infographics and diagrams

The same rules as any design (`principles.md`), plus: the reader should get the point in five seconds, so the title states it.

## Infographic

Order from top to bottom:

1. **Title that states the finding** ("三成的外卖订单来自晚上 9 点后"), with a one-line subtitle for scope and date.
2. **The key figure** very large (display size), with its label beside or under it.
3. **Two to four supporting blocks**, each one form: a bar comparison, a share (donut or stacked bar), a trend line, a short list with icons, a timeline. One message per block.
4. **Source and date** at the bottom in caption size. Never invent figures: use the user's, or label invented ones "示例数据".

Pick the form from the message: compare amounts, bars; part of a whole (up to five parts), donut or one stacked bar; change over time, a line or columns; a sequence, a timeline; a process, steps. Avoid 3D, more than five slices, dual axes, and decorating every number.

Layout: a single column of full-width blocks of equal margin for scrolling infographics; a 2×2 or 3-column grid for one-page ones. Section headings in `t-h3`, numbers in `t-display` or `t-h1`, labels `t-small`.

### Drawing charts without a library

Bars (HTML, widths from the data; the longest bar is 100%):

```html
<div class="stack gap-3">
  <div class="row gap-4">
    <span class="t-small" data-edit="bar-1-label" style="width:140px">周一</span>
    <div style="flex:1;height:28px;background:var(--color-surface);border-radius:var(--radius-s)">
      <div style="width:62%;height:100%;background:var(--color-primary);border-radius:var(--radius-s)"></div>
    </div>
    <span class="t-small" data-edit="bar-1-value">620</span>
  </div>
</div>
```

Donut (SVG circle, radius 70, circumference 2π·70 ≈ 439.8; a share of p% is a dash of 4.398·p):

```html
<svg viewBox="0 0 200 200" width="240" height="240">
  <circle cx="100" cy="100" r="70" fill="none" stroke="var(--color-surface)" stroke-width="28"/>
  <circle cx="100" cy="100" r="70" fill="none" stroke="var(--color-primary)" stroke-width="28"
          stroke-dasharray="132 307.8" transform="rotate(-90 100 100)"/>
</svg>
```

A second slice starts where the first ended: rotate it by `−90 + 3.6·(sum of earlier percentages)` degrees. Put the figure and label in the centre as HTML text over the SVG, not as SVG text.

Line: a `<polyline points="x,y …">` in a viewBox; y grows downward, so y = bottom − value/max·height. Mark the last point and label it directly; skip gridlines except a baseline.

Always put the numbers as text with `data-edit` so they can be corrected.

## Flow diagrams and process sketches

Plan before drawing: list the steps, who does each, the branches; put the main path in one direction (left to right, or top to bottom), branches off it, and keep the number of crossings at zero. Eight to twelve nodes is the practical limit for one artboard; split larger ones.

Two ways to build, simplest first:

**1. HTML boxes in a row or grid (preferred).** Text wraps by itself and takes `data-edit` plainly. Arrows are small SVG shapes without text between the boxes.

```html
<div class="row gap-4">
  <div class="card grow t-center"><p class="t-h3" data-edit="step-1">下单</p></div>
  <svg width="48" height="24" viewBox="0 0 48 24" aria-hidden="true"><path d="M0 12H40M32 4l8 8-8 8" fill="none" stroke="var(--color-muted)" stroke-width="2"/></svg>
  <div class="card grow t-center"><p class="t-h3" data-edit="step-2">付款</p></div>
</div>
```

**2. SVG for free layouts** (branches, hub and spoke, maps). Give the SVG the same size as the part of the artboard it fills, so one unit is one px. Decide each node's rectangle first (x, y, width, height) on a grid, write them down, then draw connectors from the edges' midpoints so the numbers match.

```html
<svg class="diagram" viewBox="0 0 1200 600" width="1200" height="600">
  <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path class="arrow-head" d="M0 0L10 5L0 10z"/></marker></defs>
  <rect class="node" x="40" y="240" width="220" height="100" rx="16"/>
  <text x="150" y="298" text-anchor="middle" font-size="28" data-edit="start">收到申请</text>
  <path class="link" d="M260 290H340" marker-end="url(#arrow)"/>
  <rect class="node-primary" x="340" y="240" width="220" height="100" rx="16"/>
  <text class="on-primary" x="450" y="298" text-anchor="middle" font-size="28" data-edit="review">审核</text>
</svg>
```

- SVG text does not wrap: keep each label to one line that fits its box. Width estimate: a Chinese or Japanese character is 1× the font size, a Latin letter about 0.55×. Leave 24 px inside the box on each side. Labels longer than that go in HTML.
- Vertical centre: `y` = box top + height/2 + font-size × 0.35.
- Connectors: straight lines or one elbow (`M x1 y1 H xm V y2 H x2`). Keep arrows on one side-to-side pattern; label a branch ("是", "否") next to its line, with a `data-edit` name.
- Style by role: normal step `node`, start/end or the step to remember `node-primary` (one or two per diagram), decision as a diamond path (`M cx cy−h L cx+w cy L cx cy+h L cx−w cy z`) or a `node` with a "?" label.
- Colour means something: the primary colour marks the main path; muted lines are the rest.

## Other sketches

- **Mind map / hub and spoke**: the centre node in primary at the middle; five to eight nodes evenly around it at the same distance; lines from the centre.
- **Timeline**: a line with dated points, labels alternate above and below, or one column of rows with the date in a fixed-width left column.
- **Architecture / layers**: stacked full-width bands, each with a label and boxes inside; arrows only for data flow.
- **Matrix (2×2)**: a cross of two thin lines, labelled axes at the ends, items as dots with short labels.
- **Comparison table**: a grid with the first column muted, the recommended column highlighted with `--color-surface` and a primary top border.
