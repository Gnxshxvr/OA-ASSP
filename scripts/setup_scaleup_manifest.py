"""Generate frozen 48-graph experiment configuration, split manifest, and machine-readable metadata."""

from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List
import yaml

def generate_frozen_manifests():
    configs_dir = Path("configs")
    configs_dir.mkdir(parents=True, exist_ok=True)

    master_seed = 42
    base_seed = 100
    families = ["random", "geometric", "scale_free"]
    sizes = [40, 80, 160, 320]
    degrees = [6.0, 12.0]
    seeds_per_cfg = 2
    q_values = [1, 10, 50, 100, 500]
    algorithms = ["Dijkstra", "Bidirectional Dijkstra", "A*"]
    feature_tiers = ["Tier 0", "Tier 0+1", "Tier 0+1+2"]
    warmup_count = 1
    timing_repetitions = 3
    bootstrap_B = 1000
    selector_hyperparameters = {
        "max_depth": 4,
        "min_samples_leaf": 3,
        "random_state": 42,
        "criterion": "gini",
        "epsilon": 0.05,
    }

    # Generate all 48 graph entries deterministically
    graphs_list = []
    cfg_idx = 0
    for fam in families:
        fam_prefix = "scalefree" if fam == "scale_free" else fam
        for V in sizes:
            for D in degrees:
                for s_i in range(seeds_per_cfg):
                    cfg_idx += 1
                    seed = base_seed + cfg_idx
                    gid = f"{fam_prefix}_V{V}_D{int(round(D))}_s{seed}"
                    graphs_list.append({
                        "cfg_idx": cfg_idx,
                        "graph_id": gid,
                        "family": fam,
                        "V": V,
                        "D": D,
                        "seed": seed,
                        "s_i": s_i,
                    })

    assert len(graphs_list) == 48, f"Expected 48 graphs, got {len(graphs_list)}"

    # Design the exact deterministic split:
    # 8 Test graphs:
    # 2 per size (one D=6, one D=12), covering all 3 families (3 random, 3 geometric, 2 scale-free)
    # V=40:  D=6 -> random (s102),     D=12 -> geometric (s120)
    # V=80:  D=6 -> scalefree (s138),  D=12 -> random (s108)
    # V=160: D=6 -> geometric (s126),  D=12 -> scalefree (s144)
    # V=320: D=6 -> random (s114),     D=12 -> geometric (s132)
    test_graph_ids = {
        "random_V40_D6_s102",
        "geometric_V40_D12_s120",
        "scalefree_V80_D6_s138",
        "random_V80_D12_s108",
        "geometric_V160_D6_s126",
        "scalefree_V160_D12_s144",
        "random_V320_D6_s114",
        "geometric_V320_D12_s132",
    }

    # 8 Validation graphs:
    # 2 per size (one D=6, one D=12), covering all 3 families (2 random, 3 geometric, 3 scale-free)
    # V=40:  D=6 -> scalefree (s134),  D=12 -> random (s104)
    # V=80:  D=6 -> geometric (s122),  D=12 -> scalefree (s140)
    # V=160: D=6 -> random (s110),     D=12 -> geometric (s128)
    # V=320: D=6 -> geometric (s130),  D=12 -> scalefree (s148)
    val_graph_ids = {
        "scalefree_V40_D6_s134",
        "random_V40_D12_s104",
        "geometric_V80_D6_s122",
        "scalefree_V80_D12_s140",
        "random_V160_D6_s110",
        "geometric_V160_D12_s128",
        "geometric_V320_D6_s130",
        "scalefree_V320_D12_s148",
    }

    # Train graphs: remaining 32 graphs
    train_graph_ids = set()
    for g in graphs_list:
        gid = g["graph_id"]
        if gid not in test_graph_ids and gid not in val_graph_ids:
            train_graph_ids.add(gid)

    # Assign split attribute
    for g in graphs_list:
        gid = g["graph_id"]
        if gid in test_graph_ids:
            g["split"] = "test"
        elif gid in val_graph_ids:
            g["split"] = "validation"
        else:
            g["split"] = "train"

    # Required assertions
    assert len(train_graph_ids) == 32, f"Expected 32 train graphs, got {len(train_graph_ids)}"
    assert len(val_graph_ids) == 8, f"Expected 8 val graphs, got {len(val_graph_ids)}"
    assert len(test_graph_ids) == 8, f"Expected 8 test graphs, got {len(test_graph_ids)}"
    assert len(train_graph_ids & val_graph_ids) == 0, "Overlap between train and val"
    assert len(train_graph_ids & test_graph_ids) == 0, "Overlap between train and test"
    assert len(val_graph_ids & test_graph_ids) == 0, "Overlap between val and test"

    # Compute deterministic configuration hash over the full sorted specification
    hash_payload = {
        "master_seed": master_seed,
        "families": families,
        "sizes": sizes,
        "degrees": degrees,
        "seeds_per_cfg": seeds_per_cfg,
        "q_values": q_values,
        "algorithms": algorithms,
        "feature_tiers": feature_tiers,
        "timing_repetitions": timing_repetitions,
        "warmup_count": warmup_count,
        "bootstrap_B": bootstrap_B,
        "selector_hyperparameters": selector_hyperparameters,
        "graphs": [
            {"graph_id": g["graph_id"], "family": g["family"], "V": g["V"], "D": g["D"], "seed": g["seed"], "split": g["split"]}
            for g in sorted(graphs_list, key=lambda x: x["graph_id"])
        ],
    }
    canonical_json = json.dumps(hash_payload, sort_keys=True)
    config_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    experiment_id = f"scaleup_48g_{config_hash[:12]}"

    # 1. Save CSV Split Manifest
    csv_path = configs_dir / "graph_split_manifest_48g.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["graph_id", "family", "V", "D", "seed", "split"])
        writer.writeheader()
        for g in sorted(graphs_list, key=lambda x: (x["family"], x["V"], x["D"], x["seed"])):
            writer.writerow({
                "graph_id": g["graph_id"],
                "family": g["family"],
                "V": g["V"],
                "D": g["D"],
                "seed": g["seed"],
                "split": g["split"],
            })

    # 2. Save YAML Configuration
    yaml_dict = {
        "experiment_id": experiment_id,
        "configuration_hash": config_hash,
        "seeds": {
            "master_seed": master_seed,
            "base_seed": base_seed,
            "query_seed_policy": "graph_seed + 2000",
            "selector_seed": 42,
            "bootstrap_seed": 4001,
        },
        "graphs": {
            "families": families,
            "sizes": sizes,
            "degrees": degrees,
            "seeds_per_cfg": seeds_per_cfg,
            "total_count": 48,
            "train_count": 32,
            "val_count": 8,
            "test_count": 8,
        },
        "queries": {
            "count_per_graph": 500,
            "q_checkpoints": q_values,
        },
        "solvers": {
            "algorithms": algorithms,
            "timing": {
                "warmup_runs": warmup_count,
                "repetitions": timing_repetitions,
                "timeout_seconds": 30.0,
            },
        },
        "features": {
            "tiers": feature_tiers,
        },
        "selector": {
            "model": "DecisionTreeClassifier",
            "hyperparameters": selector_hyperparameters,
        },
        "bootstrap": {
            "samples": bootstrap_B,
            "confidence_level": 0.95,
        },
    }
    yaml_path = configs_dir / "experiment_scaleup_48g.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(yaml_dict, f, default_flow_style=False, sort_keys=False)

    # 3. Save Machine-Readable Experiment Manifest JSON
    manifest_json = {
        "experiment_id": experiment_id,
        "configuration_hash": config_hash,
        "master_seed": master_seed,
        "graph_seeds": [g["seed"] for g in graphs_list],
        "query_seed_policy": "graph_seed + 2000",
        "train_graph_ids": sorted(list(train_graph_ids)),
        "validation_graph_ids": sorted(list(val_graph_ids)),
        "test_graph_ids": sorted(list(test_graph_ids)),
        "graph_families": families,
        "V_values": sizes,
        "D_values": degrees,
        "Q_values": q_values,
        "algorithms": algorithms,
        "feature_tiers": feature_tiers,
        "timing_repetitions": timing_repetitions,
        "warmup_count": warmup_count,
        "bootstrap_B": bootstrap_B,
        "selector_hyperparameters": selector_hyperparameters,
        "graph_manifest_file": str(csv_path.as_posix()),
        "config_file": str(yaml_path.as_posix()),
    }
    json_path = configs_dir / "experiment_manifest_48g.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(manifest_json, f, indent=2)

    print(f"Generated:")
    print(f"  - {csv_path} ({len(graphs_list)} rows)")
    print(f"  - {yaml_path}")
    print(f"  - {json_path}")
    print(f"Configuration Hash: {config_hash}")
    print(f"Test Graph IDs ({len(test_graph_ids)}): {sorted(list(test_graph_ids))}")
    print(f"Validation Graph IDs ({len(val_graph_ids)}): {sorted(list(val_graph_ids))}")
    print(f"Train Graph IDs ({len(train_graph_ids)}): {sorted(list(train_graph_ids))}")

if __name__ == "__main__":
    generate_frozen_manifests()
