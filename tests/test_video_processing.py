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
    get_video_properties,
    is_image_file,
    load_video,
    process_image,
    process_media,
    process_video_frames,
)
from tests.helpers import make_test_video


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


if __name__ == "__main__":
    unittest.main()
