import rasterio
import geopandas as gpd
import pandas as pd
import numpy as np

from pathlib import Path
from rasterio.mask import mask
from rasterio.warp import reproject, Resampling


# ============================================================
# PATHS
# ============================================================

GRID_FILE = Path(
    "data/processed/grid/mine_grid_coverage.geojson"
)

PRODUCT_DIR = Path(
    "data/processed/hyp3/test_pair_02"
)

LOS_FILE = PRODUCT_DIR / (
    "S1AA_20240603T121315_20240615T121315_"
    "referenced_los_disp_aoi.tif"
)

CORR_FILE = next(
    PRODUCT_DIR.rglob("*_corr.tif")
)

OUTPUT_FILE = Path(
    "data/processed/grid/"
    "spatial_features_test_pair_02.csv"
)


# ============================================================
# SETTINGS
# ============================================================

CORRELATION_THRESHOLD = 0.5
MIN_VALID_PERCENTAGE = 30.0


# ============================================================
# LOAD GRID
# ============================================================

grid = gpd.read_file(GRID_FILE)

print("=" * 70)
print("          PAIR 02 INSAR GRID FEATURE EXTRACTION")
print("=" * 70)

print("\nGrid cells:", len(grid))
print("Grid CRS  :", grid.crs)


# ============================================================
# OPEN LOS AND CORRELATION
# ============================================================

with rasterio.open(LOS_FILE) as los_src, \
     rasterio.open(CORR_FILE) as corr_src:

    print("LOS CRS  :", los_src.crs)
    print("CORR CRS :", corr_src.crs)

    print("\nLOS shape :", los_src.height, "x", los_src.width)
    print("CORR shape:", corr_src.height, "x", corr_src.width)

    if los_src.crs != corr_src.crs:
        raise RuntimeError(
            "LOS and correlation CRS do not match."
        )

    # --------------------------------------------------------
    # CREATE CORRELATION RASTER ON LOS GRID
    # --------------------------------------------------------

    correlation_on_los_grid = np.full(
        (los_src.height, los_src.width),
        np.nan,
        dtype="float32"
    )

    reproject(
        source=rasterio.band(corr_src, 1),
        destination=correlation_on_los_grid,
        src_transform=corr_src.transform,
        src_crs=corr_src.crs,
        src_nodata=corr_src.nodata,
        dst_transform=los_src.transform,
        dst_crs=los_src.crs,
        dst_nodata=np.nan,
        resampling=Resampling.nearest
    )

    print("\nCorrelation successfully aligned to LOS grid.")

    print(
        "Aligned correlation shape:",
        correlation_on_los_grid.shape
    )

    # --------------------------------------------------------
    # CREATE AN IN-MEMORY CORRELATION DATASET
    # --------------------------------------------------------

    corr_profile = corr_src.profile.copy()

    corr_profile.update(
        driver="GTiff",
        height=los_src.height,
        width=los_src.width,
        transform=los_src.transform,
        crs=los_src.crs,
        dtype="float32",
        count=1,
        nodata=np.nan
    )

    from rasterio.io import MemoryFile

    with MemoryFile() as memfile:

        with memfile.open(**corr_profile) as aligned_corr:

            aligned_corr.write(
                correlation_on_los_grid,
                1
            )

            # ------------------------------------------------
            # GRID IN LOS CRS
            # ------------------------------------------------

            grid_raster = grid.to_crs(
                los_src.crs
            )

            results = []

            # ================================================
            # PROCESS GRID CELLS
            # ================================================

            for index, cell in grid_raster.iterrows():

                cell_id = cell["cell_id"]

                geometry = [
                    cell.geometry
                ]

                # --------------------------------------------
                # LOS AND CORRELATION NOW USE SAME GRID
                # --------------------------------------------

                try:

                    los_data, _ = mask(
                        los_src,
                        geometry,
                        crop=True,
                        filled=False
                    )

                    corr_data, _ = mask(
                        aligned_corr,
                        geometry,
                        crop=True,
                        filled=False
                    )

                except ValueError:

                    results.append({
                        "cell_id": cell_id,
                        "mean_los_m": np.nan,
                        "median_los_m": np.nan,
                        "mean_los_mm": np.nan,
                        "median_los_mm": np.nan,
                        "mean_correlation": np.nan,
                        "valid_pixel_count": 0,
                        "total_pixel_count": 0,
                        "valid_percentage": 0.0,
                        "quality_flag": "NO_DATA"
                    })

                    continue

                # --------------------------------------------
                # CONVERT MASKED ARRAYS TO NORMAL ARRAYS
                # --------------------------------------------

                los = np.ma.filled(
                    los_data[0],
                    np.nan
                ).astype("float64")

                corr = np.ma.filled(
                    corr_data[0],
                    np.nan
                ).astype("float64")

                # --------------------------------------------
                # BOTH ARRAYS MUST NOW HAVE SAME SHAPE
                # --------------------------------------------

                if los.shape != corr.shape:

                    raise RuntimeError(
                        f"Grid alignment error for cell "
                        f"{cell_id}: "
                        f"LOS={los.shape}, "
                        f"CORR={corr.shape}"
                    )

                total_pixels = los.size

                # --------------------------------------------
                # VALID PIXELS
                #
                # Zero LOS IS VALID after reference correction.
                # --------------------------------------------

                valid = (
                    np.isfinite(los)
                    &
                    np.isfinite(corr)
                    &
                    (corr >= CORRELATION_THRESHOLD)
                )

                los_values = los[valid]
                corr_values = corr[valid]

                valid_count = len(
                    los_values
                )

                if total_pixels > 0:

                    valid_percentage = (
                        valid_count /
                        total_pixels *
                        100
                    )

                else:

                    valid_percentage = 0.0

                # --------------------------------------------
                # QUALITY FLAG
                # --------------------------------------------

                if valid_count == 0:

                    quality = "NO_DATA"

                elif valid_percentage < MIN_VALID_PERCENTAGE:

                    quality = "LOW_COVERAGE"

                else:

                    quality = "VALID"

                # --------------------------------------------
                # STATISTICS
                # --------------------------------------------

                if valid_count > 0:

                    mean_los = float(
                        np.mean(los_values)
                    )

                    median_los = float(
                        np.median(los_values)
                    )

                    mean_corr = float(
                        np.mean(corr_values)
                    )

                else:

                    mean_los = np.nan
                    median_los = np.nan
                    mean_corr = np.nan

                results.append({

                    "cell_id": cell_id,

                    "mean_los_m": mean_los,

                    "median_los_m": median_los,

                    "mean_los_mm": (
                        mean_los * 1000
                        if np.isfinite(mean_los)
                        else np.nan
                    ),

                    "median_los_mm": (
                        median_los * 1000
                        if np.isfinite(median_los)
                        else np.nan
                    ),

                    "mean_correlation": mean_corr,

                    "valid_pixel_count": valid_count,

                    "total_pixel_count": total_pixels,

                    "valid_percentage": valid_percentage,

                    "quality_flag": quality
                })


# ============================================================
# DATAFRAME
# ============================================================

df = pd.DataFrame(results)


# ============================================================
# SAVE
# ============================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\nExtraction complete.")

print(
    "Output:",
    OUTPUT_FILE
)

print("\nQuality summary:")

print(
    df["quality_flag"].value_counts()
)

print("\nValid percentage:")

print(
    "Min  :",
    df["valid_percentage"].min()
)

print(
    "Max  :",
    df["valid_percentage"].max()
)

print(
    "Mean :",
    df["valid_percentage"].mean()
)

valid_df = df[
    df["quality_flag"] == "VALID"
]

if len(valid_df) > 0:

    print(
        "\nVALID cells:",
        len(valid_df)
    )

    print(
        "Mean LOS (mm):",
        valid_df["mean_los_mm"].mean()
    )

    print(
        "Mean correlation:",
        valid_df["mean_correlation"].mean()
    )

print("\n" + "=" * 70)
print("PAIR 02 GRID EXTRACTION COMPLETE")
print("=" * 70)