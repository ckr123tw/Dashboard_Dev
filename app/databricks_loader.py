"""Databricks-backed data loader.

Reads the four dashboard tables from Unity Catalog Delta tables via a
serverless SQL Warehouse, converts them to pandas DataFrames, and hands
off to the shared validation pipeline in ``app.data_loader``. Returns the
same ``DataBundle`` the CSV loader produces, so the rest of the app is
backend-agnostic.

Auth modes (auto-detected, in order of preference):

1.  **Workspace identity (OAuth)** — when running inside Databricks Apps,
    the platform injects ``DATABRICKS_HOST`` and an OAuth token available
    via the Databricks SDK's default credential provider. This is the
    production path.
2.  **Personal Access Token** — for local development, set
    ``DATABRICKS_TOKEN`` alongside ``DATABRICKS_HOST``.

Required env vars in both modes:

- ``DATABRICKS_HOST`` — e.g. ``https://my-workspace.cloud.databricks.com``
- ``DATABRICKS_WAREHOUSE_ID`` — SQL Warehouse id (serverless recommended)
- ``DASHBOARD_CATALOG`` / ``DASHBOARD_SCHEMA`` — where the four tables live
  (defaults: ``main`` / ``variant_dashboard``).

No network calls happen at import time.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Protocol

import pandas as pd

from app.config import Config
from app.data_loader import (
    DataBundle,
    _validate_gene_pathways,
    _validate_samples,
    _validate_subtypes,
    _validate_variants,
)

log = logging.getLogger(__name__)

# Simple identifier regex to protect against SQL injection in catalog/schema/table names.
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

TABLES = ("subtypes", "samples", "gene_pathways", "variants")


class _Cursor(Protocol):
    def execute(self, query: str) -> Any: ...
    def fetchall_arrow(self) -> Any: ...
    def fetchall(self) -> list[tuple]: ...
    @property
    def description(self) -> list[tuple]: ...
    def close(self) -> None: ...


class _Connection(Protocol):
    def cursor(self) -> _Cursor: ...
    def close(self) -> None: ...


def _require_ident(name: str, value: str) -> None:
    if not _IDENT_RE.fullmatch(value):
        raise ValueError(f"{name} must be a simple SQL identifier, got {value!r}")


def _connect(cfg: Config) -> _Connection:
    """Open a Databricks SQL connection using the configured auth mode.

    Imported lazily so the rest of the app (and its tests) don't require the
    connector to be installed when using the CSV backend.
    """
    try:
        from databricks import sql  # type: ignore
    except ImportError as exc:  # pragma: no cover - import-time safeguard
        raise RuntimeError(
            "databricks-sql-connector is not installed. "
            "Run `pip install databricks-sql-connector databricks-sdk` "
            "or activate the pecan-dash conda env."
        ) from exc

    if not cfg.databricks_host:
        raise RuntimeError("DATABRICKS_HOST is not set")
    if not cfg.databricks_warehouse_id:
        raise RuntimeError("DATABRICKS_WAREHOUSE_ID is not set")

    server = cfg.databricks_host.replace("https://", "").replace("http://", "").rstrip("/")
    http_path = f"/sql/1.0/warehouses/{cfg.databricks_warehouse_id}"

    if cfg.databricks_token:
        log.info("Connecting to Databricks SQL Warehouse using PAT")
        return sql.connect(
            server_hostname=server,
            http_path=http_path,
            access_token=cfg.databricks_token,
        )

    # Fall back to the SDK's default credential chain (workspace OAuth when
    # running inside Databricks Apps, CLI profile / env OAuth elsewhere).
    try:
        from databricks.sdk.core import Config as SdkConfig  # type: ignore
        from databricks.sdk.core import oauth_service_principal  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "databricks-sdk is required for OAuth. "
            "pip install databricks-sdk"
        ) from exc

    sdk_cfg = SdkConfig(host=cfg.databricks_host)

    def credential_provider():  # pragma: no cover - exercised only on a real workspace
        return oauth_service_principal(sdk_cfg)

    log.info("Connecting to Databricks SQL Warehouse using workspace OAuth")
    return sql.connect(
        server_hostname=server,
        http_path=http_path,
        credentials_provider=credential_provider,
    )


def _fetch_table(cursor: _Cursor, fqtn: str) -> pd.DataFrame:
    """Run ``SELECT * FROM fqtn`` and return a pandas DataFrame.

    Prefers the Arrow fetch path (fast, preserves dtypes) and falls back to
    the tuple path if Arrow is unavailable (e.g. in mocks).
    """
    cursor.execute(f"SELECT * FROM {fqtn}")
    try:
        table = cursor.fetchall_arrow()
        df = table.to_pandas() if table is not None else pd.DataFrame()
    except (AttributeError, NotImplementedError):
        rows = cursor.fetchall()
        cols = [c[0] for c in (cursor.description or [])]
        df = pd.DataFrame(rows, columns=cols)

    # Coerce ID/string columns to str to match the CSV loader's behaviour.
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).where(df[col].notna(), "")
    return df


def load_data_from_databricks(cfg: Config) -> DataBundle:
    """Build a ``DataBundle`` by reading four Delta tables from Unity Catalog."""
    _require_ident("DASHBOARD_CATALOG", cfg.databricks_catalog)
    _require_ident("DASHBOARD_SCHEMA", cfg.databricks_schema)

    conn = _connect(cfg)
    try:
        cur = conn.cursor()
        try:
            frames: dict[str, pd.DataFrame] = {}
            for table in TABLES:
                fqtn = f"`{cfg.databricks_catalog}`.`{cfg.databricks_schema}`.`{table}`"
                log.info("Fetching %s", fqtn)
                frames[table] = _fetch_table(cur, fqtn)
        finally:
            cur.close()
    finally:
        conn.close()

    return _build_bundle(frames)


def _build_bundle(frames: dict[str, pd.DataFrame]) -> DataBundle:
    """Validate + assemble a ``DataBundle`` from in-memory frames.

    Split out from :func:`load_data_from_databricks` so tests can exercise the
    validation path without touching the network. Mirrors the cast-and-validate
    sequence in ``app.data_loader.load_data``.
    """
    subtypes = frames["subtypes"].copy()
    samples = frames["samples"].copy()
    gene_pathways = frames["gene_pathways"].copy()
    variants = frames["variants"].copy()

    required = {
        "subtypes": ("subtype_code", "subtype_name", "parent_code", "root", "level"),
        "samples": ("sample_id", "subject_id", "subtype_code"),
        "gene_pathways": ("gene", "pathway", "gene_list"),
        "variants": (
            "variant_id",
            "sample_id",
            "gene",
            "variant_class",
            "variant_category",
            "origin",
        ),
    }
    for name, cols in required.items():
        df = frames[name]
        missing = [c for c in cols if c not in df.columns]
        if missing:
            from app.data_loader import SchemaError

            raise SchemaError(f"{name}: missing required columns {missing}")

    subtypes["level"] = pd.to_numeric(subtypes["level"], errors="raise").astype(int)
    if "age_years" in samples.columns:
        samples["age_years"] = pd.to_numeric(samples["age_years"], errors="coerce")
    if "display_order" in gene_pathways.columns:
        gene_pathways["display_order"] = (
            pd.to_numeric(gene_pathways["display_order"], errors="coerce")
            .fillna(0)
            .astype(int)
        )

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
