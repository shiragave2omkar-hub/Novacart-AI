MAX_UPSELL_INR = 2000


def check_upsell(current_price, new_price):
    """
    Check whether an upgrade is allowed by the merchant policy.
    """

    if current_price is None or new_price is None:
        return {
            "allowed": False,
            "reason": "Missing product price."
        }

    difference = new_price - current_price

    if difference <= 0:
        return {
            "allowed": True,
            "reason": "Product is not an upsell.",
            "difference": difference
        }

    if difference <= MAX_UPSELL_INR:
        return {
            "allowed": True,
            "reason": "Within merchant upsell limit.",
            "difference": difference
        }

    return {
        "allowed": False,
        "reason": (
            f"Upsell exceeds merchant limit of "
            f"₹{MAX_UPSELL_INR}."
        ),
        "difference": difference
    }

def validate_upsell(current_product, new_product):
    """
    Validate an upgrade using trusted catalog prices.
    """

    current_price = current_product.get("price_inr")
    new_price = new_product.get("price_inr")

    result = check_upsell(
        current_price,
        new_price
    )

    return {
        **result,
        "current_product": current_product.get("name"),
        "new_product": new_product.get("name"),
    }

def check_discount(discount_amount):
    """
    Check whether a campaign discount is within merchant policy.
    """

    MAX_DISCOUNT_INR = 500

    try:
        discount_amount = float(discount_amount)
    except (ValueError, TypeError):
        return {
            "allowed": False,
            "reason": "Invalid discount amount."
        }

    if discount_amount < 0:
        return {
            "allowed": False,
            "reason": "Discount cannot be negative."
        }

    if discount_amount <= MAX_DISCOUNT_INR:
        return {
            "allowed": True,
            "reason": "Within merchant discount limit.",
            "discount": discount_amount
        }

    return {
        "allowed": False,
        "reason": (
            f"Discount exceeds merchant limit of "
            f"₹{MAX_DISCOUNT_INR}."
        ),
        "discount": discount_amount
    }
