"""Tests for the Databricks-backed loader.

No workspace is contacted. We stub the SQL-connector ``cursor`` so the
loader's `_fetch_table` path is exercised against a fake result set, and
verify that:

- the same schema-validation rules fire,
- string coercion works for int-like columns coming back from the connector,
- ``_build_bundle`` rejects unknown variant classes (same contract as CSV),
- identifier validation rejects unsafe catalog/schema names.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from app.data_loader import SchemaError
from app.databricks_loader import _build_bundle, _require_ident


def _frames_from_bundle(bundle) -> dict[str, pd.DataFrame]:
    """Round-trip a DataBundle into the frame-dict `_build_bundle` expects."""
    return {
        "subtypes": bundle.subtypes.copy(),
        "samples": bundle.samples.copy(),
        "gene_pathways": bundle.gene_pathways.copy(),
        "variants": bundle.variants.copy(),
    }


def test_build_bundle_from_toy_frames(toy_bundle):
    frames = _frames_from_bundle(toy_bundle)
    # Simulate the connector returning ints for `level` (Delta IntegerType)
    # rather than strings; the loader must still coerce correctly.
    frames["subtypes"]["level"] = frames["subtypes"]["level"].astype(int)
    rebuilt = _build_bundle(frames)
    assert len(rebuilt.subtypes) == len(toy_bundle.subtypes)
    assert len(rebuilt.variants) == len(toy_bundle.variants)


def test_build_bundle_missing_column_rejected(toy_bundle):
    frames = _frames_from_bundle(toy_bundle)
    frames["variants"] = frames["variants"].drop(columns=["origin"])
    with pytest.raises(SchemaError, match="origin"):
        _build_bundle(frames)


def test_build_bundle_unknown_variant_class_rejected(toy_bundle):
    frames = _frames_from_bundle(toy_bundle)
    frames["variants"].loc[0, "variant_class"] = "NOT_A_REAL_CLASS"
    with pytest.raises(SchemaError, match="variant_class"):
        _build_bundle(frames)


def test_require_ident_blocks_injection():
    _require_ident("catalog", "main")
    _require_ident("schema", "variant_dashboard_42")
    for bad in ["main; DROP TABLE x", "my catalog", "", "1leading_digit", "ok`quote"]:
        with pytest.raises(ValueError):
            _require_ident("catalog", bad)


# ---------- _fetch_table via fake cursor ----------

class _FakeCursor:
    """Mimics the databricks-sql-connector cursor interface for one row set."""

    def __init__(self, rows: list[tuple], columns: list[str]) -> None:
        self._rows = rows
        self._columns = columns

    def execute(self, query: str) -> None:
        self._last_query = query  # noqa: F841

    def fetchall_arrow(self) -> Any:  # Force the pandas-fallback path.
        raise NotImplementedError

    def fetchall(self) -> list[tuple]:
        return self._rows

    @property
    def description(self) -> list[tuple]:
        return [(c,) for c in self._columns]

    def close(self) -> None:
        pass


def test_fetch_table_fallback_path():
    from app.databricks_loader import _fetch_table

    cur = _FakeCursor(
        rows=[("S1", "SUBJ1", "L1"), ("S2", "SUBJ2", "L1")],
        columns=["sample_id", "subject_id", "subtype_code"],
    )
    df = _fetch_table(cur, "`main`.`variant_dashboard`.`samples`")
    assert list(df.columns) == ["sample_id", "subject_id", "subtype_code"]
    assert df.shape == (2, 3)
    # String columns are coerced to str (pandas may use `object` or `StringDtype`).
    assert str(df["sample_id"].dtype) in ("object", "str", "string")
    assert df.iloc[0]["sample_id"] == "S1"


def test_load_data_from_databricks_uses_connection(monkeypatch, toy_bundle):
    """End-to-end with a fake connection: pulls the four tables and builds a bundle."""
    from app import databricks_loader

    frames = _frames_from_bundle(toy_bundle)
    # Make sure `level` is an int to mirror the Delta schema.
    frames["subtypes"]["level"] = frames["subtypes"]["level"].astype(int)

    table_to_frame = {
        "subtypes": frames["subtypes"],
        "samples": frames["samples"],
        "gene_pathways": frames["gene_pathways"],
        "variants": frames["variants"],
    }

    class _Cursor:
        def __init__(self) -> None:
            self._pending: pd.DataFrame | None = None

        def execute(self, query: str) -> None:
            # Extract the final `table` name from the backticked FQTN.
            name = query.rsplit(".", 1)[-1].strip("`")
            self._pending = table_to_frame[name]

        def fetchall_arrow(self):  # Skip arrow path
            raise NotImplementedError

        def fetchall(self):
            assert self._pending is not None
            return [tuple(r) for r in self._pending.to_numpy()]

        @property
        def description(self):
            assert self._pending is not None
            return [(c,) for c in self._pending.columns]

        def close(self) -> None:
            pass

    class _Conn:
        def cursor(self) -> _Cursor:
            return _Cursor()

        def close(self) -> None:
            pass

    monkeypatch.setattr(databricks_loader, "_connect", lambda cfg: _Conn())

    from pathlib import Path

    from app.config import Config

    fake_cfg = Config(
        data_backend="delta",
        data_dir=Path("/tmp/unused"),
        host="0.0.0.0",
        port=8050,
        debug=False,
        databricks_host="https://example.cloud.databricks.com",
        databricks_token="dapi-fake",
        databricks_warehouse_id="warehouse1",
        databricks_catalog="main",
        databricks_schema="variant_dashboard",
    )
    bundle = databricks_loader.load_data_from_databricks(fake_cfg)
    assert len(bundle.samples) == len(toy_bundle.samples)
    # cohort traversal still works on the rebuilt bundle
    assert "BALLETV6RUNX1" in bundle.descendants("HM")
