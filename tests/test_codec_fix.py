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

from siss.codec_fix import (
    create_video_writer,
    get_compatible_codec,
    get_working_codec,
    validate_codec,
)


class TestGetCompatibleCodec(unittest.TestCase):
    """Tests for OS- and extension-based codec selection."""

    def _by_os(self, system):
        with mock.patch("siss.codec_fix.platform.system", return_value=system):
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
        with mock.patch("siss.codec_fix.platform.system", return_value="Linux"):
            self.assertEqual(get_compatible_codec("OUT.MP4"), "mp4v")

    def test_case_insensitive_extension(self):
        with mock.patch("siss.codec_fix.platform.system", return_value="Darwin"):
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

    def test_probe_file_uses_requested_extension(self):
        seen_suffixes = []
        real_mkstemp = __import__("tempfile").mkstemp

        def spy_mkstemp(*args, **kwargs):
            seen_suffixes.append(kwargs.get("suffix"))
            return real_mkstemp(*args, **kwargs)

        for ext in (".avi", ".mov", ".mkv", ".wmv"):
            with mock.patch("siss.codec_fix.tempfile.mkstemp", side_effect=spy_mkstemp):
                with mock.patch("siss.codec_fix.os.close"):
                    validate_codec("mp4v", 64, 48, fps=10.0, ext=ext)
            self.assertEqual(seen_suffixes[-1], ext)


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
        with mock.patch("siss.codec_fix.validate_codec", return_value=False):
            with self.assertRaises(RuntimeError) as ctx:
                get_working_codec("out.mp4", 64, 48, fps=10.0)
            self.assertIn("No compatible codec", str(ctx.exception))

    def test_uses_primary_codec_when_it_works(self):
        # If the OS-specific primary codec validates, it should be returned
        # directly without trying fallbacks.
        with mock.patch("siss.codec_fix.platform.system", return_value="Linux"):
            with mock.patch("siss.codec_fix.validate_codec", return_value=True) as vc:
                codec = get_working_codec("out.mp4", 64, 48)
        self.assertEqual(codec, "mp4v")  # Linux primary for .mp4
        # validate_codec should have been called exactly once (primary only).
        self.assertEqual(vc.call_count, 1)

    def test_fallback_chain_tried_when_primary_fails(self):
        # On Darwin, the primary codec for .mp4 is 'avc1'. Fail every
        # codec except the final MJPG last-resort fallback, so the full
        # fallback chain is exercised, and confirm every call carries the
        # requested container extension.
        call_log = []

        def fake_validate(codec, w, h, fps=30.0, *, ext):
            call_log.append((codec, ext))
            # Only MJPG (the last-resort fallback) succeeds.
            return codec == "MJPG"

        with mock.patch("siss.codec_fix.platform.system", return_value="Darwin"):
            with mock.patch("siss.codec_fix.validate_codec", side_effect=fake_validate):
                codec = get_working_codec("out.mp4", 64, 48)
        self.assertEqual(codec, "MJPG")
        tried_codecs = [c for c, _ in call_log]
        # Primary (avc1), at least one fallback, and MJPG were all attempted.
        self.assertIn("avc1", tried_codecs)
        self.assertGreater(len(tried_codecs), 2)
        self.assertEqual(tried_codecs[-1], "MJPG")
        # Every validate_codec call must receive the requested extension.
        for _, ext in call_log:
            self.assertEqual(ext, ".mp4")

    def test_propagates_output_extension_to_validate_codec(self):
        # get_working_codec should forward the output file's extension to
        # validate_codec for every supported container.
        for ext in (".mp4", ".avi", ".mov", ".mkv", ".wmv"):
            with mock.patch(
                "siss.codec_fix.validate_codec", return_value=True
            ) as vc:
                get_working_codec(f"out{ext}", 64, 48, fps=10.0)
            vc.assert_called_once()
            _, kwargs = vc.call_args
            self.assertEqual(kwargs.get("ext"), ext)


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
        with mock.patch("siss.codec_fix.get_working_codec", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                create_video_writer("out.mp4", fps=10.0, width=64, height=48)


if __name__ == "__main__":
    unittest.main()
