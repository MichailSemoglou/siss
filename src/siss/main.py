#!/usr/bin/env python3
"""
CLI tool for applying duotone and halftone effects to videos and still images.

Colors can be supplied in any of these designer-friendly forms:

* Hex string:  ``--color1 "#ff0044"``  (quote it so the shell keeps the ``#``)
* CSS name:    ``--color1 rebeccapurple``
* RGB triple:  ``--color1 255 0 0``    (the original syntax)

Or pick a whole look at once with ``--palette <name>`` (see ``--list-palettes``).

Output format is chosen from the output path extension: ``.mp4``/``.mov`` write
a video, while ``.png``/``.jpg``/``.webp`` write a single still image.
"""
import argparse
import logging
import os
import sys
from typing import List, Optional, Tuple

from .colors import (
    export_palette_preview,
    get_palette,
    list_palettes,
    load_palette_file,
    parse_color,
)
from .duotone import apply_duotone
from .halftone import apply_halftone


def validate_file_path(file_path: str, check_exists: bool = True) -> str:
    """
    Validate file path.

    Args:
        file_path (str): Path to validate
        check_exists (bool): Whether to check if file exists

    Returns:
        str: Valid file path

    Raises:
        FileNotFoundError: If check_exists is True and file does not exist
        ValueError: If file path is invalid
    """
    if not file_path:
        raise ValueError("File path cannot be empty")

    if check_exists and not os.path.isfile(file_path):
        raise FileNotFoundError(f"File does not exist: {file_path}")

    return file_path


def resolve_color_arg(
    value: Optional[List[str]], default_rgb: Tuple[int, int, int]
) -> Tuple[int, int, int]:
    """
    Resolve a ``--color1`` / ``--color2`` CLI value into an RGB tuple.

    ``value`` is the raw ``nargs="+"`` list from argparse:

    * ``None``      -> the caller did not pass the flag; use ``default_rgb``.
    * 1 element     -> a hex string (``"#ff0044"``) or CSS name (``"red"``).
    * 3 elements    -> the classic ``R G B`` integer triple.

    Any parsing/validation error from :func:`parse_color` is surfaced as-is.
    """
    if value is None:
        return default_rgb
    if len(value) == 1:
        return parse_color(value[0])
    return parse_color(value)


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description=(
            "Apply duotone and halftone effects to a video or still image. "
            "Colors accept hex (#ff0044), CSS names (rebeccapurple), "
            "RGB triples (255 0 0), or a named --palette. "
            "Output format is chosen from the output path extension."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Positionals are optional so --list-palettes / --help work without paths.
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to the input video or still image",
    )

    parser.add_argument(
        "output",
        nargs="?",
        help="Path to save the output video or still image",
    )

    parser.add_argument(
        "--effect",
        type=str,
        choices=["duotone", "halftone"],
        default=None,
        help="Effect to apply to the video (duotone or halftone)",
    )

    parser.add_argument(
        "--color1",
        nargs="+",
        default=None,
        metavar="SPEC",
        help=(
            "First color: dark areas in duotone, symbols in halftone. "
            "Accepts hex (#ff0044), CSS name (rebeccapurple), or 'R G B'. "
            "Overrides the palette's color1 if both are given."
        ),
    )

    parser.add_argument(
        "--color2",
        nargs="+",
        default=None,
        metavar="SPEC",
        help=(
            "Second color: light areas in duotone, background in halftone. "
            "Accepts hex (#ff0044), CSS name (rebeccapurple), or 'R G B'. "
            "Overrides the palette's color2 if both are given."
        ),
    )

    parser.add_argument(
        "--palette",
        type=str,
        default=None,
        help=(
            "Apply a curated two-color palette by name. "
            "Use --list-palettes to see the options. "
            "Individual --color1/--color2 flags override single slots."
        ),
    )

    parser.add_argument(
        "--palette-file",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Path to a JSON file of custom palettes. "
            "Each entry must have 'color1' and 'color2' keys; "
            "colors accept the same forms as --color1/--color2. "
            "Custom names override built-in ones."
        ),
    )

    parser.add_argument(
        "--list-palettes",
        action="store_true",
        help="Print the available curated palettes and exit.",
    )

    parser.add_argument(
        "--export-palette-preview",
        type=str,
        default=None,
        metavar="PATH",
        help="Render a PNG contact sheet of every palette and save it to PATH.",
    )

    parser.add_argument(
        "--symbol-size",
        "--symbol_size",
        type=int,
        default=10,
        dest="symbol_size",
        help="Size of the largest symbol in the halftone effect",
    )

    parser.add_argument(
        "--symbol-type",
        "--symbol_type",
        type=str,
        choices=["plus", "asterisk", "slash", "dot"],
        default="plus",
        dest="symbol_type",
        help="Symbol type for halftone effect",
    )

    parser.add_argument(
        "--grid-type",
        "--grid_type",
        type=str,
        choices=["square", "hex"],
        default="square",
        dest="grid_type",
        help=(
            "Sampling grid for halftone effect. 'hex' staggers alternating "
            "rows by half a step, giving the interlocking dot screen of a "
            "traditional print halftone instead of a plain square lattice."
        ),
    )

    parser.add_argument(
        "--no-audio",
        action="store_true",
        help=(
            "Skip merging the original audio track into the output video. "
            "By default, Siss copies audio from the source with ffmpeg "
            "after rendering."
        ),
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help=(
            "Increase log verbosity. Use -v for INFO, -vv for DEBUG. "
            "Without --verbose, only warnings and errors are shown."
        ),
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        default=False,
        help=(
            "Suppress informational output, progress bars, and logs below "
            "ERROR level. The final result-path line is still printed."
        ),
    )

    parser.add_argument(
        "--split-view",
        type=str,
        choices=["vertical", "horizontal"],
        default=None,
        metavar="DIRECTION",
        help=(
            "Export a before/after comparison: vertical (left/right) or "
            "horizontal (top/bottom). Works with any input orientation "
            "including portrait and 9:16 vertical video."
        ),
    )

    return parser.parse_args()


def _resolve_colors(
    args,
    custom_palettes=None,
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """
    Resolve the final (color1_rgb, color2_rgb) pair.

    Precedence (highest to lowest) for each slot:
        1. Explicit --color1 / --color2 flag.
        2. --palette value (custom palettes from --palette-file take
           priority over built-in ones with the same name).
        3. Built-in defaults (red / cyan).

    Parameters
    ----------
    args : Namespace
        Parsed CLI arguments.
    custom_palettes : dict or None
        Mapping loaded from --palette-file via load_palette_file().

    Returns
    -------
    tuple
        ((r, g, b), (r, g, b)) validated RGB tuples.
    """
    color1_rgb = (255, 0, 0)
    color2_rgb = (0, 255, 255)

    if args.palette:
        color1_rgb, color2_rgb = get_palette(args.palette, custom_palettes)

    color1_rgb = resolve_color_arg(args.color1, color1_rgb)
    color2_rgb = resolve_color_arg(args.color2, color2_rgb)

    return color1_rgb, color2_rgb


def _validate_args_and_paths(args):
    """
    Validate that required args are present and return the resolved input path.

    Creates the output directory if it does not exist.

    Returns
    -------
    str
        Validated input file path.

    Raises
    ------
    ValueError
        If input, output, or --effect is missing.
    FileNotFoundError
        If the input path does not exist.
    """
    missing = []
    if not args.input:
        missing.append("input")
    if not args.output:
        missing.append("output")
    if not args.effect:
        missing.append("--effect")
    if missing:
        raise ValueError(
            "Missing required argument(s): "
            + ", ".join(missing)
            + ". Use --list-palettes to browse palettes."
        )

    input_path = validate_file_path(args.input, check_exists=True)
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    return input_path


def _dispatch_effect(args, input_path, color1_rgb, color2_rgb):
    """
    Dispatch to the selected effect entry point.

    Each entry point routes to the video or still-image path based on the
    output file extension.
    """
    split_direction = getattr(args, "split_view", None)
    if args.effect == "duotone":
        apply_duotone(
            input_path,
            args.output,
            color1_rgb,
            color2_rgb,
            no_audio=args.no_audio,
            split_direction=split_direction,
        )
    elif args.effect == "halftone":
        apply_halftone(
            input_path,
            args.output,
            args.symbol_size,
            color1_rgb,
            color2_rgb,
            symbol_type=args.symbol_type,
            grid_type=args.grid_type,
            no_audio=args.no_audio,
            split_direction=split_direction,
        )


def _configure_logging(args) -> None:
    """Set up structured logging based on --verbose and --quiet flags."""
    if args.quiet:
        level = logging.ERROR
    elif args.verbose >= 2:
        level = logging.DEBUG
    elif args.verbose == 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(
        format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=level,
        stream=sys.stderr,
    )


def main():
    """Main function to process command line arguments and apply video effects."""
    args = parse_arguments()
    _configure_logging(args)

    logger = logging.getLogger(__name__)

    try:
        custom_palettes = None
        if args.palette_file:
            validate_file_path(args.palette_file, check_exists=True)
            custom_palettes = load_palette_file(args.palette_file)

        if args.list_palettes:
            print(list_palettes(custom_palettes))
            return 0

        if args.export_palette_preview:
            export_palette_preview(args.export_palette_preview, custom_palettes)
            return 0

        input_path = _validate_args_and_paths(args)
        color1_rgb, color2_rgb = _resolve_colors(args, custom_palettes)
        _dispatch_effect(args, input_path, color1_rgb, color2_rgb)

    except FileNotFoundError as e:
        logger.error("%s", e)
        return 1
    except ValueError as e:
        logger.error("%s", e)
        return 1
    except RuntimeError as e:
        logger.error("%s", e)
        return 1
    except Exception:
        if logger.getEffectiveLevel() <= logging.DEBUG:
            logger.exception("Unexpected error")
        else:
            logger.error(
                "An unexpected error occurred. "
                "Re-run with -vv for the full traceback."
            )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
