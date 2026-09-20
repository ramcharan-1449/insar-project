"""Validate the node_id-to-cell_id contract consumed by GNN and GP pipelines."""

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAPPING_FILE = PROJECT_ROOT / "config" / "node_cell_mapping.csv"
REQUIRED_COLUMNS = {
    "node_id", "cell_id", "assignment_method", "assignment_crs",
    "source", "review_status", "reviewed_by", "reviewed_at",
}


def main() -> None:
    if not MAPPING_FILE.exists():
        raise FileNotFoundError(
            "Missing config/node_cell_mapping.csv. Copy "
            "config/node_cell_mapping.template.csv and complete the joint InSAR/ML review."
        )
    with MAPPING_FILE.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
        columns = set(rows[0]) if rows else set()
    missing = REQUIRED_COLUMNS - columns
    if missing or not rows:
        raise ValueError(f"Invalid node/cell mapping; missing columns or rows: {sorted(missing)}")
    if any(not row["node_id"] or not row["cell_id"] for row in rows):
        raise ValueError("Every mapping row requires node_id and cell_id.")
    if len({row["node_id"] for row in rows}) != len(rows):
        raise ValueError("node_id values must be unique.")
    if any(row["review_status"].upper() != "APPROVED" for row in rows):
        raise ValueError("All mapping rows must be APPROVED before downstream use.")
    print(f"NODE/CELL MAPPING: PASS ({len(rows)} approved nodes)")


if __name__ == "__main__":
    main()
