import json
from datetime import datetime
from pathlib import Path

from audit import log_event
from policy import check_discount
from tools import load_products


SALES_FILE = Path(__file__).parent / "sales_data.json"


# Categories that can be promoted in an accessory campaign
ACCESSORY_CATEGORIES = {
    "Backpack",
    "Charger",
    "Headset",
    "Keyboard",
    "Keyboard + Mouse",
    "Laptop Sleeve",
    "Mouse",
    "Power Bank",
    "Stylus",
    "USB Drive",
    "USB-C Hub",
    "Webcam",
}


# Business relevance used when multiple categories
# have the same sales performance.
ACCESSORY_RELEVANCE = {
    "USB-C Hub": 10,
    "Charger": 9,
    "Backpack": 9,
    "Laptop Sleeve": 9,
    "Mouse": 8,
    "Keyboard": 8,
    "Keyboard + Mouse": 8,
    "Webcam": 6,
    "Headset": 5,
    "Power Bank": 5,
    "USB Drive": 4,
    "Stylus": 3,
}


def load_sales_data():
    """Load synthetic/demo sales data."""

    if not SALES_FILE.exists():
        return []

    try:
        with open(SALES_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            return []

        return data

    except (json.JSONDecodeError, OSError):
        return []


def analyze_accessory_opportunity():
    """
    Calculate overall accessory attachment among laptop buyers.
    """

    sales = load_sales_data()

    if not sales:
        return {
            "status": "no_data",
            "laptop_buyers": 0,
            "laptop_buyers_with_accessories": 0,
            "accessory_attach_rate": 0.0,
        }

    laptop_buyers = 0
    laptop_buyers_with_accessories = 0

    for order in sales:
        items = order.get("items", [])

        categories = {
            str(item.get("category", "")).strip()
            for item in items
        }

        if "Laptop" not in categories:
            continue

        laptop_buyers += 1

        has_accessory = any(
            category in ACCESSORY_CATEGORIES
            for category in categories
        )

        if has_accessory:
            laptop_buyers_with_accessories += 1

    attach_rate = (
        laptop_buyers_with_accessories / laptop_buyers * 100
        if laptop_buyers > 0
        else 0.0
    )

    return {
        "status": "analyzed",
        "laptop_buyers": laptop_buyers,
        "laptop_buyers_with_accessories": laptop_buyers_with_accessories,
        "accessory_attach_rate": round(attach_rate, 2),
    }


def analyze_accessory_categories():
    """
    Calculate sales and attachment rate for every accessory category
    among laptop buyers.
    """

    sales = load_sales_data()

    category_sales = {
        category: 0
        for category in ACCESSORY_CATEGORIES
    }

    laptop_buyers = 0

    for order in sales:
        items = order.get("items", [])

        categories = {
            str(item.get("category", "")).strip()
            for item in items
        }

        if "Laptop" not in categories:
            continue

        laptop_buyers += 1

        for category in ACCESSORY_CATEGORIES:
            if category in categories:
                category_sales[category] += 1

    results = []

    for category, sales_count in category_sales.items():
        attachment_rate = (
            sales_count / laptop_buyers * 100
            if laptop_buyers > 0
            else 0.0
        )

        results.append({
            "category": category,
            "sales": sales_count,
            "attachment_rate": round(attachment_rate, 2),
        })

    results.sort(
        key=lambda item: (
            item["sales"],
            item["attachment_rate"],
            item["category"],
        )
    )

    return {
        "laptop_buyers": laptop_buyers,
        "category_sales": results,
    }


def choose_campaign_category():
    """
    Choose the strongest accessory growth opportunity.

    Lower attachment rate means a larger opportunity.
    Relevance is used to break ties between categories.
    """

    analysis = analyze_accessory_categories()
    category_data = analysis["category_sales"]

    if not category_data:
        return {
            "category": "Laptop Sleeve",
            "sales": 0,
            "attachment_rate": 0.0,
            "opportunity_score": 0.0,
        }

    scored = []

    for item in category_data:
        category = item["category"]
        attachment_rate = item["attachment_rate"]

        relevance = ACCESSORY_RELEVANCE.get(
            category,
            0
        )

        opportunity_score = (
            (100 - attachment_rate)
            + relevance
        )

        scored.append({
            "category": category,
            "sales": item["sales"],
            "attachment_rate": attachment_rate,
            "opportunity_score": round(
                opportunity_score,
                2
            ),
        })

    scored.sort(
        key=lambda item: (
            item["opportunity_score"],
            -item["sales"],
        ),
        reverse=True,
    )

    return scored[0]


def select_real_products(category=None, limit=5):
    """
    Select real products from the 101-product catalog.

    If category is supplied, only that accessory category
    is considered.
    """

    products = load_products()

    candidates = []

    for product in products:
        product_category = str(
            product.get("category", "")
        ).strip()

        # Never promote non-accessory products
        if product_category not in ACCESSORY_CATEGORIES:
            continue

        # If a category is selected, restrict to it
        if category and product_category != category:
            continue

        name = str(
            product.get("name", "")
        ).lower()

        brand = str(
            product.get("brand", "")
        ).lower()

        tags = " ".join(
            str(tag)
            for tag in product.get("tags", [])
        ).lower()

        use_cases = " ".join(
            str(use_case)
            for use_case in product.get("use_cases", [])
        ).lower()

        complements = " ".join(
            str(item)
            for item in product.get("complements", [])
        ).lower()

        searchable_text = " ".join([
            name,
            brand,
            product_category.lower(),
            tags,
            use_cases,
            complements,
        ])

        score = 0

        # Category relevance
        score += ACCESSORY_RELEVANCE.get(
            product_category,
            0
        )

        # Laptop relevance
        if "laptop" in searchable_text:
            score += 10

        # College relevance
        if "college" in searchable_text:
            score += 5

        # Productivity relevance
        if "productivity" in searchable_text:
            score += 4

        # General usefulness
        for keyword in [
            "office",
            "student",
            "travel",
            "portable",
            "work",
        ]:
            if keyword in searchable_text:
                score += 2

        candidates.append(
            (score, product)
        )

    candidates.sort(
        key=lambda item: (
            -item[0],
            item[1].get("price_inr") is None,
            item[1].get("price_inr") or 0,
        )
    )

    selected = []

    for score, product in candidates:
        selected.append({
            "id": product.get("id"),
            "brand": product.get("brand"),
            "name": product.get("name"),
            "category": product.get("category"),
            "price_inr": product.get("price_inr"),
            "score": score,
        })

        if len(selected) >= limit:
            break

    return selected


def validate_campaign_discount(
    products,
    discount_percent,
    max_discount_inr,
):
    """
    Validate the discount against merchant policy.

    The merchant's absolute maximum discount is enforced
    independently from the percentage.
    """

    checks = []

    for product in products:
        price = product.get("price_inr")

        if price is None:
            continue

        discount_amount = (
            price * discount_percent / 100
        )

        # Apply merchant's maximum cap
        effective_discount = min(
            discount_amount,
            max_discount_inr
        )

        result = check_discount(
            effective_discount
        )

        checks.append({
            "product_id": product.get("id"),
            "product_name": product.get("name"),
            "product_price": price,
            "requested_discount": round(
                discount_amount,
                2
            ),
            "effective_discount": round(
                effective_discount,
                2
            ),
            "allowed": result["allowed"],
            "reason": result["reason"],
        })

    blocked = [
        check
        for check in checks
        if not check["allowed"]
    ]

    return {
        "allowed": len(blocked) == 0,
        "checks": checks,
        "blocked": blocked,
    }


def count_campaign_target_customers(target_category):
    """Count unique demo laptop buyers without the promoted category."""

    laptop_customer_categories = {}

    for index, order in enumerate(load_sales_data()):
        items = order.get("items", [])
        categories = {
            str(item.get("category", "")).strip()
            for item in items
        }

        if "Laptop" not in categories:
            continue

        # sales_data.json supplies customer IDs. The deterministic order ID
        # fallback keeps the calculation defined for incomplete demo records.
        customer_id = str(
            order.get("customer_id")
            or order.get("order_id")
            or f"demo-order-{index}"
        )

        laptop_customer_categories.setdefault(
            customer_id,
            set(),
        ).update(categories)

    return sum(
        1
        for categories in laptop_customer_categories.values()
        if target_category not in categories
    )


def calculate_campaign_economics(
    target_category,
    recommended_products,
    discount_percent,
    max_discount_inr,
):
    """Return a conservative, deterministic estimate from the demo dataset.

    Expected orders are capped at the synthetic dataset's existing overall
    accessory-attachment rate. Revenue is modeled from the lowest-priced
    policy-eligible recommended product, not an average or premium item.
    This is an estimate only and deliberately excludes costs absent from the
    dataset, such as COGS, tax, and fulfilment.
    """

    baseline = analyze_accessory_opportunity()
    target_customers = count_campaign_target_customers(target_category)
    historical_attach_rate = baseline.get(
        "accessory_attach_rate",
        0.0,
    )

    eligible_products = [
        product
        for product in recommended_products
        if product.get("category") == target_category
        and isinstance(product.get("price_inr"), (int, float))
    ]

    if not eligible_products:
        return {
            "label": "Estimated using synthetic demo data",
            "scenario": "conservative_demo_estimate",
            "target_customers": target_customers,
            "expected_orders": 0,
            "estimated_revenue_inr": 0.0,
            "discount_cost_inr": 0.0,
            "net_incremental_revenue_inr": 0.0,
            "estimated_roi_percent": 0.0,
            "inputs": {
                "historical_accessory_attachment_rate": (
                    historical_attach_rate
                ),
                "revenue_product": None,
            },
            "assumptions": [
                "Target customers are demo laptop buyers who have not purchased the promoted category.",
                "No priced, policy-eligible recommended product was available, so all estimated outcomes are zero.",
                "This estimate uses synthetic demo data and is not actual campaign performance.",
            ],
        }

    revenue_product = min(
        eligible_products,
        key=lambda product: product["price_inr"],
    )
    revenue_per_order = float(revenue_product["price_inr"])

    # Integer floor prevents the estimate from exceeding the observed
    # accessory-attachment benchmark in the synthetic sample.
    expected_orders = int(
        target_customers * historical_attach_rate / 100
    )

    discount_per_order = min(
        revenue_per_order * discount_percent / 100,
        max_discount_inr,
    )
    estimated_revenue = expected_orders * revenue_per_order
    discount_cost = expected_orders * discount_per_order
    net_incremental_revenue = estimated_revenue - discount_cost
    estimated_roi = (
        net_incremental_revenue / discount_cost * 100
        if discount_cost > 0
        else 0.0
    )

    return {
        "label": "Estimated using synthetic demo data",
        "scenario": "conservative_demo_estimate",
        "target_customers": target_customers,
        "expected_orders": expected_orders,
        "estimated_revenue_inr": round(estimated_revenue, 2),
        "discount_cost_inr": round(discount_cost, 2),
        "net_incremental_revenue_inr": round(
            net_incremental_revenue,
            2,
        ),
        "estimated_roi_percent": round(estimated_roi, 2),
        "inputs": {
            "historical_accessory_attachment_rate": (
                historical_attach_rate
            ),
            "revenue_product": {
                "id": revenue_product.get("id"),
                "name": revenue_product.get("name"),
                "price_inr": revenue_product.get("price_inr"),
            },
            "discount_per_expected_order_inr": round(
                discount_per_order,
                2,
            ),
        },
        "assumptions": [
            "Target customers are unique demo laptop buyers who have not purchased the promoted category.",
            (
                "Expected orders use the existing synthetic overall accessory "
                f"attachment rate of {historical_attach_rate}% and round "
                "down to a whole order."
            ),
            (
                "Estimated revenue uses the lowest-priced policy-eligible "
                f"recommended product: {revenue_product.get('name')} "
                f"at ₹{revenue_product.get('price_inr'):,.0f}."
            ),
            (
                "Discount cost applies the campaign offer and merchant cap "
                "to each expected order."
            ),
            (
                "Net incremental revenue is estimated revenue less discount "
                "cost only; it excludes COGS, tax, logistics, and actual "
                "campaign performance."
            ),
        ],
    }


def create_campaign(goal):
    """
    Create a merchant campaign draft using:
    sales analysis + opportunity detection +
    real catalog products + merchant policy.
    """

    goal = str(goal or "").strip()

    # Analyze current performance
    overall_opportunity = (
        analyze_accessory_opportunity()
    )

    # Identify strongest opportunity
    opportunity = choose_campaign_category()

    target_category = opportunity["category"]

    # Select real products
    recommended_products = select_real_products(
        category=target_category,
        limit=5,
    )

    # Campaign offer
    discount_percent = 10
    max_discount_inr = 500

    # Validate discount policy
    discount_validation = validate_campaign_discount(
        recommended_products,
        discount_percent,
        max_discount_inr,
    )

    campaign_economics = calculate_campaign_economics(
        target_category,
        recommended_products,
        discount_percent,
        max_discount_inr,
    )

    campaign_id = (
        "NC-CAMP-"
        f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )

    # Stop campaign creation if policy is violated
    if not discount_validation["allowed"]:
        blocked_campaign = {
            "campaign_id": campaign_id,
            "status": "blocked",
            "goal": goal,
            "reason": (
                "Campaign exceeds merchant discount policy."
            ),
            "policy_violations": (
                discount_validation["blocked"]
            ),
            "created_at": datetime.now().isoformat(
                timespec="seconds"
            ),
        }

        log_event(
            "campaign_blocked",
            {
                "campaign_id": campaign_id,
                "goal": goal,
                "reason": (
                    "Campaign exceeds merchant "
                    "discount policy."
                ),
            },
        )

        return blocked_campaign

    campaign = {
        "campaign_id": campaign_id,

        "campaign_name": (
            f"{target_category} Growth Campaign"
        ),

        "goal": goal,

        "opportunity": {
            "category": target_category,
            "sales": opportunity["sales"],
            "attachment_rate": (
                opportunity["attachment_rate"]
            ),
            "opportunity_score": (
                opportunity["opportunity_score"]
            ),
        },

        "target": (
            "Laptop buyers who did not purchase "
            f"{target_category}"
        ),

        "offer": {
            "type": "percentage",
            "value": discount_percent,
            "max_discount_inr": max_discount_inr,
        },

        "recommended_products": (
            recommended_products
        ),

        "discount_validation": (
            discount_validation
        ),

        "economics": campaign_economics,

        "duration_days": 3,

        "status": "draft",

        "baseline": overall_opportunity,

        "created_at": datetime.now().isoformat(
            timespec="seconds"
        ),
    }

    log_event(
        "campaign_created",
        {
            "campaign_id": campaign_id,
            "goal": goal,
            "campaign_category": target_category,
            "recommended_product_ids": [
                product["id"]
                for product in recommended_products
            ],
            "status": "draft",
        },
    )

    return campaign
