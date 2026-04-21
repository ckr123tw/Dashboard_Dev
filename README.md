# Variant Prevalence Dashboard

A Plotly/Dash dashboard modelled on the
[St. Jude PeCan Variant Prevalence](https://pecan.stjude.cloud/variants/prevalence)
page, powered by **your own** data via a documented schema. A small toy
dataset ships under `data/toy/` so you can demo and debug immediately.

See [`plan.md`](plan.md) for the full execution plan and TODO list (with
recommended Cursor model per task, to resume if interrupted), and
[`docs/data_schema.md`](docs/data_schema.md) for the data ingestion contract.

## Features (v1)

- **Sunburst** navigator over a 3-level disease hierarchy (root → family → leaf).
- Header stats: N samples · N subjects in the selected cohort.
- **Variant Prevalence by Pathway** chart with three vertically stacked rows:
  1. Variant class proportion (stacked to 100 %).
  2. Variant origin (somatic vs germline).
  3. Per-gene prevalence (% of subjects with ≥1 variant).
- Filter panel: curated vs pan-cancer gene list, point/structural toggle,
  reset button, Export SVG.
- Pathway separators and headers on the chart.

## Quick start (WSL Ubuntu + conda)

1. From PowerShell, run the one-shot setup (installs Miniforge into
   `~/miniforge3` if missing and creates the `pecan-dash` env):

   ```powershell
   wsl -d Ubuntu -- bash /mnt/c/DinMA/Projects/Dashboard_Dev/scripts/setup_wsl_conda.sh
   ```

2. Launch the app:

   ```powershell
   wsl -d Ubuntu -- bash -lc "source ~/miniforge3/etc/profile.d/conda.sh && conda activate pecan-dash && cd /mnt/c/DinMA/Projects/Dashboard_Dev && python -m app.main"
   ```

   Then open <http://localhost:8050> in your Windows browser.

3. Run the test suite:

   ```powershell
   wsl -d Ubuntu -- bash /mnt/c/DinMA/Projects/Dashboard_Dev/scripts/run_tests.sh
   ```

## Repository layout

```
app/                # Dash application
  main.py           # entry point (python -m app.main)
  config.py         # env-driven config + colour palette
  data_loader.py    # CSV/parquet ingest + schema validation
  prevalence.py     # pure-python prevalence math
  components/       # sunburst, prevalence_chart, filters, layout
  assets/styles.css # custom styling
data/toy/           # toy dataset used for demo and tests
docs/data_schema.md # data ingestion contract
scripts/            # setup + smoke scripts (WSL bash)
tests/              # pytest suite (16 tests)
environment.yml     # conda env spec (Python 3.11)
plan.md             # execution plan + TODO list (resume-safe)
```

## Databricks deployment

The same app runs unchanged on **Databricks Apps** backed by **Unity Catalog
Delta tables**. Flip the `DASHBOARD_DATA_BACKEND` env var from `csv` to `delta`
and the app reads from Delta via a SQL Warehouse instead of the local CSVs.

```bash
cd databricks
export WAREHOUSE_ID=<your-sql-warehouse-id>
./deploy.sh all          # validates bundle → loads Delta tables → deploys the App
```

This creates:

- a Databricks **Job** that loads `data/toy/*.csv` into
  `main.variant_dashboard.{subtypes,samples,gene_pathways,variants}` (catalog
  and schema are configurable),
- a **Databricks App** named `variant-prevalence` hosting the Dash server
  behind workspace OAuth.

See [`databricks/README.md`](databricks/README.md) for prerequisites, target
envs (`dev`/`prod`), auth modes, and troubleshooting. The complete task
breakdown (with model assignments) is in [`plan.md`](plan.md) §4b.

## Swapping in your own data

1. Produce the four tables described in
   [`docs/data_schema.md`](docs/data_schema.md) (`subtypes`, `samples`,
   `gene_pathways`, `variants`) as CSV or Parquet.
2. Drop them into a directory, e.g. `data/real/`.
3. Launch with:

   ```powershell
   wsl -d Ubuntu -- bash -lc "source ~/miniforge3/etc/profile.d/conda.sh && conda activate pecan-dash && cd /mnt/c/DinMA/Projects/Dashboard_Dev && DASHBOARD_DATA_DIR=data/real python -m app.main"
   ```

The loader performs strict validation and refuses to start if columns or
controlled-vocabulary values are wrong — the error message tells you what to fix.

## Environment variables

| Variable              | Default        | Purpose                                     |
| --------------------- | -------------- | ------------------------------------------- |
| `DASHBOARD_DATA_BACKEND` | `csv`       | `csv` (local) or `delta` (Databricks).      |
| `DASHBOARD_DATA_DIR`  | `data/toy`     | CSV backend: directory with the four tables.|
| `DASHBOARD_HOST`      | `0.0.0.0`      | Interface to bind.                          |
| `DASHBOARD_PORT`      | `8050`         | Port to serve on (overridden by `DATABRICKS_APP_PORT` on Databricks Apps). |
| `DASHBOARD_DEBUG`     | `1`            | Dash debug mode (`0`/`false` to disable).   |
| `DASHBOARD_CATALOG`   | `main`         | Delta backend: Unity Catalog name.          |
| `DASHBOARD_SCHEMA`    | `variant_dashboard` | Delta backend: schema within catalog.  |
| `DATABRICKS_HOST`     | —              | Delta backend: workspace URL.               |
| `DATABRICKS_TOKEN`    | —              | Delta backend (local dev only): PAT.        |
| `DATABRICKS_WAREHOUSE_ID` | —          | Delta backend: SQL Warehouse id.            |

## Regenerating the toy dataset

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/c/DinMA/Projects/Dashboard_Dev && python3 scripts/generate_toy_data.py"
```

Output is deterministic (seeded); re-running gives the same files.

## Tests

`pytest` covers:

- Schema validation (`tests/test_data_loader.py`): column presence, orphan
  parents, unknown variant classes, sample→subtype FK.
- Prevalence math (`tests/test_prevalence.py`): exact counts on a
  hand-rolled 3-sample fixture, empty-cohort edge case, and a range
  invariant on the full toy dataset.
- Dash wiring (`tests/test_app_smoke.py`): sunburst + prevalence figures
  build for every root, category filter drops point-mutation traces, and
  the registered callbacks wire the expected component IDs.

All 16 tests pass on the prototype.
