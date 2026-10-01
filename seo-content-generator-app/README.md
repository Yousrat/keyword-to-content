# SEO Content Generator — Web App

A no-code version of the SEO content pipeline. Anyone on your team can open
a link, type a keyword, upload their Ahrefs/SEMrush exports, and get a
content brief + full draft + SEO validation report — no Python, no Colab,
no code required.

## What it does

1. Enter a **primary keyword** and (optionally) **secondary keywords**.
2. Upload up to three research exports:
   - SERP overview
   - Content gap
   - Keyword explorer comparison
   These can be raw Ahrefs/SEMrush CSV exports in any encoding — the app
   automatically detects encoding (UTF-8/UTF-16) and delimiter (comma/tab),
   and trims each file down to the columns that actually matter (keyword,
   position, volume, difficulty, title, etc.) so large exports never blow
   past the AI model's input limit.
3. Click **Generate**. The app produces:
   - A structured content brief (title, meta description, outline, keywords)
   - A full markdown draft following that brief
   - An automated on-page SEO report (keyword density, header structure, length checks)
4. Download any of the three outputs directly from the browser.

