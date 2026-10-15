# X (formerly Twitter)

## Rules that matter

- X's rules forbid automating its website ("scripting the X website" can get the account permanently suspended). So you never type, press, choose or upload anything on x.com; the app refuses it. You open X's share page with the post already in it, and the user presses Post.
- Automated or AI-written accounts should say so in their bio; posts written with Otoha's help are posted by the user.

## Writing

- At most 280 characters, counted X's way: each Chinese, Japanese or Korean character counts as 2 (so about 140 of them), a link counts as 23 whatever its length.
- One idea per post. Lead with the point, not with a greeting.
- One or two hashtags at most, at the end. A link to the page being promoted when it helps.
- For a thread, write each post separately in the draft; the user posts the first, then replies.

## Preparing a post

1. Put the post's text together, with its hashtags and link.
2. Open the share page with browser_open: `https://x.com/intent/post?text=<the text, URL-encoded>`. The link can go in the text or as `&url=<link>`.
3. Read the page with browser_read to see the text is in place. If it asks to log in, stop and ask the user to log in in the browser beside the conversation, then open the share page again.
4. Images cannot be added through the share page. Name the image files for the user (from `宣传/`) if the post should have them.
5. Report `needs_you`: the post is filled in on the right; check it, add the named images if wanted, and press Post; then tell you.
