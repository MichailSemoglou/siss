"""
Merge the original audio track back into a video rendered by OpenCV.

OpenCV ``VideoWriter`` produces silent output. This module uses ``ffmpeg``
to copy the audio stream from the source file into the rendered video,
avoiding a re-encode of the video track.
"""
import os
import shutil
import subprocess
import tempfile


def _has_audio_stream(video_path: str) -> bool:
    """
    Return True if *video_path* carries at least one audio stream.

    Probes with ``ffprobe`` when available; falls back to False when
    ``ffprobe`` is not on ``PATH``, so the caller skips the merge rather
    than failing.
    """
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return False
    try:
        result = subprocess.run(
            [
                ffprobe, "-v", "error",
                "-show_entries", "stream=codec_type",
                "-of", "csv=p=0",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return "audio" in result.stdout


def merge_audio(source_path: str, output_path: str) -> bool:
    """
    Copy the audio track from *source_path* into *output_path*.

    The merge replaces *output_path* with a new file that carries the
    video stream of the original output and the audio stream of the
    source.  No video re-encode happens: both streams are ``-c copy``.

    Returns True when audio was merged successfully, False otherwise.
    Prints a warning to stderr when ``ffmpeg`` is not on ``PATH``.
    """
    if not _has_audio_stream(source_path):
        return False

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        import sys
        print(
            "Warning: ffmpeg not found; output will be silent. "
            "Install ffmpeg for audio passthrough.",
            file=sys.stderr,
        )
        return False

    tmp_fd, tmp_path = tempfile.mkstemp(
        suffix=os.path.splitext(output_path)[1], prefix=".siss_audio_"
    )
    os.close(tmp_fd)

    try:
        subprocess.run(
            [
                ffmpeg, "-v", "error",
                "-i", source_path,
                "-i", output_path,
                "-c:v", "copy",
                "-c:a", "copy",
                "-map", "0:a",
                "-map", "1:v",
                "-y",
                tmp_path,
            ],
            check=True,
            timeout=120,
        )
        os.replace(tmp_path, output_path)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        import sys
        print(
            "Warning: ffmpeg could not merge audio; output is silent.",
            file=sys.stderr,
        )
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return False
