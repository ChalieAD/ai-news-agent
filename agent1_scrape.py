"""
Agent 1 — Scraper
Pulls the latest 5 articles from three curated sources:
  - Anthropic News   (anthropic.com/news)
  - HuggingFace Blog (huggingface.co/blog)
  - VentureBeat AI   (venturebeat.com/category/ai/)

Saves combined results to data/items_YYYY-MM-DD.json
"""

import json
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}
LIMIT = 5


# ── Anthropic News ────────────────────────────────────────────────────────────

def scrape_anthropic(limit: int = LIMIT) -> list[dict]:
    print("  [Anthropic] Fetching anthropic.com/news...")
    url = "https://www.anthropic.com/news"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [Anthropic] Request failed: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    items = []

    # Articles are <a> tags linking to /news/* with a title inside
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("/news/") or href == "/news":
            continue

        title_el = a.find(["h2", "h3", "h4", "p"])
        title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)
        if not title or len(title) < 10:
            continue

        full_url = f"https://www.anthropic.com{href}" if href.startswith("/") else href

        # Deduplicate by URL
        if any(i["url"] == full_url for i in items):
            continue

        items.append({
            "source": "Anthropic News",
            "title": title,
            "url": full_url,
        })

        if len(items) >= limit:
            break

    print(f"  [Anthropic] {len(items)} articles found")
    return items


# ── HuggingFace Blog ──────────────────────────────────────────────────────────

def scrape_huggingface(limit: int = LIMIT) -> list[dict]:
    print("  [HuggingFace] Fetching huggingface.co/blog...")
    url = "https://huggingface.co/blog"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [HuggingFace] Request failed: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    items = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Blog post URLs look like /blog/some-slug (not the /blog index itself)
        if not href.startswith("/blog/") or href == "/blog/":
            continue

        title_el = a.find(["h2", "h3", "h4"])
        title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)
        if not title or len(title) < 10:
            continue

        full_url = f"https://huggingface.co{href}" if href.startswith("/") else href

        if any(i["url"] == full_url for i in items):
            continue

        items.append({
            "source": "HuggingFace Blog",
            "title": title,
            "url": full_url,
        })

        if len(items) >= limit:
            break

    print(f"  [HuggingFace] {len(items)} articles found")
    return items


# ── VentureBeat AI ────────────────────────────────────────────────────────────

def scrape_venturebeat(limit: int = LIMIT) -> list[dict]:
    print("  [VentureBeat] Fetching venturebeat.com/category/ai/...")
    url = "https://venturebeat.com/category/ai/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [VentureBeat] Request failed: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    items = []

    for article in soup.find_all("article"):
        a = article.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        if "venturebeat.com" not in href and not href.startswith("/"):
            continue

        title_el = article.find(["h2", "h3", "h4"])
        title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)
        if not title or len(title) < 10:
            continue

        full_url = href if href.startswith("http") else f"https://venturebeat.com{href}"

        if any(i["url"] == full_url for i in items):
            continue

        items.append({
            "source": "VentureBeat AI",
            "title": title,
            "url": full_url,
        })

        if len(items) >= limit:
            break

    print(f"  [VentureBeat] {len(items)} articles found")
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

    anthropic_items  = scrape_anthropic(limit=LIMIT)
    time.sleep(0.5)
    hf_items         = scrape_huggingface(limit=LIMIT)
    time.sleep(0.5)
    vb_items         = scrape_venturebeat(limit=LIMIT)

    all_items = anthropic_items + hf_items + vb_items
    print(f"\n  Total items collected: {len(all_items)}")
    print(f"    Anthropic News:  {len(anthropic_items)}")
    print(f"    HuggingFace Blog:{len(hf_items)}")
    print(f"    VentureBeat AI:  {len(vb_items)}")

    save(all_items)
    return all_items


if __name__ == "__main__":
    run()
