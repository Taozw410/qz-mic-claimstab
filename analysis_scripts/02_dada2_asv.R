options(stringsAsFactors = FALSE)
suppressPackageStartupMessages({
  library(dada2)
  library(Biostrings)
})

set.seed(20261023)

root <- "C:/Users/hthome/AppData/Local/Temp/qz_mic_paper2"
raw_root <- file.path(root, "rawlink")
out_root <- file.path(root, "out", "asv")
dir.create(out_root, recursive = TRUE, showWarnings = FALSE)

process_one <- function(primer_id, min_len) {
  message("=== Processing ", primer_id, " ===")
  read_dir <- file.path(root, "input", if (primer_id == "338F_806R") "16S" else "ITS")
  files <- sort(list.files(read_dir, pattern = "^trim\\..*\\.fq$", full.names = TRUE))
  samples <- sub("^trim\\.", "", sub("\\.fq$", "", basename(files)))
  stopifnot(length(files) == 18)

  primer_out <- file.path(out_root, primer_id)
  filtered_dir <- file.path(primer_out, "filtered")
  dir.create(filtered_dir, recursive = TRUE, showWarnings = FALSE)
  filtered <- file.path(filtered_dir, paste0(samples, ".filt.fastq.gz"))
  max_ee <- if (primer_id == "338F_806R") 5 else 3

  filt <- filterAndTrim(
    fwd = files,
    filt = filtered,
    truncLen = 0,
    maxN = 0,
    maxEE = max_ee,
    truncQ = 0,
    minLen = min_len,
    rm.phix = FALSE,
    compress = TRUE,
    multithread = TRUE,
    verbose = TRUE
  )
  write.csv(filt, file.path(primer_out, "filter_tracking.csv"), row.names = TRUE)

  err <- learnErrors(
    filtered,
    nbases = 1e7,
    MAX_CONSIST = 2,
    multithread = TRUE,
    randomize = TRUE,
    verbose = TRUE
  )
  saveRDS(err, file.path(primer_out, "error_model.rds"))

  denoised <- dada(
    filtered,
    err = err,
    pool = FALSE,
    multithread = TRUE,
    verbose = TRUE
  )
  saveRDS(denoised, file.path(primer_out, "denoised.rds"))

  seqtab <- makeSequenceTable(denoised)
  seqtab_nochim <- removeBimeraDenovo(
    seqtab,
    method = "consensus",
    multithread = TRUE,
    verbose = TRUE
  )
  rownames(seqtab_nochim) <- samples
  saveRDS(seqtab_nochim, file.path(primer_out, "seqtab_nochim.rds"))

  asv_table <- as.data.frame(t(seqtab_nochim))
  asv_table <- data.frame(ASV = paste0("ASV_", seq_len(nrow(asv_table))), asv_table, check.names = FALSE)
  write.csv(asv_table, file.path(primer_out, "asv_table.csv"), row.names = FALSE)

  fasta_names <- paste0("ASV_", seq_len(ncol(seqtab_nochim)))
  seqs <- DNAStringSet(colnames(seqtab_nochim))
  names(seqs) <- fasta_names
  writeXStringSet(seqs, file.path(primer_out, "asv_representative_sequences.fasta"))

  read_tracking <- data.frame(
    Sample = samples,
    InputReads = filt[, "reads.in"],
    FilteredReads = filt[, "reads.out"],
    DenoisedReads = vapply(denoised, function(x) sum(x$denoised), numeric(1)),
    MergedReads = rowSums(seqtab),
    NonChimeraReads = rowSums(seqtab_nochim),
    ASVs = rowSums(seqtab_nochim > 0),
    ChimeraRetention = rowSums(seqtab_nochim) / rowSums(seqtab)
  )
  write.csv(read_tracking, file.path(primer_out, "read_tracking.csv"), row.names = FALSE)

  if (primer_id == "338F_806R") {
    message("Assigning 16S taxonomy with region-matched SILVA")
    train <- "D:/CodexWork/mic-re/ref_region/silva_V3V4_338F_806R.fa.gz"
    taxonomy <- assignTaxonomy(
      seqtab_nochim,
      train,
      multithread = TRUE,
      minBoot = 50,
      verbose = TRUE
    )
    rownames(taxonomy) <- fasta_names
    saveRDS(taxonomy, file.path(primer_out, "taxonomy_silva.rds"))
    write.csv(
      data.frame(ASV = rownames(taxonomy), taxonomy, check.names = FALSE),
      file.path(primer_out, "taxonomy_silva.csv"),
      row.names = FALSE
    )
  }

  message("Finished ", primer_id)
}

process_one("338F_806R", 300)
process_one("ITS1F_ITS2R", 50)
writeLines("DADA2 ASV processing completed.", file.path(out_root, "COMPLETE.txt"))
