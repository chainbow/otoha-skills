# Otoha skills

Official skills for [Otoha AI](https://otohaai.com), published through the Otoha skill market (https://skills.otohaai.com) as `otoha:otoha/<name>`.

Each skill is a folder with a `SKILL.md` and its own files. Each skill works on its own and brings its instructions, scripts and files, but never a runtime: scripts run on the system's public Python or Node, which a skill declares (`package.json` `engines`, PEP 723 or `requirements.txt`) so Otoha can check it and offer to install it. They are written for Otoha's tools and are independent work: no third-party skill text or code is copied in.

| Skill | What it does |
| --- | --- |
| `design` | Posters, interface and web drafts, infographics, diagrams and prototypes as HTML, previewed beside the conversation |
| `slides` | Presentations as HTML slides, one file per slide, presented full screen and exported to PDF; editable PowerPoint through the `pptx` skill |
| `pptx` | Editable PowerPoint decks (`.pptx`) that open in PowerPoint and Keynote |
| `docx` | Word documents (`.docx`) that open in Word and Pages |
| `xlsx` | Excel workbooks (`.xlsx`) with formatted tables, formulas and charts |
| `report` | Web research reports with numbered sources |
| `web-research` | Multi-platform web research (search, feeds, transcripts, GitHub, forums) |
| `quick-lookup` | Fast fact checks confirmed against cited sources |
| `promotion` | Social media promotion planning and post preparation for the user to publish |

License: MIT.
