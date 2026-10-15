---
name: web-research
description: Research a topic on the web by platform (search, news feeds, YouTube and Bilibili transcripts, GitHub, Hacker News, Reddit, sign-in sites), then rank, merge and cite the findings. For what sources said recently, not one quick fact. 网上查资料、调研讨论、视频内容、开源项目。
allowed-tools: skill_read browser_search browser_open browser_read browser_click browser_scroll browser_wait browser_press browser_type
version: 1.0.0
---
# Web research

Research goes by platform: each kind of source has a way to read it that works best. Everything here goes through the app's browser, which the user sees beside the conversation; nothing is fetched behind their back, and sites they have not allowed ask first.

## Before searching

1. Keep the project's private things (names, amounts, file contents) out of what is searched: it is sent to the sites.
2. Settle the time window the question needs (the last 30 days by default for "what is new" questions) and say it in the answer.
3. Turn the topic into several queries: its names and nicknames, the people, products and projects involved, and the communities, accounts and repositories where it is discussed. Search each.

## Routes by platform

### Web pages and search

- Search with browser_search, then open the pages that look like sources with browser_click or browser_open.
- A site's text for AI is used when it has one: a page's Markdown version is read in its place, and `https://<site>/llms.txt` lists what the site offers.
- A long page is read in parts: when browser_read says more follows, read on from where it says.

### News feeds (blogs, news sites, release notes)

- Many sites have a feed: try `/feed`, `/rss`, `/atom.xml`, `/index.xml`, or the RSS link on the page.
- Open the feed's address, then use browser_read on the feed: its entries come back newest first, each with its title, address, date and a short summary. Open an entry for the whole article.

### YouTube

1. Open the video. Press the description's "...more" and then "Show transcript" (显示文字记录, 文字起こしを表示); if the description shows no such button, the transcript may be under the video's "..." menu.
2. Read the page; the transcript lists the spoken words with times. When it is long, read on in parts.
3. Cite the video's address, with the time of a quoted passage as `&t=<seconds>s`.
4. A video without a transcript: say so, and answer only from its title, description and comments, saying that is all it is.

### Bilibili

- Open the video (`https://www.bilibili.com/video/<BV id>`). Its subtitles are in the player's subtitle list (字幕列表) or the AI assistant's subtitles, which usually need a signed-in account.
- Not signed in: ask the user to sign in themselves in the browser beside the conversation, then read again. Without subtitles, use the title, description and the top comments, and say so.

### GitHub

- A repository's page gives its description, stars and recent activity; its README as plain text is at `https://raw.githubusercontent.com/<owner>/<repo>/HEAD/README.md`.
- Releases, newest first, are a feed: `https://github.com/<owner>/<repo>/releases.atom`.
- Issues and discussions: search the repository's issues page (`/issues?q=<words>`), sorted by most commented when the question is what people run into.
- The public interface answers in plain JSON, for example `https://api.github.com/repos/<owner>/<repo>`; it allows few requests an hour without signing in, so use it sparingly.

### Hacker News and Reddit

- Hacker News: `https://hn.algolia.com/api/v1/search?query=<words>&tags=story` lists stories with points and comment counts; each story's discussion is at `https://news.ycombinator.com/item?id=<objectID>`.
- Reddit: `https://old.reddit.com/r/<subreddit>/search?q=<words>&restrict_sr=1&sort=top&t=month` reads well; open a thread for its top comments.

### Platforms that need an account (X, 小红书, 微博, 知乎, 抖音, LinkedIn)

- They are read only with the user's own sign-in. Ask the user to sign in themselves in the browser beside the conversation; once they have, read and search there as they would.
- Never ask for a password, and never use another browser's cookies or saved sign-ins.
- What a platform leaves to people (posting, following, liking, messaging) is not done; this skill only reads.
- The site asks the user to show they are a person: the browser stops for the user. Tell them to do it in the browser beside the conversation, and do not search again until they have.

## Weigh what was found

1. Rank sources by how many people engaged with them (points, comments, stars, views), how recent they are, and how closely they answer the question.
2. Merge the same story told in several places into one finding, naming every place it appeared.
3. For a discussion, note what the most-supported comments say, including disagreement.
4. Prefer the primary source (the project, the company, the paper, the official channel) over retellings; where they differ, the primary source wins.

## Answer

- Lead with what was found, fact by fact. Beside each fact give the source title, address and the page result's `retrievedAt` time, labelled as when you checked it. A publication date, when available, is separate. Do not invent a read time or a source.
- When aggregating research cards or earlier findings, keep each fact's own source address and checked time; a bibliography alone is not enough. Mark estimates and unverified allowances separately from confirmed facts.
- Quote briefly, and for videos give the time.
- Say what could not be confirmed, which sources could not be read and why (sign-in, no transcript, a site that refused), and the time window searched.
