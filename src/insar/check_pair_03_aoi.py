import numpy as np
import rasterio
import geopandas as gpd
from pathlib import Path
from rasterio.mask import mask

BASE = Path("data/processed/hyp3/test_pair_03")

los_file = BASE / "pair_03_los_disp.tif"
corr_file = next(BASE.rglob("*_corr.tif"))
aoi_file = Path("config/mine_aoi.geojson")

print("Starting Pair 03 AOI QC...")

with rasterio.open(los_file) as los_src:
    with rasterio.open(corr_file) as corr_src:

        aoi = gpd.read_file(aoi_file).to_crs(los_src.crs)

        los, _ = mask(
            los_src,
            aoi.geometry,
            crop=True,
            nodata=np.nan
        )

        corr, _ = mask(
            corr_src,
            aoi.geometry,
            crop=True,
            nodata=np.nan
        )

los = los[0]
corr = corr[0]

valid = (
    np.isfinite(los) &
    np.isfinite(corr) &
    (corr > 0)
)

high_quality = valid & (corr >= 0.5)

print()
print("PAIR 03 AOI QC")
print("================")

print("AOI pixels:", int(valid.size))
print("Valid LOS pixels:", int(valid.sum()))

print(
    "Valid coverage:",
    round(valid.sum() / valid.size * 100, 2),
    "%"
)

print()
print("Correlation:")
print("Min:", float(corr[valid].min()))
print("Max:", float(corr[valid].max()))
print("Mean:", float(corr[valid].mean()))
print("Median:", float(np.median(corr[valid])))

print()
print("Correlation >= 0.5:")
print("Pixels:", int(high_quality.sum()))

print(
    "Percentage of valid pixels:",
    round(high_quality.sum() / valid.sum() * 100, 2),
    "%"
)

v = los[high_quality]

print()
print("LOS displacement after correlation filtering:")
print("Min (mm):", float(v.min() * 1000))
print("Max (mm):", float(v.max() * 1000))
print("Mean (mm):", float(v.mean() * 1000))
print("Median (mm):", float(np.median(v) * 1000))
print("Std (mm):", float(v.std() * 1000))

print()
print("Pair 03 AOI QC complete.")