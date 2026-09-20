from pathlib import Path
import json
import re

import numpy as np
import pandas as pd
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

HYP3_DIR = (
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
    / "insar_grid_features_all_pairs.csv"
)


# ============================================================
# SETTINGS
# ============================================================

MIN_COHERENCE = 0.50
MIN_COVERAGE = 0.10


# ============================================================
# DATE EXTRACTION
# ============================================================

def extract_pair_key(product_dir):

    # Dates are stored in the HyP3 TIFF filename,
    # not in the P01/P02/... folder name.

    los_file = find_los_file(product_dir)

    if los_file is None:
        return None, None, None

    text = los_file.name

    # Example:
    # S1AA_20240123T121315_20240204T121314_..._los_disp.tif

    dates = re.findall(
        r"20\d{6}",
        text
    )

    if len(dates) < 2:
        return None, None, None

    reference_date = dates[0]
    secondary_date = dates[1]

    pair_key = (
        f"{reference_date}_{secondary_date}"
    )

    return (
        pair_key,
        reference_date,
        secondary_date
    )


# ============================================================
# FIND LOS FILE
# ============================================================

def find_los_file(product_dir):

    files = list(
        product_dir.glob("*_los_disp.tif")
    )

    if not files:
        return None

    return files[0]


# ============================================================
# FIND CORRELATION FILE
# ============================================================

def find_corr_file(product_dir):

    files = list(
        product_dir.glob("*_corr.tif")
    )

    if not files:
        return None

    return files[0]


# ============================================================
# VALID RASTER VALUES
# ============================================================

def clean_values(array, nodata):

    values = array.astype(
        np.float64,
        copy=False
    )

    invalid = ~np.isfinite(values)

    if nodata is not None:
        invalid |= np.isclose(
            values,
            nodata
        )

    values = values[~invalid]

    return values


# ============================================================
# CELL EXTRACTION
# ============================================================

def extract_cell_statistics(
    dataset,
    cell_geometry,
    corr_dataset=None
):

    try:

        # ----------------------------------------------------
        # LOS
        # ----------------------------------------------------

        los_data, _ = mask(
            dataset,
            [mapping(cell_geometry)],
            crop=True,
            filled=True,
            nodata=np.nan
        )

        los = los_data[0]

        # ----------------------------------------------------
        # Correlation
        # ----------------------------------------------------

        if corr_dataset is not None:

            corr_data, _ = mask(
                corr_dataset,
                [mapping(cell_geometry)],
                crop=True,
                filled=True,
                nodata=np.nan
            )

            corr = corr_data[0]

        else:

            corr = None

        # ----------------------------------------------------
        # LOS VALID PIXELS
        # ----------------------------------------------------

        los_valid = clean_values(
            los,
            dataset.nodata
        )

        # Number of pixels represented by the
        # raster mask for this cell
        total_pixels = los.size

        if total_pixels == 0:

            return {
                "los_displacement_m": np.nan,
                "los_median_m": np.nan,
                "los_std_m": np.nan,
                "mean_coherence": np.nan,
                "coverage_fraction": 0.0,
                "quality_flag": "NO_DATA"
            }

        coverage_fraction = (
            len(los_valid)
            /
            total_pixels
        )

        if len(los_valid) == 0:

            return {
                "los_displacement_m": np.nan,
                "los_median_m": np.nan,
                "los_std_m": np.nan,
                "mean_coherence": np.nan,
                "coverage_fraction": coverage_fraction,
                "quality_flag": "NO_DATA"
            }

        # ----------------------------------------------------
        # LOS STATISTICS
        # ----------------------------------------------------

        los_mean = float(
            np.mean(los_valid)
        )

        los_median = float(
            np.median(los_valid)
        )

        los_std = float(
            np.std(los_valid)
        )

        # ----------------------------------------------------
        # COHERENCE
        # ----------------------------------------------------

        if corr is not None:

            corr_valid = clean_values(
                corr,
                corr_dataset.nodata
            )

            if len(corr_valid) > 0:

                mean_coherence = float(
                    np.mean(corr_valid)
                )

            else:

                mean_coherence = np.nan

        else:

            mean_coherence = np.nan

        # ----------------------------------------------------
        # QUALITY FLAG
        # ----------------------------------------------------

        if coverage_fraction < MIN_COVERAGE:

            quality = "LOW_COVERAGE"

        elif (
            np.isfinite(mean_coherence)
            and
            mean_coherence < MIN_COHERENCE
        ):

            quality = "LOW_CORRELATION"

        else:

            quality = "VALID"

        return {
            "los_displacement_m": los_mean,
            "los_median_m": los_median,
            "los_std_m": los_std,
            "mean_coherence": mean_coherence,
            "coverage_fraction": coverage_fraction,
            "quality_flag": quality
        }

    except Exception:

        return {
            "los_displacement_m": np.nan,
            "los_median_m": np.nan,
            "los_std_m": np.nan,
            "mean_coherence": np.nan,
            "coverage_fraction": 0.0,
            "quality_flag": "NO_DATA"
        }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("       INSAR GRID SPATIAL FEATURE EXTRACTION")
    print("=" * 70)

    # --------------------------------------------------------
    # LOAD GRID
    # --------------------------------------------------------

    print("\nLoading mine grid...")

    grid = gpd.read_file(
        GRID_FILE
    )

    print(
        f"Grid cells : {len(grid)}"
    )

    print(
        f"Grid CRS   : {grid.crs}"
    )

    # --------------------------------------------------------
    # FIND PRODUCTS
    # --------------------------------------------------------

    product_dirs = sorted(
        [
            p for p in HYP3_DIR.iterdir()
            if p.is_dir()
            and p.name.startswith("P")
        ],
        key=lambda p: int(
            re.search(
                r"\d+",
                p.name
            ).group()
        )
    )

    print(
        f"Product folders found : "
        f"{len(product_dirs)}"
    )

    # --------------------------------------------------------
    # DISCOVER UNIQUE PAIRS
    # --------------------------------------------------------

    pair_products = {}

    for product_dir in product_dirs:

        product_id = product_dir.name

        pair_key, ref_date, sec_date = (
            extract_pair_key(product_dir)
        )

        if pair_key is None:

            print(
                f"SKIP {product_id}: "
                f"could not determine dates"
            )

            continue

        los_file = find_los_file(
            product_dir
        )

        if los_file is None:

            print(
                f"SKIP {product_id}: "
                f"LOS displacement missing"
            )

            continue

        if pair_key not in pair_products:

            pair_products[pair_key] = {
                "product_id": product_id,
                "product_dir": product_dir,
                "reference_date": ref_date,
                "secondary_date": sec_date
            }

        else:

            existing = pair_products[
                pair_key
            ]["product_id"]

            print(
                f"DUPLICATE: {pair_key} "
                f"-> keeping {existing}, "
                f"skipping {product_id}"
            )

    print(
        f"\nUnique acquisition pairs : "
        f"{len(pair_products)}"
    )

    # --------------------------------------------------------
    # EXTRACT
    # --------------------------------------------------------

    output_rows = []

    for pair_key in sorted(
        pair_products.keys()
    ):

        info = pair_products[
            pair_key
        ]

        product_id = info[
            "product_id"
        ]

        product_dir = info[
            "product_dir"
        ]

        reference_date = info[
            "reference_date"
        ]

        secondary_date = info[
            "secondary_date"
        ]

        los_file = find_los_file(
            product_dir
        )

        corr_file = find_corr_file(
            product_dir
        )

        print(
            f"\nProcessing {product_id}: "
            f"{reference_date} -> "
            f"{secondary_date}"
        )

        print(
            f"  LOS : {los_file.name}"
        )

        if corr_file:

            print(
                f"  CORR: {corr_file.name}"
            )

        else:

            print(
                "  CORR: not available"
            )

        # ----------------------------------------------------
        # OPEN RASTERS
        # ----------------------------------------------------

        with rasterio.open(
            los_file
        ) as los_dataset:

            if corr_file:

                corr_dataset = (
                    rasterio.open(
                        corr_file
                    )
                )

            else:

                corr_dataset = None

            # ------------------------------------------------
            # CRS CHECK
            # ------------------------------------------------

            if grid.crs != los_dataset.crs:

                print(
                    "  Reprojecting grid "
                    "to raster CRS..."
                )

                grid_for_product = (
                    grid.to_crs(
                        los_dataset.crs
                    )
                )

            else:

                grid_for_product = grid

            # ------------------------------------------------
            # CELL LOOP
            # ------------------------------------------------

            for _, cell in (
                grid_for_product.iterrows()
            ):

                statistics = (
                    extract_cell_statistics(
                        los_dataset,
                        cell.geometry,
                        corr_dataset
                    )
                )

                output_rows.append({

                    "product_id":
                        product_id,

                    "pair_key":
                        pair_key,

                    "reference_date":
                        reference_date,

                    "secondary_date":
                        secondary_date,

                    "cell_id":
                        cell["cell_id"],

                    "los_displacement_m":
                        statistics[
                            "los_displacement_m"
                        ],

                    "los_median_m":
                        statistics[
                            "los_median_m"
                        ],

                    "los_std_m":
                        statistics[
                            "los_std_m"
                        ],

                    "mean_coherence":
                        statistics[
                            "mean_coherence"
                        ],

                    "coverage_fraction":
                        statistics[
                            "coverage_fraction"
                        ],

                    "quality_flag":
                        statistics[
                            "quality_flag"
                        ]
                })

            if corr_dataset:

                corr_dataset.close()

    # --------------------------------------------------------
    # CREATE DATAFRAME
    # --------------------------------------------------------

    df = pd.DataFrame(
        output_rows
    )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    df = df.sort_values(
        [
            "product_id",
            "cell_id"
        ]
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # SAVE
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
    # VALIDATION SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("STAGE 9 COMPLETE")
    print("=" * 70)

    print(
        f"Unique products : "
        f"{df['product_id'].nunique()}"
    )

    print(
        f"Grid cells      : "
        f"{df['cell_id'].nunique()}"
    )

    print(
        f"Feature rows    : "
        f"{len(df)}"
    )

    print(
        f"Unique pairs    : "
        f"{df['pair_key'].nunique()}"
    )

    print("\nQuality flags:")

    print(
        df["quality_flag"]
        .value_counts()
        .to_string()
    )

    print("\nSpatial variation check:")

    for pair_key in sorted(
        df["pair_key"].unique()
    ):

        subset = df[
            df["pair_key"] == pair_key
        ]

        unique_los = (
            subset[
                "los_displacement_m"
            ]
            .nunique()
        )

        print(
            f"  {pair_key}: "
            f"{unique_los} unique LOS "
            f"values across "
            f"{len(subset)} cells"
        )

    print("\nOutput:")
    print(OUTPUT_FILE)

    print("=" * 70)


if __name__ == "__main__":
    main()
