from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import asf_search as asf
import json
from shapely.geometry import shape


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AOI_FILE = PROJECT_ROOT / "config" / "mine_aoi.geojson"

MANIFEST_FILE = PROJECT_ROOT / "config" / "sentinel1_scene_manifest.csv"

START_DATE = "2024-01-01"

# Automatically uses today's UTC date
END_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ============================================================
# LOAD AOI
# ============================================================

with open(AOI_FILE, "r", encoding="utf-8") as f:
    aoi = json.load(f)

geometry = shape(aoi["features"][0]["geometry"])
aoi_wkt = geometry.wkt


# ============================================================
# SEARCH SENTINEL-1 ONLINE
# ============================================================

print("=" * 70)
print("AUTOMATIC SENTINEL-1 NEW-SCENE DETECTION")
print("=" * 70)

print(f"AOI       : {AOI_FILE}")
print(f"Start date: {START_DATE}")
print(f"End date  : {END_DATE}")
print()

print("Searching ASF for Sentinel-1 SLC scenes...")

results = asf.search(
    platform="Sentinel-1",
    processingLevel="SLC",
    beamMode="IW",
    intersectsWith=aoi_wkt,
    start=START_DATE,
    end=END_DATE,
)

print(f"Online scenes found: {len(results)}")


# ============================================================
# EXTRACT METADATA
# ============================================================

records = []

for result in results:

    p = result.properties

    records.append({
        "scene_id": p.get("sceneName"),
        "acquisition_date": p.get("startTime"),
        "orbit_direction": p.get("flightDirection"),
        "relative_orbit": p.get("pathNumber"),
        "frame": p.get("frameNumber"),
        "platform": p.get("platform"),
        "polarization": p.get("polarization"),
        "product_type": p.get("processingLevel"),
        "beam_mode": p.get("beamModeType"),
        "url": p.get("url"),
    })


online_df = pd.DataFrame(records)


if online_df.empty:
    print("No Sentinel-1 scenes found.")
    raise SystemExit(0)


# ============================================================
# NORMALIZE
# ============================================================

online_df["acquisition_date"] = pd.to_datetime(
    online_df["acquisition_date"],
    utc=True,
    errors="coerce"
)

online_df = online_df.drop_duplicates(
    subset=["scene_id"]
)

online_df = online_df.sort_values(
    "acquisition_date"
).reset_index(drop=True)


# ============================================================
# LOAD EXISTING MANIFEST
# ============================================================

if MANIFEST_FILE.exists():

    manifest_df = pd.read_csv(
        MANIFEST_FILE
    )

    if "scene_id" in manifest_df.columns:
        known_scene_ids = set(
            manifest_df["scene_id"]
            .dropna()
            .astype(str)
        )
    else:
        known_scene_ids = set()

else:

    manifest_df = pd.DataFrame()
    known_scene_ids = set()


# ============================================================
# DETECT NEW SCENES
# ============================================================

online_df["scene_id"] = online_df["scene_id"].astype(str)

new_df = online_df[
    ~online_df["scene_id"].isin(known_scene_ids)
].copy()


print()
print(f"Known scenes : {len(known_scene_ids)}")
print(f"New scenes   : {len(new_df)}")


# ============================================================
# ADD MANIFEST FIELDS
# ============================================================

if not new_df.empty:

    new_df["first_seen"] = datetime.now(
        timezone.utc
    ).isoformat()

    new_df["processing_status"] = "NEW"

    new_df["pair_status"] = "NOT_PAIRED"

    new_df["hyP3_status"] = "NOT_SUBMITTED"


# ============================================================
# UPDATE MANIFEST
# ============================================================

if manifest_df.empty:

    updated_df = new_df.copy()

else:

    # Convert existing manifest to strings
    manifest_df["scene_id"] = (
        manifest_df["scene_id"]
        .astype(str)
    )

    updated_df = pd.concat(
        [
            manifest_df,
            new_df
        ],
        ignore_index=True
    )


# Remove accidental duplicates
updated_df = updated_df.drop_duplicates(
    subset=["scene_id"],
    keep="first"
)


# ============================================================
# SAVE
# ============================================================

MANIFEST_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

updated_df.to_csv(
    MANIFEST_FILE,
    index=False
)


# ============================================================
# REPORT
# ============================================================

print()
print("-" * 70)
print("SCENE DETECTION RESULT")
print("-" * 70)

print(f"Online scenes : {len(online_df)}")
print(f"Known scenes  : {len(known_scene_ids)}")
print(f"New scenes    : {len(new_df)}")
print(f"Manifest total: {len(updated_df)}")

print()
print(f"Manifest saved:")
print(MANIFEST_FILE)


if not new_df.empty:

    print()
    print("NEW SENTINEL-1 SCENES")
    print("-" * 70)

    for _, row in new_df.iterrows():

        print(
            row["acquisition_date"],
            "|",
            row["orbit_direction"],
            "|",
            row["relative_orbit"],
            "|",
            row["scene_id"]
        )

else:

    print()
    print("No new Sentinel-1 scenes detected.")


print()
print("=" * 70)
print("PHASE 14 COMPLETE")
print("=" * 70)