"""Failure injector stub (Module 14). TODO(student): implement mechanisms listed in scenarios.yaml."""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

HERE = Path(__file__).parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario")
    a = ap.parse_args()
    scenarios = {s["id"]: s for s in yaml.safe_load((HERE / "scenarios.yaml").read_text())["scenarios"]}
    s = scenarios[a.scenario]
    print(f"would apply {s['mechanism']} and expect: {s['expected']}")
    raise NotImplementedError("wire the mechanism, run the agent, compare observed vs expected")


if __name__ == "__main__":
    raise SystemExit(main())
