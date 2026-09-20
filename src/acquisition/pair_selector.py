from pathlib import Path
from datetime import datetime, timezone
import json
import math
import time

import pandas as pd
import asf_search as asf
from shapely.geometry import shape


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_DIR = PROJECT_ROOT / "config"

INVENTORY_FILE = (
    CONFIG_DIR / "sentinel1_scene_inventory_auto.csv"
)

CANDIDATE_OUTPUT = (
    CONFIG_DIR / "sentinel1_candidate_pairs_scientific.csv"
)

RANKED_OUTPUT = (
    CONFIG_DIR / "sentinel1_ranked_pairs_scientific.csv"
)

PRIORITY_OUTPUT = (
    CONFIG_DIR / "sentinel1_priority_pairs_scientific.csv"
)

# Existing validated pairs
FINAL_PAIRS_FILE = (
    CONFIG_DIR / "sentinel1_final_pairs_geometry_validated.csv"
)

# Existing HyP3 jobs
HYP3_REGISTRY_FILE = (
    CONFIG_DIR / "hyp3_job_registry.csv"
)

AOI_CONFIG = (
    CONFIG_DIR / "aoi_config.json"
)

# ------------------------------------------------------------
# Temporal constraint
# ------------------------------------------------------------

MAX_TEMPORAL_DAYS = 24

# ------------------------------------------------------------
# Perpendicular baseline thresholds
# ------------------------------------------------------------

GOOD_PERP_M = 200
ACCEPTABLE_PERP_M = 500

# ------------------------------------------------------------
# Maximum new priority pairs per orbit track
# ------------------------------------------------------------

PAIRS_PER_TRACK = 3


# ============================================================
# ASF BASELINE RETRY
# ============================================================

def get_stack_with_retry(reference, max_attempts=5):
    """
    Query ASF/CMR for stack information.

    Temporary network/DNS failures are retried automatically.
    """

    for attempt in range(1, max_attempts + 1):

        try:
            return reference.stack()

        except Exception as e:

            print(
                f"    Baseline query failed "
                f"(attempt {attempt}/{max_attempts}): {e}"
            )

            if attempt < max_attempts:

                wait_seconds = 2 ** attempt

                print(
                    f"    Retrying in "
                    f"{wait_seconds} seconds..."
                )

                time.sleep(wait_seconds)

    return None


# ============================================================
# DATE PARSER
# ============================================================

def parse_datetime(value):
    """
    Convert inventory date/time into Python datetime.
    """

    if pd.isna(value):
        return None

    value = str(value).strip()

    # ISO format
    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    except ValueError:
        pass

    # Other possible formats
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:

        try:
            return datetime.strptime(
                value,
                fmt
            )

        except ValueError:
            continue

    return None


# ============================================================
# SCENE NAME
# ============================================================

def get_scene_name(row):
    """
    Get Sentinel-1 scene name from inventory.
    """

    for column in [
        "scene_id",
        "scene_name",
        "granule",
        "product_name"
    ]:

        if column in row and pd.notna(row[column]):

            return str(
                row[column]
            ).strip()

    return None


# ============================================================
# ACQUISITION DATE
# ============================================================

def extract_date(row):
    """
    Extract acquisition datetime from inventory.
    """

    for column in [
        "acquisition_date",
        "acquisition_datetime",
        "start_time",
        "scene_date"
    ]:

        if column in row and pd.notna(row[column]):

            dt = parse_datetime(
                row[column]
            )

            if dt is not None:
                return dt

    # --------------------------------------------------------
    # Last-resort extraction from Sentinel-1 scene name
    # --------------------------------------------------------

    scene = get_scene_name(row)

    if scene:

        parts = scene.split("_")

        for part in parts:

            if "T" in part and len(part) >= 15:

                try:

                    return datetime.strptime(
                        part[:15],
                        "%Y%m%dT%H%M%S"
                    )

                except ValueError:
                    continue

    return None


# ============================================================
# LOAD AOI
# ============================================================

def load_aoi_wkt():
    """
    Load AOI and convert it to WKT.
    """

    with open(
        AOI_CONFIG,
        "r",
        encoding="utf-8"
    ) as f:

        config = json.load(f)

    # Support multiple possible config structures

    geojson_path = None

    if "geojson" in config:

        geojson_path = config["geojson"]

    elif "aoi_geojson" in config:

        geojson_path = config["aoi_geojson"]

    elif "aoi_file" in config:

        geojson_path = config["aoi_file"]

    # Default AOI

    if geojson_path is None:

        geojson_path = (
            CONFIG_DIR / "mine_aoi.geojson"
        )

    else:

        geojson_path = Path(
            geojson_path
        )

        if not geojson_path.is_absolute():

            geojson_path = (
                PROJECT_ROOT / geojson_path
            )

    with open(
        geojson_path,
        "r",
        encoding="utf-8"
    ) as f:

        aoi = json.load(f)

    geometry = shape(
        aoi["features"][0]["geometry"]
    )

    return geometry.wkt


# ============================================================
# BASELINE VALUE
# ============================================================

def baseline_value(product, key):
    """
    Safely extract baseline information
    from an ASF product.
    """

    # Direct properties

    if hasattr(
        product,
        "properties"
    ):

        props = (
            product.properties or {}
        )

        if key in props:

            return props[key]

    # Baseline dictionary

    if hasattr(
        product,
        "baseline"
    ):

        baseline = product.baseline

        if isinstance(
            baseline,
            dict
        ):

            if key in baseline:

                return baseline[key]

    return None


# ============================================================
# NUMERIC CONVERSION
# ============================================================

def numeric(value):
    """
    Convert value to float when possible.
    """

    if value is None:

        return None

    try:

        value = float(value)

        if math.isfinite(value):

            return value

    except (
        TypeError,
        ValueError
    ):

        pass

    return None


# ============================================================
# LOAD EXISTING PAIRS
# ============================================================

def load_existing_pair_keys():
    """
    Load acquisition pairs that have already been:

    1. Geometry validated
    2. Registered with HyP3

    These pairs will NOT be selected again.
    """

    existing = set()

    # ========================================================
    # Existing validated pairs
    # ========================================================

    if FINAL_PAIRS_FILE.exists():

        print(
            "\nLoading existing validated pairs..."
        )

        try:

            df = pd.read_csv(
                FINAL_PAIRS_FILE
            )

            required = {
                "reference_scene",
                "secondary_scene"
            }

            if required.issubset(
                df.columns
            ):

                for _, row in df.iterrows():

                    ref = str(
                        row["reference_scene"]
                    ).strip()

                    sec = str(
                        row["secondary_scene"]
                    ).strip()

                    if (
                        ref
                        and sec
                        and ref.lower() != "nan"
                        and sec.lower() != "nan"
                    ):

                        existing.add(
                            (
                                ref,
                                sec
                            )
                        )

        except Exception as e:

            print(
                "WARNING: Could not read "
                f"{FINAL_PAIRS_FILE}: {e}"
            )

    # ========================================================
    # Existing HyP3 registry
    # ========================================================

    if HYP3_REGISTRY_FILE.exists():

        print(
            "Loading existing HyP3 registry..."
        )

        try:

            df = pd.read_csv(
                HYP3_REGISTRY_FILE
            )

            required = {
                "reference_scene",
                "secondary_scene"
            }

            if required.issubset(
                df.columns
            ):

                for _, row in df.iterrows():

                    ref = str(
                        row["reference_scene"]
                    ).strip()

                    sec = str(
                        row["secondary_scene"]
                    ).strip()

                    if (
                        ref
                        and sec
                        and ref.lower() != "nan"
                        and sec.lower() != "nan"
                    ):

                        existing.add(
                            (
                                ref,
                                sec
                            )
                        )

        except Exception as e:

            print(
                "WARNING: Could not read "
                f"{HYP3_REGISTRY_FILE}: {e}"
            )

    return existing


# ============================================================
# LOAD INVENTORY
# ============================================================

print("=" * 70)
print("STAGE 2 — SCIENTIFIC SENTINEL-1 PAIR SELECTION")
print("=" * 70)

if not INVENTORY_FILE.exists():

    raise FileNotFoundError(
        f"Inventory not found: "
        f"{INVENTORY_FILE}"
    )


inventory = pd.read_csv(
    INVENTORY_FILE
)

print(
    f"\nInventory scenes: "
    f"{len(inventory)}"
)


# ============================================================
# NORMALIZE SCENE NAMES
# ============================================================

inventory["scene_id"] = inventory.apply(
    get_scene_name,
    axis=1
)

inventory["acquisition_dt"] = inventory.apply(
    extract_date,
    axis=1
)


inventory = inventory[
    inventory["scene_id"].notna()
    &
    inventory["acquisition_dt"].notna()
].copy()


inventory = inventory.drop_duplicates(
    subset=["scene_id"]
)


print(
    f"Usable scenes: "
    f"{len(inventory)}"
)


# ============================================================
# SEARCH ASF
# ============================================================

print(
    "\nSearching ASF for current scene metadata..."
)

aoi_wkt = load_aoi_wkt()

scene_objects = {}

# Dynamic current UTC date

end_date = datetime.now(
    timezone.utc
).strftime(
    "%Y-%m-%d"
)


try:

    results = asf.search(
        platform=asf.PLATFORM.SENTINEL1,
        processingLevel=asf.PRODUCT_TYPE.SLC,
        intersectsWith=aoi_wkt,
        beamMode=asf.BEAMMODE.IW,
        start="2024-01-01",
        end=end_date,
        maxResults=5000,
    )

except Exception as e:

    raise RuntimeError(
        f"ASF search failed: {e}"
    )


# ============================================================
# BUILD ASF SCENE MAP
# ============================================================

for product in results:

    scene_name = getattr(
        product,
        "sceneName",
        None
    )

    if (
        scene_name is None
        and hasattr(product, "properties")
    ):

        scene_name = (
            product.properties
            .get("sceneName")
        )

    if scene_name:

        scene_objects[
            str(scene_name)
        ] = product


print(
    f"ASF scene objects retrieved: "
    f"{len(scene_objects)}"
)


# ============================================================
# MATCH INVENTORY TO ASF
# ============================================================

inventory["asf_found"] = (
    inventory["scene_id"].isin(
        scene_objects
    )
)


matched = inventory[
    inventory["asf_found"]
].copy()


print(
    f"Inventory scenes matched to ASF: "
    f"{len(matched)}"
)


if len(matched) == 0:

    raise RuntimeError(
        "No inventory scenes could be "
        "matched to ASF products."
    )


# ============================================================
# GET INVENTORY VALUES
# ============================================================

def get_value(
    row,
    possible_columns
):

    for column in possible_columns:

        if (
            column in row
            and pd.notna(row[column])
        ):

            return row[column]

    return None


matched["orbit_direction"] = matched.apply(
    lambda r: get_value(
        r,
        [
            "orbit_direction",
            "flight_direction",
            "direction"
        ]
    ),
    axis=1
)


matched["relative_orbit"] = matched.apply(
    lambda r: get_value(
        r,
        [
            "relative_orbit",
            "relativeOrbit"
        ]
    ),
    axis=1
)


matched["frame"] = matched.apply(
    lambda r: get_value(
        r,
        [
            "frame",
            "frame_number"
        ]
    ),
    axis=1
)


matched["orbit_direction"] = (
    matched["orbit_direction"]
    .astype(str)
    .str.upper()
)


matched["relative_orbit"] = (
    matched["relative_orbit"]
    .astype(str)
)


# ============================================================
# CREATE CANDIDATE PAIRS
# ============================================================

candidate_rows = []

groups = matched.groupby(
    [
        "orbit_direction",
        "relative_orbit"
    ],
    dropna=False
)


print(
    "\nGenerating candidate pairs..."
)


for (
    direction,
    relative_orbit
), group in groups:

    group = group.sort_values(
        "acquisition_dt"
    ).reset_index(
        drop=True
    )

    products = []

    for _, row in group.iterrows():

        scene_name = row["scene_id"]

        if scene_name not in scene_objects:

            continue

        products.append(
            (
                row,
                scene_objects[scene_name]
            )
        )

    if len(products) < 2:

        continue

    # ========================================================
    # Every scene becomes a reference
    # ========================================================

    for i, (
        ref_row,
        reference
    ) in enumerate(products):

        baseline_stack = (
            get_stack_with_retry(
                reference,
                max_attempts=5
            )
        )

        if baseline_stack is None:

            print(
                "WARNING: baseline stack "
                "unavailable after retries "
                f"for {ref_row['scene_id']}"
            )

            continue

        # ----------------------------------------------------
        # Map stack products by scene name
        # ----------------------------------------------------

        stack_map = {}

        for product in baseline_stack:

            name = getattr(
                product,
                "sceneName",
                None
            )

            if (
                name is None
                and hasattr(
                    product,
                    "properties"
                )
            ):

                name = (
                    product.properties
                    .get("sceneName")
                )

            if name:

                stack_map[
                    str(name)
                ] = product

        # ====================================================
        # Generate secondaries
        # ====================================================

        for j in range(
            i + 1,
            len(products)
        ):

            sec_row, secondary = (
                products[j]
            )

            temporal_days = (
                sec_row["acquisition_dt"]
                -
                ref_row["acquisition_dt"]
            ).total_seconds() / 86400.0

            if temporal_days <= 0:

                continue

            if temporal_days > MAX_TEMPORAL_DAYS:

                break

            secondary_name = (
                sec_row["scene_id"]
            )

            stacked_secondary = (
                stack_map.get(
                    secondary_name
                )
            )

            if stacked_secondary is None:

                continue

            # =================================================
            # Baseline metadata
            # =================================================

            perp = baseline_value(
                stacked_secondary,
                "perpendicularBaseline"
            )

            temp = baseline_value(
                stacked_secondary,
                "temporalBaseline"
            )

            # Alternate names

            if perp is None:

                perp = baseline_value(
                    stacked_secondary,
                    "perpendicular_baseline"
                )

            if temp is None:

                temp = baseline_value(
                    stacked_secondary,
                    "temporal_baseline"
                )

            perp = numeric(perp)
            temp = numeric(temp)

            # Use independently calculated temporal baseline
            # if ASF does not provide it.

            if temp is None:

                temp = temporal_days

            # =================================================
            # CLASSIFICATION
            # =================================================

            if perp is None:

                quality = (
                    "UNKNOWN_BASELINE"
                )

                score = float("inf")

            else:

                abs_perp = abs(perp)

                if abs_perp <= GOOD_PERP_M:

                    quality = "GOOD"

                elif abs_perp <= ACCEPTABLE_PERP_M:

                    quality = "ACCEPTABLE"

                else:

                    quality = "LOW_PRIORITY"

                # Lower score is better

                score = (
                    abs_perp
                    +
                    abs(temp) * 5
                )

            candidate_rows.append(
                {
                    "reference_scene":
                        ref_row["scene_id"],

                    "secondary_scene":
                        secondary_name,

                    "reference_date":
                        ref_row[
                            "acquisition_dt"
                        ].isoformat(),

                    "secondary_date":
                        sec_row[
                            "acquisition_dt"
                        ].isoformat(),

                    "temporal_baseline_days":
                        round(
                            float(temp),
                            3
                        ),

                    "perpendicular_baseline_m":
                        (
                            None
                            if perp is None
                            else round(
                                float(perp),
                                3
                            )
                        ),

                    "orbit_direction":
                        direction,

                    "relative_orbit":
                        relative_orbit,

                    "reference_frame":
                        ref_row["frame"],

                    "secondary_frame":
                        sec_row["frame"],

                    "baseline_score":
                        (
                            round(
                                score,
                                3
                            )
                            if math.isfinite(score)
                            else None
                        ),

                    "quality":
                        quality,

                    "selection_status":
                        "CANDIDATE",
                }
            )


# ============================================================
# BUILD DATAFRAME
# ============================================================

pairs = pd.DataFrame(
    candidate_rows
)


if pairs.empty:

    raise RuntimeError(
        "No scientific candidate pairs were produced."
    )


# ============================================================
# REMOVE DUPLICATES
# ============================================================

pairs = pairs.drop_duplicates(
    subset=[
        "reference_scene",
        "secondary_scene"
    ]
).copy()


print(
    f"\nAll scientific candidate pairs: "
    f"{len(pairs)}"
)


# ============================================================
# LOAD EXISTING PAIRS
# ============================================================

existing_pair_keys = (
    load_existing_pair_keys()
)


print(
    f"Existing validated/registered pairs: "
    f"{len(existing_pair_keys)}"
)


# ============================================================
# REMOVE EXISTING PAIRS
# ============================================================

pairs["pair_key_tuple"] = list(
    zip(
        pairs["reference_scene"],
        pairs["secondary_scene"]
    )
)


before_filter = len(pairs)


pairs = pairs[
    ~pairs["pair_key_tuple"].isin(
        existing_pair_keys
    )
].copy()


pairs = pairs.drop(
    columns=["pair_key_tuple"]
)


skipped_count = (
    before_filter
    -
    len(pairs)
)


print(
    f"Already processed pairs skipped: "
    f"{skipped_count}"
)


# ============================================================
# HANDLE NO NEW PAIRS
# ============================================================

if pairs.empty:

    print()
    print("=" * 70)
    print("NO NEW SCIENTIFIC PAIRS AVAILABLE")
    print("=" * 70)

    print(
        "\nAll currently suitable pairs "
        "are already validated or registered."
    )

    # Save empty outputs with correct columns

    empty_columns = [
        "reference_scene",
        "secondary_scene",
        "reference_date",
        "secondary_date",
        "temporal_baseline_days",
        "perpendicular_baseline_m",
        "orbit_direction",
        "relative_orbit",
        "reference_frame",
        "secondary_frame",
        "baseline_score",
        "quality",
        "selection_status",
    ]

    empty = pd.DataFrame(
        columns=empty_columns
    )

    empty.to_csv(
        CANDIDATE_OUTPUT,
        index=False
    )

    empty.to_csv(
        RANKED_OUTPUT,
        index=False
    )

    empty.to_csv(
        PRIORITY_OUTPUT,
        index=False
    )

    print(
        f"\nOutput files updated:"
    )

    print(
        f"  {CANDIDATE_OUTPUT}"
    )

    print(
        f"  {RANKED_OUTPUT}"
    )

    print(
        f"  {PRIORITY_OUTPUT}"
    )

    print(
        "\nHyP3 submission: NOT PERFORMED"
    )

    print("=" * 70)

    raise SystemExit(0)


# ============================================================
# SAVE NEW CANDIDATES
# ============================================================

pairs = pairs.sort_values(
    [
        "orbit_direction",
        "relative_orbit",
        "baseline_score"
    ],
    na_position="last"
).reset_index(
    drop=True
)


pairs.to_csv(
    CANDIDATE_OUTPUT,
    index=False
)


# ============================================================
# RANK NEW PAIRS
# ============================================================

ranked_parts = []


quality_rank = {
    "GOOD": 0,
    "ACCEPTABLE": 1,
    "LOW_PRIORITY": 2,
    "UNKNOWN_BASELINE": 3,
}


for (
    direction,
    orbit
), group in pairs.groupby(
    [
        "orbit_direction",
        "relative_orbit"
    ],
    dropna=False
):

    group = group.copy()

    group["quality_rank"] = (
        group["quality"]
        .map(quality_rank)
        .fillna(99)
    )

    group = group.sort_values(
        [
            "quality_rank",
            "baseline_score"
        ],
        na_position="last"
    )

    group["track_rank"] = range(
        1,
        len(group) + 1
    )

    ranked_parts.append(
        group
    )


ranked = pd.concat(
    ranked_parts,
    ignore_index=True
)


ranked = ranked.drop(
    columns=["quality_rank"]
)


ranked.to_csv(
    RANKED_OUTPUT,
    index=False
)


# ============================================================
# SELECT NEW PRIORITY PAIRS
# ============================================================

priority = ranked[
    ranked["quality"].isin(
        [
            "GOOD",
            "ACCEPTABLE"
        ]
    )
].copy()


priority_parts = []


for (
    direction,
    orbit
), group in priority.groupby(
    [
        "orbit_direction",
        "relative_orbit"
    ],
    dropna=False
):

    group = group.sort_values(
        "baseline_score"
    ).head(
        PAIRS_PER_TRACK
    )

    priority_parts.append(
        group
    )


if priority_parts:

    priority = pd.concat(
        priority_parts,
        ignore_index=True
    )

else:

    priority = pd.DataFrame(
        columns=ranked.columns
    )


priority["selection_status"] = (
    "PRIORITY"
)


priority.to_csv(
    PRIORITY_OUTPUT,
    index=False
)


# ============================================================
# FINAL REPORT
# ============================================================

print()
print("=" * 70)
print("SCIENTIFIC PAIR SELECTION COMPLETE")
print("=" * 70)


print(
    f"\nNEW candidate pairs: "
    f"{len(pairs)}"
)


print(
    f"GOOD: "
    f"{(
        pairs['quality'] == 'GOOD'
    ).sum()}"
)


print(
    f"ACCEPTABLE: "
    f"{(
        pairs['quality'] == 'ACCEPTABLE'
    ).sum()}"
)


print(
    f"LOW_PRIORITY: "
    f"{(
        pairs['quality'] == 'LOW_PRIORITY'
    ).sum()}"
)


print(
    f"UNKNOWN_BASELINE: "
    f"{(
        pairs['quality'] == 'UNKNOWN_BASELINE'
    ).sum()}"
)


print(
    f"\nPriority NEW pairs selected: "
    f"{len(priority)}"
)


print(
    "\nPriority pairs:"
)


if not priority.empty:

    display_columns = [
        "reference_date",
        "secondary_date",
        "orbit_direction",
        "relative_orbit",
        "temporal_baseline_days",
        "perpendicular_baseline_m",
        "quality",
        "baseline_score",
    ]

    print(
        priority[
            display_columns
        ].to_string(
            index=False
        )
    )


print(
    "\nOutput files:"
)


print(
    f"  {CANDIDATE_OUTPUT}"
)


print(
    f"  {RANKED_OUTPUT}"
)


print(
    f"  {PRIORITY_OUTPUT}"
)


print(
    "\nHyP3 submission: NOT PERFORMED"
)


print("=" * 70)