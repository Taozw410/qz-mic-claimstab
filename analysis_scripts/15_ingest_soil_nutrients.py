from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from docx import Document


ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT.parent
DOCX_PATH = PROJECT_ROOT / "数据" / "原始数据" / "土壤养分结果.docx"
OUTPUT_DIR = ROOT / "03_结果" / "10_土壤养分核查"

ANALYTES = {
    "pH值": ("pH", "水:土 2.5:1", "pH"),
    "有机质": ("OrganicMatter", "g/kg", "有机质"),
    "碱解氮": ("AlkaliHydrolyzableN", "mg/kg", "碱解氮"),
    "有效磷": ("AvailableP", "mg/kg", "有效磷"),
    "速效钾": ("AvailableK", "mg/kg", "速效钾"),
    "全氮": ("TotalN", "g/kg", "全氮"),
    "全磷": ("TotalP", "g/kg", "全磷"),
    "全钾": ("TotalK", "g/kg", "全钾"),
    "水分": ("Moisture", "%", "水分"),
}

TREATMENT_BY_SAMPLE = {
    **{str(i): f"T{i}" for i in range(1, 22)},
    "3-2": "T3",
    "6-2": "T6",
    "22": "T22",
    "22-2": "T22",
    "23": "EXTERNAL_ROADSIDE_BARE",
    "24": "T23",
    "25": "UNKNOWN",
}


def normalize_sample_id(value: object) -> str:
    text = str(value).strip()
    if re.fullmatch(r"\d+\.0", text):
        return text.split(".")[0]
    return text


def parse_value(raw: object) -> tuple[float | None, str]:
    if raw is None:
        return None, "missing"
    text = str(raw).strip()
    if not text:
        return None, "missing"
    try:
        return float(text), "parsed"
    except ValueError:
        # Preserve ambiguous entries such as 69.7（150） rather than choosing a value.
        return None, "ambiguous_source_value"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    document = Document(DOCX_PATH)
    long_rows = []
    for table_index, table in enumerate(document.tables):
        matrix = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        sample_ids = [normalize_sample_id(value) for value in matrix[0][1:]]
        for row in matrix[1:]:
            analyte_label = row[0].replace("\n", " ").strip()
            analyte_key = next(
                (key for key in ANALYTES if analyte_label.startswith(key)),
                None,
            )
            if analyte_key is None:
                continue
            variable, unit, analyte_zh = ANALYTES[analyte_key]
            for sample_id, raw_value in zip(sample_ids, row[1:]):
                if not sample_id:
                    continue
                numeric, status = parse_value(raw_value)
                long_rows.append(
                    {
                        "TableIndex": table_index,
                        "SoilSampleID": sample_id,
                        "TreatmentCode": TREATMENT_BY_SAMPLE.get(sample_id, "UNKNOWN"),
                        "Analyte": variable,
                        "AnalyteZH": analyte_zh,
                        "Unit": unit,
                        "RawValue": raw_value,
                        "NumericValue": numeric,
                        "ParsingStatus": status,
                    }
                )

    long = pd.DataFrame(long_rows)
    expected_samples = {str(i) for i in range(1, 26)} | {"3-2", "6-2", "22-2"}
    observed_samples = set(long["SoilSampleID"])
    if observed_samples != expected_samples:
        raise ValueError(
            f"Soil sample IDs differ from expected: "
            f"missing={sorted(expected_samples - observed_samples)}, "
            f"extra={sorted(observed_samples - expected_samples)}"
        )
    expected_rows = len(expected_samples) * len(ANALYTES)
    if len(long) != expected_rows:
        raise ValueError(f"Expected {expected_rows} soil observations, found {len(long)}")
    long.to_csv(OUTPUT_DIR / "soil_nutrients_long.csv", index=False)

    identity_rows = []
    for sample_id in sorted(
        expected_samples,
        key=lambda value: (
            int(re.match(r"\d+", value).group()),
            1 if "-" in value else 0,
            value,
        ),
    ):
        treatment = TREATMENT_BY_SAMPLE[sample_id]
        if sample_id == "23":
            sample_type = "roadside bare soil outside experimental plots"
            include = "external context only"
        elif sample_id == "24":
            sample_type = "natural reference"
            include = "paper2 primary reference"
        elif sample_id in {"22", "22-2"}:
            sample_type = "in-field unplanted artificial bare plot"
            include = "paper2 treatment-level BP"
        elif treatment.startswith("T"):
            sample_type = "field treatment"
            include = "treatment-level"
        else:
            sample_type = "unresolved"
            include = "exclude until identified"
        identity_rows.append(
            {
                "SoilSampleID": sample_id,
                "TreatmentCode": treatment,
                "SampleType": sample_type,
                "Paper2Use": include,
                "MappingStatus": "user-confirmed" if sample_id in {"22", "22-2", "23", "24"} else "source-derived",
            }
        )
    identity = pd.DataFrame(identity_rows)
    identity.to_csv(OUTPUT_DIR / "soil_sample_identity.csv", index=False)

    primary = long.loc[
        long["TreatmentCode"].isin(["T1", "T6", "T7", "T22", "T23"])
    ].copy()
    primary.to_csv(OUTPUT_DIR / "paper2_soil_observations.csv", index=False)
    long.loc[long["SoilSampleID"].eq("23")].to_csv(
        OUTPUT_DIR / "external_roadside_bare_soil23.csv", index=False
    )

    ambiguity = long.loc[long["ParsingStatus"].ne("parsed")][
        ["SoilSampleID", "TreatmentCode", "Analyte", "RawValue", "ParsingStatus"]
    ]
    ambiguity.to_csv(OUTPUT_DIR / "soil_value_ambiguities.csv", index=False)

    summary = {
        "soil_samples": len(identity),
        "soil_observations": len(long),
        "analytes": len(ANALYTES),
        "paper2_soil_samples": ["1", "6", "6-2", "7", "22", "22-2", "24"],
        "roadside_reference_sample": "23",
        "natural_reference_sample": "24",
        "bare_plot_samples": ["22", "22-2"],
        "ambiguous_values": ambiguity.to_dict("records"),
    }
    (OUTPUT_DIR / "soil_audit.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
