"""Central error reporter must log, persist, and rate-limit notifies."""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
for path in (BACKEND_DIR, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)


class ErrorReporterTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "errors.db")
        os.environ["ROUTING_DB_PATH"] = self.db_path
        # Re-import database paths after env set is hard; patch get_db_context instead.
        import sqlite3
        from contextlib import contextmanager

        def _connect():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn

        @contextmanager
        def fake_ctx():
            conn = _connect()
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

        self._ctx_patch = patch("services.error_reporter.get_db_context", create=True)
        # Patch both import styles used inside the module
        self.patches = [
            patch("database.get_db_context", fake_ctx),
        ]
        for p in self.patches:
            p.start()

        # Ensure module uses our patched database
        import services.error_reporter as er
        self.er = er
        self._orig_persist_import = None

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self._tmpdir.cleanup()

    def test_report_error_logs_api_error_tag(self):
        with self.assertLogs("error_reporter", level="ERROR") as cm:
            self.er.report_error(
                "send2",
                "text",
                "boom",
                detail="body",
                http_status=200,
                wa_id="9198",
                notify=False,
            )
        self.assertTrue(any("API_ERROR" in line and "send2" in line for line in cm.output))

    def test_classify_opt_out_triggers_reporter(self):
        from routing.whatsapp import log_send2_outcome

        with (
            patch("services.error_reporter.report_error") as mock_report,
            self.assertLogs("chiki_webhook", level="WARNING") as cm,
        ):
            outcome = log_send2_outcome(
                "text", "919876543210", 200, "User has OPT OUT", tenant_id="demo",
            )
        self.assertEqual(outcome, "opt_out")
        self.assertTrue(any("SEND2_OPT_OUT" in line for line in cm.output))
        mock_report.assert_called()
        kwargs = mock_report.call_args.kwargs
        self.assertEqual(mock_report.call_args.args[0], "send2")
        self.assertEqual(kwargs.get("severity"), "warning")


if __name__ == "__main__":
    unittest.main()
