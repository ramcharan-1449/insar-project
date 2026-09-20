import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio

from pathlib import Path
from rasterio.mask import mask
from rasterio.warp import reproject, Resampling


BASE = Path("data/processed/hyp3/test_pair_03")

GRID_FILE = Path(
    "data/processed/grid/mine_grid_coverage.geojson"
)

LOS_FILE = BASE / "pair_03_referenced_los_disp_aoi.tif"

CORR_FILE = next(
    BASE.rglob("*_corr.tif")
)

OUTPUT = Path(
    "data/processed/grid/"
    "spatial_features_test_pair_03.csv"
)

CORRELATION_THRESHOLD = 0.5
MIN_VALID_PERCENTAGE = 30.0


print("PAIR 03 GRID EXTRACTION")
print("=======================")

# --------------------------------------------------
# Read grid
# --------------------------------------------------

grid = gpd.read_file(GRID_FILE)

print("Grid cells:", len(grid))
print("Grid CRS:", grid.crs)


# --------------------------------------------------
# Read referenced LOS raster
# --------------------------------------------------

with rasterio.open(LOS_FILE) as los_src:

    grid = grid.to_crs(los_src.crs)

    los_aoi, los_transform = mask(
        los_src,
        grid.geometry,
        crop=True,
        nodata=np.nan
    )

    los_aoi = los_aoi[0]

    los_crs = los_src.crs

    print("LOS CRS:", los_crs)
    print("LOS AOI shape:", los_aoi.shape)


# --------------------------------------------------
# Read correlation raster
# and align it to LOS AOI grid
# --------------------------------------------------

with rasterio.open(CORR_FILE) as corr_src:

    corr_aoi = np.full(
        los_aoi.shape,
        np.nan,
        dtype=np.float32
    )

    reproject(
        source=rasterio.band(corr_src, 1),
        destination=corr_aoi,

        src_transform=corr_src.transform,
        src_crs=corr_src.crs,

        dst_transform=los_transform,
        dst_crs=los_crs,

        src_nodata=corr_src.nodata,
        dst_nodata=np.nan,

        resampling=Resampling.nearest
    )

print("Correlation aligned to LOS grid.")
print("Correlation shape:", corr_aoi.shape)


# --------------------------------------------------
# Check alignment
# --------------------------------------------------

if los_aoi.shape != corr_aoi.shape:

    raise ValueError(
        "LOS and correlation grids are still misaligned."
    )

print("Raster grids aligned successfully.")


# --------------------------------------------------
# Extract grid-cell statistics
# --------------------------------------------------

results = []

with rasterio.open(LOS_FILE) as los_src:

    for _, cell in grid.iterrows():

        cell_id = cell["cell_id"]

        geometry = [cell.geometry]

        # Extract LOS values
        los_values, _ = mask(
            los_src,
            geometry,
            crop=True,
            nodata=np.nan
        )

        los_values = los_values[0]

        # Create a temporary raster-like extraction
        # for correlation using the LOS grid geometry.
        #
        # Determine the pixel window of this cell.
        window = rasterio.features.geometry_window(
            los_src,
            geometry
        )

        row_start = window.row_off
        row_stop = window.row_off + window.height

        col_start = window.col_off
        col_stop = window.col_off + window.width

        # Convert global AOI-aligned correlation to cell
        # values using the corresponding LOS cell window.
        #
        # Because the referenced LOS file is already AOI-clipped,
        # use direct masking on the original correlation raster
        # in a separate aligned temporary workflow below.

        with rasterio.open(CORR_FILE) as corr_src:

            corr_values, _ = mask(
                corr_src,
                geometry,
                crop=True,
                nodata=np.nan
            )

        corr_values = corr_values[0]

        # If the independent mask crop differs by one row/column,
        # align correlation to LOS cell shape through nearest
        # resampling.

        if corr_values.shape != los_values.shape:

            corr_aligned = np.full(
                los_values.shape,
                np.nan,
                dtype=np.float32
            )

            # Build temporary transforms for both cropped arrays
            # using the original raster transforms.

            with rasterio.open(CORR_FILE) as corr_src:

                corr_transform = corr_src.window_transform(
                    rasterio.features.geometry_window(
                        corr_src,
                        geometry
                    )
                )

            with rasterio.open(LOS_FILE) as los_src2:

                los_transform_cell = (
                    los_src2.window_transform(window)
                )

                reproject(
                    source=corr_values,
                    destination=corr_aligned,

                    src_transform=corr_transform,
                    src_crs=los_crs,

                    dst_transform=los_transform_cell,
                    dst_crs=los_crs,

                    src_nodata=np.nan,
                    dst_nodata=np.nan,

                    resampling=Resampling.nearest
                )

            corr_values = corr_aligned

        # --------------------------------------------------
        # Quality filtering
        # --------------------------------------------------

        valid = (
            np.isfinite(los_values) &
            np.isfinite(corr_values) &
            (corr_values >= CORRELATION_THRESHOLD)
        )

        total_pixel_count = int(
            np.isfinite(corr_values).sum()
        )

        valid_pixel_count = int(
            valid.sum()
        )

        if total_pixel_count > 0:

            valid_percentage = (
                valid_pixel_count /
                total_pixel_count *
                100.0
            )

        else:

            valid_percentage = 0.0

        if valid_pixel_count == 0:

            quality = "NO_DATA"

            mean_los = np.nan
            median_los = np.nan
            mean_corr = np.nan

        else:

            values = los_values[valid]
            correlations = corr_values[valid]

            mean_los = float(
                np.mean(values)
            )

            median_los = float(
                np.median(values)
            )

            mean_corr = float(
                np.mean(correlations)
            )

            if valid_percentage < MIN_VALID_PERCENTAGE:

                quality = "LOW_COVERAGE"

            else:

                quality = "VALID"

        results.append(
            {
                "cell_id": cell_id,

                "mean_los_disp_m": mean_los,
                "median_los_disp_m": median_los,

                "mean_los_disp_mm": (
                    mean_los * 1000
                    if np.isfinite(mean_los)
                    else np.nan
                ),

                "median_los_disp_mm": (
                    median_los * 1000
                    if np.isfinite(median_los)
                    else np.nan
                ),

                "mean_correlation": mean_corr,

                "valid_pixel_count":
                    valid_pixel_count,

                "total_pixel_count":
                    total_pixel_count,

                "valid_pixel_percentage":
                    valid_percentage,

                "quality_flag":
                    quality
            }
        )


# --------------------------------------------------
# Save
# --------------------------------------------------

df = pd.DataFrame(results)

df.to_csv(
    OUTPUT,
    index=False
)


print()
print("Output:", OUTPUT)
print("Rows:", len(df))

print()
print("Quality:")
print(
    df["quality_flag"]
    .value_counts()
    .to_string()
)

print()
print(
    "Valid cells:",
    int(
        (df["quality_flag"] == "VALID").sum()
    )
)

print(
    "Mean valid percentage:",
    round(
        df["valid_pixel_percentage"].mean(),
        2
    )
)

print()
print("Pair 03 grid extraction complete.")