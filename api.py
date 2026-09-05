"""Thin HTTP adapter for the existing NovaCart agent modules.

The browser never receives credentials and never supplies trusted prices,
discounts, or totals. This file intentionally delegates those decisions to
the existing catalog, cart, checkout, policy, campaign, and audit modules.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

from agent import SYSTEM_PROMPT, run_agent
from audit import get_audit_log, log_event
from campaign import (
    analyze_accessory_categories,
    analyze_accessory_opportunity,
    choose_campaign_category,
    create_campaign,
)
from cart import add_to_cart, get_cart, remove_from_cart
from checkout import PAYMENT_UNAVAILABLE_MESSAGE, get_checkout_summary
from payments import (
    PaymentIntegrationUnavailable,
    PaymentProviderError,
    PaymentVerificationFailed,
    create_test_order,
    verify_test_payment,
)
from tools import load_products, search_products


ROOT = Path(__file__).parent
WEB_DIST = ROOT / "web" / "dist"
app = Flask(__name__, static_folder=None)
PAYMENT_OR_CHECKOUT_INTENT = re.compile(r"\b(?:pay(?:ment)?|checkout|check\s*out)\b", re.IGNORECASE)
PENDING_PAYMENT_ORDERS: dict[str, dict[str, Any]] = {}


def json_error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def format_product(product: dict[str, Any]) -> dict[str, Any]:
    """Return only catalog-backed product fields safe for client rendering."""
    source = product.get("source") or {}
    return {
        "id": product.get("id"),
        "brand": product.get("brand"),
        "name": product.get("name"),
        "category": product.get("category"),
        "price_inr": product.get("price_inr"),
        "currency": product.get("currency", "INR"),
        "price_status": product.get("price_status"),
        "price_checked_at": product.get("price_checked_at"),
        "availability": product.get("availability"),
        "specifications": product.get("specifications") or {},
        "use_cases": product.get("use_cases") or [],
        "tags": product.get("tags") or [],
        "compatible_with": product.get("compatible_with") or [],
        "complements": product.get("complements") or [],
        "image_url": product.get("image_url"),
        "product_url": product.get("product_url"),
        "source": {
            "name": source.get("name"),
            "url": source.get("url"),
        },
    }


def catalog_by_id() -> dict[str, dict[str, Any]]:
    return {product.get("id"): product for product in load_products()}


def parse_budget(text: str) -> int | None:
    """Extract a customer-stated INR cap for presentation, never for pricing."""
    normalized = text.lower().replace(",", "")
    lakh_match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lac)\b", normalized)
    if lakh_match:
        return int(float(lakh_match.group(1)) * 100000)

    thousand_match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*k\b", normalized)
    if thousand_match:
        return int(float(thousand_match.group(1)) * 1000)

    currency_match = re.search(r"(?:under|below|within|budget(?:\s+of)?|₹|rs\.?|inr)\s*(\d{3,7})\b", normalized)
    if currency_match:
        return int(currency_match.group(1))
    return None


def factual_highlights(product: dict[str, Any], budget: int | None) -> list[str]:
    """Build display facts strictly from catalog fields, without inferred claims."""
    highlights: list[str] = []
    use_cases = product.get("use_cases") or []
    if use_cases:
        highlights.append(f"Catalog use cases: {', '.join(use_cases[:3])}")

    specs = product.get("specifications") or {}
    for field in ("processor", "ram", "storage", "gpu", "weight", "battery"):
        value = specs.get(field)
        if value:
            highlights.append(str(value))
        if len(highlights) >= 4:
            break

    price = product.get("price_inr")
    if budget is not None and isinstance(price, (int, float)) and price <= budget:
        highlights.append(f"₹{price:,.0f}, within your stated budget")
    return highlights[:4]


def matching_accessories(product: dict[str, Any], budget: int | None) -> list[dict[str, Any]]:
    """Use the catalog's explicit complement metadata for non-spammy add-ons."""
    complements = [str(item).lower() for item in product.get("complements") or []]
    if not complements:
        return []

    results: list[dict[str, Any]] = []
    for candidate in load_products():
        category = str(candidate.get("category") or "").lower()
        name = str(candidate.get("name") or "").lower()
        if not any(term in category or term in name for term in complements):
            continue
        price = candidate.get("price_inr")
        if price is None:
            continue
        if budget is not None and product.get("price_inr") is not None:
            if product["price_inr"] + price > budget:
                continue
        results.append(candidate)

    results.sort(key=lambda candidate: candidate.get("price_inr") or float("inf"))
    return [format_product(candidate) for candidate in results[:2]]


def recommendation_payload(query: str, trace: list[dict[str, Any]]) -> dict[str, Any] | None:
    budget = parse_budget(query)
    searched_products: list[dict[str, Any]] = []
    for event in trace:
        if event.get("name") == "search_products" and isinstance(event.get("result"), list):
            searched_products = event["result"]
            break

    if not searched_products:
        searched_products = search_products(query=query, max_price=budget)

    if not searched_products:
        return None

    best = searched_products[0]
    alternatives = searched_products[1:3]
    all_matches = search_products(query=query, max_price=None)
    stretch = None
    if budget is not None:
        over_budget = [
            product for product in all_matches
            if isinstance(product.get("price_inr"), (int, float))
            and product["price_inr"] > budget
        ]
        if over_budget:
            stretch_candidate = min(over_budget, key=lambda product: product["price_inr"])
            stretch = format_product(stretch_candidate)
            stretch["overage_inr"] = stretch_candidate["price_inr"] - budget

    return {
        "budget_inr": budget,
        "best_fit": format_product(best),
        "alternatives": [format_product(product) for product in alternatives],
        "why_this": factual_highlights(best, budget),
        "cross_sell": matching_accessories(best, budget),
        "stretch_option": stretch,
        "why_not": (
            f"The stretch option is ₹{stretch['overage_inr']:,.0f} above your stated budget."
            if stretch else None
        ),
    }


def customer_display_message(recommendations: dict[str, Any] | None) -> str:
    """A safe UI summary built only from the selected catalog payload.

    The model remains responsible for tool selection and conversational flow,
    but its free-form prose is not an authority for catalog facts. Rendering a
    catalog-backed summary prevents a speculative price or specification from
    being shown beside trusted product cards.
    """
    if not recommendations or not recommendations.get("best_fit"):
        return "NovaCart completed the analysis. Review the catalog results below."

    product = recommendations["best_fit"]
    title = " ".join(part for part in [product.get("brand"), product.get("name")] if part)
    price = product.get("price_inr")
    price_text = f" at ₹{price:,.0f}" if isinstance(price, (int, float)) else " with a catalog price currently unavailable"
    alternatives = len(recommendations.get("alternatives") or [])
    suffix = f" {alternatives} catalog alternative{'s are' if alternatives != 1 else ' is'} ready to compare." if alternatives else ""
    return f"Based on your goal, NovaCart surfaced {title}{price_text} as the top catalog match.{suffix}"


def detailed_cart() -> dict[str, Any]:
    """Join cart quantities with non-authoritative display metadata from catalog."""
    cart = get_cart()
    products = catalog_by_id()
    items = []
    for item in cart["items"]:
        product = products.get(item["id"], {})
        items.append({**item, "product": format_product(product)})
    return {"items": items, "total": cart["total"]}


def is_payment_or_checkout_intent(message: str) -> bool:
    """Route explicit payment requests before any model-driven catalog search."""
    return bool(PAYMENT_OR_CHECKOUT_INTENT.search(message))


def payment_intent_response():
    """Return the server-authoritative checkout state without charging a payment."""
    summary = get_checkout_summary()
    log_event("checkout_requested", {"status": summary.get("status"), "total": summary.get("total")})
    message = summary.get("message") if summary.get("status") == "empty" else summary.get("payment_message")
    return jsonify({
        "message": message,
        "recommendations": None,
        "tool_events": [{"name": "get_checkout_summary", "arguments": {}}],
        "cart": detailed_cart(),
    })


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "catalog_count": len(load_products())})


@app.get("/api/products")
def products():
    query = request.args.get("query", "").strip()
    category = request.args.get("category") or None
    raw_budget = request.args.get("max_price")
    try:
        budget = int(raw_budget) if raw_budget else None
    except ValueError:
        return json_error("max_price must be an integer amount in INR.")

    source = search_products(query, budget, category) if query or category or budget else load_products()
    return jsonify({"products": [format_product(product) for product in source]})


@app.get("/api/product/<product_id>")
def product(product_id: str):
    found = catalog_by_id().get(product_id)
    if not found:
        return json_error("Product not found.", 404)
    return jsonify({"product": format_product(found)})


@app.post("/api/chat")
def chat():
    body = request.get_json(silent=True) or {}
    message = str(body.get("message") or "").strip()
    if not message:
        return json_error("A message is required.")

    history = body.get("history") or []
    safe_history = []
    if isinstance(history, list):
        for entry in history[-10:]:
            if not isinstance(entry, dict):
                continue
            role = entry.get("role")
            content = str(entry.get("content") or "").strip()
            if role in {"user", "assistant"} and content:
                safe_history.append({"role": role, "content": content[:4000]})

    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *safe_history, {"role": "user", "content": message}]
    trace: list[dict[str, Any]] = []
    log_event("goal_received", {"message": message})

    if is_payment_or_checkout_intent(message):
        return payment_intent_response()

    try:
        response = run_agent(messages, tool_trace=trace)
    except Exception:
        # The application remains honest about an unavailable model. Existing
        # catalog and cart APIs still work and no response is fabricated.
        return jsonify({
            "error": "NovaCart could not reach the AI service. Your cart has been preserved.",
            "recommendations": recommendation_payload(message, trace),
        }), 503

    # The model remains the first path for all requests. These narrow,
    # catalog-backed command fallbacks keep common conversational cart actions
    # reliable when prior tool details have fallen outside the model context.
    lower_message = message.lower()
    model_added_product = any(event.get("name") == "add_to_cart" for event in trace)
    context = body.get("context") or {}
    command_note = None
    if not model_added_product and re.search(r"\badd\s+(?:the\s+)?best(?:\s+one|\s+fit)?\b", lower_message):
        best_id = str(context.get("best_fit_id") or "")
        best_product = catalog_by_id().get(best_id)
        if best_product and best_product.get("price_inr") is not None:
            add_to_cart(best_id, 1)
            log_event("product_added_to_cart", {"product_id": best_id, "quantity": 1, "source": "web_command"})
            command_note = f"Added {best_product.get('brand', '')} {best_product.get('name', '')} to your cart."
    elif not model_added_product and "add something useful" in lower_message:
        current_items = get_cart().get("items", [])
        product_map = catalog_by_id()
        budget = context.get("budget_inr")
        try:
            budget = int(budget) if budget is not None else None
        except (ValueError, TypeError):
            budget = None
        if current_items:
            primary = product_map.get(current_items[-1].get("id"))
            add_ons = matching_accessories(primary, budget) if primary else []
            if add_ons:
                add_to_cart(add_ons[0]["id"], 1)
                log_event("product_added_to_cart", {"product_id": add_ons[0]["id"], "quantity": 1, "source": "web_command"})
                command_note = f"Added {add_ons[0].get('brand', '')} {add_ons[0].get('name', '')} as a catalog-listed complement."

    recommendations = recommendation_payload(message, trace)
    display_message = customer_display_message(recommendations)
    if command_note:
        display_message = f"{display_message}\n\n{command_note}"

    return jsonify({
        "message": display_message,
        "recommendations": recommendations,
        "tool_events": [{"name": event["name"], "arguments": event["arguments"]} for event in trace],
        "cart": detailed_cart(),
    })


@app.get("/api/cart")
def cart():
    return jsonify(detailed_cart())


@app.post("/api/cart/add")
def cart_add():
    body = request.get_json(silent=True) or {}
    product_id = str(body.get("product_id") or "").strip()
    quantity = body.get("quantity", 1)
    if not product_id:
        return json_error("product_id is required.")

    result = add_to_cart(product_id, quantity)
    if result.get("error"):
        return json_error(result["error"], 404)
    log_event("product_added_to_cart", {"product_id": product_id, "quantity": quantity, "source": "web"})
    return jsonify(detailed_cart())


@app.post("/api/cart/remove")
def cart_remove():
    body = request.get_json(silent=True) or {}
    product_id = str(body.get("product_id") or "").strip()
    if not product_id:
        return json_error("product_id is required.")
    remove_from_cart(product_id)
    log_event("product_removed_from_cart", {"product_id": product_id, "source": "web"})
    return jsonify(detailed_cart())


@app.post("/api/checkout/summary")
def checkout_summary():
    body = request.get_json(silent=True) or {}
    budget = body.get("budget_inr")
    try:
        budget = int(budget) if budget is not None else None
    except (ValueError, TypeError):
        return json_error("budget_inr must be an integer amount in INR.")

    summary = get_checkout_summary()
    if summary.get("status") != "empty":
        summary["budget_inr"] = budget
        summary["difference_inr"] = summary["total"] - budget if budget is not None else None
    log_event("checkout_requested", {"status": summary.get("status"), "total": summary.get("total")})
    return jsonify(summary)


@app.post("/api/payment/create-order")
def create_payment_order():
    """Create a Razorpay Test Mode order from the current server cart."""
    summary = get_checkout_summary()
    if summary.get("status") == "empty":
        return json_error(summary["message"], 400)

    try:
        order = create_test_order(summary)
    except PaymentIntegrationUnavailable:
        return json_error(PAYMENT_UNAVAILABLE_MESSAGE, 503)
    except PaymentProviderError:
        return json_error("Razorpay Test Mode could not create a payment order. No payment has been processed.", 502)

    PENDING_PAYMENT_ORDERS[order["order_id"]] = {
        "amount": order["amount"],
        "currency": order["currency"],
        "receipt": order["receipt"],
    }
    log_event("payment_order_created", {
        "order_id": order["order_id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "receipt": order["receipt"],
    })
    return jsonify({
        "key_id": order["key_id"],
        "order_id": order["order_id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "cart": summary,
    })


@app.post("/api/payment/verify")
def verify_payment():
    """Verify Razorpay Checkout data before reporting a payment as successful."""
    body = request.get_json(silent=True) or {}
    payment_details = {
        field: str(body.get(field) or "").strip()
        for field in ("razorpay_order_id", "razorpay_payment_id", "razorpay_signature")
    }
    order_id = payment_details["razorpay_order_id"]

    if not all(payment_details.values()):
        log_event("payment_verification_failed", {"order_id": order_id or None, "reason": "missing_payment_details"})
        return json_error("Payment was not verified.", 400)
    if order_id not in PENDING_PAYMENT_ORDERS:
        log_event("payment_verification_failed", {"order_id": order_id, "reason": "unknown_order"})
        return json_error("Payment was not verified.", 400)

    try:
        verify_test_payment(payment_details)
    except (PaymentIntegrationUnavailable, PaymentVerificationFailed):
        log_event("payment_verification_failed", {"order_id": order_id, "reason": "signature_not_verified"})
        return json_error("Payment was not verified.", 400)

    order = PENDING_PAYMENT_ORDERS.pop(order_id)
    log_event("payment_verified", {
        "order_id": order_id,
        "payment_id": payment_details["razorpay_payment_id"],
        "amount": order["amount"],
        "currency": order["currency"],
    })
    return jsonify({
        "status": "verified",
        "message": "Payment verified successfully.",
        "order_id": order_id,
        "payment_id": payment_details["razorpay_payment_id"],
        "cart": detailed_cart(),
    })


@app.get("/api/merchant/analytics")
def merchant_analytics():
    overall = analyze_accessory_opportunity()
    categories = analyze_accessory_categories()
    # Keep the dashboard opportunity consistent with the campaign
    # orchestrator's relevance-aware selection, rather than merely taking
    # the first category in the attachment-rate sort order.
    opportunity = choose_campaign_category() if categories.get("category_sales") else None
    return jsonify({
        "data_label": "Demo analytics - synthetic sales dataset",
        "accessory_attachment": overall,
        "category_attachment": categories,
        "growth_opportunity": opportunity,
        "recent_actions": get_audit_log()[-6:],
    })


@app.post("/api/campaign")
def campaign():
    body = request.get_json(silent=True) or {}
    goal = str(body.get("goal") or "").strip()
    if not goal:
        return json_error("A campaign goal is required.")
    draft = create_campaign(goal)
    product_map = catalog_by_id()
    draft["recommended_products"] = [
        format_product(product_map[item["id"]])
        for item in draft.get("recommended_products", [])
        if item.get("id") in product_map
    ]
    return jsonify(draft)


@app.get("/api/audit")
def audit():
    return jsonify({"events": get_audit_log()})


@app.post("/api/ai-buyer/quote")
def ai_buyer_quote():
    """Structured catalog response for a future external buyer integration."""
    body = request.get_json(silent=True) or {}
    goal = str(body.get("goal") or "").strip()
    if not goal:
        return json_error("A buyer goal is required.")
    trace: list[dict[str, Any]] = []
    payload = recommendation_payload(goal, trace)
    log_event("ai_buyer_quote_requested", {"goal": goal})
    return jsonify({
        "status": "catalog_quote_ready",
        "mode": "api_ready_shell",
        "goal": goal,
        "recommendations": payload,
        "cart": detailed_cart(),
    })


@app.get("/")
def index():
    if WEB_DIST.exists():
        return send_from_directory(WEB_DIST, "index.html")
    return jsonify({"message": "NovaCart API is running. Start the Vite client with npm run dev."})


@app.get("/<path:path>")
def frontend(path: str):
    if WEB_DIST.exists() and (WEB_DIST / path).exists():
        return send_from_directory(WEB_DIST, path)
    return json_error("Not found.", 404)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5050"))
    app.run(host="127.0.0.1", port=port, debug=True)
