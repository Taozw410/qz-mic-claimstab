options(stringsAsFactors = FALSE)
suppressPackageStartupMessages({
  library(dada2)
  library(Biostrings)
})

set.seed(20261023)

args <- commandArgs(trailingOnly = TRUE)
get_arg <- function(flag, default) {
  index <- match(flag, args)
  if (is.na(index) || index == length(args)) default else args[[index + 1]]
}

input_fasta <- get_arg(
  "--input",
  "D:/CodexWork/QZ-mic/论文2-微生物/01_数据/ASV_ITS/asv_representative_sequences.fasta"
)
reference_fasta <- get_arg(
  "--reference",
  "D:/bioenv/envs/riz16s/share/unite/v10.0_2025-02-19/sh_general_release_dynamic_19.02.2025.fasta"
)
output_dir <- get_arg(
  "--output-dir",
  "C:/Users/<local-user>/AppData/Local/Temp/qz_mic_its_unite"
)
threads <- as.integer(get_arg("--threads", "8"))
min_boot <- as.integer(get_arg("--min-boot", "50"))

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
if (!file.exists(input_fasta)) {
  stop("ITS ASV FASTA not found: ", input_fasta)
}
if (!file.exists(reference_fasta)) {
  stop(
    "UNITE reference not found: ",
    reference_fasta,
    "\nInstall UNITE v10.0 under D:/bioenv/envs/riz16s/share/unite/."
  )
}

sequences <- readDNAStringSet(input_fasta)
if (anyDuplicated(names(sequences))) {
  stop("ASV names are not unique in ", input_fasta)
}

message("Classifying ", length(sequences), " ITS ASVs with ", basename(reference_fasta))
taxa <- assignTaxonomy(
  setNames(as.character(sequences), names(sequences)),
  reference_fasta,
  minBoot = min_boot,
  tryRC = TRUE,
  multithread = threads
)

taxonomy <- data.frame(
  ASV = names(sequences),
  taxa,
  check.names = FALSE
)
taxonomy_path <- file.path(output_dir, "taxonomy_unite.csv")
write.csv(taxonomy, taxonomy_path, row.names = FALSE)

assigned <- vapply(
  colnames(taxa),
  function(rank) sum(!is.na(taxa[, rank])),
  integer(1)
)
run_summary <- data.frame(
  Reference = "UNITE",
  Version = "10.0",
  ReleaseDate = "2025-02-19",
  DOI = "10.15156/BIO/3301229",
  ReferenceFile = reference_fasta,
  ReferenceSHA256 = toupper(digest::digest(
    reference_fasta,
    algo = "sha256",
    file = TRUE
  )),
  InputFile = input_fasta,
  ASVs = length(sequences),
  MinBoot = min_boot,
  TryRC = TRUE,
  Threads = threads,
  AssignedKingdom = unname(assigned[["Kingdom"]]),
  AssignedPhylum = unname(assigned[["Phylum"]]),
  AssignedClass = unname(assigned[["Class"]]),
  AssignedOrder = unname(assigned[["Order"]]),
  AssignedFamily = unname(assigned[["Family"]]),
  AssignedGenus = unname(assigned[["Genus"]]),
  AssignedSpecies = unname(assigned[["Species"]]),
  DADA2Version = as.character(packageVersion("dada2")),
  RVersion = R.version.string,
  RandomSeed = 20261023
)
write.csv(
  run_summary,
  file.path(output_dir, "taxonomy_unite_run.csv"),
  row.names = FALSE
)

writeLines(
  c(
    "ITS UNITE taxonomy assignment completed.",
    paste0("Reference: ", reference_fasta),
    paste0("Reference release: UNITE v10.0 / 2025-02-19"),
    paste0("DOI: 10.15156/BIO/3301229"),
    paste0("ASVs: ", length(sequences)),
    paste0("minBoot: ", min_boot),
    paste0("tryRC: TRUE"),
    paste0("Output: ", taxonomy_path)
  ),
  file.path(output_dir, "COMPLETE.txt")
)

print(run_summary[, c(
  "ASVs",
  "AssignedKingdom",
  "AssignedPhylum",
  "AssignedClass",
  "AssignedOrder",
  "AssignedFamily",
  "AssignedGenus",
  "AssignedSpecies"
)])
