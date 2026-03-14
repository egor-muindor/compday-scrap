import asyncio
import json
import logging
from pathlib import Path

from playwright.async_api import async_playwright

from scraper.config import (
    CATEGORIES,
    DELAY_BETWEEN_CATEGORIES,
    HEADLESS,
    LISTING_PAGE_SIZE,
    NAVIGATION_TIMEOUT,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path("data/listing")


async def _wait_for_items_ready(page, timeout: float = 20) -> bool:
    """Wait until #catItems has opacity 1 (animation complete) and visible items exist."""
    for _ in range(int(timeout * 2)):
        ready = await page.evaluate("""
            (() => {
                const container = document.getElementById('catItems');
                if (!container) return false;
                const opacity = parseFloat(getComputedStyle(container).opacity);
                if (opacity < 0.9) return false;
                const visible = container.querySelectorAll('div.item:not([style*="display: none"]):not([style*="display:none"])');
                return visible.length > 0;
            })()
        """)
        if ready:
            return True
        await asyncio.sleep(0.5)
    return False


EXTRACT_ITEMS_JS = """
    (() => {
        const items = document.querySelectorAll('#catItems > div.item');
        const results = [];
        for (const item of items) {
            if (getComputedStyle(item).display === 'none') continue;
            const nameEl = item.querySelector('a.name');
            const priceEl = item.querySelector('b.actual.price');
            const descEl = item.querySelector('span.description');
            results.push({
                title: nameEl ? nameEl.textContent.trim() : '',
                price: priceEl ? priceEl.textContent.trim() : '',
                specs: descEl ? descEl.textContent.trim() : '',
                url: nameEl ? nameEl.href : '',
            });
        }
        return results;
    })()
"""


async def _scrape_page(page) -> list[dict]:
    """Extract visible items from current page."""
    return await page.evaluate(EXTRACT_ITEMS_JS)


async def _scrape_with_hash(page, category: dict, use_base: bool) -> list[dict]:
    """Scrape category using hash-fragment filters + 'Все' button."""
    url = category["base_url"] if use_base else category["filtered_url"]
    slug = category["slug"]

    await page.goto(url, wait_until="networkidle", timeout=NAVIGATION_TIMEOUT)

    if not await _wait_for_items_ready(page):
        logger.warning(f"Items not ready for {slug}, saving HTML for analysis")
        html = await page.content()
        debug_path = DATA_DIR / f"{slug}_debug.html"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(html, encoding="utf-8")
        logger.info(f"Debug HTML saved to {debug_path}")
        return []

    show_all_btn = await page.query_selector('a[href="#onpage-all"]')
    if show_all_btn:
        logger.info(f"Clicking 'Все' to load all items for {slug}")
        await show_all_btn.click()
        await _wait_for_items_ready(page)

    return await _scrape_page(page)


async def _scrape_with_pagination(page, category: dict, use_base: bool) -> list[dict]:
    """Scrape category using query-parameter pagination."""
    base_url = category["base_url"]
    query_filters = "" if use_base else category.get("query_filters", "")
    slug = category["slug"]
    all_results = []
    page_num = 1

    while True:
        params = f"?p={page_num}&onpage={LISTING_PAGE_SIZE}"
        if query_filters:
            params += f"&{query_filters}"
        url = base_url + params

        logger.info(f"Page {page_num}: {url}")
        await page.goto(url, wait_until="networkidle", timeout=NAVIGATION_TIMEOUT)

        if not await _wait_for_items_ready(page, timeout=10):
            if page_num == 1:
                logger.warning(f"No items on first page for {slug}")
            break

        items = await _scrape_page(page)
        if not items:
            break

        all_results.extend(items)
        logger.info(f"Page {page_num}: {len(items)} items (total: {len(all_results)})")

        if len(items) < LISTING_PAGE_SIZE:
            break

        page_num += 1
        await asyncio.sleep(DELAY_BETWEEN_CATEGORIES)

    return all_results


async def scrape_category(page, category: dict, use_base: bool = False) -> list[dict]:
    slug = category["slug"]
    name = category["name"]
    has_query_filters = category.get("query_filters")
    has_hash_filters = category.get("filtered_url")

    logger.info(f"Scraping listing: {name} ({slug})")

    if has_query_filters and not use_base:
        results = await _scrape_with_pagination(page, category, use_base)
    elif has_hash_filters or use_base:
        results = await _scrape_with_hash(page, category, use_base)
    else:
        # No filters at all — use base URL with pagination
        results = await _scrape_with_pagination(page, category, use_base)

    logger.info(f"Found {len(results)} products in {slug}")
    return results


def save_listing(slug: str, data: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{slug}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Saved {len(data)} items to {path}")


def update_prices(slug: str, fresh: list[dict]) -> None:
    """Update only prices in existing listing, keeping other data intact."""
    path = DATA_DIR / f"{slug}.json"
    if not path.exists():
        save_listing(slug, fresh)
        return

    existing = json.loads(path.read_text(encoding="utf-8"))
    existing_by_url = {item["url"]: item for item in existing}

    fresh_by_url = {item["url"]: item for item in fresh}

    # Update prices for existing items, add new items
    updated = []
    for item in fresh:
        if item["url"] in existing_by_url:
            old = existing_by_url[item["url"]]
            if old["price"] != item["price"]:
                logger.info(f"Price changed: {item['title']}: {old['price']} -> {item['price']}")
            old["price"] = item["price"]
            updated.append(old)
        else:
            logger.info(f"New item: {item['title']}")
            updated.append(item)

    # Log removed items
    for url in existing_by_url:
        if url not in fresh_by_url:
            logger.info(f"Removed: {existing_by_url[url]['title']}")

    path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Updated prices for {slug}: {len(updated)} items")


async def scrape_listings(
    categories: list[dict] | None = None,
    use_base: bool = False,
    prices_only: bool = False,
) -> None:
    if categories is None:
        categories = CATEGORIES

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        page = await browser.new_page()

        for i, cat in enumerate(categories):
            try:
                items = await scrape_category(page, cat, use_base=use_base)
                if prices_only:
                    update_prices(cat["slug"], items)
                else:
                    save_listing(cat["slug"], items)
            except Exception as e:
                logger.error(f"Failed to scrape {cat['slug']}: {e}")

            if i < len(categories) - 1:
                await asyncio.sleep(DELAY_BETWEEN_CATEGORIES)

        await browser.close()
