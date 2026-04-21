"""Top-level page layout."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from app.components.filters import build_filters


def build_layout() -> html.Div:
    header = html.Div(
        [
            html.Div(
                [
                    html.Span("Variants", className="app-title-main"),
                    html.Span(" · Prevalence Dashboard", className="app-title-sub"),
                ],
                className="app-title",
            ),
            html.Div(id="cohort-stats", className="cohort-stats"),
        ],
        className="app-header",
    )

    sidebar = html.Div(
        [
            html.H5("Subtype", className="sidebar-title"),
            dcc.Graph(
                id="sunburst",
                config={"displayModeBar": False},
                style={"height": "420px"},
            ),
            html.Div(id="selected-subtype-label", className="selected-label"),
            html.Hr(),
            build_filters(),
        ],
        className="sidebar",
    )

    main = html.Div(
        [
            html.Div(id="section-title", className="section-title"),
            html.Div(
                "This bar graph summarises mutational prevalence for individual "
                "genes grouped by their annotated biological pathways in the "
                "selected cancer type or subtype. For cancer types/subtypes "
                "lacking curated pathway information, the pan-cancer gene list is used.",
                className="section-subtitle",
            ),
            dcc.Loading(
                dcc.Graph(
                    id="prevalence-chart",
                    config={
                        "displaylogo": False,
                        "modeBarButtonsToRemove": ["select2d", "lasso2d"],
                        "toImageButtonOptions": {
                            "format": "svg",
                            "filename": "variant_prevalence",
                        },
                    },
                    style={"height": "760px"},
                ),
                type="circle",
            ),
        ],
        className="main-content",
    )

    body = dbc.Row(
        [
            dbc.Col(sidebar, width=3, className="sidebar-col"),
            dbc.Col(main, width=9, className="main-col"),
        ],
        className="g-0",
    )

    return html.Div(
        [
            dcc.Store(id="selected-subtype", data="HM"),
            header,
            body,
        ],
        className="app-container",
    )
