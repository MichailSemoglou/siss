import cv2
import numpy as np
import pytest

from siss.duotone import _make_duotone_processor
from siss.halftone import _draw_symbols, _grid_means, _make_halftone_processor


def test_grid_means_basic():
    # 4x4 gray image with values 0..150 step 10
    gray = np.array([
        [0, 10, 20, 30],
        [40, 50, 60, 70],
        [80, 90, 100, 110],
        [120, 130, 140, 150]
    ], dtype=np.uint8)
    integral = cv2.integral(gray, sdepth=cv2.CV_64F)
    ys = np.array([0, 2])
    xs = np.array([0, 2])
    means = _grid_means(integral, ys, xs, h=4, w=4)
    expected = np.array([[50.0, 65.0], [110.0, 125.0]])
    np.testing.assert_allclose(means, expected)


def test_grid_means_near_right_edge():
    gray = np.array([
        [10, 20, 30, 40],
        [50, 60, 70, 80],
    ], dtype=np.uint8)
    integral = cv2.integral(gray, sdepth=cv2.CV_64F)
    ys = np.array([0, 1])
    xs = np.array([0, 3])
    means = _grid_means(integral, ys, xs, h=2, w=4)
    np.testing.assert_allclose(means, np.array([[40.0, 60.0], [60.0, 80.0]]))


def test_grid_means_near_bottom_edge():
    gray = np.array([
        [10, 20],
        [30, 40],
        [50, 60],
        [70, 80],
    ], dtype=np.uint8)
    integral = cv2.integral(gray, sdepth=cv2.CV_64F)
    ys = np.array([0, 3])
    xs = np.array([0, 1])
    means = _grid_means(integral, ys, xs, h=4, w=2)
    np.testing.assert_allclose(means, np.array([[35.0, 40.0], [75.0, 80.0]]))


def test_grid_means_single_point():
    gray = np.ones((5, 5), dtype=np.uint8) * 100
    integral = cv2.integral(gray, sdepth=cv2.CV_64F)
    ys = np.array([2])
    xs = np.array([2])
    means = _grid_means(integral, ys, xs, h=5, w=5)
    np.testing.assert_allclose(means, np.array([[100.0]]))


def test_grid_means_non_default_k():
    gray = np.ones((10, 10), dtype=np.uint8) * 50
    integral = cv2.integral(gray, sdepth=cv2.CV_64F)
    ys = np.array([0])
    xs = np.array([0])
    means = _grid_means(integral, ys, xs, h=10, w=10, k=5)
    np.testing.assert_allclose(means, np.array([[50.0]]))


def _mask_to_array(mask):
    return np.array(mask, copy=False)

@pytest.mark.parametrize("symbol_type,expected_zero_coords", [
    ("plus", [(2, 1), (2, 2), (2, 3), (1, 2), (3, 2)]),
    ("dot", [(2, 2), (2, 1), (2, 3), (1, 2), (3, 2)])
])
def test_draw_symbols_plus_and_dot(symbol_type, expected_zero_coords):
    mask = np.full((5, 5), 255, dtype=np.uint8)
    cx = np.array([2])
    cy = np.array([2])
    sizes = np.array([1])
    _draw_symbols(mask, symbol_type, cx, cy, sizes)
    # Verify expected zero positions
    for y, x in expected_zero_coords:
        assert mask[y, x] == 0
    # Verify corners stay untouched
    for y in (0, 4):
        for x in (0, 4):
            assert mask[y, x] == 255

def test_draw_symbols_asterisk_and_slash():
    # Test asterisk
    mask_a = np.full((5, 5), 255, dtype=np.uint8)
    cx = np.array([2])
    cy = np.array([2])
    sizes = np.array([1])
    _draw_symbols(mask_a, "asterisk", cx, cy, sizes)
    # Expected zeroes for asterisk: plus plus two diagonal lines
    expected = [(2, 1), (2, 2), (2, 3), (1, 2), (3, 2), (1, 1), (1, 3), (3, 1), (3, 3)]
    for y, x in expected:
        assert mask_a[y, x] == 0
    # Test slash
    mask_s = np.full((5, 5), 255, dtype=np.uint8)
    _draw_symbols(mask_s, "slash", cx, cy, sizes)
    # Slash draws a diagonal from top‑right to bottom‑left across the cell
    slash_expected = [(1, 3), (2, 2), (3, 1)]
    for y, x in slash_expected:
        assert mask_s[y, x] == 0
    # Ensure other positions remain 255
    assert mask_s[0, 0] == 255
    assert mask_s[4, 4] == 255


def test_draw_symbols_empty_sizes():
    mask = np.full((5, 5), 255, dtype=np.uint8)
    cx = np.array([], dtype=np.intp)
    cy = np.array([], dtype=np.intp)
    sizes = np.array([], dtype=np.intp)
    _draw_symbols(mask, "plus", cx, cy, sizes)
    np.testing.assert_array_equal(mask, np.full((5, 5), 255, dtype=np.uint8))


def test_draw_symbols_multi_size():
    mask = np.full((15, 15), 255, dtype=np.uint8)
    cx = np.array([3, 11], dtype=np.intp)
    cy = np.array([3, 11], dtype=np.intp)
    sizes = np.array([1, 2], dtype=np.intp)
    _draw_symbols(mask, "plus", cx, cy, sizes)
    assert mask[3, 2] == 0 and mask[3, 3] == 0 and mask[3, 4] == 0
    assert mask[2, 3] == 0 and mask[4, 3] == 0
    assert mask[11, 9] == 0 and mask[11, 13] == 0
    assert mask[9, 11] == 0 and mask[13, 11] == 0
    assert mask[0, 0] == 255 and mask[14, 14] == 255


def test_draw_symbols_asterisk_edge():
    mask = np.full((5, 5), 255, dtype=np.uint8)
    cx = np.array([1], dtype=np.intp)
    cy = np.array([1], dtype=np.intp)
    sizes = np.array([2], dtype=np.intp)
    _draw_symbols(mask, "asterisk", cx, cy, sizes)
    assert mask[1, 1] == 0
    assert mask[2, 2] == 0


def test_draw_symbols_slash_edge():
    mask = np.full((5, 5), 255, dtype=np.uint8)
    cx = np.array([3], dtype=np.intp)
    cy = np.array([3], dtype=np.intp)
    sizes = np.array([2], dtype=np.intp)
    _draw_symbols(mask, "slash", cx, cy, sizes)
    assert mask[3, 2] == 0
    assert mask[2, 3] == 0


def test_halftone_processor_narrow_image():
    frame = np.zeros((100, 3, 3), dtype=np.uint8)
    frame[50, 1, :] = 255
    processor = _make_halftone_processor(10, (0, 0, 0), (255, 255, 255),
                                         symbol_type='plus', grid_type='square')
    result = processor(frame)
    assert result.shape == frame.shape
    assert result.dtype == np.uint8


def test_halftone_processor_negative_symbol_size_raises():
    with pytest.raises(ValueError):
        _make_halftone_processor(-5, (0, 0, 0), (255, 255, 255))


def test_duotone_frame_black_white():
    # 2x2 frame with black, white, mid‑gray, dark‑gray
    frame = np.array([
        [[0, 0, 0], [255, 255, 255]],
        [[128, 128, 128], [64, 64, 64]]
    ], dtype=np.uint8)
    processor = _make_duotone_processor((0, 0, 0), (255, 255, 255))
    result = processor(frame)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    expected = np.stack([gray] * 3, axis=-1)
    np.testing.assert_array_equal(result, expected)


def test_duotone_frame_custom_colors():
    # Single pixel mid‑gray
    frame = np.full((1, 1, 3), 128, dtype=np.uint8)
    processor = _make_duotone_processor((255, 0, 0), (0, 0, 255))
    result = processor(frame)
    norm = 128 / 255.0
    # color1 (red) reversed to BGR = (0, 0, 255)
    # color2 (blue) reversed to BGR = (255, 0, 0)
    expected = np.round((1 - norm) * np.array([0, 0, 255]) + norm * np.array([255, 0, 0]))
    expected = expected.astype(np.uint8).reshape((1, 1, 3))
    np.testing.assert_array_equal(result, expected)


@pytest.mark.parametrize("symbol_type,expected_zeros", [
    (
        "asterisk",
        frozenset({
            (5, 5), (5, 7), (5, 9),
            (6, 6), (6, 7), (6, 8),
            (7, 5), (7, 6), (7, 7), (7, 8), (7, 9),
            (8, 6), (8, 7), (8, 8),
            (9, 5), (9, 7), (9, 9),
        }),
    ),
    (
        "slash",
        frozenset({
            (5, 9), (6, 8), (7, 7), (8, 6), (9, 5),
        }),
    ),
])
def test_edge_vs_bulk_pixel_consistency(symbol_type, expected_zeros):
    """
    Interior symbols use the bulk drawer; edge symbols use the per-cell
    edge drawer.  Drawing a size-2 symbol at (7, 7) on a 10x10 mask
    exercises the bulk path only.  Verify the rendered pixels match
    the expected pattern produced by the bulk drawers.
    """
    mask = np.full((10, 10), 255, dtype=np.uint8)
    cx = np.array([7], dtype=np.intp)
    cy = np.array([7], dtype=np.intp)
    sizes = np.array([2], dtype=np.intp)
    _draw_symbols(mask, symbol_type, cx, cy, sizes)

    actual_zeros = frozenset((int(r), int(c)) for r, c in zip(*np.where(mask == 0)))
    assert (7, 7) in actual_zeros, f"{symbol_type} center pixel should be zeroed"
    assert actual_zeros == expected_zeros, (
        f"{symbol_type} zeroed coordinates mismatch.\n"
        f"  Expected: {sorted(expected_zeros)}\n"
        f"  Got:      {sorted(actual_zeros)}"
    )
