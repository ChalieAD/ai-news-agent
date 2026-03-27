"""
Agent 2 — AI Scorer
Loads today's scraped items, sends them to Groq (LLaMA 3.3 70B) for scoring,
and saves only items that score 6 or above.

Scoring criteria: relevance to an AI automation developer who builds Python
pipelines, uses Claude/Groq/GitHub Actions/Vercel, and sells AI services.

Output: data/scored_YYYY-MM-DD.json
"""

import json
import os
import re
from datetime import date
from pathlib import Path

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

MIN_SCORE = 6
BATCH_SIZE = 20   # items per Groq call (stays well within context limits)


# ── Load ──────────────────────────────────────────────────────────────────────

def load_latest(data_dir: str = "data") -> list[dict]:
    files = sorted(Path(data_dir).glob("items_*.json"), reverse=True)
    if not files:
        raise FileNotFoundError(
            f"No items files in '{data_dir}/'. Run agent1_scrape.py first."
        )
    path = files[0]
    print(f"  Loading: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── Groq scoring ──────────────────────────────────────────────────────────────

SCORE_PROMPT = """You are scoring news items for Aryan, a 24-year-old AI automation developer who:
- Builds AI automation pipelines in Python (agents, scrapers, schedulers)
- Uses Claude, Groq, LLaMA, GitHub Actions, Vercel, Next.js daily
- Sells AI automation services on Upwork and Fiverr
- Wants to know about new AI tools, model releases, and product launches he can apply today

Score each item in the JSON array below. For each item return:
- "id": the same id from input
- "score": integer 1-10 (10 = must read, 1 = irrelevant)
- "reason": one punchy sentence explaining the score
- "category": exactly one of NEW_TOOL | TUTORIAL | BUSINESS_OPP | JUST_NEWS
- "action_required": true if Aryan should act on this today, false otherwise

Scoring guide:
- 9-10: New AI tool/model/API he can use right now, model release, or direct business opportunity
- 7-8:  Product launch, framework update, or useful practical insight
- 6:    Mildly relevant — worth knowing but no immediate action
- 1-5:  Academic research papers, highly technical ML theory, off-topic, or too generic — score these LOW

Important: penalise anything that is a research paper, benchmark study, or academic/theoretical content. Aryan wants practical tools and launches, not papers.

Items to score:
{items_json}

Return ONLY a valid JSON array. No markdown, no explanation, no code block. Just the array."""


def _extract_json_array(text: str) -> list:
    """Extract JSON array from LLM response, handling markdown code blocks."""
    text = text.strip()
    # Strip markdown code blocks if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # Find the first [ and last ]
    start = text.find("[")
    end   = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array found in response:\n{text[:200]}")
    return json.loads(text[start:end + 1])


def score_batch(items: list[dict], client: Groq) -> list[dict]:
    """Score a batch of items in a single Groq call."""
    slim = [
        {"id": i, "title": item["title"], "source": item["source"]}
        for i, item in enumerate(items)
    ]
    prompt = SCORE_PROMPT.format(items_json=json.dumps(slim, indent=2))

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=4096,
        temperature=0.2,   # low temp for consistent JSON
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content
    return _extract_json_array(raw)


def score_all(items: list[dict], api_key: str) -> list[dict]:
    """Score all items in batches, merge scores back into original dicts."""
    client = Groq(api_key=api_key)
    scored = []

    total_batches = (len(items) + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_num in range(total_batches):
        batch = items[batch_num * BATCH_SIZE:(batch_num + 1) * BATCH_SIZE]
        print(f"  Scoring batch {batch_num + 1}/{total_batches} "
              f"({len(batch)} items) via Groq...")

        try:
            results = score_batch(batch, client)
        except Exception as e:
            print(f"  [!] Batch {batch_num + 1} failed: {e}")
            print("      Skipping batch — items will not appear in report.")
            continue

        # Map id -> score result, merge into original item
        result_map = {r["id"]: r for r in results}
        for local_id, item in enumerate(batch):
            r = result_map.get(local_id, {})
            merged = {
                **item,
                "ai_score":       r.get("score", 0),
                "ai_reason":      r.get("reason", ""),
                "ai_category":    r.get("category", "JUST_NEWS"),
                "action_required": r.get("action_required", False),
            }
            scored.append(merged)

    return scored


# ── Filter + sort ─────────────────────────────────────────────────────────────

def filter_and_rank(scored: list[dict], min_score: int = MIN_SCORE) -> list[dict]:
    passing = [i for i in scored if i.get("ai_score", 0) >= min_score]
    return sorted(passing, key=lambda x: x["ai_score"], reverse=True)


# ── Save ──────────────────────────────────────────────────────────────────────

def save(items: list[dict], out_dir: str = "data") -> str:
    Path(out_dir).mkdir(exist_ok=True)
    date_str = date.today().isoformat()
    path = Path(out_dir) / f"scored_{date_str}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"  Saved {len(items)} scored items -> {path}")
    return str(path)


# ── Entry point ───────────────────────────────────────────────────────────────

def run() -> list[dict]:
    print(f"\n{'='*60}")
    print("  AGENT 2 -- AI SCORER")
    print(f"{'='*60}\n")

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not set.\n"
            "Add it to your .env file: GROQ_API_KEY=your_key_here\n"
            "Get a free key at: console.groq.com"
        )

    items = load_latest()
    print(f"  {len(items)} items loaded\n")

    scored = score_all(items, api_key)
    ranked = filter_and_rank(scored, MIN_SCORE)

    print(f"\n  {len(scored)} items scored")
    print(f"  {len(ranked)} items passed threshold (score >= {MIN_SCORE})")

    # Print score distribution
    buckets = {"9-10": 0, "7-8": 0, "6": 0, "1-5": 0}
    for item in scored:
        s = item.get("ai_score", 0)
        if s >= 9:   buckets["9-10"] += 1
        elif s >= 7: buckets["7-8"]  += 1
        elif s >= 6: buckets["6"]    += 1
        else:        buckets["1-5"]  += 1
    print(f"\n  Score distribution:")
    for band, count in buckets.items():
        print(f"    {band:>5}: {count}")

    save(ranked)
    return ranked


if __name__ == "__main__":
    run()
