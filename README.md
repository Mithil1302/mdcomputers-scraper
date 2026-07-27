# MDComputers Product Scraper

A small Python script that scrapes product details from [MDComputers.in](https://mdcomputers.in)
for a given search term, e.g.:

```
https://mdcomputers.in/?route=product/search&search=external harddrive
```

For each matching product it extracts:

- Product name
- Product page URL
- Image URL
- Current (discounted) price
- Original price (if the item is on sale)
- Discount badge (e.g. `-23%`)
- Stock status (when shown on the listing page)

## Setup

```bash
git clone https://github.com/Mithil1302/mdcomputers-scraper.git
cd mdcomputers-scraper
pip install -r requirements.txt
```

## Usage

```bash
python mdcomputers_scraper.py "external harddrive"
```

Optional flags:

```bash
python mdcomputers_scraper.py "external harddrive" --pages 2 --out results.csv --delay 1.5
```

| Flag       | Description                                  | Default                     |
|------------|-----------------------------------------------|------------------------------|
| `--pages`  | Number of result pages to scrape              | `1`                          |
| `--out`    | Output CSV file path                          | `mdcomputers_results.csv`    |
| `--delay`  | Seconds to wait between page requests          | `1.0`                        |

The script prints a numbered summary of every product found and saves the
full details to a CSV file.

## How it works

MDComputers runs on an OpenCart-based storefront. Each product on a search
results page is rendered inside a `product-thumb` card containing:

- an `<h4><a>` with the product name and link
- an `<img>` for the thumbnail
- a `.price` block with `.price-new` / `.price-old` spans when the item is
  discounted

`parse_products()` in `mdcomputers_scraper.py` walks these cards with
BeautifulSoup and falls back to looser selectors if the theme markup
changes slightly (storefront themes get tweaked over time, so a few
fallback strategies keep the scraper resilient).

## Running tests

The parsing logic is covered by unit tests that run against saved HTML
snippets (no network access needed):

```bash
pip install pytest
pytest tests/ -v
```

## Notes

- The script sends a browser-like `User-Agent` header and a short delay
  between page requests to be a considerate scraper.
- Only public product-listing data is scraped; no login-gated content is
  accessed.
- If MDComputers changes its site markup, update the CSS selectors in
  `parse_products()` accordingly.
