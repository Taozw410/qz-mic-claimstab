from __future__ import annotations

import csv
import shutil
from pathlib import Path


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(
    path: Path, columns: list[str], rows: list[dict[str, str]]
) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def has_dataset(row: dict[str, str], dataset: str, field: str = "notes") -> bool:
    return f"dataset={dataset}" in row.get(field, "").split(";")


def merge_main(source: Path, replacement: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    _, original_claims = read_csv(source / "claims.csv")
    soil_claim_ids = {
        row["claim_id"]
        for row in original_claims
        if has_dataset(row, "soilrep")
    }
    for name in ("claims.csv", "endpoints.csv"):
        columns, original = read_csv(source / name)
        _, corrected = read_csv(replacement / name)
        if name == "claims.csv":
            kept = [
                row for row in original if row["claim_id"] not in soil_claim_ids
            ]
        else:
            kept = [
                row for row in original if row["claim_id"] not in soil_claim_ids
            ]
        write_csv(target / name, columns, kept + corrected)

    columns, original = read_csv(source / "reconstruction.csv")
    _, corrected = read_csv(replacement / "reconstruction.csv")
    kept = [
        row
        for row in original
        if row["reconstruction_id"] != "SOIL_RECON"
    ]
    write_csv(target / "reconstruction.csv", columns, kept + corrected)


def merge_permutation(source: Path, replacement: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for name in ("claims.csv", "endpoints.csv"):
        columns, original = read_csv(source / name)
        _, corrected = read_csv(replacement / name)
        kept = [
            row
            for row in original
            if not row["claim_id"].startswith("PERM_SOIL_")
        ]
        write_csv(target / name, columns, kept + corrected)

    columns, original = read_csv(source / "reconstruction.csv")
    _, corrected = read_csv(replacement / "reconstruction.csv")
    kept = [
        row
        for row in original
        if row["reconstruction_id"] != "SOILREP_PERM"
    ]
    write_csv(target / "reconstruction.csv", columns, kept + corrected)


def main() -> int:
    source = Path("output2")
    corrected = Path("soilfix")
    target = Path("output2_corrected")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    merge_main(source / "main", corrected / "main", target / "main")
    merge_permutation(
        source / "permutation",
        corrected / "permutation",
        target / "permutation",
    )

    columns, manifest = read_csv(source / "dataset_manifest.csv")
    for row in manifest:
        if row["dataset"] == "soilrep":
            row["samples_used"] = "24"
            row["contrast"] = (
                "Warmed and Clipped; technical replicates aggregated "
                "to 24 communities"
            )
    write_csv(target / "dataset_manifest.csv", columns, manifest)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
