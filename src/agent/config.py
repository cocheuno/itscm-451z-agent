"""Environment configuration. Refuses to start if a secret looks committed."""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    anthropic_model: str
    sn_instance: str
    sn_user: str
    sn_password: str
    max_cost_per_run_usd: float
    agent_mode: str  # dry_run | live


def _env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise RuntimeError(f"missing environment variable {name}; copy .env.example to .env")
    return v


def load() -> Settings:
    return Settings(
        anthropic_api_key=_env("ANTHROPIC_API_KEY"),
        anthropic_model=_env("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        sn_instance=_env("SN_INSTANCE").rstrip("/"),
        sn_user=_env("SN_USER"),
        sn_password=_env("SN_PASSWORD"),
        max_cost_per_run_usd=float(_env("MAX_COST_PER_RUN_USD", "1.00")),
        agent_mode=_env("AGENT_MODE", "dry_run"),
    )


def assert_env_not_tracked() -> None:
    """Guard: .env must never be tracked by git."""
    try:
        out = subprocess.run(["git", "ls-files", ".env"], cwd=ROOT, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return
    if out.stdout.strip():
        raise RuntimeError(".env is tracked by git — remove it from the index and rotate your keys")


if __name__ == "__main__":
    assert_env_not_tracked()
    s = load()
    print(f"config ok — instance {s.sn_instance}, model {s.anthropic_model}, mode {s.agent_mode}")
    sys.exit(0)
