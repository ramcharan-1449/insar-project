from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GRID_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "mine_grid_coverage.geojson"
)

HYP3_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hyp3"
    / "test_pair_01"
    / "S1AA_20240123T121315_20240204T121314_VVP012_INT80_G_ueF_96C4"
)

LOS_FILE = next(HYP3_DIR.glob("*_los_disp.tif"))
CORR_FILE = next(HYP3_DIR.glob("*_corr.tif"))

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "spatial_features_test_pair_01.csv"
)


# ============================================================
# SETTINGS
# ============================================================

# Minimum percentage of valid InSAR pixels required
# for a cell to be considered usable.
MIN_VALID_PERCENTAGE = 30.0

# Correlation threshold used only for the quality flag.
# This is a project-level starting value, not a universal law.
CORRELATION_THRESHOLD = 0.5


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("       INSAR → GRID SPATIAL FEATURE EXTRACTION")
    print("=" * 70)

    print("\nGrid file:")
    print(GRID_FILE)

    print("\nLOS displacement:")
    print(LOS_FILE)

    print("\nCorrelation:")
    print(CORR_FILE)

    # --------------------------------------------------------
    # Load grid
    # --------------------------------------------------------

    print("\nLoading grid...")

    grid = gpd.read_file(GRID_FILE)

    print(f"Grid cells: {len(grid)}")
    print(f"Grid CRS  : {grid.crs}")

    # --------------------------------------------------------
    # Open LOS raster
    # --------------------------------------------------------

    with rasterio.open(LOS_FILE) as los_src:

        print("\nLOS raster:")
        print(f"CRS        : {los_src.crs}")
        print(f"Resolution : {los_src.res}")
        print(f"Width      : {los_src.width}")
        print(f"Height     : {los_src.height}")

        # Reproject grid if required
        if grid.crs != los_src.crs:
            print("\nCRS mismatch detected.")
            print("Reprojecting grid to LOS raster CRS...")

            grid_for_raster = grid.to_crs(los_src.crs)

        else:
            grid_for_raster = grid.copy()

        # ----------------------------------------------------
        # Open correlation raster
        # ----------------------------------------------------

        with rasterio.open(CORR_FILE) as corr_src:

            if corr_src.crs != los_src.crs:
                raise ValueError(
                    "LOS and correlation rasters have different CRS."
                )

            results = []

            # ------------------------------------------------
            # Process every grid cell
            # ------------------------------------------------

            print("\nProcessing grid cells...")

            for index, row in grid_for_raster.iterrows():

                cell_id = row["cell_id"]
                geometry = row.geometry

                try:

                    # Extract LOS pixels inside this cell
                    los_data, _ = mask(
                        los_src,
                        [geometry],
                        crop=True,
                        filled=True,
                        nodata=0
                    )

                    # Extract correlation pixels
                    corr_data, _ = mask(
                        corr_src,
                        [geometry],
                        crop=True,
                        filled=True,
                        nodata=0
                    )

                    los_values = los_data[0]
                    corr_values = corr_data[0]

                    total_pixel_count = los_values.size

                    # HyP3 uses 0 as NoData for these float rasters.
                    valid_mask = (
                        np.isfinite(los_values)
                        & np.isfinite(corr_values)
                        & (los_values != 0)
                        & (corr_values > 0)
                    )

                    valid_los = los_values[valid_mask]
                    valid_corr = corr_values[valid_mask]

                    valid_pixel_count = len(valid_los)

                    if total_pixel_count > 0:
                        valid_percentage = (
                            valid_pixel_count
                            / total_pixel_count
                            * 100
                        )
                    else:
                        valid_percentage = 0.0

                    # ----------------------------------------
                    # Calculate statistics
                    # ----------------------------------------

                    if valid_pixel_count > 0:

                        mean_los = float(np.mean(valid_los))
                        median_los = float(np.median(valid_los))

                        mean_corr = float(np.mean(valid_corr))

                        mean_los_mm = mean_los * 1000.0
                        median_los_mm = median_los * 1000.0

                    else:

                        mean_los = np.nan
                        median_los = np.nan
                        mean_corr = np.nan

                        mean_los_mm = np.nan
                        median_los_mm = np.nan

                    # ----------------------------------------
                    # Quality flag
                    # ----------------------------------------

                    if valid_pixel_count == 0:

                        quality_flag = "NO_DATA"

                    elif valid_percentage < MIN_VALID_PERCENTAGE:

                        quality_flag = "LOW_COVERAGE"

                    elif mean_corr < CORRELATION_THRESHOLD:

                        quality_flag = "LOW_CORRELATION"

                    else:

                        quality_flag = "VALID"

                    results.append(
                        {
                            "cell_id": cell_id,

                            "mean_los_disp_m": mean_los,
                            "median_los_disp_m": median_los,

                            "mean_los_disp_mm": mean_los_mm,
                            "median_los_disp_mm": median_los_mm,

                            "mean_correlation": mean_corr,

                            "valid_pixel_count": valid_pixel_count,
                            "total_pixel_count": total_pixel_count,

                            "valid_pixel_percentage": valid_percentage,

                            "quality_flag": quality_flag,
                        }
                    )

                except Exception as error:

                    print(
                        f"WARNING: Could not process cell {cell_id}: "
                        f"{error}"
                    )

                    results.append(
                        {
                            "cell_id": cell_id,

                            "mean_los_disp_m": np.nan,
                            "median_los_disp_m": np.nan,

                            "mean_los_disp_mm": np.nan,
                            "median_los_disp_mm": np.nan,

                            "mean_correlation": np.nan,

                            "valid_pixel_count": 0,
                            "total_pixel_count": 0,

                            "valid_pixel_percentage": 0.0,

                            "quality_flag": "ERROR",
                        }
                    )

    # --------------------------------------------------------
    # Create DataFrame
    # --------------------------------------------------------

    df = pd.DataFrame(results)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)

    print(f"\nTotal grid cells : {len(df)}")

    print("\nQuality summary:")
    print(df["quality_flag"].value_counts())

    print("\nValid pixel percentage:")
    print(
        f"Minimum : {df['valid_pixel_percentage'].min():.2f}%"
    )
    print(
        f"Maximum : {df['valid_pixel_percentage'].max():.2f}%"
    )
    print(
        f"Mean    : {df['valid_pixel_percentage'].mean():.2f}%"
    )

    print("\nMedian LOS displacement:")
    print(
        f"Minimum : {df['median_los_disp_m'].min():.6f} m"
    )
    print(
        f"Maximum : {df['median_los_disp_m'].max():.6f} m"
    )
    print(
        f"Mean    : {df['median_los_disp_m'].mean():.6f} m"
    )

    print("\nOutput:")
    print(OUTPUT_FILE)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()