# Data Schema — Variant Prevalence Dashboard

The dashboard ingests **four CSV (or parquet) tables**. All four must be present
in the data directory (default `data/toy/`, override via `DASHBOARD_DATA_DIR`).

This contract is enforced by `app/data_loader.py` at startup — the app refuses
to launch if required columns are missing or types are wrong.

Encoding: UTF-8. Delimiter: comma. Missing values: empty string. All `_id`
columns are strings (treat as opaque identifiers, not integers).

---

## 1. `subtypes.csv` — disease / subtype hierarchy (drives the sunburst)

One row per node in the disease hierarchy (root + intermediate families +
leaf subtypes).

| Column            | Type   | Nullable | Description                                                                                           |
| ----------------- | ------ | -------- | ----------------------------------------------------------------------------------------------------- |
| `subtype_code`    | str    | no       | Short unique code, e.g. `BALLETV6RUNX1`. Primary key.                                                 |
| `subtype_name`    | str    | no       | Human-readable name, e.g. "B-Cell ALL with ETV6::RUNX1 Fusion".                                       |
| `parent_code`     | str    | yes      | `subtype_code` of the parent node. Empty for root nodes.                                              |
| `root`            | str    | no       | One of `HM`, `BT`, `ST` (Hematopoietic / Brain Tumor / Solid Tumor). Root nodes have `root == code`.  |
| `level`           | int    | no       | 0 = root, 1 = family, 2 = leaf subtype. The dashboard expects three levels.                           |
| `description`     | str    | yes      | Optional long description shown in tooltips.                                                          |

Rules:

- The `(subtype_code)` column is unique.
- `parent_code` must exist as a `subtype_code` row or be empty.
- Each row's `root` must match the root of its ancestor chain.

---

## 2. `samples.csv` — cohort of cases/samples

One row per sample. A subject may have multiple samples; prevalence counts
**subjects once** (de-duplicated via `subject_id`).

| Column         | Type | Nullable | Description                                                  |
| -------------- | ---- | -------- | ------------------------------------------------------------ |
| `sample_id`    | str  | no       | Unique sample identifier. Primary key.                       |
| `subject_id`   | str  | no       | Patient/subject identifier (can repeat across samples).      |
| `subtype_code` | str  | no       | FK → `subtypes.subtype_code`. Must be a **leaf** (level 2).  |
| `sex`          | str  | yes      | `M` / `F` / `U`. Metadata for future filters.                |
| `age_years`    | float| yes      | Age at diagnosis.                                            |

Rules:

- `sample_id` is unique.
- `subtype_code` must resolve to an existing leaf subtype.

---

## 3. `gene_pathways.csv` — gene → pathway assignment

Defines the pathway groups shown on the x-axis of the prevalence chart.

| Column          | Type | Nullable | Description                                                                 |
| --------------- | ---- | -------- | --------------------------------------------------------------------------- |
| `gene`          | str  | no       | Official gene symbol, e.g. `TP53`.                                          |
| `pathway`       | str  | no       | Pathway label, e.g. `Cell Cycle`, `RTK/RAS`, `Epigenetic`, `Transcription`. |
| `gene_list`     | str  | no       | `curated` (cancer-type-specific) or `pan_cancer` (fallback).                |
| `cancer_root`   | str  | yes      | For `curated` rows, the `root` code the curation applies to. Empty for `pan_cancer`.|
| `display_order` | int  | yes      | Optional gene ordering within a pathway (lower = left).                     |

Rules:

- A gene may appear in multiple pathways (rare) or multiple gene-lists.
- When the user selects a subtype whose root has curated genes, `curated` rows
  for that root are used; otherwise the loader falls back to `pan_cancer`.

---

## 4. `variants.csv` — per-variant records (the fact table)

One row per observed variant in a sample.

| Column           | Type | Nullable | Description                                                                                   |
| ---------------- | ---- | -------- | --------------------------------------------------------------------------------------------- |
| `variant_id`     | str  | no       | Unique variant record id.                                                                     |
| `sample_id`      | str  | no       | FK → `samples.sample_id`.                                                                     |
| `gene`           | str  | no       | Affected gene symbol; should match a `gene_pathways.gene` for it to appear in the chart.      |
| `variant_class`  | str  | no       | Controlled vocabulary — see below.                                                            |
| `variant_category`| str | no       | `point_mutation` or `structural_variant`. Derived from `variant_class`; enforced on ingest.   |
| `origin`         | str  | no       | `somatic` or `germline`.                                                                      |

### Controlled vocabulary for `variant_class`

**Point mutations** (`variant_category = point_mutation`):

- `FRAMESHIFT`
- `MISSENSE`
- `NONSENSE`
- `PROTEININS`
- `PROTEINDEL`
- `SPLICE`
- `SPLICE_REGION`
- `EXON`

**Structural variants** (`variant_category = structural_variant`):

- `COPY_LOSS`
- `ITD`
- `FUSION`
- `ENHANCER`
- `INTRAGENIC_DELETION`
- `DELETION`
- `SILENCING`
- `ACTIVATING`

Rules:

- A single sample may have multiple variants in the same gene — they are all
  counted for class/origin breakdowns, but a subject is only counted **once**
  toward the "% of cases" prevalence metric for that gene.
- Unknown `variant_class` values cause ingest to fail (prevents silent
  mis-colouring on the chart).

---

## 5. Derived metrics (computed, not stored)

Given a selection (a `subtype_code`, which may be root/family/leaf), the
dashboard computes:

- **Cohort**: all samples whose subtype is the selected node or any descendant.
  `N_subjects = |unique subject_id in cohort|`, `N_samples = |sample_id|`.
- **Per-gene prevalence**:
  `prevalence_g = |subjects with ≥1 variant in g| / N_subjects`.
- **Variant-class breakdown** for gene `g`:
  proportion of the class among all variants in `g` within the cohort.
- **Origin breakdown** for gene `g`:
  `somatic_frac = somatic variants / all variants` in `g` (within cohort).

---

## 6. Extending with real data

1. Produce the four CSVs with the columns above (extra columns are allowed and
   ignored — missing columns break ingest).
2. Place them in `data/real/` (or any directory).
3. Run the app with `DASHBOARD_DATA_DIR=data/real python -m app.main`.
4. The loader prints a validation report on startup; fix any reported issues.
