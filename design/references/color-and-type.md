# Colour and type

Decide colours and fonts first, write them into `tokens.css`, and use only those in the artboards.

## tokens.css

Every name below has a fallback in `lib/base.css`, so write all the ones you change and no others. Sizes are in px of the artboard.

```css
:root {
  /* colours */
  --color-bg: #FBF5EA;          /* the page */
  --color-surface: #F2E7D3;     /* cards, panels */
  --color-text: #2B2118;
  --color-muted: #6B5B4B;       /* secondary text */
  --color-line: #DCCBAE;        /* rules, borders */
  --color-primary: #B4472B;     /* the main brand colour, buttons, key shapes */
  --color-on-primary: #FFFFFF;  /* text on primary */
  --color-accent: #E0A526;      /* a small second colour: highlights, fills */

  /* fonts: see the stacks below */
  --font-display: "Songti SC", "Noto Serif CJK SC", "Source Han Serif SC", "SimSun", serif;
  --font-body: "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;

  /* type scale for this artboard (see sizes.md for the numbers by size) */
  --text-caption: 22px;  --text-small: 26px;  --text-body: 30px;  --text-lead: 38px;
  --text-h3: 46px;  --text-h2: 60px;  --text-h1: 88px;  --text-display: 140px;
  --leading-tight: 1.15;  --leading-normal: 1.6;  --tracking-display: 0;

  /* spacing ladder: roughly 1/4 of body size, doubling; margin is the outer margin */
  --space-1: 8px; --space-2: 16px; --space-3: 24px; --space-4: 32px;
  --space-5: 48px; --space-6: 64px; --space-7: 96px; --space-8: 128px;
  --margin: 80px;
  --radius-s: 8px; --radius-m: 16px; --radius-l: 32px;
}
```

Dark variant: put the colour tokens again under `.dark`, and write `class="artboard dark"`.

## Choosing colours

1. Start from the mood of the subject and the user's brand, not from a favourite colour.
2. **Neutrals first**: a background, a text colour and one muted text colour. A very slightly tinted off-white or near-black (not pure `#000`/`#fff`) feels designed; pure black on pure white is harsh but fine for a technical or austere look.
3. **One primary**, one optional accent. Roughly 60% background, 30% surface and text, 10% primary and accent.
4. Check text pairs with the numbers in `accessibility.md` before you commit. `--color-accent` is a fill colour; set text on it with `--color-text`, and do not use a yellow or orange accent for small text on a light background.
5. Semantic colours (success green, warning amber, error red) only for those meanings, always with a word or icon too.
6. Data: up to six categories, spaced in hue; for ordered values one hue from light to dark. Never rely on colour alone to tell series apart; label them directly.

Starting palettes (all pass the text contrast levels of `accessibility.md`; accent as a fill only):

| Mood | bg | surface | text | muted | primary | on-primary | accent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Warm, food, craft | #FBF5EA | #F2E7D3 | #2B2118 | #6B5B4B | #B4472B | #FFFFFF | #E0A526 |
| Fresh, health, nature | #F4F8F2 | #E3EDE0 | #1D2B22 | #51645A | #2F6B45 | #FFFFFF | #E8683B |
| Calm, business, finance | #F7F7F5 | #ECECE8 | #1F2933 | #5B6670 | #2B5C8A | #FFFFFF | #D2691E |
| Tech, night, product | #0F172A | #1B2540 | #F1F5F9 | #A3B1C6 | #6EA8FE | #0B1220 | #F5B544 |
| Bold, event, youth | #FFE14D | #FFF0A6 | #111111 | #3D3A2A | #111111 | #FFE14D | #E6334D |
| Black and white, editorial | #FFFFFF | #F2F2F2 | #111111 | #595959 | #111111 | #FFFFFF | #C8102E |

## Fonts

The preview shows only fonts installed on the viewer's computer, so every stack ends with a generic family and lists the usual fonts of each system. Put the Latin font first and the CJK fonts after it: Latin letters and digits then use the Latin face, and Chinese and Japanese characters fall to the CJK face. Do not load fonts from the network.

| Use | Stack |
| --- | --- |
| Latin sans | `system-ui, "Helvetica Neue", Arial, "Segoe UI", sans-serif` |
| Latin serif | `"Iowan Old Style", Georgia, "Times New Roman", serif` |
| Simplified Chinese sans | `"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", "Source Han Sans SC", sans-serif` |
| Simplified Chinese serif | `"Songti SC", "STSong", "SimSun", "Noto Serif CJK SC", "Source Han Serif SC", serif` |
| Traditional Chinese sans | `"PingFang TC", "Microsoft JhengHei", "Noto Sans CJK TC", "Source Han Sans TC", sans-serif` |
| Traditional Chinese serif | `"Songti TC", "PMingLiU", "Noto Serif CJK TC", serif` |
| Japanese sans | `"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", "Meiryo", "Noto Sans CJK JP", "Source Han Sans JP", sans-serif` |
| Japanese serif | `"Hiragino Mincho ProN", "Yu Mincho", "Noto Serif CJK JP", "Source Han Serif JP", serif` |
| Korean sans | `"Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans CJK KR", sans-serif` |
| Monospace | `ui-monospace, "SF Mono", Menlo, Consolas, monospace` |

Full stacks combine the two, e.g. a Chinese poster in a text face: `system-ui, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif`. Set `lang` on `<html>` (`zh`, `zh-Hant`, `ja`, `ko`, `en`) so the same character gets the right glyph shape; when one design mixes languages, set `lang` on the element too.

Choosing:

- Sans for screens, small text and a modern look; serif (Songti, Mincho, Georgia) for a literary, traditional, cultural or premium look. Pair a serif display with a sans body, not two sans of different character.
- Weight: CJK system fonts may have only regular and bold. Use 400 and 700 (or 600 on Latin); do not rely on 300 or 800 showing.
- **No italics in Chinese or Japanese**: use weight or colour for emphasis. Do not letter-space body CJK text; a small positive tracking (0.04–0.1em) only on short CJK headings.
- Do not make uppercase transforms on CJK; they do nothing, and the eyebrow style uppercases Latin only.

## Type scale

Pick the scale by artboard size from `sizes.md` (body size, ratio about 1.25 on screens and 1.5 on posters), then keep to eight roles: caption, small, body, lead, h3, h2, h1, display. Use three or four of them per artboard.

- Line height: body 1.5 (Latin) to 1.7 (CJK); headings 1.1–1.25 (Latin), 1.25–1.4 (CJK, which looks loose at 1.1 when large).
- Line length: 35–70 Latin characters or 18–35 CJK characters per line for reading text. Narrow the box rather than shrinking the type.
- Wrap: CJK breaks anywhere; avoid a line that ends with a single character or starts with closing punctuation (set `line-break: strict`). Korean and Latin text break at spaces (`word-break: keep-all` for Korean).
- Numbers in tables and prices: `font-variant-numeric: tabular-nums`.
- Large display text may be tighter: line-height 1.05–1.15, letter-spacing −0.01 to −0.03em for Latin.
