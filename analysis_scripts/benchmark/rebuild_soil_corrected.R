options(stringsAsFactors = FALSE)
suppressPackageStartupMessages({
  library(phyloseq)
  library(vegan)
})

source_lines <- readLines("build_public_multiverse.R", warn = FALSE)
cut_index <- grep("^# GlobalPatterns", source_lines)[1] - 1
eval(parse(text = source_lines[seq_len(cut_index)]), envir = .GlobalEnv)

safe_alpha_test <- function(values, groups) {
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
}

output_dir <- "soilfix"
main_dir <- file.path(output_dir, "main")
perm_dir <- file.path(output_dir, "permutation")
dir.create(main_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(perm_dir, recursive = TRUE, showWarnings = FALSE)

claims <- list()
endpoints <- list()
reconstructions <- list()

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
      source = "soilrep via phyloseq; 24 aggregated communities",
      permutations = MAIN_PERMUTATIONS
    )
  }
}

write_table(do.call(rbind, claims), file.path(main_dir, "claims.csv"))
write_table(do.call(rbind, endpoints), file.path(main_dir, "endpoints.csv"))
write_table(
  do.call(rbind, reconstructions),
  file.path(main_dir, "reconstruction.csv")
)

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
    "partial",
    "Only group labels were permuted; data-layer totals were unchanged."
  )
}

claims <- list()
endpoints <- list()
reconstructions <- list()
run_null_grid(
  dataset = "soilrep",
  prefix = "SOIL_Warmed",
  domain = "16S",
  contrast = "Warmed",
  sample_sets = soil_sample_sets$Warmed,
  group_lookup = setNames(soil_meta$Warmed, rownames(soil_meta)),
  alpha_specs = soil_alpha_specs,
  beta_specs = soil_beta_specs,
  source = "soilrep via phyloseq; 24 aggregated communities",
  reconstruction_id = "SOILREP_PERM"
)

write_table(do.call(rbind, claims), file.path(perm_dir, "claims.csv"))
write_table(do.call(rbind, endpoints), file.path(perm_dir, "endpoints.csv"))
write_table(
  do.call(rbind, reconstructions),
  file.path(perm_dir, "reconstruction.csv")
)
