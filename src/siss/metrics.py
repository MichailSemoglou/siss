"""Utilities for benchmarking halftone fidelity and rendering performance."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Sequence

import cv2
import numpy as np


def _to_gray(image: np.ndarray) -> np.ndarray:
    image = np.asarray(image)
    if image.ndim == 2:
        return image.astype(np.float64)
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return gray.astype(np.float64)
    raise ValueError(f"Unsupported image shape: {image.shape}")


def compute_metrics(reference: np.ndarray, candidate: np.ndarray) -> dict[str, float]:
    """Compute a compact fidelity summary for a rendered image.

    Metrics include PSNR, SSIM, MS-SSIM, and a simple mean absolute loss-map
    value derived from the absolute luminance difference.
    """
    ref = _to_gray(reference)
    cand = _to_gray(candidate)
    ref = ref.astype(np.float64)
    cand = cand.astype(np.float64)

    if ref.shape != cand.shape:
        raise ValueError(f"Image shapes differ: {ref.shape} vs {cand.shape}")

    mse = float(np.mean((ref - cand) ** 2))
    psnr = float("inf") if mse == 0.0 else 20.0 * np.log10(255.0 / np.sqrt(mse))

    ssim = _ssim(ref, cand)
    msssim = _msssim(ref, cand)
    loss_mean = float(np.mean(np.abs(ref - cand)))
    return {
        "psnr": psnr,
        "ssim": ssim,
        "msssim": msssim,
        "loss_mean": loss_mean,
    }


def compute_loss_map(reference: np.ndarray, candidate: np.ndarray) -> np.ndarray:
    """Return an 8-bit loss map for a reference/candidate pair."""
    ref = _to_gray(reference)
    cand = _to_gray(candidate)
    ref = ref.astype(np.float64)
    cand = cand.astype(np.float64)

    if ref.shape != cand.shape:
        raise ValueError(f"Image shapes differ: {ref.shape} vs {cand.shape}")

    diff = np.abs(ref - cand).astype(np.uint8)
    return diff


def write_benchmark_report(
    names: Sequence[str],
    references: Sequence[np.ndarray],
    candidates: Sequence[np.ndarray],
    loss_maps: Sequence[np.ndarray],
    output_path: str | Path | None = None,
) -> dict[str, object]:
    """Write a machine-readable benchmark report for a set of renders."""
    if not (len(names) == len(references) == len(candidates) == len(loss_maps)):
        raise ValueError("names, references, candidates, and loss_maps must have the same length")

    items: List[dict[str, object]] = []
    for name, reference, candidate, loss_map in zip(names, references, candidates, loss_maps):
        metrics = compute_metrics(reference, candidate)
        item = {
            "name": name,
            "psnr": metrics["psnr"],
            "ssim": metrics["ssim"],
            "msssim": metrics["msssim"],
            "loss_mean": metrics["loss_mean"],
            "loss_map_mean": float(np.mean(loss_map)),
        }
        for key, value in list(item.items()):
            if isinstance(value, (float, np.floating)) and not np.isfinite(value):
                item[key] = None
        items.append(item)

    report = {
        "generated_by": "siss.metrics.write_benchmark_report",
        "items": items,
    }
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2))
    return report


def _ssim(reference: np.ndarray, candidate: np.ndarray) -> float:
    if reference.shape != candidate.shape:
        raise ValueError(f"Image shapes differ: {reference.shape} vs {candidate.shape}")

    if reference.size == 0:
        return 1.0

    c1 = (0.01 * 255.0) ** 2
    c2 = (0.03 * 255.0) ** 2

    kernel = np.array([[1, 4, 6, 4, 1]], dtype=np.float64)
    kernel = kernel.T @ kernel
    kernel /= kernel.sum()

    def _local_stats(image: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        mu = cv2.filter2D(image, -1, kernel)
        mu_sq = mu * mu
        sigma_sq = cv2.filter2D(image * image, -1, kernel) - mu_sq
        return mu, mu_sq, sigma_sq

    ref_mu, _, ref_var = _local_stats(reference)
    cand_mu, _, cand_var = _local_stats(candidate)
    ref_cand = cv2.filter2D(reference * candidate, -1, kernel)
    cov = ref_cand - ref_mu * cand_mu

    numerator = (2 * ref_mu * cand_mu + c1) * (2 * cov + c2)
    denominator = (ref_mu * ref_mu + cand_mu * cand_mu + c1) * (ref_var + cand_var + c2)

    scores = numerator / denominator
    return float(np.mean(scores))


def _msssim(reference: np.ndarray, candidate: np.ndarray) -> float:
    if reference.shape != candidate.shape:
        raise ValueError(f"Image shapes differ: {reference.shape} vs {candidate.shape}")

    if reference.size == 0:
        return 1.0

    weights = np.array([0.0448, 0.2856, 0.6696], dtype=np.float64)
    refs = [reference]
    cands = [candidate]
    while len(refs) < 3:
        height, width = refs[-1].shape
        next_height = max(1, height // 2)
        next_width = max(1, width // 2)
        if next_height == height and next_width == width:
            break
        next_ref = cv2.resize(refs[-1], (next_width, next_height), interpolation=cv2.INTER_AREA)
        next_cand = cv2.resize(cands[-1], (next_width, next_height), interpolation=cv2.INTER_AREA)
        if next_ref.size == 0 or next_cand.size == 0:
            break
        refs.append(next_ref)
        cands.append(next_cand)

    scores = []
    for ref, cand in zip(refs, cands):
        score = _ssim(ref, cand)
        if not np.isfinite(score):
            score = 0.0
        scores.append(score)

    if len(scores) == 1:
        return float(scores[0])

    weights_used = weights[: len(scores)]
    total_weight = float(weights_used.sum())
    return float(np.dot(weights_used, np.asarray(scores, dtype=np.float64)) / total_weight)
