# Databricks notebook source
# MAGIC %md
# MAGIC # Load Toy Dataset into Unity Catalog Delta Tables
# MAGIC
# MAGIC Ingests the four CSV tables shipped under `data/toy/` into a Unity
# MAGIC Catalog schema. Idempotent: re-running overwrites the tables.
# MAGIC
# MAGIC Parameters (declared via `dbutils.widgets`, overridable from the Jobs UI
# MAGIC or Databricks Asset Bundle):
# MAGIC
# MAGIC | Widget      | Default                                                  | Purpose                                            |
# MAGIC | ----------- | -------------------------------------------------------- | -------------------------------------------------- |
# MAGIC | `catalog`   | `main`                                                   | Destination Unity Catalog.                         |
# MAGIC | `schema`    | `variant_dashboard`                                      | Destination schema (created if missing).           |
# MAGIC | `data_path` | _(must be supplied — use the bundle's `${workspace.file_path}/data/toy`)_ | Source directory containing the four CSVs. |
# MAGIC
# MAGIC The notebook re-uses the same **schema validation** code as the app so
# MAGIC bad data fails loudly *before* it becomes a runtime issue in the
# MAGIC dashboard.

# COMMAND ----------

dbutils.widgets.text("catalog", "main", "Catalog")
dbutils.widgets.text("schema", "variant_dashboard", "Schema")
# `data_path` has no sensible default: it depends on where the repo is
# synced. The DAB passes `${workspace.file_path}/data/toy`; for ad-hoc
# runs, set it to the folder containing the four CSVs.
dbutils.widgets.text("data_path", "", "CSV source directory (required)")

catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
data_path = dbutils.widgets.get("data_path").strip().rstrip("/")

import re

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
if not _IDENT.fullmatch(catalog):
    raise ValueError(f"catalog must be a simple identifier: {catalog!r}")
if not _IDENT.fullmatch(schema):
    raise ValueError(f"schema must be a simple identifier: {schema!r}")
if not data_path:
    raise ValueError(
        "data_path widget is empty. Pass the path to the directory containing "
        "the four CSVs (subtypes, samples, gene_pathways, variants). "
        "The bundle supplies ${workspace.file_path}/data/toy automatically."
    )

print(f"target: {catalog}.{schema}")
print(f"source: {data_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Ensure catalog / schema exist

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Read the four CSVs with explicit schemas

# COMMAND ----------

from pyspark.sql.types import (
    IntegerType,
    StringType,
    StructField,
    StructType,
    DoubleType,
)

SUBTYPES_SCHEMA = StructType(
    [
        StructField("subtype_code", StringType(), nullable=False),
        StructField("subtype_name", StringType(), nullable=False),
        StructField("parent_code", StringType(), nullable=True),
        StructField("root", StringType(), nullable=False),
        StructField("level", IntegerType(), nullable=False),
        StructField("description", StringType(), nullable=True),
    ]
)

SAMPLES_SCHEMA = StructType(
    [
        StructField("sample_id", StringType(), nullable=False),
        StructField("subject_id", StringType(), nullable=False),
        StructField("subtype_code", StringType(), nullable=False),
        StructField("sex", StringType(), nullable=True),
        StructField("age_years", DoubleType(), nullable=True),
    ]
)

GENE_PATHWAYS_SCHEMA = StructType(
    [
        StructField("gene", StringType(), nullable=False),
        StructField("pathway", StringType(), nullable=False),
        StructField("gene_list", StringType(), nullable=False),
        StructField("cancer_root", StringType(), nullable=True),
        StructField("display_order", IntegerType(), nullable=True),
    ]
)

VARIANTS_SCHEMA = StructType(
    [
        StructField("variant_id", StringType(), nullable=False),
        StructField("sample_id", StringType(), nullable=False),
        StructField("gene", StringType(), nullable=False),
        StructField("variant_class", StringType(), nullable=False),
        StructField("variant_category", StringType(), nullable=False),
        StructField("origin", StringType(), nullable=False),
    ]
)


def _read_csv(filename: str, struct):
    return (
        spark.read.option("header", True)
        .schema(struct)
        .csv(f"{data_path}/{filename}")
    )


subtypes_df = _read_csv("subtypes.csv", SUBTYPES_SCHEMA)
samples_df = _read_csv("samples.csv", SAMPLES_SCHEMA)
gene_pathways_df = _read_csv("gene_pathways.csv", GENE_PATHWAYS_SCHEMA)
variants_df = _read_csv("variants.csv", VARIANTS_SCHEMA)

print("row counts:",
      {"subtypes": subtypes_df.count(),
       "samples": samples_df.count(),
       "gene_pathways": gene_pathways_df.count(),
       "variants": variants_df.count()})

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Cross-table validation (reuses the app's validators)
# MAGIC
# MAGIC Convert to pandas (tables are small) and run the exact same checks the
# MAGIC dashboard's loader performs.

# COMMAND ----------

import sys

# The bundle passes data_path = "${workspace.file_path}/data/toy", so the
# repo root is two levels up. Strip `data/toy` (or `data/<anything>`) off
# the end to locate the repo.
_parts = data_path.rstrip("/").split("/")
if len(_parts) < 2:
    raise ValueError(f"data_path is too shallow to derive a repo root: {data_path!r}")
repo_root = "/".join(_parts[:-2])
if repo_root and repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from app.data_loader import (  # type: ignore  # noqa: E402
    validate_gene_pathways,
    validate_samples,
    validate_subtypes,
    validate_variants,
)

st = subtypes_df.toPandas()
sm = samples_df.toPandas()
gp = gene_pathways_df.toPandas()
vr = variants_df.toPandas()

st["parent_code"] = st["parent_code"].fillna("")
st["description"] = st["description"].fillna("")
gp["cancer_root"] = gp["cancer_root"].fillna("")
gp["display_order"] = gp["display_order"].fillna(0).astype(int)

validate_subtypes(st)
validate_samples(sm, st)
validate_gene_pathways(gp)
validate_variants(vr, sm)

print("validation OK")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Write Delta tables (overwrite mode)

# COMMAND ----------

for name, df in [
    ("subtypes", subtypes_df),
    ("samples", samples_df),
    ("gene_pathways", gene_pathways_df),
    ("variants", variants_df),
]:
    fqtn = f"`{catalog}`.`{schema}`.`{name}`"
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(fqtn)
    )
    print(f"wrote {fqtn}  ({df.count()} rows)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Smoke-check with a handful of reads

# COMMAND ----------

display(spark.sql(f"SELECT * FROM `{catalog}`.`{schema}`.`subtypes` LIMIT 5"))
display(
    spark.sql(
        f"""
        SELECT gene, COUNT(*) AS n_variants
        FROM `{catalog}`.`{schema}`.`variants`
        GROUP BY gene
        ORDER BY n_variants DESC
        LIMIT 10
        """
    )
)
