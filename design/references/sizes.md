# Sizes

Artboards are px in CSS (96 per inch). Choose by where the design is seen; if unsure, take the suggested size and say so. Set it on `.artboard` as `--w` and `--h`, and set the type scale and spacing in `tokens.css` to match.

## Screen and social

| Purpose | Size (w×h) | Body | Display | Margin |
| --- | --- | --- | --- | --- |
| Phone screen (modern iPhone, Android) | 390×844 | 16 | 40 | 20 |
| Phone screen, small | 360×740 | 16 | 36 | 16 |
| Tablet, portrait | 834×1194 | 18 | 56 | 40 |
| Laptop / web page above the fold | 1440×900 | 18 | 72 | 80 |
| Wide screen, 16:9 (banner, cover) | 1920×1080 | 28 | 120 | 120 |
| Square post | 1080×1080 | 30 | 120 | 80 |
| Portrait post, feed (4:5) | 1080×1350 | 30 | 130 | 80 |
| Portrait poster for a phone (3:4) | 1080×1440 | 30 | 140 | 80 |
| Story / vertical cover (9:16) | 1080×1920 | 34 | 150 | 96 (keep the top and bottom 250 free of key text) |
| Link card / wide image (1.91:1) | 1200×630 | 28 | 84 | 60 |
| Banner, long (3:1) | 1500×500 | 28 | 84 | 48 |

## Print

At 96 px per inch, a sheet is:

| Paper | mm | Size (w×h) | Body | Display | Margin |
| --- | --- | --- | --- | --- | --- |
| A4 portrait (flyer, one-pager) | 210×297 | 794×1123 | 16–18 | 88 | 56 |
| A3 portrait (poster) | 297×420 | 1123×1587 | 22 | 130 | 80 |
| A5 (small flyer, menu) | 148×210 | 559×794 | 14 | 64 | 40 |
| Business card (91×55 mm) | 91×55 | 344×208 | 11 | 28 | 20 |
| Letter | 8.5×11 in | 816×1056 | 16–18 | 88 | 56 |

Landscape: swap width and height. Keep key text 5% (print: 3 mm, 12 px) inside every edge, because printers trim. Larger posters (A2, A1) are made at the A3 size, which scales up; say so.

## Infographic and diagrams

| Purpose | Size |
| --- | --- |
| Long infographic for phones (scroll) | 1080 wide × 1920–4000 tall, in sections of about 1080×1350 |
| One-page infographic, print | A4 or A3 portrait |
| Flow diagram, slide-like | 1600×900 |
| Process / architecture sketch | 1440×900 |

## Type size by distance

Poster seen from 2–3 m: the title at least 1/10 of the height, body at least 1/50. Phone: body 16 px at 390 wide or 30 px at 1080 wide (same proportion, about 1/25 of the width ≈ 4%). Check with `accessibility.md`.

## Choosing a size, quick answers

- "Poster" with no other word: A3 portrait if printed, 1080×1440 if it will be shared on a phone.
- "Social media / 朋友圈 / 小红书": 1080×1440 (3:4) or 1080×1350 (4:5). Instagram feed 1080×1350. 
- "App screen / mockup / 界面": 390×844.
- "Website / web page design / 网页稿": 1440×900 first screen; add a 390 wide version if it is responsive.
- "Infographic / 信息图": 1080 wide, tall as needed; print: A3.
- "Cover / banner": the place decides; ask once.
