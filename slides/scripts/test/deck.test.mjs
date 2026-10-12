import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync, writeFileSync, statSync, utimesSync } from 'node:fs';
import { join } from 'node:path';
import { checkDeck, buildDeck } from '../lib/deck.mjs';
import { makeDeck, basicFiles, bullets, cover, withDeck } from './helpers.mjs';

const messages = (result) => result.errors.map((e) => (e.slide ? `${e.slide}: ` : '') + e.message);
const has = (result, pattern) => messages(result).some((m) => pattern.test(m));

test('a valid deck builds index.html in the order of deck.json', () => {
  const { deck } = makeDeck(basicFiles());
  const result = buildDeck(deck);
  assert.deepEqual(messages(result), []);
  const html = readFileSync(join(deck, 'index.html'), 'utf8');
  assert.match(html, /<html lang="zh">/);
  assert.match(html, /<title>让家，更懂你<\/title>/);
  assert.match(html, /<link rel="stylesheet" href="lib\/deck\.css">/);
  assert.match(html, /<script src="lib\/deck\.js"><\/script>/);
  assert.ok(html.indexOf('id="cover"') < html.indexOf('id="why-now"'));
  assert.match(html, /<section class="slide cover" id="cover" data-source="slides\/cover\.html">/);
  assert.match(html, /data-edit="point-2">操作越来越复杂/);
});

test('building twice gives the same file', () => {
  const { deck } = makeDeck(basicFiles());
  buildDeck(deck);
  const first = readFileSync(join(deck, 'index.html'), 'utf8');
  buildDeck(deck);
  assert.equal(readFileSync(join(deck, 'index.html'), 'utf8'), first);
});

test('changing one slide file changes only that slide in index.html and never touches the other slide files', () => {
  const { deck } = makeDeck(basicFiles());
  buildDeck(deck);
  const before = readFileSync(join(deck, 'index.html'), 'utf8');
  const coverPath = join(deck, 'slides/cover.html');
  const old = new Date(2020, 0, 1);
  utimesSync(coverPath, old, old);
  writeFileSync(join(deck, 'slides/why-now.html'), bullets('why-now').replace('设备越来越多', '设备多得数不过来'));
  buildDeck(deck);
  const after = readFileSync(join(deck, 'index.html'), 'utf8');
  const lines = (s) => s.split('\n');
  const changed = lines(after).filter((line, i) => line !== lines(before)[i]);
  assert.equal(changed.length, 1);
  assert.match(changed[0], /设备多得数不过来/);
  assert.equal(statSync(coverPath).mtimeMs, old.getTime());
});

test('a deck with errors does not touch an existing index.html', () => {
  const { deck } = makeDeck(basicFiles());
  buildDeck(deck);
  const before = readFileSync(join(deck, 'index.html'), 'utf8');
  writeFileSync(join(deck, 'slides/why-now.html'), '<section class="slide" id="other"><h2 data-edit="t">x</h2></section>');
  const result = buildDeck(deck);
  assert.equal(result.ok, false);
  assert.equal(readFileSync(join(deck, 'index.html'), 'utf8'), before);
});

test('sections: a label on a slide carries to the slides after it', () => {
  const files = basicFiles();
  files['deck.json'].slides[0].section = '开场';
  files['deck.json'].slides[1].section = '产品';
  const { deck } = makeDeck(files);
  buildDeck(deck);
  const html = readFileSync(join(deck, 'index.html'), 'utf8');
  assert.match(html, /id="cover" data-source="slides\/cover\.html" data-section="开场"/);
  assert.match(html, /id="why-now" data-source="slides\/why-now\.html" data-section="产品"/);
});

test('a section label stays on the slides after it until the next label', () => {
  const files = basicFiles({ 'slides/third-one.html': bullets('third-one') });
  files['deck.json'].slides.push({ id: 'third-one' });
  files['deck.json'].slides[1].section = '产品';
  const { deck } = makeDeck(files);
  buildDeck(deck);
  const html = readFileSync(join(deck, 'index.html'), 'utf8');
  assert.match(html, /id="third-one" data-source="slides\/third-one\.html" data-section="产品"/);
  assert.doesNotMatch(html, /id="cover"[^>]*data-section/);
});

test('file defaults to slides/<id>.html', () => {
  const files = basicFiles();
  delete files['deck.json'].slides[1].file;
  const { deck } = makeDeck(files);
  assert.deepEqual(messages(checkDeck(deck)), []);
});

// deck.json
test('deck.json missing, broken, without title or without slides', () => {
  const missing = makeDeck({});
  assert.ok(has(checkDeck(missing.deck), /deck\.json.*not found/));
  const broken = makeDeck({ 'deck.json': '{oops' });
  assert.ok(has(checkDeck(broken.deck), /deck\.json is not valid/));
  const noTitle = makeDeck({ 'deck.json': { slides: [{ id: 'cover' }] } });
  assert.ok(has(checkDeck(noTitle.deck), /title/));
  const noSlides = makeDeck({ 'deck.json': { title: 'x', slides: [] } });
  assert.ok(has(checkDeck(noSlides.deck), /at least one slide/));
});

test('lib/deck.css and lib/deck.js must be in the deck folder', () => {
  const { deck } = makeDeck(basicFiles(), { lib: false });
  assert.ok(has(checkDeck(deck), /lib\/deck\.css.*skill_copy/));
});

// ids and files
test('ids must be unique', () => {
  const files = basicFiles();
  files['deck.json'].slides[1].id = 'cover';
  const { deck } = makeDeck(files);
  assert.ok(has(checkDeck(deck), /id "cover" is used twice/));
});

test('ids must say what the slide is about, not a number', () => {
  for (const id of ['slide-1', 'page2', '3', 's4', 'slide3']) {
    const files = basicFiles({ [`slides/${id}.html`]: bullets(id) });
    files['deck.json'].slides.push({ id });
    const { deck } = makeDeck(files);
    assert.ok(has(checkDeck(deck), /by number|numbered|not a number/), id);
  }
});

test('ids are lowercase letters, digits and hyphens', () => {
  for (const id of ['Why Now', 'why_now', '为什么', '-a', 'a--b']) {
    const files = basicFiles();
    files['deck.json'].slides[1] = { id, file: 'slides/why-now.html' };
    const { deck } = makeDeck(files);
    assert.ok(has(checkDeck(deck), /lowercase/), id);
  }
});

test('every listed file must exist', () => {
  const files = basicFiles();
  files['deck.json'].slides.push({ id: 'pricing' });
  const { deck } = makeDeck(files);
  assert.ok(has(checkDeck(deck), /pricing: .*slides\/pricing\.html.*does not exist/));
});

test('files must be .html files inside slides/', () => {
  for (const file of ['../secret.html', '/etc/passwd.html', 'other/x.html', 'slides/x.txt', 'slides/../x.html']) {
    const files = basicFiles();
    files['deck.json'].slides[1].file = file;
    const { deck } = makeDeck(files);
    assert.ok(has(checkDeck(deck), /why-now: file/), file);
  }
});

test('two slides may not share a file', () => {
  const files = basicFiles();
  files['deck.json'].slides.push({ id: 'again', file: 'slides/why-now.html' });
  const { deck } = makeDeck(files);
  assert.ok(has(checkDeck(deck), /again: .*already used by why-now/));
});

test('a file in slides/ that deck.json does not list is a warning', () => {
  const { deck } = makeDeck(basicFiles({ 'slides/leftover.html': bullets('leftover') }));
  const result = checkDeck(deck);
  assert.equal(result.ok, true);
  assert.ok(result.warnings.some((w) => /slides\/leftover\.html.*not listed/.test(w.message)));
});

// the section element
test('the section id must match the id in deck.json', () => {
  const { deck } = withDeck((f) => { f['slides/why-now.html'] = bullets('other'); });
  assert.ok(has(checkDeck(deck), /why-now: .*id="other".*id="why-now"/));
});

test('the file holds exactly one section with class slide', () => {
  const two = withDeck((f) => { f['slides/why-now.html'] = bullets('why-now') + bullets('again'); });
  assert.ok(has(checkDeck(two.deck), /why-now: .*exactly one/));
  const wrong = withDeck((f) => { f['slides/why-now.html'] = '<div id="why-now"><h2 data-edit="t">x</h2></div>'; });
  assert.ok(has(checkDeck(wrong.deck), /why-now: .*<section/));
  const noClass = withDeck((f) => { f['slides/why-now.html'] = '<section id="why-now"><h2 data-edit="t">x</h2></section>'; });
  assert.ok(has(checkDeck(noClass.deck), /why-now: .*class="slide/));
  const stray = withDeck((f) => { f['slides/why-now.html'] = bullets('why-now') + 'loose words'; });
  assert.ok(has(checkDeck(stray.deck), /why-now: .*outside the section/));
});

test('unclosed tags are reported with the slide and line', () => {
  const { deck } = withDeck((f) => { f['slides/why-now.html'] = '<section class="slide" id="why-now">\n<h2 data-edit="t">x</h2>\n<ul>\n</section>'; });
  assert.ok(has(checkDeck(deck), /why-now: line 3: <ul> is never closed/));
});

// data-edit
test('every text element needs data-edit', () => {
  const { deck } = withDeck((f) => { f['slides/why-now.html'] = '<section class="slide" id="why-now"><h2 data-edit="title">x</h2><p>no marker</p></section>'; });
  assert.ok(has(checkDeck(deck), /why-now: line 1: <p> holds text but has no data-edit/));
});

test('text straight inside a div is reported with advice to wrap it', () => {
  const { deck } = withDeck((f) => { f['slides/why-now.html'] = '<section class="slide" id="why-now"><h2 data-edit="title">x</h2><div class="note">loose</div></section>'; });
  assert.ok(has(checkDeck(deck), /why-now: .*<div> holds text.*wrap/));
});

test('inline tags inside a data-edit element are part of it', () => {
  const { deck } = withDeck((f) => { f['slides/why-now.html'] = '<section class="slide" id="why-now"><h2 data-edit="title">a <b>bold</b> <em>word</em></h2></section>'; });
  assert.deepEqual(messages(checkDeck(deck)), []);
});

test('data-edit values are unique within a slide, but may repeat across slides', () => {
  const dup = withDeck((f) => { f['slides/why-now.html'] = '<section class="slide" id="why-now"><h2 data-edit="title">x</h2><p data-edit="title">y</p></section>'; });
  assert.ok(has(checkDeck(dup.deck), /why-now: .*data-edit="title" is used twice/));
  const across = makeDeck(basicFiles());
  assert.deepEqual(messages(checkDeck(across.deck)), []);
});

test('data-edit must not be empty, odd, or nested', () => {
  const empty = withDeck((f) => { f['slides/why-now.html'] = '<section class="slide" id="why-now"><h2 data-edit="">x</h2></section>'; });
  assert.ok(has(checkDeck(empty.deck), /data-edit.*lowercase/));
  const odd = withDeck((f) => { f['slides/why-now.html'] = '<section class="slide" id="why-now"><h2 data-edit="Title 1">x</h2></section>'; });
  assert.ok(has(checkDeck(odd.deck), /data-edit.*lowercase/));
  const nested = withDeck((f) => { f['slides/why-now.html'] = '<section class="slide" id="why-now"><ul data-edit="list"><li data-edit="a">x</li></ul></section>'; });
  assert.ok(has(checkDeck(nested.deck), /data-edit="a" is inside data-edit="list"/));
});

test('chart script text and styles are not text elements', () => {
  const chart = `<section class="slide" id="why-now"><h2 data-edit="title">x</h2><figure class="chart"><script type="application/json">{"type":"column","categories":["a"],"series":[{"name":"s","values":[1]}]}</script><figcaption data-edit="source">来源</figcaption></figure></section>`;
  const { deck } = withDeck((f) => { f['slides/why-now.html'] = chart; });
  assert.deepEqual(messages(checkDeck(deck)), []);
});

// what slides may not carry
test('own scripts, styles and links are not allowed', () => {
  for (const [bad, pattern] of [
    ['<script>alert(1)</script>', /<script>/],
    ['<style>p{color:red}</style>', /<style>/],
    ['<link rel="stylesheet" href="x.css">', /<link>/],
    ['<p data-edit="p" onclick="x()">t</p>', /onclick/],
    ['<a data-edit="a" href="javascript:alert(1)">t</a>', /javascript:/],
  ]) {
    const { deck } = withDeck((f) => { f['slides/why-now.html'] = `<section class="slide" id="why-now"><h2 data-edit="title">x</h2>${bad}</section>`; });
    assert.ok(has(checkDeck(deck), pattern), bad);
  }
});

test('nothing is loaded from the network', () => {
  for (const bad of ['<img src="https://example.com/a.png" alt="x">', '<img src="//example.com/a.png" alt="x">', '<a data-edit="a" href="http://example.com">t</a>']) {
    const { deck } = withDeck((f) => { f['slides/why-now.html'] = `<section class="slide" id="why-now"><h2 data-edit="title">x</h2>${bad}</section>`; });
    assert.ok(has(checkDeck(deck), /network|internet/), bad);
  }
});

test('an image must be a file in the deck folder', () => {
  const html = (src) => `<section class="slide" id="why-now"><h2 data-edit="title">x</h2><figure class="image"><img src="${src}" alt="x"></figure></section>`;
  const missing = withDeck((f) => { f['slides/why-now.html'] = html('images/a.png'); });
  assert.ok(has(checkDeck(missing.deck), /why-now: .*images\/a\.png.*does not exist/));
  const present = withDeck((f) => { f['slides/why-now.html'] = html('images/a.png'); f['images/a.png'] = 'png'; });
  assert.deepEqual(messages(checkDeck(present.deck)), []);
  const outside = withDeck((f) => { f['slides/why-now.html'] = html('../../etc/hosts'); });
  assert.ok(has(checkDeck(outside.deck), /why-now: .*inside the deck folder/));
});

test('an image needs alt text', () => {
  const { deck } = withDeck((f) => { f['slides/why-now.html'] = '<section class="slide" id="why-now"><h2 data-edit="title">x</h2><img src="a.png"></section>'; f['a.png'] = 'x'; });
  assert.ok(has(checkDeck(deck), /<img> needs alt/));
});

// charts
test('charts: invalid JSON and values that do not fit are errors', () => {
  const chart = (json) => `<section class="slide" id="why-now"><h2 data-edit="title">x</h2><figure class="chart"><script type="application/json">${json}</script></figure></section>`;
  const bad = withDeck((f) => { f['slides/why-now.html'] = chart('{nope'); });
  assert.ok(has(checkDeck(bad.deck), /why-now: chart.*not valid JSON/));
  const fewer = withDeck((f) => { f['slides/why-now.html'] = chart('{"type":"column","categories":["a","b"],"series":[{"name":"s","values":[1]}]}'); });
  assert.ok(has(checkDeck(fewer.deck), /why-now: chart.*one value per category/));
  const type = withDeck((f) => { f['slides/why-now.html'] = chart('{"type":"donut","categories":["a"],"series":[{"name":"s","values":[1]}]}'); });
  assert.ok(has(checkDeck(type.deck), /why-now: chart.*type/));
  const missing = withDeck((f) => { f['slides/why-now.html'] = '<section class="slide" id="why-now"><h2 data-edit="title">x</h2><figure class="chart"></figure></section>'; });
  assert.ok(has(checkDeck(missing.deck), /why-now: chart.*script/));
});

// theme
test('theme colours and font become a style block that wins over dark mode', () => {
  const files = basicFiles();
  files['deck.json'].theme = { mode: 'dark', accent: '#0a7d5a', ink: '#101820', font: "'Noto Serif SC', serif", chart: ['#0a7d5a', '#e0a019'] };
  const { deck } = makeDeck(files);
  const result = buildDeck(deck);
  assert.deepEqual(messages(result), []);
  const html = readFileSync(join(deck, 'index.html'), 'utf8');
  assert.match(html, /<body class="dark themed">/);
  assert.match(html, /<style id="deck-theme">\s*body\.themed \{[^}]*--accent: #0a7d5a;[^}]*--ink: #101820;[^}]*--font: 'Noto Serif SC', serif;[^}]*--chart-1: #0a7d5a;[^}]*--chart-2: #e0a019;/);
  assert.match(html, /--accent-soft: #[0-9a-f]{6};/);
});

test('without a theme there is no style block and the body is plain', () => {
  const { deck } = makeDeck(basicFiles());
  buildDeck(deck);
  const html = readFileSync(join(deck, 'index.html'), 'utf8');
  assert.doesNotMatch(html, /deck-theme/);
  assert.match(html, /<body>/);
});

test('theme values that are not plain colours or font names are refused', () => {
  for (const theme of [{ accent: 'red; } body { display:none' }, { accent: 'url(http://x)' }, { font: 'x; } </style><script>' }, { mode: 'blue' }, { chart: ['#fff', 'nope'] }, { colour: '#fff' }]) {
    const files = basicFiles();
    files['deck.json'].theme = theme;
    const { deck } = makeDeck(files);
    assert.equal(checkDeck(deck).ok, false, JSON.stringify(theme));
  }
});

test('a pale accent warns because the cover text is white', () => {
  const files = basicFiles();
  files['deck.json'].theme = { accent: '#ffe08a' };
  const { deck } = makeDeck(files);
  const result = checkDeck(deck);
  assert.equal(result.ok, true);
  assert.ok(result.warnings.some((w) => /contrast/.test(w.message)));
});

// warnings about writing
test('more than five bullets, a missing title and a first slide that is not a cover warn', () => {
  const many = '<section class="slide" id="why-now"><ul>' + Array.from({ length: 6 }, (_, i) => `<li data-edit="p-${i}">x</li>`).join('') + '</ul></section>';
  const files = basicFiles({ 'slides/why-now.html': many });
  files['deck.json'].slides.reverse();
  const { deck } = makeDeck(files);
  const result = checkDeck(deck);
  assert.equal(result.ok, true);
  const text = result.warnings.map((w) => w.message).join('\n');
  assert.match(text, /6 bullets/);
  assert.match(text, /no <h2>/);
  assert.match(text, /first slide/);
});

// the command line
test('the command line prints every problem and exits 1; a good deck exits 0', async () => {
  const { spawnSync } = await import('node:child_process');
  const script = new URL('../build.mjs', import.meta.url).pathname;
  const bad = withDeck((f) => { f['slides/why-now.html'] = '<section class="slide" id="x"><p>t</p></section>'; });
  const failed = spawnSync(process.execPath, [script, 'build', bad.deck], { encoding: 'utf8' });
  assert.equal(failed.status, 1);
  assert.match(failed.stdout, /ERROR why-now: /);
  assert.ok(!existsSync(join(bad.deck, 'index.html')));
  const good = makeDeck(basicFiles());
  const done = spawnSync(process.execPath, [script, 'build', good.deck], { encoding: 'utf8' });
  assert.equal(done.status, 0);
  assert.match(done.stdout, /OK: 2 slides/);
  assert.ok(existsSync(join(good.deck, 'index.html')));
  const checked = makeDeck(basicFiles());
  const only = spawnSync(process.execPath, [script, 'check', checked.deck], { encoding: 'utf8' });
  assert.equal(only.status, 0);
  assert.ok(!existsSync(join(checked.deck, 'index.html')));
  const usage = spawnSync(process.execPath, [script], { encoding: 'utf8' });
  assert.equal(usage.status, 2);
});

// The examples in the reference pass the checks they describe.
test('every slide example in references/layouts.md builds without errors', async () => {
  const { readFileSync: read } = await import('node:fs');
  const text = read(new URL('../../references/layouts.md', import.meta.url), 'utf8');
  const blocks = [...text.matchAll(/```html\n([\s\S]*?)```/g)].map((m) => m[1]).filter((b) => b.startsWith('<section'));
  assert.ok(blocks.length >= 9);
  const files = { 'images/product.png': 'png', 'deck.json': { title: 'Layouts', slides: [] } };
  for (const block of blocks) {
    const id = /id="([^"]+)"/.exec(block)[1];
    files[`slides/${id}.html`] = block;
    files['deck.json'].slides.push({ id });
  }
  const { deck } = makeDeck(files);
  const result = buildDeck(deck);
  assert.deepEqual(messages(result), []);
  assert.equal(result.slides.length, blocks.length);
});
