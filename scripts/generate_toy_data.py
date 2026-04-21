"""Generate a small, deterministic toy dataset matching docs/data_schema.md.

Run from repo root:
    python scripts/generate_toy_data.py

Writes four CSVs into data/toy/.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

SEED = 42
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "toy"

POINT_MUT_CLASSES = [
    "FRAMESHIFT",
    "MISSENSE",
    "NONSENSE",
    "PROTEININS",
    "PROTEINDEL",
    "SPLICE",
    "SPLICE_REGION",
    "EXON",
]
SV_CLASSES = [
    "COPY_LOSS",
    "ITD",
    "FUSION",
    "ENHANCER",
    "INTRAGENIC_DELETION",
    "DELETION",
    "SILENCING",
    "ACTIVATING",
]

# ------------------------------------------------------------------
# Disease hierarchy: 3 roots × ~3 families × ~3 leaf subtypes
# ------------------------------------------------------------------
HIERARCHY = {
    "HM": {
        "name": "Hematologic Malignancy",
        "families": {
            "LYMPH": {
                "name": "Lymphoid Neoplasm",
                "leaves": {
                    "BALLETV6RUNX1": "B-Cell ALL with ETV6::RUNX1 Fusion",
                    "BALLHYPER": "B-Cell ALL with Hyperdiploidy",
                    "TALLNOS": "T-Cell ALL, NOS",
                },
            },
            "MYELO": {
                "name": "Myeloid Neoplasm",
                "leaves": {
                    "AMLKMT2A": "AML with KMT2A Rearrangement",
                    "AMLRUNX1": "AML with RUNX1::RUNX1T1 Fusion",
                    "MDS": "Myelodysplastic Syndrome",
                },
            },
        },
    },
    "BT": {
        "name": "Brain Tumor",
        "families": {
            "GLIOMA": {
                "name": "Glioma",
                "leaves": {
                    "HGGH3K27": "High-Grade Glioma, H3 K27-altered",
                    "LGG": "Low-Grade Glioma",
                },
            },
            "EMBR": {
                "name": "Embryonal Tumor",
                "leaves": {
                    "MBSHH": "Medulloblastoma, SHH-activated",
                    "MBWNT": "Medulloblastoma, WNT-activated",
                    "ATRT": "Atypical Teratoid/Rhabdoid Tumor",
                },
            },
        },
    },
    "ST": {
        "name": "Solid Tumor",
        "families": {
            "SARC": {
                "name": "Sarcoma",
                "leaves": {
                    "OS": "Osteosarcoma",
                    "EWS": "Ewing Sarcoma",
                    "RMSALV": "Alveolar Rhabdomyosarcoma",
                },
            },
            "NEUR": {
                "name": "Neural Tumor",
                "leaves": {
                    "NBMYCN": "Neuroblastoma, MYCN-amplified",
                    "NBNOS": "Neuroblastoma, NOS",
                },
            },
        },
    },
}

# ------------------------------------------------------------------
# Genes & pathways
# ------------------------------------------------------------------
PATHWAYS = {
    "Cell Cycle": ["TP53", "CDKN2A", "CDKN2B", "RB1"],
    "RTK/RAS": ["NRAS", "KRAS", "FLT3", "PTPN11"],
    "Transcription": ["RUNX1", "ETV6", "PAX5", "IKZF1"],
    "Epigenetic": ["KMT2A", "EZH2", "DNMT3A"],
    "WNT/SHH": ["CTNNB1", "PTCH1", "SMO"],
}

# Genes that get boosted prevalence in specific roots (gives the chart some signal).
ROOT_HOT_GENES = {
    "HM": {"TP53": 0.25, "ETV6": 0.35, "RUNX1": 0.3, "FLT3": 0.2, "KMT2A": 0.25, "PAX5": 0.2, "IKZF1": 0.22},
    "BT": {"TP53": 0.4, "CDKN2A": 0.3, "CTNNB1": 0.35, "PTCH1": 0.3, "SMO": 0.2, "EZH2": 0.25},
    "ST": {"TP53": 0.5, "RB1": 0.3, "CDKN2A": 0.25, "KRAS": 0.15, "NRAS": 0.1},
}


def class_pool_for(gene: str) -> list[str]:
    """Bias gene → typical variant classes so the toy chart looks plausible."""
    cc_genes = {"TP53", "RB1", "CDKN2A", "CDKN2B"}
    fusion_genes = {"ETV6", "RUNX1", "KMT2A", "PAX5"}
    rtk = {"FLT3", "KRAS", "NRAS", "PTPN11"}
    if gene in cc_genes:
        return (
            ["MISSENSE"] * 5
            + ["NONSENSE"] * 2
            + ["FRAMESHIFT"] * 2
            + ["SPLICE"]
            + ["COPY_LOSS"] * 4
            + ["DELETION"] * 2
        )
    if gene in fusion_genes:
        return ["FUSION"] * 6 + ["MISSENSE"] + ["FRAMESHIFT"] + ["COPY_LOSS"]
    if gene in rtk:
        return ["MISSENSE"] * 6 + ["PROTEININS"] + ["ITD"] * 2 + ["ACTIVATING"]
    return (
        ["MISSENSE"] * 4
        + ["FRAMESHIFT"] * 2
        + ["NONSENSE"]
        + ["SPLICE_REGION"]
        + ["COPY_LOSS"]
        + ["SILENCING"]
    )


def category_of(variant_class: str) -> str:
    return "point_mutation" if variant_class in POINT_MUT_CLASSES else "structural_variant"


# How many samples to create per leaf subtype.
SAMPLES_PER_LEAF = {
    "BALLETV6RUNX1": 40,
    "BALLHYPER": 35,
    "TALLNOS": 25,
    "AMLKMT2A": 20,
    "AMLRUNX1": 18,
    "MDS": 12,
    "HGGH3K27": 22,
    "LGG": 30,
    "MBSHH": 18,
    "MBWNT": 15,
    "ATRT": 10,
    "OS": 25,
    "EWS": 20,
    "RMSALV": 15,
    "NBMYCN": 20,
    "NBNOS": 18,
}


def main() -> None:
    random.seed(SEED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---------------- subtypes.csv ----------------
    subtype_rows: list[dict] = []
    for root_code, root in HIERARCHY.items():
        subtype_rows.append(
            dict(
                subtype_code=root_code,
                subtype_name=root["name"],
                parent_code="",
                root=root_code,
                level=0,
                description=f"Root node for {root['name']}",
            )
        )
        for fam_code, fam in root["families"].items():
            subtype_rows.append(
                dict(
                    subtype_code=fam_code,
                    subtype_name=fam["name"],
                    parent_code=root_code,
                    root=root_code,
                    level=1,
                    description=fam["name"],
                )
            )
            for leaf_code, leaf_name in fam["leaves"].items():
                subtype_rows.append(
                    dict(
                        subtype_code=leaf_code,
                        subtype_name=leaf_name,
                        parent_code=fam_code,
                        root=root_code,
                        level=2,
                        description=leaf_name,
                    )
                )

    _write_csv(
        OUT_DIR / "subtypes.csv",
        subtype_rows,
        ["subtype_code", "subtype_name", "parent_code", "root", "level", "description"],
    )

    # ---------------- samples.csv ----------------
    sample_rows: list[dict] = []
    leaf_to_root: dict[str, str] = {}
    for r in subtype_rows:
        if r["level"] == 2:
            leaf_to_root[r["subtype_code"]] = r["root"]

    next_sample = 1
    next_subject = 1
    for leaf_code, n in SAMPLES_PER_LEAF.items():
        for _ in range(n):
            sid = f"S{next_sample:05d}"
            next_sample += 1
            # ~20% of subjects have 2 samples
            if random.random() < 0.2 and next_subject > 1:
                subj = f"SUBJ{random.randint(1, next_subject - 1):05d}"
            else:
                subj = f"SUBJ{next_subject:05d}"
                next_subject += 1
            sample_rows.append(
                dict(
                    sample_id=sid,
                    subject_id=subj,
                    subtype_code=leaf_code,
                    sex=random.choice(["M", "F", "U"]),
                    age_years=round(random.uniform(0.5, 21.0), 1),
                )
            )

    _write_csv(
        OUT_DIR / "samples.csv",
        sample_rows,
        ["sample_id", "subject_id", "subtype_code", "sex", "age_years"],
    )

    # ---------------- gene_pathways.csv ----------------
    gp_rows: list[dict] = []
    # Pan-cancer: every gene, no root context.
    order = 0
    for pathway, genes in PATHWAYS.items():
        for g in genes:
            gp_rows.append(
                dict(
                    gene=g,
                    pathway=pathway,
                    gene_list="pan_cancer",
                    cancer_root="",
                    display_order=order,
                )
            )
            order += 1
    # Curated per root: include only the "hot" genes for that root.
    for root_code, hot in ROOT_HOT_GENES.items():
        ord2 = 0
        for pathway, genes in PATHWAYS.items():
            for g in genes:
                if g in hot:
                    gp_rows.append(
                        dict(
                            gene=g,
                            pathway=pathway,
                            gene_list="curated",
                            cancer_root=root_code,
                            display_order=ord2,
                        )
                    )
                    ord2 += 1

    _write_csv(
        OUT_DIR / "gene_pathways.csv",
        gp_rows,
        ["gene", "pathway", "gene_list", "cancer_root", "display_order"],
    )

    # ---------------- variants.csv ----------------
    variant_rows: list[dict] = []
    next_vid = 1
    all_genes = [g for genes in PATHWAYS.values() for g in genes]

    for s in sample_rows:
        root = leaf_to_root[s["subtype_code"]]
        hot = ROOT_HOT_GENES.get(root, {})
        for gene in all_genes:
            # Base per-gene probability of being mutated in this sample.
            p = hot.get(gene, 0.03)
            if random.random() > p:
                continue
            # Some samples have multiple variants in the same gene.
            n_variants = random.choices([1, 2, 3], weights=[0.8, 0.17, 0.03])[0]
            for _ in range(n_variants):
                vclass = random.choice(class_pool_for(gene))
                # Germline is rarer; TP53 has elevated germline fraction.
                germline_p = 0.15 if gene == "TP53" else 0.05
                origin = "germline" if random.random() < germline_p else "somatic"
                variant_rows.append(
                    dict(
                        variant_id=f"V{next_vid:06d}",
                        sample_id=s["sample_id"],
                        gene=gene,
                        variant_class=vclass,
                        variant_category=category_of(vclass),
                        origin=origin,
                    )
                )
                next_vid += 1

    _write_csv(
        OUT_DIR / "variants.csv",
        variant_rows,
        ["variant_id", "sample_id", "gene", "variant_class", "variant_category", "origin"],
    )

    print(
        f"wrote {len(subtype_rows)} subtypes, {len(sample_rows)} samples, "
        f"{len(gp_rows)} gene-pathway rows, {len(variant_rows)} variants "
        f"to {OUT_DIR}"
    )


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
