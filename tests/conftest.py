"""Shared fixtures. The synthetic generator lives outside the package (data/synthetic/), so load it by path."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "data" / "synthetic" / "generate_tickets.py"


def load_generator_module():
    spec = importlib.util.spec_from_file_location("generate_tickets", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses need the module registered before exec
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def gen():
    return load_generator_module()


@pytest.fixture(scope="session")
def corpus(gen):
    """One deterministic generation per test session: (Corpus, patterns config)."""
    return gen.generate()
