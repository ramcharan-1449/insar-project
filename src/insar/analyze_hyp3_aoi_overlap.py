import rasterio
import geopandas as gpd
import numpy as np
from pathlib import Path
from rasterio.mask import mask
from shapely.geometry import mapping

PRODUCT_DIR = Path(
    "data/processed/hyp3/test_pair_01/"
    "S1AA_20240123T121315_20240204T121314_VVP012_INT80_G_ueF_96C4"
)

AOI_FILE = "config/mine_aoi_projected.geojson"

los_file = next(PRODUCT_DIR.glob("*_los_disp.tif"))
corr_file = next(PRODUCT_DIR.glob("*_corr.tif"))

print("=" * 70)
print("             HYP3 + AOI OVERLAP ANALYSIS")
print("=" * 70)

# ---------------------------------------------------------
# Load AOI
# ---------------------------------------------------------

aoi = gpd.read_file(AOI_FILE)

print("\nAOI CRS:", aoi.crs)

# ---------------------------------------------------------
# Open LOS raster
# ---------------------------------------------------------

with rasterio.open(los_file) as src:

    print("\nHyP3 CRS:", src.crs)
    print("Resolution:", src.res)
    print("Raster bounds:", src.bounds)

    # Make sure AOI uses raster CRS
    aoi_raster = aoi.to_crs(src.crs)

    geometry = [mapping(geom) for geom in aoi_raster.geometry]

    # Clip LOS to AOI
    los_data, los_transform = mask(
        src,
        geometry,
        crop=True,
        nodata=src.nodata
    )

    los = los_data[0]

    # Valid LOS pixels
    valid_los = (
        np.isfinite(los) &
        (los != src.nodata)
    )

    print("\nLOS AOI analysis:")
    print("AOI pixels:", los.size)
    print("Valid LOS pixels:", int(valid_los.sum()))

    if valid_los.sum() > 0:

        values = los[valid_los]

        print("Minimum LOS:", float(values.min()), "m")
        print("Maximum LOS:", float(values.max()), "m")
        print("Mean LOS:", float(values.mean()), "m")
        print("Median LOS:", float(np.median(values)), "m")

# ---------------------------------------------------------
# Correlation
# ---------------------------------------------------------

with rasterio.open(corr_file) as src:

    aoi_raster = aoi.to_crs(src.crs)

    geometry = [mapping(geom) for geom in aoi_raster.geometry]

    corr_data, corr_transform = mask(
        src,
        geometry,
        crop=True,
        nodata=src.nodata
    )

    corr = corr_data[0]

    valid_corr = (
        np.isfinite(corr) &
        (corr != src.nodata)
    )

    print("\nCorrelation AOI analysis:")
    print("AOI pixels:", corr.size)
    print("Valid correlation pixels:", int(valid_corr.sum()))

    if valid_corr.sum() > 0:

        values = corr[valid_corr]

        print("Minimum correlation:", float(values.min()))
        print("Maximum correlation:", float(values.max()))
        print("Mean correlation:", float(values.mean()))
        print("Median correlation:", float(np.median(values)))

print("\n" + "=" * 70)
print("AOI OVERLAP ANALYSIS COMPLETE")
print("=" * 70)
