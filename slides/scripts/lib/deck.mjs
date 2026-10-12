// Checks a deck folder (deck.json and slides/<id>.html) and puts it together as index.html.
// The same inputs always give the same file; nothing here reads the network or the clock.

import { existsSync, readFileSync, readdirSync, renameSync, writeFileSync } from 'node:fs';
import { isAbsolute, join, normalize, relative } from 'node:path';
import { parseHtml, decodeEntities, elements } from './html.mjs';

const CHART_TYPES = ['column', 'bar', 'line', 'pie', 'stacked'];
const THEME_KEYS = ['mode', 'accent', 'accentSoft', 'ink', 'muted', 'line', 'paper', 'font', 'chart'];
const THEME_VARIABLES = { accent: '--accent', accentSoft: '--accent-soft', ink: '--ink', muted: '--muted', line: '--line', paper: '--paper' };
const COLOR = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;
const FONT = /^[\p{L}\p{N} ,'"\-_.]{1,200}$/u;
const ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const NUMBERED_ID = /^(?:slide|page|s|p)?-?\d+$/;
const EDIT_NAME = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$/;
const NOT_ALLOWED_TAGS = { style: '<style>', link: '<link>', iframe: '<iframe>', object: '<object>', embed: '<embed>', base: '<base>', meta: '<meta>' };
const URL_ATTRIBUTES = ['src', 'href', 'poster', 'srcset', 'action', 'data'];
const BLOCK_TAGS = new Set(['div', 'section', 'figure', 'ul', 'ol', 'article', 'header', 'footer', 'main', 'aside', 'nav']);

const problem = (list, slide, message) => list.push(slide ? { slide, message } : { message });

/** Why a chart's data cannot be drawn, or null; the same rules as the deck's chart drawing. */
export function chartProblem(spec) {
  if (!spec || typeof spec !== 'object' || !CHART_TYPES.includes(spec.type)) return `type must be one of: ${CHART_TYPES.join(', ')}`;
  const { categories, series } = spec;
  if (!Array.isArray(categories) || !categories.length || !Array.isArray(series) || !series.length) return 'it needs categories and series';
  for (const item of series) {
    const values = item && item.values;
    if (!Array.isArray(values) || values.length !== categories.length) return 'each series needs one value per category';
    if (values.some((v) => typeof v !== 'number' || !Number.isFinite(v))) return 'values must be numbers';
  }
  if (spec.type === 'pie' && (series.length !== 1 || series[0].values.some((v) => v < 0))) return 'a pie chart has one series of values of 0 or more';
  return null;
}

// Colours -----------------------------------------------------------------------------------------------

function rgb(hex) {
  const h = hex.slice(1);
  const full = h.length === 3 ? [...h].map((c) => c + c).join('') : h;
  return [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16));
}

const toHex = (channels) => '#' + channels.map((c) => Math.round(c).toString(16).padStart(2, '0')).join('');

function luminance(hex) {
  const [r, g, b] = rgb(hex).map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrast(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

function mix(color, into, share) {
  const a = rgb(color);
  const b = rgb(into);
  return toHex(a.map((c, i) => c * share + b[i] * (1 - share)));
}

// The theme ---------------------------------------------------------------------------------------------

function checkTheme(theme, errors, warnings) {
  if (theme === undefined) return null;
  if (!theme || typeof theme !== 'object' || Array.isArray(theme)) {
    problem(errors, null, 'deck.json: theme must be an object such as {"accent": "#0a7d5a"}.');
    return null;
  }
  let ok = true;
  const fail = (message) => { ok = false; problem(errors, null, `deck.json: theme ${message}`); };
  for (const key of Object.keys(theme)) {
    if (!THEME_KEYS.includes(key)) fail(`has "${key}", which is not one of: ${THEME_KEYS.join(', ')}.`);
  }
  if (theme.mode !== undefined && theme.mode !== 'light' && theme.mode !== 'dark') fail('mode must be "light" or "dark".');
  for (const key of Object.keys(THEME_VARIABLES)) {
    if (theme[key] !== undefined && !(typeof theme[key] === 'string' && COLOR.test(theme[key]))) fail(`${key} must be a colour like #0a7d5a.`);
  }
  if (theme.font !== undefined && !(typeof theme.font === 'string' && FONT.test(theme.font))) fail('font must be font names such as "\'Noto Sans SC\', sans-serif".');
  if (theme.chart !== undefined) {
    if (!Array.isArray(theme.chart) || theme.chart.length > 5 || !theme.chart.every((c) => typeof c === 'string' && COLOR.test(c))) {
      fail('chart must be a list of up to 5 colours like ["#0a7d5a", "#e0a019"].');
    }
  }
  if (!ok) return null;

  const paper = theme.paper || (theme.mode === 'dark' ? '#111216' : '#ffffff');
  if (theme.accent) {
    if (contrast('#ffffff', theme.accent) < 4.5) {
      problem(warnings, null, `theme accent ${theme.accent} has low contrast (${contrast('#ffffff', theme.accent).toFixed(1)}:1) with the white text on the cover; choose a darker accent.`);
    }
  }
  if (theme.ink && contrast(theme.ink, paper) < 4.5) {
    problem(warnings, null, `theme ink ${theme.ink} has low contrast (${contrast(theme.ink, paper).toFixed(1)}:1) with the page colour; text may be hard to read.`);
  }
  const lines = [];
  for (const [key, variable] of Object.entries(THEME_VARIABLES)) {
    let value = theme[key];
    if (key === 'accentSoft' && value === undefined && theme.accent) value = mix(theme.accent, paper, 0.12);
    if (value !== undefined) lines.push(`${variable}: ${value.toLowerCase()};`);
  }
  if (theme.font) lines.push(`--font: ${theme.font};`);
  (theme.chart || []).forEach((color, i) => lines.push(`--chart-${i + 1}: ${color.toLowerCase()};`));
  return { dark: theme.mode === 'dark', lines };
}

// A slide -----------------------------------------------------------------------------------------------

function ownText(element) {
  return element.children.some((c) => c.type === 'text' && decodeEntities(c.text).trim() !== '');
}

function localFileProblem(value, deckDir) {
  if (isAbsolute(value) || value.startsWith('/')) return `"${value}" is not inside the deck folder; use a relative path such as images/photo.png`;
  const resolved = normalize(join(deckDir, value.split(/[?#]/)[0]));
  const inside = relative(deckDir, resolved);
  if (inside.startsWith('..') || isAbsolute(inside)) return `"${value}" is not inside the deck folder; use a relative path such as images/photo.png`;
  if (!existsSync(resolved)) return `"${value}" does not exist in the deck folder`;
  return null;
}

function checkSlide(entry, source, deckDir, errors, warnings) {
  const id = entry.id;
  const fail = (message) => problem(errors, id, message);
  const { nodes, errors: parseErrors } = parseHtml(source);
  for (const e of parseErrors) fail(`line ${e.line}: ${e.message}`);

  const loose = nodes.some((n) => n.type === 'text' && n.text.trim() !== '');
  const tops = nodes.filter((n) => n.type === 'element');
  if (loose) fail('there is text outside the section; everything belongs inside <section class="slide">.');
  if (tops.length !== 1) {
    fail(`the file must hold exactly one <section class="slide" id="${id}"> (it has ${tops.length} top-level elements).`);
    return null;
  }
  const section = tops[0];
  if (section.tag !== 'section') {
    fail(`the file must start with <section class="slide" id="${id}">, not <${section.tag}>.`);
    return null;
  }
  if (!(section.attrs.class || '').split(/\s+/).includes('slide')) fail('the <section> needs class="slide" (for example class="slide cover").');
  if (section.attrs.id !== id) fail(`the <section> has id="${section.attrs.id ?? ''}" but deck.json lists this slide as id="${id}"; they must match.`);

  const seen = new Map();
  const classes = (section.attrs.class || '').split(/\s+/);
  let hasTitle = false;

  const visit = (element, editAncestor, inChart) => {
    const tag = element.tag;
    const where = `line ${element.line}`;
    if (tag === 'h1' || tag === 'h2') hasTitle = true;

    if (tag === 'script') {
      const isChartData = inChart && element.attrs.type === 'application/json';
      if (!isChartData) fail(`${where}: <script> is not allowed in a slide; only a chart's data (<script type="application/json"> inside <figure class="chart">).`);
      return;
    }
    if (NOT_ALLOWED_TAGS[tag]) {
      fail(`${where}: ${NOT_ALLOWED_TAGS[tag]} is not allowed in a slide; the look comes from the deck's own style.`);
      return;
    }
    for (const [name, value] of Object.entries(element.attrs)) {
      if (name.startsWith('on')) fail(`${where}: ${name} is not allowed; slides carry no scripts.`);
      if (URL_ATTRIBUTES.includes(name)) {
        const v = value.trim().toLowerCase();
        if (v.startsWith('javascript:')) fail(`${where}: javascript: addresses are not allowed.`);
        else if (/^(?:[a-z][a-z0-9+.-]*:|\/\/)/.test(v) && !v.startsWith('data:image/') && !v.startsWith('mailto:')) {
          fail(`${where}: "${value}" would load from the internet; slides work without a network, so use a picture file in the deck folder.`);
        } else if (tag === 'img' && name === 'src' && !v.startsWith('data:')) {
          const trouble = localFileProblem(value.trim(), deckDir);
          if (trouble) fail(`${where}: <img> ${trouble}.`);
        }
      }
      if (name === 'style' && /url\(\s*['"]?\s*(?:https?:|\/\/)/i.test(value)) fail(`${where}: style would load from the internet.`);
    }
    if (tag === 'img' && element.attrs.alt === undefined) fail(`${where}: <img> needs alt="…" saying what the picture shows.`);

    let chartHere = inChart;
    if (tag === 'figure' && (element.attrs.class || '').split(/\s+/).includes('chart')) {
      chartHere = true;
      const data = element.children.find((c) => c.type === 'element' && c.tag === 'script' && c.attrs.type === 'application/json');
      if (!data) {
        fail('chart: <figure class="chart"> needs its data in a <script type="application/json"> inside it.');
      } else {
        let spec = null;
        try {
          spec = JSON.parse((data.children[0] && data.children[0].text) || '');
        } catch {
          fail('chart: the data is not valid JSON.');
          spec = undefined;
        }
        if (spec !== undefined) {
          const trouble = chartProblem(spec);
          if (trouble) fail(`chart: ${trouble}.`);
        }
      }
    }

    let edit = editAncestor;
    const marker = element.attrs['data-edit'];
    if (marker !== undefined) {
      if (!EDIT_NAME.test(marker)) {
        fail(`${where}: data-edit="${marker}" must be lowercase letters, digits and hyphens, starting with a letter (for example "title" or "point-1").`);
      } else if (editAncestor) {
        fail(`${where}: data-edit="${marker}" is inside data-edit="${editAncestor}"; mark only the outer element.`);
      } else if (seen.has(marker)) {
        fail(`${where}: data-edit="${marker}" is used twice in this slide (first at line ${seen.get(marker)}); give each text its own name.`);
      } else {
        seen.set(marker, element.line);
      }
      if (!editAncestor) edit = marker;
    } else if (!editAncestor && ownText(element)) {
      const advice = BLOCK_TAGS.has(tag) ? `; wrap it in a <p> or <span> with data-edit="a-short-name"` : `; add data-edit="a-short-name"`;
      fail(`${where}: <${tag}> holds text but has no data-edit${advice}.`);
    }
    for (const child of element.children) if (child.type === 'element') visit(child, edit, chartHere);
  };
  for (const child of section.children) if (child.type === 'element') visit(child, null, false);

  // Writing advice that does not stop the build.
  const kind = ['cover', 'section', 'closing'].find((k) => classes.includes(k));
  if (!hasTitle && !classes.includes('quote')) {
    problem(warnings, id, kind ? 'has no <h1> title.' : 'has no <h2> title; give the slide a title that says its point.');
  }
  for (const el of elements([section])) {
    if (el.tag === 'ul' || el.tag === 'ol') {
      const count = el.children.filter((c) => c.type === 'element' && c.tag === 'li').length;
      if (count > 5) problem(warnings, id, `has ${count} bullets; five or fewer read better, or split the slide.`);
    }
  }
  return { section, classes };
}

// The deck ----------------------------------------------------------------------------------------------

function readDeckJson(deckDir, errors) {
  const path = join(deckDir, 'deck.json');
  if (!existsSync(path)) {
    problem(errors, null, `deck.json not found in ${deckDir}.`);
    return null;
  }
  let deck;
  try {
    deck = JSON.parse(readFileSync(path, 'utf8'));
  } catch (error) {
    problem(errors, null, `deck.json is not valid JSON (${error.message}).`);
    return null;
  }
  if (!deck || typeof deck !== 'object' || Array.isArray(deck)) {
    problem(errors, null, 'deck.json must be an object with "title" and "slides".');
    return null;
  }
  return deck;
}

/** Checks the deck folder. `slides` carries what the build needs; `errors` stop the build, `warnings` do not. */
export function checkDeck(deckDir) {
  const errors = [];
  const warnings = [];
  const result = { ok: false, errors, warnings, deck: null, slides: [] };
  const deck = readDeckJson(deckDir, errors);
  if (!deck) return result;
  result.deck = deck;

  if (typeof deck.title !== 'string' || deck.title.trim() === '') problem(errors, null, 'deck.json needs a "title" (the deck\'s name, shown as the page title).');
  if (deck.lang !== undefined && !(typeof deck.lang === 'string' && /^[a-z]{2,3}(?:-[A-Za-z0-9]+)*$/.test(deck.lang))) {
    problem(errors, null, 'deck.json: lang must be a language code such as "zh", "en" or "ja".');
  }
  const theme = checkTheme(deck.theme, errors, warnings);
  for (const file of ['lib/deck.css', 'lib/deck.js']) {
    if (!existsSync(join(deckDir, file))) problem(errors, null, `${file} is missing in the deck folder; copy this skill's assets folder to <deck folder>/lib with skill_copy.`);
  }
  if (!Array.isArray(deck.slides) || deck.slides.length === 0) {
    problem(errors, null, 'deck.json needs "slides": a list with at least one slide, each {"id": "…", "file": "slides/<id>.html"}.');
    return result;
  }

  const ids = new Map();
  const files = new Map();
  let section = null;
  deck.slides.forEach((raw, index) => {
    if (!raw || typeof raw !== 'object' || typeof raw.id !== 'string') {
      problem(errors, null, `deck.json: slides[${index}] must be an object with an "id".`);
      return;
    }
    const id = raw.id;
    const fail = (message) => problem(errors, id, message);
    if (!ID.test(id)) fail(`id "${id}" must use lowercase letters, digits and single hyphens only (for example "why-now").`);
    else if (NUMBERED_ID.test(id)) fail(`id "${id}" is numbered; name the slide by what it says (for example "booking-growth"), so adding or moving slides does not rename anything.`);
    if (ids.has(id)) fail(`id "${id}" is used twice (also at position ${ids.get(id) + 1}); ids must be unique.`);
    else ids.set(id, index);

    const file = raw.file === undefined ? `slides/${id}.html` : raw.file;
    let fileOk = typeof file === 'string';
    if (fileOk) {
      const parts = file.split('/');
      fileOk = !file.startsWith('/') && parts.length === 2 && parts[0] === 'slides' && /^[^/\\]+\.html$/.test(parts[1]) && !parts.includes('..');
    }
    if (!fileOk) {
      fail(`file ${JSON.stringify(file)} must be a path like "slides/${id}.html" (an .html file directly inside slides/).`);
      return;
    }
    if (files.has(file)) {
      fail(`file ${file} is already used by ${files.get(file)}; each slide has its own file.`);
      return;
    }
    files.set(file, id);
    if (raw.section !== undefined && (typeof raw.section !== 'string' || raw.section.trim() === '')) {
      fail('section must be a non-empty text such as "产品".');
    } else if (raw.section !== undefined) {
      section = raw.section;
    }
    const path = join(deckDir, file);
    if (!existsSync(path)) {
      fail(`${file} does not exist; write the slide there.`);
      return;
    }
    const source = readFileSync(path, 'utf8');
    const checked = checkSlide({ id, file }, source, deckDir, errors, warnings);
    result.slides.push({ id, file, section, source, section_: checked && checked.section });
  });

  const first = result.slides[0];
  if (first && !/\bcover\b/.test((first.section_ && first.section_.attrs.class) || '')) {
    problem(warnings, first.id, 'the first slide is not a cover (class="slide cover"); a deck usually opens with one.');
  }
  const slidesDir = join(deckDir, 'slides');
  if (existsSync(slidesDir)) {
    for (const name of readdirSync(slidesDir).sort()) {
      if (name.endsWith('.html') && !files.has(`slides/${name}`)) problem(warnings, null, `slides/${name} is not listed in deck.json, so it is not in the deck.`);
    }
  }
  result.theme = theme;
  result.ok = errors.length === 0;
  return result;
}

const escapeText = (text) => String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const escapeAttribute = (text) => escapeText(text).replace(/"/g, '&quot;');

/** The slide's markup with where it came from (and its part of the talk) noted on the section tag. */
function annotated(slide) {
  const { source } = slide;
  const section = slide.section_;
  const open = source.slice(section.open.start, section.open.end);
  let extra = ` data-source="${escapeAttribute(slide.file)}"`;
  if (slide.section) extra += ` data-section="${escapeAttribute(slide.section)}"`;
  const tag = open.replace(/\s*\/?>$/, (end) => extra + end.trim());
  return (source.slice(0, section.open.start) + tag + source.slice(section.open.end, section.close ? section.close.end : source.length)).trim();
}

/** The page as text from a deck that passed checkDeck. */
export function assemble(result) {
  const { deck, slides, theme } = result;
  const lang = deck.lang || 'zh';
  const classes = [];
  if (theme && theme.dark) classes.push('dark');
  if (theme && theme.lines.length) classes.push('themed');
  const head = [
    '<meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1">',
    `<title>${escapeText(deck.title)}</title>`,
    '<link rel="stylesheet" href="lib/deck.css">',
  ];
  if (theme && theme.lines.length) head.push(`<style id="deck-theme">\nbody.themed {\n${theme.lines.map((l) => '  ' + l).join('\n')}\n}\n</style>`);
  return [
    '<!doctype html>',
    '<!-- Made by the slides skill from deck.json and slides/*.html. Change those files, not this one. -->',
    `<html lang="${escapeAttribute(lang)}">`,
    '<head>',
    ...head,
    '</head>',
    classes.length ? `<body class="${classes.join(' ')}">` : '<body>',
    ...slides.map(annotated),
    '<script src="lib/deck.js"></script>',
    '</body>',
    '</html>',
    '',
  ].join('\n');
}

/** Checks the deck and, when there are no errors, writes index.html next to deck.json. */
export function buildDeck(deckDir) {
  const result = checkDeck(deckDir);
  if (!result.ok) return result;
  const target = join(deckDir, 'index.html');
  const temporary = join(deckDir, `.index.html.${process.pid}.tmp`);
  writeFileSync(temporary, assemble(result));
  renameSync(temporary, target);
  result.indexPath = target;
  return result;
}

