# Databricks Deployment

This folder converts the local CSV prototype into a Databricks-native
deployment:

| Layer            | Artefact                                  |
| ---------------- | ----------------------------------------- |
| Storage          | Four **Delta tables** in Unity Catalog    |
| Ingestion        | `notebooks/load_toy_to_delta.py` (PySpark) |
| Serving          | **Databricks Apps** (hosted Dash runtime) |
| Orchestration    | Databricks Asset Bundle (`databricks.yml`) |

The application code itself is untouched — the only difference is that
`app/config.py` now supports `DASHBOARD_DATA_BACKEND=delta`, which routes
through `app/databricks_loader.py` instead of the CSV loader. The same
`DataBundle` / `prevalence.py` / chart components are re-used.

---

## Prerequisites

1. **Databricks workspace** with Unity Catalog enabled.
2. A **SQL Warehouse** (serverless recommended) you can use — note its id.
3. **Databricks CLI ≥ 0.220** installed and authenticated:

   ```bash
   # macOS / Linux / WSL
   curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh

   # verify
   databricks --version

   # auth (pick one)
   databricks auth login --host https://<your-workspace>.cloud.databricks.com  # OAuth
   # or
   export DATABRICKS_HOST=https://<your-workspace>.cloud.databricks.com
   export DATABRICKS_TOKEN=dapi***
   ```

4. Permissions you need:
   - `USE CATALOG` + `CREATE SCHEMA` on the destination catalog.
   - `CAN USE` on the SQL Warehouse.
   - Workspace `CAN MANAGE` on Apps (for first-time deploy).

---

## One-shot deployment

From `databricks/`:

```bash
export WAREHOUSE_ID=abcdef1234567890     # your SQL Warehouse id
export CATALOG=main                      # optional, default 'main'
export TARGET=dev                        # or 'prod'

./deploy.sh all
```

`deploy.sh all` runs three steps sequentially:

1. **`init`** — `databricks bundle validate -t $TARGET`
2. **`data`** — deploys + runs the `load_toy_data` job. This reads the four
   CSVs from `../data/toy/` (synced into the workspace by the bundle) and
   writes them as Delta tables in `$CATALOG.$SCHEMA`.
3. **`app`** — deploys the Databricks App (named
   `variant-prevalence-dashboard` by default) and prints its URL.

You can also run each step individually:

```bash
./deploy.sh init
./deploy.sh data
./deploy.sh app
```

---

## What gets created in the workspace

- **Job** `[Dashboard] Load toy data into Delta` — a single notebook task
  that ingests the four CSVs into `$CATALOG.$SCHEMA.{subtypes, samples,
  gene_pathways, variants}`. In `dev` target the schema name is suffixed
  with your short username so multiple developers don't collide.
- **Databricks App** `variant-prevalence-dashboard` — hosts the Dash app.
  The app runtime sets `DATABRICKS_APP_PORT`; `app/config.py` picks it up
  automatically. The bundle configures the app with:
  - `DASHBOARD_DATA_BACKEND=delta`
  - `DASHBOARD_CATALOG`, `DASHBOARD_SCHEMA`
  - `DATABRICKS_WAREHOUSE_ID`
  - OAuth workspace identity (no tokens baked into the image).

---

## Local development against Delta

To run the **same code path locally** against a real workspace (useful for
debugging the Delta loader before deploying):

```bash
export DASHBOARD_DATA_BACKEND=delta
export DATABRICKS_HOST=https://<your-workspace>.cloud.databricks.com
export DATABRICKS_TOKEN=dapi***
export DATABRICKS_WAREHOUSE_ID=abcdef1234567890
export DASHBOARD_CATALOG=main
export DASHBOARD_SCHEMA=variant_dashboard_<you>

python -m app.main
```

---

## Updating the app

Any change to `app/**` requires a new deploy:

```bash
./deploy.sh app
```

Data changes (new CSV content) require re-running the job:

```bash
./deploy.sh data
```

You can also run the notebook ad-hoc from the Workspace UI — the widgets
default to the same arguments the job uses.

---

## Troubleshooting

| Symptom                                             | Fix                                                                            |
| --------------------------------------------------- | ------------------------------------------------------------------------------ |
| `databricks-sql-connector is not installed`         | App env must include `databricks-sql-connector`; check `requirements.txt`.     |
| `SchemaError: ...` at app start-up                  | Re-run the data-load job; validation rules are the same as local.              |
| `DATABRICKS_WAREHOUSE_ID is not set`                | Resource binding missing — redeploy with `WAREHOUSE_ID=... ./deploy.sh app`.   |
| App page loads but shows empty chart                | Confirm the job wrote non-empty tables: `SELECT COUNT(*) FROM $CATALOG.$SCHEMA.variants`. |
| `403 on /sql/1.0/warehouses/...`                    | Grant the app's service principal `CAN USE` on the Warehouse.                  |

See `../plan.md` §4b (Phase 2) for the matching task list.
