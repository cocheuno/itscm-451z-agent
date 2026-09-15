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
    """Choice-list reader plus an incident store that stamps dates like the course PDI does.

    stamp_on_insert / stamp_on_update: overwrite opened_at/resolved_at/closed_at with NOW on that operation.
    """

    NOW = "2026-09-15 01:37:20"

    def __init__(self, rows=None, fail=False, stamp_on_insert=False, stamp_on_update=False, refuse_update=False):
        self.rows, self.fail, self.calls = rows or [], fail, []
        self.stamp_on_insert, self.stamp_on_update, self.refuse_update = stamp_on_insert, stamp_on_update, refuse_update
        self.store: dict[str, dict] = {}

    def list(self, table, query="", fields=None, limit=100, offset=0):
        self.calls.append((table, query))
        if self.fail:
            raise RuntimeError("403 forbidden")
        return self.rows

    def _stamp(self, rec):
        for f in ("sys_created_on", "opened_at", "resolved_at", "closed_at"):
            rec[f] = self.NOW

    def create(self, table, payload):
        sys_id = f"id{len(self.store) + 1}"
        rec = {**payload, "sys_id": sys_id, "number": f"INC{len(self.store) + 1:07d}"}
        if self.stamp_on_insert:
            self._stamp(rec)
        self.store[sys_id] = rec
        self.calls.append(("create", table, sys_id))
        return rec

    def get(self, table, sys_id, fields=None):
        rec = self.store[sys_id]
        return {f: rec.get(f, "") for f in fields} if fields else dict(rec)

    def update(self, table, sys_id, payload):
        self.calls.append(("update", table, sys_id))
        if self.refuse_update:
            raise RuntimeError("PATCH -> 403: ACL Exception Update Failed due to security constraints")
        self.store[sys_id].update(payload)
        if self.stamp_on_update:
            self._stamp(self.store[sys_id])
        return self.store[sys_id]


ROW = {"number": "SYN0000001", "short_description": "s", "description": "d", "category": "Inquiry / Help",
       "subcategory": "How-to", "impact": "3", "urgency": "3", "contact_type": "email", "state": "7",
       "opened_at": "2026-03-01 09:00:00", "resolved_at": "2026-03-01 10:00:00", "closed_at": "2026-03-02 10:00:00",
       "close_code": "Solved (Permanently)", "close_notes": "n", "reassignment_count": "0", "reopen_count": "0",
       "made_sla": "true"}


def rows(n):
    return [{**ROW, "number": f"SYN{i + 1:07d}"} for i in range(n)]


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
    payload = seed.history_payload(ROW, "[SYN]", lambda c: "Solution provided")
    assert payload["close_code"] == "Solution provided"
    assert payload["category"] == "inquiry"
    assert payload["short_description"].startswith("[SYN] ")
    assert payload["sys_created_on"] == ROW["opened_at"]  # the backdating probe field
    assert payload["correlation_id"] == "SYN0000001"  # join key back to the corpus CSV


def test_load_history_keeps_dates_when_insert_honours_them(tmp_path):
    seed = load_seeder()
    sn = FakeClient()
    report, patched = seed.load_history(sn, rows(3), "[SYN]", lambda c: c, map_path=tmp_path / "map.csv")
    assert all(report[d] for d in seed.DATE_FIELDS)
    assert patched is False
    assert [c for c in sn.calls if c[0] == "update"] == []
    assert (tmp_path / "map.csv").read_text().splitlines()[1] == "SYN0000001,id1,INC0000001"


def test_load_history_patches_every_row_when_update_restores_dates(tmp_path):
    seed = load_seeder()
    sn = FakeClient(stamp_on_insert=True)
    report, patched = seed.load_history(sn, rows(3), "[SYN]", lambda c: c, map_path=tmp_path / "map.csv")
    assert not any(report[d] for d in seed.DATE_FIELDS)
    assert patched is True
    assert [c[2] for c in sn.calls if c[0] == "update"] == ["id1", "id2", "id3"]
    assert sn.store["id3"]["opened_at"] == ROW["opened_at"]


def test_load_history_stops_patching_when_update_is_stamped_too(tmp_path, capsys):
    seed = load_seeder()
    sn = FakeClient(stamp_on_insert=True, stamp_on_update=True)
    report, patched = seed.load_history(sn, rows(3), "[SYN]", lambda c: c, map_path=tmp_path / "map.csv")
    assert patched is False
    assert [c[2] for c in sn.calls if c[0] == "update"] == ["id1"]  # one experiment, then no wasted calls
    assert sn.store["id2"]["correlation_id"] == "SYN0000002"  # the join key survives either way
    out = capsys.readouterr().out
    assert "backdating probe" in out and "after PATCH" in out and "OVERRIDDEN" in out


def test_load_history_survives_a_refused_patch(tmp_path, capsys):
    seed = load_seeder()
    sn = FakeClient(stamp_on_insert=True, refuse_update=True)
    report, patched = seed.load_history(sn, rows(3), "[SYN]", lambda c: c, map_path=tmp_path / "map.csv")
    assert patched is False
    assert [c[2] for c in sn.calls if c[0] == "update"] == ["id1"]
    assert len([c for c in sn.calls if c[0] == "create"]) == 3  # the load finished
    assert "after PATCH: refused -> PATCH -> 403: ACL Exception" in capsys.readouterr().out
