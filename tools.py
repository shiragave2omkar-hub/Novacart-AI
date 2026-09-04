import json
from pathlib import Path


PRODUCT_FILE = Path(__file__).parent / "products.json"


def load_products():
    with open(PRODUCT_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def search_products(query="", max_price=None, category=None):
    products = load_products()

    # Normalize query
    query = str(query or "").lower().strip()

    # Normalize max price
    if max_price is not None:
        if str(max_price).lower() in ("none", "null", ""):
            max_price = None
        else:
            try:
                max_price = float(max_price)
            except (ValueError, TypeError):
                max_price = None

    # Normalize category
    if category is not None:
        category = str(category).strip()

        if category.lower() in (
            "",
            "none",
            "null",
            "any",
            "all",
        ):
            category = None

    stop_words = {
        "show",
        "me",
        "all",
        "the",
        "products",
        "product",
        "available",
        "items",
        "item",
        "please",
        "find",
        "want",
        "need",
        "for",
        "under",
        "below",
        "within",
        "my",
        "some",
        "something",
        "looking",
        "use",
        "using",
    }

    query_words = [
        word.strip(".,!?")
        for word in query.split()
        if word.strip(".,!?") not in stop_words
    ]

    results = []

    for product in products:

        searchable_text = " ".join([
            product["name"],
            product["category"],
            product["brand"],
            product["description"],
            " ".join(product["tags"]),
            " ".join(product["use_cases"]),
        ]).lower()

        # Search matching
        if query_words:

            matches = sum(
                1
                for word in query_words
                if word in searchable_text
            )

            if matches == 0:
                continue

        # Budget filtering
        if max_price is not None:

            if product["price"] > max_price:
                continue

        # Category filtering
        if category:

            if category.lower() not in product["category"].lower():
                continue

        results.append(product)

    return results
