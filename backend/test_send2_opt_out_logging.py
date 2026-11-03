"""Send2 OPT OUT responses must produce greppable logs (not silent failed: None)."""

import logging
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
for path in (BACKEND_DIR, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from routing.whatsapp import classify_send2_response, log_send2_outcome, send_whatsapp_message


class ClassifySend2ResponseTests(unittest.TestCase):
    def test_opt_out_body(self):
        self.assertEqual(
            classify_send2_response(200, "User has OPT OUT from receiving messages"),
            "opt_out",
        )

    def test_success_json(self):
        self.assertEqual(
            classify_send2_response(200, '{"success":true,"message":"ok"}'),
            "ok",
        )

    def test_http_error(self):
        self.assertEqual(classify_send2_response(500, "boom"), "error")


class OptOutLoggingTests(unittest.TestCase):
    def test_log_send2_outcome_emits_send2_opt_out(self):
        with self.assertLogs("chiki_webhook", level="WARNING") as cm:
            outcome = log_send2_outcome(
                "text",
                "919876543210",
                200,
                "User has OPT OUT",
                tenant_id="demo",
            )
        self.assertEqual(outcome, "opt_out")
        self.assertTrue(any("SEND2_OPT_OUT" in line for line in cm.output))

    def test_send_whatsapp_message_logs_opt_out_not_none(self):
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.text = "User has OPT OUT from this WhatsApp business"

        with (
            patch("routing.whatsapp.get_tenant_send2_credentials", return_value=("u", "p")),
            patch("routing.whatsapp.requests.post", return_value=fake_resp),
            patch("routing.hookdeck.tee_outbound"),
            self.assertLogs("chiki_webhook", level="WARNING") as cm,
        ):
            ok = send_whatsapp_message("919876543210", "hello", retries=2)

        self.assertFalse(ok)
        joined = "\n".join(cm.output)
        self.assertIn("SEND2_OPT_OUT", joined)
        self.assertNotIn("failed: None", joined)


if __name__ == "__main__":
    unittest.main()
