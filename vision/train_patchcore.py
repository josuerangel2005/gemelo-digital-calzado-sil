"""Train PatchCore on MVTec AD `leather`, export it and write its metrics.

Usage: python -m vision.train_patchcore

- Downloads MVTec AD `leather` into data/MVTecAD the first time
  (vision.dataset.download) and checks the official image counts.
- Trains only on `leather/train/good`.
- Exports the model to models/patchcore/ (TorchInferencer format).
- Writes reports/vision_patchcore.json with Anomalib's test metrics plus
  per-defect recall, false rejections on good pieces and latency.
"""
import json
import time

import numpy as np
from anomalib.data import MVTecAD
from anomalib.deploy import ExportType, TorchInferencer
from anomalib.engine import Engine
from anomalib.models import Patchcore
from lightning.pytorch import seed_everything

from vision.dataset import CATEGORY, DATA_ROOT, DEFECT_LABELS, category_dir, download
from vision.models import PATCHCORE_DIR, REPORTS_DIR, ROOT, load_patchcore

REPORT_PATH = REPORTS_DIR / "vision_patchcore.json"
SEED = 42


def train() -> dict:
    download()
    seed_everything(SEED, workers=True)
    datamodule = MVTecAD(
        root=DATA_ROOT,
        category=CATEGORY,
        train_batch_size=16,
        eval_batch_size=16,
        num_workers=4,
        seed=SEED,
    )
    model = Patchcore()
    engine = Engine(default_root_dir=ROOT / "results")
    engine.fit(model=model, datamodule=datamodule)
    metrics = engine.test(model=model, datamodule=datamodule)[0]
    engine.export(model=model, export_type=ExportType.TORCH, export_root=PATCHCORE_DIR)
    return {k: float(v) for k, v in metrics.items()}


def evaluate(inferencer: TorchInferencer) -> dict:
    """Runs the exported model on every test image, grouped by folder."""
    test_root = category_dir() / "test"
    per_folder: dict[str, dict] = {}
    latencies: list[float] = []
    for folder in sorted(p for p in test_root.iterdir() if p.is_dir()):
        flagged, scores = 0, []
        images = sorted(folder.glob("*.png"))
        for image in images:
            t0 = time.perf_counter()
            pred = inferencer.predict(image)
            latencies.append((time.perf_counter() - t0) * 1000)
            flagged += int(bool(pred.pred_label.item()))
            scores.append(float(pred.pred_score.item()))
        per_folder[folder.name] = {
            "images": len(images),
            "flagged_as_defect": flagged,
            "rate": flagged / len(images),
            "score_mean": float(np.mean(scores)),
        }
    good = per_folder.pop("good")
    return {
        "false_rejection_rate": good["rate"],
        "good": good,
        "recall_per_defect": {
            DEFECT_LABELS[name]: stats for name, stats in per_folder.items()
        },
        # The first prediction includes model warm-up; report it apart.
        "latency_ms": {
            "first": latencies[0],
            "median": float(np.median(latencies[1:])),
            "p95": float(np.percentile(latencies[1:], 95)),
        },
    }


def main() -> None:
    anomalib_metrics = train()
    inferencer = load_patchcore()
    report = {
        "model": "PatchCore (anomalib 2.7.0, defaults: wide_resnet50_2, layer2+layer3)",
        "dataset": f"MVTec AD / {CATEGORY}",
        "seed": SEED,
        "device": str(inferencer.device),
        "anomalib_test_metrics": anomalib_metrics,
        **evaluate(inferencer),
    }
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
