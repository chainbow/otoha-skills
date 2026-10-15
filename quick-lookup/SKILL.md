---
name: quick-lookup
description: Answer a factual question fast from Google's AI answer, then confirm the key facts on a source it cites before answering. Use for prices, opening hours, dates, schedules and other quick facts, especially when what can be read at once is short. 查价格、时间、日期等事实，快速查询。
allowed-tools: skill_read browser_search browser_open browser_read browser_click
---
# Quick lookup

Google puts an AI answer above its results, with the pages it drew on; its AI mode answers questions asked in plain words. One page then gives an overall answer and where it came from. The AI answer can be wrong or out of date, so it is a lead, never the source.

## Look it up

1. Keep the project's own private things (names, amounts, file contents) out of the question: it is sent to Google.
2. Ask in plain words with browser_open at `https://www.google.com/search?udm=50&q=<the question, URL-encoded>` (AI mode). Where that does not answer (not offered in every region, language or account, or the page has changed), use browser_search with the question; the AI answer, when there is one, is at the top of the results.
3. Read the AI answer and the links it cites. Note the facts that matter for the question: prices, dates, times, places, numbers.

## Confirm before answering

4. Open at least one cited source with browser_click, preferring the official one (the place's own site, the operator, the government), and read it. Check each key fact there.
5. Where the source says otherwise than the AI answer, the source wins. Where no source confirms a fact, say it could not be confirmed.
6. Answer with the facts as the source states them, with its title and address and, when it shows one, its date. Do not cite the AI answer itself.

## When it does not work

- No AI answer: say so to the user in a sentence, then answer from an ordinary search, confirming on a source in the same way.
- The site asks the user to show they are a person: the browser stops for the user. Tell them to do it in the browser beside the conversation; do not search again until they have.
