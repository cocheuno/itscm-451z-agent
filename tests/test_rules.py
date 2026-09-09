from agent.rung0_poller import classify_with_rules


def test_vpn_rule():
    assert classify_with_rules({"short_description": "VPN drops", "description": ""})["pred_category"] == "Network"


def test_no_match():
    assert classify_with_rules({"short_description": "???", "description": ""})["pred_category"] is None
