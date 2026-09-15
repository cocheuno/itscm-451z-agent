"""ServiceNowClient._request behaviour that the seeder scripts depend on."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from agent.servicenow.client import ServiceNowClient, ServiceNowError


@dataclass
class FakeResponse:
    status_code: int
    content: bytes = b""

    @property
    def text(self) -> str:
        return self.content.decode()

    def json(self):
        return json.loads(self.content)


@dataclass
class FakeSession:
    responses: list[FakeResponse]
    calls: list[tuple[str, str]] = field(default_factory=list)
    auth: tuple = ()
    headers: dict = field(default_factory=dict)

    def request(self, method, url, **kw):
        self.calls.append((method, url))
        return self.responses.pop(0)


def make_client(*responses: FakeResponse) -> tuple[ServiceNowClient, FakeSession]:
    sn = ServiceNowClient("https://example.service-now.com", "u", "p")
    fake = FakeSession(list(responses))
    sn.session = fake  # type: ignore[assignment]
    return sn, fake


def test_delete_accepts_204_no_content():
    sn, fake = make_client(FakeResponse(204))
    assert sn.delete("incident", "abc") is None
    assert fake.calls == [("DELETE", "https://example.service-now.com/api/now/table/incident/abc")]


def test_empty_200_body_is_not_a_json_error():
    sn, _ = make_client(FakeResponse(200, b""))
    assert sn._request("DELETE", "x") == {}


def test_json_body_still_parsed():
    sn, _ = make_client(FakeResponse(200, b'{"result": [{"sys_id": "1"}]}'))
    assert sn.list("incident") == [{"sys_id": "1"}]


def test_4xx_raises_with_body():
    sn, _ = make_client(FakeResponse(403, b'{"error": {"message": "Data Policy Exception"}}'))
    with pytest.raises(ServiceNowError, match="403.*Data Policy"):
        sn.create("incident", {})
