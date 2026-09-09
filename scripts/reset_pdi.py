"""Delete every record the seeder created (marker prefix [SYN] or [RT]). Pages until nothing is left."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent.servicenow import tables  # noqa: E402
from agent.servicenow.client import ServiceNowClient  # noqa: E402

QUERY = "descriptionSTARTSWITH[SYN]^ORdescriptionSTARTSWITH[RT]"


def main() -> int:
    sn = ServiceNowClient.from_env()
    n = 0
    for table in (tables.INCIDENT, tables.PROBLEM, tables.CHANGE, tables.KB):
        while True:
            page = sn.list(table, QUERY, ["sys_id"], limit=500)
            if not page:
                break
            for rec in page:
                sn.delete(table, rec["sys_id"])
                n += 1
    print(f"deleted {n} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
