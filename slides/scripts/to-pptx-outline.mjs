// Writes the outline the pptx skill builds a PowerPoint file from, out of a slide deck folder.
//   node to-pptx-outline.mjs <deck folder> [outline file]      (default: <deck folder>/outline.json)
// Run it from the project's folder with paths relative to it, so picture paths come out right.

import { writeFileSync } from 'node:fs';
import { isAbsolute, join, relative, resolve } from 'node:path';
import { checkDeck } from './lib/deck.mjs';
import { pptxOutline } from './lib/outline.mjs';

const [folder, target] = process.argv.slice(2);
if (!folder) {
  console.log('Usage: to-pptx-outline.mjs <deck folder> [outline file]');
  process.exit(2);
}

const deckDir = resolve(folder);
const checked = checkDeck(deckDir);
if (!checked.ok) {
  for (const error of checked.errors) console.log(`ERROR${error.slide ? ' ' + error.slide : ''}: ${error.message}`);
  console.log('No outline written: fix the deck first (build.mjs check).');
  process.exit(1);
}
const inProject = isAbsolute(folder) ? relative(process.cwd(), deckDir) : folder;
const { outline, notes } = pptxOutline(checked, inProject);
const out = target ? resolve(target) : join(deckDir, 'outline.json');
writeFileSync(out, JSON.stringify(outline, null, 2) + '\n');
for (const note of notes) console.log(`NOTE ${note}`);
console.log(`OK: ${outline.slides.length} slides → ${target || join(folder, 'outline.json')}`);
