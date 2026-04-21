#!/usr/bin/env bash
# Import-time smoke check: loads the toy data, computes prevalence, builds
# both figures, and instantiates the Dash app (no network, no server).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${HERE}/_lib.sh"
activate_env
cd "${REPO_ROOT}"

python - <<'PY'
from app.components.prevalence_chart import build_prevalence_figure
from app.components.sunburst import build_sunburst_figure
from app.config import CONFIG
from app.data_loader import active_gene_list, iter_pathway_genes, load_data
from app.main import create_app
from app.prevalence import cohort_stats, prevalence_per_gene

bundle = load_data(CONFIG.data_dir)
print(f"load OK: {len(bundle.subtypes)} subtypes, "
      f"{len(bundle.samples)} samples, {len(bundle.variants)} variants")

cohort = bundle.cohort_samples("HM")
print(f"HM cohort: {cohort_stats(cohort)}")

gl = active_gene_list(bundle.gene_pathways, "HM", "curated")
pg = list(iter_pathway_genes(gl))
print(f"pathway_genes: {pg}")

prev = prevalence_per_gene(cohort, bundle.variants, [g for _, gs in pg for g in gs])
print("prevalence head:")
print(prev.head())

fig = build_prevalence_figure(cohort, bundle.variants, pg)
print(f"prevalence figure traces: {len(fig.data)}")
sunburst = build_sunburst_figure(bundle.subtypes, bundle.samples)
print(f"sunburst traces: {len(sunburst.data)}")

app = create_app(bundle)
print(f"Dash app created: {type(app).__name__}")
PY
