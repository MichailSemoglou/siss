"""
Merge the original audio track back into a video rendered by OpenCV.

OpenCV ``VideoWriter`` produces silent output. This module uses ``ffmpeg``
to copy the audio stream from the source file into the rendered video,
avoiding a re-encode of the video track.

Binary resolution
-----------------
The ``ffmpeg`` and ``ffprobe`` executables are located as follows:

1. ``SISS_FFMPEG`` / ``SISS_FFPROBE`` environment variables, if set.
2. The first match on ``PATH`` via :func:`shutil.which`.

This means the caller's environment is trusted for binary selection.
In a server or container context, set the environment variables to pin
the executables to known-good absolute paths.
"""
import logging
import os
import shutil
import subprocess
import tempfile

_log = logging.getLogger(__name__)


def _find_ffprobe() -> str | None:
    """Return the ffprobe executable path.

    Checks ``SISS_FFPROBE`` first, then falls back to PATH.
    """
    return os.environ.get("SISS_FFPROBE") or shutil.which("ffprobe")


def _find_ffmpeg() -> str | None:
    """Return the ffmpeg executable path.

    Checks ``SISS_FFMPEG`` first, then falls back to PATH.
    """
    return os.environ.get("SISS_FFMPEG") or shutil.which("ffmpeg")


def _has_audio_stream(video_path: str) -> bool:
    """
    Return True if *video_path* carries at least one audio stream.

    Probes with ``ffprobe``, resolved via ``SISS_FFPROBE`` or PATH.
    Falls back to False when neither the environment variable nor PATH
    yields a usable binary, so the caller skips the merge rather than
    failing.
    """
    ffprobe = _find_ffprobe()
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
    except (subprocess.TimeoutExpired, OSError) as exc:
        _log.debug("ffprobe probe failed for %r: %s", video_path, exc)
        return False
    return result.returncode == 0 and "audio" in result.stdout


def merge_audio(source_path: str, output_path: str) -> bool:
    """
    Copy the audio track from *source_path* into *output_path*.

    The merge replaces *output_path* with a new file that carries the
    video stream of the original output and the audio stream of the
    source.  No video re-encode happens: both streams are ``-c copy``.

    Returns True when audio was merged successfully, False otherwise.
    Logs a warning when ``ffmpeg`` is unavailable, that is, when neither
    ``SISS_FFMPEG`` nor a PATH lookup resolves to a usable binary.
    """
    if not _has_audio_stream(source_path):
        return False

    ffmpeg = _find_ffmpeg()
    if ffmpeg is None:
        _log.warning(
            "ffmpeg not found; output will be silent. "
            "Install ffmpeg for audio passthrough."
        )
        return False

    tmp_fd, tmp_path = tempfile.mkstemp(
        suffix=os.path.splitext(output_path)[1],
        prefix=".siss_audio_",
        dir=os.path.dirname(output_path) or ".",
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
            stderr=subprocess.PIPE,
        )
        os.replace(tmp_path, output_path)
        return True
    except subprocess.CalledProcessError as e:
        msg = "ffmpeg could not merge audio; output is silent."
        if e.stderr:
            # The last stderr line (capped at 200 chars) is forwarded to
            # the warning so CLI users can diagnose the failure without
            # having to re-run with -vv.  It may contain file-system
            # paths; avoid forwarding this detail in log aggregation
            # pipelines by setting the log level above WARNING.
            detail = e.stderr.decode(errors='replace').strip().rsplit(chr(10), 1)[-1]
            detail = detail[:200] + ("..." if len(detail) > 200 else "")
            msg += f" ({detail})"
        _log.warning(msg)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return False
    except (subprocess.TimeoutExpired, OSError):
        _log.warning("ffmpeg could not merge audio; output is silent.")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return False
