import argparse
import asyncio
import logging

from scraper.config import CATEGORIES
from scraper.listing import scrape_listings
from scraper.detail import scrape_details


def get_categories(name: str | None) -> list[dict] | None:
    if name is None:
        return None
    for cat in CATEGORIES:
        if cat["slug"] == name:
            return [cat]
    available = ", ".join(c["slug"] for c in CATEGORIES)
    raise ValueError(f"Unknown category: {name}. Available: {available}")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Scraper for compday.ru")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # listing
    listing_parser = subparsers.add_parser("listing", help="Scrape product listings")
    listing_parser.add_argument("--category", type=str, default=None, help="Single category slug")
    listing_parser.add_argument("--base", action="store_true", help="Use base URLs (no filters)")

    # details
    details_parser = subparsers.add_parser("details", help="Scrape product details")
    details_parser.add_argument("--category", type=str, default=None, help="Single category slug")
    details_parser.add_argument("--reset-progress", action="store_true", help="Reset progress tracking")
    details_parser.add_argument("--workers", type=int, default=None, help="Number of parallel workers (default: 3)")

    # update-prices
    prices_parser = subparsers.add_parser("update-prices", help="Update only prices in existing listings")
    prices_parser.add_argument("--category", type=str, default=None, help="Single category slug")
    prices_parser.add_argument("--base", action="store_true", help="Use base URLs (no filters)")

    args = parser.parse_args()

    if args.command == "listing":
        categories = get_categories(args.category)
        asyncio.run(scrape_listings(categories=categories, use_base=args.base))
    elif args.command == "details":
        categories = get_categories(args.category)
        asyncio.run(scrape_details(categories=categories, reset=args.reset_progress, workers=args.workers))
    elif args.command == "update-prices":
        categories = get_categories(args.category)
        asyncio.run(scrape_listings(categories=categories, use_base=args.base, prices_only=True))


if __name__ == "__main__":
    main()
