// A small HTML reader for slide files: enough to find elements, attributes, text and where each opening tag
// sits, and to say plainly when tags do not match. It is not a browser; it reads the markup slides use.

const VOID = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr']);
const RAW = new Set(['script', 'style']);

function lineAt(source, offset) {
  let line = 1;
  for (let i = 0; i < offset && i < source.length; i += 1) if (source[i] === '\n') line += 1;
  return line;
}

/** Reads the attributes inside an opening tag; returns them and the offset just after the tag's `>`. */
function readTag(source, from) {
  const attrs = {};
  let i = from;
  const n = source.length;
  const blank = (c) => c === ' ' || c === '\n' || c === '\t' || c === '\r' || c === '\f';
  while (i < n) {
    while (i < n && (blank(source[i]) || source[i] === '/')) i += 1;
    if (source[i] === '>') return { attrs, end: i + 1 };
    const start = i;
    while (i < n && !blank(source[i]) && source[i] !== '=' && source[i] !== '>' && source[i] !== '/') i += 1;
    const name = source.slice(start, i).toLowerCase();
    if (!name) { i += 1; continue; }
    while (i < n && blank(source[i])) i += 1;
    let value = '';
    if (source[i] === '=') {
      i += 1;
      while (i < n && blank(source[i])) i += 1;
      const quote = source[i];
      if (quote === '"' || quote === "'") {
        const close = source.indexOf(quote, i + 1);
        if (close < 0) return { attrs, end: n, broken: true };
        value = source.slice(i + 1, close);
        i = close + 1;
      } else {
        const v = i;
        while (i < n && !blank(source[i]) && source[i] !== '>') i += 1;
        value = source.slice(v, i);
      }
    }
    if (!(name in attrs)) attrs[name] = value;
  }
  return { attrs, end: n, broken: true };
}

/**
 * Parses markup into a tree. Elements: { type: 'element', tag, attrs, children, open: {start, end}, close, line };
 * text: { type: 'text', text, start }. Mismatched or unclosed tags are listed in `errors` with their line.
 */
export function parseHtml(source) {
  const root = { type: 'root', children: [] };
  const stack = [root];
  const errors = [];
  const n = source.length;
  let i = 0;

  const addText = (text, start) => {
    if (text) stack[stack.length - 1].children.push({ type: 'text', text, start });
  };

  while (i < n) {
    const lt = source.indexOf('<', i);
    if (lt < 0) { addText(source.slice(i), i); break; }
    if (lt > i) addText(source.slice(i, lt), i);
    i = lt;
    if (source.startsWith('<!--', i)) {
      const close = source.indexOf('-->', i + 4);
      i = close < 0 ? n : close + 3;
      continue;
    }
    if (source[i + 1] === '!' || source[i + 1] === '?') {
      const close = source.indexOf('>', i);
      i = close < 0 ? n : close + 1;
      continue;
    }
    if (source[i + 1] === '/') {
      const close = source.indexOf('>', i);
      const end = close < 0 ? n : close + 1;
      const tag = source.slice(i + 2, close < 0 ? n : close).trim().toLowerCase();
      let depth = stack.length - 1;
      while (depth > 0 && stack[depth].tag !== tag) depth -= 1;
      if (depth === 0) {
        errors.push({ message: `</${tag}> closes a tag that was never opened`, line: lineAt(source, i) });
      } else {
        while (stack.length - 1 > depth) {
          const open = stack.pop();
          errors.push({ message: `<${open.tag}> is never closed`, line: open.line });
        }
        const element = stack.pop();
        element.close = { start: i, end };
      }
      i = end;
      continue;
    }
    const name = /^<([a-zA-Z][a-zA-Z0-9-]*)/.exec(source.slice(i, i + 64));
    if (!name) { addText('<', i); i += 1; continue; }
    const tag = name[1].toLowerCase();
    const { attrs, end, broken } = readTag(source, i + name[0].length);
    const element = { type: 'element', tag, attrs, children: [], open: { start: i, end }, close: null, line: lineAt(source, i) };
    if (broken) errors.push({ message: `<${tag}> has an unfinished tag`, line: element.line });
    stack[stack.length - 1].children.push(element);
    i = end;
    if (VOID.has(tag)) continue;
    if (RAW.has(tag)) {
      const closing = new RegExp(`</${tag}\\s*>`, 'i').exec(source.slice(i));
      const rawEnd = closing ? i + closing.index : n;
      if (rawEnd > i) element.children.push({ type: 'text', text: source.slice(i, rawEnd), start: i });
      element.close = { start: rawEnd, end: closing ? rawEnd + closing[0].length : n };
      if (!closing) errors.push({ message: `<${tag}> is never closed`, line: element.line });
      i = element.close.end;
      continue;
    }
    stack.push(element);
  }
  while (stack.length > 1) {
    const open = stack.pop();
    errors.push({ message: `<${open.tag}> is never closed`, line: open.line });
  }
  return { nodes: root.children, errors };
}

/** All the text inside a node, in order. */
export function textOf(node) {
  if (node.type === 'text') return node.text;
  return (node.children || []).map(textOf).join('');
}

/** Every element under the nodes, in document order. */
export function* elements(nodes) {
  for (const node of nodes) {
    if (node.type !== 'element') continue;
    yield node;
    yield* elements(node.children);
  }
}

export function decodeEntities(text) {
  return text
    .replace(/&nbsp;/g, ' ')
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(Number(d)))
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").replace(/&amp;/g, '&');
}
