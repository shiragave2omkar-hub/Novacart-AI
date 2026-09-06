from tools import load_products
import json
from pathlib import Path
import os

CART_FILE = Path("/tmp/novacart_cart.json") if os.getenv("VERCEL") else Path(__file__).parent / "cart.json"


def load_cart():
    if not CART_FILE.exists():
        return []

    with open(CART_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_cart(cart):
    with open(CART_FILE, "w", encoding="utf-8") as file:
        json.dump(cart, file, indent=2, ensure_ascii=False)


def add_to_cart(product_id, quantity=1):
    products = load_products()

    # Validate product ID before adding
    product_ids = {product["id"] for product in products}

    if product_id not in product_ids:
        return {
            "error": f"Product {product_id} does not exist in the catalog."
        }

    try:
        quantity = int(quantity)
    except (ValueError, TypeError):
        quantity = 1

    if quantity < 1:
        quantity = 1

    cart = load_cart()

    for item in cart:
        if item["product_id"] == product_id:
            item["quantity"] += quantity
            save_cart(cart)
            return get_cart()

    cart.append({
        "product_id": product_id,
        "quantity": quantity
    })

    save_cart(cart)
    return get_cart()


def remove_from_cart(product_id):
    cart = load_cart()

    cart = [
        item for item in cart
        if item["product_id"] != product_id
    ]

    save_cart(cart)
    return get_cart()


def clear_cart():
    save_cart([])
    return get_cart()


def get_cart():
    cart = load_cart()
    products = load_products()

    product_map = {
        product["id"]: product
        for product in products
    }

    detailed_cart = []
    total = 0

    for item in cart:
        product = product_map.get(item["product_id"])

        if not product:
            continue

        quantity = item["quantity"]
        price = product.get("price_inr")

        if price is None:
            continue

        subtotal = price * quantity

        detailed_cart.append({
            "id": product["id"],
            "name": product["name"],
            "brand": product.get("brand"),
            "price": price,
            "quantity": quantity,
            "subtotal": subtotal
        })

        total += subtotal

    return {
        "items": detailed_cart,
        "total": total
    }
