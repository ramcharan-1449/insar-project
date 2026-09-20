import rasterio
import numpy as np
from pathlib import Path

PRODUCT_DIR = Path("data/processed/hyp3/test_pair_02")

los_file = next(PRODUCT_DIR.rglob("*_los_disp.tif"))
corr_file = next(PRODUCT_DIR.rglob("*_corr.tif"))
phase_file = next(PRODUCT_DIR.rglob("*_unw_phase.tif"))
vert_file = next(PRODUCT_DIR.rglob("*_vert_disp.tif"))
inc_file = next(PRODUCT_DIR.rglob("*_inc_map.tif"))

print("=" * 70)
print("              HYP3 PAIR 02 VALUE INSPECTION")
print("=" * 70)


def inspect_raster(name, path, exclude_zero=True):

    with rasterio.open(path) as src:
        data = src.read(1).astype("float64")

        if exclude_zero:
            valid = np.isfinite(data) & (data != 0)
        else:
            valid = np.isfinite(data)

        values = data[valid]

        print("\n" + "-" * 70)
        print(f"{name}")
        print("-" * 70)
        print("File   :", path.name)
        print("Pixels :", data.size)
        print("Valid  :", values.size)

        if values.size > 0:
            print("Min    :", np.min(values))
            print("Max    :", np.max(values))
            print("Mean   :", np.mean(values))
            print("Median :", np.median(values))
            print("Std    :", np.std(values))
        else:
            print("No valid values found.")


inspect_raster("LOS DISPLACEMENT", los_file)
inspect_raster("CORRELATION", corr_file)
inspect_raster("UNWRAPPED PHASE", phase_file)
inspect_raster("VERTICAL DISPLACEMENT", vert_file)
inspect_raster("INCIDENCE ANGLE", inc_file, exclude_zero=False)

print("\n" + "=" * 70)
print("PAIR 02 VALUE INSPECTION COMPLETE")
print("=" * 70)