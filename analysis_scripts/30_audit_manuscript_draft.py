from __future__ import annotations

import re
import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SECTION_DIR = ROOT / "05_稿件"
MASTER = SECTION_DIR / "10_MASTER_draft_en.md"
REPORT = SECTION_DIR / "12_稿件事务审计.md"

REQUIRED_HEADINGS = [
    "## Abstract",
    "## Introduction",
    "## Materials and methods",
    "## Results",
    "## Discussion",
    "## Conclusion",
    "# References",
    "# Declarations",
]

DISALLOWED_PATTERNS = [
    r"independent validation",
    r"independent replication",
    r"AEFP is the optimal",
    r"AEFP is confirmed",
    r"original results were false",
    r"no biological effect",
    r"proves causality",
]

EXPECTED_CITATIONS = [
    "Tao et al. (2024)",
    "Arumugam et al., 2011",
    "Callahan et al., 2016",
    "Callahan et al., 2017",
    "Caporaso et al., 2011",
    "Chiarello et al., 2022",
    "Eisenhauer et al., 2017",
    "Fernandes et al., 2014",
    "Gann et al., 2019",
    "Gloor et al., 2017",
    "Glöckner et al., 2017",
    "Knight et al., 2018",
    "Lahti et al., 2014",
    "Lin & Peddada, 2024",
    "McLaren & Callahan, 2021",
    "McMurdie & Holmes, 2013",
    "Nearing et al., 2022",
    "Oksanen et al., 2026",
    "Prober et al., 2015",
    "Quast et al., 2013",
    "Simonsohn et al., 2020",
    "Steegen et al., 2016",
    "UNITE Community, 2025",
    "Weiss et al., 2017",
    "Yang et al., 2017",
    "Yilmaz et al., 2014",
    "Zhou et al., 2011",
]

EXPECTED_REFERENCE_SURNAMES = [
    "Tao, Z.",
    "Arumugam, M.",
    "Callahan, B. J.",
    "Caporaso, J. G.",
    "Chiarello, M.",
    "Eisenhauer, N.",
    "Fernandes, A. D.",
    "Gann, G. D.",
    "Gloor, G. B.",
    "Glöckner, F. O.",
    "Knight, R.",
    "Lahti, L.",
    "Lin, H.",
    "McLaren, M. R.",
    "McMurdie, P. J.",
    "Nearing, J. T.",
    "Oksanen, J.",
    "Prober, S. M.",
    "Quast, C.",
    "Simonsohn, U.",
    "Steegen, S.",
    "UNITE Community.",
    "Weiss, S.",
    "Yang, T.",
    "Yilmaz, P.",
    "Zhou, J.",
]


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text))


def section(text: str, heading: str, next_heading_level: str = "##") -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    content_start = start + len(heading)
    next_match = re.search(
        rf"\n{re.escape(next_heading_level)} ",
        text[content_start:],
    )
    if next_match is None:
        return text[content_start:]
    return text[content_start : content_start + next_match.start()]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    text = MASTER.read_text(encoding="utf-8")
    flat_text = re.sub(r"\s+", " ", text)
    reference_text = (SECTION_DIR / "06_references_verified.md").read_text(
        encoding="utf-8"
    )
    bib_text = (SECTION_DIR / "16_references_verified.bib").read_text(
        encoding="utf-8"
    )
    with (SECTION_DIR / "14_extended_reference_verification.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        verification_dois = {
            row["DOI"].strip() for row in csv.DictReader(handle)
        }
    lines = []
    passed = True

    lines.append("# Manuscript transaction audit")
    lines.append("")
    lines.append(f"- Total words: {word_count(text)}")
    lines.append(f"- Characters: {len(text)}")
    lines.append(f"- Em dashes: {text.count('—')}")
    lines.append(f"- Semicolons: {text.count(';')}")
    lines.append("")

    lines.append("## Required headings")
    for heading in REQUIRED_HEADINGS:
        ok = heading in text
        lines.append(f"- {'PASS' if ok else 'FAIL'}: `{heading}`")
        passed = passed and ok

    abstract_text = section(text, "## Abstract", "##")
    abstract_words = word_count(abstract_text)
    abstract_ok = 150 <= abstract_words <= 300
    lines.append("")
    lines.append("## Abstract")
    lines.append(f"- Words: {abstract_words}")
    lines.append(
        f"- {'PASS' if abstract_ok else 'FAIL'}: English abstract target 150–300 words"
    )
    passed = passed and abstract_ok

    lines.append("")
    lines.append("## Citation consistency")
    for citation in EXPECTED_CITATIONS:
        ok = citation in flat_text
        lines.append(f"- {'PASS' if ok else 'FAIL'}: in-text `{citation}`")
        passed = passed and ok
    for surname in EXPECTED_REFERENCE_SURNAMES:
        ok = surname in text
        lines.append(f"- {'PASS' if ok else 'FAIL'}: reference `{surname}`")
        passed = passed and ok

    reference_dois = set(
        value.rstrip(".,;")
        for value in re.findall(r"https://doi\.org/([^\s\)]+)", reference_text)
    )
    bib_dois = set(
        value.strip()
        for value in re.findall(r"doi\s*=\s*\{([^}]+)\}", bib_text, re.IGNORECASE)
    )
    lines.append(
        f"- Reference DOI count: {len(reference_dois)}; BibTeX DOI count: {len(bib_dois)}"
    )
    lines.append(
        "- DOI set match: "
        + ("PASS" if reference_dois == bib_dois else "FAIL")
    )
    passed = passed and reference_dois == bib_dois
    lines.append(
        "- Verification-table DOI match: "
        + ("PASS" if reference_dois == verification_dois else "FAIL")
    )
    passed = passed and reference_dois == verification_dois

    lines.append("")
    lines.append("## Claim-boundary scan")
    for pattern in DISALLOWED_PATTERNS:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        ok = len(matches) == 0
        lines.append(f"- {'PASS' if ok else 'REVIEW'}: `{pattern}` ({len(matches)})")

    lines.append("")
    lines.append("## Assets")
    figure_path = (
        ROOT
        / "04_图表"
        / "14_分析可重复性"
        / "pipeline_endpoint_sensitivity.png"
    )
    figure_s1_path = (
        ROOT
        / "04_图表"
        / "14_分析可重复性"
        / "alpha_18sample_sensitivity.png"
    )
    figure_2_path = (
        ROOT
        / "04_图表"
        / "14_分析可重复性"
        / "claimstab_framework.png"
    )
    figure_3_path = (
        ROOT
        / "04_图表"
        / "15_多数据集框架验证"
        / "multidataset_claim_stability.png"
    )
    lines.append(f"- Figure exists: {'PASS' if figure_path.exists() else 'FAIL'}")
    lines.append(
        f"- Figure S1 exists: {'PASS' if figure_s1_path.exists() else 'FAIL'}"
    )
    lines.append(f"- Figure 2 exists: {'PASS' if figure_2_path.exists() else 'FAIL'}")
    lines.append(f"- Figure 2 in master: {'PASS' if '## Figure 2' in text else 'FAIL'}")
    lines.append(f"- Figure 3 exists: {'PASS' if figure_3_path.exists() else 'FAIL'}")
    lines.append(f"- Figure 3 in master: {'PASS' if '## Figure 3' in text else 'FAIL'}")
    passed = passed and figure_path.exists()
    passed = passed and figure_s1_path.exists()
    passed = passed and figure_2_path.exists() and "## Figure 2" in text
    passed = passed and figure_3_path.exists() and "## Figure 3" in text
    for table_number in (1, 2, 3, 4, 5):
        ok = f"## Table {table_number}." in text
        lines.append(f"- Table {table_number} in master: {'PASS' if ok else 'FAIL'}")
        passed = passed and ok
    table_s1_ok = "## Table S1." in text
    lines.append(f"- Table S1 in master: {'PASS' if table_s1_ok else 'FAIL'}")
    passed = passed and table_s1_ok
    table_s2_ok = "## Table S2." in text
    lines.append(f"- Table S2 in master: {'PASS' if table_s2_ok else 'FAIL'}")
    passed = passed and table_s2_ok
    table_s3_ok = "## Table S3." in text
    lines.append(f"- Table S3 in master: {'PASS' if table_s3_ok else 'FAIL'}")
    passed = passed and table_s3_ok
    table_s4_ok = "## Table S4." in text
    lines.append(f"- Table S4 in master: {'PASS' if table_s4_ok else 'FAIL'}")
    passed = passed and table_s4_ok

    lines.append("")
    lines.append(f"**Overall structural status: {'PASS' if passed else 'CHECK'}**")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(REPORT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
