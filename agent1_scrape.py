"""
Agent 1 — Scraper
Pulls top AI/ML/automation stories from three sources:
  - HackerNews  (top 30, keyword filtered)
  - ProductHunt (top 5 today, ai / developer-tools topics)
  - Reddit r/artificial (top 10 today, no auth needed)

Saves combined results to data/items_YYYY-MM-DD.json
"""

import json
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# ── Keywords to keep from HackerNews ─────────────────────────────────────────

AI_KEYWORDS = {
    # Core AI/ML
    "ai", "artificial intelligence", "machine learning", "ml", "llm", "gpt",
    "claude", "openai", "anthropic", "groq", "llama", "mistral", "gemini",
    "deepseek", "qwen", "phi", "grok", "perplexity", "cohere",
    # Techniques
    "neural", "deep learning", "rag", "vector", "embedding", "fine-tun",
    "inference", "transformer", "diffusion", "multimodal", "text-to",
    "image generation", "reasoning", "benchmark",
    # Frameworks & tools
    "langchain", "langgraph", "llamaindex", "ollama", "hugging face",
    "pytorch", "tensorflow", "copilot", "cursor", "codeium", "replit",
    # Automation & dev
    "automation", "agent", "agentic", "workflow", "pipeline", "scraper",
    "n8n", "zapier", "make.com", "github actions", "cron",
    # Stack
    "python", "vercel", "next.js", "typescript", "supabase", "fastapi",
    # Business
    "saas", "open source", "self-hosted", "api", "upwork", "freelance",
    "solopreneur", "indie hacker", "devtools", "startup", "launch",
    # Broad tech that often correlates
    "model", "chatbot", "assistant", "autonomous", "prompt",
}


# ── HackerNews (via Algolia API — more reliable, keyword-searchable) ──────────
# Firebase endpoint is sometimes firewalled; Algolia is the official HN search API.

HN_SEARCH_QUERIES = [
    "AI LLM automation agent",
    "machine learning open source",
    "Claude OpenAI Anthropic Groq",
    "python scraper pipeline workflow",
    "SaaS developer tools launch",
]


def scrape_hackernews(limit: int = 30) -> list[dict]:
    print("  [HN] Fetching stories via Algolia HN Search API...")
    base = "https://hn.algolia.com/api/v1/search"
    seen_ids = set()
    items    = []

    for query in HN_SEARCH_QUERIES:
        if len(items) >= limit:
            break
        try:
            resp = requests.get(
                base,
                params={
                    "query":       query,
                    "tags":        "story",
                    "hitsPerPage": 15,
                    "numericFilters": "points>5",  # filter out very low-signal posts
                },
                timeout=10,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
        except Exception as e:
            print(f"  [HN] Query '{query}' failed: {e}")
            continue

        for hit in hits:
            story_id = hit.get("objectID", "")
            if story_id in seen_ids:
                continue
            seen_ids.add(story_id)

            title = hit.get("title", "")
            if not title:
                continue

            items.append({
                "source":    "HackerNews",
                "title":     title,
                "url":       hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                "hn_url":    f"https://news.ycombinator.com/item?id={story_id}",
                "score":     hit.get("points", 0),
                "comments":  hit.get("num_comments", 0),
                "author":    hit.get("author", ""),
                "timestamp": hit.get("created_at_i", 0),
            })

            if len(items) >= limit:
                break

        time.sleep(0.2)

    print(f"  [HN] {len(items)} stories found")
    return items


# ── ProductHunt ───────────────────────────────────────────────────────────────

PH_QUERY = """
query TodaysPosts($after: String) {
  posts(order: VOTES, first: 20, after: $after) {
    nodes {
      id
      name
      tagline
      url
      votesCount
      topics {
        nodes { name slug }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

PH_TARGET_TOPICS = {
    "artificial-intelligence", "ai", "developer-tools", "machine-learning",
    "productivity", "no-code", "automation", "saas", "api", "open-source",
}


def scrape_producthunt(limit: int = 5) -> list[dict]:
    token = os.environ.get("PRODUCTHUNT_TOKEN", "")
    if not token:
        print("  [PH] PRODUCTHUNT_TOKEN not set — skipping ProductHunt")
        return []

    print("  [PH] Fetching today's posts...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }

    try:
        resp = requests.post(
            "https://api.producthunt.com/v2/api/graphql",
            headers=headers,
            json={"query": PH_QUERY, "variables": {"after": None}},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [PH] Request failed: {e}")
        return []

    if "errors" in data:
        print(f"  [PH] API error: {data['errors']}")
        return []

    posts = data.get("data", {}).get("posts", {}).get("nodes", [])
    items = []

    for post in posts:
        topic_slugs = {t["slug"] for t in post.get("topics", {}).get("nodes", [])}
        if not topic_slugs.intersection(PH_TARGET_TOPICS):
            continue

        topic_names = [t["name"] for t in post.get("topics", {}).get("nodes", [])]
        items.append({
            "source":   "ProductHunt",
            "title":    f"{post['name']} — {post['tagline']}",
            "url":      post.get("url", f"https://www.producthunt.com/posts/{post['id']}"),
            "votes":    post.get("votesCount", 0),
            "topics":   topic_names,
            "author":   "",
            "timestamp": 0,
        })

        if len(items) >= limit:
            break

    print(f"  [PH] {len(items)} relevant products found")
    return items


# ── Reddit r/artificial ───────────────────────────────────────────────────────

def scrape_reddit(limit: int = 10) -> list[dict]:
    print("  [Reddit] Fetching r/artificial top posts...")

    headers = {"User-Agent": "JarvisAIBriefing/1.0 (daily news agent)"}
    url = "https://www.reddit.com/r/artificial/top.json"
    params = {"limit": 25, "t": "day"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [Reddit] Request failed: {e}")
        return []

    posts = data.get("data", {}).get("children", [])
    items = []

    for post in posts:
        p = post.get("data", {})
        if p.get("stickied") or p.get("is_self") and len(p.get("selftext", "")) < 30:
            continue

        items.append({
            "source":    "Reddit r/artificial",
            "title":     p.get("title", ""),
            "url":       p.get("url") or f"https://reddit.com{p.get('permalink', '')}",
            "reddit_url": f"https://reddit.com{p.get('permalink', '')}",
            "score":     p.get("score", 0),
            "comments":  p.get("num_comments", 0),
            "author":    p.get("author", ""),
            "timestamp": int(p.get("created_utc", 0)),
        })

        if len(items) >= limit:
            break

    print(f"  [Reddit] {len(items)} posts found")
    return items


# ── Save ──────────────────────────────────────────────────────────────────────

def save(items: list[dict], out_dir: str = "data") -> str:
    Path(out_dir).mkdir(exist_ok=True)
    date_str = date.today().isoformat()
    path = Path(out_dir) / f"items_{date_str}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved {len(items)} items -> {path}")
    return str(path)


# ── Entry point ───────────────────────────────────────────────────────────────

def run() -> list[dict]:
    print(f"\n{'='*60}")
    print("  AGENT 1 -- SCRAPER")
    print(f"{'='*60}\n")

    hn_items     = scrape_hackernews(limit=30)
    ph_items     = scrape_producthunt(limit=5)
    reddit_items = scrape_reddit(limit=10)

    all_items = hn_items + ph_items + reddit_items
    print(f"\n  Total items collected: {len(all_items)}")
    print(f"    HackerNews:  {len(hn_items)}")
    print(f"    ProductHunt: {len(ph_items)}")
    print(f"    Reddit:      {len(reddit_items)}")

    save(all_items)
    return all_items


if __name__ == "__main__":
    run()
