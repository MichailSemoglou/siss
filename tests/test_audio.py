"""
Unit and integration tests for the audio passthrough module.

Covers:
  - _has_audio_stream(): ffprobe detection and fallback
  - merge_audio(): happy path, no-ffmpeg, no-audio-source, ffmpeg failure
  - process_media(): no_audio flag forwarding and image/video dispatch
  - apply_duotone / apply_halftone: no_audio kwarg forwarding
  - CLI --no-audio flag: integration with main() (in test_main.py)
"""
import os
import tempfile
import unittest
from unittest import mock

from siss.duotone import apply_duotone
from siss.halftone import apply_halftone
from siss.utils.video_processing import process_media

# ---------------------------------------------------------------------------
# _has_audio_stream
# ---------------------------------------------------------------------------

class TestHasAudioStream(unittest.TestCase):
    """Unit tests for _has_audio_stream()."""

    def test_returns_true_when_audio_stream_present(self):
        from siss.audio import _has_audio_stream

        with mock.patch("siss.audio.shutil.which", return_value="/usr/bin/ffprobe"):
            with mock.patch("siss.audio.subprocess.run") as mock_run:
                mock_run.return_value.stdout = "video\naudio\n"
                mock_run.return_value.returncode = 0
                self.assertTrue(_has_audio_stream("video.mp4"))

    def test_returns_false_when_no_audio_stream(self):
        from siss.audio import _has_audio_stream

        with mock.patch("siss.audio.shutil.which", return_value="/usr/bin/ffprobe"):
            with mock.patch("siss.audio.subprocess.run") as mock_run:
                mock_run.return_value.stdout = "video\n"
                mock_run.return_value.returncode = 0
                self.assertFalse(_has_audio_stream("video.mp4"))

    def test_returns_false_when_ffprobe_not_found(self):
        from siss.audio import _has_audio_stream

        with mock.patch("siss.audio.shutil.which", return_value=None):
            self.assertFalse(_has_audio_stream("video.mp4"))

    def test_returns_false_on_subprocess_timeout(self):
        import subprocess as sp_mod

        from siss.audio import _has_audio_stream

        with mock.patch("siss.audio.shutil.which", return_value="/usr/bin/ffprobe"):
            with mock.patch("siss.audio.subprocess.run",
                            side_effect=sp_mod.TimeoutExpired("ffprobe", 15)):
                self.assertFalse(_has_audio_stream("video.mp4"))

    def test_returns_false_on_os_error(self):
        from siss.audio import _has_audio_stream

        with mock.patch("siss.audio.shutil.which", return_value="/usr/bin/ffprobe"):
            with mock.patch("siss.audio.subprocess.run",
                            side_effect=OSError("broken pipe")):
                self.assertFalse(_has_audio_stream("video.mp4"))


# ---------------------------------------------------------------------------
# merge_audio
# ---------------------------------------------------------------------------

class TestMergeAudio(unittest.TestCase):
    """Unit tests for merge_audio()."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.source = os.path.join(self.tmp.name, "source.mp4")
        self.output = os.path.join(self.tmp.name, "output.mp4")
        open(self.source, "wb").close()
        open(self.output, "wb").close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_skips_when_source_has_no_audio(self):
        from siss.audio import merge_audio

        with mock.patch("siss.audio._has_audio_stream", return_value=False):
            with mock.patch("siss.audio.shutil.which") as mock_which:
                result = merge_audio(self.source, self.output)
        self.assertFalse(result)
        mock_which.assert_not_called()

    def test_warns_when_ffmpeg_not_found(self):
        from siss.audio import merge_audio

        with mock.patch("siss.audio._has_audio_stream", return_value=True):
            with mock.patch("siss.audio.shutil.which", return_value=None):
                with mock.patch("sys.stderr"):
                    result = merge_audio(self.source, self.output)
        self.assertFalse(result)

    def test_merges_audio_successfully(self):
        from siss.audio import merge_audio

        with mock.patch("siss.audio._has_audio_stream", return_value=True):
            with mock.patch("siss.audio.shutil.which", return_value="/usr/bin/ffmpeg"):
                with mock.patch("siss.audio.subprocess.run") as mock_run:
                    with mock.patch("siss.audio.os.replace") as mock_replace:
                        with mock.patch("siss.audio.tempfile.mkstemp",
                                        return_value=(3, "/tmp/.siss_audio_test.mp4")):
                            with mock.patch("siss.audio.os.close"):
                                result = merge_audio(self.source, self.output)
        self.assertTrue(result)
        mock_run.assert_called_once()
        mock_replace.assert_called_once()

    def test_returns_false_on_ffmpeg_failure(self):
        import subprocess as sp_mod

        from siss.audio import merge_audio

        with mock.patch("siss.audio._has_audio_stream", return_value=True):
            with mock.patch("siss.audio.shutil.which", return_value="/usr/bin/ffmpeg"):
                with mock.patch("siss.audio.subprocess.run",
                                side_effect=sp_mod.CalledProcessError(1, "ffmpeg")):
                    with mock.patch("siss.audio.tempfile.mkstemp",
                                    return_value=(3, "/tmp/.siss_audio_test.mp4")):
                        with mock.patch("siss.audio.os.close"):
                            with mock.patch("siss.audio.os.path.exists",
                                            return_value=True):
                                with mock.patch("siss.audio.os.unlink"):
                                    result = merge_audio(self.source, self.output)
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# process_media audio forwarding
# ---------------------------------------------------------------------------

class TestProcessMediaAudio(unittest.TestCase):
    """process_media() calls merge_audio for videos and skips it for images."""

    def test_no_audio_true_skips_merge_for_video(self):
        with mock.patch("siss.utils.video_processing.process_video_frames"):
            with mock.patch("siss.audio.merge_audio") as mock_merge:
                process_media("in.mp4", "out.mp4", lambda f: f, no_audio=True)
        mock_merge.assert_not_called()

    def test_no_audio_false_calls_merge_for_video(self):
        with mock.patch("siss.utils.video_processing.process_video_frames"):
            with mock.patch("siss.utils.video_processing.is_image_file",
                            return_value=False):
                with mock.patch("siss.audio.merge_audio") as mock_merge:
                    process_media("in.mp4", "out.mp4", lambda f: f, no_audio=False)
        mock_merge.assert_called_once_with("in.mp4", "out.mp4")

    def test_default_calls_merge_for_video(self):
        with mock.patch("siss.utils.video_processing.process_video_frames"):
            with mock.patch("siss.utils.video_processing.is_image_file",
                            return_value=False):
                with mock.patch("siss.audio.merge_audio") as mock_merge:
                    process_media("in.mp4", "out.mp4", lambda f: f)
        mock_merge.assert_called_once_with("in.mp4", "out.mp4")

    def test_no_audio_ignored_for_still_image(self):
        with mock.patch("siss.utils.video_processing.process_image"):
            with mock.patch("siss.audio.merge_audio") as mock_merge:
                process_media("in.png", "out.png", lambda f: f, no_audio=False)
        mock_merge.assert_not_called()

    def test_no_audio_true_ignored_for_still_image(self):
        with mock.patch("siss.utils.video_processing.process_image"):
            with mock.patch("siss.audio.merge_audio") as mock_merge:
                process_media("in.png", "out.png", lambda f: f, no_audio=True)
        mock_merge.assert_not_called()


# ---------------------------------------------------------------------------
# apply_duotone / apply_halftone kwargs forwarding
# ---------------------------------------------------------------------------

class TestEffectAudioForwarding(unittest.TestCase):
    """apply_duotone() and apply_halftone() forward no_audio to process_media."""

    def test_apply_duotone_defaults_no_audio_to_false(self):
        with mock.patch("siss.duotone.process_media") as mock_pm:
            apply_duotone("in.mp4", "out.mp4", (255, 0, 0), (0, 255, 255))
        _, kwargs = mock_pm.call_args
        self.assertFalse(kwargs["no_audio"])

    def test_apply_duotone_forwards_no_audio_true(self):
        with mock.patch("siss.duotone.process_media") as mock_pm:
            apply_duotone("in.mp4", "out.mp4", (255, 0, 0), (0, 255, 255),
                          no_audio=True)
        _, kwargs = mock_pm.call_args
        self.assertTrue(kwargs["no_audio"])

    def test_apply_halftone_defaults_no_audio_to_false(self):
        with mock.patch("siss.halftone.process_media") as mock_pm:
            apply_halftone("in.mp4", "out.mp4", 10, (255, 0, 0), (0, 255, 255))
        _, kwargs = mock_pm.call_args
        self.assertFalse(kwargs["no_audio"])

    def test_apply_halftone_forwards_no_audio_true(self):
        with mock.patch("siss.halftone.process_media") as mock_pm:
            apply_halftone("in.mp4", "out.mp4", 10, (255, 0, 0), (0, 255, 255),
                           no_audio=True)
        _, kwargs = mock_pm.call_args
        self.assertTrue(kwargs["no_audio"])


if __name__ == "__main__":
    unittest.main()
