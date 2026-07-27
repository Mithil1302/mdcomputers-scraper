"""
mdcomputers_scraper.py

Scrapes product details (name, price, discounted price, URL, image, availability)
from MDComputers.in for a given search term.

Example:
    https://mdcomputers.in/?route=product/search&search=external harddrive

Usage:
    python mdcomputers_scraper.py "external harddrive"
    python mdcomputers_scraper.py "external harddrive" --pages 2 --out results.csv

Author: Mithil
"""

import argparse
import csv
import sys
import time
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://mdcomputers.in/"
SEARCH_ROUTE = "index.php?route=product/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def build_search_url(search_term: str, page: int = 1) -> str:
    """Build the MDComputers search URL for a given term and page number."""
    encoded_term = quote_plus(search_term)
    url = f"{BASE_URL}{SEARCH_ROUTE}&search={encoded_term}"
    if page > 1:
        url += f"&page={page}"
    return url


def fetch_page(url: str, session: requests.Session, retries: int = 3, timeout: int = 15):
    """Fetch a URL with basic retry logic. Returns the response text or None."""
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            print(f"[warn] attempt {attempt}/{retries} failed for {url}: {exc}", file=sys.stderr)
            time.sleep(1.5 * attempt)
    return None


def _clean_text(tag) -> str:
    return tag.get_text(strip=True) if tag else ""


def parse_products(html: str):
    """
    Parse a MDComputers search results page (OpenCart-based storefront) and
    return a list of dicts with product details.

    The theme uses a `product-thumb` (or `product-layout`) wrapper per item,
    with the name in an <h4>/.caption block and prices inside spans whose
    class contains "price". Several fallbacks are used because storefront
    themes tend to tweak class names between updates.
    """
    soup = BeautifulSoup(html, "html.parser")
    products = []

    # Candidate containers for a single product card. Selectors are tried in
    # order (not combined) to avoid matching both a wrapper (.product-layout)
    # and its nested card (.product-thumb) as two separate "products".
    cards = soup.select(".product-thumb")
    if not cards:
        cards = soup.select(".product-layout")
    if not cards:
        # Fallback: some theme variants wrap cards in <div class="product-item">
        cards = soup.select("[class*='product-item']")

    for card in cards:
        # --- Name & product URL ---
        name_tag = card.select_one(".caption h4 a") or card.select_one("h4 a") or card.select_one(".name a")
        name = _clean_text(name_tag)
        product_url = name_tag.get("href", "").strip() if name_tag else ""

        if not name:
            # Not a real product card (e.g. an ad banner picked up by a loose selector); skip it.
            continue

        # --- Image ---
        img_tag = card.select_one(".image img") or card.select_one("img")
        image_url = ""
        if img_tag:
            image_url = img_tag.get("data-src") or img_tag.get("src") or ""

        # --- Prices (current / discounted, and original if on sale) ---
        price_new_tag = card.select_one(".price-new") or card.select_one(".price")
        price_old_tag = card.select_one(".price-old")

        price_new = _clean_text(price_new_tag)
        price_old = _clean_text(price_old_tag)

        # If there's no explicit "new" price span, the .price block may contain
        # both figures as plain text (e.g. "₹12,000 ₹9,199"); split as a fallback.
        if not price_new and price_new_tag:
            raw_price_text = _clean_text(price_new_tag)
            parts = raw_price_text.split()
            if len(parts) >= 2:
                price_old, price_new = parts[0], parts[1]
            else:
                price_new = raw_price_text

        # --- Discount badge, e.g. "-23%" ---
        discount_tag = card.select_one(".ex-tax, .special-tag, .product-badge, .label-danger")
        discount = _clean_text(discount_tag)

        # --- Stock status (not always present on the listing page) ---
        stock_tag = card.select_one(".stock, .instock, .out-of-stock")
        stock_status = _clean_text(stock_tag)

        products.append(
            {
                "name": name,
                "url": product_url,
                "image_url": image_url,
                "price": price_new,
                "original_price": price_old,
                "discount": discount,
                "stock_status": stock_status,
            }
        )

    return products


def get_total_pages(html: str) -> int:
    """Best-effort detection of how many result pages exist."""
    soup = BeautifulSoup(html, "html.parser")
    page_links = soup.select("ul.pagination a, .pagination a")
    max_page = 1
    for link in page_links:
        text = link.get_text(strip=True)
        if text.isdigit():
            max_page = max(max_page, int(text))
    return max_page


def scrape(search_term: str, max_pages: int = 1, delay: float = 1.0):
    """
    Scrape MDComputers for `search_term` across up to `max_pages` pages.
    Returns a list of product dicts. Stops early if a page returns no products.
    """
    session = requests.Session()
    all_products = []

    first_url = build_search_url(search_term, page=1)
    first_html = fetch_page(first_url, session)
    if first_html is None:
        print("[error] could not reach MDComputers. Check your connection or the URL.", file=sys.stderr)
        return all_products

    all_products.extend(parse_products(first_html))

    pages_available = get_total_pages(first_html)
    pages_to_fetch = min(max_pages, pages_available) if pages_available else max_pages

    for page_num in range(2, pages_to_fetch + 1):
        time.sleep(delay)  # be a polite scraper
        url = build_search_url(search_term, page=page_num)
        html = fetch_page(url, session)
        if not html:
            break
        page_products = parse_products(html)
        if not page_products:
            break
        all_products.extend(page_products)

    return all_products


def save_to_csv(products, filepath: str):
    if not products:
        print("[info] no products to save.")
        return
    fieldnames = list(products[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(products)
    print(f"[info] saved {len(products)} products to {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape product details from MDComputers.in for a given search term."
    )
    parser.add_argument("search_term", help='Search term, e.g. "external harddrive"')
    parser.add_argument("--pages", type=int, default=1, help="Number of result pages to scrape (default: 1)")
    parser.add_argument("--out", default="mdcomputers_results.csv", help="Output CSV file path")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay in seconds between page requests")
    args = parser.parse_args()

    print(f'[info] searching MDComputers for: "{args.search_term}"')
    products = scrape(args.search_term, max_pages=args.pages, delay=args.delay)

    if not products:
        print("[warn] no products found. The site markup may have changed, or the search returned nothing.")
        sys.exit(1)

    for i, p in enumerate(products, start=1):
        print(f"{i}. {p['name']} | {p['price']} (was {p['original_price'] or '-'}) | {p['url']}")

    save_to_csv(products, args.out)


if __name__ == "__main__":
    main()
