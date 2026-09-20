import pandas as pd
from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_all_dynamic_baselines.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "config"
    / "sentinel1_ranked_baselines.csv"
)


# ============================================================
# SETTINGS
# ============================================================

GOOD_BASELINE_M = 200
ACCEPTABLE_BASELINE_M = 500

MAX_TEMPORAL_DAYS = 24


print("=" * 70)
print("             SENTINEL-1 BASELINE RANKING")
print("=" * 70)


# ============================================================
# 1. LOAD DATA
# ============================================================

print("\nLoading baseline candidates:")

print(INPUT_FILE)

df = pd.read_csv(INPUT_FILE)

print("\nRows loaded:", len(df))


# ============================================================
# 2. KEEP VALID CANDIDATES
# ============================================================

df = df[
    df["status"] == "BASELINE_CANDIDATE"
].copy()


# ============================================================
# 3. CONVERT NUMERIC VALUES
# ============================================================

df["temporal_baseline_days"] = pd.to_numeric(
    df["temporal_baseline_days"],
    errors="coerce"
)

df["perpendicular_baseline_m"] = pd.to_numeric(
    df["perpendicular_baseline_m"],
    errors="coerce"
)


# ============================================================
# 4. REMOVE INVALID VALUES
# ============================================================

df = df.dropna(
    subset=[
        "temporal_baseline_days",
        "perpendicular_baseline_m"
    ]
)


# ============================================================
# 5. REMOVE SELF-PAIRS
# ============================================================

df = df[
    df["reference_scene"]
    != df["secondary_scene"]
].copy()


print(
    "Valid non-self candidates:",
    len(df)
)


# ============================================================
# 6. ABSOLUTE BASELINE VALUES
# ============================================================

df["abs_temporal_days"] = (
    df["temporal_baseline_days"]
    .abs()
)

df["abs_perpendicular_m"] = (
    df["perpendicular_baseline_m"]
    .abs()
)


# ============================================================
# 7. VERIFY TEMPORAL LIMIT
# ============================================================

df = df[
    df["abs_temporal_days"]
    <= MAX_TEMPORAL_DAYS
].copy()


# ============================================================
# 8. CLASSIFY PERPENDICULAR BASELINE
# ============================================================

def classify_baseline(value):

    if value <= GOOD_BASELINE_M:
        return "GOOD"

    elif value <= ACCEPTABLE_BASELINE_M:
        return "ACCEPTABLE"

    else:
        return "LOW_PRIORITY"


df["baseline_class"] = (
    df["abs_perpendicular_m"]
    .apply(classify_baseline)
)


# ============================================================
# 9. CALCULATE RANKING SCORE
# ============================================================

# Lower score = better candidate.
#
# Perpendicular baseline is given stronger importance.
#
# Temporal separation is included as a smaller penalty.

df["ranking_score"] = (
    df["abs_perpendicular_m"]
    + (
        df["abs_temporal_days"] * 5
    )
)


# ============================================================
# 10. RANK WITHIN EACH REFERENCE SCENE
# ============================================================

df = df.sort_values(
    by=[
        "reference_scene",
        "ranking_score"
    ]
)


df["candidate_rank"] = (
    df.groupby(
        "reference_scene"
    ).cumcount() + 1
)


# ============================================================
# 11. ADD RECOMMENDATION
# ============================================================

df["recommendation"] = "NORMAL_PRIORITY"


# Best candidate for each reference
df.loc[
    df["candidate_rank"] == 1,
    "recommendation"
] = "HIGH_PRIORITY"


# ============================================================
# 12. SELECT FINAL COLUMNS
# ============================================================

output_columns = [

    "reference_scene",

    "secondary_scene",

    "reference_date",

    "secondary_date",

    "orbit_direction",

    "relative_orbit",

    "frame",

    "temporal_baseline_days",

    "perpendicular_baseline_m",

    "abs_temporal_days",

    "abs_perpendicular_m",

    "baseline_class",

    "ranking_score",

    "candidate_rank",

    "recommendation"
]


df = df[
    output_columns
]


# ============================================================
# 13. SAVE
# ============================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# 14. DISPLAY SUMMARY
# ============================================================

print("\n" + "=" * 70)

print(
    "                 RANKING COMPLETE"
)

print("=" * 70)


print(
    "\nTotal ranked candidates:",
    len(df)
)


print("\nBaseline classification:")

print(
    df["baseline_class"]
    .value_counts()
    .to_string()
)


# ============================================================
# 15. DISPLAY TOP CANDIDATE FOR EACH REFERENCE
# ============================================================

print(
    "\nTOP CANDIDATE FOR EACH REFERENCE:"
)


top_candidates = df[
    df["candidate_rank"] == 1
]


for _, row in top_candidates.iterrows():

    print("\nReference:")

    print(
        row["reference_scene"]
    )

    print(
        "Secondary:",
        row["secondary_scene"]
    )

    print(
        "Temporal:",
        row["temporal_baseline_days"],
        "days"
    )

    print(
        "Perpendicular:",
        row["perpendicular_baseline_m"],
        "m"
    )

    print(
        "Class:",
        row["baseline_class"]
    )

    print(
        "Score:",
        round(
            row["ranking_score"],
            2
        )
    )


# ============================================================
# 16. OUTPUT
# ============================================================

print("\nRanked CSV created:")

print(
    OUTPUT_FILE
)


print("\nIMPORTANT:")

print(
    "These are ranked candidates,"
)

print(
    "not yet the final HyP3 submission list."
)


print("\nNext step:")

print(
    "Select final scientifically suitable"
)

print(
    "InSAR pairs before submitting jobs to HyP3."
)


print("\n" + "=" * 70)