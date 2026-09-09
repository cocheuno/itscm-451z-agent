"""Delete every record the seeder created (marker prefix [SYN] or [RT])."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent.servicenow.client import ServiceNowClient  # noqa: E402


def main() -> int:
    sn = ServiceNowClient.from_env()
    n = 0
    for table in ("incident", "problem", "change_request", "kb_knowledge"):
        for rec in sn.list(table, "descriptionSTARTSWITH[SYN]^ORdescriptionSTARTSWITH[RT]", ["sys_id"], limit=1000):
            sn.delete(table, rec["sys_id"])
            n += 1
    print(f"deleted {n} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
