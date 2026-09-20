import numpy as np
import rasterio
from pathlib import Path
from rasterio.mask import mask
import geopandas as gpd

BASE = Path("data/processed/hyp3/test_pair_03")

los_file = BASE / "pair_03_los_disp.tif"
corr_file = next(BASE.rglob("*_corr.tif"))
aoi_file = Path("config/mine_aoi.geojson")

output_file = BASE / "pair_03_referenced_los_disp_aoi.tif"

REFERENCE_CORR_THRESHOLD = 0.7

print("Starting Pair 03 reference correction...")

with rasterio.open(los_file) as los_src:
    los_aoi, transform = mask(
        los_src,
        gpd.read_file(aoi_file).to_crs(los_src.crs).geometry,
        crop=True,
        nodata=np.nan
    )

    profile = los_src.profile.copy()

with rasterio.open(corr_file) as corr_src:
    corr_aoi, _ = mask(
        corr_src,
        gpd.read_file(aoi_file).to_crs(corr_src.crs).geometry,
        crop=True,
        nodata=np.nan
    )

los = los_aoi[0].astype(np.float32)
corr = corr_aoi[0].astype(np.float32)

# Valid pixels for reference selection
reference_candidates = (
    np.isfinite(los) &
    np.isfinite(corr) &
    (corr >= REFERENCE_CORR_THRESHOLD)
)

if reference_candidates.sum() == 0:
    raise RuntimeError("No valid reference pixels found.")

reference_value = np.median(los[reference_candidates])

# Reference correction
referenced_los = np.full(
    los.shape,
    np.nan,
    dtype=np.float32
)

valid = (
    np.isfinite(los) &
    np.isfinite(corr) &
    (corr >= 0.5)
)

referenced_los[valid] = (
    los[valid] - reference_value
)

profile.update(
    height=referenced_los.shape[0],
    width=referenced_los.shape[1],
    transform=transform,
    dtype="float32",
    count=1,
    nodata=np.nan,
    compress="deflate"
)

with rasterio.open(output_file, "w", **profile) as dst:
    dst.write(referenced_los, 1)

v = referenced_los[np.isfinite(referenced_los)]

print()
print("PAIR 03 REFERENCE QC")
print("====================")

print("Reference candidates:", int(reference_candidates.sum()))
print("Reference LOS (mm):", float(reference_value * 1000))

print()
print("Referenced LOS statistics:")
print("Min (mm):", float(v.min() * 1000))
print("Max (mm):", float(v.max() * 1000))
print("Mean (mm):", float(v.mean() * 1000))
print("Median (mm):", float(np.median(v) * 1000))
print("Std (mm):", float(v.std() * 1000))
print("Valid pixels:", int(len(v)))

print()
print("Output:", output_file)
print()
print("Pair 03 reference correction complete.")