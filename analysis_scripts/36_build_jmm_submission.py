from __future__ import annotations

import hashlib
import importlib.util
import re
import shutil
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "05_稿件" / "10_MASTER_draft_en.md"
PACKAGE = ROOT / "投稿包_JMM_2026-10-30"

MANUSCRIPT_DIR = PACKAGE / "01_Manuscript"
TITLE_DIR = PACKAGE / "02_Title_Page"
COVER_DIR = PACKAGE / "03_Cover_Letter"
FIGURE_DIR = PACKAGE / "04_Figures"
SUPPLEMENT_DIR = PACKAGE / "05_Supplementary"
DECLARATION_DIR = PACKAGE / "06_Declarations_and_CRediT"
DATA_CODE_DIR = PACKAGE / "07_Data_and_Code"
AUDIT_DIR = PACKAGE / "08_Submission_Audit"

JMM_TITLE = (
    "Claimstab: a reconstruction-aware framework for endpoint-specific "
    "reproducibility of microbiome claims"
)

DATA_RELEASE_URL = (
    "https://github.com/Taozw410/qz-mic-data/releases/tag/v1.0.0"
)
CODE_RELEASE_URL = (
    "https://github.com/Taozw410/qz-mic-claimstab/releases/tag/v0.3.0"
)

AUTHORS = [
    ("ZiWei Tao", "a", "taozw@gxust.edu.cn", "0000-0003-0310-748X"),
    ("Jian Xie", "a", "guangxixiejian@gxust.edu.cn", ""),
    ("Fan Yang", "b", "489486943@qq.com", ""),
]

AFFILIATIONS = {
    "a": (
        "Guangxi University of Science and Technology, Guangxi Colleges and "
        "Universities Key Laboratory of Intelligent Computing and Distributed "
        "Information Processing, 2 Wenchang Road, Chengzhong District, "
        "Liuzhou, Guangxi 545006, China"
    ),
    "b": (
        "Zhejiang University of Water Resources and Electric Power, 508 No. 2 "
        "Street, Xiasha Higher Education Park, Qiantang District, Hangzhou, "
        "Zhejiang 310018, China"
    ),
}

COI_STATEMENT = (
    "The authors declare that they have no known competing financial interests "
    "or personal relationships that could have appeared to influence the work "
    "reported in this paper."
)

AI_STATEMENT = (
    "Generative AI tools were used to assist with language editing and "
    "translation during the preparation of this manuscript. All AI-assisted "
    "output was carefully reviewed, verified, and edited by the authors, who "
    "take full responsibility for the accuracy, originality, and integrity of "
    "the content."
)

JMM_ABSTRACT = """
Microbiome conclusions often depend on incompletely reported preprocessing and
analytical choices. We developed claimstab, a four-component framework that
separates data reconstruction, dependence on analytical choices, inference
stability, and evidence grading, and applied it to archived 16S and ITS data
from a sown grassland and four public microbiome datasets. The grassland
analysis compared original phylum, alpha-diversity, and summary outputs with
DADA2 ASVs and phylum aggregation across 15 primary plots and an 18-sample
sensitivity set. We evaluated alpha diversity, Bray-Curtis and Aitchison
structure, reference distance, and phylum-level ALDEx2 and ANCOM-BC2 results.
ASV aggregation reconstructed 16S phylum composition closely and ITS
composition mostly closely. Shannon and Simpson null results were stable, and
11 of 12 P < 0.05 decisions were unchanged in the sensitivity set. In contrast,
observed richness changed between OTUs and ASVs. Treatment separation was
strong at ASV level but absent with phylum-level Bray-Curtis, and no phylum
passed both differential-abundance methods. Across 32 claims from four public
datasets, claimstab graded 12 as supported, the same number as a strict
all-specifications rule and fewer than a majority rule. The contribution is an
auditable assessment of which claims remain stable under specified choices,
not improved binary classification accuracy. Claimstab helps microbiologists
identify endpoint- and workflow-dependent conclusions before interpreting
ecological effects.
""".strip()

KEYWORDS = [
    "reproducibility",
    "microbiome",
    "claim stability",
    "analytical robustness",
    "data reconstruction",
    "multiverse analysis",
    "amplicon sequencing",
]

SECTION_NUMBERS = {
    "Introduction": 1,
    "Materials and methods": 2,
    "Results": 3,
    "Discussion": 4,
    "Conclusion": 5,
}

FIGURES = [
    (
        "Figure_1.pdf",
        ROOT
        / "04_图表"
        / "14_分析可重复性"
        / "pipeline_endpoint_sensitivity.pdf",
        "Main figure",
    ),
    (
        "Figure_2.pdf",
        ROOT / "04_图表" / "14_分析可重复性" / "claimstab_framework.pdf",
        "Main figure",
    ),
    (
        "Figure_3.pdf",
        ROOT
        / "04_图表"
        / "15_多数据集框架验证"
        / "multidataset_claim_stability.pdf",
        "Main figure",
    ),
    (
        "Figure_S1.pdf",
        ROOT
        / "04_图表"
        / "14_分析可重复性"
        / "alpha_18sample_sensitivity.pdf",
        "Supplementary figure",
    ),
]


def load_general_builder():
    path = ROOT / "02_脚本" / "35_build_general_docx.py"
    spec = importlib.util.spec_from_file_location("general_docx_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load builder: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GB = load_general_builder()
GB.BODY_SIZE = 11.0


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text))


def set_font(run, name: str, size: float, bold: bool | None = None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor(0, 0, 0)
    if bold is not None:
        run.bold = bold


def add_plain_hyperlink(paragraph, text: str, url: str, size: float = 11.0):
    part = paragraph.part
    relationship_id = part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)
    run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "1F4E79")
    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:ascii"), GB.BODY_FONT)
    fonts.set(qn("w:hAnsi"), GB.BODY_FONT)
    font_size = OxmlElement("w:sz")
    font_size.set(qn("w:val"), str(int(round(size * 2))))
    properties.extend([fonts, color, font_size])
    run.append(properties)
    text_element = OxmlElement("w:t")
    text_element.text = text
    run.append(text_element)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


GB.add_hyperlink = add_plain_hyperlink


def horizontal_cell_border(cell, color: str = "000000", size: int = 4):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        if edge in {"left", "right", "insideV"}:
            element.set(qn("w:val"), "nil")
        else:
            element.set(qn("w:val"), "single")
            element.set(qn("w:sz"), str(size))
            element.set(qn("w:space"), "0")
            element.set(qn("w:color"), color)


def no_shading(cell, fill: str):
    del cell, fill


GB.set_cell_border = horizontal_cell_border
GB.shade_cell = no_shading


def configure_section(section, landscape: bool = False, line_numbers: bool = True):
    section.orientation = WD_ORIENT.LANDSCAPE if landscape else WD_ORIENT.PORTRAIT
    if landscape:
        section.page_width = Cm(27.94)
        section.page_height = Cm(21.59)
        section.left_margin = Cm(1.8)
        section.right_margin = Cm(1.8)
        section.top_margin = Cm(1.8)
        section.bottom_margin = Cm(1.8)
    else:
        section.page_width = Cm(21.59)
        section.page_height = Cm(27.94)
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.2)
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
    section.header_distance = Cm(1.0)
    section.footer_distance = Cm(1.0)
    set_line_numbering(section, enabled=line_numbers)


def set_line_numbering(section, enabled: bool = True):
    sect_pr = section._sectPr
    existing = sect_pr.find(qn("w:lnNumType"))
    if not enabled:
        if existing is not None:
            sect_pr.remove(existing)
        return
    if existing is None:
        existing = OxmlElement("w:lnNumType")
        sect_pr.append(existing)
    existing.set(qn("w:countBy"), "1")
    existing.set(qn("w:start"), "1")
    existing.set(qn("w:restart"), "continuous")
    cols = sect_pr.find(qn("w:cols"))
    if cols is not None:
        cols.addprevious(existing)


def add_page_field(section):
    footer = section.footer
    footer.is_linked_to_previous = False
    paragraph = footer.paragraphs[0]
    paragraph.clear()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    set_font(run, "Arial", 8)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instruction, separate, text, end])


def configure_document(doc: Document, manuscript: bool = False):
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    title = doc.styles["Title"]
    title.font.name = "Arial"
    title._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    title._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    title.font.size = Pt(16 if manuscript else 20)
    title.font.bold = True
    title.font.color.rgb = RGBColor(0, 0, 0)
    title.paragraph_format.space_before = Pt(0)
    title.paragraph_format.space_after = Pt(12)
    title_properties = title._element.get_or_add_pPr()
    for border in title_properties.findall(qn("w:pBdr")):
        title_properties.remove(border)

    for style_name, size, before, after in (
        ("Heading 1", 13, 12, 6),
        ("Heading 2", 11.5, 9, 4),
        ("Heading 3", 11, 8, 3),
    ):
        style = doc.styles[style_name]
        style.font.name = "Arial"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        paragraph_properties = style._element.get_or_add_pPr()
        for border in paragraph_properties.findall(qn("w:pBdr")):
            paragraph_properties.remove(border)

    doc.core_properties.author = ""
    doc.core_properties.last_modified_by = ""
    doc.core_properties.comments = ""


def parse_master(text: str):
    lines = text.splitlines()
    title = JMM_TITLE
    blocks: dict[str, list[str]] = {}
    current_name: str | None = None
    current: list[str] = []

    def flush():
        nonlocal current_name, current
        if current_name is not None:
            blocks[current_name] = current
        current_name = None
        current = []

    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            flush()
            current_name = line[2:].strip()
            continue
        if line.startswith("## "):
            flush()
            current_name = line[3:].strip()
            continue
        if current_name is not None:
            current.append(line)
    flush()
    return title, blocks


def numbered_section(name: str, number: int, content: list[str]) -> list[str]:
    output = [f"## {number}. {name}", ""]
    subsection = 0
    for line in content:
        stripped = line.strip()
        if stripped.startswith("### "):
            subsection += 1
            output.append(f"### {number}.{subsection} {stripped[4:].strip()}")
        else:
            output.append(line)
    return output


def clean_figure_block(block: list[str]) -> list[str]:
    return [
        line
        for line in block
        if not line.strip().startswith("![")
    ]


def build_jmm_markdown(blocks: dict[str, list[str]]) -> tuple[str, str]:
    main: list[str] = [
        f"# {JMM_TITLE}",
        "",
        "## Abstract",
        "",
        JMM_ABSTRACT,
        "",
        "## Keywords",
        "",
        "; ".join(KEYWORDS),
        "",
    ]

    for name in (
        "Introduction",
        "Materials and methods",
        "Results",
        "Discussion",
        "Conclusion",
    ):
        main.extend(numbered_section(name, SECTION_NUMBERS[name], blocks[name]))
        main.append("")

    main.extend(
        [
            "## 6. Data and code availability",
            "",
            (
                "The analysis-ready QZ amplicon data, sample metadata, derived "
                "results, and SHA256 manifest are available in the versioned "
                f"data release at {DATA_RELEASE_URL}. The four public datasets "
                "are identified in Section 2 and in the reference list. Raw "
                "sequencing reads are available from the corresponding author "
                "on reasonable request because the original sequencing archive "
                "did not provide a stable public accession."
            ),
            "",
            (
                "claimstab 0.3.0 and the manuscript analysis code are available "
                f"in the versioned code release at {CODE_RELEASE_URL}. The "
                "release includes the installable wheel, source distribution, "
                "complete analysis scripts, schemas, tests, example inputs, and "
                "benchmark outputs under the MIT License."
            ),
            "",
            "## 7. Declarations",
            "",
            "**Funding.** This research did not receive any specific grant from "
            "funding agencies in the public, commercial, or not-for-profit "
            "sectors.",
            "",
            f"**Declaration of competing interest.** {COI_STATEMENT}",
            "",
            (
                "**CRediT author statement.** ZiWei Tao: Writing - original "
                "draft. Jian Xie: Data curation. Fan Yang: Conceptualization."
            ),
            "",
            (
                "**Declaration of generative AI and AI-assisted technologies in the "
                "manuscript preparation process.** "
                f"{AI_STATEMENT}"
            ),
            "",
            (
                "**Ethics approval and consent to participate.** This study "
                "reanalyzed existing soil microbial sequencing data from a field "
                "experiment and publicly available, de-identified human gut "
                "microbiome datasets. No new human participants or animals were "
                "involved."
            ),
            "",
            "**Consent for publication.** Not applicable.",
            "",
            "# References",
            "",
            *[line for line in blocks["References"] if line.strip()],
            "",
            "# Tables",
            "",
        ]
    )

    for table_number in range(1, 6):
        names = [
            name
            for name in blocks
            if name.startswith(f"Table {table_number}.")
        ]
        if not names:
            raise KeyError(f"Table {table_number} not found")
        main.append(f"## {names[0]}")
        main.append("")
        main.extend(blocks[names[0]])
        main.append("")

    main.extend(["# Figure captions", ""])
    for figure_number in range(1, 4):
        name = f"Figure {figure_number}"
        main.extend([f"## {name}", "", *clean_figure_block(blocks[name]), ""])

    main_markdown = "\n".join(main).strip() + "\n"

    supplementary: list[str] = [
        "# Supplementary material",
        "",
        (
            "Supplementary material for: "
            f"{JMM_TITLE}"
        ),
        "",
        "## Figure S1",
        "",
        *clean_figure_block(blocks["Figure S1"]),
        "",
    ]
    for table_name in (
        "Table S1. Alpha-diversity sensitivity",
        "Table S2. GlobalPatterns external case",
        "Table S3. Multi-dataset public benchmark",
        "Table S4. Cross-dataset endpoint and stability conditions",
    ):
        supplementary.extend([f"## {table_name}", "", *blocks[table_name], ""])
    supplement_markdown = "\n".join(supplementary).strip() + "\n"
    return main_markdown, supplement_markdown


def add_markdown_paragraph(doc: Document, text: str, size: float = 11.0):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.paragraph_format.line_spacing = 1.15
    GB.add_inline_markdown(paragraph, text, size=size)
    return paragraph


def add_markdown_body(
    doc: Document,
    markdown: str,
    landscape: bool = False,
    figure_captions: bool = False,
):
    lines = markdown.splitlines()
    paragraph_buffer: list[str] = []

    def flush():
        nonlocal paragraph_buffer
        if not paragraph_buffer:
            return
        text = re.sub(r"\s+", " ", " ".join(paragraph_buffer)).strip()
        if text:
            add_markdown_paragraph(doc, text)
        paragraph_buffer = []

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            flush()
            i += 1
            continue

        if stripped.startswith("# "):
            flush()
            heading = stripped[2:].strip()
            if heading not in {"References", "Tables", "Figure captions"}:
                title = doc.add_paragraph(style="Title")
                title.alignment = WD_ALIGN_PARAGRAPH.LEFT
                run = title.add_run(heading)
                set_font(run, "Arial", 16, bold=True)
            else:
                doc.add_page_break()
                doc.add_heading(heading, level=1)
                if heading == "References":
                    GB.mod_references_mode = True
            i += 1
            continue

        if stripped.startswith("## "):
            flush()
            heading = stripped[3:].strip()
            if heading.startswith("Table ") or (
                figure_captions and heading.startswith("Figure ")
            ):
                if heading.startswith("Table "):
                    doc.add_page_break()
                GB.add_caption(doc, heading)
            else:
                doc.add_heading(heading, level=1 if heading == "Abstract" else 2)
            i += 1
            continue

        if stripped.startswith("### "):
            flush()
            doc.add_heading(stripped[4:].strip(), level=3)
            i += 1
            continue

        if stripped.startswith("|"):
            flush()
            rows, next_i = GB.parse_markdown_table(lines, i)
            separator_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            alignments = GB.infer_alignments(separator_line, len(rows[0]))
            GB.add_table(doc, rows, alignments, landscape=landscape)
            i = next_i
            continue

        if "References" in markdown and i > markdown.splitlines().index("# References"):
            paragraph = doc.add_paragraph()
            paragraph.paragraph_format.left_indent = Cm(0.65)
            paragraph.paragraph_format.first_line_indent = Cm(-0.65)
            paragraph.paragraph_format.space_after = Pt(4)
            GB.add_inline_markdown(paragraph, stripped, size=9.4)
            i += 1
            continue

        paragraph_buffer.append(stripped)
        i += 1

    flush()


def new_doc(landscape: bool = False, line_numbers: bool = True) -> Document:
    doc = Document()
    configure_document(doc)
    configure_section(doc.sections[0], landscape=landscape, line_numbers=line_numbers)
    add_page_field(doc.sections[0])
    return doc


def save_doc(doc: Document, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)


def build_main_manuscript(markdown: str):
    doc = new_doc(landscape=False, line_numbers=True)
    doc.core_properties.title = JMM_TITLE
    doc.core_properties.subject = "Journal of Microbiological Methods submission"

    lines = markdown.splitlines()
    split_index = next(i for i, line in enumerate(lines) if line == "# Tables")
    body_markdown = "\n".join(lines[:split_index]).strip() + "\n"
    tail_markdown = "\n".join(lines[split_index:]).strip() + "\n"

    add_markdown_body(doc, body_markdown, landscape=False)
    add_markdown_body(
        doc,
        tail_markdown,
        landscape=False,
        figure_captions=True,
    )

    save_doc(doc, MANUSCRIPT_DIR / "JMM_Manuscript_Anonymous.docx")
    (MANUSCRIPT_DIR / "JMM_Manuscript_Anonymous.md").write_text(
        markdown,
        encoding="utf-8",
    )


def build_supplement(markdown: str):
    doc = new_doc(landscape=True, line_numbers=True)
    doc.core_properties.title = "Supplementary material"
    add_markdown_body(doc, markdown, landscape=True, figure_captions=True)
    save_doc(doc, SUPPLEMENT_DIR / "JMM_Supplementary_Material.docx")
    (SUPPLEMENT_DIR / "JMM_Supplementary_Material.md").write_text(
        markdown,
        encoding="utf-8",
    )


def add_label_value(doc: Document, label: str, value: str):
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(5)
    label_run = paragraph.add_run(f"{label}: ")
    set_font(label_run, "Arial", 10.5, bold=True)
    value_run = paragraph.add_run(value)
    set_font(value_run, "Times New Roman", 10.5)


def build_title_page():
    doc = new_doc(landscape=False, line_numbers=False)
    title = doc.add_paragraph(style="Title")
    run = title.add_run(JMM_TITLE)
    set_font(run, "Arial", 20, bold=True)
    for label, value in [
        ("Article type", "Research Article"),
        ("Journal", "Journal of Microbiological Methods"),
        ("Authors", "ZiWei Tao (a); Jian Xie (a); Fan Yang (b)"),
        (
            "Affiliation a",
            "Guangxi University of Science and Technology, Guangxi Colleges and "
            "Universities Key Laboratory of Intelligent Computing and Distributed "
            "Information Processing, 2 Wenchang Road, Chengzhong District, "
            "Liuzhou, Guangxi 545006, China",
        ),
        (
            "Affiliation b",
            "Zhejiang University of Water Resources and Electric Power, 508 No. 2 "
            "Street, Xiasha Higher Education Park, Qiantang District, Hangzhou, "
            "Zhejiang 310018, China",
        ),
        (
            "Corresponding author",
            "ZiWei Tao",
        ),
        ("Email", "taozw@gxust.edu.cn"),
        ("Telephone", "[TELEPHONE REQUIRED IN SUBMISSION SYSTEM]"),
        ("Postal address", AFFILIATIONS["a"]),
        ("Author email addresses", "taozw@gxust.edu.cn; guangxixiejian@gxust.edu.cn; 489486943@qq.com"),
        ("ORCID", "ZiWei Tao: 0000-0003-0310-748X"),
        ("Abstract word count", str(count_words(JMM_ABSTRACT))),
        ("Keywords", f"{len(KEYWORDS)}"),
        ("Review model", "Single anonymized"),
    ]:
        add_label_value(doc, label, value)
    save_doc(doc, TITLE_DIR / "JMM_Title_Page.docx")


def build_cover_letter():
    doc = new_doc(landscape=False, line_numbers=False)
    title = doc.add_paragraph(style="Title")
    run = title.add_run("Cover letter")
    set_font(run, "Arial", 20, bold=True)
    add_label_value(doc, "Date", "31 October 2026")
    add_label_value(doc, "To", "The Editors, Journal of Microbiological Methods")

    paragraphs = [
        "Dear Editors,",
        (
            f"We submit the Research Article entitled “{JMM_TITLE}” for "
            "consideration by the Journal of Microbiological Methods."
        ),
        (
            "Microbiome conclusions can change when feature resolution, "
            "normalization, distance, sample inclusion, or differential-abundance "
            "method changes. The manuscript separates four questions that are "
            "often combined: whether the required data layer can be reconstructed, "
            "how strongly an endpoint depends on analytical choices, whether the "
            "substantive claim remains stable, and what evidence grade should be "
            "reported."
        ),
        (
            "We applied the framework to archived bacterial and fungal amplicon "
            "data from a sown grassland and tested its portability across four "
            "independent public microbiome datasets. To make the analysis "
            "operational, we implemented the workflow in the open-source claimstab "
            "package and benchmarked it against majority and strict "
            "all-specifications rules. The framework does not claim improved "
            "binary accuracy. Its contribution is an auditable report of analysis "
            "dependence, reconstruction status, threshold-crossing endpoints, and "
            "evidence grade."
        ),
        (
            "The article matches the journal’s scope in microbial ecology, "
            "high-throughput sequencing, bioinformatics, and validation of "
            "analytical methods. It contributes a reusable way to evaluate whether "
            "microbiome claims are stable enough for ecological interpretation."
        ),
        (
            "The manuscript is not published or under consideration elsewhere. "
            "All authors have reviewed and approved the submitted version. The "
            "authors report no competing interests and no specific funding support."
        ),
        "Sincerely,",
        (
            "ZiWei Tao (Corresponding author)\n"
            "Guangxi University of Science and Technology\n"
            "taozw@gxust.edu.cn\n"
            "ORCID: 0000-0003-0310-748X"
        ),
    ]
    for text in paragraphs:
        add_markdown_paragraph(doc, text)
    save_doc(doc, COVER_DIR / "JMM_Cover_Letter.docx")


def build_declarations():
    doc = new_doc(landscape=False, line_numbers=False)
    title = doc.add_paragraph(style="Title")
    run = title.add_run("Author declarations and CRediT statement")
    set_font(run, "Arial", 20, bold=True)

    doc.add_heading("CRediT author statement", level=1)
    for text in (
        "ZiWei Tao: Writing - original draft.",
        "Jian Xie: Data curation.",
        "Fan Yang: Conceptualization.",
    ):
        paragraph = doc.add_paragraph(style="List Bullet")
        paragraph.add_run(text)

    doc.add_heading("Funding", level=1)
    doc.add_paragraph(
        "This research did not receive any specific grant from funding agencies "
        "in the public, commercial, or not-for-profit sectors."
    )

    doc.add_heading("Declaration of competing interest", level=1)
    doc.add_paragraph(COI_STATEMENT)

    doc.add_heading("Data and code availability", level=1)
    doc.add_paragraph(
        f"Data release: {DATA_RELEASE_URL}. "
        f"Code release: {CODE_RELEASE_URL}. "
        "Code license: MIT. Data license: CC BY 4.0. "
        "Raw sequencing reads are available from the corresponding author on "
        "reasonable request because the original sequencing archive did not "
        "provide a stable public accession."
    )

    doc.add_heading("Generative AI declaration", level=1)
    doc.add_paragraph(AI_STATEMENT)

    doc.add_heading("Ethics approval and consent to participate", level=1)
    doc.add_paragraph(
        "This study reanalyzed existing soil microbial sequencing data from a "
        "field experiment and publicly available, de-identified human gut "
        "microbiome datasets. No new human participants or animals were involved."
    )

    doc.add_heading("Consent for publication", level=1)
    doc.add_paragraph("Not applicable.")
    save_doc(doc, DECLARATION_DIR / "JMM_Declarations_and_CRediT.docx")


def copy_figures_and_code():
    for filename, source, _ in FIGURES:
        if not source.exists():
            raise FileNotFoundError(source)
        shutil.copy2(source, FIGURE_DIR / filename)

    claimstab_dist = ROOT / "07_可复用框架" / "claimstab" / "dist"
    for filename in (
        "claimstab-0.3.0-py3-none-any.whl",
        "claimstab-0.3.0-source.tar.gz",
        "claimstab-0.3.0-source.zip",
        "SHA256SUMS.txt",
    ):
        source = claimstab_dist / filename
        if source.exists():
            shutil.copy2(source, DATA_CODE_DIR / filename)


def write_support_files(main_markdown: str, supplement_markdown: str):
    abstract_words = count_words(JMM_ABSTRACT)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    (AUDIT_DIR / "JMM_Author_Guide_Audit.md").write_text(
        "\n".join(
            [
                "# JMM author-guide audit",
                "",
                "Source: ScienceDirect Guide for Authors for Journal of Microbiological Methods, accessed 31 October 2026.",
                "",
                "| Requirement | Current package | Status |",
                "| --- | --- | --- |",
                "| Research Article; no journal word limit | Manuscript supplied as Research Article; text retained because methods require detail | PASS |",
                f"| Abstract no more than 250 words | {abstract_words} words | PASS |",
                f"| Keywords 1-7 | {len(KEYWORDS)} keywords | PASS |",
                "| Editable DOCX, single-column layout | Main manuscript and supplementary material are editable DOCX | PASS |",
                "| Numbered sections and subsections | Main sections 1-7 and subsections are numbered | PASS |",
                "| Continuous line numbering | OOXML line numbering enabled in manuscript and supplementary files | PASS |",
                "| Tables editable, no vertical rules or shading | Tables are native Word tables with horizontal rules only | PASS |",
                "| Figures supplied separately | Figure 1, Figure 2, Figure 3, and Figure S1 are separate PDF files | PASS |",
                "| Figure captions | Captions are present in the manuscript and supplementary material | PASS |",
                "| Data are deposited and cited | Public v1.0.0 data discovery release and v0.3.0 code release are cited; raw reads use the journal's documented access exception | PASS WITH NOTE |",
                "| Title page with authors, affiliations, corresponding email | Names, order, affiliations, email, postal addresses, and ORCID supplied | PASS EXCEPT TELEPHONE |",
                "| CRediT statement | Completed from the supplied author contribution text | PASS |",
                "| Funding and competing-interest declarations | Statements completed; Elsevier declarations tool still requires entry | AUTHOR ACTION REQUIRED |",
                "| Generative-AI declaration | Supplied author statement inserted verbatim | PASS |",
                "| Open-access choice | Use subscription route if no APC is available | AUTHOR ACTION REQUIRED |",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (AUDIT_DIR / "Author_Action_Required.md").write_text(
        """# Author action required before submission

1. Enter the corresponding-author telephone number in the submission system
   and title page.
2. Enter the completed statements in Elsevier's declarations tool and upload
   the generated declaration document.
3. All authors should confirm the final author order, CRediT roles, funding
   statement, competing-interest statement, and generative-AI statement.
4. At submission, choose the subscription route if the requirement is zero
   author payment. Do not select gold open access unless an APC is funded.
5. Optionally provide suggested reviewers and opposed reviewers.
6. Run a final spelling and reference check in the submission system.
""",
        encoding="utf-8",
    )

    (DATA_CODE_DIR / "README_DEPOSITION.md").write_text(
        """# Data and code deposition

The public archives are:

- Data: https://github.com/Taozw410/qz-mic-data/releases/tag/v1.0.0
- Code: https://github.com/Taozw410/qz-mic-claimstab/releases/tag/v0.3.0

The package also includes the `claimstab` 0.3.0 wheel and source archives.

Before submission:

1. Archive both GitHub releases in Zenodo only if the journal, institution, or
   funder requires a DOI in addition to the versioned GitHub release.
2. Raw sequencing reads are available from the corresponding author on
   reasonable request, as stated in the manuscript and declarations.
""",
        encoding="utf-8",
    )

    (AUDIT_DIR / "JMM_Author_Guide_Excerpt.md").write_text(
        """# JMM requirements used in this package

- Article type: Research Article; no imposed word limit.
- Abstract: maximum 250 words.
- Keywords: 1 to 7.
- Source files: editable DOCX or TeX; PDF is not an acceptable source file.
- Layout: single-column Word layout.
- Sections: clearly numbered; subsections use 1.1, 1.1.1, and similar.
- Line numbering: continuous line numbering in the manuscript.
- Tables: editable text, captions included, no vertical rules or shading.
- Figures: separate files, logical names, captions in the manuscript.
- Vector artwork: EPS or PDF.
- Research data: Option C applies. Deposit data, cite and link it, or explain why
  sharing is not possible.
- Required declarations: competing interests, funding, CRediT, and generative AI
  where applicable.
- Review model: single anonymized.
""",
        encoding="utf-8",
    )

    manifest_path = AUDIT_DIR / "Submission_Package_Manifest.md"
    files = sorted(
        path
        for path in PACKAGE.rglob("*")
        if path.is_file() and path != manifest_path
    )
    lines = [
        "# JMM submission package manifest",
        "",
        "Generated 31 October 2026.",
        "",
        "| File | Purpose | Size | SHA256 |",
        "| --- | --- | ---: | --- |",
    ]
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        relative = path.relative_to(PACKAGE).as_posix()
        purpose = {
            ".docx": "Editable submission document",
            ".md": "Instructions, source, or audit",
            ".pdf": "Separate vector figure",
            ".zip": "Software source archive",
            ".gz": "Software source archive",
            ".whl": "Installable software archive",
            ".txt": "Checksums",
        }.get(path.suffix, "Supporting file")
        lines.append(
            f"| `{relative}` | {purpose} | {path.stat().st_size:,} | `{digest}` |"
        )
    manifest_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    (PACKAGE / "00_READ_ME.md").write_text(
        "\n".join(
            [
                "# Journal of Microbiological Methods submission package",
                "",
                f"Article: {JMM_TITLE}",
                "",
                "Start with `08_Submission_Audit/Author_Action_Required.md`.",
                "",
                "The manuscript has been adjusted to the current JMM guide:",
                f"- Abstract: {abstract_words} words (limit 250).",
                f"- Keywords: {len(KEYWORDS)} (limit 7).",
                "- Numbered sections and continuous line numbering.",
                "- Editable tables without vertical rules or cell shading.",
                "- Separate vector figure files with captions in the manuscript.",
                "- Anonymous manuscript plus a separate title page.",
                "- Single-column editable DOCX source files.",
                "",
                "Submission remains blocked only by the corresponding-author",
                "telephone number, entry of the prepared statements in Elsevier's",
                "declarations tool, and the author's choice of subscription versus",
                "funded open access.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main():
    if count_words(JMM_ABSTRACT) > 250:
        raise ValueError(f"Abstract exceeds 250 words: {count_words(JMM_ABSTRACT)}")
    if len(KEYWORDS) > 7:
        raise ValueError("Too many keywords")

    for folder in (
        MANUSCRIPT_DIR,
        TITLE_DIR,
        COVER_DIR,
        FIGURE_DIR,
        SUPPLEMENT_DIR,
        DECLARATION_DIR,
        DATA_CODE_DIR,
        AUDIT_DIR,
    ):
        folder.mkdir(parents=True, exist_ok=True)

    _, blocks = parse_master(MASTER.read_text(encoding="utf-8"))
    main_markdown, supplement_markdown = build_jmm_markdown(blocks)

    copy_figures_and_code()
    build_main_manuscript(main_markdown)
    build_supplement(supplement_markdown)
    build_title_page()
    build_cover_letter()
    build_declarations()
    write_support_files(main_markdown, supplement_markdown)
    print(f"Built {PACKAGE}")
    print(f"Abstract words: {count_words(JMM_ABSTRACT)}")


if __name__ == "__main__":
    main()
