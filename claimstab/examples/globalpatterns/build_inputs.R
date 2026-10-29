options(stringsAsFactors = FALSE)
suppressPackageStartupMessages({
  library(phyloseq)
  library(vegan)
})

args <- commandArgs(trailingOnly = TRUE)
output_dir <- if (length(args) >= 1) args[[1]] else "."
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
set.seed(20261025)

RARE_DEPTH <- 58688
ALPHA <- 0.05

data(GlobalPatterns)
sample_table <- data.frame(sample_data(GlobalPatterns), check.names = FALSE)
sample_table$SampleType <- factor(sample_table$SampleType)
sample_table$EnvironmentClass <- factor(
  ifelse(sample_table$SampleType == "Mock", "Mock", "Environmental"),
  levels = c("Environmental", "Mock")
)

aggregate_rank <- function(ps, rank_name) {
  counts <- as(otu_table(ps), "matrix")
  if (!taxa_are_rows(ps)) {
    counts <- t(counts)
  }
  tax <- as(tax_table(ps), "matrix")
  labels <- tax[, rank_name]
  labels[is.na(labels) | !nzchar(labels)] <- "Unclassified"
  aggregated <- rowsum(counts, group = labels, reorder = TRUE)
  t(aggregated)
}

otu_counts <- t(as(otu_table(GlobalPatterns), "matrix"))
genus_counts <- aggregate_rank(GlobalPatterns, "Genus")
phylum_counts <- aggregate_rank(GlobalPatterns, "Phylum")
feature_matrices <- list(
  OTU = otu_counts,
  Genus = genus_counts,
  Phylum = phylum_counts
)

total_differences <- vapply(
  feature_matrices,
  function(matrix) max(abs(rowSums(matrix) - rowSums(otu_counts))),
  numeric(1)
)

eta_squared <- function(values, groups) {
  grand_mean <- mean(values)
  total_ss <- sum((values - grand_mean)^2)
  between_ss <- sum(vapply(
    split(values, groups),
    function(current) length(current) * (mean(current) - grand_mean)^2,
    numeric(1)
  ))
  between_ss / total_ss
}

welch_test <- function(values, groups) {
  result <- oneway.test(values ~ groups, var.equal = FALSE)
  data.frame(
    F = unname(result$statistic),
    P = result$p.value,
    Eta2 = eta_squared(values, groups)
  )
}

alpha_rows <- list()
beta_rows <- list()

for (sample_set in c("all26", "environmental23")) {
  keep_samples <- if (sample_set == "all26") {
    rownames(sample_table)
  } else {
    rownames(sample_table)[sample_table$SampleType != "Mock"]
  }
  metadata <- sample_table[keep_samples, , drop = FALSE]
  metadata$SampleType <- droplevels(metadata$SampleType)

  for (pipeline in names(feature_matrices)) {
    counts <- feature_matrices[[pipeline]][keep_samples, , drop = FALSE]
    counts <- counts[, colSums(counts) > 0, drop = FALSE]
    rare <- rrarefy(counts, sample = RARE_DEPTH)
    observed <- rowSums(rare > 0)
    shannon <- diversity(rare, index = "shannon")
    simpson <- diversity(rare, index = "simpson")

    for (metric in c("Observed", "Shannon", "Simpson")) {
      values <- switch(
        metric,
        Observed = observed,
        Shannon = shannon,
        Simpson = simpson
      )
      result <- welch_test(as.numeric(values), metadata$SampleType)
      alpha_rows[[length(alpha_rows) + 1]] <- data.frame(
        claim_id = paste0("GP_alpha_", metric),
        domain = "16S",
        outcome = "alpha_diversity",
        contrast = metric,
        pipeline = pipeline,
        sample_set = sample_set,
        estimate = result$F,
        p_value = result$P,
        direction = "not_applicable",
        rank = NA_integer_,
        testable = TRUE,
        source = "GlobalPatterns via phyloseq",
        notes = paste0("eta2=", signif(result$Eta2, 6))
      )
    }

    relative <- sweep(counts, 1, rowSums(counts), "/")
    bray <- vegdist(relative, method = "bray")
    pseudo <- relative + 0.5
    clr <- log(pseudo / rowSums(pseudo))
    clr <- clr - rowMeans(clr)
    aitchison <- dist(clr, method = "euclidean")

    for (metric in c("Bray", "Aitchison")) {
      distance <- if (metric == "Bray") bray else aitchison
      model <- adonis2(
        distance ~ SampleType,
        data = metadata,
        permutations = 9999
      )
      beta_rows[[length(beta_rows) + 1]] <- data.frame(
        claim_id = paste0("GP_beta_", metric),
        domain = "16S",
        outcome = "community_composition",
        contrast = "SampleType",
        pipeline = pipeline,
        sample_set = sample_set,
        estimate = model$R2[1],
        p_value = model$`Pr(>F)`[1],
        direction = "not_applicable",
        rank = NA_integer_,
        testable = TRUE,
        source = "GlobalPatterns via phyloseq",
        notes = "PERMANOVA R2"
      )
    }

    if (sample_set == "all26") {
      for (metric in c("Bray", "Aitchison")) {
        distance <- if (metric == "Bray") bray else aitchison
        model <- adonis2(
          distance ~ EnvironmentClass,
          data = metadata,
          permutations = 9999
        )
        beta_rows[[length(beta_rows) + 1]] <- data.frame(
          claim_id = paste0("GP_mock_", metric),
          domain = "16S",
          outcome = "mock_vs_environment",
          contrast = "Mock vs environmental",
          pipeline = pipeline,
          sample_set = sample_set,
          estimate = model$R2[1],
          p_value = model$`Pr(>F)`[1],
          direction = "not_applicable",
          rank = NA_integer_,
          testable = TRUE,
          source = "GlobalPatterns via phyloseq",
          notes = "PERMANOVA R2"
        )
      }
    }
  }
}

claims <- data.frame(
  claim_id = c(
    "GP_alpha_Observed",
    "GP_alpha_Shannon",
    "GP_alpha_Simpson",
    "GP_beta_Bray",
    "GP_beta_Aitchison",
    "GP_mock_Bray",
    "GP_mock_Aitchison"
  ),
  claim_text = c(
    "Observed richness differs by sample type",
    "Shannon diversity differs by sample type",
    "Simpson diversity differs by sample type",
    "Bray-Curtis composition differs by sample type",
    "Aitchison composition differs by sample type",
    "Mock communities differ from environmental samples on Bray-Curtis",
    "Mock communities differ from environmental samples on Aitchison"
  ),
  claim_type = "difference",
  reconstruction_id = "R_aggregation",
  manual_evidence_grade = "",
  notes = ""
)

reconstruction <- data.frame(
  reconstruction_id = rep("R_aggregation", 3),
  domain = "16S",
  layer = c("OTU", "Genus", "Phylum"),
  metric = c("sample_total_difference_vs_OTU", "sample_total_difference_vs_OTU", "sample_total_difference_vs_OTU"),
  value = c(0, total_differences[["Genus"]], total_differences[["Phylum"]]),
  threshold = "0",
  status = "stable",
  source = "GlobalPatterns via phyloseq",
  notes = c(
    "Reference layer",
    "All reads retained; missing genus assigned Unclassified",
    "All reads retained; missing phylum assigned Unclassified"
  )
)

endpoints <- rbind(do.call(rbind, alpha_rows), do.call(rbind, beta_rows))
write.csv(
  claims,
  file.path(output_dir, "claims.csv"),
  row.names = FALSE
)
write.csv(
  reconstruction,
  file.path(output_dir, "reconstruction.csv"),
  row.names = FALSE
)
write.csv(
  endpoints,
  file.path(output_dir, "endpoints.csv"),
  row.names = FALSE
)

print(
  aggregate(
    p_value ~ claim_id + sample_set,
    data = endpoints,
    FUN = function(x) paste(signif(x, 4), collapse = "/")
  )
)
