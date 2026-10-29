from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT.parent / "tmp" / "reference_export_20261025"
OUTPUT = ROOT / "05_稿件" / "16_references_verified.bib"

MANUAL_ENTRIES = r"""
@article{arumugam2011,
  author  = {Arumugam, Manimozhiyan and Raes, Jeroen and Pelletier, Eric and Le Paslier, Denis and Yamada, Takuji and Mende, Daniel R. and Fernandes, Gabriel R. and Tap, Julien and Bruls, Thomas and Batto, Jean-Michel and others},
  title   = {{Enterotypes of the human gut microbiome}},
  journal = {Nature},
  year    = {2011},
  volume  = {473},
  number  = {7346},
  pages   = {174--180},
  doi     = {10.1038/nature09944}
}

@article{caporaso2011,
  author  = {Caporaso, J. Gregory and Lauber, Christian L. and Walters, William A. and Berg-Lyons, Donna and Lozupone, Catherine A. and Turnbaugh, Peter J. and Fierer, Noah and Knight, Rob},
  title   = {{Global patterns of 16S rRNA diversity at a depth of millions of sequences per sample}},
  journal = {Proceedings of the National Academy of Sciences},
  year    = {2011},
  volume  = {108},
  number  = {supplement_1},
  pages   = {4516--4522},
  doi     = {10.1073/pnas.1000080107}
}

@article{lahti2014,
  author  = {Lahti, Leo and Saloj{\"a}rvi, Jarkko and Salonen, Anne and Scheffer, Marten and de Vos, Willem M.},
  title   = {{Tipping elements in the human intestinal ecosystem}},
  journal = {Nature Communications},
  year    = {2014},
  volume  = {5},
  pages   = {4344},
  doi     = {10.1038/ncomms5344}
}

@article{simonsohn2020,
  author  = {Simonsohn, Uri and Simmons, Joseph P. and Nelson, Leif D.},
  title   = {{Specification curve analysis}},
  journal = {Nature Human Behaviour},
  year    = {2020},
  volume  = {4},
  number  = {11},
  pages   = {1208--1214},
  doi     = {10.1038/s41562-020-0912-z}
}

@article{steegen2016,
  author  = {Steegen, Sara and Tuerlinckx, Francis and Gelman, Andrew and Vanpaemel, Wolf},
  title   = {{Increasing transparency through a multiverse analysis}},
  journal = {Perspectives on Psychological Science},
  year    = {2016},
  volume  = {11},
  number  = {5},
  pages   = {702--712},
  doi     = {10.1177/1745691616658637}
}

@article{zhou2011,
  author  = {Zhou, Jizhong and Wu, Liyou and Deng, Ye and Zhi, Xiaoyang and Jiang, Yi-Huei and Tu, Qichao and Xie, Jianping and Van Nostrand, Joy D. and He, Zhili and Luo, Yiqi},
  title   = {{Reproducibility and quantitation of amplicon sequencing-based detection}},
  journal = {The ISME Journal},
  year    = {2011},
  volume  = {5},
  number  = {8},
  pages   = {1303--1313},
  doi     = {10.1038/ismej.2011.11}
}

@manual{oksanen2026,
  author = {Oksanen, Jari and Simpson, Gavin L. and Blanchet, F. Guillaume and Kindt, Roeland and Legendre, Pierre and Minchin, Peter R. and O'Hara, Robert B. and Solymos, Peter and Stevens, M. Henry H. and Szoecs, Eduard and Wagner, Helene and Bedward, Michael and Bolker, Ben and Borcard, Daniel and Carvalho, Gustavo and De Caceres, Miquel and Durand, Sebastien and Evangelista, Heloisa Beatriz Antoniazi and Hannigan, Geoffrey and Hill, Mark O. and Lahti, Leo and Martino, Cameron and Ouellette, Marie-Helene and Ribeiro Cunha, Eduardo and Smith, Tyler and Stier, Adrian and Ter Braak, Cajo J.F. and Weedon, James},
  title = {vegan: Community Ecology Package},
  year = {2026},
  note = {R package version 2.7-6},
  doi = {10.32614/CRAN.package.vegan},
  url = {https://CRAN.R-project.org/package=vegan}
}

@misc{mclaren2021,
  author = {McLaren, Michael R. and Callahan, Benjamin J.},
  title = {Silva 138.1 prokaryotic SSU taxonomic training data formatted for DADA2},
  year = {2021},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.4587955},
  url = {https://doi.org/10.5281/zenodo.4587955}
}

@misc{unite2025,
  author = {{UNITE Community}},
  title = {UNITE general FASTA release for Fungi},
  year = {2025},
  publisher = {UNITE Community},
  doi = {10.15156/BIO/3301229},
  url = {https://doi.org/10.15156/BIO/3301229}
}
""".strip()


def normalize_entry(text: str) -> str:
    # Journal issue year is the citable year for these two records.
    if "10.1111/ele.12381" in text:
        text = text.replace("@article{prober2014,", "@article{prober2015,")
        text = text.replace("year    = {2014},", "year    = {2015},")
    if "10.1093/nar/gks1219" in text:
        text = text.replace("@article{quast2012,", "@article{quast2013,")
        text = text.replace("year    = {2012},", "year    = {2013},")
    if "10.1093/nar/gkt1209" in text:
        text = text.replace("@article{yilmaz2013,", "@article{yilmaz2014,")
        text = text.replace("year    = {2013},", "year    = {2014},")
    return text.strip()


def main() -> None:
    entries = []
    for path in sorted(INPUT_DIR.glob("*.bib")):
        entries.append(normalize_entry(path.read_text(encoding="utf-8")))
    entries.append(MANUAL_ENTRIES)
    combined = "\n\n".join(entries) + "\n"
    keys = re.findall(r"@\w+\{([^,]+),", combined)
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if len(keys) != 27:
        raise ValueError(f"Expected 27 entries, found {len(keys)}")
    if duplicates:
        raise ValueError(f"Duplicate BibTeX keys: {duplicates}")
    OUTPUT.write_text(combined, encoding="utf-8")
    print(f"Wrote {len(keys)} entries to {OUTPUT}")


if __name__ == "__main__":
    main()
