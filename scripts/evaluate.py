# -*- coding: utf-8 -*-
"""Evaluation script comparing detection outputs against benchmark ground truth."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


def normalize_text(text: str) -> str:
    """Normalize text for evaluation comparison."""
    text = text.lower().strip()
    return re.sub(r'\s+', ' ', text)


def load_json(path: str) -> Dict[str, Any]:
    """Load JSON helper."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _word_overlap(text1: str, text2: str) -> float:
    """Word-level Jaccard similarity."""
    w1 = set(text1.split())
    w2 = set(text2.split())
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)


def match_spans(
    gt_annotations: List[Dict[str, Any]],
    detected_spans: List[Dict[str, Any]],
) -> Dict[str, Dict[str, int]]:
    """Match ground truth items with detections."""
    gt_by_type: Dict[str, List[Dict]] = defaultdict(list)
    det_by_type: Dict[str, List[Dict]] = defaultdict(list)

    for ann in gt_annotations:
        gt_by_type[ann["pii_type"]].append(ann)
    for span in detected_spans:
        det_by_type[span["pii_type"]].append(span)

    all_types = set(list(gt_by_type.keys()) + list(det_by_type.keys()))
    results: Dict[str, Dict[str, int]] = {}

    for pii_type in sorted(all_types):
        gt_items = gt_by_type.get(pii_type, [])
        det_items = det_by_type.get(pii_type, [])

        gt_texts = [normalize_text(a["text"]) for a in gt_items]
        det_texts = [normalize_text(s["matched_text"]) for s in det_items]

        matched_gt: Set[int] = set()
        matched_det: Set[int] = set()

        for gi, gt_text in enumerate(gt_texts):
            for di, det_text in enumerate(det_texts):
                if di in matched_det:
                    continue
                match = (
                    gt_text == det_text
                    or gt_text in det_text
                    or det_text in gt_text
                    or _word_overlap(gt_text, det_text) > 0.7
                )
                if match:
                    matched_gt.add(gi)
                    matched_det.add(di)
                    break

        tp = len(matched_gt)
        fn = len(gt_texts) - tp
        fp = len(det_texts) - len(matched_det)
        results[pii_type] = {"TP": tp, "FP": fp, "FN": fn}

    return results


def compute_metrics(results: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, Any]]:
    """Compute Precision, Recall, Accuracy (Jaccard Index) & F1."""
    metrics: Dict[str, Dict[str, Any]] = {}

    for pii_type, counts in results.items():
        tp, fp, fn = counts["TP"], counts["FP"], counts["FN"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        accuracy = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        metrics[pii_type] = {
            "TP": tp, "FP": fp, "FN": fn,
            "Precision": round(precision, 4),
            "Recall": round(recall, 4),
            "Accuracy": round(accuracy, 4),
            "F1": round(f1, 4),
        }

    total_tp = sum(m["TP"] for m in metrics.values())
    total_fp = sum(m["FP"] for m in metrics.values())
    total_fn = sum(m["FN"] for m in metrics.values())
    total_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    total_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    total_acc = total_tp / (total_tp + total_fp + total_fn) if (total_tp + total_fp + total_fn) > 0 else 0.0
    total_f1 = (2 * total_prec * total_rec / (total_prec + total_rec)) if (total_prec + total_rec) > 0 else 0.0

    metrics["OVERALL"] = {
        "TP": total_tp, "FP": total_fp, "FN": total_fn,
        "Precision": round(total_prec, 4),
        "Recall": round(total_rec, 4),
        "Accuracy": round(total_acc, 4),
        "F1": round(total_f1, 4),
    }

    return metrics


def generate_report(metrics: Dict[str, Dict[str, Any]], output_path: str) -> None:
    """Generate Markdown evaluation report."""
    lines = [
        "# PII Redaction — Evaluation Report\n",
        "## Methodology\n",
        "Ground truth was manually annotated from representative PII-dense sections of the KSH International Limited Red Herring Prospectus (~15-20% of document text, covering ~80-90% of PII instances).\n",
        "**Accuracy formula**: Jaccard index = `TP / (TP + FP + FN)`.\n",
        "## Benchmark Results\n",
        "| PII Type | TP | FP | FN | Precision | Recall | Accuracy (Jaccard) | F1 |",
        "|----------|----|----|----|-----------|---------|--------------------|------|",
    ]

    for pii_type in sorted(m for m in metrics if m != "OVERALL"):
        m = metrics[pii_type]
        lines.append(
            f"| {pii_type} | {m['TP']} | {m['FP']} | {m['FN']} | "
            f"{m['Precision']:.2%} | {m['Recall']:.2%} | "
            f"{m['Accuracy']:.2%} | {m['F1']:.2%} |"
        )

    if "OVERALL" in metrics:
        m = metrics["OVERALL"]
        lines.append(
            f"| **OVERALL** | **{m['TP']}** | **{m['FP']}** | **{m['FN']}** | "
            f"**{m['Precision']:.2%}** | **{m['Recall']:.2%}** | "
            f"**{m['Accuracy']:.2%}** | **{m['F1']:.2%}** |"
        )

    report_content = "\n".join(lines)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    print(f"Evaluation report written to: {output_path}")


def main() -> None:
    """CLI evaluation main."""
    parser = argparse.ArgumentParser(description="Evaluate PII Redaction")
    parser.add_argument(
        "--detections", "-d",
        default=str(root_dir / "output" / "detection_log.json"),
    )
    parser.add_argument(
        "--ground-truth", "-g",
        default=str(root_dir / "data" / "ground_truth.json"),
    )
    parser.add_argument(
        "--output", "-o",
        default=str(root_dir / "evaluation_report.md"),
    )
    args = parser.parse_args()

    gt = load_json(args.ground_truth).get("annotations", [])
    det = load_json(args.detections).get("spans", [])

    results = match_spans(gt, det)
    metrics = compute_metrics(results)
    generate_report(metrics, args.output)


if __name__ == "__main__":
    main()
