import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { checkDeck } from '../lib/deck.mjs';
import { pptxOutline } from '../lib/outline.mjs';
import { makeDeck, cover } from './helpers.mjs';

const slide = (id, classes, inner) => `<section class="slide${classes ? ' ' + classes : ''}" id="${id}">\n${inner}\n</section>\n`;

function deckOf(slides, extra = {}) {
  const files = { 'deck.json': { title: 'Demo', slides: slides.map(([id]) => ({ id })) }, ...extra };
  for (const [id, html] of slides) files[`slides/${id}.html`] = html;
  return makeDeck(files);
}

const outlineOf = (deck, folder = 'my-deck') => pptxOutline(checkDeck(deck), folder);

test('every layout of the deck maps to a layout of the pptx skill', () => {
  const chart = '{"type":"column","categories":["7月","8月"],"series":[{"name":"预约（万）","values":[3.2,5.8]}]}';
  const { deck } = deckOf([
    ['cover', cover()],
    ['intro', slide('intro', 'section', '<h1 data-edit="title">产品</h1><p data-edit="sub">先看现状</p>')],
    ['why-now', slide('why-now', '', '<h2 data-edit="title">为什么是现在</h2><ul><li data-edit="a">设备多</li><li data-edit="b">操作繁</li></ul><aside class="notes" data-edit="notes">讲稿在这里</aside>')],
    ['before-after', slide('before-after', '', '<h2 data-edit="title">以前与现在</h2><div class="columns"><div><h3 data-edit="l-h">以前</h3><ul><li data-edit="l-1">逐个打开</li></ul></div><div><h3 data-edit="r-h">现在</h3><ul><li data-edit="r-1">一句话</li><li data-edit="r-2">记住习惯</li></ul></div></div>')],
    ['numbers', slide('numbers', '', '<h2 data-edit="title">三个数字</h2><div class="stats"><div class="stat"><strong data-edit="v1">0.3 秒</strong><span data-edit="l1">唤醒</span></div><div class="stat"><strong data-edit="v2">2 天</strong><span data-edit="l2">续航</span></div></div>')],
    ['bookings', slide('bookings', '', `<h2 data-edit="title">预约量持续上升</h2><figure class="chart"><script type="application/json">${chart}</script><figcaption data-edit="source">数据截至 9 月 25 日</figcaption></figure>`)],
    ['look', slide('look', '', '<h2 data-edit="title">产品外观</h2><figure class="image"><img src="images/product.png" alt="正面"><figcaption data-edit="cap">哑光白</figcaption></figure>')],
    ['voice', slide('voice', 'quote', '<blockquote data-edit="quote">它是家里的一位成员。</blockquote><cite data-edit="who">产品负责人</cite>')],
    ['thanks', slide('thanks', 'closing', '<h1 data-edit="title">谢谢</h1><p data-edit="sub">欢迎体验</p>')],
  ], { 'images/product.png': 'png' });
  const { outline, notes } = outlineOf(deck);
  assert.deepEqual(notes, []);
  assert.equal(outline.title, 'Demo');
  const [c, s, b, two, st, ch, im, q, cl] = outline.slides;
  assert.deepEqual(c, { layout: 'cover', title: '让家，更懂你', subtitle: '2026 秋季' });
  assert.deepEqual(s, { layout: 'section', title: '产品', subtitle: '先看现状' });
  assert.deepEqual(b, { layout: 'bullets', title: '为什么是现在', bullets: ['设备多', '操作繁'], notes: '讲稿在这里' });
  assert.deepEqual(two, { layout: 'two-column', title: '以前与现在', left: { heading: '以前', bullets: ['逐个打开'] }, right: { heading: '现在', bullets: ['一句话', '记住习惯'] } });
  assert.deepEqual(st, { layout: 'stats', title: '三个数字', stats: [{ value: '0.3 秒', label: '唤醒' }, { value: '2 天', label: '续航' }] });
  assert.deepEqual(ch, { layout: 'chart', title: '预约量持续上升', chart: JSON.parse(chart), caption: '数据截至 9 月 25 日' });
  assert.deepEqual(im, { layout: 'image', title: '产品外观', image: 'my-deck/images/product.png', caption: '哑光白' });
  assert.deepEqual(q, { layout: 'quote', title: '它是家里的一位成员。', subtitle: '产品负责人' });
  assert.deepEqual(cl, { layout: 'closing', title: '谢谢', subtitle: '欢迎体验' });
});

test('text with inline tags and entities is flattened to plain words', () => {
  const { deck } = deckOf([['why-now', slide('why-now', '', '<h2 data-edit="t">A &amp; B</h2><ul><li data-edit="a">  one <b>two</b>\n  three </li></ul>')]]);
  const { outline } = outlineOf(deck);
  assert.equal(outline.slides[0].title, 'A & B');
  assert.deepEqual(outline.slides[0].bullets, ['one two three']);
});

test('a lead paragraph becomes the first bullet', () => {
  const { deck } = deckOf([['why-now', slide('why-now', '', '<h2 data-edit="t">Why</h2><p class="lead" data-edit="l">The short version</p><ul><li data-edit="a">one</li></ul>')]]);
  assert.deepEqual(outlineOf(deck).outline.slides[0].bullets, ['The short version', 'one']);
});

test('a slide that fits no layout is simplified to bullets and said so', () => {
  const { deck } = deckOf([['odd', slide('odd', '', '<h2 data-edit="t">Odd</h2><div class="x"><p data-edit="a">first</p><p data-edit="b">second</p></div>')]]);
  const { outline, notes } = outlineOf(deck);
  assert.deepEqual(outline.slides[0], { layout: 'bullets', title: 'Odd', bullets: ['first', 'second'] });
  assert.match(notes[0], /odd.*simplified/);
});

test('the command line writes the outline file next to the deck', () => {
  const { deck } = deckOf([['cover', cover()]]);
  const script = new URL('../to-pptx-outline.mjs', import.meta.url).pathname;
  const run = spawnSync(process.execPath, [script, deck], { encoding: 'utf8' });
  assert.equal(run.status, 0, run.stdout + run.stderr);
  const outline = JSON.parse(readFileSync(join(deck, 'outline.json'), 'utf8'));
  assert.equal(outline.slides[0].layout, 'cover');
  assert.match(run.stdout, /outline\.json/);
});


for (const mode of ['light', 'dark']) {
  test(`outline carries resolved ${mode} colours and fonts to PowerPoint`, () => {
    const { deck } = deckOf([['cover', cover()]], {
      'deck.json': { title: 'Demo', theme: { mode, accent: '#123456', paper: '#203040', ink: '#fefdfc', font: "'Noto Sans JP', sans-serif", muted: '#abcdef', line: '#456789', accentSoft: '#345678', chart: ['#654321', '#987654'] }, slides: [{ id: 'cover' }] },
    });
    const { outline, notes } = outlineOf(deck);
    assert.deepEqual(outline.theme, { mode, accent: '#123456', background: '#203040', text: '#fefdfc', headingFont: 'Noto Sans JP', bodyFont: 'Noto Sans JP', muted: '#abcdef', line: '#456789', soft: '#345678', chart: ['#654321', '#987654'] });
    assert.deepEqual(notes, []);
  });
}

test('missing theme and dark mode resolve the colours actually used by the preview', () => {
  for (const [theme, expected] of [[undefined, ['light', '#ffffff', '#0f1115', '#5b57ef']], [{ mode: 'dark' }, ['dark', '#111216', '#e9ebef', '#8481ff']]]) {
    const { deck } = deckOf([['cover', cover()]], { 'deck.json': { title: 'Demo', ...(theme ? { theme } : {}), slides: [{ id: 'cover' }] } });
    const actual = outlineOf(deck).outline.theme;
    assert.deepEqual([actual.mode, actual.background, actual.text, actual.accent], expected);
    assert.equal(actual.headingFont, 'Helvetica Neue');
    assert.equal(actual.bodyFont, 'Helvetica Neue');
  }
});

test('font stacks choose a supported face or explain a family fallback', () => {
  for (const [font, face, warned] of [["'Hiragino Sans', sans-serif", 'Hiragino Sans', false], ["'Unknown Face', Georgia, serif", 'Georgia', true], ["'Unknown Serif', serif", 'serif', true], ["'Unknown Mono', monospace", 'monospace', true], ["'Unknown Face'", 'sans-serif', true]]) {
    const { deck } = deckOf([['cover', cover()]], { 'deck.json': { title: 'Demo', theme: { font }, slides: [{ id: 'cover' }] } });
    const { outline, notes } = outlineOf(deck);
    assert.equal(outline.theme.bodyFont, face);
    assert.equal(outline.theme.headingFont, face);
    assert.equal(notes.some(note => /font/i.test(note)), warned);
  }
});

test('fallback explanations identify the page number and preserve its speaker notes', () => {
  const { deck } = deckOf([['cover', cover()], ['custom', slide('custom', '', '<h2 data-edit="t">Custom</h2><div><p data-edit="a">A</p><p data-edit="b">B</p></div><aside class="notes" data-edit="n">Remember this</aside>')]]);
  const { outline, notes } = outlineOf(deck);
  assert.match(notes[0], /2.*custom.*simplified/);
  assert.equal(outline.slides[1].notes, 'Remember this');
});


test('three columns cannot silently lose their third column during export', () => {
  const html = '<h2 data-edit="title">Choices</h2><div class="columns">' + ['A', 'B', 'C'].map((v, i) => `<div><h3 data-edit="h${i}">${v}</h3><ul><li data-edit="v${i}">Option ${v}</li></ul></div>`).join('') + '</div>';
  const { deck } = deckOf([['choices', slide('choices', '', html)]]);
  const { outline, notes } = outlineOf(deck);
  assert.equal(outline.slides[0].layout, 'bullets');
  assert.deepEqual(outline.slides[0].bullets, ['A', 'Option A', 'B', 'Option B', 'C', 'Option C']);
  assert.match(notes[0], /1.*choices.*simplified/);
});


test('valid short web colours become six-digit colours accepted by pptx', () => {
  for (const extra of [{}, { accentSoft: '#abc' }]) {
    const { deck } = deckOf([['cover', cover()]], { 'deck.json': { title: 'Demo', theme: { accent: '#123', paper: '#fed', ink: '#012', muted: '#456', line: '#789', chart: ['#abc', '#def'], ...extra }, slides: [{ id: 'cover' }] } });
    const theme = outlineOf(deck).outline.theme;
    assert.equal(theme.accent, '#112233');
    assert.equal(theme.background, '#ffeedd');
    assert.equal(theme.text, '#001122');
    assert.equal(theme.muted, '#445566');
    assert.equal(theme.line, '#778899');
    assert.deepEqual(theme.chart, ['#aabbcc', '#ddeeff']);
    assert.match(theme.soft, /^#[a-f0-9]{6}$/);
    if (extra.accentSoft) assert.equal(theme.soft, '#aabbcc');
  }
});


test('paragraphs in two columns stay editable and never disappear', () => {
  const { deck } = deckOf([['compare', slide('compare', '', '<h2 data-edit="t">Compare</h2><div class="columns"><div><h3 data-edit="a">A</h3><p data-edit="b">Keep A</p></div><div><h3 data-edit="c">B</h3><p data-edit="d">Keep B</p></div></div>')]]);
  const { outline } = outlineOf(deck);
  assert.deepEqual(outline.slides[0].left.bullets, ['Keep A']);
  assert.deepEqual(outline.slides[0].right.bullets, ['Keep B']);
});

test('custom inline content survives fallback while speaker notes remain private', () => {
  const { deck } = deckOf([['custom', slide('custom', '', '<h2 data-edit="t">Custom</h2><div><span data-edit="a">Keep visible text</span></div><aside class="notes"><p data-edit="n">Speaker only</p></aside>')]]);
  const { outline, notes } = outlineOf(deck);
  assert.deepEqual(outline.slides[0].bullets, ['Keep visible text']);
  assert.equal(outline.slides[0].notes, 'Speaker only');
  assert.match(notes[0], /custom.*simplified/);
});


test('plain lists retain adjacent paragraphs without leaking nested speaker notes', () => {
  const { deck } = deckOf([['plain', slide('plain', '', '<h2 data-edit="t">Plain</h2><p data-edit="a">Keep context</p><ul><li data-edit="b">Keep item</li></ul><aside class="notes"><ul><li data-edit="n">Speaker only</li></ul></aside>')]]);
  const { outline } = outlineOf(deck);
  assert.deepEqual(outline.slides[0].bullets, ['Keep context', 'Keep item']);
  assert.equal(outline.slides[0].notes, 'Speaker only');
});


test('mixed chart pages explain where extra body text went and retain it in speaker notes', () => {
  const chart = '{"type":"column","categories":["A"],"series":[{"name":"Count","values":[3]}]}';
  const { deck } = deckOf([['mixed', slide('mixed', '', `<h2 data-edit="t">Results</h2><p class="lead" data-edit="l">Important context</p><p data-edit="detail">Do not lose this explanation</p><figure class="chart"><script type="application/json">${chart}</script><figcaption data-edit="source">Source</figcaption></figure><aside class="notes" data-edit="n">Original speaker note</aside>`)]]);
  const { outline, notes } = outlineOf(deck);
  assert.equal(outline.slides[0].layout, 'chart');
  assert.equal(outline.slides[0].caption, 'Source');
  assert.match(outline.slides[0].notes, /Original speaker note/);
  assert.match(outline.slides[0].notes, /Important context/);
  assert.match(outline.slides[0].notes, /Do not lose this explanation/);
  assert.match(notes[0], /1.*mixed.*speaker notes/);
});
