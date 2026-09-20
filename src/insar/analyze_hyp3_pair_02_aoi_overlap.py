import rasterio
import geopandas as gpd
import numpy as np
from pathlib import Path
from rasterio.mask import mask

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

AOI_FILE = Path("config/mine_aoi_projected.geojson")
PRODUCT_DIR = Path("data/processed/hyp3/test_pair_02")

LOS_FILE = next(PRODUCT_DIR.rglob("*_los_disp.tif"))
CORR_FILE = next(PRODUCT_DIR.rglob("*_corr.tif"))

# ------------------------------------------------------------
# LOAD AOI
# ------------------------------------------------------------

aoi = gpd.read_file(AOI_FILE)

print("=" * 70)
print("             HYP3 PAIR 02 AOI OVERLAP ANALYSIS")
print("=" * 70)

print("\nAOI CRS:", aoi.crs)

# ------------------------------------------------------------
# LOS ANALYSIS
# ------------------------------------------------------------

with rasterio.open(LOS_FILE) as los_src:

    print("\nLOS CRS:", los_src.crs)
    print("LOS resolution:", los_src.res)

    # Reproject AOI if necessary
    aoi_for_raster = aoi.to_crs(los_src.crs)

    geometry = aoi_for_raster.geometry

    los_data, los_transform = mask(
        los_src,
        geometry,
        crop=True
    )

    los = los_data[0].astype("float64")

    # Valid LOS:
    # finite + not zero + not nodata
    valid_los = (
        np.isfinite(los)
        & (los != 0)
    )

    if los_src.nodata is not None:
        valid_los &= los != los_src.nodata

# ------------------------------------------------------------
# CORRELATION ANALYSIS
# ------------------------------------------------------------

with rasterio.open(CORR_FILE) as corr_src:

    corr_data, corr_transform = mask(
        corr_src,
        geometry,
        crop=True
    )

    corr = corr_data[0].astype("float64")

    valid_corr = (
        np.isfinite(corr)
        & (corr > 0)
    )

    if corr_src.nodata is not None:
        valid_corr &= corr != corr_src.nodata

# ------------------------------------------------------------
# COMMON VALID PIXELS
# ------------------------------------------------------------

common_valid = valid_los & valid_corr

los_values = los[common_valid]
corr_values = corr[common_valid]

# ------------------------------------------------------------
# RESULTS
# ------------------------------------------------------------

print("\n" + "-" * 70)
print("AOI RESULTS")
print("-" * 70)

print("AOI raster pixels :", los.size)
print("Valid LOS pixels  :", np.sum(valid_los))
print("Valid Corr pixels :", np.sum(valid_corr))
print("Common valid      :", np.sum(common_valid))

if los.size > 0:
    print(
        "Valid coverage    :",
        round(np.sum(common_valid) / los.size * 100, 2),
        "%"
    )

if len(los_values) > 0:

    print("\nLOS displacement (meters):")
    print("Min               :", np.min(los_values))
    print("Max               :", np.max(los_values))
    print("Mean              :", np.mean(los_values))
    print("Median            :", np.median(los_values))
    print("Std               :", np.std(los_values))

    print("\nLOS displacement (millimeters):")
    print("Min               :", np.min(los_values) * 1000)
    print("Max               :", np.max(los_values) * 1000)
    print("Mean              :", np.mean(los_values) * 1000)
    print("Median            :", np.median(los_values) * 1000)

if len(corr_values) > 0:

    print("\nCorrelation:")
    print("Min               :", np.min(corr_values))
    print("Max               :", np.max(corr_values))
    print("Mean              :", np.mean(corr_values))
    print("Median            :", np.median(corr_values))
    print("Std               :", np.std(corr_values))

    # Project threshold
    threshold = 0.5

    high_corr = corr_values >= threshold

    print("\nCorrelation >= 0.5:")
    print("Pixels            :", np.sum(high_corr))
    print(
        "Percentage        :",
        round(np.sum(high_corr) / len(corr_values) * 100, 2),
        "%"
    )

print("\n" + "=" * 70)
print("PAIR 02 AOI ANALYSIS COMPLETE")
print("=" * 70)
