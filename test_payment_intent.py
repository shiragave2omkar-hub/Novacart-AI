import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import api
import audit
import cart


PAYMENT_REQUEST = "Pay for my order and tell me when the payment is successful."
PAYMENT_UNAVAILABLE_MESSAGE = "Payment has not been processed because the payment integration is not connected."


class PaymentIntentRoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        self.cart_file = temp_path / "cart.json"
        self.audit_file = temp_path / "audit_log.json"
        self.cart_patch = patch.object(cart, "CART_FILE", self.cart_file)
        self.audit_patch = patch.object(audit, "AUDIT_FILE", self.audit_file)
        self.environment_patch = patch.dict(os.environ, {"RAZORPAY_KEY_ID": "", "RAZORPAY_KEY_SECRET": ""})
        self.cart_patch.start()
        self.audit_patch.start()
        self.environment_patch.start()
        self.client = api.app.test_client()
        api.app.config.update(TESTING=True)
        cart.add_to_cart("L001")

    def tearDown(self):
        self.audit_patch.stop()
        self.cart_patch.stop()
        self.environment_patch.stop()
        self.temp_dir.cleanup()

    def assert_checkout_route(self, message):
        with patch("api.run_agent") as run_agent, patch("api.search_products") as search_products:
            response = self.client.post("/api/chat", json={"message": message})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["message"], PAYMENT_UNAVAILABLE_MESSAGE)
        self.assertIsNone(payload["recommendations"])
        self.assertEqual(payload["tool_events"], [{"name": "get_checkout_summary", "arguments": {}}])
        self.assertEqual(payload["cart"]["items"][0]["id"], "L001")
        run_agent.assert_not_called()
        search_products.assert_not_called()

    def test_payment_request_uses_existing_checkout_without_catalog_search(self):
        self.assert_checkout_route(PAYMENT_REQUEST)

    def test_checkout_command_uses_existing_checkout_without_catalog_search(self):
        self.assert_checkout_route("Checkout.")


if __name__ == "__main__":
    unittest.main()
