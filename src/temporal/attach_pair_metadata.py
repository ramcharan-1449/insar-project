from pathlib import Path
import re

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SPATIAL_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_spatial_features.csv"
)

PAIR_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_final_pairs_geometry_validated.csv"
)

EXTRACTED_ROOT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hyp3"
    / "extracted"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_temporal_spatial_features.csv"
)


# ============================================================
# EXPECTED PRODUCTS
# ============================================================

EXPECTED_PRODUCTS = [
    "P04",
    "P05",
    "P06",
    "P07",
    "P08",
    "P09",
    "P10",
    "P11",
    "P12",
]


# ============================================================
# START
# ============================================================

print("=" * 70)
print("STAGE 11 - TEMPORAL METADATA ATTACHMENT")
print("=" * 70)
print()


# ============================================================
# LOAD SPATIAL FEATURES
# ============================================================

if not SPATIAL_FILE.exists():
    print(
        f"ERROR: Spatial file not found:\n"
        f"{SPATIAL_FILE}"
    )
    raise SystemExit(1)

spatial = pd.read_csv(SPATIAL_FILE)

print(f"Spatial records loaded: {len(spatial)}")


if "product_id" not in spatial.columns:
    print(
        "ERROR: Spatial data does not contain "
        "'product_id'."
    )
    raise SystemExit(1)

spatial_products = sorted(
    spatial["product_id"]
    .dropna()
    .astype(str)
    .unique()
)

print(f"Spatial products found: {len(spatial_products)}")

for product in spatial_products:
    print(f"  {product}")

print()


# ============================================================
# LOAD PAIR METADATA
# ============================================================

if not PAIR_FILE.exists():
    print(
        f"ERROR: Pair metadata file not found:\n"
        f"{PAIR_FILE}"
    )
    raise SystemExit(1)

pairs = pd.read_csv(PAIR_FILE)

print(f"Pair records loaded: {len(pairs)}")
print()


# ============================================================
# DISPLAY PAIR COLUMNS
# ============================================================

print("Pair metadata columns:")

for column in pairs.columns:
    print(f"  {column}")

print()


# ============================================================
# FIND REQUIRED COLUMNS
# ============================================================

def find_column(dataframe, candidates):
    for column in candidates:
        if column in dataframe.columns:
            return column

    return None


ref_date_column = find_column(
    pairs,
    [
        "reference_date",
        "ref_date",
        "acquisition_date_ref",
    ],
)

sec_date_column = find_column(
    pairs,
    [
        "secondary_date",
        "sec_date",
        "acquisition_date_sec",
    ],
)

orbit_column = find_column(
    pairs,
    [
        "orbit_direction",
        "direction",
    ],
)

relative_orbit_column = find_column(
    pairs,
    [
        "relative_orbit",
        "relative_orbit_number",
    ],
)

frame_column = find_column(
    pairs,
    [
        "frame",
        "frame_number",
    ],
)


# ============================================================
# DISPLAY DETECTED MAPPING
# ============================================================

print("Detected pair metadata mapping:")

print(f"Reference date  : {ref_date_column}")
print(f"Secondary date  : {sec_date_column}")
print(f"Orbit direction : {orbit_column}")
print(f"Relative orbit  : {relative_orbit_column}")
print(f"Frame           : {frame_column}")

print()


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

if (
    ref_date_column is None
    or sec_date_column is None
    or orbit_column is None
    or relative_orbit_column is None
):
    print(
        "ERROR: Required pair metadata columns "
        "could not be identified."
    )
    raise SystemExit(1)


# ============================================================
# NORMALIZE PAIR METADATA
# ============================================================

metadata = pairs.copy()

metadata["reference_date"] = pd.to_datetime(
    metadata[ref_date_column],
    errors="coerce",
).dt.normalize()

metadata["secondary_date"] = pd.to_datetime(
    metadata[sec_date_column],
    errors="coerce",
).dt.normalize()

# IMPORTANT:
# Calculate temporal baseline directly from acquisition dates.
metadata["temporal_baseline_days"] = (
    metadata["secondary_date"]
    - metadata["reference_date"]
).dt.days

metadata["orbit_direction"] = (
    metadata[orbit_column]
    .astype(str)
    .str.upper()
    .str.strip()
)

metadata["relative_orbit"] = pd.to_numeric(
    metadata[relative_orbit_column],
    errors="coerce",
)

if frame_column is not None:
    metadata["frame"] = pd.to_numeric(
        metadata[frame_column],
        errors="coerce",
    )
else:
    metadata["frame"] = pd.NA


# ============================================================
# VALIDATE DATES
# ============================================================

invalid_dates = (
    metadata["reference_date"].isna()
    | metadata["secondary_date"].isna()
).sum()

print(f"Invalid date records: {invalid_dates}")

if invalid_dates > 0:
    print("ERROR: Invalid acquisition dates.")
    raise SystemExit(1)


# ============================================================
# VALIDATE BASELINES
# ============================================================

invalid_baselines = (
    metadata["temporal_baseline_days"] <= 0
).sum()

print(f"Invalid temporal baselines: {invalid_baselines}")

if invalid_baselines > 0:
    print(
        "ERROR: One or more temporal baselines "
        "are zero or negative."
    )
    raise SystemExit(1)


# ============================================================
# IDENTIFY PRODUCTS FROM HYP3 FILES
# ============================================================

print()
print("=" * 70)
print("IDENTIFYING PRODUCTS FROM HYP3 PRODUCT FILES")
print("=" * 70)
print()

if not EXTRACTED_ROOT.exists():
    print(
        f"ERROR: HyP3 extraction directory not found:\n"
        f"{EXTRACTED_ROOT}"
    )
    raise SystemExit(1)


product_date_map = {}


# Example filename:
#
# S1AA_20240627T121314_20240709T121313_VVP012...
#
# Captures:
# 20240627
# 20240709

date_pattern = re.compile(
    r"_(\d{8})T\d{6}_(\d{8})T\d{6}_"
)


for product_id in EXPECTED_PRODUCTS:

    product_folder = EXTRACTED_ROOT / product_id

    if not product_folder.exists():
        print(
            f"ERROR: Product folder not found: "
            f"{product_id}"
        )
        raise SystemExit(1)

    detected_pairs = set()

    for tif_file in product_folder.rglob("*.tif"):

        filename = tif_file.name

        match = date_pattern.search(filename)

        if match:

            ref_date = pd.to_datetime(
                match.group(1),
                format="%Y%m%d",
            )

            sec_date = pd.to_datetime(
                match.group(2),
                format="%Y%m%d",
            )

            detected_pairs.add(
                (
                    ref_date.strftime("%Y-%m-%d"),
                    sec_date.strftime("%Y-%m-%d"),
                )
            )

    if len(detected_pairs) == 0:
        print(
            f"ERROR: Could not identify acquisition "
            f"dates for {product_id}"
        )
        raise SystemExit(1)

    if len(detected_pairs) > 1:

        print(
            f"ERROR: Multiple acquisition pairs "
            f"detected for {product_id}:"
        )

        for pair in sorted(detected_pairs):
            print(
                f"  {pair[0]} -> {pair[1]}"
            )

        raise SystemExit(1)

    pair = next(iter(detected_pairs))

    product_date_map[product_id] = pair

    print(
        f"{product_id}: "
        f"{pair[0]} -> {pair[1]}"
    )

print()


# ============================================================
# MATCH PRODUCTS TO PAIR METADATA
# ============================================================

print("=" * 70)
print("MATCHING PRODUCTS TO PAIR METADATA")
print("=" * 70)
print()

matched_rows = []

for product_id, date_pair in product_date_map.items():

    ref_date_string = date_pair[0]
    sec_date_string = date_pair[1]

    matches = metadata[
        (
            metadata["reference_date"]
            .dt.strftime("%Y-%m-%d")
            == ref_date_string
        )
        &
        (
            metadata["secondary_date"]
            .dt.strftime("%Y-%m-%d")
            == sec_date_string
        )
    ]

    if len(matches) == 0:
        print(
            f"ERROR: No pair metadata found for "
            f"{product_id}: "
            f"{ref_date_string} -> "
            f"{sec_date_string}"
        )
        raise SystemExit(1)

    if len(matches) > 1:
        print(
            f"ERROR: Multiple pair metadata records "
            f"found for {product_id}:"
        )

        print(
            matches.to_string(index=False)
        )

        raise SystemExit(1)

    row = matches.iloc[0].copy()

    row["product_id"] = product_id

    matched_rows.append(row)

    print(
        f"{product_id} matched successfully: "
        f"{ref_date_string} -> "
        f"{sec_date_string}"
    )

print()


# ============================================================
# CREATE PRODUCT METADATA TABLE
# ============================================================

metadata = pd.DataFrame(matched_rows)

metadata_columns = [
    "product_id",
    "reference_date",
    "secondary_date",
    "temporal_baseline_days",
    "orbit_direction",
    "relative_orbit",
    "frame",
]

metadata = metadata[
    metadata_columns
].copy()


# ============================================================
# CHECK EXPECTED PRODUCTS
# ============================================================

metadata_products = sorted(
    metadata["product_id"]
    .astype(str)
    .unique()
)

missing_products = [
    product
    for product in EXPECTED_PRODUCTS
    if product not in metadata_products
]

if missing_products:

    print("ERROR: Missing expected products:")

    for product in missing_products:
        print(f"  {product}")

    raise SystemExit(1)


if len(metadata) != len(EXPECTED_PRODUCTS):

    print(
        "ERROR: Expected exactly one metadata "
        "record per product."
    )

    print(
        f"Metadata records: {len(metadata)}"
    )

    raise SystemExit(1)


# ============================================================
# BASELINE VERIFICATION
# ============================================================

print("=" * 70)
print("BASELINE VERIFICATION")
print("=" * 70)
print()

for _, row in metadata.iterrows():

    calculated_baseline = (
        row["secondary_date"]
        - row["reference_date"]
    ).days

    stored_baseline = int(
        row["temporal_baseline_days"]
    )

    print(
        f"{row['product_id']}: "
        f"{row['reference_date'].strftime('%Y-%m-%d')} "
        f"-> "
        f"{row['secondary_date'].strftime('%Y-%m-%d')} | "
        f"baseline = {stored_baseline} days | "
        f"calculated = {calculated_baseline} days"
    )

    if stored_baseline != calculated_baseline:

        print(
            "ERROR: Baseline mismatch detected."
        )

        raise SystemExit(1)

print()


# ============================================================
# MERGE WITH SPATIAL FEATURES
# ============================================================

merged = spatial.merge(
    metadata,
    on="product_id",
    how="left",
    validate="many_to_one",
)


missing_metadata_rows = (
    merged["reference_date"].isna()
).sum()

print(f"Rows after merge: {len(merged)}")

print(
    f"Rows without temporal metadata: "
    f"{missing_metadata_rows}"
)

if missing_metadata_rows > 0:

    print(
        "ERROR: Some spatial observations "
        "could not be matched to pair metadata."
    )

    raise SystemExit(1)


# ============================================================
# FORMAT DATES
# ============================================================

merged["reference_date"] = (
    merged["reference_date"]
    .dt.strftime("%Y-%m-%d")
)

merged["secondary_date"] = (
    merged["secondary_date"]
    .dt.strftime("%Y-%m-%d")
)


# ============================================================
# COLUMN ORDER
# ============================================================

preferred_order = [
    "cell_id",
    "product_id",

    "reference_date",
    "secondary_date",
    "temporal_baseline_days",

    "orbit_direction",
    "relative_orbit",
    "frame",

    "los_displacement_mean_mm",
    "los_displacement_median_mm",
    "los_displacement_std_mm",

    "coherence_mean",
    "coherence_median",

    "unwrapped_phase_mean",
    "unwrapped_phase_median",

    "valid_pixel_count",
    "total_pixel_count",
    "valid_pixel_percent",

    "qc_status",
]

existing_columns = [
    column
    for column in preferred_order
    if column in merged.columns
]

remaining_columns = [
    column
    for column in merged.columns
    if column not in existing_columns
]

merged = merged[
    existing_columns + remaining_columns
]


# ============================================================
# SAVE
# ============================================================

merged.to_csv(
    OUTPUT_FILE,
    index=False,
)


# ============================================================
# PRODUCT SUMMARY
# ============================================================

print()
print("=" * 70)
print("TEMPORAL METADATA SUMMARY")
print("=" * 70)
print()

summary = (
    merged[
        [
            "product_id",
            "reference_date",
            "secondary_date",
            "temporal_baseline_days",
            "orbit_direction",
            "relative_orbit",
            "frame",
        ]
    ]
    .drop_duplicates()
    .sort_values("reference_date")
)

print(
    summary.to_string(index=False)
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("=" * 70)
print("STAGE 11 SUMMARY")
print("=" * 70)

print(
    f"Spatial records : {len(spatial)}"
)

print(
    f"Final records   : {len(merged)}"
)

print(
    f"Products        : "
    f"{merged['product_id'].nunique()}"
)

print(
    f"Grid cells      : "
    f"{merged['cell_id'].nunique()}"
)

print(
    f"Missing metadata: "
    f"{missing_metadata_rows}"
)

print()
print("Output:")
print(OUTPUT_FILE)

print()
print(
    "Stage 11 temporal metadata attachment complete."
)