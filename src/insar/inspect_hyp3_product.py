import rasterio
from pathlib import Path

PRODUCT_DIR = Path(
    "data/processed/hyp3/test_pair_01/"
    "S1AA_20240123T121315_20240204T121314_VVP012_INT80_G_ueF_96C4"
)

print("=" * 70)
print("              HYP3 PRODUCT INSPECTION")
print("=" * 70)

tif_files = list(PRODUCT_DIR.glob("*.tif"))

print(f"\nGeoTIFF files found: {len(tif_files)}")

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
print("INSPECTION COMPLETE")
print("=" * 70)