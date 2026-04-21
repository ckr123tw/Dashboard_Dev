"""Sunburst disease/subtype navigator, built from subtypes + samples."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


ROOT_COLORS = {
    "HM": "#c0392b",
    "BT": "#2980b9",
    "ST": "#16a085",
}


def build_sunburst_figure(subtypes: pd.DataFrame, samples: pd.DataFrame) -> go.Figure:
    """Build a sunburst whose slice size = cohort-sample count.

    The Plotly sunburst expects one row per node with (id, parent, value, label).
    We compute per-node counts (samples attached to this node or any descendant).
    """
    # Count samples per leaf subtype_code.
    leaf_counts = samples.groupby("subtype_code").size().to_dict()

    # For every node, accumulate counts of descendants.
    children_map = (
        subtypes.groupby("parent_code")["subtype_code"].apply(list).to_dict()
    )

    def descendant_count(code: str) -> int:
        total = leaf_counts.get(code, 0)
        for ch in children_map.get(code, []):
            total += descendant_count(ch)
        return total

    ids: list[str] = []
    labels: list[str] = []
    parents: list[str] = []
    values: list[int] = []
    customdata: list[list[str]] = []
    colors: list[str] = []

    for _, row in subtypes.iterrows():
        code = row["subtype_code"]
        ids.append(code)
        labels.append(code)
        parents.append(row["parent_code"] or "")
        values.append(descendant_count(code))
        customdata.append([row["subtype_name"], str(descendant_count(code))])
        colors.append(ROOT_COLORS.get(row["root"], "#7f8c8d"))

    fig = go.Figure(
        go.Sunburst(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            customdata=customdata,
            branchvalues="total",
            hovertemplate=(
                "<b>%{label}</b><br>%{customdata[0]}<br>"
                "Samples: %{customdata[1]}<extra></extra>"
            ),
            marker=dict(colors=colors, line=dict(color="#ffffff", width=1)),
            insidetextorientation="radial",
        )
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        uniformtext=dict(minsize=10, mode="hide"),
    )
    return fig
