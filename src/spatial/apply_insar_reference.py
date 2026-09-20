import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.mask import mask
import geopandas as gpd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_FILE = PROJECT_ROOT / "config" / "insar_reference_config.json"

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
    / "hyp3"
    / "test_pair_01"
    / "S1AA_20240123T121315_20240204T121314"
    "_referenced_los_disp_aoi.tif"
)


# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("       APPLY AOI-RESTRICTED INSAR REFERENCE")
print("=" * 70)


# ------------------------------------------------------------
# 1. Load configuration
# ------------------------------------------------------------

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

minimum_correlation = config["quality_rules"]["minimum_correlation"]
reference_correlation = config["quality_rules"]["reference_candidate_correlation"]

print("\nReference configuration loaded.")
print(f"Minimum correlation: {minimum_correlation}")
print(f"Reference candidate correlation: {reference_correlation}")


# ------------------------------------------------------------
# 2. Load AOI
# ------------------------------------------------------------

aoi = gpd.read_file(AOI_FILE)

if aoi.empty:
    raise ValueError("AOI file is empty.")

print("\nAOI loaded.")
print(f"AOI CRS: {aoi.crs}")

geometries = list(aoi.geometry)


# ------------------------------------------------------------
# 3. Read LOS and correlation rasters
# ------------------------------------------------------------

with rasterio.open(LOS_FILE) as los_src:

    print("\nLOS raster:")
    print(f"CRS: {los_src.crs}")
    print(f"Resolution: {los_src.res}")
    print(f"Raster size: {los_src.width} x {los_src.height}")

    # Reproject AOI if necessary
    if aoi.crs != los_src.crs:
        aoi = aoi.to_crs(los_src.crs)
        geometries = list(aoi.geometry)

    # Clip LOS to AOI
    los_aoi, los_transform = mask(
        los_src,
        geometries,
        crop=True,
        filled=True,
        nodata=np.nan
    )

    los_data = los_aoi[0]

    los_nodata = los_src.nodata


with rasterio.open(CORR_FILE) as corr_src:

    # AOI should already match LOS CRS
    if aoi.crs != corr_src.crs:
        aoi = aoi.to_crs(corr_src.crs)
        geometries = list(aoi.geometry)

    corr_aoi, corr_transform = mask(
        corr_src,
        geometries,
        crop=True,
        filled=True,
        nodata=np.nan
    )

    corr_data = corr_aoi[0]


# ------------------------------------------------------------
# 4. Check raster alignment
# ------------------------------------------------------------

if los_data.shape != corr_data.shape:
    raise ValueError(
        f"LOS and correlation AOI shapes do not match: "
        f"{los_data.shape} vs {corr_data.shape}"
    )

if los_transform != corr_transform:
    raise ValueError("LOS and correlation AOI transforms do not match.")


print("\nAOI raster:")
print(f"Shape: {los_data.shape}")


# ------------------------------------------------------------
# 5. Create valid pixel mask
# ------------------------------------------------------------

valid_mask = (
    np.isfinite(los_data)
    & np.isfinite(corr_data)
    & (los_data != 0)
    & (corr_data >= minimum_correlation)
)


valid_pixels = np.count_nonzero(valid_mask)

print(f"Valid AOI pixels: {valid_pixels}")


if valid_pixels == 0:
    raise ValueError("No valid InSAR pixels found inside AOI.")


# ------------------------------------------------------------
# 6. Select reference candidates INSIDE AOI
# ------------------------------------------------------------

reference_mask = (
    valid_mask
    & (corr_data >= reference_correlation)
)

reference_pixels = np.count_nonzero(reference_mask)

print(f"Reference candidate pixels: {reference_pixels}")


if reference_pixels == 0:
    raise ValueError(
        "No high-correlation reference candidates found inside AOI."
    )


# ------------------------------------------------------------
# 7. Calculate reference LOS
# ------------------------------------------------------------

reference_values = los_data[reference_mask]

reference_los = float(np.median(reference_values))

print(f"\nAOI-restricted reference LOS estimate: {reference_los:.6f} m")
print(f"AOI-restricted reference LOS estimate: {reference_los * 1000:.3f} mm")


# ------------------------------------------------------------
# 8. Apply reference to AOI pixels
# ------------------------------------------------------------

referenced_los = np.full(
    los_data.shape,
    np.nan,
    dtype=np.float32
)

referenced_los[valid_mask] = (
    los_data[valid_mask] - reference_los
).astype(np.float32)


# ------------------------------------------------------------
# 9. Statistics
# ------------------------------------------------------------

values = referenced_los[np.isfinite(referenced_los)]

print("\nReferenced LOS statistics:")

print(f"Minimum: {values.min():.6f} m")
print(f"Maximum: {values.max():.6f} m")
print(f"Mean: {values.mean():.6f} m")
print(f"Median: {np.median(values):.6f} m")
print(f"Std: {values.std():.6f} m")

print("\nMillimetres:")

print(f"Range: {values.min() * 1000:.3f} to {values.max() * 1000:.3f} mm")
print(f"Mean: {values.mean() * 1000:.3f} mm")
print(f"Median: {np.median(values) * 1000:.3f} mm")


# ------------------------------------------------------------
# 10. Save referenced raster
# ------------------------------------------------------------

with rasterio.open(LOS_FILE) as src:

    profile = src.profile.copy()

    profile.update(
        dtype="float32",
        count=1,
        height=referenced_los.shape[0],
        width=referenced_los.shape[1],
        transform=los_transform,
        nodata=np.nan,
        compress="deflate"
    )

    with rasterio.open(OUTPUT_FILE, "w", **profile) as dst:

        dst.write(referenced_los, 1)


print("\nOutput:")
print(OUTPUT_FILE)

print("\nIMPORTANT:")
print(
    "This raster contains relative LOS displacement "
    "with respect to an AOI-restricted development reference."
)

print(
    "It does not represent absolute ground displacement."
)

print(
    "The reference area still requires scientific stability review."
)

print("=" * 70)