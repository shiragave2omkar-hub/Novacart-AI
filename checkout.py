from cart import get_cart


def get_checkout_summary():
    cart = get_cart()

    if not cart["items"]:
        return {
            "status": "empty",
            "message": "Your cart is empty. There is nothing to checkout."
        }

    return {
        "status": "pending_confirmation",
        "items": cart["items"],
        "total": cart["total"],
        "message": (
            "Please review the order total and explicitly confirm "
            "before payment."
        )
    }
