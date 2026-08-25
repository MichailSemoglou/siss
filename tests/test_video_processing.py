"""
Unit tests for src/siss/utils/video_processing.py.

Covers:
  - is_image_file(): extension detection
  - process_image(): output creation, missing-input guard, kwargs forwarding
  - load_video(): success and FileNotFoundError paths
  - get_video_properties(): keys, types, and dimension accuracy
  - process_video_frames(): identity passthrough, missing-input guard,
    kwargs forwarding
  - process_media(): extension-based dispatch and kwargs forwarding
"""
import os
import tempfile
import unittest
from unittest import mock

import cv2
import numpy as np

from siss.utils.video_processing import (
    _safe_int,
    extract_frame,
    get_video_properties,
    is_image_file,
    load_video,
    process_image,
    process_media,
    process_video_frames,
    save_frame,
)
from tests.helpers import make_test_video


def _write_marker_video(path, frames, marked_index, marker_color):
    """Write a synthetic video with one identifiable marker frame."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, 30.0, (160, 120))
    if not writer.isOpened():
        writer.release()
        raise unittest.SkipTest("mp4v codec not available in this environment")

    for index in range(frames):
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        if index == marked_index:
            frame[20:40, 20:40] = marker_color
        writer.write(frame)

    writer.release()


# ---------------------------------------------------------------------------
# is_image_file
# ---------------------------------------------------------------------------

class TestIsImageFile(unittest.TestCase):
    """is_image_file() detects still-image extensions."""

    def test_png_is_image(self):
        self.assertTrue(is_image_file("photo.png"))

    def test_uppercase_png_is_image(self):
        self.assertTrue(is_image_file("photo.PNG"))

    def test_mp4_is_not_image(self):
        self.assertFalse(is_image_file("clip.mp4"))

    def test_no_extension_is_not_image(self):
        self.assertFalse(is_image_file("clip"))


# ---------------------------------------------------------------------------
# process_image
# ---------------------------------------------------------------------------

class TestProcessImage(unittest.TestCase):
    """process_image() applies a function to a still image."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.in_path = os.path.join(self.tmp.name, "in.png")
        self.out_path = os.path.join(self.tmp.name, "out.png")
        image = np.zeros((120, 160, 3), dtype=np.uint8)
        cv2.imwrite(self.in_path, image)

    def tearDown(self):
        self.tmp.cleanup()

    def test_identity_function_produces_output_image(self):
        process_image(self.in_path, self.out_path, lambda f: f)
        self.assertTrue(os.path.exists(self.out_path))
        output = cv2.imread(self.out_path)
        self.assertIsNotNone(output)
        self.assertEqual(output.shape, (120, 160, 3))

    def test_nonexistent_input_raises_file_not_found(self):
        missing = os.path.join(self.tmp.name, "never_created.png")
        with self.assertRaises(FileNotFoundError):
            process_image(missing, self.out_path, lambda f: f)

    def test_kwargs_are_forwarded_to_function(self):
        received = {}

        def capture_kwargs(frame, **kw):
            received.update(kw)
            return frame

        process_image(self.in_path, self.out_path, capture_kwargs, alpha=0.5, tag="test")
        self.assertEqual(received.get("alpha"), 0.5)
        self.assertEqual(received.get("tag"), "test")

    def test_unwritable_output_raises_runtime_error(self):
        """A missing output directory causes cv2.imwrite to fail."""
        bad_path = os.path.join(self.tmp.name, "missing_dir", "out.png")
        with self.assertRaises(RuntimeError):
            process_image(self.in_path, bad_path, lambda f: f)


# ---------------------------------------------------------------------------
# load_video
# ---------------------------------------------------------------------------

class TestLoadVideo(unittest.TestCase):
    """load_video() happy path and FileNotFoundError path."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "clip.mp4")
        make_test_video(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_returns_video_capture_object(self):
        cap = load_video(self.path)
        try:
            self.assertIsInstance(cap, cv2.VideoCapture)
            self.assertTrue(cap.isOpened())
        finally:
            cap.release()

    def test_nonexistent_path_raises_file_not_found(self):
        missing = os.path.join(self.tmp.name, "never_created.mp4")
        with self.assertRaises(FileNotFoundError):
            load_video(missing)


# ---------------------------------------------------------------------------
# get_video_properties
# ---------------------------------------------------------------------------

class TestGetVideoProperties(unittest.TestCase):
    """get_video_properties() returns the expected keys and correct values."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        path = os.path.join(self.tmp.name, "clip.mp4")
        make_test_video(path, width=160, height=120, frames=5, fps=24.0)
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            self.cap.release()
            raise unittest.SkipTest("Could not open test video for reading")

    def tearDown(self):
        self.cap.release()
        self.tmp.cleanup()

    def test_contains_all_required_keys(self):
        props = get_video_properties(self.cap)
        for key in ("fps", "width", "height", "frame_count"):
            self.assertIn(key, props)

    def test_width_is_correct(self):
        props = get_video_properties(self.cap)
        self.assertEqual(props["width"], 160)

    def test_height_is_correct(self):
        props = get_video_properties(self.cap)
        self.assertEqual(props["height"], 120)

    def test_frame_count_is_int(self):
        props = get_video_properties(self.cap)
        self.assertIsInstance(props["frame_count"], int)

    def test_fps_is_positive(self):
        props = get_video_properties(self.cap)
        self.assertGreater(props["fps"], 0)

    def test_frame_count_is_non_negative(self):
        props = get_video_properties(self.cap)
        self.assertGreaterEqual(props["frame_count"], 0)


# ---------------------------------------------------------------------------
# process_video_frames
# ---------------------------------------------------------------------------

class TestProcessVideoFrames(unittest.TestCase):
    """process_video_frames() applies a function to every frame."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.in_path = os.path.join(self.tmp.name, "in.mp4")
        self.out_path = os.path.join(self.tmp.name, "out.mp4")
        make_test_video(self.in_path, frames=3)

    def tearDown(self):
        self.tmp.cleanup()

    def test_identity_function_produces_output_file(self):
        try:
            process_video_frames(self.in_path, self.out_path, lambda f: f)
            self.assertTrue(os.path.exists(self.out_path))
        except (cv2.error, RuntimeError):
            self.skipTest("Codec not available in this environment")

    def test_nonexistent_input_raises_file_not_found(self):
        missing = os.path.join(self.tmp.name, "never_created.mp4")
        with self.assertRaises(FileNotFoundError):
            process_video_frames(
                missing, self.out_path, lambda f: f
            )

    def test_kwargs_are_forwarded_to_function(self):
        """Extra **kwargs must be passed through to the processing function."""
        received = {}

        def capture_kwargs(frame, **kw):
            received.update(kw)
            return frame

        try:
            process_video_frames(
                self.in_path,
                self.out_path,
                capture_kwargs,
                alpha=0.5,
                tag="test",
            )
            self.assertEqual(received.get("alpha"), 0.5)
            self.assertEqual(received.get("tag"), "test")
        except (cv2.error, RuntimeError):
            self.skipTest("Codec not available in this environment")

    def test_processing_function_receives_numpy_array(self):
        """The frame passed to the processing function must be a numpy array."""
        frame_types = []

        def record_type(frame):
            frame_types.append(type(frame))
            return frame

        try:
            process_video_frames(self.in_path, self.out_path, record_type)
            self.assertEqual(len(frame_types), 3, "record_type was never called")
            self.assertTrue(
                all(t is np.ndarray for t in frame_types),
                f"Expected ndarray frames, got: {frame_types}",
            )
        except (cv2.error, RuntimeError):
            self.skipTest("Codec not available in this environment")


# ---------------------------------------------------------------------------
# process_media
# ---------------------------------------------------------------------------

class TestProcessMedia(unittest.TestCase):
    """process_media() dispatches on the output path extension."""

    def test_image_extension_routes_to_process_image(self):
        with mock.patch(
            "siss.utils.video_processing.process_image"
        ) as image_fn, mock.patch(
            "siss.utils.video_processing.process_video_frames"
        ) as video_fn:
            process_media("in.png", "out.png", lambda f: f)
        image_fn.assert_called_once()
        video_fn.assert_not_called()

    def test_preview_frame_writes_single_output_image(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "clip.mp4")
            output_path = os.path.join(tmpdir, "preview.png")
            make_test_video(input_path, frames=5)

            process_media(input_path, output_path, lambda frame: frame, preview_frame=2)

            self.assertTrue(os.path.exists(output_path))
            output = cv2.imread(output_path)
            self.assertIsNotNone(output)
            self.assertEqual(output.shape[0], 120)
            self.assertEqual(output.shape[1], 160)

    def test_preview_frame_ignores_split_direction(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "clip.mp4")
            preview_output = os.path.join(tmpdir, "preview.png")
            make_test_video(input_path, frames=5)

            process_media(
                input_path,
                os.path.join(tmpdir, "out.mov"),
                lambda frame: frame,
                preview_frame=2,
                preview_output_path=preview_output,
                split_direction="vertical",
            )

            self.assertTrue(os.path.exists(preview_output))

    def test_preview_frame_ignores_loss_map_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "clip.mp4")
            preview_output = os.path.join(tmpdir, "preview.png")
            make_test_video(input_path, frames=5)

            process_media(
                input_path,
                os.path.join(tmpdir, "out.mov"),
                lambda frame: frame,
                preview_frame=2,
                preview_output_path=preview_output,
                loss_map_path=os.path.join(tmpdir, "loss.png"),
            )

            self.assertTrue(os.path.exists(preview_output))


class TestExtractFrame(unittest.TestCase):
    """extract_frame() selects a single frame from a video input."""

    def test_middle_frame_is_selected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "clip.mp4")
            _write_marker_video(input_path, frames=5, marked_index=2, marker_color=[0, 255, 0])

            frame = extract_frame(input_path, "middle")

            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(frame.shape[:2], (120, 160))
            self.assertGreaterEqual(int(frame[20, 20, 1]), 200)
            self.assertLessEqual(int(frame[20, 20, 0]), 50)

    def test_numeric_string_frame_is_selected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "clip.mp4")
            _write_marker_video(input_path, frames=60, marked_index=48, marker_color=[255, 0, 0])

            frame = extract_frame(input_path, "48")

            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(frame.shape[:2], (120, 160))
            self.assertGreaterEqual(int(frame[20, 20, 0]), 200)
            self.assertLessEqual(int(frame[20, 20, 1]), 50)

    def test_video_extension_routes_to_process_video_frames(self):
        with mock.patch(
            "siss.utils.video_processing.process_image"
        ) as image_fn, mock.patch(
            "siss.utils.video_processing.process_video_frames"
        ) as video_fn:
            process_media("in.mp4", "out.mp4", lambda f: f)
        video_fn.assert_called_once()
        image_fn.assert_not_called()

    def test_kwargs_are_forwarded(self):
        with mock.patch(
            "siss.utils.video_processing.process_video_frames"
        ) as video_fn:
            process_media("in.mp4", "out.mp4", lambda f: f, alpha=0.5)
        self.assertEqual(video_fn.call_args[1].get("alpha"), 0.5)


class TestSaveFrame(unittest.TestCase):
    """save_frame() writes a raw video frame to an image path."""

    def test_writes_selected_frame_unprocessed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "clip.mp4")
            output_path = os.path.join(tmpdir, "frame.png")
            _write_marker_video(input_path, frames=5, marked_index=2, marker_color=[0, 255, 0])

            save_frame(input_path, 2, output_path)

            saved = cv2.imread(output_path)
            self.assertIsNotNone(saved)
            self.assertEqual(saved.shape[:2], (120, 160))
            self.assertGreaterEqual(int(saved[30, 30, 1]), 200)
            self.assertLessEqual(int(saved[30, 30, 0]), 50)

    def test_middle_selector_writes_image(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "clip.mp4")
            output_path = os.path.join(tmpdir, "frame.png")
            make_test_video(input_path, frames=5)

            save_frame(input_path, "middle", output_path)

            self.assertTrue(os.path.isfile(output_path))
            saved = cv2.imread(output_path)
            self.assertIsNotNone(saved)
            self.assertEqual(saved.shape[:2], (120, 160))

    def test_rejects_non_image_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "clip.mp4")
            make_test_video(input_path, frames=5)

            with self.assertRaises(ValueError):
                save_frame(input_path, 0, os.path.join(tmpdir, "frame.mp4"))


class TestSafeInt(unittest.TestCase):
    """_safe_int() graceful-degradation edge cases."""

    def test_normal_value(self):
        self.assertEqual(_safe_int(42.0), 42)

    def test_inf_returns_zero(self):
        self.assertEqual(_safe_int(float('inf')), 0)

    def test_nan_returns_zero(self):
        self.assertEqual(_safe_int(float('nan')), 0)

    def test_negative_returns_zero(self):
        self.assertEqual(_safe_int(-1.0), 0)

    def test_zero_returns_zero(self):
        self.assertEqual(_safe_int(0.0), 0)

    def test_negative_inf_returns_zero(self):
        self.assertEqual(_safe_int(float('-inf')), 0)


class TestSplitView(unittest.TestCase):
    """Tests for --split-view feature in process_image and process_video_frames."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.tmp.name, "input.png")
        self.output_path = os.path.join(self.tmp.name, "output.png")
        h, w = 60, 80
        self.original = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
        cv2.imwrite(self.input_path, self.original)

    def tearDown(self):
        self.tmp.cleanup()

    def _identity(self, frame):
        return frame

    def test_vertical_split_preserves_dimensions(self):
        process_image(self.input_path, self.output_path, self._identity,
                       split_direction="vertical")
        result = cv2.imread(self.output_path)
        self.assertEqual(result.shape, self.original.shape)

    def test_horizontal_split_preserves_dimensions(self):
        process_image(self.input_path, self.output_path, self._identity,
                       split_direction="horizontal")
        result = cv2.imread(self.output_path)
        self.assertEqual(result.shape, self.original.shape)

    def test_vertical_full_split_doubles_width(self):
        process_image(self.input_path, self.output_path, self._identity,
                       split_direction="vertical-full")
        result = cv2.imread(self.output_path)
        self.assertEqual(result.shape[0], self.original.shape[0])
        self.assertEqual(result.shape[1], self.original.shape[1] * 2)

    def test_horizontal_full_split_doubles_height(self):
        process_image(self.input_path, self.output_path, self._identity,
                       split_direction="horizontal-full")
        result = cv2.imread(self.output_path)
        self.assertEqual(result.shape[0], self.original.shape[0] * 2)
        self.assertEqual(result.shape[1], self.original.shape[1])

    def test_vertical_split_left_half_is_original(self):
        process_image(self.input_path, self.output_path, self._identity,
                       split_direction="vertical")
        result = cv2.imread(self.output_path)
        w = self.original.shape[1]
        half = w // 2
        np.testing.assert_array_equal(result[:, :half], self.original[:, :half])

    def test_horizontal_split_top_half_is_original(self):
        process_image(self.input_path, self.output_path, self._identity,
                       split_direction="horizontal")
        result = cv2.imread(self.output_path)
        h = self.original.shape[0]
        half = h // 2
        np.testing.assert_array_equal(result[:half, :], self.original[:half, :])

    def test_no_split_produces_same_dimensions(self):
        process_image(self.input_path, self.output_path, self._identity)
        result = cv2.imread(self.output_path)
        self.assertEqual(result.shape, self.original.shape)

    def test_invalid_split_direction_raises(self):
        with self.assertRaises(ValueError):
            process_image(self.input_path, self.output_path, self._identity,
                          split_direction="diagonal")


class TestVideoSplitView(unittest.TestCase):
    """Tests for --split-view feature in process_video_frames."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.in_path = os.path.join(self.tmp.name, "in.mp4")
        self.out_path = os.path.join(self.tmp.name, "out.mp4")
        make_test_video(self.in_path, width=160, height=120, frames=3, gradient=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _identity(self, frame):
        return frame

    def _invert(self, frame):
        return cv2.bitwise_not(frame)

    def test_vertical_split_preserves_dimensions(self):
        try:
            process_video_frames(self.in_path, self.out_path, self._invert,
                                  split_direction="vertical")
            cap = cv2.VideoCapture(self.out_path)
            self.assertTrue(cap.isOpened())
            ret, frame = cap.read()
            self.assertTrue(ret)
            self.assertEqual(frame.shape[0], 120)
            self.assertEqual(frame.shape[1], 160)
            # Left half is the original gradient (dark at top); right half is
            # the inverted gradient (bright at top).
            w = frame.shape[1] // 2
            left_top_mean = float(frame[:30, :w].mean())
            right_top_mean = float(frame[:30, w:].mean())
            self.assertLess(
                left_top_mean + 50, right_top_mean,
                f"Left (original) top rows mean {left_top_mean:.1f} should be "
                f"at least 50 units darker than right (inverted) top rows mean "
                f"{right_top_mean:.1f}",
            )
            cap.release()
        except (cv2.error, RuntimeError):
            self.skipTest("Codec not available in this environment")

    def test_horizontal_split_preserves_dimensions(self):
        try:
            process_video_frames(self.in_path, self.out_path, self._invert,
                                  split_direction="horizontal")
            cap = cv2.VideoCapture(self.out_path)
            self.assertTrue(cap.isOpened())
            ret, frame = cap.read()
            self.assertTrue(ret)
            self.assertEqual(frame.shape[0], 120)
            self.assertEqual(frame.shape[1], 160)
            # Top half is the original gradient (dark at top); bottom half is
            # the inverted gradient.
            h = frame.shape[0] // 2
            orig_top_mean = float(frame[:10].mean())
            inv_top_mean = float(frame[h:h + 10].mean())
            self.assertLess(
                orig_top_mean + 50, inv_top_mean,
                f"Original top rows mean {orig_top_mean:.1f} should be at least "
                f"50 units darker than bottom-half top rows mean {inv_top_mean:.1f}",
            )
            cap.release()
        except (cv2.error, RuntimeError):
            self.skipTest("Codec not available in this environment")

    def test_vertical_full_split_doubles_width(self):
        try:
            process_video_frames(self.in_path, self.out_path, self._invert,
                                  split_direction="vertical-full")
            cap = cv2.VideoCapture(self.out_path)
            self.assertTrue(cap.isOpened())
            ret, frame = cap.read()
            self.assertTrue(ret)
            self.assertEqual(frame.shape[0], 120)
            self.assertEqual(frame.shape[1], 320)
            cap.release()
        except (cv2.error, RuntimeError):
            self.skipTest("Codec not available in this environment")

    def test_horizontal_full_split_doubles_height(self):
        try:
            process_video_frames(self.in_path, self.out_path, self._invert,
                                  split_direction="horizontal-full")
            cap = cv2.VideoCapture(self.out_path)
            self.assertTrue(cap.isOpened())
            ret, frame = cap.read()
            self.assertTrue(ret)
            self.assertEqual(frame.shape[0], 240)
            self.assertEqual(frame.shape[1], 160)
            cap.release()
        except (cv2.error, RuntimeError):
            self.skipTest("Codec not available in this environment")

    def test_vertical_full_split_skip_concat_uses_already_doubled_frame(self):
        def already_doubled(frame):
            return np.concatenate((frame, frame), axis=1)

        process_video_frames(
            self.in_path,
            self.out_path,
            already_doubled,
            split_direction="vertical-full",
            _skip_split_concat=True,
        )
        cap = cv2.VideoCapture(self.out_path)
        self.assertTrue(cap.isOpened())
        try:
            ret, frame = cap.read()
            self.assertTrue(ret)
            self.assertEqual(frame.shape[0], 120)
            self.assertEqual(frame.shape[1], 320)
        finally:
            cap.release()

    def test_horizontal_full_split_skip_concat_uses_already_doubled_frame(self):
        def already_doubled(frame):
            return np.concatenate((frame, frame), axis=0)

        process_video_frames(
            self.in_path,
            self.out_path,
            already_doubled,
            split_direction="horizontal-full",
            _skip_split_concat=True,
        )
        cap = cv2.VideoCapture(self.out_path)
        self.assertTrue(cap.isOpened())
        try:
            ret, frame = cap.read()
            self.assertTrue(ret)
            self.assertEqual(frame.shape[0], 240)
            self.assertEqual(frame.shape[1], 160)
        finally:
            cap.release()

    def test_loss_map_path_uses_grayscale_tuple_and_releases_writers(self):
        class RecordingWriter:
            def __init__(self):
                self.frames = []
                self.released = False

            def write(self, frame):
                self.frames.append(frame)

            def release(self):
                self.released = True

        created_writers = []

        def fake_create_video_writer(path, fps, width, height):
            writer = RecordingWriter()
            created_writers.append((path, fps, width, height, writer))
            return writer

        def processor(frame):
            loss_map = np.zeros((frame.shape[0], frame.shape[1]), dtype=np.uint8)
            return frame, loss_map

        loss_path = os.path.join(self.tmp.name, "loss.mp4")
        with mock.patch("siss.utils.video_processing.create_video_writer", side_effect=fake_create_video_writer):
            process_video_frames(
                self.in_path,
                self.out_path,
                processor,
                loss_map_path=loss_path,
            )

        self.assertEqual(len(created_writers), 2)
        self.assertEqual(created_writers[0][0], self.out_path)
        self.assertEqual(created_writers[1][0], loss_path)
        self.assertEqual(created_writers[0][4].frames[0].shape, (120, 160, 3))
        self.assertEqual(created_writers[1][4].frames[0].shape, (120, 160, 3))
        self.assertTrue(created_writers[0][4].released)
        self.assertTrue(created_writers[1][4].released)

    def test_no_split_preserves_dimensions(self):
        try:
            process_video_frames(self.in_path, self.out_path, self._identity)
            cap = cv2.VideoCapture(self.out_path)
            self.assertTrue(cap.isOpened())
            ret, frame = cap.read()
            self.assertTrue(ret)
            self.assertEqual(frame.shape[0], 120)
            self.assertEqual(frame.shape[1], 160)
            cap.release()
        except (cv2.error, RuntimeError):
            self.skipTest("Codec not available in this environment")

    def test_invalid_split_direction_raises(self):
        with self.assertRaises(ValueError):
            process_video_frames(self.in_path, self.out_path, self._identity,
                                 split_direction="diagonal")


if __name__ == "__main__":
    unittest.main()
