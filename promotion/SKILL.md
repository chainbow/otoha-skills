---
name: promotion
description: Plan and carry out the promotion of a product or app on social platforms: agree the goal, audience, platforms and schedule with the user, put a day-by-day plan on the board, and write and prepare each post for the user to publish. Use when the user wants to promote, advertise, launch, 宣传, 推广 or 运营 something on X, 小红书 or similar platforms. 社交媒体、发帖、宣伝、プロモーション。
allowed-tools: skill_read matter_tasks workspace_read workspace_write workspace_search browser_search browser_open browser_read browser_click browser_type browser_press browser_choose browser_upload browser_scroll browser_wait task_report datetime
---
# Promotion

The user publishes; Otoha plans, writes and prepares. Platforms forbid posting by scripts or by an AI on its own (X bans scripting its site; 小红书 bans AI-managed posting), so never promise to publish by yourself, and never press a platform's final post or publish button.

## 1. Agree the plan

Ask only for what is missing, a few questions at a time:

1. What is promoted, in one sentence, and its link (download page, site).
2. The goal: downloads, sign-ups, visits, awareness. How the user will judge it.
3. The audience: who they are and what they care about.
4. The platforms. Suggest the ones that fit the audience and say why; the user decides. For each, read `references/platforms/<platform>.md` before planning it.
5. How long and how often, with times: for example two weeks, X at 10:00 and 18:00, 小红书 at 12:00.
6. Tone, things never to say, and claims that need care (prices, comparisons, promises).
7. Material in the project to use as images: screenshots, frames of a demo video, the logo. Look with workspace_search and workspace_read, and list what you found.

Then say how each post will go, from the platform's reference: what you prepare, what the user checks and presses, and when they will be asked. Tell them posts written with AI are labelled as such where the platform asks.

## 2. Put the plan on the board

Summarise the plan in a short table (day, time, platform, topic) and write it to `宣传/计划.md` with workspace_write. When the user agrees, add one card per post with matter_tasks:

- title: platform, date and topic, for example `小红书 · 10/1 · 三步做出演示视频`;
- details: the angle, the key message, the call to action, the link, and which images to use by file name;
- owner: otoha; runAt: the date and time to post, in the user's local time without a time zone, like `2026-10-01T10:00` (only times the user gave);
- start: `itself` when the user said you may start preparing at the time without asking; otherwise leave it;
- site: `creator.xiaohongshu.com` for 小红书 posts, so the user can allow you to fill in notes there when accepting the card. X posts have no site: you do nothing on X's pages.

Give each day's post its own card rather than one repeating card, since each day's content differs. Keep topics varied across days: no near-duplicates, which platforms treat as spam. The cards are suggestions until the user accepts them.

At most 20 cards go on the board in one reply. For a longer plan, add the first week now and say so; add the next week when the user asks, or when the first week is under way.

## 3. When a post's card runs

1. Read the task, the plan (`宣传/计划.md`) and the platform's reference.
2. Write the post within the platform's limits and in its style. Save it as `宣传/<date>-<platform>.md` with the images it uses, so the user can see and reuse it.
3. Prepare it on the platform exactly as the reference says. Label AI-written content where the platform asks.
4. Report with task_report `needs_you`: say that the post is ready, where, what to check, and which button to press. The user's answer comes in this conversation.
5. When the user says it is published, look at the page if it is open, then report `done` with the post's address when you can see it, and add a line to `宣传/记录.md`: date, time, platform, title, address.

If the page asks the user to log in, or shows anything you did not expect, stop and report `needs_you` saying what they should do. Never type a password or a code for the user.

## 4. Review

When the user asks how it is going, read `宣传/记录.md` and, if they share numbers (views, likes, sign-ups), suggest what to keep and what to change in the rest of the plan.
