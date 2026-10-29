options(stringsAsFactors = FALSE)
suppressPackageStartupMessages({
  library(phyloseq)
  library(ALDEx2)
  library(ANCOMBC)
})

set.seed(20261023)

args <- commandArgs(trailingOnly = TRUE)
get_arg <- function(flag, default) {
  index <- match(flag, args)
  if (is.na(index) || index == length(args)) default else args[[index + 1]]
}

input_dir <- get_arg("--input-dir", "")
sample_sheet_path <- get_arg("--sample-sheet", "")
output_dir <- get_arg("--output-dir", "")
prevalence_fraction <- as.numeric(get_arg("--prevalence-fraction", "0.10"))
minimum_total_count <- as.integer(get_arg("--minimum-total-count", "10"))
if (!nzchar(input_dir) || !nzchar(sample_sheet_path) || !nzchar(output_dir)) {
  stop("--input-dir, --sample-sheet and --output-dir are required")
}
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

metadata <- read.csv(sample_sheet_path, check.names = FALSE)
metadata$Primary5 <- tolower(as.character(metadata$Primary5)) %in% c("true", "1", "yes")
metadata <- metadata[metadata$Primary5, ]
metadata$Composition <- factor(
  metadata$Composition,
  levels = c("Natural", "As", "AFP", "AEFP", "BP")
)
if (nrow(metadata) != 15 || any(table(metadata$Composition) != 3)) {
  stop("Expected 15 primary samples, three per group")
}
rownames(metadata) <- metadata$Sample

asv <- read.csv(file.path(input_dir, "asv_table.csv"), check.names = FALSE)
counts <- as.matrix(asv[, metadata$Sample, drop = FALSE])
rownames(counts) <- asv$ASV

taxonomy <- read.csv(file.path(input_dir, "taxonomy_unite.csv"), check.names = FALSE)
rownames(taxonomy) <- taxonomy$ASV
taxonomy <- taxonomy[rownames(counts), , drop = FALSE]
taxonomy$Genus <- trimws(taxonomy$Genus)

# Unclassified ASVs are retained in a descriptive table but excluded from
# interpretable genus-level differential-abundance tests.
classified <- !is.na(taxonomy$Genus) & nzchar(taxonomy$Genus)
classified_counts <- counts[classified, , drop = FALSE]
genus <- sub("^g__", "", taxonomy$Genus[classified])
genus_counts <- rowsum(classified_counts, group = genus)
prevalence <- rowSums(genus_counts > 0)
minimum_prevalence_samples <- ceiling(prevalence_fraction * nrow(metadata))
genus_counts <- genus_counts[
  prevalence >= minimum_prevalence_samples &
    rowSums(genus_counts) >= minimum_total_count,
  ,
  drop = FALSE
]
write.csv(
  data.frame(Genus = rownames(genus_counts), genus_counts, check.names = FALSE),
  file.path(output_dir, "genus_counts_primary.csv"),
  row.names = FALSE
)

conditions <- as.character(metadata$Composition)
global <- aldex(
  genus_counts,
  conditions,
  mc.samples = 256,
  test = "kw",
  effect = FALSE,
  denom = "all",
  verbose = TRUE
)
global$Genus <- rownames(global)
write.csv(global, file.path(output_dir, "ALDEx2_global_KW.csv"), row.names = FALSE)

pairwise_all <- list()
for (group in c("As", "AFP", "AEFP", "BP")) {
  samples <- metadata$Sample[metadata$Composition %in% c(group, "Natural")]
  group_labels <- as.character(metadata$Composition[match(samples, metadata$Sample)])
  result <- aldex(
    genus_counts[, samples, drop = FALSE],
    group_labels,
    mc.samples = 256,
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
write.csv(
  do.call(rbind, pairwise_all),
  file.path(output_dir, "ALDEx2_pairwise_vs_natural.csv"),
  row.names = FALSE
)

ps <- phyloseq(
  otu_table(genus_counts, taxa_are_rows = TRUE),
  sample_data(metadata)
)
ancom_result <- tryCatch(
  ancombc2(
    data = ps,
    fix_formula = "Composition",
    p_adj_method = "BH",
    prv_cut = prevalence_fraction,
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
    writeLines(conditionMessage(error), file.path(output_dir, "ANCOMBC2_ERROR.txt"))
    NULL
  }
)
if (!is.null(ancom_result)) {
  write.csv(
    ancom_result$res,
    file.path(output_dir, "ANCOMBC2_pairwise.csv"),
    row.names = FALSE
  )
}

write.csv(
  data.frame(
    Parameter = c(
      "Domain", "InputASVs", "ClassifiedASVs", "GenusFeaturesRetained",
      "PrevalenceMinimum", "MinimumTotalCount", "ALDExMC",
      "ALDExTest", "ANCOMBC2Adjustment", "ANCOMBC2Prevalence",
      "RandomSeed"
    ),
    Value = c(
      "ITS", nrow(counts), sum(classified), nrow(genus_counts),
      minimum_prevalence_samples, minimum_total_count, 256, "Welch t",
      "BH", prevalence_fraction, 20261023
    )
  ),
  file.path(output_dir, "analysis_parameters.csv"),
  row.names = FALSE
)
writeLines(
  "ITS genus differential-abundance analysis completed.",
  file.path(output_dir, "COMPLETE.txt")
)
