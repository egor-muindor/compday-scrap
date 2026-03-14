import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

from scraper.config import (
    CATEGORIES,
    HEADLESS,
    NAVIGATION_TIMEOUT,
    random_delay,
)

logger = logging.getLogger(__name__)

LISTING_DIR = Path("data/listing")
DETAILS_DIR = Path("data/details")
PROGRESS_FILE = Path("data/progress.json")


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


async def scrape_product_page(page, url: str) -> dict:
    await page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT)
    # Wait for specs section to render
    try:
        await page.wait_for_selector("#tab-specs", timeout=15_000)
    except Exception:
        pass
    await asyncio.sleep(1)

    data = await page.evaluate("""
        (() => {
            const result = {};

            // Title
            const h1 = document.querySelector('h1');
            result.title = h1 ? h1.textContent.trim() : '';

            // Product code
            const code = document.getElementById('catCode');
            result.code = code ? code.textContent.replace('КОД ТОВАРА:', '').trim() : '';

            // Current price (cash price is the actual selling price)
            const cashPrice = document.querySelector('b.actual.cash.price');
            const cardPrice = document.querySelector('b.card.price');
            result.price = cashPrice ? cashPrice.textContent.trim() : '';
            result.card_price = cardPrice ? cardPrice.textContent.trim() : '';

            // Availability
            const availStrong = document.querySelector('.announce + p strong, p strong[style]');
            result.availability = '';
            const allParas = document.querySelectorAll('p');
            for (const p of allParas) {
                if (p.textContent.includes('Товар доступен')) {
                    const strong = p.querySelector('strong');
                    result.availability = strong ? strong.textContent.trim() : p.textContent.trim();
                    break;
                }
            }

            // Specs table
            const specs = {};
            const specRows = document.querySelectorAll('#tab-specs table tr');
            let currentSection = '';
            for (const row of specRows) {
                const cells = row.querySelectorAll('td');
                if (cells.length === 1) {
                    // Section header
                    currentSection = cells[0].textContent.trim();
                } else if (cells.length >= 2) {
                    const key = cells[0].textContent.trim();
                    const value = cells[1].textContent.trim();
                    if (key && value) {
                        specs[key] = value;
                    }
                }
            }
            result.specs = specs;

            // Images
            const imgEls = document.querySelectorAll('#cardImg a[data-gallery="item"] img');
            result.images = Array.from(imgEls).map(img => img.src).filter(Boolean);

            // Warranty (from meta description)
            const metaDesc = document.querySelector('meta[name="description"]');
            result.warranty = '';
            if (metaDesc) {
                const content = metaDesc.getAttribute('content') || '';
                const match = content.match(/Гарантия\\s+([^.➤]+)/);
                if (match) result.warranty = match[1].trim();
            }

            result.url = window.location.href;
            return result;
        })()
    """)

    data["scraped_at"] = datetime.now(timezone.utc).isoformat()
    return data


async def scrape_details(
    categories: list[dict] | None = None,
    reset: bool = False,
) -> None:
    if categories is None:
        categories = CATEGORIES

    if reset:
        reset_progress()

    done = load_progress()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        page = await browser.new_page()

        for cat in categories:
            slug = cat["slug"]
            listing_path = LISTING_DIR / f"{slug}.json"

            if not listing_path.exists():
                logger.warning(f"No listing for {slug}, run 'listing' first")
                continue

            items = json.loads(listing_path.read_text(encoding="utf-8"))
            urls = [item["url"] for item in items if item.get("url")]

            to_scrape = [u for u in urls if u not in done]
            logger.info(f"Details for {slug}: {len(to_scrape)} remaining ({len(urls) - len(to_scrape)} already done)")

            results_path = DETAILS_DIR / f"{slug}.json"
            DETAILS_DIR.mkdir(parents=True, exist_ok=True)

            existing = []
            if results_path.exists() and not reset:
                existing = json.loads(results_path.read_text(encoding="utf-8"))

            for url in to_scrape:
                try:
                    logger.info(f"Scraping: {url}")
                    detail = await scrape_product_page(page, url)
                    existing.append(detail)

                    done.add(url)
                    save_progress(done)

                    results_path.write_text(
                        json.dumps(existing, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                except Exception as e:
                    logger.error(f"Failed to scrape {url}: {e}")

                delay = random_delay()
                await asyncio.sleep(delay)

        await browser.close()
