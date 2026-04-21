"""Exact-value tests for prevalence math."""

from __future__ import annotations

import math

from app.prevalence import (
    cohort_stats,
    origin_breakdown,
    prevalence_per_gene,
    variant_class_breakdown,
)


def test_cohort_stats(tiny_bundle):
    stats = cohort_stats(tiny_bundle.samples)
    assert stats.n_samples == 3
    assert stats.n_subjects == 3


def test_prevalence_per_gene_exact(tiny_bundle):
    prev = prevalence_per_gene(
        tiny_bundle.samples, tiny_bundle.variants, ["TP53", "KRAS"]
    )
    # 2 of 3 subjects have TP53 variants (S1, S3).
    assert prev.loc["TP53", "n_subjects_mutated"] == 2
    assert prev.loc["TP53", "n_subjects_total"] == 3
    assert math.isclose(prev.loc["TP53", "prevalence"], 2 / 3, rel_tol=1e-9)

    # 1 of 3 for KRAS (S1 only).
    assert prev.loc["KRAS", "n_subjects_mutated"] == 1
    assert math.isclose(prev.loc["KRAS", "prevalence"], 1 / 3)


def test_variant_class_breakdown_sums_to_one(tiny_bundle):
    df = variant_class_breakdown(
        tiny_bundle.samples, tiny_bundle.variants, ["TP53"]
    )
    total_prop = df["proportion"].sum()
    assert math.isclose(total_prop, 1.0)
    # TP53 has 2 MISSENSE + 1 COPY_LOSS = 3 variants.
    miss = df.loc[df["variant_class"] == "MISSENSE", "count"].iloc[0]
    cl = df.loc[df["variant_class"] == "COPY_LOSS", "count"].iloc[0]
    assert miss == 2 and cl == 1


def test_origin_breakdown_germline_kras(tiny_bundle):
    df = origin_breakdown(tiny_bundle.samples, tiny_bundle.variants, ["KRAS"])
    g = df.loc[df["origin"] == "germline"]
    assert len(g) == 1
    assert g["count"].iloc[0] == 1
    assert math.isclose(g["proportion"].iloc[0], 1.0)


def test_prevalence_empty_cohort(tiny_bundle):
    # Filter to an empty subset.
    empty = tiny_bundle.samples.iloc[0:0]
    prev = prevalence_per_gene(empty, tiny_bundle.variants, ["TP53"])
    assert prev.loc["TP53", "n_subjects_total"] == 0
    assert prev.loc["TP53", "prevalence"] == 0.0


def test_toy_prevalence_bounded(toy_bundle):
    """On the larger toy dataset, every prevalence must be in [0, 1]."""
    genes = toy_bundle.gene_pathways["gene"].unique().tolist()
    prev = prevalence_per_gene(toy_bundle.samples, toy_bundle.variants, genes)
    assert ((prev["prevalence"] >= 0) & (prev["prevalence"] <= 1)).all()
