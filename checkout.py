from cart import get_cart
from payments import razorpay_test_available


PAYMENT_UNAVAILABLE_MESSAGE = "Payment has not been processed because the payment integration is not connected."


def get_checkout_summary():
    cart = get_cart()

    if not cart["items"]:
        return {
            "status": "empty",
            "message": "Your cart is empty. There is nothing to checkout."
        }

    payment_available = razorpay_test_available()
    return {
        "status": "pending_confirmation",
        "items": cart["items"],
        "total": cart["total"],
        "payment_status": "test_available" if payment_available else "unavailable",
        "payment_message": (
            "Razorpay Test Mode is ready. Your payment will be confirmed only after server verification."
            if payment_available else PAYMENT_UNAVAILABLE_MESSAGE
        ),
        "message": (
            "Please review the order total and explicitly confirm "
            "before payment."
        )
    }
