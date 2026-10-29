from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    columns = list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def number(value: str | None) -> float | None:
    text = "" if value is None else value.strip()
    if not text or text.upper() in {"NA", "NAN", "NULL"}:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def integer(value: str | None) -> int | None:
    parsed = number(value)
    return int(parsed) if parsed is not None else None


def parse_notes(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for token in text.split(";"):
        key, separator, value = token.partition("=")
        if separator:
            parsed[key.strip()] = value.strip()
    return parsed


def rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def select_primary_endpoint(rows: list[dict[str, str]]) -> dict[str, str]:
    preferred = ("OTU", "Genus", "Phylum", "GenusAll", "OTUall")
    for pipeline in preferred:
        matches = [row for row in rows if row.get("pipeline") == pipeline]
        if matches:
            return matches[0]
    return rows[0]


def build_claim_features(
    claims: list[dict[str, str]],
    endpoints: list[dict[str, str]],
    stability: list[dict[str, str]],
    comparison: list[dict[str, str]],
) -> list[dict[str, object]]:
    endpoints_by_claim: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in endpoints:
        endpoints_by_claim[row["claim_id"]].append(row)
    stability_by_id = {row["claim_id"]: row for row in stability}
    comparison_by_id = {row["claim_id"]: row for row in comparison}

    features = []
    for claim in claims:
        claim_id = claim["claim_id"]
        rows = endpoints_by_claim.get(claim_id, [])
        testable = [
            row for row in rows if row.get("testable", "").lower() == "true"
        ]
        p_values = [
            value
            for value in (number(row.get("p_value")) for row in testable)
            if value is not None
        ]
        estimates = [
            value
            for value in (number(row.get("estimate")) for row in rows)
            if value is not None
        ]
        note_values = [parse_notes(row.get("notes", "")) for row in rows]
        sample_sizes = [
            value
            for value in (integer(item.get("n")) for item in note_values)
            if value is not None
        ]
        group_counts = [
            value
            for value in (integer(item.get("k")) for item in note_values)
            if value is not None
        ]
        max_abs_effect = max((abs(value) for value in estimates), default=0.0)
        min_abs_effect = min((abs(value) for value in estimates), default=0.0)
        effect_retention = (
            min_abs_effect / max_abs_effect if max_abs_effect > 0 else None
        )
        claim_notes = parse_notes(claim.get("notes", ""))
        stability_row = stability_by_id[claim_id]
        comparison_row = comparison_by_id[claim_id]
        p_max = max(p_values) if p_values else None
        p_min = min(p_values) if p_values else None
        if p_max is None:
            margin_bin = "no_testable_result"
        elif p_max < 0.01:
            margin_bin = "max_p_lt_0.01"
        elif p_max < 0.05:
            margin_bin = "max_p_0.01_0.05"
        elif p_max < 0.10:
            margin_bin = "max_p_0.05_0.10"
        elif p_max < 0.20:
            margin_bin = "max_p_0.10_0.20"
        else:
            margin_bin = "max_p_ge_0.20"
        if effect_retention is None:
            retention_bin = "not_evaluable"
        elif effect_retention >= 0.70:
            retention_bin = "retention_ge_0.70"
        elif effect_retention >= 0.40:
            retention_bin = "retention_0.40_0.70"
        else:
            retention_bin = "retention_lt_0.40"
        features.append(
            {
                "claim_id": claim_id,
                "dataset": claim_notes.get("dataset", comparison_row["dataset"]),
                "family": claim_notes.get("family", ""),
                "metric": claim_notes.get("metric", ""),
                "condition": claim_notes.get("condition", ""),
                "n_endpoints": len(rows),
                "n_testable": len(testable),
                "n_planned_specifications": int(
                    comparison_row["n_planned_specifications"]
                ),
                "n_missing_specifications": int(
                    comparison_row["n_missing_specifications"]
                ),
                "specification_coverage": comparison_row[
                    "specification_coverage"
                ],
                "n_pipelines": int(comparison_row["n_pipelines"]),
                "n_sample_sets": int(comparison_row["n_sample_sets"]),
                "median_sample_n": statistics.median(sample_sizes)
                if sample_sizes
                else None,
                "min_sample_n": min(sample_sizes) if sample_sizes else None,
                "median_group_count": statistics.median(group_counts)
                if group_counts
                else None,
                "p_min": p_min,
                "p_max": p_max,
                "significant_fraction": number(
                    comparison_row["majority_support_fraction"]
                ),
                "min_effect": min_abs_effect,
                "max_effect": max_abs_effect,
                "effect_retention": effect_retention,
                "signal_margin": margin_bin,
                "effect_retention_bin": retention_bin,
                "majority_call": comparison_row["majority_call"],
                "strict_call": comparison_row["strict_call"],
                "claimstab_grade": comparison_row["claimstab_grade"],
                "claimstab_supported": comparison_row["claimstab_supported"],
                "claimstab_dependency": comparison_row["analysis_dependency"],
                "disagreement": comparison_row["disagreement"],
                "reconstruction_status": comparison_row["reconstruction_status"],
            }
        )
    return features


def aggregate_support(
    features: list[dict[str, object]],
    dataset_filter: set[str] | None = None,
) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in features:
        dataset = str(row["dataset"])
        if dataset_filter and dataset not in dataset_filter:
            continue
        key = (dataset, str(row["family"]), str(row["metric"]))
        groups[key].append(row)
    output = []
    for (dataset, family, metric), rows in sorted(groups.items()):
        supported = sum(str(row["claimstab_supported"]).lower() == "true" for row in rows)
        majority = sum(str(row["majority_call"]) == "supported" for row in rows)
        support_values = [
            float(row["significant_fraction"])
            for row in rows
            if row["significant_fraction"] is not None
        ]
        p_max_values = [
            float(row["p_max"]) for row in rows if row["p_max"] is not None
        ]
        retention_values = [
            float(row["effect_retention"])
            for row in rows
            if row["effect_retention"] is not None
        ]
        output.append(
            {
                "dataset": dataset,
                "family": family,
                "metric": metric,
                "n_claims": len(rows),
                "claimstab_supported": supported,
                "claimstab_support_rate": round(rate(supported, len(rows)), 6),
                "majority_supported": majority,
                "majority_support_rate": round(rate(majority, len(rows)), 6),
                "median_significant_fraction": round(
                    statistics.median(support_values), 6
                )
                if support_values
                else None,
                "median_p_max": round(statistics.median(p_max_values), 6)
                if p_max_values
                else None,
                "median_effect_retention": round(
                    statistics.median(retention_values), 6
                )
                if retention_values
                else None,
            }
        )
    return output


def condition_bins(features: list[dict[str, object]]) -> list[dict[str, object]]:
    dimensions = {
        "family": lambda row: row["family"],
        "metric": lambda row: row["metric"],
        "sample_set_variation": lambda row: "multiple"
        if int(row["n_sample_sets"]) > 1
        else "single",
        "pipeline_depth": lambda row: "three_or_more"
        if int(row["n_pipelines"]) >= 3
        else "two",
        "signal_margin": lambda row: row["signal_margin"],
        "effect_retention": lambda row: row["effect_retention_bin"],
        "sample_size": lambda row: "n_ge_100"
        if row["median_sample_n"] is not None
        and float(row["median_sample_n"]) >= 100
        else "n_lt_100",
    }
    output = []
    for dimension, getter in dimensions.items():
        groups: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in features:
            groups[str(getter(row))].append(row)
        for level, rows in sorted(groups.items()):
            supported = sum(
                str(row["claimstab_supported"]).lower() == "true" for row in rows
            )
            majority = sum(
                str(row["majority_call"]) == "supported" for row in rows
            )
            output.append(
                {
                    "dimension": dimension,
                    "level": level,
                    "n_claims": len(rows),
                    "claimstab_supported": supported,
                    "claimstab_support_rate": round(rate(supported, len(rows)), 6),
                    "majority_supported": majority,
                    "majority_support_rate": round(rate(majority, len(rows)), 6),
                }
            )
    return output


def normalize_pipeline(value: str) -> str:
    text = value.lower()
    if "phylum" in text:
        return "phylum_aggregation"
    if "family" in text:
        return "family_aggregation"
    if "genusfiltered" in text:
        return "genus_filtered"
    if "genusall" in text:
        return "genus_all"
    if "genus" in text:
        return "genus_aggregation"
    if "prev10" in text:
        return "otu_prevalence_10pct"
    if "rare500" in text:
        return "otu_rarefied_500"
    if "rare1500" in text or "rare889" in text:
        return "otu_rarefied_high"
    if text.startswith("otu"):
        return "otu_full"
    return value


def normalize_sample_set(value: str) -> str:
    text = value.lower()
    if "all" in text or "baseline" in text:
        return "full_sample_set"
    if "stratified" in text or "balanced" in text:
        return "balanced_subset"
    return "subgroup_or_sensitivity_set"


def endpoint_conditions(
    claims: list[dict[str, str]],
    endpoints: list[dict[str, str]],
) -> list[dict[str, object]]:
    claim_notes = {
        row["claim_id"]: parse_notes(row.get("notes", "")) for row in claims
    }
    public_datasets = {
        "GlobalPatterns",
        "enterotype",
        "soilrep",
        "atlas1006",
    }
    grouped: dict[
        tuple[str, str, str, str, str], list[dict[str, str]]
    ] = defaultdict(list)
    for row in endpoints:
        note = claim_notes.get(row["claim_id"], {})
        dataset = note.get("dataset", "")
        if dataset not in public_datasets:
            continue
        key = (
            dataset,
            note.get("family", ""),
            note.get("metric", ""),
            normalize_pipeline(row.get("pipeline", "")),
            normalize_sample_set(row.get("sample_set", "")),
        )
        grouped[key].append(row)

    output = []
    for (
        dataset,
        family,
        metric,
        pipeline_type,
        sample_set_class,
    ), rows in sorted(grouped.items()):
        testable = [
            row for row in rows if row.get("testable", "").lower() == "true"
        ]
        p_values = [
            value
            for value in (number(row.get("p_value")) for row in testable)
            if value is not None
        ]
        effects = [
            abs(value)
            for value in (number(row.get("estimate")) for row in rows)
            if value is not None
        ]
        significant = sum(
            value is not None and value < 0.05 for value in p_values
        )
        output.append(
            {
                "dataset": dataset,
                "family": family,
                "metric": metric,
                "pipeline_type": pipeline_type,
                "sample_set_class": sample_set_class,
                "n_endpoints": len(rows),
                "n_testable": len(testable),
                "significant_count": significant,
                "significant_rate": round(rate(significant, len(testable)), 6),
                "median_p": round(statistics.median(p_values), 6)
                if p_values
                else None,
                "median_abs_effect": round(statistics.median(effects), 6)
                if effects
                else None,
            }
        )
    return output


def permutation_rates(
    claims: list[dict[str, str]],
    comparison: list[dict[str, str]],
) -> list[dict[str, object]]:
    claim_notes = {
        row["claim_id"]: parse_notes(row.get("notes", "")) for row in claims
    }
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    dataset_grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    dataset_outer_permutations: dict[str, set[str]] = defaultdict(set)
    for row in comparison:
        note = claim_notes[row["claim_id"]]
        dataset = note.get("dataset", row["dataset"])
        family = note.get("family", "")
        metric = note.get("metric", "")
        grouped[(dataset, family, metric)].append(row)
        dataset_grouped[dataset].append(row)
        if note.get("permutation_id"):
            dataset_outer_permutations[dataset].add(
                note["permutation_id"]
            )

    output = []
    for dataset, rows in sorted(dataset_grouped.items()):
        total = len(rows)
        majority = sum(row["majority_call"] == "supported" for row in rows)
        strict = sum(row["strict_call"] == "supported" for row in rows)
        claimstab = sum(
            row["claimstab_supported"].lower() == "true" for row in rows
        )
        output.append(
            {
                "dataset": dataset,
                "family": "all",
                "metric": "all",
                "n_permuted_claims": total,
                "n_dataset_permutation_combinations": len(
                    dataset_outer_permutations[dataset]
                ),
                "majority_support_count_under_null": majority,
                "strict_support_count_under_null": strict,
                "claimstab_support_count_under_null": claimstab,
                "majority_support_rate_under_null": round(
                    rate(majority, total), 6
                ),
                "strict_support_rate_under_null": round(
                    rate(strict, total), 6
                ),
                "claimstab_support_rate_under_null": round(
                    rate(claimstab, total), 6
                ),
            }
        )
    for (dataset, family, metric), rows in sorted(grouped.items()):
        total = len(rows)
        majority = sum(row["majority_call"] == "supported" for row in rows)
        strict = sum(row["strict_call"] == "supported" for row in rows)
        claimstab = sum(
            row["claimstab_supported"].lower() == "true" for row in rows
        )
        output.append(
            {
                "dataset": dataset,
                "family": family,
                "metric": metric,
                "n_permuted_claims": total,
                "n_dataset_permutation_combinations": len(
                    dataset_outer_permutations[dataset]
                ),
                "majority_support_count_under_null": majority,
                "strict_support_count_under_null": strict,
                "claimstab_support_count_under_null": claimstab,
                "majority_support_rate_under_null": round(
                    rate(majority, total), 6
                ),
                "strict_support_rate_under_null": round(
                    rate(strict, total), 6
                ),
                "claimstab_support_rate_under_null": round(
                    rate(claimstab, total), 6
                ),
            }
        )
    for row in output:
        row["absolute_reduction_vs_majority"] = round(
            float(row["majority_support_rate_under_null"])
            - float(row["claimstab_support_rate_under_null"]),
            6,
        )
        majority_rate = float(row["majority_support_rate_under_null"])
        claimstab_rate = float(row["claimstab_support_rate_under_null"])
        row["relative_reduction_vs_majority"] = (
            round((majority_rate - claimstab_rate) / majority_rate, 6)
            if majority_rate > 0
            else None
        )
    return output


def markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column, "")
            if isinstance(value, float):
                value = fmt(value)
            values.append("" if value is None else str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_report(
    path: Path,
    manifest: list[dict[str, str]],
    features: list[dict[str, object]],
    endpoint_summary: list[dict[str, object]],
    perm_rates: list[dict[str, object]],
    condition_rows: list[dict[str, object]],
    endpoint_condition_rows: list[dict[str, object]],
) -> None:
    public_datasets = {
        "GlobalPatterns",
        "enterotype",
        "soilrep",
        "atlas1006",
    }
    public_features = [
        row for row in features if str(row["dataset"]) in public_datasets
    ]
    overall = [
        row for row in perm_rates if row["family"] == "all"
    ]
    margin_groups = [
        row
        for row in condition_rows
        if row["dimension"] == "signal_margin"
    ]
    dataset_summary = []
    for dataset in sorted(public_datasets):
        dataset_rows = [
            row for row in public_features if row["dataset"] == dataset
        ]
        supported = sum(
            str(row["claimstab_supported"]).lower() == "true"
            for row in dataset_rows
        )
        majority = sum(
            row["majority_call"] == "supported" for row in dataset_rows
        )
        dataset_summary.append(
            {
                "dataset": dataset,
                "claims": len(dataset_rows),
                "majority_supported": majority,
                "claimstab_supported": supported,
                "majority_only": sum(
                    row["disagreement"] == "majority_overconfident"
                    for row in dataset_rows
                ),
            }
        )
    lines = [
        "# Multi-dataset claim-stability benchmark",
        "",
        "This report is generated from public microbiome datasets distributed",
        "with the `phyloseq` and `microbiome` R packages. It evaluates",
        "endpoint-specific stability; it does not claim to rediscover a new",
        "microbial ecological mechanism.",
        "",
        "## Datasets",
        "",
        markdown_table(
            manifest,
            ["dataset", "citation", "doi", "platform", "samples_used", "contrast"],
        ),
        "",
        "## Framework comparison on observed labels",
        "",
        markdown_table(
            dataset_summary,
            [
                "dataset",
                "claims",
                "majority_supported",
                "claimstab_supported",
                "majority_only",
            ],
        ),
        "",
        "`majority_only` counts claims that an unweighted majority-of-specifications",
        "rule calls supported while the four-component claimstab grade does not.",
        "",
        "## Permuted-label negative controls",
        "",
        markdown_table(
            overall,
            [
                "dataset",
                "n_permuted_claims",
                "n_dataset_permutation_combinations",
                "majority_support_count_under_null",
                "strict_support_count_under_null",
                "claimstab_support_count_under_null",
                "majority_support_rate_under_null",
                "strict_support_rate_under_null",
                "claimstab_support_rate_under_null",
                "absolute_reduction_vs_majority",
            ],
        ),
        "",
        "Each dataset was evaluated under 20 outer label permutations. Five",
        "claim evaluations were generated per dataset-permutation, yielding 400",
        "nested evaluations within 80 dataset-permutation combinations. These",
        "evaluations are not independent Bernoulli trials.",
        "",
        "## Endpoint-type summary",
        "",
        markdown_table(
            endpoint_summary,
            [
                "dataset",
                "family",
                "metric",
                "n_claims",
                "claimstab_support_rate",
                "majority_support_rate",
                "median_p_max",
                "median_effect_retention",
            ],
        ),
        "",
        "## Empirical conditions",
        "",
        "The condition table is descriptive. It identifies where support is",
        "observed in this benchmark and is not a universal causal law.",
        "",
        markdown_table(
            margin_groups,
            [
                "dimension",
                "level",
                "n_claims",
                "claimstab_supported",
                "claimstab_support_rate",
                "majority_support_rate",
            ],
        ),
        "",
        "### Pipeline and sample-set conditions",
        "",
        markdown_table(
            endpoint_condition_rows,
            [
                "dataset",
                "family",
                "metric",
                "pipeline_type",
                "sample_set_class",
                "n_testable",
                "significant_rate",
                "median_p",
                "median_abs_effect",
            ],
        ),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--claimstab-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(args.claimstab_root / "src"))
    from claimstab.core import build_claim_stability, compare_claim_frameworks

    benchmark_root = args.benchmark_root
    main_dir = benchmark_root / "main"
    perm_dir = benchmark_root / "permutation"
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    build_claim_stability(
        main_dir / "claims.csv",
        main_dir / "reconstruction.csv",
        main_dir / "endpoints.csv",
        output_dir / "main_stability",
    )
    compare_claim_frameworks(
        main_dir / "claims.csv",
        main_dir / "reconstruction.csv",
        main_dir / "endpoints.csv",
        output_dir / "main_comparison",
    )
    build_claim_stability(
        perm_dir / "claims.csv",
        perm_dir / "reconstruction.csv",
        perm_dir / "endpoints.csv",
        output_dir / "permutation_stability",
    )
    compare_claim_frameworks(
        perm_dir / "claims.csv",
        perm_dir / "reconstruction.csv",
        perm_dir / "endpoints.csv",
        output_dir / "permutation_comparison",
    )

    claims = read_csv(main_dir / "claims.csv")
    endpoints = read_csv(main_dir / "endpoints.csv")
    stability = read_csv(output_dir / "main_stability" / "claim_stability_matrix.csv")
    comparison = read_csv(
        output_dir / "main_comparison" / "framework_comparison.csv"
    )
    perm_claims = read_csv(perm_dir / "claims.csv")
    perm_comparison = read_csv(
        output_dir / "permutation_comparison" / "framework_comparison.csv"
    )
    manifest = read_csv(benchmark_root / "dataset_manifest.csv")

    features = build_claim_features(claims, endpoints, stability, comparison)
    public_datasets = {
        "GlobalPatterns",
        "enterotype",
        "soilrep",
        "atlas1006",
    }
    endpoint_summary = aggregate_support(features, public_datasets)
    conditions = condition_bins(
        [row for row in features if str(row["dataset"]) in public_datasets]
    )
    endpoint_conditions_rows = endpoint_conditions(claims, endpoints)
    perm_rates = permutation_rates(perm_claims, perm_comparison)
    overconfident = [
        row
        for row in features
        if row["disagreement"] in {"majority_overconfident", "strict_overconfident"}
    ]

    write_csv(output_dir / "claim_condition_features.csv", features)
    write_csv(output_dir / "endpoint_type_summary.csv", endpoint_summary)
    write_csv(output_dir / "condition_summary.csv", conditions)
    write_csv(
        output_dir / "endpoint_condition_summary.csv",
        endpoint_conditions_rows,
    )
    write_csv(output_dir / "permutation_support_summary.csv", perm_rates)
    write_csv(output_dir / "framework_overconfident_claims.csv", overconfident)
    write_report(
        output_dir / "benchmark_report.md",
        manifest,
        features,
        endpoint_summary,
        perm_rates,
        conditions,
        endpoint_conditions_rows,
    )
    print(f"Claims: {len(features)}")
    print(f"Permutation claims: {len(perm_comparison)}")
    print(f"Report: {output_dir / 'benchmark_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
