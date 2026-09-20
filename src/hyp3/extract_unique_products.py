
from pathlib import Path
import csv
import re
import zipfile
import shutil


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REGISTRY_FILE = (
    PROJECT_ROOT
    / "config"
    / "hyp3_job_registry.csv"
)

ZIP_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hyp3"
)

EXTRACT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hyp3"
    / "extracted_unique"
)

INVENTORY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hyp3"
    / "product_inventory_unique.csv"
)


# ------------------------------------------------------------
# Extract YYYYMMDD from a Sentinel scene ID
# ------------------------------------------------------------

def scene_date(scene):

    matches = re.findall(
        r"\d{8}T\d{6}",
        scene
    )

    if not matches:
        return None

    return matches[0][:8]


# ------------------------------------------------------------
# Extract the first two acquisition dates from a HyP3 ZIP
# ------------------------------------------------------------

def zip_dates(filename):

    matches = re.findall(
        r"\d{8}T\d{6}",
        filename
    )

    if len(matches) < 2:
        return None, None

    return (
        matches[0][:8],
        matches[1][:8]
    )


# ------------------------------------------------------------
# Identify raster type
# ------------------------------------------------------------

def raster_type(filename):

    name = filename.lower()

    if name.endswith("_amp.tif"):
        return "amplitude"

    if name.endswith("_corr.tif"):
        return "coherence"

    if name.endswith("_dem.tif"):
        return "dem"

    # Check ellipsoid incidence first
    if name.endswith("_inc_map_ell.tif"):
        return "incidence_angle_ell"

    if name.endswith("_inc_map.tif"):
        return "incidence_angle"

    if name.endswith("_los_disp.tif"):
        return "los_displacement"

    if name.endswith("_lv_phi.tif"):
        return "look_vector_phi"

    if name.endswith("_lv_theta.tif"):
        return "look_vector_theta"

    if name.endswith("_unw_phase.tif"):
        return "unwrapped_phase"

    if name.endswith("_vert_disp.tif"):
        return "vertical_displacement"

    if name.endswith("_water_mask.tif"):
        return "water_mask"

    return None


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    print("=" * 70)
    print("AUTOMATED UNIQUE HyP3 PRODUCT EXTRACTION")
    print("=" * 70)

    # --------------------------------------------------------
    # Load cleaned HyP3 registry
    # --------------------------------------------------------

    with open(
        REGISTRY_FILE,
        "r",
        encoding="utf-8",
        newline=""
    ) as f:

        registry = list(
            csv.DictReader(f)
        )

    print(
        f"Registry jobs : {len(registry)}"
    )

    # --------------------------------------------------------
    # Build automatic acquisition-pair lookup
    #
    # Key = reference acquisition date + secondary date
    # --------------------------------------------------------

    registry_pairs = {}

    for row in registry:

        reference_scene = row.get(
            "reference_scene",
            ""
        ).strip()

        secondary_scene = row.get(
            "secondary_scene",
            ""
        ).strip()

        reference_date = scene_date(
            reference_scene
        )

        secondary_date = scene_date(
            secondary_scene
        )

        if not reference_date or not secondary_date:

            print(
                "WARNING: Could not read dates:"
            )
            print(
                reference_scene
            )

            continue

        pair_key = (
            reference_date,
            secondary_date
        )

        registry_pairs[pair_key] = row

    print(
        f"Valid registry pairs : {len(registry_pairs)}"
    )

    # --------------------------------------------------------
    # Find every ZIP automatically
    # --------------------------------------------------------

    zip_files = sorted(
        ZIP_DIR.glob("*.zip")
    )

    print(
        f"ZIP files discovered : {len(zip_files)}"
    )

    # --------------------------------------------------------
    # Automatically match ZIPs to registry pairs
    # --------------------------------------------------------

    matched = {}

    ignored_duplicates = []

    unmatched_zips = []

    for zip_path in zip_files:

        reference_date, secondary_date = zip_dates(
            zip_path.name
        )

        if not reference_date or not secondary_date:

            unmatched_zips.append(
                zip_path
            )

            continue

        pair_key = (
            reference_date,
            secondary_date
        )

        # ----------------------------------------------------
        # ZIP belongs to one of our retained registry pairs
        # ----------------------------------------------------

        if pair_key in registry_pairs:

            # First ZIP for this acquisition pair wins.
            if pair_key not in matched:

                matched[pair_key] = zip_path

            else:

                ignored_duplicates.append(
                    zip_path
                )

        # ----------------------------------------------------
        # ZIP is not part of the current automated registry
        # ----------------------------------------------------

        else:

            unmatched_zips.append(
                zip_path
            )

    # --------------------------------------------------------
    # Print matching result
    # --------------------------------------------------------

    print()
    print("-" * 70)
    print("AUTOMATIC MATCHING SUMMARY")
    print("-" * 70)

    print(
        f"Registry pairs        : {len(registry_pairs)}"
    )

    print(
        f"Matched unique ZIPs   : {len(matched)}"
    )

    print(
        f"Duplicate ZIPs ignored: {len(ignored_duplicates)}"
    )

    print(
        f"Unrelated ZIPs ignored: {len(unmatched_zips)}"
    )

    # --------------------------------------------------------
    # Print duplicate products
    # --------------------------------------------------------

    if ignored_duplicates:

        print()
        print("DUPLICATE ZIP PRODUCTS")
        print("-" * 70)

        for path in ignored_duplicates:

            ref_date, sec_date = zip_dates(
                path.name
            )

            print(
                f"{ref_date} -> {sec_date}"
            )
            print(
                f"  Ignored: {path.name}"
            )

    # --------------------------------------------------------
    # Verify every registry pair has a product
    # --------------------------------------------------------

    missing_pairs = []

    for pair_key in registry_pairs:

        if pair_key not in matched:

            missing_pairs.append(
                pair_key
            )

    print()
    print(
        f"Missing registry products: {len(missing_pairs)}"
    )

    if missing_pairs:

        print()
        print(
            "ERROR: Some retained HyP3 jobs have no matching ZIP."
        )

        for ref_date, sec_date in missing_pairs:

            print(
                f"  {ref_date} -> {sec_date}"
            )

        print()
        print(
            "Extraction stopped for safety."
        )

        return

    # --------------------------------------------------------
    # Recreate clean extraction directory
    # --------------------------------------------------------

    if EXTRACT_DIR.exists():

        shutil.rmtree(
            EXTRACT_DIR
        )

    EXTRACT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Extract only the automatically selected unique products
    # --------------------------------------------------------

    inventory = []

    product_number = 0

    for pair_key in sorted(
        matched
    ):

        zip_path = matched[pair_key]

        registry_row = registry_pairs[
            pair_key
        ]

        product_number += 1

        product_id = (
            f"P{product_number:03d}"
        )

        product_dir = (
            EXTRACT_DIR
            / product_id
        )

        product_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        print()
        print("-" * 70)

        print(
            f"{product_id}: {zip_path.name}"
        )

        with zipfile.ZipFile(
            zip_path,
            "r"
        ) as archive:

            raster_count = 0

            for member in archive.namelist():

                if not member.lower().endswith(
                    ".tif"
                ):

                    continue

                raster_name = Path(
                    member
                ).name

                output_path = (
                    product_dir
                    / raster_name
                )

                with archive.open(
                    member
                ) as source:

                    with open(
                        output_path,
                        "wb"
                    ) as target:

                        shutil.copyfileobj(
                            source,
                            target
                        )

                rtype = raster_type(
                    raster_name
                )

                if rtype:

                    raster_count += 1

                    inventory.append(
                        {
                            "product_id":
                                product_id,

                            "job_id":
                                registry_row.get(
                                    "job_id",
                                    ""
                                ),

                            "reference_scene":
                                registry_row.get(
                                    "reference_scene",
                                    ""
                                ),

                            "secondary_scene":
                                registry_row.get(
                                    "secondary_scene",
                                    ""
                                ),

                            "reference_date":
                                registry_row.get(
                                    "reference_date",
                                    ""
                                ),

                            "secondary_date":
                                registry_row.get(
                                    "secondary_date",
                                    ""
                                ),

                            "orbit_direction":
                                registry_row.get(
                                    "orbit_direction",
                                    ""
                                ),

                            "relative_orbit":
                                registry_row.get(
                                    "relative_orbit",
                                    ""
                                ),

                            "reference_frame":
                                registry_row.get(
                                    "reference_frame",
                                    ""
                                ),

                            "secondary_frame":
                                registry_row.get(
                                    "secondary_frame",
                                    ""
                                ),

                            "zip_file":
                                zip_path.name,

                            "raster_type":
                                rtype,

                            "raster_file":
                                raster_name,

                            "raster_path":
                                str(
                                    output_path
                                )
                        }
                    )

        print(
            f"Raster files found : {raster_count}"
        )

    # --------------------------------------------------------
    # Save clean inventory
    # --------------------------------------------------------

    fieldnames = [
        "product_id",
        "job_id",
        "reference_scene",
        "secondary_scene",
        "reference_date",
        "secondary_date",
        "orbit_direction",
        "relative_orbit",
        "reference_frame",
        "secondary_frame",
        "zip_file",
        "raster_type",
        "raster_file",
        "raster_path"
    ]

    with open(
        INVENTORY_FILE,
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(
            inventory
        )

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    print(
        f"Registry pairs       : {len(registry_pairs)}"
    )

    print(
        f"Unique products      : {len(matched)}"
    )

    print(
        f"Duplicate ZIPs       : {len(ignored_duplicates)}"
    )

    print(
        f"Unrelated ZIPs       : {len(unmatched_zips)}"
    )

    print(
        f"Raster records       : {len(inventory)}"
    )

    print(
        f"Inventory             : {INVENTORY_FILE}"
    )

    if len(matched) == len(registry_pairs):

        print()
        print(
            "SUCCESS"
        )

        print(
            "All retained HyP3 jobs have exactly one "
            "automatically selected product."
        )

        print(
            "The pipeline is ready for spatial processing."
        )

    else:

        print()
        print(
            "WARNING: Product count does not match registry."
        )


if __name__ == "__main__":
    main()

