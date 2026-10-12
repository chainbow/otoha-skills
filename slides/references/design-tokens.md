# Using a design's colours and fonts

When the project already has a design made with the design skill (a folder with the poster, interface or web draft, and a file of shared colours and fonts), or the user names a brand, make the deck match it. Without either, keep the built-in look: white slides, dark text, one indigo accent.

## Finding it

1. List the project's folders with workspace_search or workspace_read; a design usually sits in a folder named for it, next to its design variables file (colours and fonts shared by the design's boards, often `tokens.css`).
2. Read that file only. Do not copy its CSS into slides, and do not link to it: slides carry no styles of their own.
3. If the user names a brand or gives a colour but there is no design, use what they gave.

## What to take

Write the values you need into `theme` in `deck.json`. All are optional; each is a plain colour like `#0a7d5a`.

| `theme` field | Take from the design | Used for |
| --- | --- | --- |
| `accent` | the brand or primary colour | cover background, title bars, bullets, numbers, first chart colour |
| `accentSoft` | a light tint of it (left out, it is worked out) | stat cards, the second column, quote slide |
| `ink` | the main text colour | titles, body text |
| `muted` | the secondary text colour | captions, slide numbers |
| `line` | a border or divider colour | card borders, chart grid |
| `paper` | the page or surface colour | slide background |
| `font` | the body font stack, with fallbacks (for Chinese and Japanese too) | all text |
| `chart` | up to 5 categorical colours | chart series |
| `mode` | `"dark"` for a dark design | switches the base to dark slides |

```json
"theme": {"accent": "#0a7d5a", "ink": "#14201b", "font": "'Noto Serif SC', 'Songti SC', serif", "chart": ["#0a7d5a", "#e0a019", "#4a6fa5"]}
```

## Checks

- White text sits on the accent on the cover, so the accent must be dark enough: contrast of at least 4.5:1 with white. The build warns when it is not; choose a darker shade of the same hue instead of switching the cover text.
- Dark mode needs its own values: a dark design usually gives light `ink`, dark `paper`.
- A font only works if it is on the viewer's machine or in the fallback list; always end the stack with `sans-serif` or `serif`. The deck cannot load fonts from the internet.
- Take values, not the design itself: layouts and spacing stay the deck's.
