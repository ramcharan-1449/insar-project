from pathlib import Path
import pandas as pd


# ============================================================
# STAGE 2.5 — SCIENTIFIC PRIORITY PAIR VALIDATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "config" / "sentinel1_priority_pairs_scientific.csv"
OUTPUT_FILE = PROJECT_ROOT / "config" / "sentinel1_final_pairs.csv"
REPORT_FILE = PROJECT_ROOT / "config" / "sentinel1_pair_validation_report.csv"


MAX_TEMPORAL_DAYS = 24
MAX_PERPENDICULAR_BASELINE_M = 200


def main():

    print("=" * 70)
    print("STAGE 2.5 — SCIENTIFIC PRIORITY PAIR VALIDATION")
    print("=" * 70)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Priority pair file not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    print(f"\nInput priority pairs: {len(df)}")

    validation_rows = []
    accepted_rows = []

    for _, row in df.iterrows():

        reference_date = pd.to_datetime(row["reference_date"], utc=True)
        secondary_date = pd.to_datetime(row["secondary_date"], utc=True)

        temporal_days = (
            secondary_date - reference_date
        ).total_seconds() / 86400.0

        perp = pd.to_numeric(
            row["perpendicular_baseline_m"],
            errors="coerce"
        )

        quality = str(row["quality"]).upper()

        orbit_direction = str(
            row["orbit_direction"]
        ).upper()

        relative_orbit = row["relative_orbit"]

        checks = []

        # ----------------------------------------------------
        # 1. Temporal baseline
        # ----------------------------------------------------
        temporal_ok = (
            temporal_days > 0
            and temporal_days <= MAX_TEMPORAL_DAYS
        )

        checks.append(temporal_ok)

        # ----------------------------------------------------
        # 2. Perpendicular baseline
        # ----------------------------------------------------
        perp_ok = (
            pd.notna(perp)
            and abs(perp) <= MAX_PERPENDICULAR_BASELINE_M
        )

        checks.append(perp_ok)

        # ----------------------------------------------------
        # 3. Quality
        # ----------------------------------------------------
        quality_ok = quality in ["GOOD", "ACCEPTABLE"]

        checks.append(quality_ok)

        # ----------------------------------------------------
        # 4. Orbit direction
        # ----------------------------------------------------
        orbit_ok = orbit_direction in [
            "ASCENDING",
            "DESCENDING"
        ]

        checks.append(orbit_ok)

        # ----------------------------------------------------
        # 5. Relative orbit
        # ----------------------------------------------------
        relative_orbit_ok = pd.notna(relative_orbit)

        checks.append(relative_orbit_ok)

        # ----------------------------------------------------
        # Final decision
        # ----------------------------------------------------
        accepted = all(checks)

        if accepted:
            decision = "ACCEPT"
            accepted_rows.append(row)
        else:
            decision = "REJECT"

        validation_rows.append({
            "reference_date": reference_date.isoformat(),
            "secondary_date": secondary_date.isoformat(),
            "orbit_direction": orbit_direction,
            "relative_orbit": relative_orbit,
            "temporal_baseline_days": round(
                temporal_days, 3
            ),
            "perpendicular_baseline_m": perp,
            "quality": quality,
            "temporal_check": temporal_ok,
            "perpendicular_baseline_check": perp_ok,
            "quality_check": quality_ok,
            "orbit_check": orbit_ok,
            "relative_orbit_check": relative_orbit_ok,
            "decision": decision
        })

    validation_df = pd.DataFrame(validation_rows)

    validation_df.to_csv(
        REPORT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # Build final accepted pair list
    # --------------------------------------------------------

    final_df = pd.DataFrame(accepted_rows)

    if not final_df.empty:

        # Sort chronologically
        final_df = final_df.sort_values(
            by=[
                "orbit_direction",
                "relative_orbit",
                "reference_date",
                "secondary_date"
            ]
        )

    final_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)

    print(f"\nTotal input pairs : {len(df)}")
    print(
        f"Accepted pairs   : {len(final_df)}"
    )
    print(
        f"Rejected pairs   : {len(df) - len(final_df)}"
    )

    print("\nOutput files:")

    print(f"  {OUTPUT_FILE}")
    print(f"  {REPORT_FILE}")

    if not final_df.empty:

        print("\nAccepted pairs:")

        display_columns = [
            "reference_date",
            "secondary_date",
            "orbit_direction",
            "relative_orbit",
            "temporal_baseline_days",
            "perpendicular_baseline_m",
            "quality"
        ]

        print(
            final_df[display_columns].to_string(
                index=False
            )
        )

    print("\nHyP3 submission: NOT PERFORMED")

    print("=" * 70)


if __name__ == "__main__":
    main()