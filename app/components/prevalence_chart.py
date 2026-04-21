"""Variant-prevalence-by-pathway chart.

Layout mirrors the PeCan reference: three vertically stacked sub-rows sharing
the same x-axis of (pathway, gene) pairs.

    Row 1: "Variant Class Proportion"  — stacked bars summing to 1.0
    Row 2: "Variant Origin"             — somatic / germline proportion
    Row 3: "Variant Prevalence"         — single bar per gene, 0-100 %
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.config import (
    ALL_VARIANT_CLASSES,
    ORIGIN_COLORS,
    VARIANT_CLASS_COLORS,
)
from app.prevalence import (
    origin_breakdown,
    prevalence_per_gene,
    variant_class_breakdown,
)


def _gene_labels_with_pathway(pathway_genes: list[tuple[str, list[str]]]) -> tuple[list[str], list[str]]:
    """Build parallel arrays (gene_ids, displayed_labels).

    Gene IDs are suffixed per pathway so the same gene appearing in two
    pathways gets two separate bars. Displayed label is just the gene symbol;
    the pathway header is added via annotations.
    """
    ids: list[str] = []
    labels: list[str] = []
    for pathway, genes in pathway_genes:
        for g in genes:
            ids.append(f"{pathway}::{g}")
            labels.append(g)
    return ids, labels


def _pathway_segments(pathway_genes: list[tuple[str, list[str]]]) -> list[tuple[str, int, int]]:
    """Return list of (pathway_name, start_idx, end_idx_inclusive) on the x axis."""
    segments: list[tuple[str, int, int]] = []
    cursor = 0
    for pathway, genes in pathway_genes:
        if not genes:
            continue
        segments.append((pathway, cursor, cursor + len(genes) - 1))
        cursor += len(genes)
    return segments


def build_prevalence_figure(
    samples: pd.DataFrame,
    variants: pd.DataFrame,
    pathway_genes: list[tuple[str, list[str]]],
    *,
    show_variant_classes: Iterable[str] | None = None,
) -> go.Figure:
    """Assemble the three-row figure.

    Parameters
    ----------
    samples, variants : cohort-filtered frames (already narrowed to the
        selected subtype).
    pathway_genes     : ordered list of (pathway, [genes]) pairs to display.
    show_variant_classes : optional subset of classes to include. Defaults to
        ALL_VARIANT_CLASSES.
    """
    if show_variant_classes is None:
        show_variant_classes = ALL_VARIANT_CLASSES

    gene_ids, gene_labels = _gene_labels_with_pathway(pathway_genes)
    all_genes = [g for _, gs in pathway_genes for g in gs]

    cls_df = variant_class_breakdown(samples, variants, all_genes)
    org_df = origin_breakdown(samples, variants, all_genes)
    prev_df = prevalence_per_gene(samples, variants, all_genes)

    # Build index: (pathway, gene) -> x position
    x_pos: dict[tuple[str, str], int] = {}
    pos = 0
    for pathway, genes in pathway_genes:
        for g in genes:
            x_pos[(pathway, g)] = pos
            pos += 1
    n = len(gene_ids)

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.45, 0.2, 0.35],
        subplot_titles=(
            "Variant Class Proportion",
            "Variant Origin",
            "Variant Prevalence (%)",
        ),
    )

    # ---- Row 1: variant class proportion (stacked to 1.0) ----
    for vclass in show_variant_classes:
        y_vals: list[float] = [0.0] * n
        counts: list[int] = [0] * n
        for pathway, genes in pathway_genes:
            for g in genes:
                sel = cls_df[(cls_df["gene"] == g) & (cls_df["variant_class"] == vclass)]
                idx = x_pos[(pathway, g)]
                if not sel.empty:
                    y_vals[idx] = float(sel["proportion"].iloc[0])
                    counts[idx] = int(sel["count"].iloc[0])

        if all(v == 0 for v in y_vals):
            continue
        fig.add_trace(
            go.Bar(
                x=gene_ids,
                y=y_vals,
                name=vclass,
                marker_color=VARIANT_CLASS_COLORS.get(vclass, "#888"),
                customdata=[[vclass, c] for c in counts],
                hovertemplate="%{customdata[0]}<br>%{customdata[1]} variants (%{y:.1%})<extra></extra>",
                legendgroup="vclass",
                legendgrouptitle_text="Variant class",
            ),
            row=1,
            col=1,
        )

    # ---- Row 2: origin proportion ----
    for origin in ("somatic", "germline"):
        y_vals = [0.0] * n
        counts = [0] * n
        for pathway, genes in pathway_genes:
            for g in genes:
                sel = org_df[(org_df["gene"] == g) & (org_df["origin"] == origin)]
                idx = x_pos[(pathway, g)]
                if not sel.empty:
                    y_vals[idx] = float(sel["proportion"].iloc[0])
                    counts[idx] = int(sel["count"].iloc[0])
        fig.add_trace(
            go.Bar(
                x=gene_ids,
                y=y_vals,
                name=origin.capitalize(),
                marker_color=ORIGIN_COLORS[origin],
                customdata=[[origin, c] for c in counts],
                hovertemplate="%{customdata[0]}<br>%{customdata[1]} variants (%{y:.1%})<extra></extra>",
                legendgroup="origin",
                legendgrouptitle_text="Variant origin",
            ),
            row=2,
            col=1,
        )

    # ---- Row 3: prevalence (%) ----
    prev_y: list[float] = []
    prev_custom: list[list] = []
    for pathway, genes in pathway_genes:
        for g in genes:
            row = prev_df.loc[g] if g in prev_df.index else None
            if row is None:
                prev_y.append(0.0)
                prev_custom.append([0, 0])
            else:
                prev_y.append(float(row["prevalence"]) * 100)
                prev_custom.append(
                    [int(row["n_subjects_mutated"]), int(row["n_subjects_total"])]
                )

    fig.add_trace(
        go.Bar(
            x=gene_ids,
            y=prev_y,
            name="Prevalence",
            marker_color="#2c3e50",
            customdata=prev_custom,
            hovertemplate=(
                "%{x}<br>%{customdata[0]} / %{customdata[1]} subjects"
                "<br>%{y:.1f}% prevalence<extra></extra>"
            ),
            showlegend=False,
        ),
        row=3,
        col=1,
    )

    # ---- Cosmetics ----
    fig.update_layout(
        barmode="stack",
        height=720,
        margin=dict(l=60, r=20, t=60, b=120),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="left", x=0),
        paper_bgcolor="white",
        plot_bgcolor="white",
        bargap=0.15,
    )

    # All three x axes share the same category order.
    fig.update_xaxes(
        categoryorder="array",
        categoryarray=gene_ids,
        tickmode="array",
        tickvals=gene_ids,
        ticktext=gene_labels,
        tickangle=-60,
        showgrid=False,
        row=1,
        col=1,
    )
    fig.update_xaxes(
        categoryorder="array",
        categoryarray=gene_ids,
        tickmode="array",
        tickvals=gene_ids,
        ticktext=gene_labels,
        showticklabels=False,
        showgrid=False,
        row=2,
        col=1,
    )
    fig.update_xaxes(
        categoryorder="array",
        categoryarray=gene_ids,
        tickmode="array",
        tickvals=gene_ids,
        ticktext=gene_labels,
        tickangle=-60,
        showgrid=False,
        row=3,
        col=1,
    )

    fig.update_yaxes(range=[0, 1], tickformat=".0%", row=1, col=1, title_text="Class %")
    fig.update_yaxes(range=[0, 1], tickformat=".0%", row=2, col=1, title_text="Origin %")
    fig.update_yaxes(range=[0, max(prev_y) * 1.1 if prev_y and max(prev_y) > 0 else 10],
                     row=3, col=1, title_text="% of subjects")

    # Pathway group separators + labels above Row 1.
    segments = _pathway_segments(pathway_genes)
    shapes = []
    annotations = []
    for pathway, start, end in segments:
        midpoint_index = (start + end) / 2
        annotations.append(
            dict(
                x=gene_ids[int(midpoint_index)] if end > start else gene_ids[start],
                y=1.07,
                xref="x1",
                yref="paper",
                text=f"<b>{pathway}</b>",
                showarrow=False,
                font=dict(size=12, color="#2c3e50"),
            )
        )
        if end < len(gene_ids) - 1:
            # Vertical separator between this pathway and the next.
            shapes.append(
                dict(
                    type="line",
                    xref="x1",
                    yref="paper",
                    x0=end + 0.5,
                    x1=end + 0.5,
                    y0=0,
                    y1=1.0,
                    line=dict(color="#bdc3c7", width=1, dash="dot"),
                )
            )

    existing_annotations = list(fig.layout.annotations or [])
    fig.update_layout(shapes=shapes, annotations=existing_annotations + annotations)

    return fig
