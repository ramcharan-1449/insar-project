from pathlib import Path
from datetime import datetime, timezone
import json
import math
import pandas as pd
import asf_search as asf
from shapely.geometry import shape


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PAIR_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_network_extension_pairs.csv"
)

AOI_FILE = (
    PROJECT_ROOT
    / "config"
    / "mine_aoi.geojson"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_network_pairs_validated.csv"
)

REPORT_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_network_validation_report.txt"
)


# ============================================================
# SCIENTIFIC THRESHOLDS
# ============================================================

MAX_TEMPORAL_DAYS = 24
GOOD_PERPENDICULAR_M = 200
ACCEPTABLE_PERPENDICULAR_M = 500


# ============================================================
# ASF SEARCH
# ============================================================

def load_aoi():

    with open(AOI_FILE, "r", encoding="utf-8") as f:

        aoi = json.load(f)

    geometry = shape(
        aoi["features"][0]["geometry"]
    )

    return geometry.wkt


def search_scene(scene_name, aoi_wkt):

    print(
        f"    Searching ASF: {scene_name}"
    )

    results = asf.search(
        platform="Sentinel-1",
        processingLevel="SLC",
        beamMode="IW",
        intersectsWith=aoi_wkt,
        start="2020-01-01",
        end=datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%dT23:59:59Z"),
    )

    for result in results:

        name = getattr(
            result,
            "properties",
            {}
        ).get("sceneName")

        if name == scene_name:
            return result

    return None


# ============================================================
# BASELINE
# ============================================================

def get_perpendicular_baseline(scene1, scene2):

    """
    Obtain perpendicular baseline from the ASF baseline stack.

    This follows the same method already working in
    pair_selector.py.
    """

    try:

        stack = scene1.stack()

    except Exception as e:

        print(
            f"    Baseline stack lookup failed: {e}"
        )

        return None

    if stack is None or len(stack) == 0:

        return None

    # --------------------------------------------------------
    # Build map of ASF stack products by scene name
    # --------------------------------------------------------

    stack_map = {}

    for product in stack:

        name = getattr(
            product,
            "sceneName",
            None
        )

        if name is None and hasattr(
            product,
            "properties"
        ):

            name = product.properties.get(
                "sceneName"
            )

        if name:

            stack_map[str(name)] = product

    # --------------------------------------------------------
    # Find secondary scene
    # --------------------------------------------------------

    secondary_name = (
        scene2.properties.get(
            "sceneName"
        )
    )

    stacked_secondary = stack_map.get(
        str(secondary_name)
    )

    if stacked_secondary is None:

        print(
            "    Secondary scene not found "
            "in ASF baseline stack."
        )

        return None

    # --------------------------------------------------------
    # Read perpendicular baseline
    # --------------------------------------------------------

    props = getattr(
        stacked_secondary,
        "properties",
        {}
    )

    perp = props.get(
        "perpendicularBaseline"
    )

    if perp is None:

        perp = props.get(
            "perpendicular_baseline"
        )

    # Some ASF objects expose attributes
    # instead of properties.

    if perp is None:

        perp = getattr(
            stacked_secondary,
            "perpendicularBaseline",
            None
        )

    if perp is None:

        perp = getattr(
            stacked_secondary,
            "perpendicular_baseline",
            None
        )

    # --------------------------------------------------------
    # Convert to numeric value
    # --------------------------------------------------------

    try:

        if perp is not None:

            return float(perp)

    except (
        TypeError,
        ValueError
    ):

        pass

    return None


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("       NETWORK PAIR BASELINE + GEOMETRY VALIDATION")
    print("=" * 70)

    # --------------------------------------------------------
    # Load input
    # --------------------------------------------------------

    df = pd.read_csv(
        PAIR_FILE
    )

    print(
        f"\nNetwork candidates : {len(df)}"
    )

    aoi_wkt = load_aoi()

    results = []

    # --------------------------------------------------------
    # Validate every pair
    # --------------------------------------------------------

    for index, row in df.iterrows():

        print(
            f"\n[{index + 1}/{len(df)}]"
        )

        reference = row[
            "reference_scene"
        ]

        secondary = row[
            "secondary_scene"
        ]

        ref_date = pd.to_datetime(
            row["reference_date"]
        )

        sec_date = pd.to_datetime(
            row["secondary_date"]
        )

        temporal_days = (
            sec_date - ref_date
        ).days

        direction = str(
            row["orbit_direction"]
        )

        relative_orbit = int(
            row["relative_orbit"]
        )

        print(
            f"  {ref_date.date()} "
            f"-> "
            f"{sec_date.date()}"
        )

        print(
            f"  Track: "
            f"{direction} / "
            f"orbit {relative_orbit}"
        )

        # ----------------------------------------------------
        # Temporal validation
        # ----------------------------------------------------

        temporal_ok = (
            temporal_days > 0
            and temporal_days <= MAX_TEMPORAL_DAYS
        )

        # ----------------------------------------------------
        # ASF scene search
        # ----------------------------------------------------

        ref_scene = search_scene(
            reference,
            aoi_wkt
        )

        sec_scene = search_scene(
            secondary,
            aoi_wkt
        )

        scenes_found = (
            ref_scene is not None
            and sec_scene is not None
        )

        if not scenes_found:

            print(
                "  RESULT: REJECT "
                "(scene not found)"
            )

            results.append({
                **row.to_dict(),
                "temporal_days_checked": temporal_days,
                "temporal_valid": temporal_ok,
                "reference_scene_found": ref_scene is not None,
                "secondary_scene_found": sec_scene is not None,
                "perpendicular_baseline_m": None,
                "baseline_quality": "UNKNOWN",
                "geometry_status": "FAIL",
                "validation_status": "REJECT",
            })

            continue

        # ----------------------------------------------------
        # Extract metadata
        # ----------------------------------------------------

        ref_props = getattr(
            ref_scene,
            "properties",
            {}
        )

        sec_props = getattr(
            sec_scene,
            "properties",
            {}
        )

        ref_orbit = (
            ref_props.get(
                "relativeOrbit"
            )
            or ref_props.get(
                "relativeOrbitNumber"
            )
        )

        sec_orbit = (
            sec_props.get(
                "relativeOrbit"
            )
            or sec_props.get(
                "relativeOrbitNumber"
            )
        )

        ref_direction = (
            ref_props.get(
                "orbitDirection"
            )
        )

        sec_direction = (
            sec_props.get(
                "orbitDirection"
            )
        )

        # ----------------------------------------------------
        # Track validation
        # ----------------------------------------------------

        track_ok = True

        if ref_orbit is not None:
            track_ok = (
                track_ok
                and int(ref_orbit)
                == relative_orbit
            )

        if sec_orbit is not None:
            track_ok = (
                track_ok
                and int(sec_orbit)
                == relative_orbit
            )

        if ref_direction is not None:
            track_ok = (
                track_ok
                and str(ref_direction).upper()
                == direction.upper()
            )

        if sec_direction is not None:
            track_ok = (
                track_ok
                and str(sec_direction).upper()
                == direction.upper()
            )

        # ----------------------------------------------------
        # Baseline
        # ----------------------------------------------------

        perp = get_perpendicular_baseline(
            ref_scene,
            sec_scene
        )

        if perp is None:

            baseline_quality = (
                "UNKNOWN_BASELINE"
            )

        else:

            perp_abs = abs(perp)

            if perp_abs <= GOOD_PERPENDICULAR_M:

                baseline_quality = "GOOD"

            elif (
                perp_abs
                <= ACCEPTABLE_PERPENDICULAR_M
            ):

                baseline_quality = (
                    "ACCEPTABLE"
                )

            else:

                baseline_quality = "POOR"

        # ----------------------------------------------------
        # Geometry status
        # ----------------------------------------------------

        geometry_ok = (
            scenes_found
            and track_ok
            and temporal_ok
        )

        # ----------------------------------------------------
        # Final decision
        # ----------------------------------------------------

        if not geometry_ok:

            validation_status = "REJECT"

        elif baseline_quality == "GOOD":

            validation_status = "APPROVED"

        elif baseline_quality == "ACCEPTABLE":

            validation_status = "REVIEW"

        else:

            validation_status = "REVIEW"

        print(
            f"  Temporal: "
            f"{'PASS' if temporal_ok else 'FAIL'}"
        )

        print(
            f"  Track: "
            f"{'PASS' if track_ok else 'FAIL'}"
        )

        print(
            f"  Perpendicular baseline: "
            f"{perp if perp is not None else 'UNKNOWN'}"
        )

        print(
            f"  Baseline quality: "
            f"{baseline_quality}"
        )

        print(
            f"  Decision: "
            f"{validation_status}"
        )

        results.append({
            **row.to_dict(),
            "temporal_days_checked": temporal_days,
            "temporal_valid": temporal_ok,
            "reference_scene_found": True,
            "secondary_scene_found": True,
            "reference_relative_orbit": ref_orbit,
            "secondary_relative_orbit": sec_orbit,
            "reference_orbit_direction": ref_direction,
            "secondary_orbit_direction": sec_direction,
            "track_valid": track_ok,
            "perpendicular_baseline_m": perp,
            "baseline_quality": baseline_quality,
            "geometry_status": (
                "PASS"
                if geometry_ok
                else "FAIL"
            ),
            "validation_status": validation_status,
        })

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    result_df = pd.DataFrame(
        results
    )

    result_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    approved = (
        result_df[
            result_df["validation_status"]
            == "APPROVED"
        ]
    )

    review = (
        result_df[
            result_df["validation_status"]
            == "REVIEW"
        ]
    )

    rejected = (
        result_df[
            result_df["validation_status"]
            == "REJECT"
        ]
    )

    unknown = (
        result_df[
            result_df["baseline_quality"]
            == "UNKNOWN_BASELINE"
        ]
    )

    report = []

    report.append(
        "NETWORK PAIR VALIDATION REPORT"
    )

    report.append(
        "=" * 50
    )

    report.append(
        f"Candidates checked : {len(result_df)}"
    )

    report.append(
        f"Approved           : {len(approved)}"
    )

    report.append(
        f"Review             : {len(review)}"
    )

    report.append(
        f"Rejected           : {len(rejected)}"
    )

    report.append(
        f"Unknown baseline   : {len(unknown)}"
    )

    report.append("")

    report.append(
        "Baseline thresholds:"
    )

    report.append(
        f"GOOD       <= {GOOD_PERPENDICULAR_M} m"
    )

    report.append(
        f"ACCEPTABLE <= "
        f"{ACCEPTABLE_PERPENDICULAR_M} m"
    )

    report.append(
        "Temporal baseline <= "
        f"{MAX_TEMPORAL_DAYS} days"
    )

    report_text = "\n".join(
        report
    )

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(report_text)

    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)

    print(
        f"\nCandidates checked : {len(result_df)}"
    )

    print(
        f"Approved           : {len(approved)}"
    )

    print(
        f"Review             : {len(review)}"
    )

    print(
        f"Rejected           : {len(rejected)}"
    )

    print(
        f"Unknown baseline   : {len(unknown)}"
    )

    print("\nOutput:")
    print(OUTPUT_FILE)

    print("\nReport:")
    print(REPORT_FILE)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()