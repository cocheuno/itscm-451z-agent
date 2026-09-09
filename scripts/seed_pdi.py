"""Seed the PDI with synthetic tickets (idempotent: run reset_pdi.py first if re-seeding)."""
import runpy
import sys
from pathlib import Path

sys.argv = [sys.argv[0], *sys.argv[1:]]
runpy.run_path(str(Path(__file__).resolve().parents[1] / "data" / "synthetic" / "generate_tickets.py"), run_name="__main__")
