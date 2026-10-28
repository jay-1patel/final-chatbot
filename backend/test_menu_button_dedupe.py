"""PDF/kit menu sanitize must not emit hyphen duplicates of vertical defaults."""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.auto_bifurcator import (  # noqa: E402
    AutoBifurcator,
    _menu_button_id,
    _normalize_menu_button_key,
    _sanitize_menu_buttons,
)
from shared.tenancy.merge import merge_layers  # noqa: E402
from shared.tenancy.defaults import get_vertical_defaults  # noqa: E402
from bots.customer_b2c.menus import get_main_menu  # noqa: E402


class MenuButtonDedupeTests(unittest.TestCase):
    def test_pdf_extractor_keeps_all_ten_menu_items(self):
        rows = [["Title", "Description", "Section", "Action"]]
        rows.extend(
            [f"Banking option {index}", f"Description {index}", "Banking", "faq"]
            for index in range(1, 11)
        )

        items = AutoBifurcator("state-bank-of-india").extract_menu_section(
            {"tables": [rows]},
            vertical="banking",
        )

        self.assertEqual(len(items), 10)
        self.assertEqual(items[-1]["title"], "Banking option 10")

    def test_ten_extracted_menu_items_render_as_ten_whatsapp_rows(self):
        rows = [["Title", "Description", "Section", "Action"]]
        rows.extend(
            [f"Banking option {index}", f"Description {index}", "Banking", "faq"]
            for index in range(1, 11)
        )
        extracted = AutoBifurcator("state-bank-of-india").extract_menu_section(
            {"tables": [rows]},
            vertical="banking",
        )
        buttons = _sanitize_menu_buttons(extracted, vertical="banking")
        profile = SimpleNamespace(
            brand=SimpleNamespace(name="State Bank of India"),
            display_name="State Bank of India",
            menu=SimpleNamespace(
                body="Welcome",
                buttons=[
                    SimpleNamespace(
                        id=button["id"],
                        title=button["title"],
                        description=button["description"],
                        section=button["section"],
                        icon="",
                        sort_order=button["sort_order"],
                        enabled=True,
                    )
                    for button in buttons
                ],
            ),
        )

        with (
            patch("shared.tenancy.resolver.resolve_effective_tenant_id", return_value="state-bank-of-india"),
            patch("shared.tenancy.loader.get_tenant_profile", return_value=profile),
        ):
            menu = get_main_menu("919500000000", tenant_id="state-bank-of-india")

        rendered_rows = [
            row
            for section in menu["sections"]
            for row in section["rows"]
        ]
        self.assertEqual(len(rendered_rows), 10)
        self.assertEqual(rendered_rows[-1]["title"], "Banking option 10")

    def test_menu_button_id_uses_underscores(self):
        self.assertEqual(_menu_button_id("menu-products"), "menu_products")
        self.assertEqual(_menu_button_id("menu_products"), "menu_products")
        self.assertEqual(_menu_button_id("Banking Products"), "banking_products")

    def test_normalize_equates_hyphen_and_underscore(self):
        self.assertEqual(
            _normalize_menu_button_key("menu-products"),
            _normalize_menu_button_key("menu_products"),
        )

    def test_sanitize_collapses_hyphen_duplicates_onto_banking_defaults(self):
        raw = [
            {
                "id": "menu-products",
                "title": "Banking Products",
                "description": "Accounts, cards & loans",
                "section": "Products",
                "intent": "offerings",
            },
            {
                "id": "menu_products",
                "title": "Banking Products",
                "description": "Accounts, cards & loans",
                "section": "Products",
                "intent": "product_details",
            },
            {
                "id": "menu-cards",
                "title": "Cards",
                "description": "Credit & debit card help",
                "section": "Products",
                "action": "offerings",
            },
            {
                "id": "menu_loans",
                "title": "Loans",
                "description": "Personal, home & business loans",
                "section": "Products",
                "intent": "product_details",
            },
            {
                "id": "menu-loans",
                "title": "Loans",
                "description": "Personal, home & business loans",
                "section": "Products",
                "action": "offerings",
            },
        ]
        buttons = _sanitize_menu_buttons(raw, vertical="banking")
        ids = [b["id"] for b in buttons]
        titles = [b["title"] for b in buttons]

        self.assertEqual(ids.count("menu_products"), 1)
        self.assertEqual(ids.count("menu_cards"), 1)
        self.assertEqual(ids.count("menu_loans"), 1)
        self.assertNotIn("menu-products", ids)
        self.assertNotIn("menu-cards", ids)
        self.assertNotIn("menu-loans", ids)
        self.assertEqual(titles.count("Banking Products"), 1)
        self.assertEqual(titles.count("Cards"), 1)
        self.assertEqual(titles.count("Loans"), 1)
        self.assertEqual(len(buttons), 3)

    def test_merge_with_defaults_does_not_double_after_sanitize(self):
        raw = [
            {"id": "menu-products", "title": "Banking Products", "description": "x", "section": "Products"},
            {"id": "menu-cards", "title": "Cards", "description": "y", "section": "Products"},
            {"id": "menu-loans", "title": "Loans", "description": "z", "section": "Products"},
        ]
        draft_buttons = _sanitize_menu_buttons(raw, vertical="banking")
        defaults = get_vertical_defaults("banking")
        merged = merge_layers(
            defaults,
            {"menu": {"buttons": draft_buttons}},
        )
        products = [
            b for b in merged["menu"]["buttons"]
            if _normalize_menu_button_key(b.get("title", "")) == "banking_products"
            or _normalize_menu_button_key(b.get("id", "")) == "menu_products"
        ]
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["id"], "menu_products")

    def test_merge_layers_collapses_raw_hyphen_duplicates_onto_defaults(self):
        """Draft/PDF layers with hyphen ids must not double Cards/Loans/Products."""
        defaults = get_vertical_defaults("banking")
        draft = {
            "menu": {
                "buttons": [
                    {
                        "id": "menu-products",
                        "title": "Banking Products",
                        "description": "Accounts, cards & loans",
                        "intent": "menu-products",
                    },
                    {
                        "id": "menu-cards",
                        "title": "Cards",
                        "description": "Credit & debit card help",
                        "intent": "offerings",
                    },
                    {
                        "id": "menu-loans",
                        "title": "Loans",
                        "description": "Personal, home & business loans",
                        "intent": "offerings",
                    },
                ]
            }
        }
        merged = merge_layers(defaults, draft)
        ids = [b["id"] for b in merged["menu"]["buttons"]]
        titles = [b["title"] for b in merged["menu"]["buttons"]]

        self.assertEqual(ids.count("menu_products"), 1)
        self.assertEqual(ids.count("menu_cards"), 1)
        self.assertEqual(ids.count("menu_loans"), 1)
        self.assertNotIn("menu-products", ids)
        self.assertNotIn("menu-cards", ids)
        self.assertNotIn("menu-loans", ids)
        self.assertEqual(titles.count("Banking Products"), 1)
        self.assertEqual(titles.count("Cards"), 1)
        self.assertEqual(titles.count("Loans"), 1)

    def test_merge_layers_collapses_both_forms_inside_one_layer(self):
        """A saved draft that already contains both id forms must still collapse."""
        layer = {
            "menu": {
                "buttons": [
                    {"id": "menu_products", "title": "Banking Products", "intent": "product_details"},
                    {"id": "menu_cards", "title": "Cards", "intent": "product_details"},
                    {"id": "menu-products", "title": "Banking Products", "intent": "menu-products"},
                    {"id": "menu_loans", "title": "Loans", "intent": "product_details"},
                    {"id": "menu-cards", "title": "Cards", "intent": "offerings"},
                    {"id": "menu-loans", "title": "Loans", "intent": "offerings"},
                ]
            }
        }
        merged = merge_layers({}, layer)
        ids = [b["id"] for b in merged["menu"]["buttons"]]
        titles = [b["title"] for b in merged["menu"]["buttons"]]
        self.assertEqual(ids, ["menu_products", "menu_cards", "menu_loans"])
        self.assertEqual(titles.count("Banking Products"), 1)
        self.assertEqual(titles.count("Cards"), 1)
        self.assertEqual(titles.count("Loans"), 1)


if __name__ == "__main__":
    unittest.main()
