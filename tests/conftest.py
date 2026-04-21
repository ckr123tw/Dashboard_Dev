"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.config import DEFAULT_DATA_DIR
from app.data_loader import DataBundle, load_data


@pytest.fixture(scope="session")
def toy_bundle() -> DataBundle:
    return load_data(DEFAULT_DATA_DIR)


@pytest.fixture
def tiny_bundle(tmp_path: Path) -> DataBundle:
    """A hand-rolled 3-sample bundle used to verify prevalence math exactly."""
    subtypes = pd.DataFrame(
        [
            ("R1", "Root 1", "", "R1", 0, ""),
            ("F1", "Family 1", "R1", "R1", 1, ""),
            ("L1", "Leaf 1", "F1", "R1", 2, ""),
            ("L2", "Leaf 2", "F1", "R1", 2, ""),
        ],
        columns=["subtype_code", "subtype_name", "parent_code", "root", "level", "description"],
    )
    samples = pd.DataFrame(
        [
            ("S1", "P1", "L1", "M", "10"),
            ("S2", "P2", "L1", "F", "11"),  # same gene, no variant -> not counted
            ("S3", "P3", "L2", "M", "12"),
        ],
        columns=["sample_id", "subject_id", "subtype_code", "sex", "age_years"],
    )
    gp = pd.DataFrame(
        [
            ("TP53", "Cell Cycle", "pan_cancer", "", 0),
            ("KRAS", "RTK/RAS", "pan_cancer", "", 1),
        ],
        columns=["gene", "pathway", "gene_list", "cancer_root", "display_order"],
    )
    # S1 has 2 MISSENSE TP53 (same subject, counts once), plus 1 KRAS FUSION (germline).
    # S3 has 1 TP53 COPY_LOSS (somatic).
    variants = pd.DataFrame(
        [
            ("V1", "S1", "TP53", "MISSENSE", "point_mutation", "somatic"),
            ("V2", "S1", "TP53", "MISSENSE", "point_mutation", "somatic"),
            ("V3", "S1", "KRAS", "FUSION", "structural_variant", "germline"),
            ("V4", "S3", "TP53", "COPY_LOSS", "structural_variant", "somatic"),
        ],
        columns=["variant_id", "sample_id", "gene", "variant_class", "variant_category", "origin"],
    )

    d = tmp_path
    subtypes.to_csv(d / "subtypes.csv", index=False)
    samples.to_csv(d / "samples.csv", index=False)
    gp.to_csv(d / "gene_pathways.csv", index=False)
    variants.to_csv(d / "variants.csv", index=False)
    return load_data(d)
