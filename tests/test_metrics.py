import json

import numpy as np

from siss.metrics import compute_metrics, write_benchmark_report


def test_psnr_is_infinite_for_identical_images():
    image = np.arange(16, dtype=np.uint8).reshape(4, 4)
    metrics = compute_metrics(image, image)
    assert np.isinf(metrics["psnr"])


def test_ssim_is_one_for_identical_images():
    image = np.arange(16, dtype=np.uint8).reshape(4, 4)
    metrics = compute_metrics(image, image)
    assert metrics["ssim"] == 1.0


def test_write_benchmark_report_writes_json(tmp_path):
    reference = np.zeros((4, 4), dtype=np.uint8)
    render = np.full((4, 4), 128, dtype=np.uint8)
    loss_map = np.full((4, 4), 64, dtype=np.uint8)
    output_path = tmp_path / "benchmark.json"

    report = write_benchmark_report(
        ["demo"],
        [reference],
        [render],
        [loss_map],
        output_path=output_path,
    )

    assert len(report["items"]) == 1
    assert report["items"][0]["name"] == "demo"
    assert np.isfinite(report["items"][0]["psnr"])
    payload = json.loads(output_path.read_text())
    assert payload["items"][0]["name"] == "demo"
