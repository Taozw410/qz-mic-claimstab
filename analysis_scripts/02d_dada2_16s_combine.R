options(stringsAsFactors = FALSE)
suppressPackageStartupMessages({
  library(dada2)
  library(Biostrings)
})

root <- "C:/Users/hthome/AppData/Local/Temp/qz_mic_paper2"
domain_dir <- file.path(root, "out", "asv", "338F_806R")
chunk_paths <- file.path(domain_dir, c("chunk_1_6.rds", "chunk_7_12.rds", "chunk_13_18.rds"))
stopifnot(all(file.exists(chunk_paths)))

chunks <- lapply(chunk_paths, readRDS)
tables <- lapply(chunks, `[[`, "seqtab")
merged <- mergeSequenceTables(tables = tables)
seqtab_nochim <- removeBimeraDenovo(
  merged,
  method = "consensus",
  multithread = TRUE,
  verbose = TRUE
)
saveRDS(seqtab_nochim, file.path(domain_dir, "seqtab_nochim.rds"))

asv_table <- as.data.frame(t(seqtab_nochim))
asv_table <- data.frame(
  ASV = paste0("ASV_", seq_len(nrow(asv_table))),
  asv_table,
  check.names = FALSE
)
write.csv(asv_table, file.path(domain_dir, "asv_table.csv"), row.names = FALSE)

seqs <- DNAStringSet(colnames(seqtab_nochim))
names(seqs) <- paste0("ASV_", seq_len(ncol(seqtab_nochim)))
writeXStringSet(seqs, file.path(domain_dir, "asv_representative_sequences.fasta"))

tracking <- do.call(rbind, lapply(chunks, `[[`, "tracking"))
tracking$NonChimeraReads <- rowSums(seqtab_nochim)[tracking$Sample]
tracking$ASVs <- rowSums(seqtab_nochim > 0)[tracking$Sample]
tracking$ChimeraRetention <- tracking$NonChimeraReads / tracking$RawTableReads
write.csv(tracking, file.path(domain_dir, "read_tracking.csv"), row.names = FALSE)

train <- "D:/CodexWork/mic-re/ref_region/silva_V3V4_338F_806R.fa.gz"
taxonomy <- assignTaxonomy(
  seqtab_nochim,
  train,
  multithread = TRUE,
  minBoot = 50,
  verbose = TRUE
)
rownames(taxonomy) <- paste0("ASV_", seq_len(nrow(taxonomy)))
saveRDS(taxonomy, file.path(domain_dir, "taxonomy_silva.rds"))
write.csv(
  data.frame(ASV = rownames(taxonomy), taxonomy, check.names = FALSE),
  file.path(domain_dir, "taxonomy_silva.csv"),
  row.names = FALSE
)
writeLines("16S DADA2 processing completed.", file.path(domain_dir, "COMPLETE.txt"))
