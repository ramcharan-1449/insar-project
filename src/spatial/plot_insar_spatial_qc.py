from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

QC_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_spatial_qc_test_pair_01.geojson"
)

AOI_FILE = (
    PROJECT_ROOT
    / "config"
    / "mine_aoi_projected.geojson"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid"
    / "insar_spatial_qc_test_pair_01.png"
)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("=" * 70)
    print("          INSAR SPATIAL QC MAP")
    print("=" * 70)

    # -----------------------------------------------------
    # LOAD DATA
    # -----------------------------------------------------

    qc = gpd.read_file(QC_FILE)
    aoi = gpd.read_file(AOI_FILE)

    print(f"\nQC cells : {len(qc)}")
    print(f"AOI features : {len(aoi)}")
    print(f"QC CRS : {qc.crs}")
    print(f"AOI CRS : {aoi.crs}")

    # -----------------------------------------------------
    # MAKE SURE CRS MATCHES
    # -----------------------------------------------------

    if qc.crs != aoi.crs:
        aoi = aoi.to_crs(qc.crs)

    # -----------------------------------------------------
    # SEPARATE QUALITY CLASSES
    # -----------------------------------------------------

    valid = qc[qc["quality_flag"] == "VALID"]
    low_coverage = qc[qc["quality_flag"] == "LOW_COVERAGE"]

    print(f"\nVALID cells       : {len(valid)}")
    print(f"LOW_COVERAGE cells: {len(low_coverage)}")

    # -----------------------------------------------------
    # CREATE FIGURE
    # -----------------------------------------------------

    fig, ax = plt.subplots(figsize=(10, 8))

    # Low coverage cells
    low_coverage.plot(
        ax=ax,
        color="lightgray",
        edgecolor="black",
        linewidth=0.2,
        label="Low coverage"
    )

    # Valid cells with median LOS displacement
    valid.plot(
        ax=ax,
        column="median_los_disp_mm",
        cmap="viridis",
        legend=True,
        edgecolor="black",
        linewidth=0.2,
        legend_kwds={
            "label": "Median LOS displacement (mm)",
            "shrink": 0.7
        }
    )

    # AOI boundary
    aoi.boundary.plot(
        ax=ax,
        color="red",
        linewidth=2,
        label="AOI boundary"
    )

    # -----------------------------------------------------
    # TITLE AND LABELS
    # -----------------------------------------------------

    ax.set_title(
        "Shyamsundarpur Colliery\n"
        "InSAR Spatial QC — Test Pair 01",
        fontsize=14
    )

    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")

    ax.legend()

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    plt.tight_layout()

    plt.savefig(
        OUTPUT_FILE,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close()

    print("\nMap created successfully.")
    print(f"Output: {OUTPUT_FILE}")

    print("\n" + "=" * 70)
    print("             SPATIAL QC MAP COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()