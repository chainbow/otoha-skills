# Design principles

Work from these in order; most weak designs fail at the first three.

## 1. One idea, one first look

Decide what the viewer should notice first, second and third. Make the first at least twice the size of the second (or much heavier, or the only coloured thing). If two things compete, make one smaller. Squint: you should still see the first thing.

## 2. Hierarchy with few steps

Use three to four text sizes and two to three weights, taken from the type scale in `tokens.css`. Size, weight, colour and space all signal rank; change one or two at a time, not all four. Group what belongs together (a heading with its text), separate what does not.

## 3. Space is part of the design

- Outer margin: at least 5% of the shorter side; more is calmer.
- Space between groups is clearly larger than space inside a group (about 2:1 or more).
- Do not fill every corner. A block with room around it reads as more important than a crowded block.
- Take spacing only from the ladder `--space-1 … --space-8`.

## Fill the format

The artboard has a fixed height; plan the blocks so together they use it. Make the artboard a column (`class="artboard stack pad"`), put the closing line (contact, source, signature) last with `margin-top:auto` so it sits at the bottom edge, and give the main block `flex:1` or enlarge the type, rows and gaps until the page is full. A band of empty space at the bottom means the sizes are too small for the format. check.js warns when more than 15% is empty.

## 4. Align to few lines

Choose a left edge (or a centre line) and place most things on it. Use a grid of 4, 6 or 12 equal columns for layouts with several blocks. Left-aligned text is easiest to read; centre only short lines (titles, a single sentence). Do not mix left, centre and right alignment in one block.

## 5. Contrast

Light on dark or dark on light, with a clear gap (see `accessibility.md`). Contrast is also size and weight: a thin small grey line next to a large bold black one disappears. Use at most one accent colour for the thing to act on or remember; a screen where everything is accent has none.

## 6. Repetition

Repeat the same treatment for the same kind of thing: every card the same radius and padding, every price the same style, every step the same icon size. Differences should mean something.

## 7. Restraint

One typeface family for most designs (two at most: one for headings, one for text). Two or three colours plus neutrals. No decoration without a job: a line may separate, a shape may group or point, a colour block may carry the first look. Avoid gradients, shadows and borders that are only there to look "designed"; avoid stock clichés (a handshake, a lightbulb).

## 8. Real content

Design with the real words. Titles short enough to fit one or two lines in the narrowest place; test with the longest likely text. Do not fill with "Lorem ipsum" or invented facts.

## Kinds of work

- **Poster**: one dominant title or image, one line of support, practical details small at the bottom. Readable from three metres: the title is at least 1/10 of the poster height.
- **Screen**: one primary action per screen; navigation in the usual place (bottom bar on phones, left or top on desktops); lists as repeated rows with consistent spacing; touch targets at least 44 px high.
- **Infographic**: a title that states the finding, one visual form per message, the source at the bottom. See `diagrams.md`.
- **Prototype**: screens look like one product (same tokens, same components); show the path, not every screen.

## Before you say it is done

- What is the first thing you see, and is it the right one?
- Is there any text you must lean in to read?
- Do the edges line up, and are the gaps consistent?
- Is any word or number one you made up that the user did not give you? Say so.
