# Pediatric-Cancer-style Variant Prevalence Dashboard — Execution Plan

Target reference: https://pecan.stjude.cloud/variants/prevalence (St. Jude PeCan).
Goal: build an interactive dashboard that mirrors the look-and-feel and core
functionality of the PeCan "Variant Prevalence by Pathway" page, powered by
**our own** data (schema defined in `docs/data_schema.md`). A toy dataset is
provided under `data/toy/` for demo + debug purposes.

---

## 1. Tech stack

| Layer              | Choice                                       | Why                                              |
| ------------------ | -------------------------------------------- | ------------------------------------------------ |
| Runtime            | Python 3.11 (conda, in WSL Ubuntu)           | Scientific ecosystem, user-requested             |
| Web framework      | Dash 2.x                                     | Python-native, React under the hood              |
| Charts             | Plotly 5.x                                   | First-class sunburst, stacked bars, SVG export   |
| Data               | pandas, pyarrow                              | Tabular wrangling                                |
| Styling            | dash-bootstrap-components + custom CSS       | Quickest route to PeCan-ish layout               |
| Tests              | pytest, pytest-mock, dash[testing]           | Unit + component smoke tests                     |
| Lint / format      | ruff, black                                  | Keep code tidy                                   |

---

## 2. Feature scope (v1 prototype)

Reproduce the **Variants → Prevalence** page core:

1. **Sunburst navigator** — 3-level hierarchy (root → family → subtype) with
   sample counts. Clicking a slice drives the selection state.
2. **Header summary** — "N samples / M subjects" that update with the selection.
3. **Variant Prevalence by Pathway chart** — vertically grouped stacked bars:
   - X axis grouped by pathway, one bar per gene.
   - Stack 1: variant-class proportion (MISSENSE, FRAMESHIFT, NONSENSE, SPLICE,
     PROTEININS, PROTEINDEL, COPY_LOSS, FUSION, DELETION, SILENCING, ITD,
     ENHANCER, ACTIVATING, INTRAGENIC_DELETION, SPLICE_REGION).
   - Stack 2: variant origin (somatic vs germline).
   - Stack 3: prevalence % (cases w/ ≥1 variant / total cases in selection).
4. **Filter panel** — gene-list toggle (curated vs pan-cancer), reset,
   hide/show, "Export SVG".
5. **Hover tooltips** with per-class variant counts and percentages.

Out of scope for v1 (can be iterated later): ProteinPaint/GenomePaint deep
links, oncoprint, custom gene-list upload, URL-based deep linking.

---

## 3. Repository layout

```
Dashboard_Dev/
├── plan.md                      ← this file
├── README.md
├── environment.yml              ← conda env spec
├── requirements.txt             ← pip fallback
├── pyproject.toml               ← ruff/black/pytest config
├── app/
│   ├── __init__.py
│   ├── main.py                  ← Dash entry point
│   ├── config.py
│   ├── data_loader.py           ← reads CSV/parquet, validates schema
│   ├── prevalence.py            ← core prevalence math
│   ├── components/
│   │   ├── sunburst.py
│   │   ├── prevalence_chart.py
│   │   ├── filters.py
│   │   └── layout.py
│   └── assets/
│       └── styles.css
├── data/
│   └── toy/
│       ├── samples.csv
│       ├── subtypes.csv
│       ├── variants.csv
│       └── gene_pathways.csv
├── docs/
│   └── data_schema.md
└── tests/
    ├── test_data_loader.py
    ├── test_prevalence.py
    └── test_app_smoke.py
```

---

## 4. TODO list (resume-safe)

Check off as each task lands. Each item lists the Cursor model best suited for
the work (based on complexity, not cost).

- [x] **T1. Create conda env in WSL Ubuntu** — install miniforge if absent,
      `conda env create -f environment.yml`, verify `python -c "import dash"`.
      _Model:_ `composer-2-fast` (mechanical shell work).
- [x] **T2. Draft toy datasets + schema doc** — 3 roots (HM/BT/ST), ~8 subtypes
      each, ~300 samples, 4–5 pathways, ~15 genes, ~500 variants. Write
      `docs/data_schema.md` describing every field, types, nullability, and
      the ingestion contract.
      _Model:_ `claude-4.6-sonnet-medium-thinking` (data design + prose).
- [x] **T3. Scaffold Dash app** — `app/main.py`, config, data loader with
      schema validation, baseline layout, run on `0.0.0.0:8050`.
      _Model:_ `gpt-5.3-codex` (code-heavy).
- [x] **T4. Sunburst navigator** — Plotly sunburst from `subtypes.csv` +
      `samples.csv`, click → stores selected subtype path in `dcc.Store`.
      _Model:_ `gpt-5.3-codex`.
- [x] **T5. Prevalence math** — `prevalence.py` functions: `prevalence_per_gene`,
      `variant_class_breakdown`, `origin_breakdown`, filtered by selection.
      _Model:_ `claude-4.6-sonnet-medium-thinking` (correctness-critical).
- [x] **T6. Prevalence chart component** — Plotly grouped stacked bars with
      pathway separators; tooltips; colour map matching PeCan legend.
      _Model:_ `gpt-5.3-codex`.
- [x] **T7. Filter panel** — gene-list dropdown (curated vs pan-cancer),
      reset button, hide/show toggle, Export-SVG button (uses Plotly's native
      image export).
      _Model:_ `composer-2-fast`.
- [x] **T8. Layout + theme** — two-column layout (left filters/sunburst,
      right chart), custom CSS for PeCan-like palette (blues + accent).
      _Model:_ `claude-4.6-sonnet-medium-thinking` (design judgement).
- [x] **T9. Tests** — pytest suite:
        * schema validation against toy data,
        * prevalence math on a deterministic fixture,
        * Dash callback smoke test (selection → chart figure shape).
      Run `pytest -q` and fix failures.
      _Model:_ `claude-4.6-sonnet-medium-thinking`.
- [x] **T10. README + run instructions** — how to activate env in WSL and
      launch the app; how to swap toy data for real data matching the schema.
      _Model:_ `composer-2-fast`.
- [ ] **T11. (Stretch) Architecture review** before shipping — sanity-check
      the whole thing against the PeCan reference screenshots.
      _Model:_ `claude-opus-4-7-thinking-high` (deep reasoning).

---

## 4b. Phase 2 — Databricks conversion & deployment

Phase 2 moves the prototype off local CSVs and onto Databricks infrastructure:
data in **Unity Catalog Delta tables**, app hosted on **Databricks Apps**, and
orchestration via a **Databricks Asset Bundle (DAB)**.

Additional repo layout:

```
databricks/
├── app.yaml                     ← Databricks Apps manifest
├── databricks.yml               ← DAB: apps + jobs + schema resources
├── deploy.sh                    ← one-shot deploy helper
├── notebooks/
│   └── load_toy_to_delta.py     ← ingest CSV → UC Delta tables
└── README.md                    ← step-by-step deploy docs

app/databricks_loader.py         ← Delta-backed DataBundle
```

- [x] **D1. Add data-backend switch** — `DASHBOARD_DATA_BACKEND=csv|delta`
      in `app/config.py`; respect `DATABRICKS_APP_PORT` env var injected by
      Databricks Apps runtime. Keep CSV the default for local dev.
      _Model:_ `composer-2-fast`.
- [x] **D2. Delta loader** — `app/databricks_loader.py` uses
      `databricks-sql-connector` against a SQL Warehouse; returns a
      `DataBundle` with the same schema-validation pipeline as the CSV
      loader. Auth via workspace-injected OAuth in Databricks Apps, or PAT
      locally.
      _Model:_ `claude-4.6-sonnet-medium-thinking` (correctness + security).
- [x] **D3. Data-load notebook** — `databricks/notebooks/load_toy_to_delta.py`
      uses PySpark to read the four CSVs (from a Volume or workspace files)
      and write them as Delta tables into a configurable catalog/schema.
      Idempotent: creates schema if missing, overwrites table content.
      _Model:_ `gpt-5.3-codex`.
- [x] **D4. Databricks Apps manifest** — `databricks/app.yaml` declares the
      start command, dependencies, and environment variables (backend,
      catalog, schema, warehouse id).
      _Model:_ `composer-2-fast`.
- [x] **D5. Asset Bundle** — `databricks/databricks.yml` orchestrates the
      `load_toy_to_delta` job and the Databricks App. Targets: `dev`
      (feature branches / isolated user schema) and `prod`.
      _Model:_ `claude-4.6-sonnet-medium-thinking` (DAB config surface).
- [x] **D6. Deploy helper + docs** — `databricks/deploy.sh` wrapping
      `databricks bundle deploy` / `databricks apps deploy`; step-by-step
      `databricks/README.md` covering workspace config, UC prereqs, data
      upload, bundle deploy, and health checks.
      _Model:_ `composer-2-fast`.
- [x] **D7. Tests** — mock-based unit tests for `databricks_loader` that
      stub the SQL connector cursor, exercising the same validation path as
      the CSV loader. No network calls.
      _Model:_ `claude-4.6-sonnet-medium-thinking`.
- [x] **D8. Env + top-level docs** — add `databricks-sql-connector` and
      `databricks-sdk` to `environment.yml` / `requirements.txt`; new
      "Databricks deployment" section in top-level `README.md` pointing to
      `databricks/README.md`.
      _Model:_ `composer-2-fast`.
- [ ] **D9. (Optional) Workspace smoke test** — run `databricks bundle
      validate` and `databricks apps list` against a real workspace to
      confirm the bundle + manifest are accepted. Requires a Databricks CLI
      profile configured by the user.
      _Model:_ `composer-2-fast`.

---

## 5. Resumption protocol

If the session is disrupted:

1. Re-open `plan.md` and the project todo list.
2. Find the first unchecked `T*` item; that is the next step.
3. Re-run `pytest -q` first — green tests confirm earlier steps still hold.
4. Continue from the next task using its assigned model.

---

## 6. Data ingestion contract (summary)

Real data must be provided as four tables with the schemas defined in
`docs/data_schema.md`. Drop them into `data/real/` and set
`DASHBOARD_DATA_DIR=data/real` (or edit `app/config.py`). The loader performs
schema validation and will refuse to start on mismatch, listing the offending
columns/types.

---

## 7. Model-selection rationale (cheat sheet)

| Task type                                   | Preferred model                           |
| ------------------------------------------- | ----------------------------------------- |
| Deep design, architecture reviews           | `claude-opus-4-7-thinking-high`           |
| Correctness-critical logic, prose, tests    | `claude-4.6-sonnet-medium-thinking`       |
| Bulk code generation / component wiring     | `gpt-5.3-codex`                           |
| Mechanical shell, small edits, READMEs      | `composer-2-fast`                         |
| General-purpose fallback                    | `gpt-5.4-medium`                          |
