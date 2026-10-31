options(stringsAsFactors = FALSE)
suppressPackageStartupMessages({
  library(dada2)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) {
  stop("Usage: 02c_dada2_16s_chunk.R START END")
}
start_index <- as.integer(args[1])
end_index <- as.integer(args[2])

root <- "C:/Users/<local-user>/AppData/Local/Temp/qz_mic_paper2"
domain_dir <- file.path(root, "out", "asv", "338F_806R")
filtered_dir <- file.path(domain_dir, "filtered")
files <- sort(list.files(filtered_dir, pattern = "\\.filt\\.fastq\\.gz$", full.names = TRUE))
samples <- sub("\\.filt\\.fastq\\.gz$", "", basename(files))
indices <- seq.int(start_index, end_index)
stopifnot(length(files) == 18)

err <- readRDS(file.path(domain_dir, "error_model.rds"))
denoised <- dada(
  files[indices],
  err = err,
  pool = FALSE,
  multithread = TRUE,
  verbose = TRUE
)
seqtab <- makeSequenceTable(denoised)
rownames(seqtab) <- samples[indices]

saveRDS(
  list(
    seqtab = seqtab,
    tracking = data.frame(
      Sample = samples[indices],
      DenoisedReads = vapply(denoised, function(x) sum(x$denoised), numeric(1)),
      RawTableReads = rowSums(seqtab),
      ASVsBeforeChimera = rowSums(seqtab > 0)
    )
  ),
  file.path(domain_dir, paste0("chunk_", start_index, "_", end_index, ".rds"))
)
writeLines(
  paste("Completed", start_index, end_index),
  file.path(domain_dir, paste0("chunk_", start_index, "_", end_index, ".done"))
)
