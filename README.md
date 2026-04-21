# Variant Prevalence Dashboard

A Plotly/Dash dashboard modelled on the
[St. Jude PeCan Variant Prevalence](https://pecan.stjude.cloud/variants/prevalence)
page, powered by **your own** data via a documented ingestion contract. A small
toy dataset ships under `data/toy/` so you can demo and debug immediately.

- Execution plan and task list: [`plan.md`](plan.md).
- Data ingestion contract: [`docs/data_schema.md`](docs/data_schema.md).
- Databricks deployment: [`databricks/README.md`](databricks/README.md).

## Features

- **Sunburst navigator** over a three-level disease hierarchy (root →
  family → leaf).
- Header stats: number of samples and subjects in the selected cohort.
- **Variant Prevalence by Pathway** chart with three vertically stacked rows:
  1. Variant class proportion (stacked to 100 %).
  2. Variant origin (somatic vs germline).
  3. Per-gene prevalence (% of subjects with ≥ 1 variant).
- Filter panel: curated vs pan-cancer gene list, point / structural variant
  toggle, reset, and SVG export.
- Pathway-group separators and labels on the chart.

## Prerequisites

- A POSIX shell (Linux, macOS, or WSL).
- `conda` (Miniforge / Miniconda / Anaconda). The setup script can bootstrap
  Miniforge for you — see below.

## Quick start

```bash
# 1. Create the conda environment (uses an existing conda if present).
bash scripts/setup_conda_env.sh
# First-time users without conda installed:
INSTALL_MINIFORGE=1 bash scripts/setup_conda_env.sh

# 2. Activate the env and launch the app.
conda activate pecan-dash
python -m app.main
# → http://localhost:8050

# 3. Run the test suite.
bash scripts/run_tests.sh
```

The scripts resolve the repo root from their own location, so they work from
any cwd.

## Repository layout

```
app/                      Dash application
  main.py                 Entry point (python -m app.main)
  config.py               Env-driven configuration + colour palette
  data_loader.py          CSV / Parquet ingest + schema validation
  databricks_loader.py    Delta-backed loader for Databricks deployments
  prevalence.py           Pure-Python prevalence math
  components/             sunburst, prevalence_chart, filters, layout
  assets/styles.css       Custom styling
data/toy/                 Toy dataset used for demo and tests
databricks/               Databricks deployment (app.yaml, DAB, notebook)
docs/data_schema.md       Data ingestion contract
scripts/                  Setup, test, and smoke scripts
tests/                    pytest suite
environment.yml           Conda env spec (Python 3.11)
plan.md                   Execution plan and TODO list
```

## Swapping in your own data

1. Produce the four tables described in
   [`docs/data_schema.md`](docs/data_schema.md) (`subtypes`, `samples`,
   `gene_pathways`, `variants`) as CSV or Parquet.
2. Drop them into a directory, for example `data/real/`.
3. Launch with:

   ```bash
   DASHBOARD_DATA_DIR=data/real python -m app.main
   ```

The loader performs strict validation at startup and refuses to run if any
column is missing or a controlled-vocabulary value is wrong — the error
message lists what to fix.

## Databricks deployment

The same app runs unchanged on **Databricks Apps** backed by **Unity Catalog
Delta tables**. Flip `DASHBOARD_DATA_BACKEND` from `csv` to `delta` and the
app reads via a SQL Warehouse instead of local CSVs.

```bash
cd databricks
export WAREHOUSE_ID=<your-sql-warehouse-id>
./deploy.sh all
```

This creates:

- a **Job** that loads `data/toy/*.csv` into
  `<catalog>.<schema>.{subtypes, samples, gene_pathways, variants}` (catalog
  and schema are configurable),
- a **Databricks App** hosting the Dash server behind workspace OAuth.

See [`databricks/README.md`](databricks/README.md) for prerequisites, target
environments (`dev` / `prod`), auth modes, and troubleshooting.

## Environment variables

| Variable                 | Default             | Purpose                                                                 |
| ------------------------ | ------------------- | ----------------------------------------------------------------------- |
| `DASHBOARD_DATA_BACKEND` | `csv`               | `csv` (local) or `delta` (Databricks).                                  |
| `DASHBOARD_DATA_DIR`     | `data/toy`          | CSV backend: directory with the four tables.                            |
| `DASHBOARD_HOST`         | `0.0.0.0`           | Interface to bind.                                                      |
| `DASHBOARD_PORT`         | `8050`              | Port to serve on (overridden by `DATABRICKS_APP_PORT` on Databricks Apps). |
| `DASHBOARD_DEBUG`        | `1`                 | Dash debug mode (`0` / `false` to disable).                             |
| `DASHBOARD_CATALOG`      | `main`              | Delta backend: Unity Catalog name.                                      |
| `DASHBOARD_SCHEMA`       | `variant_dashboard` | Delta backend: schema within the catalog.                               |
| `DATABRICKS_HOST`        | —                   | Delta backend: workspace URL.                                           |
| `DATABRICKS_TOKEN`       | —                   | Delta backend (local dev only): personal access token.                  |
| `DATABRICKS_WAREHOUSE_ID`| —                   | Delta backend: SQL Warehouse id.                                        |

## Regenerating the toy dataset

```bash
python scripts/generate_toy_data.py
```

Output is deterministic (seeded); re-running produces the same files.

## Tests

`bash scripts/run_tests.sh` runs `pytest`, which covers:

- **Schema validation** (`tests/test_data_loader.py`): column presence,
  orphan parents, unknown variant classes, sample → subtype foreign keys.
- **Prevalence math** (`tests/test_prevalence.py`): exact counts on a
  hand-rolled three-sample fixture, empty-cohort edge case, and a range
  invariant on the full toy dataset.
- **Dash wiring** (`tests/test_app_smoke.py`): sunburst and prevalence
  figures build for every root, the category filter drops point-mutation
  traces, and the registered callbacks wire the expected component IDs.
- **Databricks loader** (`tests/test_databricks_loader.py`): mock-based
  tests for the Delta loader that reuse the same validation path.
