import numpy as np
import rasterio
from pathlib import Path

BASE = Path("data/processed/hyp3/test_pair_03")

phase_file = next(BASE.rglob("*_unw_phase.tif"))
output_file = BASE / "pair_03_los_disp.tif"

# Sentinel-1 C-band wavelength
WAVELENGTH_M = 0.055465763

# HyP3 LOS convention:
# positive = toward sensor
# negative = away from sensor
PHASE_TO_LOS = -WAVELENGTH_M / (4.0 * np.pi)

with rasterio.open(phase_file) as src:
    phase = src.read(1).astype(np.float32)

    profile = src.profile.copy()

    nodata = src.nodata

    valid = np.isfinite(phase)

    if nodata is not None:
        valid &= phase != nodata

    # Phase raster uses 0 as nodata in this product
    valid &= phase != 0

    los = np.full(
        phase.shape,
        np.nan,
        dtype=np.float32
    )

    los[valid] = phase[valid] * PHASE_TO_LOS

    profile.update(
        dtype="float32",
        count=1,
        nodata=np.nan,
        compress="deflate"
    )

    with rasterio.open(output_file, "w", **profile) as dst:
        dst.write(los, 1)

print("Pair 03 LOS displacement created")
print("Input :", phase_file)
print("Output:", output_file)

v = los[np.isfinite(los)]

print()
print("LOS displacement statistics:")
print("Min (m):", v.min())
print("Max (m):", v.max())
print("Mean (m):", v.mean())
print("Median (m):", np.median(v))
print("Min (mm):", v.min() * 1000)
print("Max (mm):", v.max() * 1000)
print("Mean (mm):", v.mean() * 1000)
print("Median (mm):", np.median(v) * 1000)
print("Valid pixels:", len(v))
