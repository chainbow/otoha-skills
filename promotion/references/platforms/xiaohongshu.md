# 小红书

## Rules that matter

- AI-managed posting is against 小红书's rules (announcement of 2026-03-10): accounts whose notes are generated and posted by AI tools are limited or banned. You fill in the note; the user checks it and presses 发布. The app refuses pressing the publish button.
- Content written or helped by AI must be declared: in the publish page's content type declaration (内容类型声明, sometimes under 高级选项 or 设置), choose the AI option (笔记含AI合成内容 / 内容由AI生成 / 已自主标注). Undeclared AI content is limited.
- No near-duplicate notes and no templated low-effort notes; each note should give the reader something real.

## Writing

- Title: at most 20 characters, specific and useful (a result, a number, a question). No clickbait.
- Body: at most 1000 characters including punctuation and spaces. Short paragraphs, a clear structure (why, how, what you get), a few emoji as markers at most.
- Topics: 3 to 6 at the end as #话题, relevant to the content.
- Images: 1 to 18; the first is the cover. Portrait 3:4 works best. Use real screenshots or frames from the project; say in the draft which files, in order.

## Preparing a note

The page's labels may change; read the controls and choose by what they say. If you cannot find a step, stop and ask the user.

1. Open `https://creator.xiaohongshu.com/publish/publish?from=menu` with browser_open and read it. If it shows a login page, stop and ask the user to log in in the browser beside the conversation.
2. Choose image-and-text posting (上传图文) if the page offers a choice.
3. Upload the images with browser_upload on the file control (上传图片), in order, the cover first. Wait for them with browser_wait if the page says they are uploading.
4. Type the title into the title field (填写标题…) and the body into the body editor. Put the topics at the end of the body.
5. Open the content type declaration and choose the AI option.
6. Read the page again and check the title, body, images and declaration are all there.
7. Do not press 发布. Report `needs_you`: the note is filled in on the right; check it and press 发布; then tell you.
