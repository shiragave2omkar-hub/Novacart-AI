import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import api
import audit
import cart
import payments
from checkout import PAYMENT_UNAVAILABLE_MESSAGE, get_checkout_summary


TEST_KEY_ID = "rzp_test_novacart"
TEST_KEY_SECRET = "test_secret"


class RazorpayPaymentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        self.cart_patch = patch.object(cart, "CART_FILE", temp_path / "cart.json")
        self.audit_patch = patch.object(audit, "AUDIT_FILE", temp_path / "audit_log.json")
        self.environment_patch = patch.dict(os.environ, {
            "RAZORPAY_KEY_ID": TEST_KEY_ID,
            "RAZORPAY_KEY_SECRET": TEST_KEY_SECRET,
        })
        self.cart_patch.start()
        self.audit_patch.start()
        self.environment_patch.start()
        api.PENDING_PAYMENT_ORDERS.clear()
        api.app.config.update(TESTING=True)
        self.client = api.app.test_client()

    def tearDown(self):
        api.PENDING_PAYMENT_ORDERS.clear()
        self.environment_patch.stop()
        self.audit_patch.stop()
        self.cart_patch.stop()
        self.temp_dir.cleanup()

    def add_cart_item(self):
        cart.add_to_cart("L001")

    def test_empty_cart_order_is_rejected(self):
        response = self.client.post("/api/payment/create-order")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Your cart is empty. There is nothing to checkout.")

    def test_missing_credentials_keep_checkout_unavailable(self):
        self.add_cart_item()
        with patch.dict(os.environ, {"RAZORPAY_KEY_ID": "", "RAZORPAY_KEY_SECRET": ""}):
            summary = get_checkout_summary()
            response = self.client.post("/api/payment/create-order")

        self.assertEqual(summary["payment_status"], "unavailable")
        self.assertEqual(summary["payment_message"], PAYMENT_UNAVAILABLE_MESSAGE)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["error"], PAYMENT_UNAVAILABLE_MESSAGE)

    @patch("payments.razorpay.Client")
    def test_order_amount_matches_server_cart_total_in_paise(self, client_constructor):
        self.add_cart_item()
        server_total = cart.get_cart()["total"]
        razorpay_client = MagicMock()
        razorpay_client.order.create.return_value = {"id": "order_test_123"}
        client_constructor.return_value = razorpay_client

        response = self.client.post("/api/payment/create-order")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["amount"], server_total * 100)
        self.assertEqual(payload["currency"], "INR")
        self.assertEqual(payload["cart"]["total"], server_total)
        order_data = razorpay_client.order.create.call_args.kwargs["data"]
        self.assertEqual(order_data["amount"], server_total * 100)
        self.assertEqual(order_data["currency"], "INR")
        self.assertNotIn(TEST_KEY_SECRET, str(payload))

    def test_successful_signature_verification_reports_success_after_sdk_check(self):
        order_id = "order_test_verified"
        api.PENDING_PAYMENT_ORDERS[order_id] = {"amount": 6099000, "currency": "INR", "receipt": "novacart_test"}
        razorpay_client = MagicMock()
        with patch("payments.get_razorpay_client", return_value=(razorpay_client, TEST_KEY_ID)):
            response = self.client.post("/api/payment/verify", json={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": "pay_test_verified",
                "razorpay_signature": "valid_signature",
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "verified")
        razorpay_client.utility.verify_payment_signature.assert_called_once()
        self.assertEqual(audit.get_audit_log()[-1]["event"], "payment_verified")

    def test_invalid_signature_is_rejected_and_audited(self):
        order_id = "order_test_invalid"
        api.PENDING_PAYMENT_ORDERS[order_id] = {"amount": 6099000, "currency": "INR", "receipt": "novacart_test"}
        razorpay_client = MagicMock()
        razorpay_client.utility.verify_payment_signature.side_effect = ValueError("invalid signature")
        with patch("payments.get_razorpay_client", return_value=(razorpay_client, TEST_KEY_ID)):
            response = self.client.post("/api/payment/verify", json={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": "pay_test_invalid",
                "razorpay_signature": "invalid_signature",
            })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Payment was not verified.")
        self.assertEqual(audit.get_audit_log()[-1]["event"], "payment_verification_failed")


if __name__ == "__main__":
    unittest.main()
