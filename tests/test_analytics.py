"""Rung 1 scaffolding: feature helpers, the time split, the model card, and predict's artifact discovery."""
from __future__ import annotations

import json

import pytest

from agent.analytics import features, predict, train

from .conftest import ROOT

FIXTURE = ROOT / "tests" / "fixtures" / "history_sample.csv"


def test_fixture_loads_with_parsed_dates_and_boolean_sla():
    df = features.load_history(FIXTURE)
    assert len(df) > 40
    assert str(df["opened_at"].dtype).startswith("datetime64")
    assert df["made_sla"].dtype == bool
    assert set(df[features.TARGET]) <= {"Network", "Hardware", "Software", "Database", "Inquiry / Help", "Security"}


def test_text_of_tolerates_missing_description():
    assert features.text_of({"short_description": "VPN drops", "description": None}) == "VPN drops"
    assert features.text_of({"description": "only a body"}) == "only a body"


def test_time_split_is_strict_on_the_cutoff():
    df = features.load_history(FIXTURE)
    train_df, test_df = features.time_split(df, "2026-08-01")
    assert len(train_df) + len(test_df) == len(df)
    assert (train_df["opened_at"] < "2026-08-01").all()
    assert (test_df["opened_at"] >= "2026-08-01").all()
    assert len(test_df) >= 5  # August is the test month


def test_time_split_refuses_an_empty_side():
    df = features.load_history(FIXTURE)
    with pytest.raises(ValueError, match="test=0"):
        features.time_split(df, "2027-01-01")


def test_build_pipeline_rejects_unknown_kinds():
    with pytest.raises(ValueError, match="unknown pipeline"):
        train.build_pipeline("svm")


@pytest.mark.parametrize("kind", train.PIPELINES)
def test_build_pipeline_returns_a_fit_predict_pipeline_once_implemented(kind):
    """Skips while the TODO(student) is open; once implemented, each kind must be an unfitted sklearn pipeline."""
    try:
        pipe = train.build_pipeline(kind)
    except NotImplementedError:
        pytest.skip(f"TODO(student): build_pipeline({kind!r}) not implemented yet")
    assert hasattr(pipe, "fit") and hasattr(pipe, "predict")
    df = features.load_history(FIXTURE)
    train_df, test_df = features.time_split(df, "2026-08-01")
    metrics = train.fit_and_evaluate(pipe, train_df, test_df)
    assert 0.0 <= metrics["accuracy"] <= 1.0


def test_fit_evaluate_save_and_predict_round_trip(tmp_path):
    """The plumbing around build_pipeline works with any sklearn text pipeline."""
    sklearn = pytest.importorskip("sklearn")
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline

    df = features.load_history(FIXTURE)
    train_df, test_df = features.time_split(df, "2026-08-01")
    pipe = make_pipeline(TfidfVectorizer(), LogisticRegression(max_iter=200))
    metrics = train.fit_and_evaluate(pipe, train_df, test_df)
    assert 0.0 <= metrics["accuracy"] <= 1.0 and 0.0 <= metrics["macro_f1"] <= 1.0
    assert set(metrics["per_class"]) == set(metrics["confusion"]["labels"])
    assert sum(map(sum, metrics["confusion"]["matrix"])) == len(test_df)

    card = train.model_card("0.0", "2026-08-01", train_df, test_df, metrics, "ADR-0003", FIXTURE, pipe)
    assert card["training_data"]["sha256"] == train.file_sha256(FIXTURE)
    assert card["environment"]["scikit-learn"] == sklearn.__version__
    artifact, card_path = train.save(pipe, card, tmp_path)
    assert artifact.name == "category-v0.0.joblib" and json.loads(card_path.read_text())["adr"] == "ADR-0003"

    predict.load.cache_clear()
    assert predict.versions(tmp_path) == ["0.0"] and predict.available(tmp_path)
    out = predict.classify({"short_description": "VPN tunnel drops every hour", "description": ""}, models_dir=tmp_path)
    assert out["model_version"] == "0.0" and out["pred_category"] in metrics["confusion"]["labels"]
    assert out["confidence"] is not None and 0.0 < out["confidence"] <= 1.0


def test_predict_without_a_model_is_explicit(tmp_path):
    predict.load.cache_clear()
    assert predict.versions(tmp_path) == [] and not predict.available(tmp_path)
    (tmp_path / "category-v9.9.json").write_text("{}")  # a card without an artifact does not count
    assert predict.versions(tmp_path) == []
    with pytest.raises(FileNotFoundError, match="agent.analytics.train"):
        predict.classify({"short_description": "x"}, models_dir=tmp_path)


def test_selected_version_prefers_the_pin_and_falls_back_to_newest(tmp_path, monkeypatch):
    for v in ("0.1", "0.2"):
        (tmp_path / f"category-v{v}.joblib").write_bytes(b"x")
        (tmp_path / f"category-v{v}.json").write_text("{}")
    monkeypatch.delenv("CATEGORY_MODEL_VERSION", raising=False)
    assert predict.selected_version(tmp_path) == "0.2"
    monkeypatch.setenv("CATEGORY_MODEL_VERSION", "0.1")
    assert predict.selected_version(tmp_path) == "0.1"
    monkeypatch.setenv("CATEGORY_MODEL_VERSION", "9.9")
    with pytest.raises(FileNotFoundError, match="CATEGORY_MODEL_VERSION=9.9"):
        predict.selected_version(tmp_path)
