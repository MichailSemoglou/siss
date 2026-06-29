"""
Unit tests for the codec_fix module.

Covers:
  - get_compatible_codec(): codec selection per OS and file extension
  - validate_codec(): real codec validation against temp files
  - get_working_codec(): fallback chain (happy path + failure)
  - create_video_writer(): writer creation and error path

OS-dependent branches are exercised by mocking platform.system().
"""
import os
import unittest
from unittest import mock

import numpy as np

from codec_fix import (
    get_compatible_codec,
    validate_codec,
    get_working_codec,
    create_video_writer,
)


class TestGetCompatibleCodec(unittest.TestCase):
    """Tests for OS- and extension-based codec selection."""

    def _by_os(self, system):
        with mock.patch("codec_fix.platform.system", return_value=system):
            return {
                ".mp4": get_compatible_codec("out.mp4"),
                ".mov": get_compatible_codec("out.mov"),
                ".avi": get_compatible_codec("out.avi"),
                ".mkv": get_compatible_codec("out.mkv"),
                ".wmv": get_compatible_codec("out.wmv"),
                ".unknown": get_compatible_codec("out.xyz"),
            }

    def test_windows_branch(self):
        codecs = self._by_os("Windows")
        self.assertEqual(codecs[".mp4"], "H264")
        self.assertEqual(codecs[".mov"], "H264")
        self.assertEqual(codecs[".avi"], "XVID")
        self.assertEqual(codecs[".mkv"], "H264")
        self.assertEqual(codecs[".wmv"], "WMV2")

    def test_macos_branch(self):
        codecs = self._by_os("Darwin")
        self.assertEqual(codecs[".mp4"], "avc1")
        self.assertEqual(codecs[".mov"], "avc1")
        self.assertEqual(codecs[".avi"], "XVID")
        self.assertEqual(codecs[".mkv"], "avc1")
        self.assertEqual(codecs[".wmv"], "WMV2")

    def test_linux_branch(self):
        codecs = self._by_os("Linux")
        self.assertEqual(codecs[".mp4"], "mp4v")
        self.assertEqual(codecs[".mov"], "mp4v")
        self.assertEqual(codecs[".avi"], "XVID")
        self.assertEqual(codecs[".mkv"], "X264")
        self.assertEqual(codecs[".wmv"], "WMV2")

    def test_unknown_extension_defaults_to_mp4v(self):
        for system in ("Windows", "Darwin", "Linux"):
            codecs = self._by_os(system)
            self.assertEqual(codecs[".unknown"], "mp4v")

    def test_uppercase_extension_normalized(self):
        with mock.patch("codec_fix.platform.system", return_value="Linux"):
            self.assertEqual(get_compatible_codec("OUT.MP4"), "mp4v")

    def test_case_insensitive_extension(self):
        with mock.patch("codec_fix.platform.system", return_value="Darwin"):
            self.assertEqual(get_compatible_codec("clip.MOV"), "avc1")


class TestValidateCodec(unittest.TestCase):
    """Tests for codec validation against real temp files."""

    def test_mp4v_codec_validates_on_most_systems(self):
        # mp4v is broadly available; skip only if the codec is absent.
        result = validate_codec("mp4v", 64, 48, fps=10.0)
        if not result:
            self.skipTest("mp4v codec not available in this environment")
        self.assertTrue(result)

    def test_invalid_codec_returns_bool(self):
        # A garbage fourcc should not produce a working writer.
        # Some OpenCV builds accept almost anything, so we only assert
        # that the function returns a bool (True or False) without raising.
        result = validate_codec("ZZZZ", 64, 48, fps=10.0)
        self.assertIsInstance(result, bool)

    def test_returns_bool(self):
        result = validate_codec("mp4v", 64, 48)
        self.assertIsInstance(result, bool)

    def test_custom_fps(self):
        result = validate_codec("mp4v", 64, 48, fps=24.0)
        if not result:
            self.skipTest("mp4v codec not available")
        self.assertTrue(result)


class TestGetWorkingCodec(unittest.TestCase):
    """Tests for the fallback codec resolution chain."""

    def test_returns_a_working_codec_for_mp4(self):
        # On any reasonable test environment, at least one MP4 codec works.
        try:
            codec = get_working_codec("out.mp4", 64, 48, fps=10.0)
            self.assertIsInstance(codec, str)
            self.assertEqual(len(codec), 4)
        except RuntimeError:
            self.skipTest("No working MP4 codec in this environment")

    def test_raises_runtime_error_when_nothing_works(self):
        # Force every validation to fail -> should raise RuntimeError.
        with mock.patch("codec_fix.validate_codec", return_value=False):
            with self.assertRaises(RuntimeError) as ctx:
                get_working_codec("out.mp4", 64, 48, fps=10.0)
            self.assertIn("No compatible codec", str(ctx.exception))

    def test_uses_primary_codec_when_it_works(self):
        # If the OS-specific primary codec validates, it should be returned
        # directly without trying fallbacks.
        with mock.patch("codec_fix.platform.system", return_value="Linux"):
            with mock.patch("codec_fix.validate_codec", return_value=True) as vc:
                codec = get_working_codec("out.mp4", 64, 48)
        self.assertEqual(codec, "mp4v")  # Linux primary for .mp4
        # validate_codec should have been called exactly once (primary only).
        self.assertEqual(vc.call_count, 1)

    def test_fallback_chain_tried_when_primary_fails(self):
        # On Darwin, the primary codec for .mp4 is 'avc1'. Make it fail,
        # and let the first fallback ('mp4v') succeed.
        call_log = []

        def fake_validate(codec, w, h, fps=30.0):
            call_log.append(codec)
            # 'avc1' (primary) fails; 'mp4v' (first fallback) succeeds.
            return codec == "mp4v"

        with mock.patch("codec_fix.platform.system", return_value="Darwin"):
            with mock.patch("codec_fix.validate_codec", side_effect=fake_validate):
                codec = get_working_codec("out.mp4", 64, 48)
        self.assertEqual(codec, "mp4v")
        # Primary (avc1) + at least one fallback (mp4v) were attempted.
        self.assertGreaterEqual(len(call_log), 2)
        self.assertIn("avc1", call_log)


class TestCreateVideoWriter(unittest.TestCase):
    """Tests for the writer factory."""

    def test_creates_working_writer_for_mp4(self):
        tmp = os.path.join(
            __import__("tempfile").mkdtemp(), "writer_test.mp4"
        )
        try:
            try:
                writer = create_video_writer(tmp, fps=10.0, width=64, height=48)
            except RuntimeError:
                self.skipTest("No working codec in this environment")
            self.assertTrue(writer.isOpened())
            frame = np.zeros((48, 64, 3), dtype=np.uint8)
            writer.write(frame)
            writer.release()
            self.assertTrue(os.path.exists(tmp))
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_raises_runtime_error_when_all_codecs_fail(self):
        with mock.patch("codec_fix.get_working_codec", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                create_video_writer("out.mp4", fps=10.0, width=64, height=48)


if __name__ == "__main__":
    unittest.main()