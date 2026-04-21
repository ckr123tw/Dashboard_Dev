"""Prevalence / breakdown math. Pure functions, no Dash dependency."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class CohortStats:
    n_samples: int
    n_subjects: int


def cohort_stats(samples: pd.DataFrame) -> CohortStats:
    return CohortStats(
        n_samples=int(samples["sample_id"].nunique()),
        n_subjects=int(samples["subject_id"].nunique()),
    )


def prevalence_per_gene(
    samples: pd.DataFrame, variants: pd.DataFrame, genes: Iterable[str]
) -> pd.DataFrame:
    """Fraction of subjects in `samples` with ≥1 variant in each gene.

    Returns a DataFrame indexed by gene with columns:
        - n_subjects_mutated
        - n_subjects_total
        - prevalence (0-1)
    """
    genes = list(genes)
    n_total = int(samples["subject_id"].nunique())

    if n_total == 0 or not genes:
        return pd.DataFrame(
            {
                "gene": genes,
                "n_subjects_mutated": [0] * len(genes),
                "n_subjects_total": [0] * len(genes),
                "prevalence": [0.0] * len(genes),
            }
        ).set_index("gene")

    cohort_samples = samples["sample_id"]
    v = variants[variants["sample_id"].isin(cohort_samples) & variants["gene"].isin(genes)]

    # Map sample_id -> subject_id for dedup.
    subj_map = samples.set_index("sample_id")["subject_id"]
    v = v.assign(subject_id=v["sample_id"].map(subj_map))

    mutated = (
        v.groupby("gene")["subject_id"].nunique().reindex(genes).fillna(0).astype(int)
    )

    out = pd.DataFrame(
        {
            "n_subjects_mutated": mutated,
            "n_subjects_total": n_total,
            "prevalence": mutated / n_total,
        }
    )
    out.index.name = "gene"
    return out


def variant_class_breakdown(
    samples: pd.DataFrame, variants: pd.DataFrame, genes: Iterable[str]
) -> pd.DataFrame:
    """Per-gene, per-class variant counts and proportions within that gene.

    Returns a long DataFrame with columns: gene, variant_class, count, proportion.
    """
    genes = list(genes)
    cohort_samples = samples["sample_id"]
    v = variants[variants["sample_id"].isin(cohort_samples) & variants["gene"].isin(genes)]

    if v.empty:
        return pd.DataFrame(columns=["gene", "variant_class", "count", "proportion"])

    grp = v.groupby(["gene", "variant_class"]).size().reset_index(name="count")
    totals = grp.groupby("gene")["count"].transform("sum")
    grp["proportion"] = grp["count"] / totals
    return grp


def origin_breakdown(
    samples: pd.DataFrame, variants: pd.DataFrame, genes: Iterable[str]
) -> pd.DataFrame:
    """Per-gene somatic/germline counts and proportions.

    Returns DataFrame with columns: gene, origin, count, proportion.
    """
    genes = list(genes)
    cohort_samples = samples["sample_id"]
    v = variants[variants["sample_id"].isin(cohort_samples) & variants["gene"].isin(genes)]

    if v.empty:
        return pd.DataFrame(columns=["gene", "origin", "count", "proportion"])

    grp = v.groupby(["gene", "origin"]).size().reset_index(name="count")
    totals = grp.groupby("gene")["count"].transform("sum")
    grp["proportion"] = grp["count"] / totals
    return grp
