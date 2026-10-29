options(stringsAsFactors = FALSE)
suppressPackageStartupMessages({
  library(phyloseq)
  library(vegan)
  library(ggplot2)
})

set.seed(20261023)

root <- "C:/Users/hthome/AppData/Local/Temp/qz_mic_paper2"
out_dir <- file.path(root, "out", "asv_analysis")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

sample_sheet <- read.csv(file.path(root, "out", "prelim", "sample_sheet.csv"))
sample_sheet$Primary5 <- sample_sheet$Primary5 == "True"
sample_sheet$Composition <- factor(
  sample_sheet$Composition,
  levels = c("As", "AFP", "AEFP", "BP", "Natural", "Unassigned")
)
row.names(sample_sheet) <- sample_sheet$Sample
primary_samples <- sample_sheet$Sample[sample_sheet$Primary5]

group_colors <- c(
  As = "#0072B2",
  AFP = "#009E73",
  AEFP = "#D55E00",
  BP = "#E69F00",
  Natural = "#CC79A7",
  Unassigned = "#7F7F7F"
)

read_domain <- function(domain) {
  if (domain == "16S") {
    primer <- "338F_806R"
  } else {
    primer <- "ITS1F_ITS2R"
  }
  path <- file.path(root, "out", "asv", primer, "asv_table.csv")
  table <- read.csv(path, check.names = FALSE)
  asv_names <- table$ASV
  mat <- as.matrix(table[, -1, drop = FALSE])
  rownames(mat) <- asv_names
  mat <- mat[, rownames(sample_sheet), drop = FALSE]

  metadata <- sample_data(sample_sheet)
  ps <- phyloseq(otu_table(mat, taxa_are_rows = TRUE), metadata)

  tax_path <- if (domain == "16S") {
    file.path(root, "out", "asv", primer, "taxonomy_silva.csv")
  } else {
    NA_character_
  }
  taxonomy_assigned <- !is.na(tax_path) && file.exists(tax_path)

  if (taxonomy_assigned) {
    tax <- read.csv(tax_path, check.names = FALSE)
    rownames(tax) <- tax$ASV
    tax$ASV <- NULL
    tax <- as.matrix(tax)
    tax <- tax[rownames(mat), , drop = FALSE]

    chloroplast <- !is.na(tax[, "Order"]) & grepl("Chloroplast", tax[, "Order"], ignore.case = TRUE)
    mitochondria <- !is.na(tax[, "Family"]) & grepl("Mitochondria", tax[, "Family"], ignore.case = TRUE)
    keep <- !(chloroplast | mitochondria)
    ps <- prune_taxa(keep, ps)
    tax <- tax[keep, , drop = FALSE]
    ps <- merge_phyloseq(ps, tax_table(tax))
  }

  ps <- prune_taxa(taxa_sums(ps) > 0, ps)
  attr(ps, "taxonomy_assigned") <- taxonomy_assigned
  ps
}

alpha_subset <- function(ps, depth, tag) {
  rare <- rarefy_even_depth(
    ps,
    sample.size = depth,
    rngseed = 20261023,
    replace = FALSE,
    verbose = TRUE
  )
  alpha <- estimate_richness(rare, measures = c("Observed", "Shannon", "Simpson"))
  alpha$Sample <- sample_names(rare)
  alpha <- merge(alpha, sample_sheet, by = "Sample")
  write.csv(alpha, file.path(out_dir, paste0("alpha_samples_", tag, ".csv")), row.names = FALSE)

  summaries <- list()
  tests <- list()
  for (metric in c("Observed", "Shannon", "Simpson")) {
    for (group in levels(droplevels(alpha$Composition))) {
      values <- alpha[[metric]][alpha$Composition == group]
      summaries[[length(summaries) + 1]] <- data.frame(
        Composition = group,
        Metric = metric,
        N = length(values),
        Mean = mean(values),
        SD = sd(values),
        SE = sd(values) / sqrt(length(values))
      )
    }
    model <- oneway.test(alpha[[metric]] ~ alpha$Composition, var.equal = FALSE)
    tests[[length(tests) + 1]] <- data.frame(
      Metric = metric,
      WelchF = unname(model$statistic),
      P = model$p.value
    )
  }
  write.csv(
    do.call(rbind, summaries),
    file.path(out_dir, paste0("alpha_group_summary_", tag, ".csv")),
    row.names = FALSE
  )
  write.csv(
    do.call(rbind, tests),
    file.path(out_dir, paste0("alpha_omnibus_", tag, ".csv")),
    row.names = FALSE
  )
  list(alpha = alpha, rare = rare, depth = depth)
}

bray_results <- function(ps, metadata, tag) {
  ps_rel <- transform_sample_counts(ps, function(x) x / sum(x))
  bray <- distance(ps_rel, method = "bray")
  permanova <- adonis2(
    bray ~ Composition,
    data = as.data.frame(metadata),
    permutations = 9999
  )
  dispersion <- betadisper(bray, metadata$Composition)
  dispersion_test <- permutest(dispersion, permutations = 9999)

  permanova_row <- data.frame(
    Metric = "Bray-Curtis",
    F = permanova$F[1],
    R2 = permanova$R2[1],
    P = permanova$`Pr(>F)`[1],
    DispersionF = dispersion_test$tab$F[1],
    DispersionP = dispersion_test$tab$`Pr(>F)`[1]
  )

  pseudo <- as.matrix(t(otu_table(ps))) + 0.5
  clr <- log(pseudo / rowSums(pseudo))
  clr <- clr - rowMeans(clr)
  aitchison <- dist(clr, method = "euclidean")
  aitchison_model <- adonis2(
    aitchison ~ Composition,
    data = as.data.frame(metadata),
    permutations = 9999
  )
  aitchison_row <- data.frame(
    Metric = "Aitchison",
    F = aitchison_model$F[1],
    R2 = aitchison_model$R2[1],
    P = aitchison_model$`Pr(>F)`[1],
    DispersionF = NA,
    DispersionP = NA
  )

  ord <- ordinate(ps_rel, method = "PCoA", distance = "bray")
  p <- plot_ordination(ps_rel, ord, color = "Composition") +
    geom_point(size = 3) +
    scale_color_manual(values = group_colors) +
    theme_bw(base_size = 11) +
    labs(title = paste(tag, "ASV Bray-Curtis"), color = "Composition")
  ggsave(
    file.path(out_dir, paste0("pcoa_", tag, ".png")),
    p,
    width = 7,
    height = 5,
    dpi = 300
  )

  reference_distances(ps_rel, bray, metadata, tag)

  list(
    distance = bray,
    aitchison = aitchison,
    results = rbind(permanova_row, aitchison_row),
    ordination = ord
  )
}

reference_distances <- function(ps_rel, bray, metadata, tag) {
  rel <- as.matrix(t(otu_table(ps_rel)))
  natural_samples <- metadata$Sample[metadata$Composition == "Natural"]
  natural_centroid <- colMeans(rel[natural_samples, , drop = FALSE])
  manual <- sweep(rel, 2, natural_centroid)
  sample_distance <- rowSums(abs(manual)) / (rowSums(rel) + sum(natural_centroid))

  rows <- lapply(levels(droplevels(metadata$Composition)), function(group) {
    values <- sample_distance[metadata$Composition == group]
    data.frame(
      Composition = group,
      N = length(values),
      MeanDistanceToNatural = mean(values),
      SE = sd(values) / sqrt(length(values))
    )
  })
  result <- do.call(rbind, rows)
  write.csv(
    result,
    file.path(out_dir, paste0("natural_reference_distance_", tag, ".csv")),
    row.names = FALSE
  )
  result
}

analyze_domain <- function(domain) {
  message("Analyzing ", domain, " ASVs")
  ps <- read_domain(domain)
  ps_primary <- prune_samples(primary_samples, ps)
  ps_primary <- prune_taxa(taxa_sums(ps_primary) > 0, ps_primary)
  primary_depth <- min(sample_sums(ps_primary))
  if (primary_depth < 1000) {
    stop("Primary rarefaction depth below 1000 reads for ", domain)
  }

  alpha_primary <- alpha_subset(ps_primary, primary_depth, paste0(domain, "_primary"))
  beta_primary <- bray_results(
    ps_primary,
    data.frame(sample_data(ps_primary)),
    paste0(domain, "_primary")
  )

  sensitivity_depth <- min(sample_sums(ps))
  if (sensitivity_depth < 1000) {
    stop("Sensitivity rarefaction depth below 1000 reads for ", domain)
  }
  alpha_sensitivity <- alpha_subset(ps, sensitivity_depth, paste0(domain, "_sensitivity"))
  beta_sensitivity <- bray_results(
    ps,
    data.frame(sample_data(ps)),
    paste0(domain, "_sensitivity")
  )

  write.csv(
    beta_primary$results,
    file.path(out_dir, paste0("beta_", domain, "_primary.csv")),
    row.names = FALSE
  )
  write.csv(
    beta_sensitivity$results,
    file.path(out_dir, paste0("beta_", domain, "_sensitivity.csv")),
    row.names = FALSE
  )
  list(
    primary = beta_primary,
    sensitivity = beta_sensitivity,
    depth_primary = primary_depth,
    depth_sensitivity = sensitivity_depth,
    n_taxa = ntaxa(ps),
    n_samples = nsamples(ps),
    taxonomy_assigned = isTRUE(attr(ps, "taxonomy_assigned"))
  )
}

args <- commandArgs(trailingOnly = TRUE)
requested_domains <- if (length(args) == 0) c("16S", "ITS") else args
results_16s <- if ("16S" %in% requested_domains) analyze_domain("16S") else NULL
results_its <- if ("ITS" %in% requested_domains) analyze_domain("ITS") else NULL

if (!is.null(results_16s) && !is.null(results_its)) {
  mantel_result <- mantel(
    results_16s$primary$distance,
    results_its$primary$distance,
    method = "spearman",
    permutations = 9999
  )
  coords_16s <- cmdscale(results_16s$primary$distance, k = 4)
  coords_its <- cmdscale(results_its$primary$distance, k = 4)
  protest_result <- protest(coords_16s, coords_its, permutations = 9999)

  write.csv(
    data.frame(
      N = length(primary_samples),
      MantelSpearman = mantel_result$statistic,
      MantelP = mantel_result$signif,
      ProcrustesCorrelation = protest_result$t0,
      ProcrustesP = protest_result$signif
    ),
    file.path(out_dir, "domain_concordance_primary.csv"),
    row.names = FALSE
  )
}

available_results <- list()
if (!is.null(results_16s)) available_results[["16S"]] <- results_16s
if (!is.null(results_its)) available_results[["ITS"]] <- results_its
write.csv(
  data.frame(
    Domain = names(available_results),
    Samples = vapply(available_results, `[[`, integer(1), "n_samples"),
    Taxa = vapply(available_results, `[[`, integer(1), "n_taxa"),
    TaxonomyAssigned = vapply(
      available_results,
      `[[`,
      logical(1),
      "taxonomy_assigned"
    ),
    PrimaryRarefactionDepth = vapply(available_results, `[[`, numeric(1), "depth_primary"),
    SensitivityRarefactionDepth = vapply(
      available_results,
      `[[`,
      numeric(1),
      "depth_sensitivity"
    )
  ),
  file.path(out_dir, "asv_run_summary.csv"),
  row.names = FALSE
)

writeLines("ASV diversity analysis completed.", file.path(out_dir, "COMPLETE.txt"))
