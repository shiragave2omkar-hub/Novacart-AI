import json
from pathlib import Path
from datetime import datetime

SALES_FILE = Path(__file__).parent / "sales_data.json"


def load_sales_data():
    if not SALES_FILE.exists():
        return []

    with open(SALES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def analyze_accessory_opportunity():
    sales = load_sales_data()

    if not sales:
        return {
            "status": "no_data",
            "message": "No sales data available."
        }

    laptop_buyers = 0
    laptop_buyers_with_accessories = 0

    for order in sales:
        categories = [
            item.get("category", "").lower()
            for item in order.get("items", [])
        ]

        has_laptop = "laptop" in categories
        has_accessory = any(
            category in {
                "mouse",
                "keyboard",
                "laptop sleeve",
                "laptop bag",
                "charger",
                "usb hub"
            }
            for category in categories
        )

        if has_laptop:
            laptop_buyers += 1

            if has_accessory:
                laptop_buyers_with_accessories += 1

    if laptop_buyers == 0:
        attach_rate = 0
    else:
        attach_rate = (
            laptop_buyers_with_accessories / laptop_buyers
        ) * 100

    return {
        "laptop_buyers": laptop_buyers,
        "laptop_buyers_with_accessories": laptop_buyers_with_accessories,
        "accessory_attach_rate": round(attach_rate, 2)
    }


def create_campaign(goal):
    goal = str(goal or "").lower()

    opportunity = analyze_accessory_opportunity()

    if "accessor" not in goal:
        target = "Customers with recent laptop purchases"
        campaign_name = "Laptop Setup Week"
    else:
        target = "Laptop buyers who did not purchase accessories"
        campaign_name = "Laptop Setup Week"

    campaign = {
        "campaign_id": f"NC-CAMP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "campaign_name": campaign_name,
        "goal": goal,
        "target": target,
        "offer": {
            "type": "percentage",
            "value": 10,
            "max_discount_inr": 500
        },
        "recommended_products": [
            "Mouse",
            "Laptop Sleeve",
            "Laptop Stand"
        ],
        "duration_days": 3,
        "status": "draft",
        "baseline": opportunity,
        "created_at": datetime.now().isoformat(timespec="seconds")
    }

    return campaign
