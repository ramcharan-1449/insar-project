
from pathlib import Path
import json
import re

import geopandas as gpd
import pandas as pd
import numpy as np
import rasterio
from rasterstats import zonal_stats
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

with (PROJECT_ROOT / "config" / "grid_config.json").open(encoding="utf-8") as stream:
    GRID_CONFIG = json.load(stream)

GRID_FILE = PROJECT_ROOT / "data" / "processed" / "grid" / GRID_CONFIG["grid_filename"]

INVENTORY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hyp3"
    / "product_inventory_unique.csv"
)

SCENE_INVENTORY_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_scene_inventory_auto.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
)

OUTPUT_FILE = OUTPUT_DIR / "insar_grid_features.csv"


# ============================================================
# LAYER TYPES
# ============================================================

raster_typeS = [
    "los_displacement",
    "vertical_displacement",
    "unwrapped_phase",
    "coherence",
    "incidence_angle",
    "amplitude",
    "dem",
]


# ============================================================
# EXTRACT DATES FROM HYP3 PRODUCT NAME
# ============================================================

def extract_dates(filename):

    pattern = r"(\d{8})T\d{6}.*?(\d{8})T\d{6}"

    match = re.search(pattern, filename)

    if match:

        reference_date = pd.to_datetime(
            match.group(1),
            format="%Y%m%d"
        )

        secondary_date = pd.to_datetime(
            match.group(2),
            format="%Y%m%d"
        )

        temporal_days = (
            secondary_date - reference_date
        ).days

        return (
            reference_date.date(),
            secondary_date.date(),
            temporal_days,
        )

    return None, None, None


# ============================================================
# DETERMINE EXACT LAYER NAME
# ============================================================

def get_layer_prefix(raster_type, raster_path):

    filename = raster_path.name.lower()

    if raster_type == "incidence_angle":

        if "_inc_map_ell" in filename:
            return "incidence_angle_ell"

        return "incidence_angle"

    return raster_type


# ============================================================
# EXTRACT SCENE DATES FROM HYP3 ZIP NAME
# ============================================================

def extract_scene_dates(filename):

    pattern = r"(\d{8})T\d{6}.*?(\d{8})T\d{6}"

    match = re.search(pattern, filename)

    if not match:
        return None, None

    reference_date = pd.to_datetime(
        match.group(1),
        format="%Y%m%d"
    )

    secondary_date = pd.to_datetime(
        match.group(2),
        format="%Y%m%d"
    )

    return reference_date, secondary_date


# ============================================================
# FIND SENTINEL-1 SCENE METADATA
# ============================================================

def find_scene_metadata(
    scene_inventory,
    target_date,
    target_time=None
):

    candidates = scene_inventory[
        scene_inventory["acquisition_date_dt"].dt.date
        == target_date.date()
    ].copy()

    if candidates.empty:
        return None

    # If time is available, select the closest acquisition.
    if target_time is not None:

        target_seconds = (
            target_time.hour * 3600
            + target_time.minute * 60
            + target_time.second
        )

        candidates["time_difference"] = (
            candidates["seconds_of_day"]
            - target_seconds
        ).abs()

        candidates = candidates.sort_values(
            "time_difference"
        )

    return candidates.iloc[0]


# ============================================================
# EXTRACT EXACT TIMES FROM HYP3 ZIP NAME
# ============================================================

def extract_scene_times(filename):

    pattern = r"(\d{8})T(\d{6}).*?(\d{8})T(\d{6})"

    match = re.search(pattern, filename)

    if not match:
        return None, None

    reference_time = pd.to_datetime(
        match.group(1) + match.group(2),
        format="%Y%m%d%H%M%S"
    )

    secondary_time = pd.to_datetime(
        match.group(3) + match.group(4),
        format="%Y%m%d%H%M%S"
    )

    return reference_time, secondary_time


# ============================================================
# ATTACH SENTINEL-1 METADATA
# ============================================================

def attach_scene_metadata(
    result,
    zip_file,
    scene_inventory
):

    reference_time, secondary_time = (
        extract_scene_times(zip_file)
    )

    if reference_time is None:

        print(
            "  WARNING: Could not extract "
            "scene times from product."
        )

        result["orbit_direction"] = np.nan
        result["relative_orbit"] = np.nan
        result["reference_frame"] = np.nan
        result["secondary_frame"] = np.nan

        return result

    # --------------------------------------------------------
    # FIND REFERENCE SCENE
    # --------------------------------------------------------

    reference_metadata = find_scene_metadata(
        scene_inventory,
        reference_time,
        reference_time
    )

    # --------------------------------------------------------
    # FIND SECONDARY SCENE
    # --------------------------------------------------------

    secondary_metadata = find_scene_metadata(
        scene_inventory,
        secondary_time,
        secondary_time
    )

    if reference_metadata is None:

        print(
            f"  WARNING: Reference scene metadata "
            f"not found for {reference_time}"
        )

    if secondary_metadata is None:

        print(
            f"  WARNING: Secondary scene metadata "
            f"not found for {secondary_time}"
        )

    # --------------------------------------------------------
    # DEFAULT VALUES
    # --------------------------------------------------------

    orbit_direction = np.nan
    relative_orbit = np.nan
    reference_frame = np.nan
    secondary_frame = np.nan

    # --------------------------------------------------------
    # REFERENCE METADATA
    # --------------------------------------------------------

    if reference_metadata is not None:

        orbit_direction = (
            reference_metadata["orbit_direction"]
        )

        relative_orbit = (
            reference_metadata["relative_orbit"]
        )

        reference_frame = (
            reference_metadata["frame"]
        )

    # --------------------------------------------------------
    # SECONDARY METADATA
    # --------------------------------------------------------

    if secondary_metadata is not None:

        secondary_frame = (
            secondary_metadata["frame"]
        )

        # Verify consistency.
        if reference_metadata is not None:

            if (
                reference_metadata["orbit_direction"]
                != secondary_metadata["orbit_direction"]
            ):

                print(
                    "  WARNING: Orbit direction mismatch "
                    "between reference and secondary."
                )

            if (
                int(reference_metadata["relative_orbit"])
                != int(secondary_metadata["relative_orbit"])
            ):

                print(
                    "  WARNING: Relative orbit mismatch "
                    "between reference and secondary."
                )

    # --------------------------------------------------------
    # ATTACH
    # --------------------------------------------------------

    result["orbit_direction"] = orbit_direction
    result["relative_orbit"] = relative_orbit
    result["reference_frame"] = reference_frame
    result["secondary_frame"] = secondary_frame

    return result


# ============================================================
# CALCULATE TOTAL PIXELS COVERED BY EACH GRID CELL
# ============================================================

def calculate_coverage_pixel_counts(
    raster_path,
    grid
):

    counts = []

    with rasterio.open(raster_path) as src:

        raster_crs = src.crs

        if raster_crs is None:
            raise ValueError(
                f"No CRS found: {raster_path.name}"
            )

        grid_for_raster = grid.to_crs(
            raster_crs
        )

        for geometry in grid_for_raster.geometry:

            bounds = geometry.bounds

            window = from_bounds(
                bounds[0],
                bounds[1],
                bounds[2],
                bounds[3],
                transform=src.transform,
            )

            window = (
                window
                .round_offsets()
                .round_lengths()
            )

            if (
                window.width <= 0
                or window.height <= 0
            ):

                counts.append(0)

                continue

            window_transform = (
                src.window_transform(window)
            )

            mask = geometry_mask(
                [geometry],
                transform=window_transform,
                invert=True,
                all_touched=True,
                out_shape=(
                    int(window.height),
                    int(window.width),
                ),
            )

            counts.append(
                int(mask.sum())
            )

    return counts


# ============================================================
# SAFE ZONAL STATISTICS
# ============================================================

def calculate_stats(
    raster_path,
    grid
):

    with rasterio.open(raster_path) as src:

        raster_crs = src.crs

        if raster_crs is None:
            raise ValueError(
                f"No CRS found: {raster_path.name}"
            )

        grid_for_raster = grid.to_crs(
            raster_crs
        )

        nodata = src.nodata

    stats = zonal_stats(
        grid_for_raster,
        str(raster_path),
        stats=[
            "mean",
            "median",
            "std",
            "count",
            "min",
            "max",
        ],
        nodata=nodata,
        all_touched=True,
    )

    return stats


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print(
        "Stage 6.5 - Corrected InSAR Spatial Grid "
        "Feature Extraction"
    )
    print("=" * 70)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # LOAD GRID
    # --------------------------------------------------------

    print()
    print("Loading mine grid...")

    grid = gpd.read_file(
        GRID_FILE
    )

    print(
        f"Grid cells : {len(grid)}"
    )

    print(
        f"Grid CRS   : {grid.crs}"
    )

    if len(grid) != 293:

        print(
            "WARNING: Expected 293 cells, "
            f"found {len(grid)}."
        )

    # --------------------------------------------------------
    # LOAD HYP3 INVENTORY
    # --------------------------------------------------------

    print()
    print("Loading HyP3 inventory...")

    inventory = pd.read_csv(
        INVENTORY_FILE
    )

    print(
        f"Inventory records : "
        f"{len(inventory)}"
    )

    inventory = inventory[
        inventory["raster_type"].isin(
            raster_typeS
        )
    ].copy()

    print(
        f"Scientific rasters : "
        f"{len(inventory)}"
    )

    # --------------------------------------------------------
    # LOAD SENTINEL-1 SCENE INVENTORY
    # --------------------------------------------------------

    print()
    print(
        "Loading Sentinel-1 scene inventory..."
    )

    scene_inventory = pd.read_csv(
        SCENE_INVENTORY_FILE
    )

    print(
        f"Sentinel-1 scenes : "
        f"{len(scene_inventory)}"
    )

    required_scene_columns = [
        "scene_id",
        "acquisition_date",
        "orbit_direction",
        "relative_orbit",
        "frame",
    ]

    missing_scene_columns = [
        column
        for column in required_scene_columns
        if column not in scene_inventory.columns
    ]

    if missing_scene_columns:

        raise ValueError(
            "Sentinel-1 scene inventory is missing "
            f"columns: {missing_scene_columns}"
        )

    scene_inventory[
        "acquisition_date_dt"
    ] = pd.to_datetime(
        scene_inventory[
            "acquisition_date"
        ],
        utc=True
    )

    scene_inventory[
        "seconds_of_day"
    ] = (
        scene_inventory[
            "acquisition_date_dt"
        ].dt.hour * 3600
        + scene_inventory[
            "acquisition_date_dt"
        ].dt.minute * 60
        + scene_inventory[
            "acquisition_date_dt"
        ].dt.second
    )

    # --------------------------------------------------------
    # GROUP BY PRODUCT
    # --------------------------------------------------------

    product_groups = inventory.groupby(
        "product_id"
    )

    print(
        f"HyP3 products : "
        f"{len(product_groups)}"
    )

    all_results = []

    # --------------------------------------------------------
    # PROCESS EACH PRODUCT
    # --------------------------------------------------------

    for product_number, (
        product_id,
        product_df
    ) in enumerate(
        product_groups,
        start=1
    ):

        print()
        print("-" * 70)

        print(
            f"{product_number}: "
            f"{product_id}"
        )

        zip_file = (
            product_df.iloc[0]["zip_file"]
        )

        reference_date, secondary_date, temporal_days = (
            extract_dates(zip_file)
        )

        print(
            f"Reference date : "
            f"{reference_date}"
        )

        print(
            f"Secondary date : "
            f"{secondary_date}"
        )

        print(
            f"Temporal days  : "
            f"{temporal_days}"
        )

        # ----------------------------------------------------
        # START WITH GRID IDS
        # ----------------------------------------------------

        result = pd.DataFrame({

            "cell_id":
                grid["cell_id"]
                if "cell_id" in grid.columns
                else np.arange(
                    1,
                    len(grid) + 1
                )
        })

        result["product_id"] = product_id

        result["zip_file"] = zip_file

        result["reference_date"] = (
            reference_date
        )

        result["secondary_date"] = (
            secondary_date
        )

        result["temporal_baseline_days"] = (
            temporal_days
        )

        # ----------------------------------------------------
        # ATTACH SENTINEL-1 METADATA
        # ----------------------------------------------------

        result = attach_scene_metadata(
            result,
            zip_file,
            scene_inventory
        )

        print(
            f"  Orbit direction: "
            f"{result['orbit_direction'].iloc[0]}"
        )

        print(
            f"  Relative orbit : "
            f"{result['relative_orbit'].iloc[0]}"
        )

        print(
            f"  Reference frame: "
            f"{result['reference_frame'].iloc[0]}"
        )

        print(
            f"  Secondary frame: "
            f"{result['secondary_frame'].iloc[0]}"
        )

        # ----------------------------------------------------
        # PROCESS EACH RASTER
        # ----------------------------------------------------

        for _, row in product_df.iterrows():

            raster_type = row[
                "raster_type"
            ]

            raster_path = (
                PROJECT_ROOT
                / row["raster_path"]
            )

            if not raster_path.exists():

                print(
                    f"  WARNING: Missing "
                    f"{raster_path}"
                )

                continue

            prefix = get_layer_prefix(
                raster_type,
                raster_path
            )

            print(
                f"  Processing: "
                f"{prefix}"
            )

            try:

                stats = calculate_stats(
                    raster_path,
                    grid
                )

                result[
                    f"{prefix}_mean"
                ] = [
                    s["mean"]
                    for s in stats
                ]

                result[
                    f"{prefix}_median"
                ] = [
                    s["median"]
                    for s in stats
                ]

                result[
                    f"{prefix}_std"
                ] = [
                    s["std"]
                    for s in stats
                ]

                result[
                    f"{prefix}_min"
                ] = [
                    s["min"]
                    for s in stats
                ]

                result[
                    f"{prefix}_max"
                ] = [
                    s["max"]
                    for s in stats
                ]

                result[
                    f"{prefix}_valid_pixel_count"
                ] = [
                    s["count"]
                    for s in stats
                ]

            except Exception as e:

                print(
                    f"  ERROR processing "
                    f"{prefix}: {e}"
                )

        # ----------------------------------------------------
        # VALID PIXEL FRACTION
        # ----------------------------------------------------

        if (
            "coherence_valid_pixel_count"
            in result
        ):

            try:

                coherence_rows = product_df[
                    product_df[
                        "raster_type"
                    ] == "coherence"
                ]

                if not coherence_rows.empty:

                    coherence_path = (
                        PROJECT_ROOT
                        / coherence_rows.iloc[0][
                            "raster_path"
                        ]
                    )

                else:

                    coherence_path = (
                        PROJECT_ROOT
                        / product_df.iloc[0][
                            "raster_path"
                        ]
                    )

                coverage_counts = (
                    calculate_coverage_pixel_counts(
                        coherence_path,
                        grid
                    )
                )

                coverage_counts = np.array(
                    coverage_counts,
                    dtype=float
                )

                valid_counts = pd.to_numeric(
                    result[
                        "coherence_valid_pixel_count"
                    ],
                    errors="coerce"
                ).to_numpy(
                    dtype=float
                )

                result[
                    "valid_pixel_fraction"
                ] = np.where(
                    coverage_counts > 0,
                    valid_counts
                    / coverage_counts,
                    np.nan
                )

                result[
                    "valid_pixel_fraction"
                ] = result[
                    "valid_pixel_fraction"
                ].clip(
                    lower=0.0,
                    upper=1.0
                )

            except Exception as e:

                print(
                    "  WARNING: Could not calculate "
                    f"valid_pixel_fraction: {e}"
                )

                result[
                    "valid_pixel_fraction"
                ] = np.nan

        else:

            result[
                "valid_pixel_fraction"
            ] = np.nan

        all_results.append(
            result
        )

    # --------------------------------------------------------
    # COMBINE
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "Combining spatial results..."
    )
    print("=" * 70)

    if not all_results:

        print(
            "ERROR: No results generated."
        )

        return

    final_df = pd.concat(
        all_results,
        ignore_index=True
    )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    final_df = final_df.sort_values(
        [
            "reference_date",
            "secondary_date",
            "product_id",
            "cell_id",
        ]
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    final_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "STAGE 6.5 SUMMARY"
    )
    print("=" * 70)

    print(
        f"Products processed : "
        f"{len(all_results)}"
    )

    print(
        f"Grid cells/product : "
        f"{len(grid)}"
    )

    print(
        f"Final rows         : "
        f"{len(final_df)}"
    )

    print(
        f"Final columns      : "
        f"{len(final_df.columns)}"
    )

    print(
        f"Output             : "
        f"{OUTPUT_FILE}"
    )

    print()

    print(
        "Expected rows if "
        "31 products × 293 cells:"
    )

    print(
        31 * len(grid)
    )

    print()

    print(
        "Metadata completeness:"
    )

    print(
        "  Missing orbit direction : "
        f"{final_df['orbit_direction'].isna().sum()}"
    )

    print(
        "  Missing relative orbit  : "
        f"{final_df['relative_orbit'].isna().sum()}"
    )

    print(
        "  Missing reference frame : "
        f"{final_df['reference_frame'].isna().sum()}"
    )

    print(
        "  Missing secondary frame : "
        f"{final_df['secondary_frame'].isna().sum()}"
    )

    print()

    print(
        "Incidence angle fields:"
    )

    for column in final_df.columns:

        if column.startswith(
            "incidence_angle"
        ):

            print(
                f"  {column}"
            )

    print()

    print(
        "Stage 6.5 completed."
    )


if __name__ == "__main__":
    main()

