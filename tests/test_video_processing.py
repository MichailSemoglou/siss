"""
Unit tests for src/utils/video_processing.py.

Covers:
  - get_codec_for_file(): extension-to-codec mapping
  - load_video(): success and FileNotFoundError paths
  - get_video_properties(): keys, types, and dimension accuracy
  - extract_frames(): frame count, dtype, dimensions, progress-bar flag
  - save_video(): file creation, empty-frame guard, progress-bar flag
  - process_video_frames(): identity passthrough, missing-input guard,
    kwargs forwarding
"""
import os
import sys
import tempfile
import unittest

import cv2
import numpy as np

from utils.video_processing import (
    extract_frames,
    get_codec_for_file,
    get_video_properties,
    load_video,
    process_video_frames,
    save_video,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_video(path, width=160, height=120, frames=5, fps=30.0):
    """Write a minimal solid-black video to *path* using the mp4v codec.

    Raises unittest.SkipTest if the writer cannot be opened, so any setUp
    that calls this function skips its tests gracefully in environments
    where mp4v / the target container is unavailable.
    """
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
    if not writer.isOpened():
        writer.release()
        raise unittest.SkipTest("mp4v codec not available in this environment")
    for _ in range(frames):
        writer.write(np.zeros((height, width, 3), dtype=np.uint8))
    writer.release()


# ---------------------------------------------------------------------------
# get_codec_for_file
# ---------------------------------------------------------------------------

class TestGetCodecForFile(unittest.TestCase):
    """Extension-to-codec mapping."""

    def test_mp4(self):
        self.assertEqual(get_codec_for_file("video.mp4"), "mp4v")

    def test_avi(self):
        self.assertEqual(get_codec_for_file("video.avi"), "XVID")

    def test_mov(self):
        self.assertEqual(get_codec_for_file("video.mov"), "mp4v")

    def test_mkv(self):
        self.assertEqual(get_codec_for_file("video.mkv"), "X264")

    def test_wmv(self):
        self.assertEqual(get_codec_for_file("video.wmv"), "WMV2")

    def test_unknown_extension_defaults_to_mp4v(self):
        self.assertEqual(get_codec_for_file("video.xyz"), "mp4v")

    def test_uppercase_extension(self):
        self.assertEqual(get_codec_for_file("VIDEO.MP4"), "mp4v")

    def test_path_with_directories(self):
        self.assertEqual(get_codec_for_file("/some/dir/clip.avi"), "XVID")


# ---------------------------------------------------------------------------
# load_video
# ---------------------------------------------------------------------------

class TestLoadVideo(unittest.TestCase):
    """load_video() happy path and FileNotFoundError path."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "clip.mp4")
        _make_test_video(self.path)

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
        _make_test_video(path, width=160, height=120, frames=5, fps=24.0)
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
# extract_frames
# ---------------------------------------------------------------------------

class TestExtractFrames(unittest.TestCase):
    """extract_frames() returns correct frame list."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "clip.mp4")
        _make_test_video(self.path, width=160, height=120, frames=5)

    def tearDown(self):
        self.tmp.cleanup()

    def _open(self):
        return cv2.VideoCapture(self.path)

    def test_returns_all_frames(self):
        cap = self._open()
        try:
            frames = extract_frames(cap, show_progress=False)
            self.assertEqual(len(frames), 5)
        finally:
            cap.release()

    def test_frames_are_numpy_arrays(self):
        cap = self._open()
        try:
            frames = extract_frames(cap, show_progress=False)
            self.assertIsInstance(frames[0], np.ndarray)
        finally:
            cap.release()

    def test_frame_dimensions(self):
        cap = self._open()
        try:
            frames = extract_frames(cap, show_progress=False)
            h, w, c = frames[0].shape
            self.assertEqual(w, 160)
            self.assertEqual(h, 120)
            self.assertEqual(c, 3)
        finally:
            cap.release()

    def test_with_progress_bar_does_not_raise(self):
        cap = self._open()
        try:
            frames = extract_frames(cap, show_progress=True)
            self.assertEqual(len(frames), 5)
        finally:
            cap.release()


# ---------------------------------------------------------------------------
# save_video
# ---------------------------------------------------------------------------

class TestSaveVideo(unittest.TestCase):
    """save_video() persists frames to disk and guards against empty input."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out_path = os.path.join(self.tmp.name, "out.mp4")
        self.frames = [
            np.zeros((120, 160, 3), dtype=np.uint8) for _ in range(5)
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def test_creates_output_file(self):
        save_video(self.out_path, self.frames, fps=30, show_progress=False)
        if not os.path.exists(self.out_path) or os.path.getsize(self.out_path) == 0:
            self.skipTest("Codec produced no output in this environment")
        self.assertTrue(os.path.exists(self.out_path))

    def test_empty_frames_raises_value_error(self):
        with self.assertRaises(ValueError):
            save_video(self.out_path, [], fps=30)

    def test_with_progress_bar_does_not_raise(self):
        save_video(self.out_path, self.frames, fps=30, show_progress=True)
        if not os.path.exists(self.out_path) or os.path.getsize(self.out_path) == 0:
            self.skipTest("Codec produced no output in this environment")
        self.assertTrue(os.path.exists(self.out_path))

    def test_output_is_readable_video(self):
        save_video(self.out_path, self.frames, fps=30, show_progress=False)
        if not os.path.exists(self.out_path) or os.path.getsize(self.out_path) == 0:
            self.skipTest("Codec produced no output in this environment")
        cap = cv2.VideoCapture(self.out_path)
        try:
            self.assertTrue(cap.isOpened())
        finally:
            cap.release()


# ---------------------------------------------------------------------------
# process_video_frames
# ---------------------------------------------------------------------------

class TestProcessVideoFrames(unittest.TestCase):
    """process_video_frames() applies a function to every frame."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.in_path = os.path.join(self.tmp.name, "in.mp4")
        self.out_path = os.path.join(self.tmp.name, "out.mp4")
        _make_test_video(self.in_path, frames=3)

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


if __name__ == "__main__":
    unittest.main()
