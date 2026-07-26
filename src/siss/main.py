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
import os
import sys
from typing import List, Optional, Tuple

from .colors import get_palette, list_palettes, load_palette_file, parse_color
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
        "--symbol_size",
        type=int,
        default=10,
        help="Size of the largest symbol in the halftone effect",
    )

    parser.add_argument(
        "--symbol_type",
        type=str,
        choices=["plus", "asterisk", "slash", "dot"],
        default="plus",
        help="Symbol type for halftone effect",
    )

    parser.add_argument(
        "--grid_type",
        type=str,
        choices=["square", "hex"],
        default="square",
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


def main():
    """Main function to process command line arguments and apply video effects."""
    try:
        args = parse_arguments()

        # Load custom palettes early so --list-palettes can show them too.
        custom_palettes = None
        if args.palette_file:
            validate_file_path(args.palette_file, check_exists=True)
            custom_palettes = load_palette_file(args.palette_file)

        if args.list_palettes:
            print(list_palettes(custom_palettes))
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

        # Resolve colors (palette + explicit overrides + custom palette file).
        color1_rgb, color2_rgb = _resolve_colors(args, custom_palettes)

        # Apply the selected effect. Each entry point dispatches to the
        # video or still-image path based on the output file extension.
        if args.effect == "duotone":
            apply_duotone(
                input_path,
                args.output,
                color1_rgb,
                color2_rgb,
                no_audio=args.no_audio,
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
