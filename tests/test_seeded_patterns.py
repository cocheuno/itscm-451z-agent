"""Every deliberately seeded pattern in the historical corpus must be statistically present and recoverable.

These tests read the corpus the way the student will (CSV columns only) and compare against the
in-memory manifest, which is never written inside the repo. See COURSE_CONTEXT.md, PRIORITY TASK.
"""
from __future__ import annotations

import csv
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import pytest

from agent.workflow.sla import TARGETS_MIN, priority

from .conftest import ROOT

EVAL_DIR = ROOT / "data" / "eval"
FMT = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------- fixtures / helpers
@pytest.fixture(scope="session")
def history(gen, corpus):
    c, pat = corpus
    return [gen.history_row(t, pat["timestamp_format"]) for t in c.history]


@pytest.fixture(scope="session")
def manifest(corpus):
    return corpus[0].manifest


def opened(row: dict) -> datetime:
    return datetime.strptime(row["opened_at"], FMT)


def tokens(text: str) -> set[str]:
    return {w.strip(".,;:!?'\"()-").lower() for w in text.split() if len(w) > 2}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def idf_table(texts: list[str]) -> dict[str, float]:
    df: Counter = Counter()
    for t in texts:
        df.update(tokens(t))
    n = len(texts)
    return {w: math.log(n / c) for w, c in df.items()}


def weighted_jaccard(a: set[str], b: set[str], idf: dict[str, float]) -> float:
    union = sum(idf.get(w, 0.0) for w in a | b)
    return sum(idf.get(w, 0.0) for w in a & b) / union if union else 0.0


def mean_pairwise_similarity(texts_a: list[str], texts_b: list[str] | None, idf: dict[str, float] | None,
                             limit: int = 400) -> float:
    """Mean pairwise (IDF-weighted) Jaccard over a deterministic sample of pairs. texts_b=None -> within texts_a."""
    ta = [tokens(t) for t in texts_a]
    tb = [tokens(t) for t in texts_b] if texts_b is not None else ta
    pairs = [(i, j) for i in range(len(ta)) for j in range(len(tb)) if texts_b is not None or i < j]
    sample = pairs[:: max(1, len(pairs) // limit)]
    if idf is None:
        return statistics.mean(jaccard(ta[i], tb[j]) for i, j in sample)
    return statistics.mean(weighted_jaccard(ta[i], tb[j], idf) for i, j in sample)


def pearson(x: list[float], y: list[float]) -> float:
    mx, my = statistics.mean(x), statistics.mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / (sxx * syy) ** 0.5


# ---------------------------------------------------------------- reproducibility & hygiene
def test_regeneration_matches_committed_corpus(gen, corpus, tmp_path):
    """A clean clone regenerates data/eval byte for byte (fixed seed, stdlib random, no network)."""
    c, pat = corpus
    hashes = gen.write_corpus(c, tmp_path, pat["timestamp_format"])
    for name, h in hashes.items():
        assert gen.sha256_file(EVAL_DIR / name) == h, f"{name} in data/eval differs from a fresh generation"


def test_corpus_size_and_span(history, manifest):
    assert 3000 <= len(history) <= 5000
    first, last = min(map(opened, history)), max(map(opened, history))
    assert first >= datetime(2026, 3, 1) and last < datetime(2026, 9, 1)
    assert manifest["history"]["closed_incidents"] == len(history)


def test_corpus_carries_no_truth_columns_or_markers(gen):
    with (EVAL_DIR / "incidents_history.csv").open(newline="") as f:
        header = next(csv.reader(f))
    assert set(header) == set(gen.HISTORY_FIELDS)
    banned = {"tag", "cluster", "poison", "spike", "gt_", "manifest", "root_cause"}
    assert not [h for h in header if any(b in h.lower() for b in banned)]
    text = (EVAL_DIR / "incidents_history.csv").read_text()
    assert gen.MARK not in text, "the [SYN] marker is added at PDI load time, not in the corpus"


def test_manifest_refuses_unignored_repo_path(gen):
    gen.assert_manifest_path_safe(ROOT / "data" / "eval" / gen.MANIFEST_NAME)  # gitignored by name -> allowed
    with pytest.raises(SystemExit):
        gen.assert_manifest_path_safe(ROOT / "data" / "eval" / "truth.json")


def test_timestamps_and_priority_matrix_are_consistent(history):
    for r in history:
        o, res, clo = opened(r), datetime.strptime(r["resolved_at"], FMT), datetime.strptime(r["closed_at"], FMT)
        assert o < res <= clo
        assert int(r["priority"]) == priority(int(r["impact"]), int(r["urgency"]))
        assert int(r["state"]) == 7
        assert (r["made_sla"] == "true") == (int(r["resolve_minutes"]) <= int(r["sla_target_minutes"]))


def test_sla_targets_match_workflow_sla(corpus):
    """patterns.yaml copies the resolution targets so the corpus stays stable; flag drift against sla.py."""
    _, pat = corpus
    assert pat["breach"]["sla_resolution_minutes"] == {p: t[1] for p, t in TARGETS_MIN.items()}


# ---------------------------------------------------------------- 1. five latent problem clusters
def test_five_clusters_are_paraphrased_families(history, manifest):
    by_number = {r["number"]: r for r in history}
    idf = idf_table([r["short_description"] for r in history])
    clusters = manifest["clusters"]
    assert len(clusters) == 5
    assert len({c["category"] for c in clusters}) >= 4, "clusters should span categories"
    for c in clusters:
        members = [by_number[n] for n in c["ticket_numbers"]]
        assert 40 <= len(members) <= 120, c["id"]
        shorts = [m["short_description"] for m in members]
        assert len(set(shorts)) == len(shorts), f"{c['id']} has template-stamped duplicates"
        plain = mean_pairwise_similarity(shorts, None, None)
        assert 0.05 < plain < 0.5, f"{c['id']} wording too uniform or too scattered: {plain:.2f}"
        members_set = set(c["ticket_numbers"])
        background = [r["short_description"] for r in history
                      if r["subcategory"] == c["subcategory"] and r["number"] not in members_set]
        assert len(background) >= 20, "cluster subcategory needs ordinary tickets too"
        within = mean_pairwise_similarity(shorts, None, idf)
        between = mean_pairwise_similarity(shorts, background, idf)
        assert within > 1.5 * between, f"{c['id']}: within {within:.3f} vs background {between:.3f}"
        ci_visible = sum(1 for m in members if m["cmdb_ci"])
        assert 0 < ci_visible < 0.6 * len(members), "the CI column must not give the cluster away"


# ---------------------------------------------------------------- 2. change-caused spike
def test_change_spike_exceeds_baseline(history, manifest):
    sp = manifest["change_spike"]
    lo, hi = (datetime.strptime(s, FMT) for s in sp["window"])
    affected = set(sp["affected_categories"])
    span_hours = (hi - lo).total_seconds() / 3600
    all_affected = [r for r in history if r["category"] in affected]
    in_window = [r for r in all_affected if lo <= opened(r) < hi]
    total_hours = (max(map(opened, history)) - min(map(opened, history))).total_seconds() / 3600
    baseline = (len(all_affected) - len(in_window)) * span_hours / (total_hours - span_hours)
    assert len(in_window) > 2 * baseline, f"spike {len(in_window)} vs baseline {baseline:.1f}"
    assert len(in_window) >= sp["count"]
    # decoy changes must not show a comparable burst
    with (EVAL_DIR / "changes.csv").open(newline="") as f:
        changes = {c["number"]: c for c in csv.DictReader(f)}
    for num in sp["decoy_change_numbers"]:
        end = datetime.strptime(changes[num]["end"], FMT)
        w_lo, w_hi = end + timedelta(hours=sp["lag_hours"][0]), end + timedelta(hours=sp["lag_hours"][1])
        n = sum(1 for r in all_affected if w_lo <= opened(r) < w_hi)
        assert n < 2 * baseline, f"decoy {num} shows a burst ({n})"


# ---------------------------------------------------------------- 3. weekly seasonality + trend
def test_weekly_seasonality(history):
    by_dow = Counter(opened(r).weekday() for r in history)
    weekdays = [by_dow[d] for d in range(1, 5)]
    assert by_dow[0] > 1.2 * statistics.mean(weekdays), "Monday should peak"
    assert statistics.mean([by_dow[5], by_dow[6]]) < 0.4 * statistics.mean(weekdays), "weekends should be quiet"
    by_hour = Counter(opened(r).hour for r in history)
    assert sum(by_hour[h] for h in (9, 10, 11)) > 5 * sum(by_hour[h] for h in range(0, 6))


def test_upward_trend(history):
    weekly: Counter = Counter()
    for r in history:
        o = opened(r)
        weekly[(o - timedelta(days=o.weekday())).date()] += 1  # Monday-anchored weeks
    weeks = sorted(weekly)[1:-1]  # drop partial first/last weeks
    counts = [weekly[w] for w in weeks]
    assert len(counts) >= 20
    r = pearson(list(range(len(counts))), [float(c) for c in counts])
    assert r > 0.5, f"weekly volume should trend upward (r={r:.2f})"
    assert statistics.mean(counts[-4:]) > 1.15 * statistics.mean(counts[:4])


# ---------------------------------------------------------------- 4. degrading MTTR in one category
def test_degrading_category_mttr_is_monotonic_ish(history, manifest):
    deg = manifest["degrading_mttr"]["category"]
    monthly: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for r in history:
        monthly[r["category"]][r["opened_at"][:7]].append(int(r["resolve_minutes"]))
    months = sorted(monthly[deg])
    assert len(months) == 6
    means = [statistics.mean(monthly[deg][m]) for m in months]
    medians = [statistics.median(monthly[deg][m]) for m in months]
    assert pearson(list(range(6)), means) > 0.85
    assert means[-1] > 1.5 * means[0]
    assert sum(1 for a, b in zip(means, means[1:], strict=False) if b <= a) <= 1, "at most one monthly dip"
    assert medians[-1] > 1.5 * medians[0]
    # control: no other category shows the same steady climb
    for cat in monthly:
        if cat == deg:
            continue
        other = [statistics.mean(monthly[cat][m]) for m in sorted(monthly[cat])]
        climbing = pearson(list(range(len(other))), other) > 0.85 and other[-1] > 1.5 * other[0]
        assert not climbing, f"{cat} also degrades ({other[0]:.0f} -> {other[-1]:.0f})"


# ---------------------------------------------------------------- 5. learnable-but-imperfect breach signal
def test_group_load_feature_is_derivable_from_corpus(gen, corpus, history):
    """The manifest's group_load feature can be rebuilt from corpus columns alone (exactly, after the warm-up)."""
    c, pat = corpus
    derived = gen.compute_group_load(history)
    horizon = datetime(2026, 3, 1) + timedelta(days=pat["history"]["warmup_days"])
    assert all(derived[t.number] <= t.group_load_at_open for t in c.history)
    assert all(derived[t.number] == t.group_load_at_open for t in c.history if t.opened_at >= horizon)


def test_breach_signal_auc_in_window(gen, corpus, history):
    pytest.importorskip("sklearn")
    _, pat = corpus
    rate = sum(r["made_sla"] == "false" for r in history) / len(history)
    assert 0.12 < rate < 0.35
    auc = gen.estimate_breach_auc(history, pat)
    assert 0.75 <= auc <= 0.85, f"breach signal AUC {auc:.3f} outside the 0.75-0.85 window"


def test_breach_correlates_with_priority_and_off_hours(gen, corpus, history):
    _, pat = corpus
    feats = gen.breach_feature_rows(history, pat)
    by_prio = defaultdict(list)
    for f in feats:
        by_prio[f["priority"]].append(f["y"])
    assert statistics.mean(by_prio[1]) > statistics.mean(by_prio[3]) > statistics.mean(by_prio[5])
    off = [f["y"] for f in feats if f["off_hours"]]
    biz = [f["y"] for f in feats if not f["off_hours"]]
    assert statistics.mean(off) > statistics.mean(biz)


# ---------------------------------------------------------------- 6. poisoning bait
def test_poison_bait_present_but_unlabeled(history, manifest, corpus):
    _, pat = corpus
    by_number = {r["number"]: r for r in history}
    bait = manifest["poison_bait"]
    assert 5 <= len(bait) <= 12
    techniques = {b["technique"] for b in bait}
    assert len(techniques) == len(bait)
    categories = set(pat["breach"]["category"])
    for b in bait:
        row = by_number[b["number"]]
        assert row["category"] in categories  # ordinary label, nothing marks it
        assert int(row["state"]) == 7
    planted = {p["short_description"] for p in pat["poison_bait"]}
    assert planted == {by_number[b["number"]]["short_description"] for b in bait}


# ---------------------------------------------------------------- open set
def test_open_set(gen, corpus, manifest):
    c, pat = corpus
    rows = [gen.open_row(t, pat["timestamp_format"]) for t in c.open_set]
    assert len(rows) == pat["open_set"]["count"]
    lo, hi = datetime(2026, 9, 1), datetime(2026, 9, 9)
    assert all(lo <= opened(r) < hi for r in rows)
    assert {int(r["state"]) for r in rows} <= {1, 2}
    assert all(int(r["gt_priority"]) == priority(int(r["impact"]), int(r["urgency"])) for r in rows)
    in_clusters = sum(len(cl["open_set_ticket_numbers"]) for cl in manifest["clusters"])
    assert 5 <= in_clusters <= 40, "a few open tickets should belong to the seeded clusters for the live demo"
