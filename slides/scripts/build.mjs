// Checks a slide deck folder and builds its index.html.
//   node build.mjs build <deck folder>   check, then write <deck folder>/index.html
//   node build.mjs check <deck folder>   check only
// Prints every problem, one per line, and exits 1 when there is one; exits 2 when used wrongly.

import { resolve } from 'node:path';
import { buildDeck, checkDeck } from './lib/deck.mjs';

const [command, folder] = process.argv.slice(2);
if (!['build', 'check'].includes(command) || !folder) {
  console.log('Usage: build.mjs build|check <deck folder>');
  process.exit(2);
}

const deckDir = resolve(folder);
const result = command === 'build' ? buildDeck(deckDir) : checkDeck(deckDir);
const label = (item) => (item.slide ? ` ${item.slide}` : '');
for (const error of result.errors) console.log(`ERROR${label(error)}: ${error.message}`);
for (const warning of result.warnings) console.log(`WARNING${label(warning)}: ${warning.message}`);
if (!result.ok) {
  console.log(`Not built: ${result.errors.length} problem${result.errors.length === 1 ? '' : 's'} to fix.`);
  process.exit(1);
}
const count = result.slides.length;
console.log(command === 'build' ? `OK: ${count} slides → ${folder}/index.html` : `OK: ${count} slides, nothing to fix.`);
