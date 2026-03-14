import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
from selectolax.parser import HTMLParser

from scraper.config import (
    CATEGORIES,
    DETAIL_WORKERS,
    random_delay,
)

logger = logging.getLogger(__name__)

LISTING_DIR = Path("data/listing")
DETAILS_DIR = Path("data/details")
PROGRESS_FILE = Path("data/progress.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}


def load_progress() -> set[str]:
    if PROGRESS_FILE.exists():
        data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        return set(data)
    return set()


def save_progress(done: set[str]) -> None:
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(sorted(done), ensure_ascii=False), encoding="utf-8")


def reset_progress() -> None:
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
        logger.info("Progress reset")


def parse_product_page(html: str, url: str) -> dict:
    tree = HTMLParser(html)
    data = {}

    # Title
    h1 = tree.css_first("h1")
    data["title"] = h1.text(strip=True) if h1 else ""

    # Product code
    code_el = tree.css_first("#catCode")
    data["code"] = code_el.text(strip=True).replace("КОД ТОВАРА:", "").strip() if code_el else ""

    # Prices
    cash_price = tree.css_first("b.actual.cash.price")
    data["price"] = cash_price.text(strip=True) if cash_price else ""

    card_price = tree.css_first("b.card.price")
    data["card_price"] = card_price.text(strip=True) if card_price else ""

    # Availability
    data["availability"] = ""
    for p in tree.css("p"):
        text = p.text()
        if "Товар доступен" in text:
            strong = p.css_first("strong")
            data["availability"] = strong.text(strip=True) if strong else text.strip()
            break

    # Specs table
    specs = {}
    tab_specs = tree.css_first("#tab-specs")
    if tab_specs:
        for row in tab_specs.css("table tr"):
            cells = row.css("td")
            if len(cells) == 1:
                pass  # section header
            elif len(cells) >= 2:
                key = cells[0].text(strip=True)
                value = cells[1].text(strip=True)
                if key and value:
                    specs[key] = value
    data["specs"] = specs

    # Images
    images = []
    for img in tree.css("#cardImg a[data-gallery='item'] img"):
        src = img.attributes.get("src", "")
        if src:
            if not src.startswith("http"):
                src = "https://www.compday.ru" + src
            images.append(src)
    data["images"] = images

    # Warranty (from meta description)
    data["warranty"] = ""
    meta_desc = tree.css_first('meta[name="description"]')
    if meta_desc:
        content = meta_desc.attributes.get("content", "")
        match = re.search(r"Гарантия\s+([^.➤]+)", content)
        if match:
            data["warranty"] = match.group(1).strip()

    data["url"] = url
    data["scraped_at"] = datetime.now(timezone.utc).isoformat()
    return data


async def _worker(
    worker_id: int,
    queue: asyncio.Queue,
    client: httpx.AsyncClient,
    results: list[dict],
    done: set[str],
    results_path: Path,
    lock: asyncio.Lock,
) -> None:
    while True:
        try:
            url = queue.get_nowait()
        except asyncio.QueueEmpty:
            return

        try:
            logger.info(f"[W{worker_id}] Scraping: {url}")
            resp = await client.get(url)
            resp.raise_for_status()
            detail = parse_product_page(resp.text, url)

            async with lock:
                results.append(detail)
                done.add(url)
                save_progress(done)
                results_path.write_text(
                    json.dumps(results, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
        except Exception as e:
            logger.error(f"[W{worker_id}] Failed: {url}: {e}")

        delay = random_delay()
        await asyncio.sleep(delay)


async def scrape_details(
    categories: list[dict] | None = None,
    reset: bool = False,
    workers: int | None = None,
) -> None:
    if categories is None:
        categories = CATEGORIES

    if reset:
        reset_progress()

    num_workers = workers or DETAIL_WORKERS
    done = load_progress()

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        for cat in categories:
            slug = cat["slug"]
            listing_path = LISTING_DIR / f"{slug}.json"

            if not listing_path.exists():
                logger.warning(f"No listing for {slug}, run 'listing' first")
                continue

            items = json.loads(listing_path.read_text(encoding="utf-8"))
            urls = [item["url"] for item in items if item.get("url")]

            to_scrape = [u for u in urls if u not in done]
            logger.info(f"Details for {slug}: {len(to_scrape)} remaining ({len(urls) - len(to_scrape)} already done), {num_workers} workers")

            if not to_scrape:
                continue

            results_path = DETAILS_DIR / f"{slug}.json"
            DETAILS_DIR.mkdir(parents=True, exist_ok=True)

            existing = []
            if results_path.exists() and not reset:
                existing = json.loads(results_path.read_text(encoding="utf-8"))

            queue: asyncio.Queue[str] = asyncio.Queue()
            for u in to_scrape:
                queue.put_nowait(u)

            lock = asyncio.Lock()
            actual_workers = min(num_workers, len(to_scrape))

            tasks = [
                asyncio.create_task(_worker(i, queue, client, existing, done, results_path, lock))
                for i in range(actual_workers)
            ]
            await asyncio.gather(*tasks)

    logger.info("Done")
