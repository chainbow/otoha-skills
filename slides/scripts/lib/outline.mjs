// Turns a checked deck into the outline the pptx skill builds a PowerPoint file from, so one set of
// slides can go either way. Layouts that PowerPoint has no counterpart for are simplified to bullets.

import { decodeEntities, elements, textOf } from './html.mjs';

const clean = (node) => decodeEntities(textOf(node)).replace(/\s+/g, ' ').trim();
const hasClass = (element, name) => (element.attrs.class || '').split(/\s+/).includes(name);
const all = (root, test) => [...elements(root.children)].filter(test);
const first = (root, test) => all(root, test)[0];
const hex = (colour) => colour.length === 4 ? '#' + [...colour.slice(1)].map(c => c + c).join('').toLowerCase() : colour.toLowerCase();

// Preserve custom visible text in reading order; notes and chart data are never slide bullets.
function visibleBullets(root, skipHeadings = false, omitted = new Set()) {
  const lines = [];
  const visit = (node) => {
    if (node.type === 'text') {
      const value = decodeEntities(node.text).replace(/\s+/g, ' ').trim();
      if (value) lines.push(value);
      return;
    }
    if (omitted.has(node)) return;
    if (node.tag === 'script' || (node.tag === 'aside' && hasClass(node, 'notes')) || ['h1', 'h2'].includes(node.tag) || (skipHeadings && node.tag === 'h3') || hasClass(node, 'lead') || hasClass(node, 'eyebrow')) return;
    if (['li', 'p', 'h3', 'blockquote', 'figcaption'].includes(node.tag)) {
      const value = clean(node);
      if (value) lines.push(value);
    } else for (const child of node.children || []) visit(child);
  };
  for (const child of root.children || []) visit(child);
  return lines;
}

function posix(folder, file) {
  const parts = `${folder.replace(/\\/g, '/')}/${file}`.split('/').filter((p) => p && p !== '.');
  const out = [];
  for (const part of parts) {
    if (part === '..') out.pop();
    else out.push(part);
  }
  return out.join('/');
}

function convert(slide, folder, notes, index) {
  const root = slide.section_;
  const title = (tag) => { const e = first(root, (x) => x.tag === tag); return e ? clean(e) : ''; };
  const note = first(root, (e) => e.tag === 'aside' && hasClass(e, 'notes'));
  const result = (spec, consumed) => {
    const extra = consumed ? visibleBullets(root, false, new Set(consumed)) : [];
    const lead = consumed && first(root, (e) => e.tag === 'p' && hasClass(e, 'lead'));
    if (lead) extra.unshift(clean(lead));
    if (extra.length) notes.push(`Page ${index + 1} (${slide.id}): simplified ${spec.layout} export; additional body text moved to speaker notes. Check this page before presenting.`);
    const combined = [note && clean(note), ...extra].filter(Boolean).join('\n\n');
    return combined ? { ...spec, notes: combined } : spec;
  };
  const paragraphs = all(root, (e) => e.tag === 'p' && !hasClass(e, 'lead') && !hasClass(e, 'eyebrow')).map(clean).filter(Boolean);

  if (hasClass(root, 'cover')) {
    const eyebrow = first(root, (e) => hasClass(e, 'eyebrow'));
    const subtitle = [eyebrow && clean(eyebrow), ...paragraphs].filter(Boolean).join(' · ');
    return result({ layout: 'cover', title: title('h1'), ...(subtitle ? { subtitle } : {}) });
  }
  for (const layout of ['section', 'closing']) {
    if (hasClass(root, layout)) return result({ layout, title: title('h1'), ...(paragraphs.length ? { subtitle: paragraphs.join(' · ') } : {}) });
  }
  if (hasClass(root, 'quote')) {
    const quote = first(root, (e) => e.tag === 'blockquote');
    const cite = first(root, (e) => e.tag === 'cite');
    return result({ layout: 'quote', title: quote ? clean(quote) : '', ...(cite ? { subtitle: clean(cite) } : {}) });
  }

  const heading = title('h2');
  const stats = first(root, (e) => hasClass(e, 'stats'));
  if (stats) {
    const items = all(stats, (e) => hasClass(e, 'stat')).map((stat) => ({
      value: clean(first(stat, (e) => e.tag === 'strong') || stat),
      label: clean(first(stat, (e) => e.tag === 'span') || { type: 'text', text: '' }),
    }));
    return result({ layout: 'stats', title: heading, stats: items }, [stats]);
  }
  const chart = first(root, (e) => e.tag === 'figure' && hasClass(e, 'chart'));
  if (chart) {
    const data = first(chart, (e) => e.tag === 'script');
    const caption = first(chart, (e) => e.tag === 'figcaption');
    return result({ layout: 'chart', title: heading, chart: JSON.parse(textOf(data)), ...(caption ? { caption: clean(caption) } : {}) }, [chart]);
  }
  const image = first(root, (e) => e.tag === 'figure' && hasClass(e, 'image'));
  if (image) {
    const picture = first(image, (e) => e.tag === 'img');
    const caption = first(image, (e) => e.tag === 'figcaption');
    return result({ layout: 'image', title: heading, image: posix(folder, picture.attrs.src), ...(caption ? { caption: clean(caption) } : {}) }, [image]);
  }
  const columns = first(root, (e) => hasClass(e, 'columns'));
  if (columns) {
    const sides = columns.children.filter((c) => c.type === 'element').map((side) => {
      const h = first(side, (e) => e.tag === 'h3');
      return { heading: h ? clean(h) : '', bullets: visibleBullets(side, true) };
    });
    if (sides.length === 2) return result({ layout: 'two-column', title: heading, left: sides[0], right: sides[1] }, [columns]);
  }

  const lead = first(root, (e) => e.tag === 'p' && hasClass(e, 'lead'));
  let bullets = visibleBullets(root);
  const plain = bullets.length > 0 && !first(root, (e) => e.tag === 'figure' || (e.tag === 'div' && !hasClass(e, 'stat')));
  if (!plain) {
    notes.push(`Page ${index + 1} (${slide.id}): simplified to bullets; PowerPoint has no matching layout, so check how it reads.`);
  }
  if (lead) bullets = [clean(lead), ...bullets];
  return result({ layout: 'bullets', title: heading, bullets });
}

// Same defaults as assets/deck.css. Resolve them here instead of passing CSS names to pptx.
const BASE = {
  light: { accent: '#5b57ef', soft: '#eeedfe', text: '#0f1115', muted: '#5d6471', line: '#e6e8ec', background: '#ffffff' },
  dark: { accent: '#8481ff', soft: '#1f1e3d', text: '#e9ebef', muted: '#8e95a2', line: '#2a2d35', background: '#111216' },
};
const FONTS = new Set(['Helvetica Neue', 'Arial', 'Aptos', 'Calibri', 'Georgia', 'Times New Roman', 'Courier New', 'PingFang SC', 'Hiragino Sans', 'Yu Gothic', 'Noto Sans CJK SC', 'Noto Sans JP', 'Noto Serif JP', 'sans-serif', 'serif', 'monospace']);

function themeOf(source = {}, notes) {
  const mode = source.mode || 'light';
  const colours = { ...BASE[mode] };
  for (const [from, to] of Object.entries({ accent: 'accent', accentSoft: 'soft', ink: 'text', muted: 'muted', line: 'line', paper: 'background' })) {
    if (source[from]) colours[to] = hex(source[from]);
  }
  // checkDeck derives the soft accent from an explicit brand colour, just as the preview does.
  if (source.accent && !source.accentSoft) {
    const mix = (i) => Math.round(parseInt(colours.accent.slice(i, i + 2), 16) * 0.12 + parseInt(colours.background.slice(i, i + 2), 16) * 0.88).toString(16).padStart(2, '0');
    colours.soft = `#${[1, 3, 5].map(mix).join('')}`;
  }
  let font = 'Helvetica Neue';
  if (source.font) {
    const stack = source.font.split(',').map(part => part.trim().replace(/^['"]|['"]$/g, ''));
    font = stack.find(part => FONTS.has(part)) || 'sans-serif';
    if (font !== stack[0]) notes.push(`Theme font "${stack[0]}" is unavailable for editable PowerPoint; using "${font}". Check the exported typography.`);
  }
  return { mode, ...colours, headingFont: font, bodyFont: font, ...(source.chart ? { chart: source.chart.map(hex) } : {}) };
}

/** { outline, notes }: the outline object and what had to be simplified. `folder` is the deck's folder in the project. */
export function pptxOutline(checked, folder) {
  const notes = [];
  const theme = themeOf(checked.deck.theme, notes);
  const slides = checked.slides.map((slide, index) => convert(slide, folder, notes, index));
  return { outline: { title: checked.deck.title, theme, slides }, notes };
}
