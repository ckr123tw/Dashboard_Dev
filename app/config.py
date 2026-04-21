"""Runtime configuration for the dashboard."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "toy"


@dataclass(frozen=True)
class Config:
    # Core
    data_backend: str  # "csv" or "delta"
    data_dir: Path     # only used when data_backend == "csv"
    host: str
    port: int
    debug: bool

    # Databricks (only used when data_backend == "delta")
    databricks_host: str | None
    databricks_token: str | None
    databricks_warehouse_id: str | None
    databricks_catalog: str
    databricks_schema: str

    @classmethod
    def from_env(cls) -> "Config":
        data_backend = os.environ.get("DASHBOARD_DATA_BACKEND", "csv").lower()
        if data_backend not in ("csv", "delta"):
            raise ValueError(
                f"DASHBOARD_DATA_BACKEND must be 'csv' or 'delta', got {data_backend!r}"
            )

        data_dir = Path(os.environ.get("DASHBOARD_DATA_DIR", DEFAULT_DATA_DIR)).resolve()
        host = os.environ.get("DASHBOARD_HOST", "0.0.0.0")

        # Databricks Apps injects DATABRICKS_APP_PORT; honour it transparently.
        port_str = os.environ.get("DATABRICKS_APP_PORT") or os.environ.get("DASHBOARD_PORT", "8050")
        port = int(port_str)

        debug = os.environ.get("DASHBOARD_DEBUG", "1") not in ("0", "false", "False", "")

        return cls(
            data_backend=data_backend,
            data_dir=data_dir,
            host=host,
            port=port,
            debug=debug,
            databricks_host=os.environ.get("DATABRICKS_HOST"),
            databricks_token=os.environ.get("DATABRICKS_TOKEN"),
            databricks_warehouse_id=os.environ.get("DATABRICKS_WAREHOUSE_ID"),
            databricks_catalog=os.environ.get("DASHBOARD_CATALOG", "main"),
            databricks_schema=os.environ.get("DASHBOARD_SCHEMA", "variant_dashboard"),
        )


CONFIG = Config.from_env()

# Roots we know about (match subtypes.csv root column).
ROOTS = ("HM", "BT", "ST")
ROOT_LABELS = {
    "HM": "Hematologic Malignancy",
    "BT": "Brain Tumor",
    "ST": "Solid Tumor",
}

# Colour map for variant classes. Kept close to the PeCan palette intent:
# point mutations in warm hues, structural variants in cool hues.
VARIANT_CLASS_COLORS: dict[str, str] = {
    # point mutations
    "MISSENSE": "#2ecc71",
    "FRAMESHIFT": "#f1c40f",
    "NONSENSE": "#e74c3c",
    "SPLICE": "#9b59b6",
    "SPLICE_REGION": "#8e44ad",
    "PROTEININS": "#e67e22",
    "PROTEINDEL": "#d35400",
    "EXON": "#bdc3c7",
    # structural variants
    "COPY_LOSS": "#3498db",
    "ITD": "#1abc9c",
    "FUSION": "#e84393",
    "ENHANCER": "#00b894",
    "INTRAGENIC_DELETION": "#74b9ff",
    "DELETION": "#2980b9",
    "SILENCING": "#636e72",
    "ACTIVATING": "#d63031",
}

ORIGIN_COLORS = {
    "somatic": "#34495e",
    "germline": "#95a5a6",
}

POINT_MUTATION_CLASSES = (
    "FRAMESHIFT",
    "MISSENSE",
    "NONSENSE",
    "PROTEININS",
    "PROTEINDEL",
    "SPLICE",
    "SPLICE_REGION",
    "EXON",
)
STRUCTURAL_VARIANT_CLASSES = (
    "COPY_LOSS",
    "ITD",
    "FUSION",
    "ENHANCER",
    "INTRAGENIC_DELETION",
    "DELETION",
    "SILENCING",
    "ACTIVATING",
)
ALL_VARIANT_CLASSES = POINT_MUTATION_CLASSES + STRUCTURAL_VARIANT_CLASSES
