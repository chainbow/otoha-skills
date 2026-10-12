# Layouts

Every slide is one file, `slides/<id>.html`, holding one `<section class="slide …" id="<id>">`. The `id` is the same one `deck.json` lists. Titles: `<h1>` on cover, section and closing slides; `<h2>` on all others. Slide numbers, the progress bar and the part-of-the-talk label are added when the page is shown.

Every piece of text sits in an element with `data-edit="a-name"`, a name that is unique within the slide: `title`, `lead`, `point-1`, `point-2`, `caption`. The app uses it to let the user retype that text in the preview. Words that are bold or emphasised inside a line stay inside it (`<p data-edit="lead">先看 <b>三件事</b></p>`); do not mark the inner tag. Text must not sit loose in a `<div>`: use `<p>` or `<span>`.

Speaker notes are optional on any slide, last inside the section, and never shown on the slide: `<aside class="notes" data-edit="notes">讲稿</aside>`. They go into the PowerPoint hand-off too.

## Cover

```html
<section class="slide cover" id="cover">
  <p class="eyebrow" data-edit="eyebrow">2026 秋季新品发布会</p>
  <h1 data-edit="title">让家，更懂你</h1>
  <p data-edit="subtitle">10 月 28 日 · 东京</p>
</section>
```

## Bullets (the default)

```html
<section class="slide" id="why-now">
  <h2 data-edit="title">为什么是现在</h2>
  <ul>
    <li data-edit="point-1">家里的设备越来越多</li>
    <li data-edit="point-2">每个设备一个 App，操作越来越复杂</li>
    <li data-edit="point-3">需要一个真正懂你的中枢</li>
  </ul>
</section>
```

A slide can carry one paragraph under its title: `<p class="lead" data-edit="lead">…</p>`, before the list.

## Two columns

The second column is highlighted: put the one to notice there ("现在", "推荐方案").

```html
<section class="slide" id="before-and-after">
  <h2 data-edit="title">以前与现在</h2>
  <div class="columns">
    <div>
      <h3 data-edit="before-title">以前</h3>
      <ul><li data-edit="before-1">逐个打开 App</li><li data-edit="before-2">记住每个设备的操作</li></ul>
    </div>
    <div>
      <h3 data-edit="after-title">现在</h3>
      <ul><li data-edit="after-1">一句话搞定</li><li data-edit="after-2">它记得你的习惯</li></ul>
    </div>
  </div>
</section>
```

## Stats

One to four numbers.

```html
<section class="slide" id="three-numbers">
  <h2 data-edit="title">三个数字</h2>
  <div class="stats">
    <div class="stat"><strong data-edit="value-1">0.3 秒</strong><span data-edit="label-1">唤醒</span></div>
    <div class="stat"><strong data-edit="value-2">2 天</strong><span data-edit="label-2">续航</span></div>
    <div class="stat"><strong data-edit="value-3">40+</strong><span data-edit="label-3">品牌接入</span></div>
  </div>
</section>
```

## Chart

See `charts.md` for the data and the choice of chart.

```html
<section class="slide" id="bookings-rising">
  <h2 data-edit="title">预约量持续上升</h2>
  <figure class="chart">
    <script type="application/json">{"type": "column", "categories": ["7 月", "8 月", "9 月"], "series": [{"name": "预约（万）", "values": [3.2, 5.8, 9.1]}]}</script>
    <figcaption data-edit="source">数据截至 9 月 25 日</figcaption>
  </figure>
</section>
```

## Image

The picture is a file inside the deck's folder, such as `images/product.png`, with `alt` text saying what it shows. Nothing is loaded from the internet.

```html
<section class="slide" id="product-look">
  <h2 data-edit="title">产品外观</h2>
  <figure class="image"><img src="images/product.png" alt="产品正面"><figcaption data-edit="caption">哑光白与石墨灰两色</figcaption></figure>
</section>
```

## Quote

```html
<section class="slide quote" id="member-of-family">
  <blockquote data-edit="quote">它不是另一个遥控器，而是家里的一位成员。</blockquote>
  <cite data-edit="who">产品负责人</cite>
</section>
```

## Section

Opens a part of the talk. Separate from the part-of-the-talk label (`"section"` on a slide in `deck.json`), which is a small line at the foot of the slides that follow; use the layout for a title page, the label for the foot line, or both.

```html
<section class="slide section" id="launch-and-price">
  <h1 data-edit="title">上市与价格</h1>
  <p data-edit="subtitle">限量首发</p>
</section>
```

## Closing

```html
<section class="slide closing" id="thanks">
  <h1 data-edit="title">谢谢</h1>
  <p data-edit="subtitle">欢迎体验</p>
</section>
```
