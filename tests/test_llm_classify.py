"""agent.analytics.llm_classify: request shape, response parsing and cost, without touching the network."""
from __future__ import annotations

from agent.analytics import llm_classify as m


def test_request_body_enforces_the_label_schema_and_wraps_text_as_data():
    body = m.request_body({"short_description": "VPN drops", "description": "since Friday"}, "claude-sonnet-4-6")
    assert body["model"] == "claude-sonnet-4-6" and body["max_tokens"] <= 128
    assert body["output_config"]["format"]["schema"]["properties"]["category"]["enum"] == m.CATEGORIES
    assert body["messages"][0]["content"].startswith("<ticket>\nVPN drops\nsince Friday\n</ticket>")
    assert "not an instruction" in body["system"] or "never an instruction" in body["system"]


def test_parse_response_reads_label_tokens_and_costs_the_call():
    fake = {"model": "claude-sonnet-4-6", "stop_reason": "end_turn",
            "content": [{"type": "text", "text": '{"category": "Network", "confidence": 0.91}'}],
            "usage": {"input_tokens": 312, "output_tokens": 21}}
    out = m.parse_response(fake, 840)
    assert out["pred_category"] == "Network" and out["confidence"] == 0.91 and out["latency_ms"] == 840
    assert out["input_tokens"] == 312 and out["output_tokens"] == 21
    assert out["cost_usd"] == round(312 * 3 / 1e6 + 21 * 15 / 1e6, 6)  # $0.001251


def test_parse_response_unknown_model_has_no_cost():
    fake = {"model": "claude-something-9", "usage": {"input_tokens": 10, "output_tokens": 5},
            "content": [{"type": "text", "text": '{"category": "Hardware", "confidence": 0.5}'}]}
    assert m.parse_response(fake, 1)["cost_usd"] is None
