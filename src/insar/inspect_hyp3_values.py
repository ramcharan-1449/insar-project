import rasterio
import numpy as np
from pathlib import Path

PRODUCT_DIR = Path(
    "data/processed/hyp3/test_pair_01/"
    "S1AA_20240123T121315_20240204T121314_VVP012_INT80_G_ueF_96C4"
)

files = {
    "LOS displacement": "*_los_disp.tif",
    "Correlation": "*_corr.tif",
    "Unwrapped phase": "*_unw_phase.tif",
    "Vertical displacement": "*_vert_disp.tif",
    "Incidence angle": "*_inc_map.tif",
}

print("=" * 70)
print("             HYP3 PIXEL VALUE INSPECTION")
print("=" * 70)

for name, pattern in files.items():

    matches = list(PRODUCT_DIR.glob(pattern))

    if not matches:
        print(f"\n{name}: FILE NOT FOUND")
        continue

    tif = matches[0]

    print("\n" + "-" * 70)
    print(name)
    print("File:", tif.name)

    with rasterio.open(tif) as src:

        data = src.read(1)

        nodata = src.nodata

        if nodata is not None:
            valid = data[data != nodata]
        else:
            valid = data[np.isfinite(data)]

        valid = valid[np.isfinite(valid)]

        print("Total pixels :", data.size)
        print("Valid pixels :", valid.size)

        if valid.size > 0:

            print("Minimum      :", float(np.min(valid)))
            print("Maximum      :", float(np.max(valid)))
            print("Mean         :", float(np.mean(valid)))
            print("Median       :", float(np.median(valid)))
            print("Std Dev      :", float(np.std(valid)))

            print("Sample values:")

            sample = valid[:10]

            for value in sample:
                print("   ", float(value))

print("\n" + "=" * 70)
print("VALUE INSPECTION COMPLETE")
print("=" * 70)