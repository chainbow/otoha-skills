# Accessibility

check.js measures the first three below and page_check reports them; the rest you judge.

## Contrast (text against its background)

| Text | Needs |
| --- | --- |
| Normal text (under 24 px, or under 18.7 px bold) | 4.5 : 1 |
| Large text (24 px and over, or 18.7 px bold and over) | 3 : 1 |
| Icons, lines and shapes that carry meaning (a chart bar, a button edge, an input border) | 3 : 1 against what is next to them |

- Muted text is still text: `--color-muted` against `--color-bg` and `--color-surface` needs 4.5 : 1. The starting palettes in `color-and-type.md` pass.
- Text on a photo or gradient cannot be measured by the checker. Put a solid or semi-transparent panel behind it (a dark panel at 60% or more), or keep the text on a quiet part of the picture and look at the screenshot.
- Placeholder text, disabled controls and decoration are exempt by the rules, but keep them readable.
- White text on a mid-tone primary often fails (around 3 : 1). Darken the primary until `--color-on-primary` on it reaches 4.5 : 1.

## Size

- Screens: body text at least 16 px at 390 wide (about 4% of the width at any size), captions at least 12 px. The checker warns under 1.5% of the shorter side, with a floor of 11 px.
- Print: body at least 9 pt (12 px) for reading; 14 pt (19 px) or more for text meant to be read from a distance.
- Touch targets (buttons, rows that can be tapped, tabs): at least 44×44 px, with 8 px or more between them.
- Chinese and Japanese characters have more strokes; do not go under 14 px on screens, and give small CJK text line-height of 1.6 or more.

## Not by colour alone

- Status (success, error, selected) needs a word, shape or icon as well as colour.
- Chart series are labelled directly or differ by position or pattern; avoid pairs red/green only.
- Links and buttons are recognisable without colour: underline, shape or label.

## Structure

- `<html lang>` is set to the language of the text. A different language inside gets its own `lang`.
- Headings follow order: one `h1`, then `h2` for sections, `h3` inside them.
- Pictures that say something have an `alt` in the design's language; decoration has `alt=""`. Charts and diagrams have a text answer: a title or caption that states the finding.
- Use `button` for buttons and `a` for links, even in mockups; label icon-only buttons with `aria-label`.
- Reading order in the file matches the visual order: don't rely on absolute positioning to put the title first.
- Don't use motion that cannot be turned off; in a prototype, keep any animation short and respect `prefers-reduced-motion`.

## Quick test

Look at the screenshot with the page squinted (mentally blur it): can you still tell the title, the main figure and the action? Cover the colours (think greyscale): does it still make sense?
