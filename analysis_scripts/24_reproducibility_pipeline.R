options(stringsAsFactors = FALSE)
suppressPackageStartupMessages({
  library(vegan)
})

args <- commandArgs(trailingOnly = TRUE)
get_arg <- function(flag, default = "") {
  index <- match(flag, args)
  if (is.na(index) || index == length(args)) default else args[[index + 1]]
}

input_dir <- get_arg("--input-dir")
output_dir <- get_arg("--output-dir")
if (!nzchar(input_dir) || !nzchar(output_dir)) {
  stop("--input-dir and --output-dir are required")
}
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

seed <- 20261023
set.seed(seed)

group_levels <- c("As", "AFP", "AEFP", "BP", "Natural", "Unassigned")
artificial <- c("As", "AFP", "AEFP", "BP")
metrics <- c("Observed", "Shannon", "Simpson")
pipelines <- c("original_phylum", "current_asv_phylum")
domains <- c("16S", "ITS")

read_input <- function(name) {
  table <- read.csv(
    file.path(input_dir, name),
    check.names = FALSE,
    fileEncoding = "UTF-8"
  )
  names(table)[1] <- sub("^\ufeff", "", names(table)[1])
  table
}

samples <- read_input("sample_sheet.csv")
samples$Primary5 <- tolower(as.character(samples$Primary5)) %in% c("true", "1", "yes")
samples$Composition <- factor(samples$Composition, levels = group_levels)
rownames(samples) <- samples$Sample

read_count_matrix <- function(pipeline, domain) {
  filename <- if (pipeline == "original_phylum") {
    paste0("original_phylum_counts_", domain, ".csv")
  } else {
    paste0("current_asv_phylum_counts_", domain, ".csv")
  }
  table <- read_input(filename)
  matrix <- as.matrix(table[, -1, drop = FALSE])
  rownames(matrix) <- table[[1]]
  matrix
}

relative_rows <- function(matrix) {
  totals <- rowSums(matrix)
  if (any(totals <= 0)) stop("Zero-count sample encountered")
  matrix / totals
}

clr_distance <- function(matrix) {
  pseudo <- matrix + 0.5
  clr <- log(pseudo / rowSums(pseudo))
  clr <- clr - rowMeans(clr)
  dist(clr, method = "euclidean")
}

run_beta <- function(pipeline, domain, sample_set) {
  counts <- read_count_matrix(pipeline, domain)
  metadata <- if (sample_set == "primary") {
    samples[samples$Primary5, , drop = FALSE]
  } else {
    samples
  }
  counts <- counts[rownames(metadata), , drop = FALSE]
  counts <- counts[, colSums(counts) > 0, drop = FALSE]
  relative <- relative_rows(counts)
  bray <- vegdist(relative, method = "bray")

  permanova <- adonis2(
    bray ~ Composition,
    data = metadata,
    permutations = 9999
  )
  dispersion <- betadisper(bray, metadata$Composition)
  dispersion_test <- permutest(dispersion, permutations = 9999)
  bray_row <- data.frame(
    Pipeline = pipeline,
    Domain = domain,
    SampleSet = sample_set,
    Metric = "Bray-Curtis",
    N = nrow(metadata),
    Features = ncol(counts),
    F = permanova$F[1],
    R2 = permanova$R2[1],
    P = permanova$`Pr(>F)`[1],
    DispersionF = dispersion_test$tab$F[1],
    DispersionP = dispersion_test$tab$`Pr(>F)`[1]
  )

  aitchison <- clr_distance(counts)
  aitchison_permanova <- adonis2(
    aitchison ~ Composition,
    data = metadata,
    permutations = 9999
  )
  aitchison_row <- data.frame(
    Pipeline = pipeline,
    Domain = domain,
    SampleSet = sample_set,
    Metric = "Aitchison",
    N = nrow(metadata),
    Features = ncol(counts),
    F = aitchison_permanova$F[1],
    R2 = aitchison_permanova$R2[1],
    P = aitchison_permanova$`Pr(>F)`[1],
    DispersionF = NA_real_,
    DispersionP = NA_real_
  )
  rbind(bray_row, aitchison_row)
}

beta_rows <- list()
for (pipeline in pipelines) {
  for (domain in domains) {
    for (sample_set in c("primary", "sensitivity18")) {
      beta_rows[[length(beta_rows) + 1]] <- run_beta(
        pipeline, domain, sample_set
      )
    }
  }
}
beta_results <- do.call(rbind, beta_rows)
write.csv(
  beta_results,
  file.path(output_dir, "beta_pipeline_sensitivity.csv"),
  row.names = FALSE
)

read_current_alpha <- function(domain, sample_set) {
  suffix <- if (sample_set == "primary") "primary" else "sensitivity"
  read_input(paste0("current_alpha_", domain, "_", suffix, ".csv"))
}

build_alpha_comparison <- function(domain) {
  original <- read_input("original_alpha.csv")
  original <- original[original$Domain == domain, , drop = FALSE]
  original$Observed <- original$sobs
  original$Shannon <- original$shannon
  original$SimpsonComparable <- 1 - original$simpson

  current_sensitivity <- read_current_alpha(domain, "sensitivity")
  current_primary <- read_current_alpha(domain, "primary")
  current_metrics <- current_sensitivity[, c("Sample", "Observed", "Shannon", "Simpson")]
  names(current_metrics) <- c(
    "Sample", "Observed_CurrentASV", "Shannon_CurrentASV", "Simpson_CurrentASV"
  )
  original_metrics <- data.frame(
    Sample = original$Sample,
    Observed_OriginalOTU = original$Observed,
    Shannon_OriginalOTU = original$Shannon,
    Simpson_OriginalOTU = original$SimpsonComparable,
    check.names = FALSE
  )
  merged <- merge(
    original_metrics,
    current_metrics,
    by = "Sample",
    all = FALSE
  )
  merged$Domain <- domain
  merged <- merge(
    merged,
    samples[, c("Sample", "Composition", "Primary5")],
    by = "Sample",
    all.x = TRUE
  )
  merged
}

alpha_comparisons <- do.call(
  rbind,
  lapply(domains, build_alpha_comparison)
)
write.csv(
  alpha_comparisons,
  file.path(output_dir, "alpha_sample_pipeline_comparison.csv"),
  row.names = FALSE
)

alpha_concordance_rows <- list()
alpha_test_rows <- list()
alpha_group_rows <- list()
for (domain in domains) {
  subset <- alpha_comparisons[alpha_comparisons$Domain == domain, , drop = FALSE]
  original_columns <- paste0(metrics, "_OriginalOTU")
  current_columns <- paste0(metrics, "_CurrentASV")
  for (index in seq_along(metrics)) {
    old_values <- subset[[original_columns[index]]]
    current_values <- subset[[current_columns[index]]]
    alpha_concordance_rows[[length(alpha_concordance_rows) + 1]] <- data.frame(
      Domain = domain,
      Metric = metrics[index],
      N = nrow(subset),
      Spearman = cor(old_values, current_values, method = "spearman"),
      Pearson = cor(old_values, current_values),
      OriginalMean = mean(old_values),
      CurrentMean = mean(current_values)
    )
  }

  for (pipeline in c("OriginalOTU", "CurrentASV")) {
    for (metric in metrics) {
      column <- paste0(metric, "_", pipeline)
      primary <- subset[subset$Primary5, , drop = FALSE]
      model <- oneway.test(primary[[column]] ~ primary$Composition, var.equal = FALSE)
      alpha_test_rows[[length(alpha_test_rows) + 1]] <- data.frame(
        Domain = domain,
        Pipeline = pipeline,
        SampleSet = "primary",
        Metric = metric,
        N = nrow(primary),
        WelchF = unname(model$statistic),
        P = model$p.value
      )
      for (group in group_levels[group_levels != "Unassigned"]) {
        values <- subset[[column]][subset$Composition == group]
        if (length(values) == 0) next
        alpha_group_rows[[length(alpha_group_rows) + 1]] <- data.frame(
          Domain = domain,
          Pipeline = pipeline,
          Metric = metric,
          Composition = group,
          N = length(values),
          Mean = mean(values),
          SD = sd(values),
          SE = sd(values) / sqrt(length(values))
        )
      }
    }
  }
}

write.csv(
  do.call(rbind, alpha_concordance_rows),
  file.path(output_dir, "alpha_pipeline_concordance.csv"),
  row.names = FALSE
)
write.csv(
  do.call(rbind, alpha_test_rows),
  file.path(output_dir, "alpha_group_tests.csv"),
  row.names = FALSE
)
write.csv(
  do.call(rbind, alpha_group_rows),
  file.path(output_dir, "alpha_group_means.csv"),
  row.names = FALSE
)

sample_reference_distances <- function(relative, metadata) {
  natural <- rownames(metadata)[metadata$Composition == "Natural"]
  centroid <- colMeans(relative[natural, , drop = FALSE])
  numerator <- rowSums(abs(sweep(relative, 2, centroid)))
  denominator <- rowSums(relative) + sum(centroid)
  numerator / denominator
}

bootstrap_reference <- function(relative, metadata) {
  indices <- lapply(group_levels[group_levels != "Unassigned"], function(group) {
    which(metadata$Composition == group)
  })
  names(indices) <- group_levels[group_levels != "Unassigned"]
  distributions <- setNames(vector("list", length(artificial)), artificial)
  ranks <- setNames(vector("list", length(artificial)), artificial)
  for (group in artificial) {
    distributions[[group]] <- numeric(20000)
    ranks[[group]] <- integer(20000)
  }

  for (iteration in seq_len(20000)) {
    natural_indices <- sample(
      indices[["Natural"]],
      length(indices[["Natural"]]),
      replace = TRUE
    )
    centroid <- colMeans(relative[natural_indices, , drop = FALSE])
    means <- numeric(length(artificial))
    names(means) <- artificial
    for (group in artificial) {
      sampled <- sample(indices[[group]], length(indices[[group]]), replace = TRUE)
      values <- rowSums(abs(sweep(
        relative[sampled, , drop = FALSE],
        2,
        centroid
      ))) / (rowSums(relative[sampled, , drop = FALSE]) + sum(centroid))
      means[[group]] <- mean(values)
      distributions[[group]][iteration] <- mean(values)
    }
    order_groups <- names(sort(means))
    for (rank_index in seq_along(order_groups)) {
      ranks[[order_groups[rank_index]]][iteration] <- rank_index
    }
  }

  observed_values <- sample_reference_distances(relative, metadata)
  observed_means <- vapply(artificial, function(group) {
    mean(observed_values[metadata$Composition == group])
  }, numeric(1))
  group_rows <- do.call(rbind, lapply(artificial, function(group) {
    values <- distributions[[group]]
    data.frame(
      Composition = group,
      N = sum(metadata$Composition == group),
      ObservedMeanDistance = observed_means[[group]],
      BootstrapMedian = median(values),
      CI2.5 = unname(quantile(values, 0.025)),
      CI97.5 = unname(quantile(values, 0.975)),
      ProbabilityClosest = mean(ranks[[group]] == 1),
      ProbabilityRank1Or2 = mean(ranks[[group]] <= 2)
    )
  }))

  difference_rows <- do.call(rbind, lapply(c("As", "AFP", "BP"), function(comparator) {
    difference <- distributions[["AEFP"]] - distributions[[comparator]]
    data.frame(
      Contrast = paste0("AEFP minus ", comparator),
      ObservedDifference = observed_means[["AEFP"]] - observed_means[[comparator]],
      BootstrapMedian = median(difference),
      CI2.5 = unname(quantile(difference, 0.025)),
      CI97.5 = unname(quantile(difference, 0.975)),
      ProbabilityAEFPCloser = mean(difference < 0)
    )
  }))
  list(groups = group_rows, differences = difference_rows)
}

exact_label_permutation <- function(relative, metadata) {
  values_all <- sample_reference_distances(relative, metadata)
  artificial_metadata <- metadata[metadata$Composition %in% artificial, , drop = FALSE]
  values <- values_all[rownames(artificial_metadata)]
  observed_means <- vapply(artificial, function(group) {
    mean(values[artificial_metadata$Composition == group])
  }, numeric(1))
  observed_range <- max(observed_means) - min(observed_means)
  observed_pairwise <- vapply(c("As", "AFP", "BP"), function(comparator) {
    abs(observed_means[["AEFP"]] - observed_means[[comparator]])
  }, numeric(1))

  total <- 0L
  range_exceed <- 0L
  pairwise_exceed <- setNames(integer(3), c("As", "AFP", "BP"))
  positions <- seq_along(values)
  for (as_indices in combn(positions, 3, simplify = FALSE)) {
    remain_as <- setdiff(positions, as_indices)
    for (afp_indices in combn(remain_as, 3, simplify = FALSE)) {
      remain_afp <- setdiff(remain_as, afp_indices)
      for (aefp_indices in combn(remain_afp, 3, simplify = FALSE)) {
        bp_indices <- setdiff(remain_afp, aefp_indices)
        means <- c(
          As = mean(values[as_indices]),
          AFP = mean(values[afp_indices]),
          AEFP = mean(values[aefp_indices]),
          BP = mean(values[bp_indices])
        )
        total <- total + 1L
        if (max(means) - min(means) >= observed_range - 1e-12) {
          range_exceed <- range_exceed + 1L
        }
        for (comparator in names(pairwise_exceed)) {
          if (abs(means[["AEFP"]] - means[[comparator]]) >=
              observed_pairwise[[comparator]] - 1e-12) {
            pairwise_exceed[[comparator]] <- pairwise_exceed[[comparator]] + 1L
          }
        }
      }
    }
  }

  rows <- list()
  raw_p <- numeric(length(pairwise_exceed))
  names(raw_p) <- names(pairwise_exceed)
  for (comparator in names(pairwise_exceed)) {
    raw_p[[comparator]] <- (pairwise_exceed[[comparator]] + 1) / (total + 1)
    rows[[length(rows) + 1]] <- data.frame(
      Test = paste0("AEFP vs ", comparator, " (two-sided)"),
      ObservedAbsoluteDifference = observed_pairwise[[comparator]],
      RawExactP = raw_p[[comparator]]
    )
  }
  adjusted <- p.adjust(raw_p, method = "holm")
  for (index in seq_along(rows)) {
    comparator <- c("As", "AFP", "BP")[index]
    rows[[index]]$HolmAdjustedP <- adjusted[[comparator]]
  }
  rows[[length(rows) + 1]] <- data.frame(
    Test = "Any artificial-treatment difference (range)",
    ObservedAbsoluteDifference = observed_range,
    RawExactP = (range_exceed + 1) / (total + 1),
    HolmAdjustedP = NA_real_
  )
  result <- do.call(rbind, rows)
  result$PermutationsEnumerated <- total
  result$ObservedGroupMeans <- paste(
    sprintf("%s=%.6f", names(observed_means), observed_means),
    collapse = ";"
  )
  result
}

leave_one_out_reference <- function(relative, metadata) {
  rows <- list()
  for (drop_index in seq_len(nrow(metadata))) {
    subset_metadata <- metadata[-drop_index, , drop = FALSE]
    if (sum(subset_metadata$Composition == "Natural") < 1) next
    subset_relative <- relative[rownames(subset_metadata), , drop = FALSE]
    distances <- sample_reference_distances(subset_relative, subset_metadata)
    means <- vapply(artificial, function(group) {
      mean(distances[subset_metadata$Composition == group])
    }, numeric(1))
    order_groups <- names(sort(means))
    rows[[length(rows) + 1]] <- data.frame(
      DroppedSample = rownames(metadata)[drop_index],
      DroppedGroup = as.character(metadata$Composition[drop_index]),
      ClosestArtificial = order_groups[1],
      AEFPRankAmongArtificial = match("AEFP", order_groups),
      AsDistance = means[["As"]],
      AFPDistance = means[["AFP"]],
      AEFPDistance = means[["AEFP"]],
      BPDistance = means[["BP"]]
    )
  }
  do.call(rbind, rows)
}

bootstrap_groups <- list()
bootstrap_differences <- list()
exact_rows <- list()
loo_rows <- list()
for (pipeline in pipelines) {
  for (domain in domains) {
    message("Reference analysis: ", pipeline, " / ", domain)
    counts <- read_count_matrix(pipeline, domain)
    primary <- samples[samples$Primary5, , drop = FALSE]
    counts <- counts[rownames(primary), , drop = FALSE]
    relative <- relative_rows(counts)
    set.seed(seed + match(domain, domains) * 10 + match(pipeline, pipelines))
    bootstrap <- bootstrap_reference(relative, primary)
    groups <- bootstrap$groups
    groups$Pipeline <- pipeline
    groups$Domain <- domain
    differences <- bootstrap$differences
    differences$Pipeline <- pipeline
    differences$Domain <- domain
    bootstrap_groups[[length(bootstrap_groups) + 1]] <- groups
    bootstrap_differences[[length(bootstrap_differences) + 1]] <- differences

    exact <- exact_label_permutation(relative, primary)
    exact$Pipeline <- pipeline
    exact$Domain <- domain
    exact_rows[[length(exact_rows) + 1]] <- exact

    loo <- leave_one_out_reference(relative, primary)
    loo$Pipeline <- pipeline
    loo$Domain <- domain
    loo_rows[[length(loo_rows) + 1]] <- loo
  }
}

write.csv(
  do.call(rbind, bootstrap_groups),
  file.path(output_dir, "natural_reference_bootstrap.csv"),
  row.names = FALSE
)
write.csv(
  do.call(rbind, bootstrap_differences),
  file.path(output_dir, "natural_reference_bootstrap_differences.csv"),
  row.names = FALSE
)
write.csv(
  do.call(rbind, exact_rows),
  file.path(output_dir, "natural_reference_exact_permutation.csv"),
  row.names = FALSE
)
write.csv(
  do.call(rbind, loo_rows),
  file.path(output_dir, "natural_reference_leave_one_out.csv"),
  row.names = FALSE
)

parameters <- data.frame(
  Parameter = c(
    "RandomSeed", "PERMANOVAPermutations", "PERMDISPPermutations",
    "BootstrapIterations", "ExactArtificialPermutations",
    "PrimarySamples", "SensitivitySamples", "CurrentSimpson"
  ),
  Value = c(
    seed, 9999, 9999, 20000, 369600, 15, 18,
    "phyloseq estimate_richness; original Simpson transformed as 1-old_simpson"
  )
)
write.csv(
  parameters,
  file.path(output_dir, "analysis_parameters.csv"),
  row.names = FALSE
)
writeLines(
  "Reproducibility alpha, beta, and reference-distance analyses completed.",
  file.path(output_dir, "COMPLETE.txt")
)
