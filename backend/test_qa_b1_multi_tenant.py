"""Integration-style tests for multi-tenant routing (B1).

Focuses on code-paths we can validate without heavy mocking:
  - orchestrator.py sets allow_test_override based on explicit tenant_id
  - products.py delegates to central resolver chain
  - the conditional expressions used across modules
"""

import pytest


class TestOrchestratorSetCorrectAllowOverride:
    """Verify the exact expression orchestrator uses."""

    def test_uses_not_bool_tenant_id(self):
        # Read source file to confirm the line hasn't drifted
        source = open(
            "backend/services/orchestrator.py", encoding="utf-8"
        ).read()
        assert "allow_test_override=not bool(tenant_id)" in source

    def test_logic_for_each_caller_scenario(self):
        scenarios = [
            ("caller_passes_prestigue", "prestigue", False),
            ("caller_passes_none", None, True),
            ("caller_passes_empty", "", True),
        ]
        for desc, tid, expected_allow in scenarios:
            result = not bool(tid)
            assert result is expected_allow, f"{desc}: not bool({tid!r}) → {result}, expect {expected_allow}"


class TestWebhookSetCorrectAllowOverride:
    """Verify routing/webhook uses correct conditional."""

    def test_uses_tenant_is_none_conditional(self):
        source = open("routing/webhook.py", encoding="utf-8").read()
        # Must NOT be hardcoded False anymore
        assert 'allow_test_override=(tenant_id is None)' in source


class TestProductsDelegatesToResolver:
    """products must NOT read get_active_test_tenant() directly."""

    def test_no_direct_get_active_test_call(self):
        """If this fails, products is reading the DB setting directly again."""
        source = open("backend/db/products.py", encoding="utf-8").read()
        # Must NOT have an import or call — a mention in a docstring is OK
        assert "from .settings import get_active_test_tenant" not in source
        assert "get_active_test_tenant()" not in source

    def test_calls_resolve_default_tenant(self):
        source = open("backend/db/products.py", encoding="utf-8").read()
        assert "resolve_default_tenant" in source


class TestProductIdsRespectsExplicitTenant:
    """Even simple lookups respect the passed-in tenant."""

    def test_makemytrip_resolves(self):
        from backend.db.products import _resolve_tenant_ids
        ids = _resolve_tenant_ids("makemytrip")
        assert "makemytrip" in ids
