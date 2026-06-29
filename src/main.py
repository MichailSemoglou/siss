#!/usr/bin/env python3
"""
Video effects CLI tool for applying duotone and halftone effects to videos.

Colors can be supplied in any of these designer-friendly forms:

* Hex string:  ``--color1 "#ff0044"``  (quote it so the shell keeps the ``#``)
* CSS name:    ``--color1 rebeccapurple``
* RGB triple:  ``--color1 255 0 0``    (the original syntax)

Or pick a whole look at once with ``--palette <name>`` (see ``--list-palettes``).
"""
import argparse
import sys
import os
from typing import List, Optional, Tuple

from duotone import apply_duotone
from halftone import apply_halftone
from colors import parse_color, get_palette, list_palettes
from utils.video_processing import get_codec_for_file


def validate_file_path(file_path, check_exists=True):
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
            "Apply duotone and halftone effects to a video. "
            "Colors accept hex (#ff0044), CSS names (rebeccapurple), "
            "RGB triples (255 0 0), or a named --palette."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Positionals are optional so --list-palettes / --help work without paths.
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to the input video",
    )

    parser.add_argument(
        "output",
        nargs="?",
        help="Path to save the output video",
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
        "--list-palettes",
        action="store_true",
        help="Print the available curated palettes and exit.",
    )

    parser.add_argument(
        "--symbol_size",
        type=int,
        default=10,
        help="Size of the largest symbol in the halftone effect",
    )

    parser.add_argument(
        "--symbol_type",
        type=str,
        choices=["plus", "asterisk", "slash"],
        default="plus",
        help="Symbol type for halftone effect",
    )

    # Add codec override options
    parser.add_argument(
        "--use-codec-fix",
        action="store_true",
        help="Use the codec compatibility fix for different platforms",
    )

    return parser.parse_args()


def _resolve_colors(args):
    """
    Resolve the final (color1_rgb, color2_rgb) pair.

    Precedence (highest to lowest) for each slot:
        1. Explicit --color1 / --color2 flag.
        2. --palette value.
        3. Built-in defaults (red / cyan).

    Returns
    -------
    tuple
        ((r, g, b), (r, g, b)) validated RGB tuples.
    """
    # Defaults match the documented original behavior.
    color1_rgb = (255, 0, 0)   # red  -> darks / symbols
    color2_rgb = (0, 255, 255)  # cyan -> lights / background

    # Palette provides a baseline that explicit flags can override.
    if args.palette:
        color1_rgb, color2_rgb = get_palette(args.palette)

    # Explicit flags win over palette.
    color1_rgb = resolve_color_arg(args.color1, color1_rgb)
    color2_rgb = resolve_color_arg(args.color2, color2_rgb)

    return color1_rgb, color2_rgb


def main():
    """Main function to process command line arguments and apply video effects."""
    try:
        args = parse_arguments()

        # --list-palettes is a self-contained help-style command.
        if args.list_palettes:
            print(list_palettes())
            return 0

        # For any real run we need input, output, and an effect.
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

        # Validate input and output paths
        input_path = validate_file_path(args.input, check_exists=True)
        output_dir = os.path.dirname(args.output)

        # Create output directory if it doesn't exist
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Resolve colors (palette + explicit overrides).
        color1_rgb, color2_rgb = _resolve_colors(args)

        # Apply selected effect
        if args.effect == "duotone":
            apply_duotone(
                input_path,
                args.output,
                color1_rgb,
                color2_rgb,
                use_codec_fix=args.use_codec_fix,
            )
        elif args.effect == "halftone":
            apply_halftone(
                input_path,
                args.output,
                args.symbol_size,
                color1_rgb,
                color2_rgb,
                symbol_type=args.symbol_type,
                use_codec_fix=args.use_codec_fix,
            )

    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())