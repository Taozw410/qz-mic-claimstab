options(stringsAsFactors = FALSE, warn = 1)
suppressPackageStartupMessages({
  library(phyloseq)
  library(microbiome)
  library(vegan)
})

args <- commandArgs(trailingOnly = TRUE)
output_dir <- if (length(args) >= 1) args[[1]] else "."
main_dir <- file.path(output_dir, "main")
perm_dir <- file.path(output_dir, "permutation")
dir.create(main_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(perm_dir, recursive = TRUE, showWarnings = FALSE)

SEED <- 20261027
MAIN_PERMUTATIONS <- 999
NULL_PERMUTATIONS <- 999
LABEL_PERMUTATIONS <- 20
ALPHA <- 0.05

set.seed(SEED)

claims <- list()
endpoints <- list()
reconstructions <- list()

add_claim <- function(
    claim_id,
    claim_text,
    reconstruction_id,
    dataset,
    family,
    metric,
    condition,
    permutation_id = NA_integer_) {
  note <- paste(
    paste0("dataset=", dataset),
    paste0("family=", family),
    paste0("metric=", metric),
    paste0("condition=", condition),
    sep = ";"
  )
  if (!is.na(permutation_id)) {
    note <- paste(note, paste0("permutation_id=", permutation_id), sep = ";")
  }
  claims[[length(claims) + 1]] <<- data.frame(
    claim_id = claim_id,
    claim_text = claim_text,
    claim_type = "difference",
    reconstruction_id = reconstruction_id,
    manual_evidence_grade = "",
    notes = note
  )
}

add_reconstruction <- function(
    reconstruction_id,
    dataset,
    layer,
    metric,
    value,
    threshold,
    status,
    notes) {
  reconstructions[[length(reconstructions) + 1]] <<- data.frame(
    reconstruction_id = reconstruction_id,
    domain = dataset,
    layer = layer,
    metric = metric,
    value = value,
    threshold = threshold,
    status = status,
    source = paste0(dataset, " public dataset"),
    notes = notes
  )
}

add_endpoint <- function(
    claim_id,
    domain,
    outcome,
    contrast,
    pipeline,
    sample_set,
    estimate,
    p_value,
    testable,
    source,
    notes) {
  endpoints[[length(endpoints) + 1]] <<- data.frame(
    claim_id = claim_id,
    domain = domain,
    outcome = outcome,
    contrast = contrast,
    pipeline = pipeline,
    sample_set = sample_set,
    estimate = estimate,
    p_value = p_value,
    direction = "not_applicable",
    rank = NA_integer_,
    testable = testable,
    source = source,
    notes = notes
  )
}

counts_for_ps <- function(ps) {
  counts <- as(otu_table(ps), "matrix")
  if (taxa_are_rows(ps)) {
    counts <- t(counts)
  }
  storage.mode(counts) <- "double"
  counts
}

aggregate_rank_counts <- function(ps, rank_name) {
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

eta_squared <- function(values, groups) {
  grand_mean <- mean(values)
  total_ss <- sum((values - grand_mean)^2)
  if (!is.finite(total_ss) || total_ss <= 0) {
    return(NA_real_)
  }
  between_ss <- sum(vapply(
    split(values, groups),
    function(current) length(current) * (mean(current) - grand_mean)^2,
    numeric(1)
  ))
  between_ss / total_ss
}

safe_alpha_test <- function(values, groups) {
  tryCatch({
    values <- as.numeric(unlist(values, use.names = FALSE))
    groups <- factor(unlist(groups, use.names = FALSE))
    if (length(unique(groups)) < 2 || any(table(groups) < 2)) {
      return(c(F = NA_real_, P = NA_real_, Eta2 = NA_real_))
    }
    result <- oneway.test(values ~ groups, var.equal = FALSE)
    c(
      F = unname(result$statistic),
      P = unname(result$p.value),
      Eta2 = eta_squared(values, groups)
    )
  }, error = function(e) {
    c(F = NA_real_, P = NA_real_, Eta2 = NA_real_)
  })
}

alpha_values <- function(counts, mode, depth, seed) {
  if (mode == "rare") {
    integer_counts <- round(counts)
    storage.mode(integer_counts) <- "integer"
    if (any(rowSums(integer_counts) < depth)) {
      stop("Rarefaction depth exceeds a sample total")
    }
    set.seed(seed)
    evaluated <- vegan::rrarefy(integer_counts, sample = depth)
  } else {
    evaluated <- counts
  }
  list(
    Observed = rowSums(evaluated > 0),
    Shannon = vegan::diversity(evaluated, index = "shannon"),
    Simpson = vegan::diversity(evaluated, index = "simpson")
  )
}

distance_pair <- function(counts) {
  totals <- rowSums(counts)
  if (any(!is.finite(totals)) || any(totals <= 0)) {
    stop("Non-positive sample total")
  }
  relative <- sweep(counts, 1, totals, "/")
  bray <- vegan::vegdist(relative, method = "bray")
  pseudo <- relative + 0.5
  log_prob <- log(pseudo / rowSums(pseudo))
  clr <- log_prob - rowMeans(log_prob)
  aitchison <- dist(clr, method = "euclidean")
  list(Bray = bray, Aitchison = aitchison)
}

safe_adonis <- function(distance, groups, permutations) {
  tryCatch({
    groups <- factor(groups)
    if (length(unique(groups)) < 2 || any(table(groups) < 2)) {
      return(c(R2 = NA_real_, P = NA_real_))
    }
    model <- vegan::adonis2(
      distance ~ groups,
      data = data.frame(groups = groups),
      permutations = permutations
    )
    c(
      R2 = unname(model$R2[1]),
      P = unname(model$`Pr(>F)`[1])
    )
  }, error = function(e) {
    c(R2 = NA_real_, P = NA_real_)
  })
}

evaluate_grid <- function(
    claim_base,
    domain,
    contrast,
    sample_set,
    sample_ids,
    groups,
    alpha_specs,
    beta_specs,
    source,
    permutations,
    seed) {
  groups <- factor(groups)
  names(groups) <- sample_ids
  row_index <- match(sample_ids, rownames(groups))
  if (length(sample_ids) != length(groups) || any(is.na(groups))) {
    stop("Group vector does not match sample IDs")
  }

  for (spec in alpha_specs) {
    counts <- spec$counts[sample_ids, , drop = FALSE]
    counts <- counts[, colSums(counts) > 0, drop = FALSE]
    values <- alpha_values(counts, spec$mode, spec$depth, seed)
    for (metric in c("Observed", "Shannon", "Simpson")) {
      result <- safe_alpha_test(as.numeric(values[[metric]]), groups)
      add_endpoint(
        claim_id = paste0(claim_base, "_alpha_", metric),
        domain = domain,
        outcome = "alpha_diversity",
        contrast = metric,
        pipeline = spec$pipeline,
        sample_set = sample_set,
        estimate = result[["Eta2"]],
        p_value = result[["P"]],
        testable = is.finite(result[["P"]]),
        source = source,
        notes = paste0(
          "F=", signif(result[["F"]], 6),
          "; eta2=", signif(result[["Eta2"]], 6),
          "; n=", length(sample_ids),
          "; k=", nlevels(groups)
        )
      )
    }
  }

  for (spec in beta_specs) {
    counts <- spec$counts[sample_ids, , drop = FALSE]
    counts <- counts[, colSums(counts) > 0, drop = FALSE]
    distances <- distance_pair(counts)
    for (metric in c("Bray", "Aitchison")) {
      result <- safe_adonis(
        distances[[metric]],
        groups,
        permutations = permutations
      )
      add_endpoint(
        claim_id = paste0(claim_base, "_beta_", metric),
        domain = domain,
        outcome = "beta_composition",
        contrast = metric,
        pipeline = spec$pipeline,
        sample_set = sample_set,
        estimate = result[["R2"]],
        p_value = result[["P"]],
        testable = is.finite(result[["P"]]),
        source = source,
        notes = paste0(
          "PERMANOVA R2; n=", length(sample_ids),
          "; k=", nlevels(groups)
        )
      )
    }
  }
}

precompute_grid <- function(
    sample_ids,
    alpha_specs,
    beta_specs,
    seed) {
  alpha_cache <- list()
  beta_cache <- list()
  for (spec in alpha_specs) {
    counts <- spec$counts[sample_ids, , drop = FALSE]
    counts <- counts[, colSums(counts) > 0, drop = FALSE]
    alpha_cache[[spec$pipeline]] <- alpha_values(
      counts, spec$mode, spec$depth, seed
    )
  }
  for (spec in beta_specs) {
    counts <- spec$counts[sample_ids, , drop = FALSE]
    counts <- counts[, colSums(counts) > 0, drop = FALSE]
    beta_cache[[spec$pipeline]] <- distance_pair(counts)
  }
  list(alpha = alpha_cache, beta = beta_cache)
}

evaluate_precomputed <- function(
    claim_base,
    domain,
    contrast,
    sample_set,
    sample_ids,
    groups,
    cached,
    source,
    permutations) {
  groups <- factor(groups)
  if (length(sample_ids) != length(groups) || any(is.na(groups))) {
    stop("Group vector does not match sample IDs")
  }
  for (pipeline in names(cached$alpha)) {
    values <- cached$alpha[[pipeline]]
    for (metric in c("Observed", "Shannon", "Simpson")) {
      result <- safe_alpha_test(as.numeric(values[[metric]]), groups)
      add_endpoint(
        claim_id = paste0(claim_base, "_alpha_", metric),
        domain = domain,
        outcome = "alpha_diversity",
        contrast = metric,
        pipeline = pipeline,
        sample_set = sample_set,
        estimate = result[["Eta2"]],
        p_value = result[["P"]],
        testable = is.finite(result[["P"]]),
        source = source,
        notes = paste0(
          "F=", signif(result[["F"]], 6),
          "; eta2=", signif(result[["Eta2"]], 6),
          "; n=", length(sample_ids),
          "; k=", nlevels(groups)
        )
      )
    }
  }
  for (pipeline in names(cached$beta)) {
    distances <- cached$beta[[pipeline]]
    for (metric in c("Bray", "Aitchison")) {
      result <- safe_adonis(
        distances[[metric]],
        groups,
        permutations = permutations
      )
      add_endpoint(
        claim_id = paste0(claim_base, "_beta_", metric),
        domain = domain,
        outcome = "beta_composition",
        contrast = metric,
        pipeline = pipeline,
        sample_set = sample_set,
        estimate = result[["R2"]],
        p_value = result[["P"]],
        testable = is.finite(result[["P"]]),
        source = source,
        notes = paste0(
          "PERMANOVA R2; n=", length(sample_ids),
          "; k=", nlevels(groups)
        )
      )
    }
  }
}

write_table <- function(x, path) {
  write.csv(x, path, row.names = FALSE, na = "")
}

manifest <- list()
add_manifest <- function(
    dataset,
    source_package,
    study,
    citation,
    doi,
    platform,
    samples_used,
    contrast) {
  manifest[[length(manifest) + 1]] <<- data.frame(
    dataset = dataset,
    source_package = source_package,
    study = study,
    citation = citation,
    doi = doi,
    platform = platform,
    samples_used = samples_used,
    contrast = contrast
  )
}

# GlobalPatterns -----------------------------------------------------------

data(GlobalPatterns, package = "phyloseq")
gp_counts <- list(
  OTU = counts_for_ps(GlobalPatterns),
  Genus = aggregate_rank_counts(GlobalPatterns, "Genus"),
  Phylum = aggregate_rank_counts(GlobalPatterns, "Phylum")
)
gp_meta <- data.frame(sample_data(GlobalPatterns), check.names = FALSE)
gp_depth <- min(rowSums(gp_counts$OTU))
gp_alpha_specs <- lapply(names(gp_counts), function(pipeline) {
  list(
    pipeline = pipeline,
    counts = gp_counts[[pipeline]],
    mode = "rare",
    depth = gp_depth
  )
})
gp_beta_specs <- lapply(names(gp_counts), function(pipeline) {
  list(pipeline = pipeline, counts = gp_counts[[pipeline]])
})

gp_claim_ids <- c(
  "GP_alpha_Observed",
  "GP_alpha_Shannon",
  "GP_alpha_Simpson",
  "GP_beta_Bray",
  "GP_beta_Aitchison"
)
for (metric in c("Observed", "Shannon", "Simpson", "Bray", "Aitchison")) {
  family <- if (metric %in% c("Observed", "Shannon", "Simpson")) {
    "alpha"
  } else {
    "beta"
  }
  add_claim(
    paste0("GP_", family, "_", metric),
    paste("GlobalPatterns sample type differs for", metric),
    "GP_AGG",
    "GlobalPatterns",
    family,
    metric,
    "SampleType"
  )
}
for (metric in c("Bray", "Aitchison")) {
  add_claim(
    paste0("GP_mock_beta_", metric),
    paste("Mock communities differ from environmental samples for", metric),
    "GP_AGG",
    "GlobalPatterns",
    "beta",
    metric,
    "Mock_vs_environment"
  )
}

gp_total_diff <- vapply(
  gp_counts,
  function(current) max(abs(rowSums(current) - rowSums(gp_counts$OTU))),
  numeric(1)
)
add_reconstruction(
  "GP_AGG", "GlobalPatterns", "OTU_to_phylum", "sample_total_difference",
  0, 0, "stable", "OTU reference layer"
)
add_reconstruction(
  "GP_AGG", "GlobalPatterns", "Genus", "sample_total_difference",
  gp_total_diff[["Genus"]], 0, "stable", "Genus aggregation"
)
add_reconstruction(
  "GP_AGG", "GlobalPatterns", "Phylum", "sample_total_difference",
  gp_total_diff[["Phylum"]], 0, "stable", "Phylum aggregation"
)

for (sample_set in c("all26", "environmental23")) {
  sample_ids <- if (sample_set == "all26") {
    rownames(gp_meta)
  } else {
    rownames(gp_meta)[gp_meta$SampleType != "Mock"]
  }
  groups <- factor(gp_meta[sample_ids, "SampleType"])
  evaluate_grid(
    claim_base = "GP",
    domain = "16S",
    contrast = "SampleType",
    sample_set = sample_set,
    sample_ids = sample_ids,
    groups = groups,
    alpha_specs = gp_alpha_specs,
    beta_specs = gp_beta_specs,
    source = "GlobalPatterns via phyloseq",
    permutations = MAIN_PERMUTATIONS,
    seed = SEED
  )
}

gp_sample_ids <- rownames(gp_meta)
gp_env_class <- factor(
  ifelse(gp_meta$SampleType == "Mock", "Mock", "Environmental"),
  levels = c("Environmental", "Mock")
)
names(gp_env_class) <- gp_sample_ids
evaluate_grid(
  claim_base = "GP_mock",
  domain = "16S",
  contrast = "Mock_vs_environment",
  sample_set = "all26",
  sample_ids = gp_sample_ids,
  groups = gp_env_class,
  alpha_specs = list(),
  beta_specs = gp_beta_specs,
  source = "GlobalPatterns via phyloseq",
  permutations = MAIN_PERMUTATIONS,
  seed = SEED
)
add_manifest(
  "GlobalPatterns", "phyloseq", "Global patterns of 16S rRNA diversity",
  "Caporaso et al. 2011 PNAS 108:4516-4522", "10.1073/pnas.1000080107",
  "Illumina 16S", 26, "SampleType; Mock_vs_environment"
)

# Enterotype ---------------------------------------------------------------

data(enterotype, package = "phyloseq")
en_all <- counts_for_ps(enterotype)
en_tax <- as(tax_table(enterotype), "matrix")
en_labels <- en_tax[, 1]
en_keep <- !is.na(en_labels) &
  nzchar(en_labels) &
  !en_labels %in% c("-1", "Bacteria")
en_filtered <- en_all[, en_keep, drop = FALSE]
en_filtered <- en_filtered[, colSums(en_filtered) > 0, drop = FALSE]
en_counts <- list(GenusAll = en_all, GenusFiltered = en_filtered)
en_meta <- data.frame(sample_data(enterotype), check.names = FALSE)

set.seed(SEED)
en_balanced <- unlist(lapply(
  split(rownames(en_meta), en_meta$SeqTech),
  function(ids) sample(ids, 41, replace = FALSE)
))
en_balanced <- sort(en_balanced)

for (metric in c("Observed", "Shannon", "Simpson", "Bray", "Aitchison")) {
  family <- if (metric %in% c("Observed", "Shannon", "Simpson")) {
    "alpha"
  } else {
    "beta"
  }
  add_claim(
    paste0("EN_", family, "_", metric),
    paste("Enterotype genera differ by sequencing technology for", metric),
    "EN_FILTER",
    "enterotype",
    family,
    metric,
    "SeqTech"
  )
}
en_alpha_specs <- lapply(names(en_counts), function(pipeline) {
  list(
    pipeline = pipeline,
    counts = en_counts[[pipeline]],
    mode = "proportion",
    depth = NA_real_
  )
})
en_beta_specs <- lapply(names(en_counts), function(pipeline) {
  list(pipeline = pipeline, counts = en_counts[[pipeline]])
})
en_total_diff <- max(abs(rowSums(en_filtered) - rowSums(en_all)))
en_status <- if (en_total_diff <= 1e-8) "stable" else "partial"
add_reconstruction(
  "EN_FILTER", "enterotype", "Genus_filtered",
  "sample_total_difference", en_total_diff, "1e-8", en_status,
  "Exclude -1, Bacteria and missing genus labels"
)

for (sample_set in c("all280", "stratified123")) {
  sample_ids <- if (sample_set == "all280") rownames(en_meta) else en_balanced
  groups <- factor(en_meta[sample_ids, "SeqTech"])
  evaluate_grid(
    claim_base = "EN",
    domain = "genus_profile",
    contrast = "SeqTech",
    sample_set = sample_set,
    sample_ids = sample_ids,
    groups = groups,
    alpha_specs = en_alpha_specs,
    beta_specs = en_beta_specs,
    source = "enterotype via phyloseq",
    permutations = MAIN_PERMUTATIONS,
    seed = SEED
  )
}
add_manifest(
  "enterotype", "phyloseq", "Enterotypes of the human gut microbiome",
  "Arumugam et al. 2011 Nature 473:174-180", "10.1038/nature09944",
  "mixed sequencing genus profiles", 280,
  "SeqTech; all samples vs balanced 41 per technology"
)

# Soil reproducibility -----------------------------------------------------

data(soilrep, package = "phyloseq")
soil_raw_counts <- counts_for_ps(soilrep)
soil_raw_meta <- data.frame(sample_data(soilrep), check.names = FALSE)
soil_counts <- rowsum(soil_raw_counts, group = soil_raw_meta$Sample)
soil_meta <- soil_raw_meta[
  !duplicated(soil_raw_meta$Sample),
  c("Sample", "Treatment", "warmed", "clipped")
]
soil_meta <- soil_meta[match(rownames(soil_counts), soil_meta$Sample), ]
rownames(soil_meta) <- soil_meta$Sample
soil_meta$Warmed <- factor(soil_meta$warmed, levels = c("no", "yes"))
soil_meta$Clipped <- factor(soil_meta$clipped, levels = c("no", "yes"))
soil_prev <- soil_counts[, colSums(soil_counts > 0) >= 0.10 * nrow(soil_counts)]
soil_prev <- soil_prev[, colSums(soil_prev) > 0, drop = FALSE]
soil_beta_counts <- list(OTUall = soil_counts, OTUprev10 = soil_prev)

for (condition in c("Warmed", "Clipped")) {
  for (metric in c("Observed", "Shannon", "Simpson", "Bray", "Aitchison")) {
    family <- if (metric %in% c("Observed", "Shannon", "Simpson")) {
      "alpha"
    } else {
      "beta"
    }
    add_claim(
      paste0("SOIL_", condition, "_", family, "_", metric),
      paste(condition, "treatment differs for", metric),
      "SOIL_RECON",
      "soilrep",
      family,
      metric,
      condition
    )
  }
}
soil_total_diff <- max(abs(rowSums(soil_prev) - rowSums(soil_counts)))
add_reconstruction(
  "SOIL_RECON", "soilrep", "OTU", "sample_total_difference",
  0, 0, "partial",
  "Reference; beta sensitivity includes 10% prevalence filtering"
)
add_reconstruction(
  "SOIL_RECON", "soilrep", "OTUprev10", "sample_total_difference",
  soil_total_diff, 0, "partial",
  "Prevalence filtering changes sample totals"
)
soil_alpha_specs <- lapply(c(500, 1500), function(depth) {
  list(
    pipeline = paste0("OTU_rare", depth),
    counts = soil_counts,
    mode = "rare",
    depth = depth
  )
})
soil_beta_specs <- lapply(names(soil_beta_counts), function(pipeline) {
  list(pipeline = pipeline, counts = soil_beta_counts[[pipeline]])
})

soil_sample_sets <- list(
  Warmed = list(
    all24 = rownames(soil_meta),
    clipped12 = rownames(soil_meta)[soil_meta$Clipped == "yes"],
    unclipped12 = rownames(soil_meta)[soil_meta$Clipped == "no"]
  ),
  Clipped = list(
    all24 = rownames(soil_meta),
    warmed12 = rownames(soil_meta)[soil_meta$Warmed == "yes"],
    unwarmed12 = rownames(soil_meta)[soil_meta$Warmed == "no"]
  )
)
soil_cached <- lapply(
  soil_sample_sets,
  function(sets) {
    lapply(
      sets,
      function(sample_ids) {
        precompute_grid(
          sample_ids = sample_ids,
          alpha_specs = soil_alpha_specs,
          beta_specs = soil_beta_specs,
          seed = SEED
        )
      }
    )
  }
)
for (condition in names(soil_sample_sets)) {
  for (sample_set in names(soil_sample_sets[[condition]])) {
    sample_ids <- soil_sample_sets[[condition]][[sample_set]]
    groups <- factor(soil_meta[sample_ids, condition])
    evaluate_precomputed(
      claim_base = paste0("SOIL_", condition),
      domain = "16S",
      contrast = condition,
      sample_set = sample_set,
      sample_ids = sample_ids,
      groups = groups,
      cached = soil_cached[[condition]][[sample_set]],
      source = "soilrep via phyloseq",
      permutations = MAIN_PERMUTATIONS
    )
  }
}
add_manifest(
  "soilrep", "phyloseq", "Reproducibility of soil microbiome data",
  "Zhou et al. 2011 ISME Journal 5:1303-1313", "10.1038/ismej.2011.11",
  "454 16S", 24,
  "Warmed and Clipped; technical replicates aggregated to 24 communities"
)

# HITChip Atlas baseline ---------------------------------------------------

data(atlas1006, package = "microbiome")
atlas <- subset_samples(atlas1006, time == 0)
atlas_counts <- list(
  Phylum = aggregate_rank_counts(atlas, "Phylum"),
  Family = aggregate_rank_counts(atlas, "Family"),
  Genus = aggregate_rank_counts(atlas, "Genus")
)
atlas_meta <- data.frame(sample_data(atlas), check.names = FALSE)

atlas_bmi <- ifelse(
  atlas_meta$bmi_group == "lean", "lean",
  ifelse(
    atlas_meta$bmi_group %in% c(
      "overweight", "obese", "severeobese", "morbidobese"
    ),
    "overweight_or_above",
    NA_character_
  )
)
atlas_bmi <- factor(atlas_bmi, levels = c("lean", "overweight_or_above"))
names(atlas_bmi) <- rownames(atlas_meta)

atlas_sex <- factor(
  as.character(atlas_meta$sex),
  levels = c("female", "male")
)
names(atlas_sex) <- rownames(atlas_meta)

for (contrast in c("BMI", "Sex")) {
  for (metric in c("Observed", "Shannon", "Simpson", "Bray", "Aitchison")) {
    family <- if (metric %in% c("Observed", "Shannon", "Simpson")) {
      "alpha"
    } else {
      "beta"
    }
    add_claim(
      paste0("ATLAS_", contrast, "_", family, "_", metric),
      paste("Atlas baseline", contrast, "groups differ for", metric),
      "ATLAS_AGG",
      "atlas1006",
      family,
      metric,
      contrast
    )
  }
}
atlas_total_diff <- vapply(
  atlas_counts,
  function(current) max(abs(rowSums(current) - rowSums(atlas_counts$Genus))),
  numeric(1)
)
add_reconstruction(
  "ATLAS_AGG", "atlas1006", "Phylum", "sample_total_difference",
  atlas_total_diff[["Phylum"]], 0, "stable", "HITChip rank aggregation"
)
add_reconstruction(
  "ATLAS_AGG", "atlas1006", "Family", "sample_total_difference",
  atlas_total_diff[["Family"]], 0, "stable", "HITChip rank aggregation"
)
add_reconstruction(
  "ATLAS_AGG", "atlas1006", "Genus", "sample_total_difference",
  0, 0, "stable", "Reference HITChip genus layer"
)
atlas_alpha_specs <- lapply(names(atlas_counts), function(pipeline) {
  list(
    pipeline = pipeline,
    counts = atlas_counts[[pipeline]],
    mode = "proportion",
    depth = NA_real_
  )
})
atlas_beta_specs <- lapply(names(atlas_counts), function(pipeline) {
  list(pipeline = pipeline, counts = atlas_counts[[pipeline]])
})

bmi_all <- names(atlas_bmi)[!is.na(atlas_bmi)]
bmi_obese_contrast <- names(atlas_bmi)[
  !is.na(atlas_bmi) &
    (
      atlas_bmi == "lean" |
        atlas_meta$bmi_group %in% c("obese", "severeobese", "morbidobese")
    )
]
bmi_groups <- function(ids) {
  values <- as.character(atlas_bmi[ids])
  values[
    atlas_meta[ids, "bmi_group"] %in%
      c("obese", "severeobese", "morbidobese")
  ] <- "overweight_or_above"
  factor(values, levels = c("lean", "overweight_or_above"))
}
evaluate_grid(
  claim_base = "ATLAS_BMI",
  domain = "HITChip",
  contrast = "BMI",
  sample_set = "baseline_all883",
  sample_ids = bmi_all,
  groups = bmi_groups(bmi_all),
  alpha_specs = atlas_alpha_specs,
  beta_specs = atlas_beta_specs,
  source = "atlas1006 via microbiome",
  permutations = MAIN_PERMUTATIONS,
  seed = SEED
)
evaluate_grid(
  claim_base = "ATLAS_BMI",
  domain = "HITChip",
  contrast = "BMI",
  sample_set = "lean_vs_obese729",
  sample_ids = bmi_obese_contrast,
  groups = bmi_groups(bmi_obese_contrast),
  alpha_specs = atlas_alpha_specs,
  beta_specs = atlas_beta_specs,
  source = "atlas1006 via microbiome",
  permutations = MAIN_PERMUTATIONS,
  seed = SEED
)

sex_all <- names(atlas_sex)[!is.na(atlas_sex)]
set.seed(SEED)
sex_balanced_ids <- unlist(lapply(
  split(sex_all, atlas_sex[sex_all]),
  function(ids) sample(ids, min(table(atlas_sex[sex_all])), replace = FALSE)
))
evaluate_grid(
  claim_base = "ATLAS_Sex",
  domain = "HITChip",
  contrast = "Sex",
  sample_set = "baseline_all969",
  sample_ids = sex_all,
  groups = atlas_sex[sex_all],
  alpha_specs = atlas_alpha_specs,
  beta_specs = atlas_beta_specs,
  source = "atlas1006 via microbiome",
  permutations = MAIN_PERMUTATIONS,
  seed = SEED
)
evaluate_grid(
  claim_base = "ATLAS_Sex",
  domain = "HITChip",
  contrast = "Sex",
  sample_set = "balanced896",
  sample_ids = sex_balanced_ids,
  groups = atlas_sex[sex_balanced_ids],
  alpha_specs = atlas_alpha_specs,
  beta_specs = atlas_beta_specs,
  source = "atlas1006 via microbiome",
  permutations = MAIN_PERMUTATIONS,
  seed = SEED
)
add_manifest(
  "atlas1006", "microbiome", "Tipping elements of the human intestinal ecosystem",
  "Lahti et al. 2014 Nature Communications 5:4344",
  "10.1038/ncomms5344", "HITChip genus/family/phylum profiles", 1006,
  "BMI and sex; baseline time 0 only"
)

# Main outputs -------------------------------------------------------------

claims_main <- do.call(rbind, claims)
endpoints_main <- do.call(rbind, endpoints)
reconstructions_main <- do.call(rbind, reconstructions)
write_table(claims_main, file.path(main_dir, "claims.csv"))
write_table(endpoints_main, file.path(main_dir, "endpoints.csv"))
write_table(reconstructions_main, file.path(main_dir, "reconstruction.csv"))
write_table(do.call(rbind, manifest), file.path(output_dir, "dataset_manifest.csv"))

cat(
  "Main endpoint rows:", nrow(endpoints_main),
  "claims:", nrow(claims_main), "\n"
)

# Label-permutation negative controls -------------------------------------

claims <- list()
endpoints <- list()
reconstructions <- list()

add_permutation_claims <- function(
    claim_base, dataset, family, metric, permutation_id) {
  for (current_metric in metric) {
    add_claim(
      paste0(claim_base, "_", family, "_", current_metric),
      paste(
        "Permuted-label control for", dataset, family, current_metric,
        "permutation", permutation_id
      ),
      paste0(toupper(dataset), "_PERM"),
      dataset,
      family,
      current_metric,
      "permuted_labels",
      permutation_id = permutation_id
    )
  }
}

run_null_grid <- function(
    dataset,
    prefix,
    domain,
    contrast,
    sample_sets,
    group_lookup,
    alpha_specs,
    beta_specs,
    source,
    reconstruction_id) {
  cached_by_sample_set <- lapply(
    sample_sets,
    function(sample_ids) {
      precompute_grid(
        sample_ids = sample_ids,
        alpha_specs = alpha_specs,
        beta_specs = beta_specs,
        seed = SEED
      )
    }
  )
  for (permutation_id in seq_len(LABEL_PERMUTATIONS)) {
    set.seed(SEED + permutation_id)
    claim_base <- sprintf("PERM_%s_%03d", prefix, permutation_id)
    add_permutation_claims(
      claim_base,
      dataset,
      family = "alpha",
      metric = c("Observed", "Shannon", "Simpson"),
      permutation_id = permutation_id
    )
    add_permutation_claims(
      claim_base,
      dataset,
      family = "beta",
      metric = c("Bray", "Aitchison"),
      permutation_id = permutation_id
    )
    for (sample_set in names(sample_sets)) {
      sample_ids <- sample_sets[[sample_set]]
      original_groups <- factor(group_lookup[sample_ids])
      permuted_groups <- original_groups[sample(length(original_groups))]
      names(permuted_groups) <- sample_ids
      evaluate_precomputed(
        claim_base = claim_base,
        domain = domain,
        contrast = contrast,
        sample_set = sample_set,
        sample_ids = sample_ids,
        groups = permuted_groups,
        cached = cached_by_sample_set[[sample_set]],
        source = paste0(source, " label permutation ", permutation_id),
        permutations = NULL_PERMUTATIONS
      )
    }
  }
  add_reconstruction(
    reconstruction_id,
    dataset,
    "permutation_control",
    "data_layer_unchanged",
    0,
    0,
    if (dataset == "soilrep") "partial" else "stable",
    "Only group labels were permuted; data-layer totals were unchanged."
  )
}

run_null_grid(
  dataset = "GlobalPatterns",
  prefix = "GP_SampleType",
  domain = "16S",
  contrast = "SampleType",
  sample_sets = list(
    all26 = rownames(gp_meta),
    environmental23 = rownames(gp_meta)[gp_meta$SampleType != "Mock"]
  ),
  group_lookup = setNames(gp_meta$SampleType, rownames(gp_meta)),
  alpha_specs = gp_alpha_specs,
  beta_specs = gp_beta_specs,
  source = "GlobalPatterns via phyloseq",
  reconstruction_id = "GLOBALPATTERNS_PERM"
)

run_null_grid(
  dataset = "enterotype",
  prefix = "EN_SeqTech",
  domain = "genus_profile",
  contrast = "SeqTech",
  sample_sets = list(
    all280 = rownames(en_meta),
    stratified123 = en_balanced
  ),
  group_lookup = setNames(en_meta$SeqTech, rownames(en_meta)),
  alpha_specs = en_alpha_specs,
  beta_specs = en_beta_specs,
  source = "enterotype via phyloseq",
  reconstruction_id = "ENTEROTYPE_PERM"
)

run_null_grid(
  dataset = "soilrep",
  prefix = "SOIL_Warmed",
  domain = "16S",
  contrast = "Warmed",
  sample_sets = soil_sample_sets$Warmed,
  group_lookup = setNames(soil_meta$Warmed, rownames(soil_meta)),
  alpha_specs = soil_alpha_specs,
  beta_specs = soil_beta_specs,
  source = "soilrep via phyloseq",
  reconstruction_id = "SOILREP_PERM"
)

run_null_grid(
  dataset = "atlas1006",
  prefix = "ATLAS_BMI",
  domain = "HITChip",
  contrast = "BMI",
  sample_sets = list(
    baseline_all883 = bmi_all,
    lean_vs_obese729 = bmi_obese_contrast
  ),
  group_lookup = setNames(as.character(atlas_bmi), names(atlas_bmi)),
  alpha_specs = atlas_alpha_specs,
  beta_specs = atlas_beta_specs,
  source = "atlas1006 via microbiome",
  reconstruction_id = "ATLAS1006_PERM"
)

claims_perm <- do.call(rbind, claims)
endpoints_perm <- do.call(rbind, endpoints)
reconstructions_perm <- do.call(rbind, reconstructions)
write_table(claims_perm, file.path(perm_dir, "claims.csv"))
write_table(endpoints_perm, file.path(perm_dir, "endpoints.csv"))
write_table(reconstructions_perm, file.path(perm_dir, "reconstruction.csv"))

cat(
  "Permutation endpoint rows:", nrow(endpoints_perm),
  "claims:", nrow(claims_perm), "\n"
)
