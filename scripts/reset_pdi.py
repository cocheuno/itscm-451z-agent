"""Delete every record the seeder created (marker prefix [SYN] or [RT]). Pages until nothing is left."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agent.servicenow import tables  # noqa: E402
from agent.servicenow.client import ServiceNowClient  # noqa: E402

MARKS = "descriptionSTARTSWITH[SYN]^ORdescriptionSTARTSWITH[RT]"
# kb_knowledge has no description field, and CMDB items keep their real names: both carry the marker in
# short_description instead (scripts/seed_pdi.py). Groups are left in place; they hold no synthetic data.
QUERIES = {tables.INCIDENT: MARKS, tables.PROBLEM: MARKS, tables.CHANGE: MARKS,
           tables.KB: "short_descriptionSTARTSWITH[SYN]", tables.CI: "short_descriptionSTARTSWITH[SYN]"}


def main() -> int:
    sn = ServiceNowClient.from_env()
    n = 0
    for table, query in QUERIES.items():
        while True:
            page = sn.list(table, query, ["sys_id"], limit=500)
            if not page:
                break
            for rec in page:
                sn.delete(table, rec["sys_id"])
                n += 1
    print(f"deleted {n} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
