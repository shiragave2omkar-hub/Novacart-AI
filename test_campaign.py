import unittest

from campaign import (
    calculate_campaign_economics,
    select_real_products,
)


class CampaignEconomicsTests(unittest.TestCase):
    def test_usb_c_hub_economics_use_demo_cohort_and_lowest_price(self):
        products = select_real_products("USB-C Hub", limit=5)

        economics = calculate_campaign_economics(
            "USB-C Hub",
            products,
            discount_percent=10,
            max_discount_inr=500,
        )

        self.assertEqual(economics["target_customers"], 6)
        self.assertEqual(economics["expected_orders"], 3)
        self.assertEqual(
            economics["inputs"]["revenue_product"]["id"],
            "A055",
        )
        self.assertEqual(economics["estimated_revenue_inr"], 10497.0)
        self.assertEqual(economics["discount_cost_inr"], 1049.7)
        self.assertEqual(
            economics["net_incremental_revenue_inr"],
            9447.3,
        )
        self.assertEqual(economics["estimated_roi_percent"], 900.0)

    def test_economics_are_zero_without_a_priced_product(self):
        economics = calculate_campaign_economics(
            "USB-C Hub",
            [{"id": "A000", "category": "USB-C Hub", "price_inr": None}],
            discount_percent=10,
            max_discount_inr=500,
        )

        self.assertEqual(economics["expected_orders"], 0)
        self.assertEqual(economics["estimated_revenue_inr"], 0.0)
        self.assertEqual(economics["discount_cost_inr"], 0.0)


if __name__ == "__main__":
    unittest.main()
