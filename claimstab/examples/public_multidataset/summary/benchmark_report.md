# Multi-dataset claim-stability benchmark

This report is generated from public microbiome datasets distributed
with the `phyloseq` and `microbiome` R packages. It evaluates
endpoint-specific stability; it does not claim to rediscover a new
microbial ecological mechanism.

## Datasets

| dataset | citation | doi | platform | samples_used | contrast |
| --- | --- | --- | --- | --- | --- |
| GlobalPatterns | Caporaso et al. 2011 PNAS 108:4516-4522 | 10.1073/pnas.1000080107 | Illumina 16S | 26 | SampleType; Mock_vs_environment |
| enterotype | Arumugam et al. 2011 Nature 473:174-180 | 10.1038/nature09944 | mixed sequencing genus profiles | 280 | SeqTech; all samples vs balanced 41 per technology |
| soilrep | Zhou et al. 2011 ISME Journal 5:1303-1313 | 10.1038/ismej.2011.11 | 454 16S | 24 | Warmed and Clipped; technical replicates aggregated to 24 communities |
| atlas1006 | Lahti et al. 2014 Nature Communications 5:4344 | 10.1038/ncomms5344 | HITChip genus/family/phylum profiles | 1006 | BMI and sex; baseline time 0 only |

## Framework comparison on observed labels

| dataset | claims | majority_supported | claimstab_supported | majority_only |
| --- | --- | --- | --- | --- |
| GlobalPatterns | 7 | 7 | 5 | 2 |
| atlas1006 | 10 | 5 | 3 | 2 |
| enterotype | 5 | 5 | 4 | 1 |
| soilrep | 10 | 0 | 0 | 0 |

`majority_only` counts claims that an unweighted majority-of-specifications
rule calls supported while the four-component claimstab grade does not.

## Permuted-label negative controls

| dataset | n_permuted_claims | n_dataset_permutation_combinations | majority_support_count_under_null | strict_support_count_under_null | claimstab_support_count_under_null | majority_support_rate_under_null | strict_support_rate_under_null | claimstab_support_rate_under_null | absolute_reduction_vs_majority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GlobalPatterns | 100 | 20 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| atlas1006 | 100 | 20 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| enterotype | 100 | 20 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |
| soilrep | 100 | 20 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 |

Each dataset was evaluated under 20 outer label permutations. Five
claim evaluations were generated per dataset-permutation, yielding 400
nested evaluations within 80 dataset-permutation combinations. These
evaluations are not independent Bernoulli trials.

## Endpoint-type summary

| dataset | family | metric | n_claims | claimstab_support_rate | majority_support_rate | median_p_max | median_effect_retention |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GlobalPatterns | alpha | Observed | 1 | 1.000 | 1.000 | 0.003 | 0.966 |
| GlobalPatterns | alpha | Shannon | 1 | 1.000 | 1.000 | 0.007 | 0.807 |
| GlobalPatterns | alpha | Simpson | 1 | 1.000 | 1.000 | 0.012 | 0.790 |
| GlobalPatterns | beta | Aitchison | 2 | 0.500 | 1.000 | 0.051 | 0.637 |
| GlobalPatterns | beta | Bray | 2 | 0.500 | 1.000 | 0.048 | 0.607 |
| atlas1006 | alpha | Observed | 2 | 0.000 | 0.500 | 0.579 | 0.031 |
| atlas1006 | alpha | Shannon | 2 | 0.000 | 0.500 | 0.514 | 0.025 |
| atlas1006 | alpha | Simpson | 2 | 0.500 | 0.500 | 0.456 | 0.099 |
| atlas1006 | beta | Aitchison | 2 | 0.500 | 0.500 | 0.326 | 0.096 |
| atlas1006 | beta | Bray | 2 | 0.500 | 0.500 | 0.310 | 0.125 |
| enterotype | alpha | Observed | 1 | 1.000 | 1.000 | 0.000 | 0.999 |
| enterotype | alpha | Shannon | 1 | 1.000 | 1.000 | 0.000 | 0.577 |
| enterotype | alpha | Simpson | 1 | 0.000 | 1.000 | 0.140 | 0.067 |
| enterotype | beta | Aitchison | 1 | 1.000 | 1.000 | 0.001 | 0.330 |
| enterotype | beta | Bray | 1 | 1.000 | 1.000 | 0.001 | 0.442 |
| soilrep | alpha | Observed | 2 | 0.000 | 0.000 | 0.952 | 0.002 |
| soilrep | alpha | Shannon | 2 | 0.000 | 0.000 | 0.924 | 0.005 |
| soilrep | alpha | Simpson | 2 | 0.000 | 0.000 | 0.909 | 0.007 |
| soilrep | beta | Aitchison | 2 | 0.000 | 0.000 | 0.980 | 0.406 |
| soilrep | beta | Bray | 2 | 0.000 | 0.000 | 0.987 | 0.444 |

## Empirical conditions

The condition table is descriptive. It identifies where support is
observed in this benchmark and is not a universal causal law.

| dimension | level | n_claims | claimstab_supported | claimstab_support_rate | majority_support_rate |
| --- | --- | --- | --- | --- | --- |
| signal_margin | max_p_0.01_0.05 | 1 | 1 | 1.000 | 1.000 |
| signal_margin | max_p_0.05_0.10 | 1 | 0 | 0.000 | 1.000 |
| signal_margin | max_p_0.10_0.20 | 3 | 0 | 0.000 | 1.000 |
| signal_margin | max_p_ge_0.20 | 16 | 0 | 0.000 | 0.062 |
| signal_margin | max_p_lt_0.01 | 11 | 11 | 1.000 | 1.000 |

### Pipeline and sample-set conditions

| dataset | family | metric | pipeline_type | sample_set_class | n_testable | significant_rate | median_p | median_abs_effect |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GlobalPatterns | alpha | Observed | genus_aggregation | full_sample_set | 1 | 1.000 | 0.000 | 0.897 |
| GlobalPatterns | alpha | Observed | genus_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.000 | 0.883 |
| GlobalPatterns | alpha | Observed | otu_full | full_sample_set | 1 | 1.000 | 0.000 | 0.914 |
| GlobalPatterns | alpha | Observed | otu_full | subgroup_or_sensitivity_set | 1 | 1.000 | 0.000 | 0.905 |
| GlobalPatterns | alpha | Observed | phylum_aggregation | full_sample_set | 1 | 1.000 | 0.001 | 0.900 |
| GlobalPatterns | alpha | Observed | phylum_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.003 | 0.893 |
| GlobalPatterns | alpha | Shannon | genus_aggregation | full_sample_set | 1 | 1.000 | 0.000 | 0.918 |
| GlobalPatterns | alpha | Shannon | genus_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.001 | 0.901 |
| GlobalPatterns | alpha | Shannon | otu_full | full_sample_set | 1 | 1.000 | 0.000 | 0.907 |
| GlobalPatterns | alpha | Shannon | otu_full | subgroup_or_sensitivity_set | 1 | 1.000 | 0.000 | 0.905 |
| GlobalPatterns | alpha | Shannon | phylum_aggregation | full_sample_set | 1 | 1.000 | 0.007 | 0.741 |
| GlobalPatterns | alpha | Shannon | phylum_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.007 | 0.741 |
| GlobalPatterns | alpha | Simpson | genus_aggregation | full_sample_set | 1 | 1.000 | 0.000 | 0.909 |
| GlobalPatterns | alpha | Simpson | genus_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.000 | 0.888 |
| GlobalPatterns | alpha | Simpson | otu_full | full_sample_set | 1 | 1.000 | 0.000 | 0.887 |
| GlobalPatterns | alpha | Simpson | otu_full | subgroup_or_sensitivity_set | 1 | 1.000 | 0.007 | 0.883 |
| GlobalPatterns | alpha | Simpson | phylum_aggregation | full_sample_set | 1 | 1.000 | 0.001 | 0.734 |
| GlobalPatterns | alpha | Simpson | phylum_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.012 | 0.719 |
| GlobalPatterns | beta | Aitchison | genus_aggregation | full_sample_set | 2 | 1.000 | 0.003 | 0.469 |
| GlobalPatterns | beta | Aitchison | genus_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.001 | 0.708 |
| GlobalPatterns | beta | Aitchison | otu_full | full_sample_set | 2 | 1.000 | 0.015 | 0.392 |
| GlobalPatterns | beta | Aitchison | otu_full | subgroup_or_sensitivity_set | 1 | 1.000 | 0.001 | 0.685 |
| GlobalPatterns | beta | Aitchison | phylum_aggregation | full_sample_set | 2 | 0.500 | 0.051 | 0.434 |
| GlobalPatterns | beta | Aitchison | phylum_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.001 | 0.779 |
| GlobalPatterns | beta | Bray | genus_aggregation | full_sample_set | 2 | 1.000 | 0.001 | 0.508 |
| GlobalPatterns | beta | Bray | genus_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.001 | 0.750 |
| GlobalPatterns | beta | Bray | otu_full | full_sample_set | 2 | 1.000 | 0.001 | 0.425 |
| GlobalPatterns | beta | Bray | otu_full | subgroup_or_sensitivity_set | 1 | 1.000 | 0.001 | 0.695 |
| GlobalPatterns | beta | Bray | phylum_aggregation | full_sample_set | 2 | 0.500 | 0.048 | 0.437 |
| GlobalPatterns | beta | Bray | phylum_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.001 | 0.783 |
| atlas1006 | alpha | Observed | family_aggregation | balanced_subset | 1 | 0.000 | 0.621 | 0.000 |
| atlas1006 | alpha | Observed | family_aggregation | full_sample_set | 2 | 0.500 | 0.087 | 0.011 |
| atlas1006 | alpha | Observed | family_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.000 | 0.028 |
| atlas1006 | alpha | Observed | genus_aggregation | balanced_subset | 1 | 0.000 | 0.423 | 0.001 |
| atlas1006 | alpha | Observed | genus_aggregation | full_sample_set | 2 | 0.500 | 0.137 | 0.006 |
| atlas1006 | alpha | Observed | genus_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.000 | 0.019 |
| atlas1006 | alpha | Observed | phylum_aggregation | balanced_subset | 1 | 0.000 | 0.892 | 0.000 |
| atlas1006 | alpha | Observed | phylum_aggregation | full_sample_set | 2 | 0.000 | 0.245 | 0.001 |
| atlas1006 | alpha | Observed | phylum_aggregation | subgroup_or_sensitivity_set | 1 | 0.000 | 0.216 | 0.002 |
| atlas1006 | alpha | Shannon | family_aggregation | balanced_subset | 1 | 0.000 | 0.914 | 0.000 |
| atlas1006 | alpha | Shannon | family_aggregation | full_sample_set | 2 | 0.500 | 0.373 | 0.022 |
| atlas1006 | alpha | Shannon | family_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.000 | 0.060 |
| atlas1006 | alpha | Shannon | genus_aggregation | balanced_subset | 1 | 1.000 | 0.034 | 0.005 |
| atlas1006 | alpha | Shannon | genus_aggregation | full_sample_set | 2 | 1.000 | 0.009 | 0.019 |
| atlas1006 | alpha | Shannon | genus_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.000 | 0.055 |
| atlas1006 | alpha | Shannon | phylum_aggregation | balanced_subset | 1 | 0.000 | 0.458 | 0.001 |
| atlas1006 | alpha | Shannon | phylum_aggregation | full_sample_set | 2 | 0.000 | 0.183 | 0.002 |
| atlas1006 | alpha | Shannon | phylum_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.007 | 0.010 |
| atlas1006 | alpha | Simpson | family_aggregation | balanced_subset | 1 | 0.000 | 0.907 | 0.000 |
| atlas1006 | alpha | Simpson | family_aggregation | full_sample_set | 2 | 0.500 | 0.439 | 0.016 |
| atlas1006 | alpha | Simpson | family_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.000 | 0.039 |
| atlas1006 | alpha | Simpson | genus_aggregation | balanced_subset | 1 | 1.000 | 0.042 | 0.005 |
| atlas1006 | alpha | Simpson | genus_aggregation | full_sample_set | 2 | 1.000 | 0.009 | 0.017 |
| atlas1006 | alpha | Simpson | genus_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.000 | 0.046 |
| atlas1006 | alpha | Simpson | phylum_aggregation | balanced_subset | 1 | 0.000 | 0.421 | 0.001 |
| atlas1006 | alpha | Simpson | phylum_aggregation | full_sample_set | 2 | 0.500 | 0.093 | 0.005 |
| atlas1006 | alpha | Simpson | phylum_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.000 | 0.026 |
| atlas1006 | beta | Aitchison | family_aggregation | balanced_subset | 1 | 0.000 | 0.353 | 0.001 |
| atlas1006 | beta | Aitchison | family_aggregation | full_sample_set | 2 | 0.500 | 0.099 | 0.012 |
| atlas1006 | beta | Aitchison | family_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.001 | 0.050 |
| atlas1006 | beta | Aitchison | genus_aggregation | balanced_subset | 1 | 1.000 | 0.005 | 0.005 |
| atlas1006 | beta | Aitchison | genus_aggregation | full_sample_set | 2 | 1.000 | 0.001 | 0.007 |
| atlas1006 | beta | Aitchison | genus_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.001 | 0.022 |
| atlas1006 | beta | Aitchison | phylum_aggregation | balanced_subset | 1 | 0.000 | 0.651 | 0.000 |
| atlas1006 | beta | Aitchison | phylum_aggregation | full_sample_set | 2 | 0.500 | 0.168 | 0.017 |
| atlas1006 | beta | Aitchison | phylum_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.001 | 0.072 |
| atlas1006 | beta | Bray | family_aggregation | balanced_subset | 1 | 0.000 | 0.422 | 0.001 |
| atlas1006 | beta | Bray | family_aggregation | full_sample_set | 2 | 0.500 | 0.098 | 0.012 |
| atlas1006 | beta | Bray | family_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.001 | 0.048 |
| atlas1006 | beta | Bray | genus_aggregation | balanced_subset | 1 | 1.000 | 0.003 | 0.004 |
| atlas1006 | beta | Bray | genus_aggregation | full_sample_set | 2 | 1.000 | 0.002 | 0.008 |
| atlas1006 | beta | Bray | genus_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.001 | 0.026 |
| atlas1006 | beta | Bray | phylum_aggregation | balanced_subset | 1 | 0.000 | 0.620 | 0.000 |
| atlas1006 | beta | Bray | phylum_aggregation | full_sample_set | 2 | 0.500 | 0.183 | 0.017 |
| atlas1006 | beta | Bray | phylum_aggregation | subgroup_or_sensitivity_set | 1 | 1.000 | 0.001 | 0.073 |
| enterotype | alpha | Observed | genus_all | balanced_subset | 1 | 1.000 | 0.000 | 0.997 |
| enterotype | alpha | Observed | genus_all | full_sample_set | 1 | 1.000 | 0.000 | 0.998 |
| enterotype | alpha | Observed | genus_filtered | balanced_subset | 1 | 1.000 | 0.000 | 0.997 |
| enterotype | alpha | Observed | genus_filtered | full_sample_set | 1 | 1.000 | 0.000 | 0.998 |
| enterotype | alpha | Shannon | genus_all | balanced_subset | 1 | 1.000 | 0.000 | 0.132 |
| enterotype | alpha | Shannon | genus_all | full_sample_set | 1 | 1.000 | 0.000 | 0.219 |
| enterotype | alpha | Shannon | genus_filtered | balanced_subset | 1 | 1.000 | 0.000 | 0.126 |
| enterotype | alpha | Shannon | genus_filtered | full_sample_set | 1 | 1.000 | 0.000 | 0.147 |
| enterotype | alpha | Simpson | genus_all | balanced_subset | 1 | 1.000 | 0.000 | 0.166 |
| enterotype | alpha | Simpson | genus_all | full_sample_set | 1 | 1.000 | 0.000 | 0.295 |
| enterotype | alpha | Simpson | genus_filtered | balanced_subset | 1 | 0.000 | 0.140 | 0.020 |
| enterotype | alpha | Simpson | genus_filtered | full_sample_set | 1 | 1.000 | 0.042 | 0.020 |
| enterotype | beta | Aitchison | genus_all | balanced_subset | 1 | 1.000 | 0.001 | 0.528 |
| enterotype | beta | Aitchison | genus_all | full_sample_set | 1 | 1.000 | 0.001 | 0.558 |
| enterotype | beta | Aitchison | genus_filtered | balanced_subset | 1 | 1.000 | 0.001 | 0.184 |
| enterotype | beta | Aitchison | genus_filtered | full_sample_set | 1 | 1.000 | 0.001 | 0.202 |
| enterotype | beta | Bray | genus_all | balanced_subset | 1 | 1.000 | 0.001 | 0.516 |
| enterotype | beta | Bray | genus_all | full_sample_set | 1 | 1.000 | 0.001 | 0.532 |
| enterotype | beta | Bray | genus_filtered | balanced_subset | 1 | 1.000 | 0.001 | 0.235 |
| enterotype | beta | Bray | genus_filtered | full_sample_set | 1 | 1.000 | 0.001 | 0.259 |
| soilrep | alpha | Observed | otu_rarefied_500 | full_sample_set | 2 | 0.000 | 0.274 | 0.055 |
| soilrep | alpha | Observed | otu_rarefied_500 | subgroup_or_sensitivity_set | 4 | 0.000 | 0.562 | 0.049 |
| soilrep | alpha | Observed | otu_rarefied_high | full_sample_set | 2 | 0.000 | 0.538 | 0.057 |
| soilrep | alpha | Observed | otu_rarefied_high | subgroup_or_sensitivity_set | 4 | 0.000 | 0.501 | 0.054 |
| soilrep | alpha | Shannon | otu_rarefied_500 | full_sample_set | 2 | 0.000 | 0.346 | 0.041 |
| soilrep | alpha | Shannon | otu_rarefied_500 | subgroup_or_sensitivity_set | 4 | 0.000 | 0.581 | 0.045 |
| soilrep | alpha | Shannon | otu_rarefied_high | full_sample_set | 2 | 0.000 | 0.574 | 0.040 |
| soilrep | alpha | Shannon | otu_rarefied_high | subgroup_or_sensitivity_set | 4 | 0.000 | 0.418 | 0.068 |
| soilrep | alpha | Simpson | otu_rarefied_500 | full_sample_set | 2 | 0.000 | 0.627 | 0.015 |
| soilrep | alpha | Simpson | otu_rarefied_500 | subgroup_or_sensitivity_set | 4 | 0.000 | 0.708 | 0.020 |
| soilrep | alpha | Simpson | otu_rarefied_high | full_sample_set | 2 | 0.000 | 0.546 | 0.024 |
| soilrep | alpha | Simpson | otu_rarefied_high | subgroup_or_sensitivity_set | 4 | 0.000 | 0.425 | 0.087 |
| soilrep | beta | Aitchison | otu_full | full_sample_set | 2 | 0.000 | 0.974 | 0.032 |
| soilrep | beta | Aitchison | otu_full | subgroup_or_sensitivity_set | 4 | 0.000 | 0.857 | 0.071 |
| soilrep | beta | Aitchison | otu_prevalence_10pct | full_sample_set | 2 | 0.000 | 0.979 | 0.030 |
| soilrep | beta | Aitchison | otu_prevalence_10pct | subgroup_or_sensitivity_set | 4 | 0.000 | 0.879 | 0.066 |
| soilrep | beta | Bray | otu_full | full_sample_set | 2 | 0.000 | 0.963 | 0.035 |
| soilrep | beta | Bray | otu_full | subgroup_or_sensitivity_set | 4 | 0.000 | 0.971 | 0.071 |
| soilrep | beta | Bray | otu_prevalence_10pct | full_sample_set | 2 | 0.000 | 0.961 | 0.032 |
| soilrep | beta | Bray | otu_prevalence_10pct | subgroup_or_sensitivity_set | 4 | 0.000 | 0.969 | 0.066 |
