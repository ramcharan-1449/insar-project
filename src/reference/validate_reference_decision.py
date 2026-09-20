"""Validate the independently reviewable InSAR reference decision record."""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config" / "insar_reference_config.json"


def main() -> None:
    with CONFIG_FILE.open(encoding="utf-8") as stream:
        config = json.load(stream)

    framework = config.get("reference_framework", {})
    quality_rules = config.get("quality_rules", {})
    result = config.get("reference_estimation", {}).get("reference_result", {})

    required = {
        "reference_framework.status": framework.get("status"),
        "reference_framework.reference_type": framework.get("reference_type"),
        "quality_rules.minimum_correlation": quality_rules.get("minimum_correlation"),
        "quality_rules.reference_candidate_correlation": quality_rules.get("reference_candidate_correlation"),
        "reference_result.pair_id": result.get("pair_id"),
        "reference_result.reference_los_m": result.get("reference_los_m"),
        "scientific_constraints.reference_requires_review": (
            config.get("scientific_constraints", {}).get("reference_requires_review")
        ),
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ValueError("Reference decision is incomplete: " + ", ".join(missing))

    if quality_rules["reference_candidate_correlation"] < quality_rules["minimum_correlation"]:
        raise ValueError("Reference-candidate threshold must be at least the minimum correlation.")

    review_required = config["scientific_constraints"]["reference_requires_review"]
    if review_required or framework["status"] != "APPROVED_FOR_PRODUCTION":
        raise ValueError(
            "Reference decision is not approved for production. Record the production "
            "pair decision, set status to APPROVED_FOR_PRODUCTION, and set "
            "scientific_constraints.reference_requires_review to false after joint review."
        )

    print("REFERENCE DECISION RECORD: PASS (APPROVED_FOR_PRODUCTION)")


if __name__ == "__main__":
    main()
