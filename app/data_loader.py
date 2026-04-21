"""CSV/parquet loader with strict schema validation.

See ``docs/data_schema.md`` for the full contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from app.config import (
    ALL_VARIANT_CLASSES,
    POINT_MUTATION_CLASSES,
    STRUCTURAL_VARIANT_CLASSES,
)


REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "subtypes": ("subtype_code", "subtype_name", "parent_code", "root", "level"),
    "samples": ("sample_id", "subject_id", "subtype_code"),
    "gene_pathways": ("gene", "pathway", "gene_list"),
    "variants": ("variant_id", "sample_id", "gene", "variant_class", "variant_category", "origin"),
}


class SchemaError(ValueError):
    """Raised when the on-disk data does not match the ingestion contract."""


@dataclass(frozen=True)
class DataBundle:
    subtypes: pd.DataFrame
    samples: pd.DataFrame
    gene_pathways: pd.DataFrame
    variants: pd.DataFrame

    def subtype_name(self, code: str) -> str:
        row = self.subtypes.loc[self.subtypes["subtype_code"] == code]
        if row.empty:
            return code
        return str(row["subtype_name"].iloc[0])

    def descendants(self, code: str) -> list[str]:
        """Return `code` plus all descendant subtype codes (BFS)."""
        out = [code]
        frontier = [code]
        children_map = (
            self.subtypes.groupby("parent_code")["subtype_code"].apply(list).to_dict()
        )
        while frontier:
            nxt = []
            for c in frontier:
                for ch in children_map.get(c, []):
                    out.append(ch)
                    nxt.append(ch)
            frontier = nxt
        return out

    def cohort_samples(self, code: str) -> pd.DataFrame:
        """Samples belonging to ``code`` or any descendant."""
        leaves = self.descendants(code)
        return self.samples[self.samples["subtype_code"].isin(leaves)]


def _read(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _require_cols(name: str, df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS[name] if c not in df.columns]
    if missing:
        raise SchemaError(f"{name}: missing required columns {missing}")


def load_data(data_dir: Path | str) -> DataBundle:
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        raise FileNotFoundError(f"data_dir not found: {data_dir}")

    def _find(stem: str) -> Path:
        for ext in (".csv", ".parquet"):
            p = data_dir / f"{stem}{ext}"
            if p.exists():
                return p
        raise FileNotFoundError(f"{stem}.csv or {stem}.parquet not found in {data_dir}")

    subtypes = _read(_find("subtypes"))
    samples = _read(_find("samples"))
    gene_pathways = _read(_find("gene_pathways"))
    variants = _read(_find("variants"))

    _require_cols("subtypes", subtypes)
    _require_cols("samples", samples)
    _require_cols("gene_pathways", gene_pathways)
    _require_cols("variants", variants)

    # Cast types after string-safe read.
    subtypes["level"] = subtypes["level"].astype(int)
    if "age_years" in samples.columns:
        samples["age_years"] = pd.to_numeric(samples["age_years"], errors="coerce")
    if "display_order" in gene_pathways.columns:
        gene_pathways["display_order"] = pd.to_numeric(
            gene_pathways["display_order"], errors="coerce"
        ).fillna(0).astype(int)

    _validate_subtypes(subtypes)
    _validate_samples(samples, subtypes)
    _validate_gene_pathways(gene_pathways)
    _validate_variants(variants, samples)

    return DataBundle(
        subtypes=subtypes.reset_index(drop=True),
        samples=samples.reset_index(drop=True),
        gene_pathways=gene_pathways.reset_index(drop=True),
        variants=variants.reset_index(drop=True),
    )


def _validate_subtypes(df: pd.DataFrame) -> None:
    if df["subtype_code"].duplicated().any():
        dups = df.loc[df["subtype_code"].duplicated(), "subtype_code"].tolist()
        raise SchemaError(f"subtypes: duplicate subtype_code values: {dups}")
    codes = set(df["subtype_code"])
    orphans = df.loc[
        (df["parent_code"] != "") & (~df["parent_code"].isin(codes)),
        "subtype_code",
    ].tolist()
    if orphans:
        raise SchemaError(f"subtypes: parent_code references unknown codes for {orphans}")


def _validate_samples(samples: pd.DataFrame, subtypes: pd.DataFrame) -> None:
    if samples["sample_id"].duplicated().any():
        raise SchemaError("samples: duplicate sample_id")
    leaves = set(subtypes.loc[subtypes["level"] == 2, "subtype_code"])
    bad = samples.loc[~samples["subtype_code"].isin(leaves), "sample_id"].tolist()
    if bad:
        raise SchemaError(
            f"samples: {len(bad)} rows reference non-leaf or unknown subtype_code (first 5: {bad[:5]})"
        )


def _validate_gene_pathways(df: pd.DataFrame) -> None:
    bad = df.loc[~df["gene_list"].isin({"curated", "pan_cancer"}), "gene"].tolist()
    if bad:
        raise SchemaError(f"gene_pathways: gene_list must be curated|pan_cancer; bad rows for {bad[:5]}")


def _validate_variants(variants: pd.DataFrame, samples: pd.DataFrame) -> None:
    sample_ids = set(samples["sample_id"])
    missing_samples = variants.loc[~variants["sample_id"].isin(sample_ids), "variant_id"].tolist()
    if missing_samples:
        raise SchemaError(
            f"variants: {len(missing_samples)} rows reference unknown sample_id (first 5: {missing_samples[:5]})"
        )

    bad_class = variants.loc[~variants["variant_class"].isin(ALL_VARIANT_CLASSES), "variant_class"].unique().tolist()
    if bad_class:
        raise SchemaError(f"variants: unknown variant_class values: {bad_class}")

    bad_origin = variants.loc[~variants["origin"].isin({"somatic", "germline"}), "origin"].unique().tolist()
    if bad_origin:
        raise SchemaError(f"variants: unknown origin values: {bad_origin}")

    # Category must match the class bucket.
    expected_category = variants["variant_class"].map(
        lambda c: "point_mutation" if c in POINT_MUTATION_CLASSES else "structural_variant"
    )
    mismatch = variants.loc[variants["variant_category"] != expected_category, "variant_id"].tolist()
    if mismatch:
        raise SchemaError(
            f"variants: variant_category inconsistent with variant_class for {len(mismatch)} rows"
            f" (first 5: {mismatch[:5]})"
        )


def active_gene_list(
    gene_pathways: pd.DataFrame, root: str | None, prefer: str = "curated"
) -> pd.DataFrame:
    """Choose a gene list for display.

    - If ``prefer == 'curated'`` and a curated list exists for the given root,
      return it.
    - Otherwise fall back to ``pan_cancer``.
    """
    if prefer == "curated" and root:
        curated = gene_pathways[
            (gene_pathways["gene_list"] == "curated") & (gene_pathways["cancer_root"] == root)
        ]
        if not curated.empty:
            return curated.copy()
    return gene_pathways[gene_pathways["gene_list"] == "pan_cancer"].copy()


def iter_pathway_genes(df: pd.DataFrame) -> Iterable[tuple[str, list[str]]]:
    """Yield (pathway, [genes]) tuples, preserving original pathway order."""
    seen: list[str] = []
    for p in df["pathway"].tolist():
        if p not in seen:
            seen.append(p)
    for p in seen:
        sub = df[df["pathway"] == p].sort_values(
            ["display_order", "gene"], kind="mergesort"
        )
        yield p, sub["gene"].tolist()
