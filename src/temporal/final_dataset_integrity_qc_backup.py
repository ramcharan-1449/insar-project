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
# LOAD
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
# CHECK 1 — BASIC COUNTS
# ============================================================

spatial_cells = set(spatial["cell_id"].unique())
qc_cells = set(qc["cell_id"].unique())
obs_cells = set(obs["cell_id"].unique())
temporal_cells = set(temporal["cell_id"].unique())

spatial_products = set(spatial["product_id"].unique())
qc_products = set(qc["product_id"].unique())
obs_products = set(obs["product_id"].unique())

checks = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    checks.append((name, status))
    print(f"{status:5} - {name}")
    return condition


print("\n" + "=" * 70)
print("BASIC INTEGRITY")
print("=" * 70)

check(
    "Spatial dataset has 293 grid cells",
    len(spatial_cells) == 293
)

check(
    "Temporal summary has 293 grid cells",
    len(temporal_cells) == 293
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
    "Spatial and temporal-summary cell sets match",
    spatial_cells == temporal_cells
)


# ============================================================
# CHECK 2 — PRODUCT CONSISTENCY
# ============================================================

print("\n" + "=" * 70)
print("PRODUCT INTEGRITY")
print("=" * 70)

check(
    "Spatial dataset contains 31 products",
    len(spatial_products) == 31
)

check(
    "QC dataset contains 31 products",
    len(qc_products) == 31
)

check(
    "Valid observation dataset contains 30 products",
    len(obs_products) == 30
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

expected_observations = 293 * 30

print(
    f"Expected valid observations : {expected_observations}"
)

print(
    f"Actual valid observations   : {len(obs)}"
)

check(
    "293 cells × 30 valid products = 8790 observations",
    len(obs) == expected_observations
)


# ============================================================
# CHECK 5 — EVERY CELL HAS 30 OBSERVATIONS
# ============================================================

obs_per_cell = obs.groupby("cell_id").size()

check(
    "Every grid cell has exactly 30 observations",
    (
        len(obs_per_cell) == 293
        and obs_per_cell.min() == 30
        and obs_per_cell.max() == 30
    )
)


# ============================================================
# CHECK 6 — P006 EXCLUSION
# ============================================================

print("\n" + "=" * 70)
print("P006 EXCLUSION CHECK")
print("=" * 70)

p006_in_obs = (
    "P006" in set(obs["product_id"].unique())
)

p006_qc = qc[
    qc["product_id"] == "P006"
]

p006_invalid = (
    len(p006_qc) == 293
    and
    (p006_qc["qc_status"] == "INVALID").all()
)

print(f"P006 present in valid observations : {p006_in_obs}")
print(f"P006 has 293 invalid QC records    : {p006_invalid}")

check(
    "P006 is excluded from valid observations",
    not p006_in_obs
)

check(
    "P006 contains 293 INVALID QC records",
    p006_invalid
)


# ============================================================
# CHECK 7 — QC PASS CONSISTENCY
# ============================================================

print("\n" + "=" * 70)
print("QC CONSISTENCY")
print("=" * 70)

valid_qc_products = set(
    qc.loc[
        qc["temporal_qc_pass"] == True,
        "product_id"
    ].unique()
)

check(
    "Every temporal observation belongs to a QC-pass product",
    obs_products.issubset(valid_qc_products)
)


# ============================================================
# CHECK 8 — DATE CONSISTENCY
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

spatial_dates = spatial_dates.sort_values(
    ["product_id", "reference_date", "secondary_date"]
).reset_index(drop=True)

obs_dates = obs_dates.sort_values(
    ["product_id", "reference_date", "secondary_date"]
).reset_index(drop=True)

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

valid_spatial_dates = spatial_dates[
    spatial_dates["product_id"].isin(obs_products)
].reset_index(drop=True)

check(
    "Observation dates match spatial dates for valid products",
    valid_spatial_dates.equals(obs_dates)
)


# ============================================================
# CHECK 9 — ORBIT METADATA
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
# CHECK 10 — TEMPORAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("TEMPORAL SUMMARY")
print("=" * 70)

summary_counts = temporal[
    "valid_observation_count"
]

check(
    "Temporal summary contains exactly 293 cells",
    len(temporal) == 293
)

check(
    "Every temporal summary cell has 30 observations",
    (
        summary_counts.min() == 30
        and summary_counts.max() == 30
    )
)

check(
    "Temporal summary uses 30 valid products",
    (
        temporal["total_valid_products_available"]
        .eq(30)
        .all()
    )
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

print(f"\nReport:")
print(REPORT_FILE)

print("\nStage 16 completed.")
