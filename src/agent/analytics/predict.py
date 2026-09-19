"""Load the newest category model and classify one ticket. Read-tier inference; no writes, no LLM.

The harness calls classify() for Rung 1. When the poller or a tool calls it, the caller writes the
AuditEntry (tool="classify_incident", tier="read"); this module stays a pure function of its inputs.
"""
from __future__ import annotations

import json
import os
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


def selected_version(models_dir: Path = MODELS_DIR) -> str | None:
    """The version the agent serves: CATEGORY_MODEL_VERSION from .env if set, else the newest available.

    The bake-off memo (A1) names the chosen model; pinning it here makes that choice configuration rather
    than "whatever was trained last".
    """
    pinned = os.getenv("CATEGORY_MODEL_VERSION", "").strip()
    avail = versions(models_dir)
    if pinned:
        if pinned not in avail:
            raise FileNotFoundError(f"CATEGORY_MODEL_VERSION={pinned} but only {avail or 'no versions'} exist "
                                    f"under {models_dir}")
        return pinned
    return avail[-1] if avail else None


@lru_cache(maxsize=4)
def load(version: str | None = None, models_dir: Path = MODELS_DIR):
    """(pipeline, card) for a version, the pinned one, or the newest. Raises FileNotFoundError when nothing is trained."""
    import joblib

    version = version or selected_version(models_dir)
    if version is None:
        raise FileNotFoundError(f"no {TASK} model under {models_dir}; run python -m agent.analytics.train")
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
