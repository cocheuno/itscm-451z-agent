"""Load the newest category model and classify one ticket. Read-tier inference; no writes, no LLM.

The harness calls classify() for Rung 1. When the poller or a tool calls it, the caller writes the
AuditEntry (tool="classify_incident", tier="read"); this module stays a pure function of its inputs.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from agent.analytics import features
from agent.analytics.train import MODELS_DIR, TASK


def versions(models_dir: Path = MODELS_DIR) -> list[str]:
    """Available versions, oldest first, from the model cards present (an artifact without a card does not count)."""
    found = []
    for card in sorted(models_dir.glob(f"{TASK}-v*.json")):
        version = card.name[len(f"{TASK}-v"):-len(".json")]
        if (models_dir / f"{TASK}-v{version}.joblib").exists():  # not with_suffix: "0.1" looks like a suffix
            found.append(version)
    return sorted(found, key=lambda v: tuple(int(p) if p.isdigit() else p for p in v.split(".")))


def available(models_dir: Path = MODELS_DIR) -> bool:
    return bool(versions(models_dir))


@lru_cache(maxsize=4)
def load(version: str | None = None, models_dir: Path = MODELS_DIR):
    """(pipeline, card) for a version, or the newest one. Raises FileNotFoundError when nothing is trained."""
    import joblib

    avail = versions(models_dir)
    if not avail:
        raise FileNotFoundError(f"no {TASK} model under {models_dir}; run python -m agent.analytics.train")
    version = version or avail[-1]
    stem = f"{TASK}-v{version}"
    return joblib.load(models_dir / f"{stem}.joblib"), json.loads((models_dir / f"{stem}.json").read_text())


def classify(ticket: dict, version: str | None = None, models_dir: Path = MODELS_DIR) -> dict:
    """{'pred_category', 'model_version', 'confidence'} for one ticket dict with short_description/description."""
    pipeline, card = load(version, models_dir)
    text = [features.text_of(ticket)]
    pred = str(pipeline.predict(text)[0])
    confidence = None
    if hasattr(pipeline, "predict_proba"):
        confidence = round(float(pipeline.predict_proba(text).max()), 4)
    return {"pred_category": pred, "model_version": card["version"], "confidence": confidence}
