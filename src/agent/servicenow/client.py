"""ServiceNow Table API client stub.

Hand-written on purpose (Module 2): no SDK. TODO(student) markers show what to complete.
"""
from __future__ import annotations

import time
from typing import Any

import requests

from agent import config


class ServiceNowError(RuntimeError):
    pass


class ServiceNowClient:
    def __init__(self, instance: str, user: str, password: str, timeout: float = 20.0) -> None:
        self.base = f"{instance}/api/now/table"
        self.session = requests.Session()
        self.session.auth = (user, password)
        self.session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> ServiceNowClient:
        s = config.load()
        return cls(s.sn_instance, s.sn_user, s.sn_password)

    # ---- low level -------------------------------------------------------
    def _request(self, method: str, url: str, *, retries: int = 3, **kw: Any) -> dict:
        last: Exception | None = None
        for attempt in range(retries):
            try:
                r = self.session.request(method, url, timeout=self.timeout, **kw)
            except requests.RequestException as e:  # network-level failure
                last = e
                time.sleep(2**attempt)
                continue
            if r.status_code in (429, 502, 503, 504):
                time.sleep(2**attempt)
                last = ServiceNowError(f"{r.status_code} {r.text[:200]}")
                continue
            if r.status_code >= 400:
                raise ServiceNowError(f"{method} {url} -> {r.status_code}: {r.text[:300]}")
            return r.json()
        raise ServiceNowError(f"giving up after {retries} attempts: {last}")

    # ---- table API -------------------------------------------------------
    def list(self, table: str, query: str = "", fields: list[str] | None = None, limit: int = 100,
             offset: int = 0) -> list[dict]:
        params: dict[str, Any] = {"sysparm_limit": limit, "sysparm_offset": offset, "sysparm_display_value": "false"}
        if query:
            params["sysparm_query"] = query
        if fields:
            params["sysparm_fields"] = ",".join(fields)
        return self._request("GET", f"{self.base}/{table}", params=params)["result"]

    def list_all(self, table: str, query: str = "", fields: list[str] | None = None, page: int = 100) -> list[dict]:
        """TODO(student): paginate until a short page is returned."""
        raise NotImplementedError

    def get(self, table: str, sys_id: str, fields: list[str] | None = None) -> dict:
        params = {"sysparm_fields": ",".join(fields)} if fields else None
        return self._request("GET", f"{self.base}/{table}/{sys_id}", params=params)["result"]

    def create(self, table: str, payload: dict) -> dict:
        return self._request("POST", f"{self.base}/{table}", json=payload)["result"]

    def update(self, table: str, sys_id: str, payload: dict) -> dict:
        """TODO(student, Module 8): capture a before-image of the fields in payload before PATCHing,
        and return both so audit.py can store it for rollback."""
        return self._request("PATCH", f"{self.base}/{table}/{sys_id}", json=payload)["result"]

    def delete(self, table: str, sys_id: str) -> None:
        self._request("DELETE", f"{self.base}/{table}/{sys_id}")

    # ---- convenience -----------------------------------------------------
    def new_incidents_since(self, watermark: str, fields: list[str] | None = None) -> list[dict]:
        """Incidents created after an ISO timestamp watermark (Rung 0 polling)."""
        return self.list("incident", f"sys_created_on>{watermark}^ORDERBYsys_created_on", fields)
