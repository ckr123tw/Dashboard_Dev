"""Filter panel components (gene list toggle, reset, export SVG)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html


def build_filters() -> html.Div:
    return html.Div(
        [
            html.H5("Filters", className="filter-title"),
            html.Label("Gene list", className="filter-label"),
            dcc.RadioItems(
                id="gene-list-radio",
                options=[
                    {"label": " Curated (per cancer type)", "value": "curated"},
                    {"label": " Pan-cancer", "value": "pan_cancer"},
                ],
                value="curated",
                className="filter-radio",
                labelStyle={"display": "block", "marginBottom": "4px"},
            ),
            html.Hr(),
            html.Label("Variant categories", className="filter-label"),
            dcc.Checklist(
                id="variant-category-check",
                options=[
                    {"label": " Point mutations", "value": "point_mutation"},
                    {"label": " Structural variants", "value": "structural_variant"},
                ],
                value=["point_mutation", "structural_variant"],
                labelStyle={"display": "block", "marginBottom": "4px"},
            ),
            html.Hr(),
            dbc.ButtonGroup(
                [
                    dbc.Button("Reset", id="reset-btn", color="secondary", size="sm"),
                    dbc.Button("Export SVG", id="export-svg-btn", color="primary", size="sm"),
                ],
                className="filter-buttons",
            ),
            dcc.Download(id="svg-download"),
        ],
        className="filter-panel",
    )
