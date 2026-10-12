import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseHtml, textOf } from '../lib/html.mjs';

test('parses nested elements, attributes and text', () => {
  const { nodes, errors } = parseHtml('<section id="a" class="slide x"><h2 data-edit="t">Hi <b>there</b></h2></section>');
  assert.deepEqual(errors, []);
  assert.equal(nodes.length, 1);
  const section = nodes[0];
  assert.equal(section.tag, 'section');
  assert.equal(section.attrs.id, 'a');
  assert.equal(section.attrs.class, 'slide x');
  const h2 = section.children[0];
  assert.equal(h2.attrs['data-edit'], 't');
  assert.equal(textOf(h2), 'Hi there');
});

test('void elements, comments and doctype do not need closing', () => {
  const { nodes, errors } = parseHtml('<!doctype html><!-- note --><div><img src="a.png" alt="x"><br><p>a</p></div>');
  assert.deepEqual(errors, []);
  const div = nodes.find((n) => n.type === 'element');
  assert.deepEqual(div.children.map((c) => c.tag), ['img', 'br', 'p']);
});

test('script content is raw text and not parsed as markup', () => {
  const { nodes, errors } = parseHtml('<figure class="chart"><script type="application/json">{"a": "<b>"}</script></figure>');
  assert.deepEqual(errors, []);
  const script = nodes[0].children[0];
  assert.equal(script.tag, 'script');
  assert.equal(script.children[0].text, '{"a": "<b>"}');
});

test('attribute values may be single quoted, unquoted or contain >', () => {
  const { nodes, errors } = parseHtml(`<p title='a>b' data-x=1 hidden>t</p>`);
  assert.deepEqual(errors, []);
  assert.equal(nodes[0].attrs.title, 'a>b');
  assert.equal(nodes[0].attrs['data-x'], '1');
  assert.equal(nodes[0].attrs.hidden, '');
});

test('reports an unclosed element with its line', () => {
  const { errors } = parseHtml('<section>\n<div>\n<p>x</p>\n</section>');
  assert.equal(errors.length, 1);
  assert.match(errors[0].message, /<div>.*never closed/);
  assert.equal(errors[0].line, 2);
});

test('reports a closing tag without an opening one', () => {
  const { errors } = parseHtml('<p>x</p></div>');
  assert.equal(errors.length, 1);
  assert.match(errors[0].message, /<\/div>/);
});

test('records where each opening tag starts and ends', () => {
  const source = 'ab<section id="a">x</section>';
  const { nodes } = parseHtml(source);
  assert.equal(source.slice(nodes[1].open.start, nodes[1].open.end), '<section id="a">');
});

test('a tag name is case-insensitive', () => {
  const { nodes, errors } = parseHtml('<P>x</P>');
  assert.deepEqual(errors, []);
  assert.equal(nodes[0].tag, 'p');
});
