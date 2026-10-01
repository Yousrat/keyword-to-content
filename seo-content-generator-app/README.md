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

## Running it yourself (local test)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
streamlit run app.py
```

This opens the app in your browser at `http://localhost:8501`. Only you can
access it at this point — it's running on your machine.

## Making it available to your team (deploy it — free, ~5 minutes)

This is what turns it from "a script I run" into "a tool my team can use."

1. **Push this folder to a GitHub repository** (can be private).
2. Go to **share.streamlit.io** and sign in with your GitHub account.
3. Click **New app**, select this repository and branch, and set the main
   file path to `app.py`.
4. Before deploying, go to **Advanced settings → Secrets** and add:
   ```
   ANTHROPIC_API_KEY = "sk-ant-your-key-here"
   ```
   This means your teammates never see or need their own API key — the app
   uses yours automatically, and it's never exposed in the code or visible
   to users.
5. Click **Deploy**. Streamlit gives you a public URL like
   `https://your-app-name.streamlit.app` — share that link with anyone who
   needs to use the tool.

Note on cost: since the deployed app uses your API key for every request,
you're paying for usage across everyone who uses it. Keep an eye on usage
in the Anthropic Console if you share this widely, or consider adding a
simple password gate (Streamlit supports this via `st.text_input` +
secrets comparison) if it's going out beyond your immediate team.

## Why this design

- **Generic file trimming, not hardcoded columns** — the app doesn't assume
  a specific report format. It looks for columns matching known-useful
  patterns (keyword, position, volume, difficulty, title, URL, etc.) across
  whatever export you give it, so it works whether you're researching law
  firms, running shoes, or anything else — no code changes needed per project.
- **Secondary keywords are guaranteed, not just suggested** — anything you
  type in that field is force-included in the brief even if the AI's own
  suggestions didn't happen to surface it.
- **Robust to messy exports** — Ahrefs/SEMrush files are often UTF-16
  encoded and tab-separated despite the `.csv` extension. The app tries
  multiple encodings and delimiters automatically instead of erroring out.


> Ahrefs/SEMrush exports — including automated handling of inconsistent
> file encodings and delimiters, and token-budget-aware data trimming for
> large competitive research exports.
