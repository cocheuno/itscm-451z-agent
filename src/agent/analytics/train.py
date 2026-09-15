"""Train the Rung 1 category classifier and save it as a versioned artifact with a model card.

    python -m agent.analytics.train --version 0.1 --adr ADR-0003
    python -m agent.analytics.train --version 0.1 --adr ADR-0003 --cutoff 2026-08-01

TODO(student, Module 3): implement build_pipeline(). Everything else here is plumbing you can keep.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd

from agent.analytics import features

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
TASK = "category"


def build_pipeline():
    """TODO(student, Module 3): return an unfitted sklearn Pipeline: text -> TF-IDF -> logistic regression.

    Start with TfidfVectorizer (word 1-2 grams, min_df=2, sublinear_tf=True) into
    LogisticRegression(max_iter=1000, class_weight="balanced"). Fit on features.text_of() strings; predict
    the category label. A1 adds gradient boosting and an LLM classifier as further rows of the bake-off.
    """
    raise NotImplementedError("build_pipeline: see TODO(student) in src/agent/analytics/train.py")


def fit_and_evaluate(pipeline, train: pd.DataFrame, test: pd.DataFrame) -> dict:
    """Fit on train, score on test; returns per-class precision/recall/F1, accuracy and a labelled confusion matrix."""
    from sklearn.metrics import classification_report, confusion_matrix

    x_train = [features.text_of(r) for r in train.to_dict("records")]
    x_test = [features.text_of(r) for r in test.to_dict("records")]
    pipeline.fit(x_train, train[features.TARGET])
    pred = pipeline.predict(x_test)
    labels = sorted(train[features.TARGET].unique())
    report = classification_report(test[features.TARGET], pred, labels=labels, output_dict=True, zero_division=0)
    return {
        "accuracy": round(float(report["accuracy"]), 4),
        "macro_f1": round(float(report["macro avg"]["f1-score"]), 4),
        "per_class": {lab: {k: round(float(v), 4) for k, v in report[lab].items()} for lab in labels},
        "confusion": {"labels": labels,
                      "matrix": confusion_matrix(test[features.TARGET], pred, labels=labels).tolist()},
    }


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_card(version: str, cutoff: str, train: pd.DataFrame, test: pd.DataFrame, metrics: dict, adr: str,
               data_path: Path = features.HISTORY, pipeline=None) -> dict:
    """The card that travels with every artifact (COURSE_CONTEXT: models are change-managed artifacts)."""
    import sklearn

    return {
        "task": TASK,
        "version": version,
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "adr": adr,
        "features": {"text": list(features.TEXT_COLS)},
        "training_data": {"path": str(data_path.relative_to(features.ROOT)), "sha256": file_sha256(data_path),
                          "rows": int(len(train)), "split": f"opened_at < {cutoff}"},
        "test_data": {"rows": int(len(test)), "split": f"opened_at >= {cutoff}"},
        "metrics": metrics,
        "pipeline": repr(pipeline) if pipeline is not None else None,
        "environment": {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
                        "pandas": pd.__version__},
    }


def save(pipeline, card: dict, models_dir: Path = MODELS_DIR) -> tuple[Path, Path]:
    models_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{card['task']}-v{card['version']}"
    artifact, card_path = models_dir / f"{stem}.joblib", models_dir / f"{stem}.json"
    joblib.dump(pipeline, artifact)
    card_path.write_text(json.dumps(card, indent=2) + "\n")
    return artifact, card_path


def print_report(metrics: dict) -> None:
    print(f"accuracy {metrics['accuracy']}  macro F1 {metrics['macro_f1']}")
    print(f"{'class':<16}{'precision':>10}{'recall':>8}{'f1':>8}{'n':>6}")
    for lab, m in metrics["per_class"].items():
        print(f"{lab:<16}{m['precision']:>10.3f}{m['recall']:>8.3f}{m['f1-score']:>8.3f}{int(m['support']):>6}")
    labels = metrics["confusion"]["labels"]
    print("confusion (rows = truth, columns = predicted):")
    print(" " * 16 + "".join(f"{lab[:7]:>8}" for lab in labels))
    for lab, row in zip(labels, metrics["confusion"]["matrix"], strict=True):
        print(f"{lab:<16}" + "".join(f"{n:>8}" for n in row))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", required=True, help="artifact version, e.g. 0.1")
    ap.add_argument("--adr", required=True, help="the ADR that records the split and the model choice")
    ap.add_argument("--cutoff", default=features.DEFAULT_CUTOFF)
    a = ap.parse_args(argv)

    df = features.load_history()
    train, test = features.time_split(df, a.cutoff)
    print(f"train {len(train)} rows (opened_at < {a.cutoff}), test {len(test)} rows")
    pipeline = build_pipeline()
    metrics = fit_and_evaluate(pipeline, train, test)
    print_report(metrics)
    card = model_card(a.version, a.cutoff, train, test, metrics, a.adr, pipeline=pipeline)
    artifact, card_path = save(pipeline, card)
    size_mb = artifact.stat().st_size / 1e6
    shown = artifact.relative_to(features.ROOT) if artifact.is_relative_to(features.ROOT) else artifact
    print(f"saved {shown} ({size_mb:.1f} MB) and {card_path.name}")
    if size_mb > 3:
        print("artifact is over a few MB: discuss Git LFS in the ADR before committing it (COURSE_CONTEXT.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
