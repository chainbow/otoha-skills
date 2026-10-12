import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { after } from 'node:test';

const made = [];

/** A deck folder in a temporary place, with lib/ in it; `files` maps relative paths to text. Removed after the test file. */
export function makeDeck(files, { lib = true } = {}) {
  const root = mkdtempSync(join(tmpdir(), 'otoha-slides-test-'));
  made.push(root);
  const deck = join(root, 'deck');
  mkdirSync(deck);
  const all = lib ? { 'lib/deck.css': '/* css */', 'lib/deck.js': '/* js */', ...files } : files;
  for (const [name, content] of Object.entries(all)) {
    const path = join(deck, name);
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, typeof content === 'string' ? content : JSON.stringify(content));
  }
  return { root, deck };
}

after(() => { for (const root of made) rmSync(root, { recursive: true, force: true }); });

export const cover = (id = 'cover') =>
  `<section class="slide cover" id="${id}">\n  <p class="eyebrow" data-edit="eyebrow">2026 秋季</p>\n  <h1 data-edit="title">让家，更懂你</h1>\n</section>\n`;

export const bullets = (id) =>
  `<section class="slide" id="${id}">\n  <h2 data-edit="title">为什么是现在</h2>\n  <ul>\n    <li data-edit="point-1">设备越来越多</li>\n    <li data-edit="point-2">操作越来越复杂</li>\n  </ul>\n</section>\n`;

/** A valid two-slide deck, to change one thing in. */
export function basicFiles(extra = {}) {
  return {
    'deck.json': { title: '让家，更懂你', lang: 'zh', slides: [{ id: 'cover', file: 'slides/cover.html' }, { id: 'why-now', file: 'slides/why-now.html' }] },
    'slides/cover.html': cover(),
    'slides/why-now.html': bullets('why-now'),
    ...extra,
  };
}

export function withDeck(mutate) {
  const files = basicFiles();
  mutate(files);
  return makeDeck(files);
}
