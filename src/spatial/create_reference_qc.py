from pathlib import Path

import geopandas as gpd
import rasterio
from rasterio.mask import mask
import numpy as np


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AOI_FILE = PROJECT_ROOT / "config" / "mine_aoi_projected.geojson"

LOS_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hyp3"
    / "test_pair_01"
    / "S1AA_20240123T121315_20240204T121314_VVP012_INT80_G_ueF_96C4"
    / "S1AA_20240123T121315_20240204T121314_VVP012_INT80_G_ueF_96C4_los_disp.tif"
)

CORR_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hyp3"
    / "test_pair_01"
    / "S1AA_20240123T121315_20240204T121314_VVP012_INT80_G_ueF_96C4"
    / "S1AA_20240123T121315_20240204T121314_VVP012_INT80_G_ueF_96C4_corr.tif"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_reference_qc_test_pair_01.geojson"
)

MIN_CORR = 0.7


# ============================================================
# START
# ============================================================

print("=" * 70)
print("             INSAR REFERENCE SPATIAL QC")
print("=" * 70)


# ------------------------------------------------------------
# 1. Load AOI
# ------------------------------------------------------------

aoi = gpd.read_file(AOI_FILE)

print("\nAOI loaded.")
print(f"AOI CRS: {aoi.crs}")


# ------------------------------------------------------------
# 2. Read LOS raster
# ------------------------------------------------------------

with rasterio.open(LOS_FILE) as los_src:

    if aoi.crs != los_src.crs:
        aoi = aoi.to_crs(los_src.crs)

    geometries = list(aoi.geometry)

    los_data, transform = mask(
        los_src,
        geometries,
        crop=True,
        filled=True,
        nodata=np.nan
    )

    los = los_data[0]

    print("\nLOS raster loaded.")
    print(f"CRS: {los_src.crs}")
    print(f"Resolution: {los_src.res}")


# ------------------------------------------------------------
# 3. Read correlation raster
# ------------------------------------------------------------

with rasterio.open(CORR_FILE) as corr_src:

    corr_data, corr_transform = mask(
        corr_src,
        geometries,
        crop=True,
        filled=True,
        nodata=np.nan
    )

    corr = corr_data[0]


# ------------------------------------------------------------
# 4. Create candidate mask
# ------------------------------------------------------------

valid = (
    np.isfinite(los)
    & np.isfinite(corr)
    & (los != 0)
    & (corr >= MIN_CORR)
)

print("\nReference candidate analysis:")
print(f"Minimum correlation: {MIN_CORR}")
print(f"Candidate pixels: {np.count_nonzero(valid)}")


# ------------------------------------------------------------
# 5. Convert pixels to point features
# ------------------------------------------------------------

rows, cols = np.where(valid)

records = []

for row, col in zip(rows, cols):

    x, y = rasterio.transform.xy(
        transform,
        row,
        col,
        offset="center"
    )

    records.append(
        {
            "reference_candidate": True,
            "correlation": float(corr[row, col]),
            "los_displacement_m": float(los[row, col]),
            "los_displacement_mm": float(los[row, col] * 1000),
            "geometry": f"POINT ({x} {y})"
        }
    )


# ------------------------------------------------------------
# 6. Create GeoDataFrame
# ------------------------------------------------------------

from shapely import wkt

for record in records:
    record["geometry"] = wkt.loads(record["geometry"])

gdf = gpd.GeoDataFrame(
    records,
    geometry="geometry",
    crs=aoi.crs
)


# ------------------------------------------------------------
# 7. Statistics
# ------------------------------------------------------------

if len(gdf) > 0:

    print("\nReference candidate statistics:")

    print(
        f"Correlation mean: "
        f"{gdf['correlation'].mean():.4f}"
    )

    print(
        f"Correlation median: "
        f"{gdf['correlation'].median():.4f}"
    )

    print(
        f"Correlation minimum: "
        f"{gdf['correlation'].min():.4f}"
    )

    print(
        f"Correlation maximum: "
        f"{gdf['correlation'].max():.4f}"
    )

    print(
        f"LOS mean: "
        f"{gdf['los_displacement_mm'].mean():.3f} mm"
    )

    print(
        f"LOS median: "
        f"{gdf['los_displacement_mm'].median():.3f} mm"
    )


# ------------------------------------------------------------
# 8. Save
# ------------------------------------------------------------

gdf.to_file(
    OUTPUT_FILE,
    driver="GeoJSON"
)

print("\nOutput:")
print(OUTPUT_FILE)

print("\nIMPORTANT:")
print(
    "These points are high-correlation reference candidates."
)

print(
    "They are NOT automatically confirmed stable ground."
)

print("=" * 70)