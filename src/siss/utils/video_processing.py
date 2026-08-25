"""
Utility functions for video processing operations.

This module provides helper functions for common video operations like
loading videos and saving processed results.
"""
import logging
import os
from typing import Any, Callable, Dict, Optional, Union

import cv2
import numpy as np
from tqdm import tqdm

from ..codec_fix import create_video_writer

_log = logging.getLogger(__name__)


def load_video(video_path: str) -> cv2.VideoCapture:
    """
    Load a video file and return a VideoCapture object.

    Args:
        video_path (str): Path to the video file

    Returns:
        cv2.VideoCapture: OpenCV VideoCapture object

    Raises:
        FileNotFoundError: If the video file cannot be opened
    """
    video_capture = cv2.VideoCapture(video_path)
    if not video_capture.isOpened():
        raise FileNotFoundError(f"Cannot open video file: {video_path}")
    return video_capture


def get_video_properties(video_capture: cv2.VideoCapture) -> Dict[str, Any]:
    """
    Get properties of a video.

    Args:
        video_capture (cv2.VideoCapture): OpenCV VideoCapture object

    Returns:
        dict: Dictionary with video properties (fps, width, height, frame_count)
    """
    raw_fps = video_capture.get(cv2.CAP_PROP_FPS)
    fps = raw_fps if raw_fps > 0 else 30.0
    return {
        'fps': fps,
        'width': _safe_int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'height': _safe_int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        'frame_count': _safe_int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT)),
    }


def _read_frame_at(cap: cv2.VideoCapture, frame_index: int) -> tuple[bool, Optional[np.ndarray]]:
    """Seek to a frame index and return the frame if it can be read."""
    if not cap.set(cv2.CAP_PROP_POS_FRAMES, float(frame_index)):
        return False, None
    ret, frame = cap.read()
    if ret:
        return True, frame
    return False, None


def extract_frame(video_path: str, frame_selector: Union[int, str]) -> np.ndarray:
    """Extract a single frame from a video input.

    ``frame_selector`` accepts either an integer frame index, a numeric string
    like ``"48"``, or the strings ``"middle"``, ``"first"``, and ``"last"``.
    For keyframe-only codecs, the function falls back to a simple grab loop
    from the start of the video until the requested frame is reached.
    """
    cap = load_video(video_path)
    try:
        props = get_video_properties(cap)
        frame_count = props["frame_count"]
        if isinstance(frame_selector, str):
            selector = frame_selector.strip().lower()
            if selector == "middle":
                target = max(0, (frame_count - 1) // 2) if frame_count > 0 else 0
            elif selector in {"first", "start", "0"}:
                target = 0
            elif selector in {"last", "end"}:
                target = max(0, frame_count - 1) if frame_count > 0 else 0
            else:
                try:
                    target = int(selector)
                except ValueError as exc:
                    raise ValueError(f"Unsupported preview frame selector: {frame_selector!r}") from exc
        elif isinstance(frame_selector, int):
            target = frame_selector
        else:
            raise TypeError("frame_selector must be an int, a numeric string, or 'middle'")

        if target < 0:
            raise ValueError("preview frame index must be non-negative")
        if frame_count > 0 and target >= frame_count:
            target = max(0, frame_count - 1)

        ret, frame = _read_frame_at(cap, target)
        if ret and frame is not None:
            return frame

        cap.set(cv2.CAP_PROP_POS_FRAMES, 0.0)
        for _ in range(target):
            ret, _ = cap.read()
            if not ret:
                raise RuntimeError(f"Could not read preview frame {target} from {video_path}")
        ret, frame = cap.read()
        if not ret or frame is None:
            raise RuntimeError(f"Could not read preview frame {target} from {video_path}")
        return frame
    finally:
        cap.release()


def _safe_int(value: float) -> int:
    """Convert a numeric property from cv2.VideoCapture to an int.

    Corrupted files or unusual backends can return inf or nan, which
    would crash on ``int()`` conversion.  Falls back to 0 in those edge
    cases so the pipeline degrades gracefully rather than raising.
    """
    if not np.isfinite(value) or value < 0:
        return 0
    return int(value)


IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}


def is_image_file(file_path: str) -> bool:
    """
    Return True if *file_path* has a still-image extension.

    The check is case-insensitive and covers the formats OpenCV's
    ``cv2.imread``/``cv2.imwrite`` commonly handle.
    """
    return os.path.splitext(file_path)[1].lower() in IMAGE_EXTENSIONS


def save_frame(video_path: str, frame_selector: Union[int, str], output_path: str) -> None:
    """
    Extract a single frame from a video and save it as a still image.

    The frame is written exactly as decoded; no effect is applied.
    ``frame_selector`` accepts the same values as :func:`extract_frame`.

    Args:
        video_path (str): Path to the input video
        frame_selector (int or str): Frame index, numeric string, or
            'first', 'middle', 'last'
        output_path (str): Image path to write; the extension picks
            the format (``.png``, ``.jpg``, ...)

    Raises:
        ValueError: If output_path is not a still-image path
        RuntimeError: If the frame cannot be read or written
    """
    if not is_image_file(output_path):
        raise ValueError(
            f"Extracted-frame output must be an image file, got {output_path!r}"
        )
    frame = extract_frame(video_path, frame_selector)
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    success = cv2.imwrite(output_path, frame)
    if not success:
        raise RuntimeError(f"Failed to write image file: {output_path}")
    _log.info("Extracted frame saved to %s", output_path)


def _validate_split_direction(split_direction: Optional[str]) -> None:
    """Raise ValueError for unsupported split_direction values."""
    valid = (None, "vertical", "horizontal", "vertical-full", "horizontal-full")
    if split_direction not in valid:
        raise ValueError(
            f"split_direction must be one of {', '.join(repr(v) for v in valid if v is not None)}, "
            f"or None; got {split_direction!r}"
        )


def split_view_stitch(main_frame: np.ndarray, alt_frame: np.ndarray, split_direction: str) -> np.ndarray:
    """
    Stitch two processed frames side-by-side or top-and-bottom.

    Returns a single frame where the ``alt_frame`` occupies the left or
    top portion and the ``main_frame`` occupies the right or bottom
    portion. For ``-full`` modes the full frames are concatenated.
    """
    if split_direction == "vertical":
        w = main_frame.shape[1]
        half = w // 2
        return np.concatenate(
            (alt_frame[:, :half], main_frame[:, half:]), axis=1
        )
    elif split_direction == "horizontal":
        h = main_frame.shape[0]
        half = h // 2
        return np.concatenate(
            (alt_frame[:half, :], main_frame[half:, :]), axis=0
        )
    elif split_direction == "vertical-full":
        return np.concatenate((alt_frame, main_frame), axis=1)
    elif split_direction == "horizontal-full":
        return np.concatenate((alt_frame, main_frame), axis=0)
    else:
        raise ValueError(f"Unsupported split_direction: {split_direction!r}")


def process_image(image_path: str, output_path: str, process_function: Callable[..., Any], **kwargs: Any) -> None:
    """
    Process a still image by applying a function to it.

    Args:
        image_path (str): Path to the input image
        output_path (str): Path where the processed image will be saved
        process_function (callable): Function to apply to the image
            The function should take a frame and return a processed frame
        **kwargs: Additional arguments. Recognised keys:
            split_direction (str): 'vertical', 'horizontal',
                'vertical-full', or 'horizontal-full'. The -full modes
                double one output dimension (width for vertical-full,
                height for horizontal-full).
            loss_map_path (str): path for an optional loss-map image
    """
    frame = cv2.imread(image_path)
    if frame is None:
        raise FileNotFoundError(f"Cannot open image file: {image_path}")

    split = kwargs.pop("split_direction", None)
    loss_map_path = kwargs.pop("loss_map_path", None)
    skip_split_concat = kwargs.pop("_skip_split_concat", False)
    _validate_split_direction(split)
    processed = process_function(frame, **kwargs)
    if isinstance(processed, tuple):
        processed_frame, loss_frame = processed
    else:
        processed_frame = processed
        loss_frame = None
    if split and not skip_split_concat:
        if split.endswith("-full"):
            axis = 1 if split.startswith("vertical") else 0
            processed_frame = np.concatenate(
                (frame, processed_frame), axis=axis
            )
        elif split == "vertical":
            w = frame.shape[1]
            half = w // 2
            processed_frame = np.concatenate(
                (frame[:, :half], processed_frame[:, half:]), axis=1
            )
        else:
            h = frame.shape[0]
            half = h // 2
            processed_frame = np.concatenate(
                (frame[:half, :], processed_frame[half:, :]), axis=0
            )
    success = cv2.imwrite(output_path, processed_frame)
    if not success:
        raise RuntimeError(f"Failed to write image file: {output_path}")
    if loss_frame is not None and loss_map_path:
        success = cv2.imwrite(loss_map_path, loss_frame)
        if not success:
            raise RuntimeError(f"Failed to write loss map: {loss_map_path}")
    _log.info("Processed image saved to %s", output_path)


def process_video_frames(video_path: str, output_path: str, process_function: Callable[..., Any], split_direction: Optional[str] = None, **kwargs: Any) -> None:
    """
    Process a video by applying a function to each frame.

    Args:
        video_path (str): Path to the input video
        output_path (str): Path where processed video will be saved
        process_function (callable): Function to apply to each frame.
            When a ``loss_map_path`` kwarg is present, the function may
            return a ``(rendered, loss_map)`` tuple instead of a single
            frame.
        split_direction (str): 'vertical', 'horizontal', 'vertical-full',
            or 'horizontal-full'. The -full modes double one output
            dimension.
        **kwargs: Recognised keys include ``loss_map_path`` (str).

    Example:
        def grayscale(frame):
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        process_video_frames('input.mp4', 'output.mp4', grayscale)
    """
    loss_map_path = kwargs.pop("loss_map_path", None)
    skip_split_concat = kwargs.pop("_skip_split_concat", False)
    _validate_split_direction(split_direction)
    cap = load_video(video_path)
    out = None
    loss_writer = None
    progress_bar = None

    try:
        props = get_video_properties(cap)
        width, height = props['width'], props['height']
        if width <= 0 or height <= 0:
            raise ValueError(
                f"Video has degenerate dimensions ({width}x{height}); cannot write output"
            )
        if props['frame_count'] <= 0:
            raise ValueError(
                "Video reports zero or unknown frame count; cannot process"
            )

        out_width, out_height = width, height
        if split_direction and split_direction.endswith("-full"):
            if split_direction.startswith("vertical"):
                out_width = width * 2
            else:
                out_height = height * 2

        out = create_video_writer(
            output_path, props['fps'], out_width, out_height
        )

        quiet = logging.getLogger().getEffectiveLevel() >= logging.ERROR
        progress_bar = tqdm(
            total=props['frame_count'],
            desc="Processing frames",
            disable=quiet,
        )

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            processed = process_function(frame, **kwargs)
            if isinstance(processed, tuple):
                processed_frame, loss_frame = processed
                if loss_map_path and loss_writer is None:
                    loss_writer = create_video_writer(
                        loss_map_path, props['fps'], width, height
                    )
                if loss_writer is not None:
                    loss_bgr = cv2.cvtColor(loss_frame, cv2.COLOR_GRAY2BGR)
                    loss_writer.write(loss_bgr)
            else:
                processed_frame = processed

            if not skip_split_concat and not (split_direction and split_direction.endswith("-full")):
                expected_shape = (height, width)
                if processed_frame.shape[:2] != expected_shape:
                    processed_frame = cv2.resize(
                        processed_frame, (expected_shape[1], expected_shape[0]),
                        interpolation=cv2.INTER_LINEAR,
                    )
            if split_direction and not skip_split_concat:
                if split_direction.endswith("-full"):
                    axis = 1 if split_direction.startswith("vertical") else 0
                    processed_frame = np.concatenate(
                        (frame, processed_frame), axis=axis
                    )
                elif split_direction == "vertical":
                    w = frame.shape[1]
                    half = w // 2
                    processed_frame = np.concatenate(
                        (frame[:, :half], processed_frame[:, half:]), axis=1
                    )
                else:
                    h = frame.shape[0]
                    half = h // 2
                    processed_frame = np.concatenate(
                        (frame[:half, :], processed_frame[half:, :]), axis=0
                    )
            out.write(processed_frame)
            progress_bar.update(1)

        _log.info("Processed video saved to %s", output_path)

    finally:
        if progress_bar is not None:
            progress_bar.close()
        if loss_writer is not None:
            loss_writer.release()
        if out is not None:
            out.release()
        cap.release()


def process_media(input_path: str, output_path: str, process_function: Callable[..., Any], no_audio: bool = False, **kwargs: Any) -> None:
    """
    Process a video or still image, chosen from the output path extension.

    Still-image extensions dispatch to process_image(), everything else to
    process_video_frames(). This is the single dispatch point used by the
    effect entry points, so callers do not repeat the extension check.

    For video output, OpenCV writes a silent file. When *no_audio* is False
    (the default), the original audio track is merged back in after the
    frames are written, using ``ffmpeg``. Set *no_audio* to True to skip
    the merge (``--no-audio`` on the CLI).

    Args:
        input_path (str): Path to the input video or image
        output_path (str): Path where the processed result will be saved
        process_function (callable): Function to apply to each frame
        no_audio (bool): When True, skip the ffmpeg audio-merge step
        **kwargs: Additional arguments to pass to the process_function
    """
    preview_frame = kwargs.pop("preview_frame", None)
    preview_output_path = kwargs.pop("preview_output_path", None)
    if preview_output_path is not None and preview_frame is None:
        raise ValueError("preview_output_path requires preview_frame")
    split_direction = kwargs.pop("split_direction", None)
    skip_split_concat = kwargs.pop("_skip_split_concat", False)
    if preview_frame is not None:
        preview_path = preview_output_path or output_path
        if not is_image_file(preview_path):
            raise ValueError(
                f"Preview output path must be an image file, got {preview_path!r}"
            )
        frame = extract_frame(input_path, preview_frame)
        preview_kwargs = dict(kwargs)
        preview_kwargs.pop("loss_map_path", None)
        processed = process_function(frame, **preview_kwargs)
        if isinstance(processed, tuple):
            processed_frame = processed[0]
        else:
            processed_frame = processed
        if split_direction and not skip_split_concat:
            if split_direction.endswith("-full"):
                axis = 1 if split_direction.startswith("vertical") else 0
                processed_frame = np.concatenate((frame, processed_frame), axis=axis)
            elif split_direction == "vertical":
                w = frame.shape[1]
                half = w // 2
                processed_frame = np.concatenate((frame[:, :half], processed_frame[:, half:]), axis=1)
            else:
                h = frame.shape[0]
                half = h // 2
                processed_frame = np.concatenate((frame[:half, :], processed_frame[half:, :]), axis=0)
        output_dir = os.path.dirname(preview_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        success = cv2.imwrite(preview_path, processed_frame)
        if not success:
            raise RuntimeError(f"Failed to write preview frame: {preview_path}")
        _log.info("Preview frame saved to %s", preview_path)
        return

    if is_image_file(output_path):
        return process_image(
            input_path,
            output_path,
            process_function,
            split_direction=split_direction,
            _skip_split_concat=skip_split_concat,
            **kwargs,
        )
    process_video_frames(
        input_path,
        output_path,
        process_function,
        split_direction=split_direction,
        _skip_split_concat=skip_split_concat,
        **kwargs,
    )
    if not no_audio:
        from ..audio import merge_audio
        merge_audio(input_path, output_path)
