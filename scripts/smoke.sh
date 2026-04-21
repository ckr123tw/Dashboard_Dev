#!/usr/bin/env bash
set -eu
MF="$HOME/miniforge3"
# shellcheck disable=SC1091
source "$MF/etc/profile.d/conda.sh"
conda activate pecan-dash
cd /mnt/c/DinMA/Projects/Dashboard_Dev
python - <<'PY'
from app.data_loader import load_data
from app.config import CONFIG
from app.prevalence import cohort_stats, prevalence_per_gene, variant_class_breakdown
from app.components.prevalence_chart import build_prevalence_figure
from app.components.sunburst import build_sunburst_figure
from app.data_loader import active_gene_list, iter_pathway_genes
from app.main import create_app

bundle = load_data(CONFIG.data_dir)
print("OK load:", len(bundle.subtypes), "subtypes,", len(bundle.samples), "samples,",
      len(bundle.variants), "variants")

cohort = bundle.cohort_samples("HM")
print("HM cohort:", cohort_stats(cohort))

gl = active_gene_list(bundle.gene_pathways, "HM", "curated")
pg = list(iter_pathway_genes(gl))
print("pathway_genes:", pg)

prev = prevalence_per_gene(cohort, bundle.variants, [g for _, gs in pg for g in gs])
print("prevalence head:")
print(prev.head())

fig = build_prevalence_figure(cohort, bundle.variants, pg)
print("prev fig traces:", len(fig.data))

sfig = build_sunburst_figure(bundle.subtypes, bundle.samples)
print("sunburst traces:", len(sfig.data))

app = create_app(bundle)
print("Dash app created:", type(app).__name__, "version", app.__class__.__module__)
PY
