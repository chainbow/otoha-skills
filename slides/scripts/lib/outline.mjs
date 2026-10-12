// Turns a checked deck into the outline the pptx skill builds a PowerPoint file from, so one set of
// slides can go either way. Layouts that PowerPoint has no counterpart for are simplified to bullets.

import { decodeEntities, elements, textOf } from './html.mjs';

const clean = (node) => decodeEntities(textOf(node)).replace(/\s+/g, ' ').trim();
const hasClass = (element, name) => (element.attrs.class || '').split(/\s+/).includes(name);
const all = (root, test) => [...elements(root.children)].filter(test);
const first = (root, test) => all(root, test)[0];
const bulletsOf = (root) => all(root, (e) => e.tag === 'li').map(clean).filter(Boolean);

function posix(folder, file) {
  const parts = `${folder.replace(/\\/g, '/')}/${file}`.split('/').filter((p) => p && p !== '.');
  const out = [];
  for (const part of parts) {
    if (part === '..') out.pop();
    else out.push(part);
  }
  return out.join('/');
}

function convert(slide, folder, notes) {
  const root = slide.section_;
  const title = (tag) => { const e = first(root, (x) => x.tag === tag); return e ? clean(e) : ''; };
  const note = first(root, (e) => e.tag === 'aside' && hasClass(e, 'notes'));
  const result = (spec) => (note ? { ...spec, notes: clean(note) } : spec);
  const paragraphs = all(root, (e) => e.tag === 'p' && !hasClass(e, 'lead') && !hasClass(e, 'eyebrow')).map(clean).filter(Boolean);

  if (hasClass(root, 'cover')) {
    const eyebrow = first(root, (e) => hasClass(e, 'eyebrow'));
    const subtitle = [eyebrow && clean(eyebrow), ...paragraphs].filter(Boolean).join(' · ');
    return result({ layout: 'cover', title: title('h1'), ...(subtitle ? { subtitle } : {}) });
  }
  for (const layout of ['section', 'closing']) {
    if (hasClass(root, layout)) return result({ layout, title: title('h1'), ...(paragraphs[0] ? { subtitle: paragraphs[0] } : {}) });
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
    return result({ layout: 'stats', title: heading, stats: items });
  }
  const chart = first(root, (e) => e.tag === 'figure' && hasClass(e, 'chart'));
  if (chart) {
    const data = first(chart, (e) => e.tag === 'script');
    const caption = first(chart, (e) => e.tag === 'figcaption');
    return result({ layout: 'chart', title: heading, chart: JSON.parse(textOf(data)), ...(caption ? { caption: clean(caption) } : {}) });
  }
  const image = first(root, (e) => e.tag === 'figure' && hasClass(e, 'image'));
  if (image) {
    const picture = first(image, (e) => e.tag === 'img');
    const caption = first(image, (e) => e.tag === 'figcaption');
    return result({ layout: 'image', title: heading, image: posix(folder, picture.attrs.src), ...(caption ? { caption: clean(caption) } : {}) });
  }
  const columns = first(root, (e) => hasClass(e, 'columns'));
  if (columns) {
    const sides = columns.children.filter((c) => c.type === 'element').slice(0, 2).map((side) => {
      const h = first(side, (e) => e.tag === 'h3');
      return { heading: h ? clean(h) : '', bullets: bulletsOf(side) };
    });
    if (sides.length === 2) return result({ layout: 'two-column', title: heading, left: sides[0], right: sides[1] });
  }

  const lead = first(root, (e) => e.tag === 'p' && hasClass(e, 'lead'));
  let bullets = bulletsOf(root);
  const plain = bullets.length > 0 && !first(root, (e) => e.tag === 'figure' || (e.tag === 'div' && !hasClass(e, 'stat')));
  if (!plain) {
    bullets = [...bullets, ...paragraphs];
    notes.push(`${slide.id}: simplified to bullets; PowerPoint has no matching layout, so check how it reads.`);
  }
  if (lead) bullets = [clean(lead), ...bullets];
  return result({ layout: 'bullets', title: heading, bullets });
}

/** { outline, notes }: the outline object and what had to be simplified. `folder` is the deck's folder in the project. */
export function pptxOutline(checked, folder) {
  const notes = [];
  const slides = checked.slides.map((slide) => convert(slide, folder, notes));
  return { outline: { title: checked.deck.title, slides }, notes };
}
