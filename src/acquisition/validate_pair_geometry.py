from pathlib import Path
import pandas as pd
import json
import asf_search as asf
from shapely.geometry import shape
from datetime import datetime, timezone


# ============================================================
# STAGE 2.6 — FRAME / PLATFORM / AOI VALIDATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PAIR_FILE = PROJECT_ROOT / "config" / "sentinel1_final_pairs.csv"

OUTPUT_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_final_pairs_geometry_validated.csv"
)

REPORT_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_pair_geometry_report.csv"
)

AOI_FILE = PROJECT_ROOT / "config" / "mine_aoi.geojson"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def load_aoi_wkt():

    with open(AOI_FILE, "r", encoding="utf-8") as f:
        aoi = json.load(f)

    geometry = shape(
        aoi["features"][0]["geometry"]
    )

    return geometry.wkt


def get_scene_name(row, column):

    value = row.get(column)

    if pd.isna(value):
        return None

    return str(value)


def get_property(product, *names):

    """
    Return the first available ASF metadata property.
    """

    if product is None:
        return None

    properties = getattr(
        product,
        "properties",
        {}
    )

    for name in names:

        value = properties.get(name)

        if value is not None:
            return value

    return None


def normalize_direction(value):

    """
    Normalize ASF orbit-direction values.
    """

    if value is None:
        return None

    value = str(value).strip().upper()

    if value in [
        "ASC",
        "ASCENDING"
    ]:
        return "ASCENDING"

    if value in [
        "DESC",
        "DESCENDING"
    ]:
        return "DESCENDING"

    return value


def get_orbit_direction(product):

    """
    Try several ASF metadata properties.
    """

    value = get_property(
        product,
        "orbitDirection",
        "orbit_direction",
        "flightDirection",
        "flight_direction",
        "passDirection",
        "pass_direction",
        "orbitProperties_passDirection"
    )

    return normalize_direction(value)


def get_scene_geometry(product):

    """
    Safely obtain product geometry if ASF exposes it.
    """

    if product is None:
        return None

    properties = getattr(
        product,
        "properties",
        {}
    )

    geometry = getattr(
        product,
        "geometry",
        None
    )

    if geometry is not None:
        return geometry

    return properties.get(
        "geometry"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("STAGE 2.6 — FRAME / PLATFORM / AOI VALIDATION")
    print("=" * 70)

    # --------------------------------------------------------
    # Check input files
    # --------------------------------------------------------

    if not PAIR_FILE.exists():

        raise FileNotFoundError(
            f"Pair file not found:\n{PAIR_FILE}"
        )

    if not AOI_FILE.exists():

        raise FileNotFoundError(
            f"AOI file not found:\n{AOI_FILE}"
        )

    pairs = pd.read_csv(
        PAIR_FILE
    )

    print(
        f"\nPairs to validate: {len(pairs)}"
    )

    print(
        "\nSearching ASF for pair scene metadata..."
    )

    aoi_wkt = load_aoi_wkt()

    # --------------------------------------------------------
    # Collect required scene names
    # --------------------------------------------------------

    scene_names = set()

    for _, row in pairs.iterrows():

        ref = get_scene_name(
            row,
            "reference_scene"
        )

        sec = get_scene_name(
            row,
            "secondary_scene"
        )

        if ref:
            scene_names.add(ref)

        if sec:
            scene_names.add(sec)

    print(
        f"Unique scenes required: {len(scene_names)}"
    )

    # --------------------------------------------------------
    # ASF SEARCH
    # --------------------------------------------------------

    end_date = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT23:59:59Z"
    )

    results = asf.search(
        platform="SENTINEL-1",
        processingLevel="SLC",
        beamMode="IW",
        intersectsWith=aoi_wkt,
        start="2024-01-01T00:00:00Z",
        end=end_date,
        maxResults=5000
    )

    # --------------------------------------------------------
    # Build scene lookup
    # --------------------------------------------------------

    scene_map = {}

    for product in results:

        scene_name = get_property(
            product,
            "sceneName",
            "scene_name"
        )

        if scene_name:

            scene_map[
                str(scene_name)
            ] = product

    print(
        f"ASF scenes retrieved: {len(scene_map)}"
    )

    # --------------------------------------------------------
    # Check requested scenes
    # --------------------------------------------------------

    missing_scenes = []

    for scene_name in scene_names:

        if scene_name not in scene_map:

            missing_scenes.append(
                scene_name
            )

    print(
        f"Requested scenes found: "
        f"{len(scene_names) - len(missing_scenes)}"
    )

    print(
        f"Requested scenes missing: "
        f"{len(missing_scenes)}"
    )

    if missing_scenes:

        print(
            "\nWARNING — Missing scenes:"
        )

        for scene in missing_scenes:

            print(
                f"  {scene}"
            )

    # ========================================================
    # VALIDATION
    # ========================================================

    validation_rows = []

    accepted = []

    for _, row in pairs.iterrows():

        ref_name = get_scene_name(
            row,
            "reference_scene"
        )

        sec_name = get_scene_name(
            row,
            "secondary_scene"
        )

        ref_product = scene_map.get(
            ref_name
        )

        sec_product = scene_map.get(
            sec_name
        )

        # ----------------------------------------------------
        # Scene existence
        # ----------------------------------------------------

        ref_found = (
            ref_product is not None
        )

        sec_found = (
            sec_product is not None
        )

        # ----------------------------------------------------
        # Platform
        # ----------------------------------------------------

        ref_platform = get_property(
            ref_product,
            "platform",
            "platformName",
            "platformname"
        )

        sec_platform = get_property(
            sec_product,
            "platform",
            "platformName",
            "platformname"
        )

        platform_ok = (
            ref_platform is not None
            and sec_platform is not None
            and str(ref_platform).upper()
            == str(sec_platform).upper()
        )

        # ----------------------------------------------------
        # Relative orbit
        # ----------------------------------------------------

        ref_orbit = get_property(
            ref_product,
            "relativeOrbit",
            "relativeOrbitNumber",
            "pathNumber"
        )

        sec_orbit = get_property(
            sec_product,
            "relativeOrbit",
            "relativeOrbitNumber",
            "pathNumber"
        )

        relative_orbit_ok = (
            ref_orbit is not None
            and sec_orbit is not None
            and str(ref_orbit)
            == str(sec_orbit)
        )

        # ----------------------------------------------------
        # Frame
        # ----------------------------------------------------

        ref_frame = get_property(
            ref_product,
            "frameNumber",
            "frame",
            "frame_number"
        )

        sec_frame = get_property(
            sec_product,
            "frameNumber",
            "frame",
            "frame_number"
        )

        frame_ok = (
            ref_frame is not None
            and sec_frame is not None
            and str(ref_frame)
            == str(sec_frame)
        )

        # ----------------------------------------------------
        # Orbit direction
        # ----------------------------------------------------

        ref_direction = get_orbit_direction(
            ref_product
        )

        sec_direction = get_orbit_direction(
            sec_product
        )

        orbit_direction_ok = (
            ref_direction is not None
            and sec_direction is not None
            and ref_direction == sec_direction
        )

        # ----------------------------------------------------
        # AOI intersection
        # ----------------------------------------------------

        aoi_ok = (
            ref_found
            and sec_found
        )

        # ----------------------------------------------------
        # Final decision
        # ----------------------------------------------------

        approved = all([
            ref_found,
            sec_found,
            platform_ok,
            relative_orbit_ok,
            frame_ok,
            orbit_direction_ok,
            aoi_ok
        ])

        if approved:

            decision = (
                "APPROVED_FOR_HYP3"
            )

            accepted.append(row)

        else:

            decision = (
                "REVIEW_REQUIRED"
            )

        # ----------------------------------------------------
        # Store result
        # ----------------------------------------------------

        validation_rows.append({

            "reference_scene":
                ref_name,

            "secondary_scene":
                sec_name,

            "reference_platform":
                ref_platform,

            "secondary_platform":
                sec_platform,

            "platform_check":
                platform_ok,

            "reference_relative_orbit":
                ref_orbit,

            "secondary_relative_orbit":
                sec_orbit,

            "relative_orbit_check":
                relative_orbit_ok,

            "reference_frame":
                ref_frame,

            "secondary_frame":
                sec_frame,

            "frame_check":
                frame_ok,

            "reference_orbit_direction":
                ref_direction,

            "secondary_orbit_direction":
                sec_direction,

            "orbit_direction_check":
                orbit_direction_ok,

            "reference_found":
                ref_found,

            "secondary_found":
                sec_found,

            "aoi_intersection_check":
                aoi_ok,

            "decision":
                decision
        })

    # ========================================================
    # SAVE VALIDATION REPORT
    # ========================================================

    report_df = pd.DataFrame(
        validation_rows
    )

    report_df.to_csv(
        REPORT_FILE,
        index=False
    )

    # ========================================================
    # SAVE APPROVED PAIRS
    # ========================================================

    if accepted:

        final_df = pd.DataFrame(
            accepted
        )

        final_df.to_csv(
            OUTPUT_FILE,
            index=False
        )

    else:

        final_df = pd.DataFrame(
            columns=pairs.columns
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    print("\n" + "=" * 70)
    print("GEOMETRY VALIDATION COMPLETE")
    print("=" * 70)

    print(
        f"\nTotal pairs        : {len(pairs)}"
    )

    print(
        f"Approved for HyP3 : {len(final_df)}"
    )

    print(
        f"Review required    : "
        f"{len(pairs) - len(final_df)}"
    )

    print("\nOutput files:")

    print(
        f"  {OUTPUT_FILE}"
    )

    print(
        f"  {REPORT_FILE}"
    )

    # ========================================================
    # DETAILED RESULTS
    # ========================================================

    print(
        "\nPair validation:"
    )

    for _, r in report_df.iterrows():

        print(
            f"\n{r['reference_scene']}"
        )

        print(
            f"  -> {r['secondary_scene']}"
        )

        print(
            f"  Platform : "
            f"{r['reference_platform']} / "
            f"{r['secondary_platform']}"
        )

        print(
            f"  Orbit    : "
            f"{r['reference_relative_orbit']} / "
            f"{r['secondary_relative_orbit']}"
        )

        print(
            f"  Frame    : "
            f"{r['reference_frame']} / "
            f"{r['secondary_frame']}"
        )

        print(
            f"  Direction: "
            f"{r['reference_orbit_direction']} / "
            f"{r['secondary_orbit_direction']}"
        )

        print(
            f"  Decision : "
            f"{r['decision']}"
        )

    # ========================================================
    # AOI NOTE
    # ========================================================

    print(
        "\nAOI note:"
    )

    print(
        "  AOI validation confirms scene intersection only."
    )

    print(
        "  It does NOT prove complete AOI coverage."
    )

    # ========================================================
    # HYP3 GATE
    # ========================================================

    print(
        "\nHyP3 submission: NOT PERFORMED"
    )

    print("=" * 70)


if __name__ == "__main__":

    main()