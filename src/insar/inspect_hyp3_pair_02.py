import rasterio
from pathlib import Path

# Pair 02 root directory
PRODUCT_DIR = Path("data/processed/hyp3/test_pair_02")

print("=" * 70)
print("              HYP3 PAIR 02 PRODUCT INSPECTION")
print("=" * 70)

# Search recursively inside Pair 02 folder
tif_files = sorted(PRODUCT_DIR.rglob("*.tif"))

print(f"\nSearch directory: {PRODUCT_DIR}")
print(f"GeoTIFF files found: {len(tif_files)}")

if len(tif_files) == 0:
    print("\nERROR: No GeoTIFF files found.")
    print("Checking directories inside test_pair_02:")

    if PRODUCT_DIR.exists():
        for item in PRODUCT_DIR.rglob("*"):
            print(" ", item)
    else:
        print("Pair 02 directory does not exist.")

else:

    for tif in tif_files:

        print("\n" + "-" * 70)
        print("FILE:", tif.name)

        with rasterio.open(tif) as src:

            print("CRS         :", src.crs)
            print("Width       :", src.width)
            print("Height      :", src.height)
            print("Resolution  :", src.res)
            print("Bounds      :", src.bounds)
            print("Data type   :", src.dtypes[0])
            print("NoData      :", src.nodata)
            print("Bands       :", src.count)
            print("Transform   :", src.transform)

print("\n" + "=" * 70)
print("PAIR 02 INSPECTION COMPLETE")
print("=" * 70)