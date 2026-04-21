"""Dash app entry point."""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, ctx, html, no_update

from app.components.layout import build_layout
from app.components.prevalence_chart import build_prevalence_figure
from app.components.sunburst import build_sunburst_figure
from app.config import (
    CONFIG,
    POINT_MUTATION_CLASSES,
    STRUCTURAL_VARIANT_CLASSES,
)
from app.data_loader import (
    DataBundle,
    active_gene_list,
    iter_pathway_genes,
    load_data,
)
from app.prevalence import cohort_stats


def _root_of(bundle: DataBundle, code: str) -> str | None:
    row = bundle.subtypes.loc[bundle.subtypes["subtype_code"] == code]
    if row.empty:
        return None
    return str(row["root"].iloc[0])


def _load_bundle_from_env() -> DataBundle:
    """Dispatch to the configured data backend."""
    if CONFIG.data_backend == "delta":
        # Lazy-imported so CSV-only deployments don't need the connector installed.
        from app.databricks_loader import load_data_from_databricks

        return load_data_from_databricks(CONFIG)
    return load_data(CONFIG.data_dir)


def create_app(bundle: DataBundle | None = None) -> dash.Dash:
    bundle = bundle or _load_bundle_from_env()

    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.FLATLY],
        title="Variant Prevalence Dashboard",
        suppress_callback_exceptions=False,
    )
    app.layout = build_layout()

    # Preload sunburst (doesn't depend on callbacks).
    sunburst_fig = build_sunburst_figure(bundle.subtypes, bundle.samples)

    @app.callback(Output("sunburst", "figure"), Input("selected-subtype", "data"))
    def _render_sunburst(_selected):
        return sunburst_fig

    @app.callback(
        Output("selected-subtype", "data"),
        Input("sunburst", "clickData"),
        Input("reset-btn", "n_clicks"),
        State("selected-subtype", "data"),
        prevent_initial_call=True,
    )
    def _on_sunburst_click(click_data, _reset_clicks, current):
        triggered = ctx.triggered_id
        if triggered == "reset-btn":
            return "HM"
        if not click_data or "points" not in click_data:
            return current
        pt = click_data["points"][0]
        code = pt.get("id") or pt.get("label")
        return code or current

    @app.callback(
        Output("section-title", "children"),
        Output("selected-subtype-label", "children"),
        Output("cohort-stats", "children"),
        Input("selected-subtype", "data"),
    )
    def _update_header(selected):
        name = bundle.subtype_name(selected)
        cohort = bundle.cohort_samples(selected)
        stats = cohort_stats(cohort)
        title = f"Variant Prevalence by Pathway — {selected}"
        sel_label = html.Div(
            [
                html.Div("Selected", className="selected-caption"),
                html.Div(f"{name} ({selected})", className="selected-name"),
            ]
        )
        stats_el = html.Div(
            [
                html.Span(f"{stats.n_samples}", className="stat-num"),
                html.Span(" samples  ·  ", className="stat-sep"),
                html.Span(f"{stats.n_subjects}", className="stat-num"),
                html.Span(" subjects", className="stat-sep"),
            ]
        )
        return title, sel_label, stats_el

    @app.callback(
        Output("prevalence-chart", "figure"),
        Input("selected-subtype", "data"),
        Input("gene-list-radio", "value"),
        Input("variant-category-check", "value"),
    )
    def _update_prevalence(selected, gene_list_mode, categories):
        root = _root_of(bundle, selected) or "HM"
        gl = active_gene_list(bundle.gene_pathways, root=root, prefer=gene_list_mode)
        pathway_genes = list(iter_pathway_genes(gl))

        # Restrict variant-class set by selected categories.
        allowed: list[str] = []
        categories = categories or []
        if "point_mutation" in categories:
            allowed.extend(POINT_MUTATION_CLASSES)
        if "structural_variant" in categories:
            allowed.extend(STRUCTURAL_VARIANT_CLASSES)
        if not allowed:
            allowed = list(POINT_MUTATION_CLASSES) + list(STRUCTURAL_VARIANT_CLASSES)

        cohort = bundle.cohort_samples(selected)
        return build_prevalence_figure(
            cohort,
            bundle.variants,
            pathway_genes,
            show_variant_classes=allowed,
        )

    @app.callback(
        Output("svg-download", "data"),
        Input("export-svg-btn", "n_clicks"),
        State("prevalence-chart", "figure"),
        prevent_initial_call=True,
    )
    def _export_svg(_n, figure):
        if not figure:
            return no_update
        try:
            import plotly.graph_objects as go

            fig = go.Figure(figure)
            svg_bytes = fig.to_image(format="svg")
            return dict(content=svg_bytes.decode("utf-8"), filename="variant_prevalence.svg")
        except Exception as exc:  # kaleido may be unavailable
            return dict(
                content=(
                    "<!-- SVG export requires the 'kaleido' package. "
                    f"Error: {exc} -->"
                ),
                filename="variant_prevalence_error.svg",
            )

    return app


def main() -> None:
    """Build the Dash app and run the development server.

    Used both locally (``python -m app.main``) and by Databricks Apps,
    whose manifest specifies the same start command.
    """
    application = create_app()
    application.run(host=CONFIG.host, port=CONFIG.port, debug=CONFIG.debug)


if __name__ == "__main__":
    main()
