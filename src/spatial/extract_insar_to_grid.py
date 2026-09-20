from pathlib import Path
import json
import csv

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

with (PROJECT_ROOT / "config" / "grid_config.json").open(encoding="utf-8") as stream:
    GRID_CONFIG = json.load(stream)

GRID_FILE = PROJECT_ROOT / "data" / "processed" / "grid" / GRID_CONFIG["grid_filename"]

EXTRACTED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hyp3"
    / "extracted"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_spatial_features.csv"
)


# ============================================================
# SETTINGS
# ============================================================

# Automated products only
PRODUCT_IDS = [
    "P04",
    "P05",
    "P06",
    "P07",
    "P08",
    "P09",
    "P10",
    "P11",
    "P12",
]

# Minimum number of valid 80 m pixels needed
# for a useful grid-cell observation.
MIN_VALID_PIXELS = 1

# Coherence threshold used only for QC classification.
# We do NOT discard low-coherence observations here.
COHERENCE_THRESHOLD = 0.50


# ============================================================
# FUNCTIONS
# ============================================================

def find_single_file(product_dir, pattern):

    files = list(product_dir.glob(pattern))

    if len(files) == 0:
        return None

    if len(files) > 1:
        print(
            f"WARNING: Multiple files found for "
            f"{pattern} in {product_dir.name}"
        )

    return files[0]


def read_grid_cell(src, geometry):

    try:

        data, _ = mask(
            src,
            [mapping(geometry)],
            crop=True,
            filled=False
        )

    except ValueError:

        return np.array([], dtype=float)

    values = data[0]

    if np.ma.isMaskedArray(values):

        values = values.compressed()

    else:

        values = values.ravel()

    values = values.astype(float)

    values = values[
        np.isfinite(values)
    ]

    if src.nodata is not None:

        values = values[
            values != src.nodata
        ]

    return values


# ============================================================
# LOAD GRID
# ============================================================

print("=" * 70)
print("STAGE 9 - INSAR EXTRACTION TO 100 m GRID")
print("=" * 70)

print()
print(f"Grid: {GRID_FILE}")
print(f"Products: {', '.join(PRODUCT_IDS)}")
print()


grid = gpd.read_file(GRID_FILE)


if grid.empty:

    print("ERROR: Grid is empty.")
    raise SystemExit(1)


if grid.crs is None:

    print("ERROR: Grid has no CRS.")
    raise SystemExit(1)


if grid.crs.to_string() != "EPSG:32645":

    print(
        f"ERROR: Expected EPSG:32645, "
        f"got {grid.crs}"
    )

    raise SystemExit(1)


print(
    f"Grid cells: {len(grid)}"
)

print(
    f"Grid CRS  : {grid.crs}"
)

print()


# ============================================================
# OUTPUT RECORDS
# ============================================================

records = []


# ============================================================
# PROCESS PRODUCTS
# ============================================================

for product_id in PRODUCT_IDS:

    product_dir = EXTRACTED_DIR / product_id

    print("-" * 70)
    print(f"PROCESSING {product_id}")

    if not product_dir.exists():

        print(
            f"ERROR: Product directory not found: "
            f"{product_dir}"
        )

        continue


    # --------------------------------------------------------
    # Find layers
    # --------------------------------------------------------

    los_file = find_single_file(
        product_dir,
        "*_los_disp.tif"
    )

    corr_file = find_single_file(
        product_dir,
        "*_corr.tif"
    )

    phase_file = find_single_file(
        product_dir,
        "*_unw_phase.tif"
    )


    if los_file is None:

        print("LOS displacement: MISSING")
        print("Skipping product.")

        continue


    if corr_file is None:

        print("Coherence: MISSING")
        print("Skipping product.")

        continue


    if phase_file is None:

        print("Unwrapped phase: MISSING")
        print("Skipping product.")

        continue


    print(
        f"LOS   : {los_file.name}"
    )

    print(
        f"Corr  : {corr_file.name}"
    )

    print(
        f"Phase : {phase_file.name}"
    )


    # --------------------------------------------------------
    # Open rasters
    # --------------------------------------------------------

    with rasterio.open(los_file) as los_src:

        with rasterio.open(corr_file) as corr_src:

            with rasterio.open(phase_file) as phase_src:


                # ------------------------------------------------
                # Basic alignment verification
                # ------------------------------------------------

                if (
                    los_src.crs != corr_src.crs
                    or los_src.crs != phase_src.crs
                    or los_src.transform != corr_src.transform
                    or los_src.transform != phase_src.transform
                    or los_src.width != corr_src.width
                    or los_src.width != phase_src.width
                    or los_src.height != corr_src.height
                    or los_src.height != phase_src.height
                ):

                    print(
                        "ERROR: Raster alignment mismatch."
                    )

                    continue


                # ------------------------------------------------
                # Product statistics
                # ------------------------------------------------

                product_valid = 0

                product_total = 0


                # ------------------------------------------------
                # Process each grid cell
                # ------------------------------------------------

                for index, row in grid.iterrows():

                    cell_id = row["cell_id"]

                    geometry = row.geometry


                    # --------------------------------------------
                    # Read pixels inside grid cell
                    # --------------------------------------------

                    los_values = read_grid_cell(
                        los_src,
                        geometry
                    )

                    corr_values = read_grid_cell(
                        corr_src,
                        geometry
                    )

                    phase_values = read_grid_cell(
                        phase_src,
                        geometry
                    )


                    # --------------------------------------------
                    # Valid LOS values
                    # --------------------------------------------

                    los_valid = (
                        np.isfinite(los_values)
                        & (los_values != 0)
                    )


                    valid_los = (
                        los_values[los_valid]
                    )


                    # --------------------------------------------
                    # Coherence values
                    # --------------------------------------------

                    corr_valid = corr_values[
                        np.isfinite(corr_values)
                    ]


                    # --------------------------------------------
                    # Phase values
                    # --------------------------------------------

                    phase_valid = phase_values[
                        np.isfinite(phase_values)
                    ]


                    # --------------------------------------------
                    # Calculate statistics
                    # --------------------------------------------

                    if len(valid_los) >= MIN_VALID_PIXELS:

                        los_mean_m = float(
                            np.mean(valid_los)
                        )

                        los_median_m = float(
                            np.median(valid_los)
                        )

                        los_std_m = float(
                            np.std(valid_los)
                        )

                    else:

                        los_mean_m = np.nan
                        los_median_m = np.nan
                        los_std_m = np.nan


                    if len(corr_valid) > 0:

                        coherence_mean = float(
                            np.mean(corr_valid)
                        )

                        coherence_median = float(
                            np.median(corr_valid)
                        )

                    else:

                        coherence_mean = np.nan
                        coherence_median = np.nan


                    if len(phase_valid) > 0:

                        phase_mean = float(
                            np.mean(phase_valid)
                        )

                        phase_median = float(
                            np.median(phase_valid)
                        )

                    else:

                        phase_mean = np.nan
                        phase_median = np.nan


                    # --------------------------------------------
                    # Pixel counts
                    # --------------------------------------------

                    valid_pixel_count = len(
                        valid_los
                    )

                    total_pixel_count = len(
                        los_values
                    )


                    if total_pixel_count > 0:

                        valid_pixel_percent = (
                            valid_pixel_count
                            / total_pixel_count
                            * 100
                        )

                    else:

                        valid_pixel_percent = 0.0


                    # --------------------------------------------
                    # QC classification
                    # --------------------------------------------

                    if valid_pixel_count == 0:

                        qc_status = "NO_DATA"

                    elif (
                        coherence_mean >=
                        COHERENCE_THRESHOLD
                    ):

                        qc_status = "VALID"

                    else:

                        qc_status = "LOW_COHERENCE"


                    # --------------------------------------------
                    # Update product counters
                    # --------------------------------------------

                    product_total += 1

                    if valid_pixel_count > 0:

                        product_valid += 1


                    # --------------------------------------------
                    # Save record
                    # --------------------------------------------

                    records.append({

                        "cell_id": cell_id,

                        "product_id": product_id,

                        "los_displacement_mean_mm":
                            (
                                los_mean_m * 1000
                                if np.isfinite(
                                    los_mean_m
                                )
                                else np.nan
                            ),

                        "los_displacement_median_mm":
                            (
                                los_median_m * 1000
                                if np.isfinite(
                                    los_median_m
                                )
                                else np.nan
                            ),

                        "los_displacement_std_mm":
                            (
                                los_std_m * 1000
                                if np.isfinite(
                                    los_std_m
                                )
                                else np.nan
                            ),

                        "coherence_mean":
                            coherence_mean,

                        "coherence_median":
                            coherence_median,

                        "unwrapped_phase_mean":
                            phase_mean,

                        "unwrapped_phase_median":
                            phase_median,

                        "valid_pixel_count":
                            valid_pixel_count,

                        "total_pixel_count":
                            total_pixel_count,

                        "valid_pixel_percent":
                            round(
                                valid_pixel_percent,
                                4
                            ),

                        "qc_status":
                            qc_status
                    })


    # --------------------------------------------------------
    # Product summary
    # --------------------------------------------------------

    print()
    print(
        f"Grid cells processed: "
        f"{product_total}"
    )

    print(
        f"Cells with valid LOS: "
        f"{product_valid}"
    )

    if product_total > 0:

        print(
            f"Spatial availability: "
            f"{product_valid / product_total * 100:.2f}%"
        )


# ============================================================
# WRITE CSV
# ============================================================

if not records:

    print()
    print("ERROR: No records generated.")
    raise SystemExit(1)


fieldnames = [
    "cell_id",
    "product_id",
    "los_displacement_mean_mm",
    "los_displacement_median_mm",
    "los_displacement_std_mm",
    "coherence_mean",
    "coherence_median",
    "unwrapped_phase_mean",
    "unwrapped_phase_median",
    "valid_pixel_count",
    "total_pixel_count",
    "valid_pixel_percent",
    "qc_status"
]


with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    for record in records:

        writer.writerow(record)


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("=" * 70)
print("STAGE 9 SUMMARY")
print("=" * 70)

print(
    f"Products requested : "
    f"{len(PRODUCT_IDS)}"
)

print(
    f"Records generated  : "
    f"{len(records)}"
)

print(
    f"Expected records   : "
    f"{len(grid) * len(PRODUCT_IDS)}"
)

print()
print(
    f"Output:"
)

print(OUTPUT_FILE)

print()
print("Stage 9 extraction complete.")
