"""Active WhatsApp test tenant must override phone binding and user stamps."""

import os
import sys
import unittest
from unittest.mock import patch

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
for path in (BACKEND_DIR, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from shared.tenancy.resolver import resolve_effective_tenant_id


class ActiveTestTenantRoutingTests(unittest.TestCase):
    def test_active_test_beats_explicit_phone_bound_hint(self):
        with patch(
            "shared.tenancy.resolver._active_test_override",
            return_value="leeway-softech",
        ):
            tid = resolve_effective_tenant_id(
                "919512777899",
                tenant_id="meridian-bank",
            )
        self.assertEqual(tid, "leeway-softech")

    def test_hint_used_when_no_active_test(self):
        with (
            patch("shared.tenancy.resolver._active_test_override", return_value=None),
            patch("shared.tenancy.store.get_tenant", return_value={"id": "2", "slug": "meridian-bank"}),
        ):
            tid = resolve_effective_tenant_id("919512777899", tenant_id="meridian-bank")
        self.assertEqual(tid, "meridian-bank")


if __name__ == "__main__":
    unittest.main()
