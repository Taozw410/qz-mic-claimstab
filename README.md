# QZ microbiome claim-stability analysis and claimstab

This repository archives the analysis scripts and source code for the
manuscript *Claimstab: a reconstruction-aware framework for endpoint-specific
reproducibility of microbiome claims*.

## Components

- `claimstab/`: installable Python package, schemas, tests, command-line
  interface, documentation, and worked examples.
- `analysis_scripts/`: manuscript-specific R and Python scripts from sequence
  processing through figures, tables, and manuscript audits.
- `analysis_scripts/benchmark/`: scripts used to rebuild and summarize the
  four-dataset public benchmark.
- `ENVIRONMENT.md`: software environments and execution notes.
- `REPRODUCTION_STATUS.md`: verified analysis and framework status.

## Software release

- Package: `claimstab`
- Version: `0.3.0`
- Python: 3.10 or newer
- Interface: `python -m claimstab`
- License: MIT

Install from the repository:

```bash
python -m pip install ./claimstab
python -m claimstab --version
```

The `v0.3.0` GitHub release provides wheel and source archives.

## Data

The analysis-ready data and derived results are maintained at:

<https://github.com/Taozw410/qz-mic-data>

Raw sequencing reads are not duplicated in either repository.

## Citation

Cite the software using `CITATION.cff`, the repository URL, the `v0.3.0`
release, and the permanent archive DOI to be added after Zenodo archiving.
