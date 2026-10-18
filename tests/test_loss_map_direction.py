"""Regression tests: the halftone loss map must score faithfully rendered
flat white and flat black as zero loss (they need no mark and a full mark)."""
import numpy as np
import pytest

from siss.halftone import _make_halftone_processor


@pytest.mark.parametrize("value", [0, 255])
def test_flat_extremes_have_zero_loss(value):
    process = _make_halftone_processor(20, (0, 0, 0), (255, 255, 255), loss_map=True)
    frame = np.full((400, 400, 3), value, dtype=np.uint8)
    _, loss = process(frame)
    assert loss.max() == 0


def test_mid_gray_loss_reflects_quantization_only():
    process = _make_halftone_processor(20, (0, 0, 0), (255, 255, 255), loss_map=True)
    frame = np.full((400, 400, 3), 128, dtype=np.uint8)
    _, loss = process(frame)
    # Loss is bounded by one quantization step of the mark-size scale.
    assert 0 < loss.mean() < 255 / 4 + 1
