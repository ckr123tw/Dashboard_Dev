"""Tests for schema validation and descendant traversal."""

from __future__ import annotations

import pandas as pd
import pytest

from app.data_loader import SchemaError, load_data


def test_toy_bundle_loads(toy_bundle):
    assert len(toy_bundle.subtypes) > 0
    assert len(toy_bundle.samples) > 0
    assert len(toy_bundle.variants) > 0
    # Every subtype has a known root.
    assert set(toy_bundle.subtypes["root"]).issubset({"HM", "BT", "ST"})


def test_descendants_walk(toy_bundle):
    hm_nodes = toy_bundle.descendants("HM")
    assert "HM" in hm_nodes
    # At least one known leaf should be present.
    assert "BALLETV6RUNX1" in hm_nodes
    # No BT leaves.
    assert "HGGH3K27" not in hm_nodes


def test_cohort_samples_respects_subtree(toy_bundle):
    hm_cohort = toy_bundle.cohort_samples("HM")
    bt_cohort = toy_bundle.cohort_samples("BT")
    assert set(hm_cohort["sample_id"]).isdisjoint(set(bt_cohort["sample_id"]))
    assert len(hm_cohort) + len(bt_cohort) <= len(toy_bundle.samples)


def test_missing_column_rejected(tmp_path):
    # Only write three valid files + a broken subtypes.csv.
    (tmp_path / "subtypes.csv").write_text("subtype_code,subtype_name\nX,Y\n")
    (tmp_path / "samples.csv").write_text("sample_id,subject_id,subtype_code\n")
    (tmp_path / "gene_pathways.csv").write_text("gene,pathway,gene_list\n")
    (tmp_path / "variants.csv").write_text(
        "variant_id,sample_id,gene,variant_class,variant_category,origin\n"
    )
    with pytest.raises(SchemaError):
        load_data(tmp_path)


def test_unknown_variant_class_rejected(tmp_path, toy_bundle):
    # Copy toy data then corrupt one variant class.
    for name in ("subtypes", "samples", "gene_pathways"):
        df = getattr(toy_bundle, name)
        df.to_csv(tmp_path / f"{name}.csv", index=False)
    bad = toy_bundle.variants.copy()
    bad.loc[0, "variant_class"] = "BOGUS_CLASS"
    bad.to_csv(tmp_path / "variants.csv", index=False)
    with pytest.raises(SchemaError, match="variant_class"):
        load_data(tmp_path)


def test_orphan_parent_rejected(tmp_path, toy_bundle):
    for name in ("samples", "gene_pathways", "variants"):
        getattr(toy_bundle, name).to_csv(tmp_path / f"{name}.csv", index=False)
    bad = toy_bundle.subtypes.copy()
    bad.loc[0, "parent_code"] = "DOES_NOT_EXIST"
    bad.to_csv(tmp_path / "subtypes.csv", index=False)
    with pytest.raises(SchemaError, match="parent_code"):
        load_data(tmp_path)
