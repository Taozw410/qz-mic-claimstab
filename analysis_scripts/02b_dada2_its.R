options(stringsAsFactors = FALSE)
suppressPackageStartupMessages({
  library(dada2)
  library(Biostrings)
})

set.seed(20261023)

root <- "C:/Users/<local-user>/AppData/Local/Temp/qz_mic_paper2"
out_dir <- file.path(root, "out", "asv", "ITS1F_ITS2R")
filtered_dir <- file.path(out_dir, "filtered")
dir.create(filtered_dir, recursive = TRUE, showWarnings = FALSE)

files <- sort(list.files(file.path(root, "input", "ITS"), pattern = "^trim\\..*\\.fq$", full.names = TRUE))
samples <- sub("^trim\\.", "", sub("\\.fq$", "", basename(files)))
stopifnot(length(files) == 18)
filtered <- file.path(filtered_dir, paste0(samples, ".filt.fastq.gz"))

filt <- filterAndTrim(
  fwd = files,
  filt = filtered,
  truncLen = 0,
  maxN = 0,
  maxEE = 3,
  truncQ = 0,
  minLen = 50,
  rm.phix = FALSE,
  compress = TRUE,
  multithread = TRUE,
  verbose = TRUE
)
write.csv(filt, file.path(out_dir, "filter_tracking.csv"), row.names = TRUE)

err <- learnErrors(
  filtered,
  nbases = 1e7,
  MAX_CONSIST = 2,
  multithread = TRUE,
  randomize = TRUE,
  verbose = TRUE
)
saveRDS(err, file.path(out_dir, "error_model.rds"))

denoised <- dada(
  filtered,
  err = err,
  pool = FALSE,
  multithread = TRUE,
  verbose = TRUE
)
saveRDS(denoised, file.path(out_dir, "denoised.rds"))

seqtab <- makeSequenceTable(denoised)
seqtab_nochim <- removeBimeraDenovo(
  seqtab,
  method = "consensus",
  multithread = TRUE,
  verbose = TRUE
)
rownames(seqtab_nochim) <- samples
saveRDS(seqtab_nochim, file.path(out_dir, "seqtab_nochim.rds"))

asv_table <- as.data.frame(t(seqtab_nochim))
asv_table <- data.frame(
  ASV = paste0("ASV_", seq_len(nrow(asv_table))),
  asv_table,
  check.names = FALSE
)
write.csv(asv_table, file.path(out_dir, "asv_table.csv"), row.names = FALSE)

seqs <- DNAStringSet(colnames(seqtab_nochim))
names(seqs) <- paste0("ASV_", seq_len(ncol(seqtab_nochim)))
writeXStringSet(seqs, file.path(out_dir, "asv_representative_sequences.fasta"))

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
write.csv(read_tracking, file.path(out_dir, "read_tracking.csv"), row.names = FALSE)
writeLines("ITS DADA2 processing completed.", file.path(out_dir, "COMPLETE.txt"))
