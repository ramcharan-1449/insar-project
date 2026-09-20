from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

AOI_FILE = (
    PROJECT_ROOT
    / "config"
    / "mine_aoi_projected.geojson"
)

LOS_FILE = next(
    (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "hyp3"
        / "test_pair_01"
        / "S1AA_20240123T121315_20240204T121314_VVP012_INT80_G_ueF_96C4"
    ).glob("*_los_disp.tif")
)

CORR_FILE = next(
    (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "hyp3"
        / "test_pair_01"
        / "S1AA_20240123T121315_20240204T121314_VVP012_INT80_G_ueF_96C4"
    ).glob("*_corr.tif")
)


# ---------------------------------------------------------
# PARAMETERS
# ---------------------------------------------------------

CORRELATION_THRESHOLD = 0.5

# Reference candidate should have strong coherence
REFERENCE_CORRELATION_THRESHOLD = 0.7

# Ignore zero displacement values because HyP3 uses
# zero as NoData in this product.
VALID_DISPLACEMENT_MIN = -np.inf
VALID_DISPLACEMENT_MAX = np.inf


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("=" * 70)
    print("             INSAR REFERENCE CANDIDATE ANALYSIS")
    print("=" * 70)

    # -----------------------------------------------------
    # Read AOI
    # -----------------------------------------------------

    aoi = gpd.read_file(AOI_FILE)

    print("\nAOI CRS:", aoi.crs)

    # -----------------------------------------------------
    # Read LOS displacement
    # -----------------------------------------------------

    with rasterio.open(LOS_FILE) as los_src:

        los_data, los_transform = mask(
            los_src,
            aoi.geometry,
            crop=True
        )

        los = los_data[0]

        print("LOS CRS:", los_src.crs)
        print(
            "LOS resolution:",
            los_src.res
        )

        print(
            "AOI raster shape:",
            los.shape
        )

        nodata = los_src.nodata

    # -----------------------------------------------------
    # Read correlation
    # -----------------------------------------------------

    with rasterio.open(CORR_FILE) as corr_src:

        corr_data, _ = mask(
            corr_src,
            aoi.geometry,
            crop=True
        )

        corr = corr_data[0]

    # -----------------------------------------------------
    # Build valid mask
    # -----------------------------------------------------

    valid = (
        np.isfinite(los)
        & np.isfinite(corr)
        & (corr >= CORRELATION_THRESHOLD)
    )

    if nodata is not None:
        valid &= los != nodata

    # HyP3 product uses zero as NoData for LOS displacement.
    valid &= los != 0

    print("\nValid pixels:", int(valid.sum()))

    if valid.sum() == 0:
        raise ValueError(
            "No valid pixels found."
        )

    # -----------------------------------------------------
    # Candidate reference mask
    # -----------------------------------------------------

    reference_candidates = (
        valid
        & (corr >= REFERENCE_CORRELATION_THRESHOLD)
    )

    candidate_count = int(
        reference_candidates.sum()
    )

    print(
        "Reference candidates:",
        candidate_count
    )

    if candidate_count == 0:
        raise ValueError(
            "No reference candidates found."
        )

    # -----------------------------------------------------
    # Candidate statistics
    # -----------------------------------------------------

    candidate_los = los[reference_candidates]
    candidate_corr = corr[reference_candidates]

    print("\nReference candidate statistics:")

    print(
        f"LOS mean   : "
        f"{candidate_los.mean():.6f} m"
    )

    print(
        f"LOS median : "
        f"{np.median(candidate_los):.6f} m"
    )

    print(
        f"LOS std    : "
        f"{candidate_los.std():.6f} m"
    )

    print(
        f"Corr mean  : "
        f"{candidate_corr.mean():.6f}"
    )

    print(
        f"Corr median: "
        f"{np.median(candidate_corr):.6f}"
    )

    # -----------------------------------------------------
    # Robust reference estimate
    # -----------------------------------------------------

    reference_los = float(
        np.median(candidate_los)
    )

    reference_corr = float(
        np.median(candidate_corr)
    )

    print("\n----------------------------------------")

    print(
        f"Reference LOS estimate: "
        f"{reference_los:.6f} m"
    )

    print(
        f"Reference LOS estimate: "
        f"{reference_los * 1000:.3f} mm"
    )

    print(
        f"Reference correlation: "
        f"{reference_corr:.4f}"
    )

    print("----------------------------------------")

    # -----------------------------------------------------
    # Calculate relative displacement
    # -----------------------------------------------------

    relative_los = (
        los - reference_los
    )

    relative_valid = relative_los[valid]

    print("\nRelative LOS statistics:")

    print(
        f"Minimum: "
        f"{relative_valid.min():.6f} m"
    )

    print(
        f"Maximum: "
        f"{relative_valid.max():.6f} m"
    )

    print(
        f"Mean: "
        f"{relative_valid.mean():.6f} m"
    )

    print(
        f"Median: "
        f"{np.median(relative_valid):.6f} m"
    )

    print(
        f"Std: "
        f"{relative_valid.std():.6f} m"
    )

    print(
        f"\nRelative displacement range: "
        f"{relative_valid.min() * 1000:.2f} to "
        f"{relative_valid.max() * 1000:.2f} mm"
    )

    # -----------------------------------------------------
    # QC interpretation
    # -----------------------------------------------------

    print("\nQC interpretation:")

    if reference_corr >= 0.7:
        print(
            "✓ Reference candidate coherence is strong."
        )
    else:
        print(
            "⚠ Reference candidate coherence is weak."
        )

    if valid.sum() > 0:
        print(
            "✓ Valid InSAR pixels are available."
        )

    print(
        "\nIMPORTANT:"
    )

    print(
        "This is a reference CANDIDATE estimate."
    )

    print(
        "It should be scientifically reviewed before "
        "being declared the final reference."
    )

    print("=" * 70)


if __name__ == "__main__":
    main()
    