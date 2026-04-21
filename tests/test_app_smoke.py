"""Smoke tests that wire the Dash app together without spinning up a browser."""

from __future__ import annotations

import plotly.graph_objects as go

from app.components.prevalence_chart import build_prevalence_figure
from app.components.sunburst import build_sunburst_figure
from app.data_loader import active_gene_list, iter_pathway_genes
from app.main import create_app


def test_build_sunburst(toy_bundle):
    fig = build_sunburst_figure(toy_bundle.subtypes, toy_bundle.samples)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    ids = list(fig.data[0].ids)
    assert "HM" in ids and "BT" in ids and "ST" in ids


def test_build_prevalence_for_each_root(toy_bundle):
    for root in ("HM", "BT", "ST"):
        cohort = toy_bundle.cohort_samples(root)
        gl = active_gene_list(toy_bundle.gene_pathways, root, "curated")
        pg = list(iter_pathway_genes(gl))
        fig = build_prevalence_figure(cohort, toy_bundle.variants, pg)
        assert isinstance(fig, go.Figure)
        # At minimum the prevalence bar (row 3) should be present.
        names = [t.name for t in fig.data]
        assert "Prevalence" in names
        # Origin traces should be present.
        assert "Somatic" in names or "Germline" in names


def test_create_app(toy_bundle):
    app = create_app(toy_bundle)
    assert app.layout is not None
    # Dash stores callbacks on the app.callback_map dict.
    assert app.callback_map, "no callbacks registered"
    # The key callback outputs should be registered.
    output_ids = set()
    for spec in app.callback_map.values():
        outputs = spec.get("output")
        if isinstance(outputs, (list, tuple)):
            for o in outputs:
                output_ids.add(o.component_id)
        elif outputs is not None:
            output_ids.add(outputs.component_id)
    assert "prevalence-chart" in output_ids
    assert "selected-subtype" in output_ids


def test_category_filter_excludes_svs(toy_bundle):
    from app.config import STRUCTURAL_VARIANT_CLASSES

    cohort = toy_bundle.cohort_samples("HM")
    gl = active_gene_list(toy_bundle.gene_pathways, "HM", "curated")
    pg = list(iter_pathway_genes(gl))

    fig = build_prevalence_figure(
        cohort,
        toy_bundle.variants,
        pg,
        show_variant_classes=[c for c in STRUCTURAL_VARIANT_CLASSES],
    )
    class_trace_names = {t.name for t in fig.data if getattr(t, "legendgroup", None) == "vclass"}
    # No point-mutation classes should appear.
    assert "MISSENSE" not in class_trace_names
    assert "FRAMESHIFT" not in class_trace_names
