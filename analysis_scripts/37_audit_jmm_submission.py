from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "投稿包_JMM_2026-10-30"
MANUSCRIPT = PACKAGE / "01_Manuscript" / "JMM_Manuscript_Anonymous.docx"
SUPPLEMENT = (
    PACKAGE / "05_Supplementary" / "JMM_Supplementary_Material.docx"
)
REPORT = PACKAGE / "08_Submission_Audit" / "JMM_Package_Audit.md"
JSON_REPORT = (
    PACKAGE / "08_Submission_Audit" / "JMM_Package_Audit.json"
)
MANIFEST = PACKAGE / "08_Submission_Audit" / "Submission_Package_Manifest.md"


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text))


def paragraph_after(doc: Document, heading: str, stop: str) -> str:
    paragraphs = [p.text.strip() for p in doc.paragraphs]
    start = paragraphs.index(heading)
    end = paragraphs.index(stop, start + 1)
    return " ".join(text for text in paragraphs[start + 1 : end] if text)


def xml_has_any(zf: zipfile.ZipFile, needle: str, files: list[str]):
    return any(
        needle in zf.read(name).decode("utf-8", errors="ignore")
        for name in files
        if name.endswith(".xml")
    )


def audit_docx(path: Path, manuscript: bool):
    doc = Document(path)
    result = {
        "file": path.name,
        "paragraphs": len(doc.paragraphs),
        "tables": len(doc.tables),
        "sections": len(doc.sections),
        "author": doc.core_properties.author,
        "last_modified_by": doc.core_properties.last_modified_by,
        "comments": doc.core_properties.comments,
    }
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        document_xml = zf.read("word/document.xml").decode("utf-8")
        result["has_page_field"] = any(
            " PAGE " in zf.read(name).decode("utf-8", errors="ignore")
            for name in names
            if re.fullmatch(r"word/footer\d+\.xml", name)
        )
        result["tracked_insertions"] = len(
            re.findall(r"<w:ins(?:\s|>)", document_xml)
        )
        result["tracked_deletions"] = len(
            re.findall(r"<w:del(?:\s|>)", document_xml)
        )
        result["comment_parts"] = [
            name for name in names if name.startswith("word/comments")
        ]
        result["drawing_count"] = document_xml.count("<w:drawing")
        result["line_number_rule_count"] = document_xml.count("<w:lnNumType")
        result["vertical_rule_count"] = sum(
            len(re.findall(r'<w:(?:left|right|insideV)[^>]*w:val="single"', block))
            for block in re.findall(r"<w:tcBorders>.*?</w:tcBorders>", document_xml)
        )
        result["cell_shading_count"] = document_xml.count("<w:shd")
        result["repeating_header_count"] = document_xml.count("<w:tblHeader")

    if manuscript:
        abstract = paragraph_after(doc, "Abstract", "Keywords")
        keywords_text = paragraph_after(doc, "Keywords", "1. Introduction")
        all_text = "\n".join(p.text for p in doc.paragraphs)
        result["abstract_words"] = word_count(abstract)
        result["keywords"] = [
            value.strip()
            for value in keywords_text.split(";")
            if value.strip()
        ]
        result["numbered_sections"] = all(
            heading in all_text
            for heading in (
                "1. Introduction",
                "2. Materials and methods",
                "3. Results",
                "4. Discussion",
                "5. Conclusion",
                "6. Data and code availability",
                "7. Declarations",
            )
        )
        result["figure_captions_present"] = all(
            f"Figure {number}" in all_text for number in (1, 2, 3)
        )
        result["tables_cited"] = all(
            f"Table {number}" in all_text for number in range(1, 6)
        )
        result["release_urls_present"] = (
            "https://github.com/Taozw410/qz-mic-data/releases/tag/v1.0.0"
            in all_text
            and "https://github.com/Taozw410/qz-mic-claimstab/releases/tag/v0.3.0"
            in all_text
        )
    return result


def main():
    manuscript = audit_docx(MANUSCRIPT, manuscript=True)
    supplement = audit_docx(SUPPLEMENT, manuscript=False)

    figure_files = sorted((PACKAGE / "04_Figures").glob("*.pdf"))
    figure_headers = {
        path.name: path.read_bytes()[:5] for path in figure_files
    }

    checks = {
        "abstract_under_250": manuscript["abstract_words"] <= 250,
        "keywords_1_to_7": 1 <= len(manuscript["keywords"]) <= 7,
        "numbered_sections": manuscript["numbered_sections"],
        "line_numbering_each_section": (
            manuscript["line_number_rule_count"] == manuscript["sections"]
            and supplement["line_number_rule_count"] == supplement["sections"]
        ),
        "page_field_present": (
            manuscript["has_page_field"] and supplement["has_page_field"]
        ),
        "no_tracked_changes": (
            manuscript["tracked_insertions"] == 0
            and manuscript["tracked_deletions"] == 0
            and supplement["tracked_insertions"] == 0
            and supplement["tracked_deletions"] == 0
        ),
        "no_comment_parts": (
            not manuscript["comment_parts"] and not supplement["comment_parts"]
        ),
        "no_embedded_images": (
            manuscript["drawing_count"] == 0
            and supplement["drawing_count"] == 0
        ),
        "tables_horizontal_rules_only": (
            manuscript["vertical_rule_count"] == 0
            and supplement["vertical_rule_count"] == 0
        ),
        "tables_unshaded": (
            manuscript["cell_shading_count"] == 0
            and supplement["cell_shading_count"] == 0
        ),
        "table_headers_repeat": (
            manuscript["repeating_header_count"] >= 5
            and supplement["repeating_header_count"] >= 4
        ),
        "all_figures_are_pdf": (
            len(figure_files) == 4
            and all(header == b"%PDF-" for header in figure_headers.values())
        ),
        "release_urls_in_manuscript": manuscript["release_urls_present"],
    }

    package_files = sorted(
        path for path in PACKAGE.rglob("*") if path.is_file()
    )
    inventory = [
        {
            "path": path.relative_to(PACKAGE).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in package_files
    ]

    payload = {
        "package": PACKAGE.name,
        "manuscript": manuscript,
        "supplement": supplement,
        "figures": {
            name: {
                "pdf_header": header.decode("ascii", errors="replace"),
                "bytes": (PACKAGE / "04_Figures" / name).stat().st_size,
            }
            for name, header in figure_headers.items()
        },
        "checks": checks,
        "files": inventory,
    }
    JSON_REPORT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# JMM submission package audit",
        "",
        f"- Package: `{PACKAGE.name}`",
        f"- Manuscript: {manuscript['paragraphs']} paragraphs, "
        f"{manuscript['tables']} tables, {manuscript['sections']} section",
        f"- Abstract: {manuscript['abstract_words']} words",
        f"- Keywords: {len(manuscript['keywords'])}",
        f"- Supplementary material: {supplement['tables']} tables, "
        f"{supplement['sections']} section",
        f"- Figure PDFs: {len(figure_files)}",
        "",
        "## Release gates",
        "",
        "| Check | Status |",
        "| --- | --- |",
    ]
    for name, passed in checks.items():
        lines.append(f"| `{name}` | {'PASS' if passed else 'FAIL'} |")

    lines.extend(
        [
            "",
            "## Author-supplied items still required",
            "",
            "- Final author names, order, affiliations, corresponding email,",
            "  telephone, full postal address, and ORCID.",
            "- Elsevier declarations tool output and final competing-interest",
            "  statement.",
            "- Complete CRediT roles.",
            "- Funding and acknowledgement text.",
            "- Final generative-AI disclosure.",
            "- Sequencing accession or archive identifier for raw reads.",
            "- Permanent archive DOI for the GitHub data and code releases, if",
            "  required by the journal or institution.",
            "",
            "## Machine-readable report",
            "",
            "`JMM_Package_Audit.json` contains the complete file inventory and hashes.",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")

    manifest_lines = [
        "# JMM submission package manifest",
        "",
        "Generated after the final package audit.",
        "",
        "| File | Size (bytes) | SHA256 |",
        "| --- | ---: | --- |",
    ]
    for path in sorted(
        path
        for path in PACKAGE.rglob("*")
        if path.is_file() and path != MANIFEST
    ):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_lines.append(
            f"| `{path.relative_to(PACKAGE).as_posix()}` | "
            f"{path.stat().st_size:,} | `{digest}` |"
        )
    MANIFEST.write_text(
        "\n".join(manifest_lines) + "\n",
        encoding="utf-8",
    )

    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise SystemExit(f"Audit failed: {', '.join(failed)}")
    print(f"PASS: {REPORT}")


if __name__ == "__main__":
    main()
