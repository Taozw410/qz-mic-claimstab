from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Iterable


CLAIM_TYPES = {"effect", "difference", "null", "ranking", "not_verifiable"}
RECONSTRUCTION_STATUSES = {"stable", "partial", "unstable", "not_available"}
GRADES = {"strong", "moderate", "descriptive", "not_supported", "not_verifiable"}

CLAIM_COLUMNS = {"claim_id", "claim_text", "claim_type", "reconstruction_id"}
RECONSTRUCTION_COLUMNS = {
    "reconstruction_id",
    "domain",
    "layer",
    "metric",
    "status",
}
ENDPOINT_COLUMNS = {
    "claim_id",
    "domain",
    "outcome",
    "contrast",
    "pipeline",
    "sample_set",
    "testable",
}


@dataclass(frozen=True)
class Claim:
    claim_id: str
    claim_text: str
    claim_type: str
    reconstruction_id: str
    manual_evidence_grade: str
    manual_override_reason: str
    notes: str


@dataclass(frozen=True)
class Endpoint:
    claim_id: str
    domain: str
    outcome: str
    contrast: str
    pipeline: str
    sample_set: str
    estimate: float | None
    p_value: float | None
    direction: str
    rank: int | None
    testable: bool
    source: str
    notes: str


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: Iterable[dict[str, object]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _require_columns(path: Path, rows: list[dict[str, str]], required: set[str]) -> None:
    if not rows:
        raise ValueError(f"{path} is empty")
    missing = sorted(required - set(rows[0]))
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")


def _float(value: str | None) -> float | None:
    text = "" if value is None else str(value).strip()
    if not text or text.upper() in {"NA", "NAN", "NULL"}:
        return None
    return float(text)


def _int(value: str | None) -> int | None:
    text = "" if value is None else str(value).strip()
    if not text or text.upper() in {"NA", "NAN", "NULL"}:
        return None
    return int(float(text))


def _bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes"}


def _direction(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"positive", "negative", "none", "not_applicable"}:
        return normalized
    return "not_applicable"


def load_claims(path: Path) -> dict[str, Claim]:
    rows = _read_csv(path)
    _require_columns(path, rows, CLAIM_COLUMNS)
    claims: dict[str, Claim] = {}
    for row in rows:
        claim_type = row["claim_type"].strip()
        if claim_type not in CLAIM_TYPES:
            raise ValueError(f"Unknown claim_type {claim_type!r} for {row['claim_id']}")
        manual = row.get("manual_evidence_grade", "").strip()
        if manual and manual not in GRADES:
            raise ValueError(f"Unknown manual evidence grade {manual!r}")
        claim = Claim(
            claim_id=row["claim_id"].strip(),
            claim_text=row["claim_text"].strip(),
            claim_type=claim_type,
            reconstruction_id=row["reconstruction_id"].strip(),
            manual_evidence_grade=manual,
            manual_override_reason=row.get(
                "manual_override_reason", ""
            ).strip(),
            notes=row.get("notes", "").strip(),
        )
        if claim.claim_id in claims:
            raise ValueError(f"Duplicate claim_id: {claim.claim_id}")
        claims[claim.claim_id] = claim
    return claims


def load_reconstruction(path: Path) -> dict[str, str]:
    rows = _read_csv(path)
    _require_columns(path, rows, RECONSTRUCTION_COLUMNS)
    statuses: dict[str, str] = {}
    for row in rows:
        status = row["status"].strip()
        if status not in RECONSTRUCTION_STATUSES:
            raise ValueError(f"Unknown reconstruction status {status!r}")
        reconstruction_id = row["reconstruction_id"].strip()
        previous = statuses.get(reconstruction_id)
        if previous and previous != status:
            raise ValueError(
                f"Conflicting reconstruction statuses for {reconstruction_id}: "
                f"{previous}, {status}"
            )
        statuses[reconstruction_id] = status
    return statuses


def load_endpoints(path: Path) -> list[Endpoint]:
    rows = _read_csv(path)
    _require_columns(path, rows, ENDPOINT_COLUMNS)
    endpoints = []
    for row in rows:
        p_value = _float(row.get("p_value"))
        if p_value is not None and not 0 <= p_value <= 1:
            raise ValueError(f"p_value outside [0, 1]: {p_value}")
        endpoints.append(
            Endpoint(
                claim_id=row["claim_id"].strip(),
                domain=row["domain"].strip(),
                outcome=row["outcome"].strip(),
                contrast=row["contrast"].strip(),
                pipeline=row["pipeline"].strip(),
                sample_set=row["sample_set"].strip(),
                estimate=_float(row.get("estimate")),
                p_value=p_value,
                direction=_direction(row.get("direction")),
                rank=_int(row.get("rank")),
                testable=_bool(row.get("testable")),
                source=row.get("source", "").strip(),
                notes=row.get("notes", "").strip(),
            )
        )
    return endpoints


def _aggregate_comparison(
    claim: Claim, rows: list[Endpoint], alpha: float
) -> dict[str, object]:
    testable = [row for row in rows if row.testable and row.p_value is not None]
    directions = {
        row.direction
        for row in testable
        if row.direction not in {"", "not_applicable"}
    }
    p_values = [row.p_value for row in testable if row.p_value is not None]
    ranks = sorted({row.rank for row in rows if row.rank is not None})
    significant = [p < alpha for p in p_values]
    estimates = [row.estimate for row in rows if row.estimate is not None]

    if claim.claim_type in {"difference", "null", "ranking"}:
        direction_stability = "not_applicable"
    elif not directions:
        direction_stability = "insufficient"
    elif len(directions) == 1:
        direction_stability = "stable"
    else:
        direction_stability = "mixed"

    if not significant:
        significance_stability = "insufficient"
    elif all(significant):
        significance_stability = "stable_supported"
    elif not any(significant):
        significance_stability = "stable_null"
    else:
        significance_stability = "mixed"

    if claim.claim_type != "ranking":
        rank_stability = "not_applicable"
    elif not ranks:
        rank_stability = "insufficient"
    elif len(ranks) == 1:
        rank_stability = "stable"
    else:
        rank_stability = "mixed"

    if claim.claim_type in {"difference", "null"}:
        if significance_stability in {"stable_supported", "stable_null"}:
            dependency = "low"
        elif significance_stability == "mixed":
            dependency = "high"
        else:
            dependency = "not_evaluable"
    elif claim.claim_type == "ranking":
        if rank_stability == "mixed":
            dependency = "high"
        elif rank_stability == "stable" and significance_stability in {
            "stable_supported",
            "stable_null",
        }:
            dependency = "low"
        elif rank_stability == "stable":
            dependency = "moderate"
        else:
            dependency = "not_evaluable"
    else:
        if direction_stability == "mixed":
            dependency = "high"
        elif direction_stability == "stable" and significance_stability in {
            "stable_supported",
            "stable_null",
        }:
            dependency = "low"
        elif direction_stability == "stable":
            dependency = "moderate"
        else:
            dependency = "not_evaluable"

    return {
        "claim_id": claim.claim_id,
        "domain": rows[0].domain,
        "outcome": rows[0].outcome,
        "contrast": rows[0].contrast,
        "sample_set": rows[0].sample_set,
        "n_results": len(rows),
        "n_testable": len(testable),
        "pipelines": ";".join(sorted({row.pipeline for row in rows})),
        "estimate_min": min(estimates) if estimates else "",
        "estimate_max": max(estimates) if estimates else "",
        "p_min": min(p_values) if p_values else "",
        "p_max": max(p_values) if p_values else "",
        "direction_values": ";".join(sorted(directions)),
        "direction_stability": direction_stability,
        "significant_count": sum(significant),
        "non_significant_count": len(significant) - sum(significant),
        "significance_stability": significance_stability,
        "rank_values": ";".join(str(rank) for rank in ranks),
        "rank_stability": rank_stability,
        "dependency_level": dependency,
    }


def _claim_from_comparisons(
    claim: Claim,
    comparisons: list[dict[str, object]],
    reconstruction_status: str,
) -> dict[str, object]:
    dependency_values = [str(row["dependency_level"]) for row in comparisons]
    if "high" in dependency_values:
        dependency = "high"
    elif "moderate" in dependency_values:
        dependency = "moderate"
    elif dependency_values and all(value == "low" for value in dependency_values):
        dependency = "low"
    else:
        dependency = "not_evaluable"

    direction_values = {str(row["direction_stability"]) for row in comparisons}
    if "mixed" in direction_values:
        direction_stability = "mixed"
    elif direction_values == {"not_applicable"}:
        direction_stability = "not_applicable"
    elif direction_values == {"stable"}:
        direction_stability = "stable"
    else:
        direction_stability = "insufficient"

    significance_values = {str(row["significance_stability"]) for row in comparisons}
    if significance_values == {"stable_supported"}:
        significance_stability = "stable_supported"
    elif significance_values == {"stable_null"}:
        significance_stability = "stable_null"
    elif not significance_values or significance_values == {"insufficient"}:
        significance_stability = "insufficient"
    else:
        significance_stability = "mixed"

    rank_values = {str(row["rank_stability"]) for row in comparisons}
    if claim.claim_type != "ranking":
        rank_stability = "not_applicable"
    elif "mixed" in rank_values:
        rank_stability = "mixed"
    elif rank_values == {"stable"}:
        rank_stability = "stable"
    else:
        rank_stability = "insufficient"

    n_results = sum(int(row["n_results"]) for row in comparisons)
    n_testable = sum(int(row["n_testable"]) for row in comparisons)
    n_missing = n_results - n_testable
    if n_results == 0 or n_testable == 0:
        specification_coverage = "none"
    elif n_missing > 0:
        specification_coverage = "partial"
    else:
        specification_coverage = "complete"
    if (
        claim.claim_type == "not_verifiable"
        or reconstruction_status == "not_available"
        or not comparisons
        or n_results == 0
        or n_testable == 0
    ):
        inference_stability = "not_verifiable"
        auto_grade = "not_verifiable"
    elif direction_stability == "mixed" or rank_stability == "mixed":
        inference_stability = "unstable"
        auto_grade = "not_supported"
    elif claim.claim_type in {"difference", "null"}:
        if significance_stability == "stable_null":
            if claim.claim_type == "null":
                inference_stability = "stable"
                auto_grade = (
                    "strong"
                    if reconstruction_status == "stable" and dependency == "low"
                    else "moderate"
                )
            else:
                inference_stability = "conditional"
                auto_grade = "not_supported"
        elif significance_stability == "stable_supported":
            inference_stability = (
                "stable" if dependency == "low" else "conditional"
            )
            auto_grade = (
                "strong"
                if reconstruction_status == "stable" and dependency == "low"
                else "moderate"
            )
        else:
            inference_stability = "unstable"
            auto_grade = "not_supported"
    elif claim.claim_type == "ranking":
        if rank_stability != "stable":
            inference_stability = "not_verifiable"
            auto_grade = "not_verifiable"
        elif significance_stability == "stable_supported":
            inference_stability = (
                "stable" if dependency == "low" else "conditional"
            )
            auto_grade = (
                "strong"
                if reconstruction_status == "stable" and dependency == "low"
                else "moderate"
            )
        else:
            inference_stability = "conditional"
            auto_grade = "descriptive"
    elif claim.claim_type == "effect":
        if direction_stability != "stable":
            inference_stability = "not_verifiable"
            auto_grade = "not_verifiable"
        elif significance_stability == "stable_supported":
            inference_stability = (
                "stable" if dependency == "low" else "conditional"
            )
            auto_grade = (
                "strong"
                if reconstruction_status == "stable" and dependency == "low"
                else "moderate"
            )
        elif significance_stability in {"stable_null", "mixed"}:
            inference_stability = "conditional"
            auto_grade = (
                "not_supported"
                if significance_stability == "stable_null"
                else "descriptive"
            )
        else:
            inference_stability = "not_verifiable"
            auto_grade = "not_verifiable"
    elif dependency in {"low", "moderate"} and (
        direction_stability in {"stable", "not_applicable"}
    ):
        inference_stability = "conditional"
        auto_grade = (
            "descriptive"
            if claim.claim_type in {"effect", "ranking"}
            and significance_stability in {"stable_null", "mixed"}
            else "moderate"
        )
    else:
        inference_stability = "conditional"
        auto_grade = "descriptive"

    coverage_downgraded = False
    if n_missing > 0 and auto_grade == "strong":
        auto_grade = "moderate"
        inference_stability = "conditional"
        coverage_downgraded = True

    manual_override_applied = bool(
        claim.manual_evidence_grade
        and claim.manual_evidence_grade != auto_grade
    )
    final_grade = claim.manual_evidence_grade or auto_grade
    review_required = final_grade != "strong" or dependency != "low"
    if manual_override_applied:
        review_required = True
    pipelines = sorted(
        {
            pipeline
            for row in comparisons
            for pipeline in str(row["pipelines"]).split(";")
            if pipeline
        }
    )
    sample_sets = sorted({str(row["sample_set"]) for row in comparisons})
    domains = sorted({str(row["domain"]) for row in comparisons})
    outcomes = sorted({str(row["outcome"]) for row in comparisons})
    rationale = (
        f"planned={n_results}; testable={n_testable}; missing={n_missing}; "
        f"reconstruction={reconstruction_status}; dependency={dependency}; "
        f"direction={direction_stability}; significance={significance_stability}; "
        f"rank={rank_stability}"
    )
    return {
        "claim_id": claim.claim_id,
        "claim_text": claim.claim_text,
        "claim_type": claim.claim_type,
        "reconstruction_status": reconstruction_status,
        "n_comparisons": len(comparisons),
        "n_results": n_results,
        "n_planned_specifications": n_results,
        "n_testable": n_testable,
        "n_missing": n_missing,
        "specification_coverage": specification_coverage,
        "pipelines": ";".join(pipelines),
        "sample_sets": ";".join(sample_sets),
        "domains": ";".join(domains),
        "outcomes": ";".join(outcomes),
        "direction_stability": direction_stability,
        "significance_stability": significance_stability,
        "rank_stability": rank_stability,
        "analysis_dependency": dependency,
        "inference_stability": inference_stability,
        "auto_evidence_grade": auto_grade,
        "coverage_downgraded": coverage_downgraded,
        "manual_evidence_grade": claim.manual_evidence_grade,
        "manual_override_applied": manual_override_applied,
        "manual_override_reason": claim.manual_override_reason,
        "evidence_grade": final_grade,
        "review_required": review_required,
        "rationale": rationale,
    }


def _summary_report(
    claims: list[dict[str, object]],
    reconstruction: dict[str, str],
    alpha: float,
) -> str:
    grade_counts = Counter(str(row["evidence_grade"]) for row in claims)
    dependency_counts = Counter(str(row["analysis_dependency"]) for row in claims)
    lines = [
        "# Claim stability report",
        "",
        "## Framework",
        "",
        "1. Data reconstruction",
        "2. Analysis dependence",
        "3. Inference stability",
        "4. Evidence grade",
        "",
        f"Significance threshold: {alpha}.",
        "",
        "## Summary",
        "",
        f"- Claims: {len(claims)}",
        f"- Reconstruction records: {len(reconstruction)}",
    ]
    for grade in sorted(GRADES):
        lines.append(f"- Evidence `{grade}`: {grade_counts.get(grade, 0)}")
    for level in ("low", "moderate", "high", "not_evaluable"):
        lines.append(f"- Analysis dependency `{level}`: {dependency_counts.get(level, 0)}")
    lines.extend(
        [
            "",
            "## Evidence rules",
            "",
            "- Strong: stable reconstruction, low dependency, and stable",
            "  direction/significance with complete specification coverage.",
            "- Moderate: stable inference with partial reconstruction or one",
            "  moderate sensitivity; any missing planned specification caps",
            "  an otherwise strong claim at moderate.",
            "- Descriptive: stable direction/ranking without full significance",
            "  support.",
            "- Not supported: mixed direction/ranking or an effect claim with",
            "  stable null results.",
            "- Not verifiable: required data are unavailable.",
            "",
            "The generated grade is an audit aid. Analysts should set",
            "`manual_evidence_grade` when domain reasoning requires an override;",
            "the rationale should be recorded in `manual_override_reason`.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_claim_stability(
    claims_path: Path,
    reconstruction_path: Path,
    endpoints_path: Path,
    output_dir: Path,
    alpha: float = 0.05,
) -> dict[str, Path]:
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1")
    claims = load_claims(claims_path)
    reconstruction = load_reconstruction(reconstruction_path)
    endpoints = load_endpoints(endpoints_path)

    unknown_claims = sorted({row.claim_id for row in endpoints} - set(claims))
    if unknown_claims:
        raise ValueError(f"Endpoints reference unknown claim_id: {unknown_claims}")

    for claim in claims.values():
        if claim.reconstruction_id not in reconstruction:
            raise ValueError(
                f"{claim.claim_id} references missing reconstruction_id "
                f"{claim.reconstruction_id}"
            )

    grouped: dict[tuple[str, str, str, str, str], list[Endpoint]] = {}
    for endpoint in endpoints:
        key = (
            endpoint.claim_id,
            endpoint.domain,
            endpoint.outcome,
            endpoint.contrast,
            endpoint.sample_set,
        )
        grouped.setdefault(key, []).append(endpoint)

    comparison_rows = [
        _aggregate_comparison(claims[key[0]], rows, alpha)
        for key, rows in sorted(grouped.items())
    ]
    claim_rows = []
    for claim_id, claim in sorted(claims.items()):
        current = [row for row in comparison_rows if row["claim_id"] == claim_id]
        claim_rows.append(
            _claim_from_comparisons(
                claim,
                current,
                reconstruction[claim.reconstruction_id],
            )
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    comparison_columns = [
        "claim_id",
        "domain",
        "outcome",
        "contrast",
        "sample_set",
        "n_results",
        "n_testable",
        "pipelines",
        "estimate_min",
        "estimate_max",
        "p_min",
        "p_max",
        "direction_values",
        "direction_stability",
        "significant_count",
        "non_significant_count",
        "significance_stability",
        "rank_values",
        "rank_stability",
        "dependency_level",
    ]
    claim_columns = [
        "claim_id",
        "claim_text",
        "claim_type",
        "reconstruction_status",
        "n_comparisons",
        "n_results",
        "n_planned_specifications",
        "n_testable",
        "n_missing",
        "specification_coverage",
        "pipelines",
        "sample_sets",
        "domains",
        "outcomes",
        "direction_stability",
        "significance_stability",
        "rank_stability",
        "analysis_dependency",
        "inference_stability",
        "auto_evidence_grade",
        "coverage_downgraded",
        "manual_evidence_grade",
        "manual_override_applied",
        "manual_override_reason",
        "evidence_grade",
        "review_required",
        "rationale",
    ]
    paths = {
        "endpoint_dependency": output_dir / "endpoint_dependency.csv",
        "claim_stability_matrix": output_dir / "claim_stability_matrix.csv",
        "reconstruction_summary": output_dir / "reconstruction_summary.csv",
        "report": output_dir / "report.md",
    }
    _write_csv(paths["endpoint_dependency"], comparison_rows, comparison_columns)
    _write_csv(paths["claim_stability_matrix"], claim_rows, claim_columns)
    reconstruction_rows = _read_csv(reconstruction_path)
    reconstruction_columns = [
        "reconstruction_id",
        "domain",
        "layer",
        "metric",
        "value",
        "threshold",
        "status",
        "source",
        "notes",
    ]
    _write_csv(
        paths["reconstruction_summary"],
        reconstruction_rows,
        reconstruction_columns,
    )
    paths["report"].write_text(
        _summary_report(claim_rows, reconstruction, alpha),
        encoding="utf-8",
    )
    return paths


def _claim_dataset(claim: Claim) -> str:
    for token in claim.notes.split(";"):
        key, separator, value = token.partition("=")
        if separator and key.strip().lower() == "dataset":
            return value.strip()
    return ""


def _framework_calls(
    claim: Claim,
    endpoint_rows: list[Endpoint],
    stability_row: dict[str, object],
    alpha: float,
) -> dict[str, object]:
    testable = [
        row
        for row in endpoint_rows
        if row.testable and row.p_value is not None
    ]
    n_planned = len(endpoint_rows)
    n_testable = len(testable)
    n_missing = n_planned - n_testable
    n_significant = sum(
        row.p_value is not None and row.p_value < alpha for row in testable
    )
    significant_fraction = n_significant / n_testable if n_testable else 0.0

    if claim.claim_type == "null":
        majority_support_value = 1.0 - significant_fraction
        majority_basis = "non_significant_fraction"
    else:
        majority_support_value = significant_fraction
        majority_basis = "significant_fraction"

    if n_testable == 0:
        majority_call = "not_evaluable"
    elif majority_support_value > 0.5:
        majority_call = "supported"
    elif majority_support_value < 0.5:
        majority_call = "not_supported"
    else:
        majority_call = "ambiguous"

    if n_testable == 0:
        strict_call = "not_evaluable"
    elif n_significant == 0 and claim.claim_type == "null":
        strict_call = "supported"
    elif n_significant == n_testable and claim.claim_type != "null":
        strict_call = "supported"
    elif n_significant == n_testable and claim.claim_type == "null":
        strict_call = "contradicted"
    elif n_significant == 0 and claim.claim_type != "null":
        strict_call = "contradicted"
    else:
        strict_call = "mixed"

    grade = str(stability_row["evidence_grade"])
    claimstab_supported = grade in {"strong", "moderate"}
    claimstab_call = "supported" if claimstab_supported else grade

    if majority_call == "supported" and not claimstab_supported:
        disagreement = "majority_overconfident"
    elif strict_call == "supported" and not claimstab_supported:
        disagreement = "strict_overconfident"
    elif claimstab_supported and majority_call != "supported":
        disagreement = "claimstab_more_supportive"
    else:
        disagreement = "concordant"

    return {
        "claim_id": claim.claim_id,
        "dataset": _claim_dataset(claim),
        "claim_text": claim.claim_text,
        "claim_type": claim.claim_type,
        "n_pipelines": len({row.pipeline for row in endpoint_rows}),
        "n_sample_sets": len({row.sample_set for row in endpoint_rows}),
        "n_planned_specifications": n_planned,
        "n_testable": n_testable,
        "n_missing_specifications": n_missing,
        "specification_coverage": (
            "none"
            if n_testable == 0
            else "partial"
            if n_missing > 0
            else "complete"
        ),
        "significant_count": n_significant,
        "majority_basis": majority_basis,
        "majority_support_fraction": round(majority_support_value, 6),
        "majority_call": majority_call,
        "strict_call": strict_call,
        "claimstab_grade": grade,
        "claimstab_call": claimstab_call,
        "claimstab_supported": claimstab_supported,
        "disagreement": disagreement,
        "analysis_dependency": stability_row["analysis_dependency"],
        "inference_stability": stability_row["inference_stability"],
        "reconstruction_status": stability_row["reconstruction_status"],
        "rationale": stability_row["rationale"],
    }


def compare_claim_frameworks(
    claims_path: Path,
    reconstruction_path: Path,
    endpoints_path: Path,
    output_dir: Path,
    alpha: float = 0.05,
) -> dict[str, Path]:
    """Compare claimstab with simple multiverse/sensitivity decision rules.

    The comparison rules are deliberately simple and auditable:
    * majority: more than half of interpretable specifications support the claim;
    * strict: every interpretable specification supports the claim;
    * claimstab: the four-component evidence grade is strong or moderate.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1")
    claims = load_claims(claims_path)
    reconstruction = load_reconstruction(reconstruction_path)
    endpoints = load_endpoints(endpoints_path)

    grouped: dict[tuple[str, str, str, str, str], list[Endpoint]] = {}
    for endpoint in endpoints:
        key = (
            endpoint.claim_id,
            endpoint.domain,
            endpoint.outcome,
            endpoint.contrast,
            endpoint.sample_set,
        )
        grouped.setdefault(key, []).append(endpoint)

    comparison_rows = [
        _aggregate_comparison(claims[key[0]], rows, alpha)
        for key, rows in sorted(grouped.items())
    ]
    claim_rows = []
    for claim_id, claim in sorted(claims.items()):
        current = [row for row in comparison_rows if row["claim_id"] == claim_id]
        claim_rows.append(
            _claim_from_comparisons(
                claim,
                current,
                reconstruction[claim.reconstruction_id],
            )
        )
    stability_by_id = {str(row["claim_id"]): row for row in claim_rows}

    rows = []
    for claim_id, claim in sorted(claims.items()):
        endpoint_rows = [row for row in endpoints if row.claim_id == claim_id]
        rows.append(
            _framework_calls(
                claim,
                endpoint_rows,
                stability_by_id[claim_id],
                alpha,
            )
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = output_dir / "framework_comparison.csv"
    summary_path = output_dir / "framework_summary.csv"
    columns = [
        "claim_id",
        "dataset",
        "claim_text",
        "claim_type",
        "n_pipelines",
        "n_sample_sets",
        "n_planned_specifications",
        "n_testable",
        "n_missing_specifications",
        "specification_coverage",
        "significant_count",
        "majority_basis",
        "majority_support_fraction",
        "majority_call",
        "strict_call",
        "claimstab_grade",
        "claimstab_call",
        "claimstab_supported",
        "disagreement",
        "analysis_dependency",
        "inference_stability",
        "reconstruction_status",
        "rationale",
    ]
    _write_csv(comparison_path, rows, columns)

    summary = Counter()
    for row in rows:
        dataset = str(row["dataset"]) or "unspecified"
        for framework, field in (
            ("majority", "majority_call"),
            ("strict", "strict_call"),
        ):
            summary[(dataset, framework, str(row[field]))] += 1
        summary[
            (
                dataset,
                "claimstab",
                "supported" if row["claimstab_supported"] else "not_supported",
            )
        ] += 1
        summary[(dataset, "claimstab_grade", str(row["claimstab_grade"]))] += 1

    summary_rows = [
        {
            "dataset": dataset,
            "framework": framework,
            "call": call,
            "count": count,
        }
        for (dataset, framework, call), count in sorted(summary.items())
    ]
    _write_csv(
        summary_path,
        summary_rows,
        ["dataset", "framework", "call", "count"],
    )
    return {
        "framework_comparison": comparison_path,
        "framework_summary": summary_path,
    }
