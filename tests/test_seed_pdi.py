"""scripts/seed_pdi.py must adapt corpus values to whatever the target PDI release accepts."""
from __future__ import annotations

import importlib.util
import sys

from .conftest import ROOT

SEEDER = ROOT / "scripts" / "seed_pdi.py"


def load_seeder():
    spec = importlib.util.spec_from_file_location("seed_pdi", SEEDER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeClient:
    def __init__(self, rows=None, fail=False):
        self.rows, self.fail, self.calls = rows or [], fail, []

    def list(self, table, query="", fields=None, limit=100, offset=0):
        self.calls.append((table, query))
        if self.fail:
            raise RuntimeError("403 forbidden")
        return self.rows


def test_close_code_uses_live_choice_list_when_available():
    seed = load_seeder()
    modern = [{"value": "Solution provided", "label": "Solution provided"},
              {"value": "Workaround provided", "label": "Workaround provided"},
              {"value": "No resolution provided", "label": "No resolution provided"},
              {"value": "Duplicate", "label": "Duplicate"}]
    resolve = seed.close_code_resolver(FakeClient(modern))
    assert resolve("Solved (Permanently)") == "Solution provided"
    assert resolve("Solved (Work Around)") == "Workaround provided"
    assert resolve("Not Solved (Not Reproducible)") == "No resolution provided"
    assert resolve("Duplicate") == "Duplicate"  # already valid passes through


def test_close_code_keeps_legacy_values_on_older_release():
    seed = load_seeder()
    legacy = [{"value": "Solved (Permanently)", "label": "Solved (Permanently)"},
              {"value": "Solved (Work Around)", "label": "Solved (Work Around)"}]
    resolve = seed.close_code_resolver(FakeClient(legacy))
    assert resolve("Solved (Permanently)") == "Solved (Permanently)"
    # unknown even after fallback -> deterministic valid value rather than a blank that trips the data policy
    assert resolve("Not Solved (Not Reproducible)") == "Solved (Permanently)"


def test_close_code_matches_by_label_when_value_differs():
    seed = load_seeder()
    rows = [{"value": "solution_provided", "label": "Solution provided"}]
    resolve = seed.close_code_resolver(FakeClient(rows))
    assert resolve("Solved (Permanently)") == "solution_provided"


def test_close_code_falls_back_when_choice_table_unreadable():
    seed = load_seeder()
    client = FakeClient(fail=True)
    resolve = seed.close_code_resolver(client)
    assert client.calls[0][0] == "sys_choice"
    assert resolve("Solved (Permanently)") == "Solution provided"
    assert resolve("Something new") == "Something new"


def test_history_payload_applies_resolver_and_marker():
    seed = load_seeder()
    row = {"short_description": "s", "description": "d", "category": "Inquiry / Help", "subcategory": "How-to",
           "impact": "3", "urgency": "3", "contact_type": "email", "state": "7", "opened_at": "2026-03-01 09:00:00",
           "resolved_at": "2026-03-01 10:00:00", "closed_at": "2026-03-02 10:00:00",
           "close_code": "Solved (Permanently)", "close_notes": "n", "reassignment_count": "0", "reopen_count": "0",
           "made_sla": "true"}
    payload = seed.history_payload(row, "[SYN]", lambda c: "Solution provided")
    assert payload["close_code"] == "Solution provided"
    assert payload["category"] == "inquiry"
    assert payload["short_description"].startswith("[SYN] ")
    assert payload["sys_created_on"] == row["opened_at"]  # the backdating probe field
