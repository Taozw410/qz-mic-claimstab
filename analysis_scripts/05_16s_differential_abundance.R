options(stringsAsFactors = FALSE)
suppressPackageStartupMessages({
  library(phyloseq)
  library(ALDEx2)
  library(ANCOMBC)
})

set.seed(20261023)

root <- "C:/Users/<local-user>/AppData/Local/Temp/qz_mic_paper2"
asv_dir <- file.path(root, "out", "asv", "338F_806R")
out_dir <- file.path(root, "out", "da_16s")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

metadata <- read.csv(file.path(root, "out", "prelim", "sample_sheet.csv"))
metadata$Primary5 <- metadata$Primary5 == "True"
metadata$Composition <- factor(
  metadata$Composition,
  levels = c("Natural", "As", "AFP", "AEFP", "BP")
)
metadata <- metadata[metadata$Primary5, ]
row.names(metadata) <- metadata$Sample

asv <- read.csv(file.path(asv_dir, "asv_table.csv"), check.names = FALSE)
asv_matrix <- as.matrix(asv[, -1])
rownames(asv_matrix) <- asv$ASV
asv_matrix <- asv_matrix[, metadata$Sample, drop = FALSE]

taxonomy <- read.csv(file.path(asv_dir, "taxonomy_silva.csv"), check.names = FALSE)
rownames(taxonomy) <- taxonomy$ASV
taxonomy$ASV <- NULL
taxonomy <- taxonomy[rownames(asv_matrix), , drop = FALSE]

chloroplast <- !is.na(taxonomy$Order) & grepl("Chloroplast", taxonomy$Order, ignore.case = TRUE)
mitochondria <- !is.na(taxonomy$Family) & grepl("Mitochondria", taxonomy$Family, ignore.case = TRUE)
keep <- !(chloroplast | mitochondria)
asv_matrix <- asv_matrix[keep, , drop = FALSE]
taxonomy <- taxonomy[keep, , drop = FALSE]

genus <- taxonomy$Genus
genus[is.na(genus) | genus == ""] <- "Unclassified"
genus_counts <- rowsum(asv_matrix, group = genus)
prevalence <- rowSums(genus_counts > 0)
genus_counts <- genus_counts[prevalence >= 2 & rowSums(genus_counts) >= 10, , drop = FALSE]
write.csv(
  data.frame(Genus = rownames(genus_counts), genus_counts, check.names = FALSE),
  file.path(out_dir, "genus_counts_primary.csv"),
  row.names = FALSE
)

conditions <- as.character(metadata$Composition)
global <- aldex(
  genus_counts,
  conditions,
  mc.samples = 128,
  test = "kw",
  effect = FALSE,
  denom = "all",
  verbose = TRUE
)
global$Genus <- rownames(global)
write.csv(global, file.path(out_dir, "ALDEx2_global_KW.csv"), row.names = FALSE)

pairwise_all <- list()
for (group in c("As", "AFP", "AEFP", "BP")) {
  samples <- metadata$Sample[metadata$Composition %in% c(group, "Natural")]
  group_labels <- as.character(metadata$Composition[match(samples, metadata$Sample)])
  result <- aldex(
    genus_counts[, samples, drop = FALSE],
    group_labels,
    mc.samples = 128,
    test = "t",
    effect = TRUE,
    denom = "all",
    verbose = FALSE
  )
  result$Genus <- rownames(result)
  result$Contrast <- paste(group, "vs Natural")
  pairwise_all[[group]] <- result
}
pairwise_columns <- unique(unlist(lapply(pairwise_all, names), use.names = FALSE))
pairwise_all <- lapply(pairwise_all, function(frame) {
  missing <- setdiff(pairwise_columns, names(frame))
  for (column in missing) {
    frame[[column]] <- NA
  }
  frame[, pairwise_columns, drop = FALSE]
})
pairwise <- do.call(rbind, pairwise_all)
write.csv(pairwise, file.path(out_dir, "ALDEx2_pairwise_vs_natural.csv"), row.names = FALSE)

ps <- phyloseq(
  otu_table(genus_counts, taxa_are_rows = TRUE),
  sample_data(metadata)
)

ancom_result <- NULL
ancom_error <- NULL
ancom_result <- tryCatch(
  ancombc2(
    data = ps,
    fix_formula = "Composition",
    p_adj_method = "BH",
    prv_cut = 0.1,
    lib_cut = 1000,
    group = "Composition",
    struc_zero = TRUE,
    neg_lb = TRUE,
    global = FALSE,
    pairwise = TRUE,
    pseudo_sens = TRUE,
    n_cl = 1,
    verbose = TRUE
  ),
  error = function(error) {
    ancom_error <<- conditionMessage(error)
    NULL
  }
)
if (!is.null(ancom_result)) {
  write.csv(ancom_result$res, file.path(out_dir, "ANCOMBC2_pairwise.csv"), row.names = FALSE)
} else {
  writeLines(ancom_error, file.path(out_dir, "ANCOMBC2_ERROR.txt"))
}

writeLines("16S differential-abundance analysis completed.", file.path(out_dir, "COMPLETE.txt"))
