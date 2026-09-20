import rasterio
import geopandas as gpd
import numpy as np
from pathlib import Path
from rasterio.mask import mask

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

AOI_FILE = Path("config/mine_aoi_projected.geojson")

PRODUCT_DIR = Path(
    "data/processed/hyp3/test_pair_02"
)

LOS_FILE = next(PRODUCT_DIR.rglob("*_los_disp.tif"))
CORR_FILE = next(PRODUCT_DIR.rglob("*_corr.tif"))

OUTPUT_FILE = PRODUCT_DIR / (
    "S1AA_20240603T121315_20240615T121315_"
    "referenced_los_disp_aoi.tif"
)

# ------------------------------------------------------------
# SETTINGS
# ------------------------------------------------------------

MIN_CORRELATION = 0.7

# ------------------------------------------------------------
# LOAD AOI
# ------------------------------------------------------------

aoi = gpd.read_file(AOI_FILE)

# ------------------------------------------------------------
# READ LOS
# ------------------------------------------------------------

with rasterio.open(LOS_FILE) as los_src:

    aoi_raster = aoi.to_crs(los_src.crs)

    geometry = aoi_raster.geometry

    los_data, out_transform = mask(
        los_src,
        geometry,
        crop=True
    )

    los = los_data[0].astype("float64")

    profile = los_src.profile.copy()

    nodata = los_src.nodata

# ------------------------------------------------------------
# READ CORRELATION
# ------------------------------------------------------------

with rasterio.open(CORR_FILE) as corr_src:

    corr_data, _ = mask(
        corr_src,
        geometry,
        crop=True
    )

    corr = corr_data[0].astype("float64")

# ------------------------------------------------------------
# VALID PIXELS
# ------------------------------------------------------------

valid = (
    np.isfinite(los)
    & np.isfinite(corr)
    & (los != 0)
    & (corr >= MIN_CORRELATION)
)

if nodata is not None:
    valid &= los != nodata

reference_values = los[valid]

# ------------------------------------------------------------
# REFERENCE ESTIMATE
# ------------------------------------------------------------

if reference_values.size == 0:
    raise RuntimeError(
        "No valid reference pixels found inside AOI."
    )

reference_los = np.median(reference_values)

# ------------------------------------------------------------
# APPLY REFERENCE
# ------------------------------------------------------------

referenced_los = np.full(
    los.shape,
    np.nan,
    dtype="float32"
)

referenced_los[valid] = (
    los[valid] - reference_los
).astype("float32")

# ------------------------------------------------------------
# OUTPUT PROFILE
# ------------------------------------------------------------

profile.update(
    height=referenced_los.shape[0],
    width=referenced_los.shape[1],
    transform=out_transform,
    dtype="float32",
    count=1,
    nodata=np.nan,
    compress="deflate"
)

# ------------------------------------------------------------
# WRITE OUTPUT
# ------------------------------------------------------------

with rasterio.open(OUTPUT_FILE, "w", **profile) as dst:

    dst.write(
        referenced_los,
        1
    )

# ------------------------------------------------------------
# REPORT
# ------------------------------------------------------------

values = referenced_los[np.isfinite(referenced_los)]

print("=" * 70)
print("          PAIR 02 INSAR REFERENCE CORRECTION")
print("=" * 70)

print("\nAOI CRS              :", aoi.crs)
print("LOS CRS              :", profile["crs"])
print("AOI valid pixels     :", reference_values.size)
print("Reference threshold  :", MIN_CORRELATION)

print(
    "Reference LOS (m)    :",
    reference_los
)

print(
    "Reference LOS (mm)   :",
    reference_los * 1000
)

print("\nReferenced LOS:")
print("Min (mm)             :", np.min(values) * 1000)
print("Max (mm)             :", np.max(values) * 1000)
print("Mean (mm)            :", np.mean(values) * 1000)
print("Median (mm)          :", np.median(values) * 1000)
print("Std (mm)             :", np.std(values) * 1000)

print("\nOutput:")
print(OUTPUT_FILE)

print("\n" + "=" * 70)
print("PAIR 02 REFERENCE CORRECTION COMPLETE")
print("=" * 70)