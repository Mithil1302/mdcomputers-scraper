from mdcomputers_scraper import parse_products

SINGLE_PRODUCT_HTML = """
<div class="product-layout product-grid">
  <div class="product-thumb">
    <div class="image">
      <a href="https://mdcomputers.in/product/seagate-expansion-1tb-external-hard-drive-stkm1000400">
        <img src="https://mdcomputers.in/image/catalog/seagate-1tb.webp" alt="Seagate Expansion 1TB">
      </a>
      <span class="label-danger">-8%</span>
    </div>
    <div class="caption">
      <h4><a href="https://mdcomputers.in/product/seagate-expansion-1tb-external-hard-drive-stkm1000400">Seagate Expansion 1TB External Hard Drive</a></h4>
      <p class="price">
        <span class="price-old">&#8377;10,000</span>
        <span class="price-new">&#8377;9,160</span>
      </p>
    </div>
  </div>
</div>
"""

MULTI_PRODUCT_HTML = """
<div class="product-thumb">
  <div class="image"><a href="https://mdcomputers.in/product/item-a"><img src="a.webp"></a></div>
  <div class="caption">
    <h4><a href="https://mdcomputers.in/product/item-a">Item A No Discount</a></h4>
    <p class="price">&#8377;5,000</p>
  </div>
</div>
<div class="product-thumb">
  <div class="image"><a href="https://mdcomputers.in/product/item-b"><img src="b.webp"></a></div>
  <div class="caption">
    <h4><a href="https://mdcomputers.in/product/item-b">Item B With Discount</a></h4>
    <p class="price">
      <span class="price-old">&#8377;20,000</span>
      <span class="price-new">&#8377;14,999</span>
    </p>
  </div>
</div>
"""

EMPTY_RESULTS_HTML = "<div class='container'><p>There is no product that matches the search criteria.</p></div>"


def test_single_product_with_discount():
    products = parse_products(SINGLE_PRODUCT_HTML)
    assert len(products) == 1

    p = products[0]
    assert p["name"] == "Seagate Expansion 1TB External Hard Drive"
    assert p["price"] == "₹9,160"
    assert p["original_price"] == "₹10,000"
    assert p["discount"] == "-8%"
    assert "seagate-expansion-1tb" in p["url"]
    assert p["image_url"].endswith("seagate-1tb.webp")


def test_multiple_products_mixed_discount():
    products = parse_products(MULTI_PRODUCT_HTML)
    assert len(products) == 2

    item_a, item_b = products
    assert item_a["name"] == "Item A No Discount"
    assert item_a["price"] == "₹5,000"
    assert item_a["original_price"] == ""

    assert item_b["name"] == "Item B With Discount"
    assert item_b["price"] == "₹14,999"
    assert item_b["original_price"] == "₹20,000"


def test_no_products_found():
    products = parse_products(EMPTY_RESULTS_HTML)
    assert products == []
