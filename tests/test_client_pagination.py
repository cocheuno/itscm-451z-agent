"""Acceptance test for the Rung 0 TODO(student): ServiceNowClient.list_all pages until a short page.

Skipped while list_all still raises NotImplementedError; turns green when the exercise is done.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from agent.servicenow.client import ServiceNowClient

RECORDS = [{"sys_id": f"id{i}", "number": f"INC{i:07d}"} for i in range(1, 8)]  # 7 records, page of 3 -> 3+3+1


@dataclass
class PagingSession:
    calls: list[dict] = field(default_factory=list)
    auth: tuple = ()
    headers: dict = field(default_factory=dict)

    def request(self, method, url, params=None, timeout=None, **kw):
        self.calls.append(dict(params))
        limit, offset = int(params["sysparm_limit"]), int(params["sysparm_offset"])

        @dataclass
        class R:
            status_code: int = 200
            content: bytes = b"{}"
            text: str = ""

            def json(self):
                return {"result": RECORDS[offset:offset + limit]}
        return R()


def test_list_all_pages_until_a_short_page():
    sn = ServiceNowClient("https://example.service-now.com", "u", "p")
    sn.session = PagingSession()  # type: ignore[assignment]
    try:
        got = sn.list_all("incident", "active=true", ["sys_id", "number"], page=3)
    except NotImplementedError:
        pytest.skip("TODO(student): ServiceNowClient.list_all not implemented yet")
    assert got == RECORDS
    assert [c["sysparm_offset"] for c in sn.session.calls] == [0, 3, 6]
    assert all(c["sysparm_query"] == "active=true" for c in sn.session.calls)
