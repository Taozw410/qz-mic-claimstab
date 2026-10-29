options(stringsAsFactors = FALSE)
suppressPackageStartupMessages({
  library(phyloseq)
  library(ALDEx2)
  library(ANCOMBC)
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

group_levels <- c("Natural", "As", "AFP", "AEFP", "BP")
contrast_groups <- c("As", "AFP", "AEFP", "BP")
pipelines <- c("original_phylum", "current_asv_phylum")
domains <- c("16S", "ITS")
prevalence_fraction <- 0.10
minimum_prevalence <- ceiling(prevalence_fraction * 15)
minimum_total <- 10

rbind_fill <- function(frames) {
  columns <- unique(unlist(lapply(frames, names), use.names = FALSE))
  frames <- lapply(frames, function(frame) {
    missing <- setdiff(columns, names(frame))
    for (column in missing) frame[[column]] <- NA
    frame[, columns, drop = FALSE]
  })
  do.call(rbind, frames)
}

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
samples <- samples[samples$Primary5, , drop = FALSE]
samples$Composition <- factor(samples$Composition, levels = group_levels)
rownames(samples) <- samples$Sample
if (nrow(samples) != 15 || any(table(samples$Composition) != 3)) {
  stop("Expected 15 primary samples, three per group")
}

read_count_matrix <- function(pipeline, domain) {
  filename <- if (pipeline == "original_phylum") {
    paste0("original_phylum_counts_", domain, ".csv")
  } else {
    paste0("current_asv_phylum_counts_", domain, ".csv")
  }
  table <- read_input(filename)
  matrix <- as.matrix(table[, -1, drop = FALSE])
  rownames(matrix) <- table[[1]]
  matrix <- matrix[samples$Sample, , drop = FALSE]
  feature_counts <- t(matrix)
  storage.mode(feature_counts) <- "numeric"
  prevalence <- rowSums(feature_counts > 0)
  feature_counts <- feature_counts[
    prevalence >= minimum_prevalence & rowSums(feature_counts) >= minimum_total,
    ,
    drop = FALSE
  ]
  feature_counts
}

ALDEx_rows <- list()
ANCOM_rows <- list()
summary_rows <- list()
for (pipeline in pipelines) {
  for (domain in domains) {
    message("Phylum DA: ", pipeline, " / ", domain)
    counts <- read_count_matrix(pipeline, domain)
    conditions <- as.character(samples$Composition)

    for (group in contrast_groups) {
      selected <- samples$Sample[samples$Composition %in% c(group, "Natural")]
      labels <- as.character(
        samples$Composition[match(selected, samples$Sample)]
      )
      result <- aldex(
        counts[, selected, drop = FALSE],
        labels,
        mc.samples = 256,
        test = "t",
        effect = TRUE,
        denom = "all",
        verbose = FALSE
      )
      result$Taxon <- rownames(result)
      result$Pipeline <- pipeline
      result$Domain <- domain
      result$Contrast <- paste0(group, " vs Natural")
      result$Significant <- result$we.eBH < 0.05 & abs(result$effect) > 1
      ALDEx_rows[[length(ALDEx_rows) + 1]] <- result
    }

    ps <- phyloseq(
      otu_table(counts, taxa_are_rows = TRUE),
      sample_data(samples)
    )
    ancom <- tryCatch(
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
        writeLines(
          conditionMessage(error),
          file.path(
            output_dir,
            paste0("ANCOMBC2_ERROR_", pipeline, "_", domain, ".txt")
          )
        )
        NULL
      }
    )
    if (!is.null(ancom)) {
      raw <- ancom$res
      raw$Pipeline <- pipeline
      raw$Domain <- domain
      ANCOM_rows[[length(ANCOM_rows) + 1]] <- raw
    }
  }
}

aldex_all <- rbind_fill(ALDEx_rows)
write.csv(
  aldex_all,
  file.path(output_dir, "ALDEx2_phylum_pairwise.csv"),
  row.names = FALSE
)

ancom_all <- rbind_fill(ANCOM_rows)
write.csv(
  ancom_all,
  file.path(output_dir, "ANCOMBC2_phylum_pairwise.csv"),
  row.names = FALSE
)

hit_rows <- list()
for (pipeline in pipelines) {
  for (domain in domains) {
    for (group in contrast_groups) {
      contrast <- paste0(group, " vs Natural")
      aldex_group <- aldex_all[
        aldex_all$Pipeline == pipeline &
          aldex_all$Domain == domain &
          aldex_all$Contrast == contrast,
        ,
        drop = FALSE
      ]
      ancom_group <- ancom_all[
        ancom_all$Pipeline == pipeline & ancom_all$Domain == domain,
        c(
          "taxon",
          paste0("lfc_Composition", group),
          paste0("q_Composition", group),
          paste0("passed_ss_Composition", group),
          paste0("diff_robust_Composition", group)
        ),
        drop = FALSE
      ]
      names(ancom_group) <- c(
        "Taxon",
        "ANCOMBC2LogFoldChange",
        "ANCOMBC2Q",
        "ANCOMBC2PassedSensitivity",
        "ANCOMBC2Significant"
      )
      merged <- merge(
        aldex_group,
        ancom_group,
        by = "Taxon",
        all = TRUE
      )
      merged$Pipeline <- pipeline
      merged$Domain <- domain
      merged$Contrast <- contrast
      merged$ALDEx2Significant <- merged$Significant
      merged$ALDEx2Significant[is.na(merged$ALDEx2Significant)] <- FALSE
      merged$ANCOMBC2Significant[is.na(merged$ANCOMBC2Significant)] <- FALSE
      merged$ConsensusSignificant <-
        merged$ALDEx2Significant & merged$ANCOMBC2Significant
      hit_rows[[length(hit_rows) + 1]] <- merged
      summary_rows[[length(summary_rows) + 1]] <- data.frame(
        Pipeline = pipeline,
        Domain = domain,
        Contrast = contrast,
        FeaturesTested = nrow(merged),
        ALDEx2Hits = sum(merged$ALDEx2Significant),
        ANCOMBC2Hits = sum(merged$ANCOMBC2Significant),
        ConsensusHits = sum(merged$ConsensusSignificant)
      )
    }
  }
}

hits <- rbind_fill(hit_rows)
write.csv(
  hits,
  file.path(output_dir, "phylum_DA_candidates.csv"),
  row.names = FALSE
)
write.csv(
  do.call(rbind, summary_rows),
  file.path(output_dir, "phylum_DA_summary.csv"),
  row.names = FALSE
)

parameters <- data.frame(
  Parameter = c(
    "RandomSeed", "PrimarySamples", "PrevalenceFraction",
    "MinimumPrevalenceSamples", "MinimumTotalCount", "ALDExMC",
    "ALDExTest", "ALDExEffectThreshold", "ANCOMBC2Adjustment",
    "ANCOMBC2StructuralZero", "ANCOMBC2PseudoSensitivity"
  ),
  Value = c(
    seed, 15, prevalence_fraction, minimum_prevalence, minimum_total,
    256, "Welch t", 1, "BH", TRUE, TRUE
  )
)
write.csv(
  parameters,
  file.path(output_dir, "analysis_parameters.csv"),
  row.names = FALSE
)
writeLines(
  "Phylum-level differential-abundance sensitivity completed.",
  file.path(output_dir, "COMPLETE.txt")
)
