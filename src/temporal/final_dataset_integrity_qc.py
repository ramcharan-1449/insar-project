
from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SPATIAL_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_grid_features.csv"
)

QC_FILE = (
    PROJECT_ROOT
    / "config"
    / "insar_temporal_qc.csv"
)

OBS_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_temporal_observations.csv"
)

TEMPORAL_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_temporal_features_qc.csv"
)

REPORT_FILE = (
    PROJECT_ROOT
    / "config"
    / "final_dataset_integrity_report.txt"
)


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("STAGE 16 - FINAL DATASET INTEGRITY & PACKAGING QC")
print("=" * 70)


# ============================================================
# LOAD DATASETS
# ============================================================

spatial = pd.read_csv(SPATIAL_FILE)
qc = pd.read_csv(QC_FILE)
obs = pd.read_csv(OBS_FILE)
temporal = pd.read_csv(TEMPORAL_FILE)

print("\nInput datasets:")
print(f"Spatial features       : {len(spatial)} rows")
print(f"Temporal QC            : {len(qc)} rows")
print(f"Temporal observations  : {len(obs)} rows")
print(f"Temporal summaries     : {len(temporal)} rows")


# ============================================================
# HELPER
# ============================================================

checks = []


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    checks.append((name, status))
    print(f"{status:5} - {name}")
    return condition


# ============================================================
# DISCOVER CURRENT DATASET STRUCTURE
# ============================================================

spatial_cells = set(
    spatial["cell_id"].dropna().unique()
)

qc_cells = set(
    qc["cell_id"].dropna().unique()
)

obs_cells = set(
    obs["cell_id"].dropna().unique()
)

temporal_cells = set(
    temporal["cell_id"].dropna().unique()
)


spatial_products = set(
    spatial["product_id"].dropna().unique()
)

qc_products = set(
    qc["product_id"].dropna().unique()
)

obs_products = set(
    obs["product_id"].dropna().unique()
)


# Products that passed temporal QC
valid_qc_products = set(
    qc.loc[
        qc["temporal_qc_pass"] == True,
        "product_id"
    ].dropna().unique()
)


grid_cell_count = len(spatial_cells)
spatial_product_count = len(spatial_products)
qc_product_count = len(qc_products)
valid_product_count = len(valid_qc_products)
observation_product_count = len(obs_products)


print("\nCurrent dataset structure:")
print(f"Grid cells             : {grid_cell_count}")
print(f"Spatial products       : {spatial_product_count}")
print(f"QC products            : {qc_product_count}")
print(f"QC-valid products      : {valid_product_count}")
print(f"Observation products   : {observation_product_count}")


# ============================================================
# CHECK 1 — BASIC COUNTS
# ============================================================

print("\n" + "=" * 70)
print("BASIC INTEGRITY")
print("=" * 70)


check(
    "At least one spatial grid cell exists",
    grid_cell_count > 0
)

check(
    "Temporal summary has the same grid cells as spatial dataset",
    spatial_cells == temporal_cells
)

check(
    "Spatial and QC cell sets match",
    spatial_cells == qc_cells
)

check(
    "Spatial and observation cell sets match",
    spatial_cells == obs_cells
)

check(
    "Temporal summary cell count matches spatial grid",
    len(temporal_cells) == grid_cell_count
)


# ============================================================
# CHECK 2 — PRODUCT CONSISTENCY
# ============================================================

print("\n" + "=" * 70)
print("PRODUCT INTEGRITY")
print("=" * 70)


check(
    "Spatial and QC product sets match",
    spatial_products == qc_products
)

check(
    "Observation products are exactly QC-valid products",
    obs_products == valid_qc_products
)

check(
    "All observation products are present in QC",
    obs_products.issubset(qc_products)
)


# ============================================================
# CHECK 3 — DUPLICATES
# ============================================================

print("\n" + "=" * 70)
print("DUPLICATE CHECKS")
print("=" * 70)


spatial_duplicates = spatial.duplicated(
    ["cell_id", "product_id"]
).sum()

qc_duplicates = qc.duplicated(
    ["cell_id", "product_id"]
).sum()

obs_duplicates = obs.duplicated(
    ["cell_id", "product_id"]
).sum()


check(
    "No duplicate spatial cell/product records",
    spatial_duplicates == 0
)

check(
    "No duplicate QC cell/product records",
    qc_duplicates == 0
)

check(
    "No duplicate temporal observation cell/product records",
    obs_duplicates == 0
)


# ============================================================
# CHECK 4 — OBSERVATION COUNT
# ============================================================

print("\n" + "=" * 70)
print("OBSERVATION COUNT")
print("=" * 70)


expected_observations = (
    grid_cell_count * valid_product_count
)

print(
    f"Grid cells                  : {grid_cell_count}"
)

print(
    f"QC-valid products           : {valid_product_count}"
)

print(
    f"Expected valid observations: {expected_observations}"
)

print(
    f"Actual valid observations  : {len(obs)}"
)


check(
    "Observation count matches grid cells × valid products",
    len(obs) == expected_observations
)


# ============================================================
# CHECK 5 — EVERY CELL HAS ONE OBSERVATION PER VALID PRODUCT
# ============================================================

print("\n" + "=" * 70)
print("OBSERVATIONS PER GRID CELL")
print("=" * 70)


obs_per_cell = (
    obs.groupby("cell_id")
    .size()
)


if len(obs_per_cell) > 0:

    min_observations = obs_per_cell.min()
    max_observations = obs_per_cell.max()

else:

    min_observations = 0
    max_observations = 0


print(
    f"Minimum observations/cell : {min_observations}"
)

print(
    f"Maximum observations/cell : {max_observations}"
)

print(
    f"Expected per cell         : {valid_product_count}"
)


check(
    "Every grid cell has exactly one observation per valid product",
    (
        len(obs_per_cell) == grid_cell_count
        and min_observations == valid_product_count
        and max_observations == valid_product_count
    )
)


# ============================================================
# CHECK 6 — QC PASS CONSISTENCY
# ============================================================

print("\n" + "=" * 70)
print("QC CONSISTENCY")
print("=" * 70)


check(
    "Every temporal observation belongs to a QC-pass product",
    obs_products.issubset(valid_qc_products)
)


# ============================================================
# CHECK 7 — DATE CONSISTENCY
# ============================================================

print("\n" + "=" * 70)
print("DATE CONSISTENCY")
print("=" * 70)


spatial_dates = spatial[
    [
        "product_id",
        "reference_date",
        "secondary_date",
    ]
].drop_duplicates()


obs_dates = obs[
    [
        "product_id",
        "reference_date",
        "secondary_date",
    ]
].drop_duplicates()


spatial_dates = (
    spatial_dates
    .sort_values(
        [
            "product_id",
            "reference_date",
            "secondary_date",
        ]
    )
    .reset_index(drop=True)
)


obs_dates = (
    obs_dates
    .sort_values(
        [
            "product_id",
            "reference_date",
            "secondary_date",
        ]
    )
    .reset_index(drop=True)
)


spatial_dates["reference_date"] = pd.to_datetime(
    spatial_dates["reference_date"]
)

spatial_dates["secondary_date"] = pd.to_datetime(
    spatial_dates["secondary_date"]
)

obs_dates["reference_date"] = pd.to_datetime(
    obs_dates["reference_date"]
)

obs_dates["secondary_date"] = pd.to_datetime(
    obs_dates["secondary_date"]
)


valid_spatial_dates = (
    spatial_dates[
        spatial_dates["product_id"].isin(obs_products)
    ]
    .reset_index(drop=True)
)


check(
    "Observation dates match spatial dates for valid products",
    valid_spatial_dates.equals(obs_dates)
)


# ============================================================
# CHECK 8 — ORBIT METADATA
# ============================================================

print("\n" + "=" * 70)
print("ORBIT METADATA")
print("=" * 70)


required_metadata = [
    "orbit_direction",
    "relative_orbit",
    "reference_frame",
    "secondary_frame",
]


metadata_complete = all(
    col in obs.columns
    and obs[col].notna().all()
    for col in required_metadata
)


check(
    "Orbit and frame metadata complete",
    metadata_complete
)


# ============================================================
# CHECK 9 — TEMPORAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("TEMPORAL SUMMARY")
print("=" * 70)


summary_counts = temporal[
    "valid_observation_count"
]


check(
    "Temporal summary contains the current grid cells",
    len(temporal) == grid_cell_count
)


if len(summary_counts) > 0:

    summary_min = summary_counts.min()
    summary_max = summary_counts.max()

else:

    summary_min = 0
    summary_max = 0


print(
    f"Minimum summary observations : {summary_min}"
)

print(
    f"Maximum summary observations : {summary_max}"
)

print(
    f"Expected observations/cell   : {valid_product_count}"
)


check(
    "Every temporal summary cell has all valid observations",
    (
        summary_min == valid_product_count
        and summary_max == valid_product_count
    )
)


check(
    "Temporal summary uses current valid product count",
    (
        temporal[
            "total_valid_products_available"
        ]
        .eq(valid_product_count)
        .all()
    )
)


# ============================================================
# CHECK 10 — FINAL PRODUCT/CELL MATRIX
# ============================================================

print("\n" + "=" * 70)
print("FINAL PRODUCT-CELL MATRIX")
print("=" * 70)


expected_spatial_records = (
    grid_cell_count * spatial_product_count
)

expected_qc_records = (
    grid_cell_count * qc_product_count
)


print(
    f"Expected spatial records : {expected_spatial_records}"
)

print(
    f"Actual spatial records   : {len(spatial)}"
)

print(
    f"Expected QC records      : {expected_qc_records}"
)

print(
    f"Actual QC records        : {len(qc)}"
)


check(
    "Spatial records match grid cells × spatial products",
    len(spatial) == expected_spatial_records
)

check(
    "QC records match grid cells × QC products",
    len(qc) == expected_qc_records
)


# ============================================================
# FINAL STATUS
# ============================================================

failed_checks = [
    name
    for name, status in checks
    if status == "FAIL"
]


print("\n" + "=" * 70)
print("STAGE 16 FINAL RESULT")
print("=" * 70)


if failed_checks:

    final_status = "FAIL"

    print("FINAL STATUS : FAIL")

    print("\nFailed checks:")

    for item in failed_checks:
        print(f"  - {item}")

else:

    final_status = "PASS"

    print("FINAL STATUS : PASS")

    print(
        "\nAll final dataset integrity checks passed."
    )


# ============================================================
# WRITE REPORT
# ============================================================

report_lines = [
    "STAGE 16 - FINAL DATASET INTEGRITY & PACKAGING QC",
    "=" * 60,
    "",
    f"Spatial records          : {len(spatial)}",
    f"QC records               : {len(qc)}",
    f"Valid observations       : {len(obs)}",
    f"Temporal summary cells   : {len(temporal)}",
    "",
    f"Grid cells               : {grid_cell_count}",
    f"Spatial products         : {spatial_product_count}",
    f"QC products              : {qc_product_count}",
    f"QC-valid products        : {valid_product_count}",
    f"Observation products     : {observation_product_count}",
    "",
    f"Expected observations    : {expected_observations}",
    f"Actual observations      : {len(obs)}",
    "",
    f"Final status             : {final_status}",
    "",
    "CHECK RESULTS",
    "-" * 60,
]


for name, status in checks:

    report_lines.append(
        f"{status:5} - {name}"
    )


if failed_checks:

    report_lines.extend(
        [
            "",
            "FAILED CHECKS",
            "-" * 60,
        ]
    )

    report_lines.extend(
        f"- {item}"
        for item in failed_checks
    )


REPORT_FILE.write_text(
    "\n".join(report_lines),
    encoding="utf-8"
)


print("\nReport:")
print(REPORT_FILE)

print("\nStage 16 completed.")

