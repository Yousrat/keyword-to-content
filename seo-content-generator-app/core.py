"""
Core SEO content generation logic.
Shared by both the command-line script and the Streamlit web app.
"""

import json
import re
import io
from dataclasses import dataclass, asdict

import pandas as pd
from anthropic import Anthropic

MODEL = "claude-sonnet-4-5"


@dataclass
class ContentBrief:
    title: str
    meta_description: str
    search_intent: str
    target_keyword: str
    secondary_keywords: list
    header_outline: list
    target_word_count: int
    tone: str


# ---------------------------------------------------------------------------
# File handling: robust reading of messy Ahrefs/SEMrush exports
# ---------------------------------------------------------------------------

def read_export_any_format(file_bytes: bytes) -> pd.DataFrame:
    """
    Reads an Ahrefs/SEMrush-style export regardless of encoding (UTF-8,
    UTF-16 are both common) or delimiter (comma or tab, despite the .csv
    extension).
    """
    last_error = None
    for encoding in ("utf-8", "utf-16", "utf-16-le", "latin-1"):
        for sep in ("\t", ","):
            try:
                df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    encoding=encoding,
                    sep=sep,
                    on_bad_lines="skip",
                    engine="python",
                )
                if df.shape[1] > 1:
                    return df
            except Exception as e:
                last_error = e
                continue
    raise ValueError(f"Could not parse file with any known encoding/delimiter: {last_error}")


# Column name patterns worth keeping when trimming an unknown export.
# Matched case-insensitively as substrings.
PRIORITY_COLUMN_PATTERNS = [
    "keyword", "url", "title", "position", "volume", "difficulty", "kd",
    "traffic", "words", "page type", "intent", "organic position",
]


def trim_dataframe(df: pd.DataFrame, max_rows: int = 20, max_cols: int = 12) -> pd.DataFrame:
    """
    Generic trimmer for any Ahrefs/SEMrush-style export:
      - Keeps columns matching known-useful patterns (keyword, position,
        volume, etc.) up to max_cols. Falls back to the first N columns
        if nothing matches.
      - Sorts by a meaningful column if one exists (Volume > Traffic > Position)
      - Truncates to max_rows.
    This keeps the output small enough to stay well under API token limits
    without hardcoding assumptions about which specific report type it is.
    """
    cols = list(df.columns)

    matched = [c for c in cols if any(p in c.lower() for p in PRIORITY_COLUMN_PATTERNS)]
    if matched:
        keep_cols = matched[:max_cols]
    else:
        keep_cols = cols[:max_cols]

    trimmed = df[keep_cols].copy()

    sort_col = None
    for candidate in ("Volume", "volume", "Traffic", "traffic", "Position", "position"):
        if candidate in trimmed.columns:
            sort_col = candidate
            break

    if sort_col:
        ascending = "position" in sort_col.lower()
        trimmed = trimmed.sort_values(sort_col, ascending=ascending, na_position="last")

    return trimmed.head(max_rows)


def build_competitor_notes(files: dict) -> str:
    """
    files: dict mapping a label (e.g. "SERP Overview") to raw file bytes.
    Returns a single combined, trimmed text block safe to pass to the API.
    """
    sections = []
    for label, file_bytes in files.items():
        if file_bytes is None:
            continue
        try:
            df = read_export_any_format(file_bytes)
            trimmed = trim_dataframe(df)
            sections.append(f"=== {label} ===\n{trimmed.to_string(index=False)}\n")
        except Exception as e:
            sections.append(f"=== {label} ===\n[Could not parse file: {e}]\n")
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Stage 1: Brief generation
# ---------------------------------------------------------------------------

def generate_brief(
    client: Anthropic,
    keyword: str,
    competitor_notes: str,
    tone: str,
    user_secondary_keywords: list = None,
) -> ContentBrief:
    system_prompt = (
        "You are an expert SEO content strategist. You produce content briefs "
        "used by writers to draft high-ranking, genuinely useful articles. "
        "Respond ONLY with valid JSON matching the exact schema given. "
        "No markdown fences, no preamble, no commentary."
    )

    schema_instructions = """
Return JSON with exactly these keys:
{
  "title": "SEO-optimized H1, under 60 characters",
  "meta_description": "under 155 characters, includes target keyword",
  "search_intent": "one of: informational, commercial, transactional, navigational",
  "target_keyword": "the primary keyword",
  "secondary_keywords": ["3-8 related/LSI keywords to naturally include"],
  "header_outline": [
    {"level": "H2", "text": "..."},
    {"level": "H3", "text": "..."}
  ],
  "target_word_count": 1200,
  "tone": "the requested tone"
}
"""

    user_supplied = ""
    if user_secondary_keywords:
        user_supplied = (
            "\nThe user has also specified these secondary keywords that MUST "
            "be included in secondary_keywords and woven into the outline where relevant:\n"
            + ", ".join(user_secondary_keywords)
        )

    user_prompt = f"""
Target keyword: {keyword}
Requested tone: {tone}

Competitor / SERP / keyword-gap context:
{competitor_notes if competitor_notes else "None provided - infer typical competitive angles for this keyword."}
{user_supplied}

{schema_instructions}

Build an outline that beats typical competitor content by covering angles
they miss, not just matching their structure.
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = response.content[0].text.strip()
    raw_text = re.sub(r"^```(json)?|```$", "", raw_text, flags=re.MULTILINE).strip()
    data = json.loads(raw_text)

    # Guarantee any user-supplied secondary keywords survive even if the
    # model's JSON omitted one.
    if user_secondary_keywords:
        existing = set(k.lower() for k in data.get("secondary_keywords", []))
        for kw in user_secondary_keywords:
            if kw.lower() not in existing:
                data["secondary_keywords"].append(kw)

    return ContentBrief(**data)


# ---------------------------------------------------------------------------
# Stage 2: Draft generation
# ---------------------------------------------------------------------------

def generate_draft(client: Anthropic, brief: ContentBrief) -> str:
    system_prompt = (
        "You are a skilled SEO content writer. Write natural, helpful, "
        "human-sounding content that satisfies search intent. Never keyword-stuff. "
        "Follow the provided outline structure using markdown headers."
    )

    outline_text = "\n".join(f"{h['level']}: {h['text']}" for h in brief.header_outline)

    user_prompt = f"""
Write a full article draft based on this brief:

Title: {brief.title}
Meta description: {brief.meta_description}
Search intent: {brief.search_intent}
Primary keyword: {brief.target_keyword}
Secondary keywords to weave in naturally: {", ".join(brief.secondary_keywords)}
Tone: {brief.tone}
Target length: ~{brief.target_word_count} words

Outline to follow (use as markdown headers):
{outline_text}

Write the full article in markdown, starting with "# {brief.title}".
Include the primary keyword in the first 100 words. Keep paragraphs short
and scannable. Do not include a meta description in the output itself.
"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text.strip()


# ---------------------------------------------------------------------------
# Stage 3: SEO validation
# ---------------------------------------------------------------------------

def check_seo(draft: str, brief: ContentBrief) -> dict:
    words = re.findall(r"\b\w+\b", draft.lower())
    word_count = len(words)

    keyword_terms = brief.target_keyword.lower().split()
    keyword_hits = len(re.findall(re.escape(brief.target_keyword.lower()), draft.lower()))
    keyword_density = round((keyword_hits * len(keyword_terms) / word_count) * 100, 2) if word_count else 0

    h2_count = len(re.findall(r"^##\s", draft, flags=re.MULTILINE))
    h3_count = len(re.findall(r"^###\s", draft, flags=re.MULTILINE))
    has_h1 = bool(re.search(r"^#\s", draft, flags=re.MULTILINE))

    first_100_words = " ".join(words[:100])
    keyword_in_intro = brief.target_keyword.lower() in first_100_words

    return {
        "word_count": word_count,
        "target_word_count": brief.target_word_count,
        "word_count_within_10pct": abs(word_count - brief.target_word_count) <= brief.target_word_count * 0.1,
        "keyword_density_pct": keyword_density,
        "keyword_density_healthy": 0.5 <= keyword_density <= 2.5,
        "has_h1": has_h1,
        "h2_count": h2_count,
        "h3_count": h3_count,
        "keyword_in_first_100_words": keyword_in_intro,
        "title_length_ok": len(brief.title) <= 60,
        "meta_description_length_ok": len(brief.meta_description) <= 155,
    }
