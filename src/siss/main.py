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
import json
import logging
import os
import sys
from argparse import Namespace
from typing import Any, Dict, List, Optional, Tuple

from .colors import (
    export_palette_preview,
    get_palette,
    list_palettes,
    load_palette_file,
    parse_color,
)
from .duotone import apply_duotone
from .halftone import GRID_TYPES, SYMBOL_TYPES, _validate_gamma, apply_halftone

_GAMMA_DEFAULT = 1.0
EFFECT_TYPES = ("duotone", "halftone")


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


def _validate_output_path(output_path: str) -> str:
    """
    Validate an output path, rejecting parent-directory traversal.

    Returns the path unchanged on success.

    Raises ValueError if the path is empty or contains ``..`` segments
    that would escape the working directory.
    """
    if not output_path:
        raise ValueError("Output path cannot be empty")
    normalized = os.path.normpath(output_path)
    if ".." in normalized.split(os.sep):
        raise ValueError(
            f"Output path {output_path!r} contains parent-directory traversal"
        )
    return output_path


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


def parse_arguments() -> Namespace:
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
        choices=list(EFFECT_TYPES),
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
        "--preview-frame",
        type=str,
        default=None,
        metavar="SPEC",
        help=(
            "Process a single frame from a video input. Accepts an integer "
            "frame index or 'middle'. When the main output path is an image, "
            "the processed frame is written there. Use --preview-output to save "
            "to a separate file."
        ),
    )

    parser.add_argument(
        "--preview-output",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Path to save a single preview frame when --preview-frame is used. "
            "If omitted and the main output path is an image file, that path is used."
        ),
    )

    parser.add_argument(
        "--symbol-size",
        "--symbol_size",
        type=int,
        default=None,
        dest="symbol_size",
        help="Size of the largest symbol in the halftone effect",
    )

    parser.add_argument(
        "--symbol-type",
        "--symbol_type",
        type=str,
        choices=list(SYMBOL_TYPES),
        default=None,
        dest="symbol_type",
        help="Symbol type for halftone effect",
    )

    parser.add_argument(
        "--grid-type",
        "--grid_type",
        type=str,
        choices=list(GRID_TYPES),
        default=None,
        dest="grid_type",
        help=(
            "Sampling grid for halftone effect. 'hex' staggers alternating "
            "rows by half a step, giving the interlocking dot screen of a "
            "traditional print halftone instead of a plain square lattice."
        ),
    )

    parser.add_argument(
        "--constraints",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Path to a JSON constraints file that locks every rendering "
            "parameter (effect, colors, symbol type, grid, and luminance "
            "curve gamma). CLI flags override individual slots. Use "
            "--dump-constraints to capture an effective file from a run."
        ),
    )

    parser.add_argument(
        "--dump-constraints",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Write the effective constraints of this run to PATH as a JSON "
            "file. The output is a valid constraints file for --constraints."
        ),
    )

    parser.add_argument(
        "--loss-map",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Write a grayscale loss map to PATH alongside the rendered "
            "output. Each pixel encodes the absolute difference between "
            "the source luminance and the luminance reproducible under "
            "the chosen grammar, bright where the filter diverged. Only "
            "valid with --effect halftone."
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
        choices=["vertical", "horizontal", "vertical-full", "horizontal-full"],
        default=None,
        metavar="DIRECTION",
        dest="split_view",
        help=(
            "Stitch a before/after comparison: vertical (left/right halves) "
            "or horizontal (top/bottom halves) at original dimensions. Append "
            "-full for full-canvas mode (doubled width or height). Use with "
            "--split-alt-* flags to apply a different style to each side."
        ),
    )

    parser.add_argument(
        "--split-alt-constraints",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Constraints file for the alternate half in --split-view. "
            "When provided, the alt side is processed with these settings "
            "instead of showing the original frame."
        ),
    )

    parser.add_argument(
        "--split-alt-color1",
        type=str,
        nargs="+",
        default=None,
        metavar="COLOR",
        help=(
            "Color 1 for the alternate half in --split-view. "
            "Overrides --split-alt-constraints if both are given."
        ),
    )

    parser.add_argument(
        "--split-alt-color2",
        type=str,
        nargs="+",
        default=None,
        metavar="COLOR",
        help=(
            "Color 2 for the alternate half in --split-view. "
            "Overrides --split-alt-constraints if both are given."
        ),
    )

    parser.add_argument(
        "--split-alt-palette",
        type=str,
        default=None,
        metavar="NAME",
        help=(
            "Palette for the alternate half in --split-view. "
            "Overridden by --split-alt-constraints and explicit color flags."
        ),
    )

    return parser.parse_args()


def _resolve_colors(
    args,
    custom_palettes=None,
    constraints=None,
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """
    Resolve the final (color1_rgb, color2_rgb) pair.

    Precedence (highest to lowest) for each slot:
        1. Explicit --color1 / --color2 flag.
        2. --constraints file.
        3. --palette value (custom palettes from --palette-file take
           priority over built-in ones with the same name).
        4. Built-in defaults (red / cyan).

    Parameters
    ----------
    args : Namespace
        Parsed CLI arguments.
    custom_palettes : dict or None
        Mapping loaded from --palette-file via load_palette_file().
    constraints : dict or None
        Validated constraints loaded from --constraints.

    Returns
    -------
    tuple
        ((r, g, b), (r, g, b)) validated RGB tuples.
    """
    color1_rgb = (255, 0, 0)
    color2_rgb = (0, 255, 255)

    if args.palette:
        color1_rgb, color2_rgb = get_palette(args.palette, custom_palettes)

    if constraints:
        if "_parsed_color1" in constraints:
            color1_rgb = constraints["_parsed_color1"]
        elif "color1" in constraints:
            color1_rgb = parse_color(constraints["color1"])
        if "_parsed_color2" in constraints:
            color2_rgb = constraints["_parsed_color2"]
        elif "color2" in constraints:
            color2_rgb = parse_color(constraints["color2"])

    color1_rgb = resolve_color_arg(args.color1, color1_rgb)
    color2_rgb = resolve_color_arg(args.color2, color2_rgb)

    return color1_rgb, color2_rgb


_CONSTRAINTS_KEYS = frozenset({
    "effect", "color1", "color2",
    "symbol_type", "grid_type", "symbol_size",
    "luminance_curve",
})


def _make_alt_args(args: Namespace) -> Namespace:
    """Build a minimal namespace carrying the alt split-view overrides."""
    ns = argparse.Namespace()
    ns.palette = getattr(args, "split_alt_palette", None)
    ns.palette_file = None
    ns.color1 = args.split_alt_color1
    ns.color2 = args.split_alt_color2
    return ns


def _load_and_validate_constraints(path: str) -> Dict[str, Any]:
    """
    Load and validate a JSON constraints file.

    The file must contain only known keys. ``effect``, ``symbol_type``,
    and ``grid_type`` are validated against their CLI choice sets.
    ``color1`` and ``color2`` are parsed with :func:`parse_color` so the
    file accepts the same color forms as the CLI. ``luminance_curve``
    must be an object with an optional numeric ``gamma`` field.

    Returns a dict of the raw JSON contents on success.

    Raises ValueError with an exact message on unknown keys, bad values,
    or malformed JSON.
    """
    max_bytes = 1 * 1024 * 1024
    try:
        file_size = os.path.getsize(path)
    except OSError as e:
        raise ValueError(f"Cannot read constraints file: {e}") from e
    if file_size > max_bytes:
        raise ValueError(
            f"Constraints file {path!r} is {file_size:_d} bytes; "
            f"the limit is {max_bytes:_d} bytes (1 MiB)."
        )
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except OSError as e:
        raise ValueError(f"Cannot read constraints file: {e}") from e
    except UnicodeDecodeError as e:
        raise ValueError(f"Constraints file is not valid UTF-8: {e}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Constraints file is not valid JSON: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(
            "Constraints file must contain a JSON object, "
            f"got {type(data).__name__}"
        )

    unknown = set(data) - _CONSTRAINTS_KEYS
    if unknown:
        quoted = ", ".join(sorted(unknown))
        raise ValueError(f"Unknown constraint key(s): {quoted}")

    if "effect" in data:
        if data["effect"] not in EFFECT_TYPES:
            raise ValueError(
                "effect must be one of "
                + ", ".join(EFFECT_TYPES)
                + f", got {data['effect']!r}"
            )

    if "color1" in data:
        data["_parsed_color1"] = parse_color(data["color1"])
    if "color2" in data:
        data["_parsed_color2"] = parse_color(data["color2"])

    if "symbol_type" in data:
        if data["symbol_type"] not in SYMBOL_TYPES:
            raise ValueError(
                "symbol_type must be one of "
                + ", ".join(SYMBOL_TYPES)
                + f", got {data['symbol_type']!r}"
            )

    if "grid_type" in data:
        if data["grid_type"] not in GRID_TYPES:
            raise ValueError(
                "grid_type must be one of "
                + ", ".join(GRID_TYPES)
                + f", got {data['grid_type']!r}"
            )

    if "symbol_size" in data:
        value = data["symbol_size"]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(
                "symbol_size must be a positive integer, "
                f"got {value!r}"
            )

    if "luminance_curve" in data:
        lc = data["luminance_curve"]
        if not isinstance(lc, dict):
            raise ValueError(
                "luminance_curve must be a JSON object, "
                f"got {type(lc).__name__}"
            )
        if "gamma" in lc:
            _validate_gamma(lc["gamma"], parameter_name="luminance_curve.gamma")

    return data


def _resolve_params(args: Namespace, constraints: Optional[Dict[str, Any]], custom_palettes: Optional[Dict[str, Tuple[int, int, int]]]) -> Dict[str, Any]:
    """
    Resolve all rendering parameters with full precedence.

    Precedence for each slot: explicit CLI flag > constraints file >
    palette > built-in default.

    Returns a dict with keys matching the rendering parameters used by
    the dispatch functions.
    """
    color1_rgb, color2_rgb = _resolve_colors(args, custom_palettes, constraints)

    effect = args.effect
    if effect is None and constraints and "effect" in constraints:
        effect = constraints["effect"]

    symbol_size = args.symbol_size
    if symbol_size is None and constraints and "symbol_size" in constraints:
        symbol_size = constraints["symbol_size"]
    if symbol_size is None:
        symbol_size = 10

    symbol_type = args.symbol_type
    if symbol_type is None and constraints and "symbol_type" in constraints:
        symbol_type = constraints["symbol_type"]
    if symbol_type is None:
        symbol_type = "plus"

    grid_type = args.grid_type
    if grid_type is None and constraints and "grid_type" in constraints:
        grid_type = constraints["grid_type"]
    if grid_type is None:
        grid_type = "square"

    gamma = _GAMMA_DEFAULT
    if constraints and "luminance_curve" in constraints:
        lc = constraints["luminance_curve"]
        if isinstance(lc, dict) and "gamma" in lc:
            gamma = float(lc["gamma"])

    return {
        "color1_rgb": color1_rgb,
        "color2_rgb": color2_rgb,
        "effect": effect,
        "symbol_size": symbol_size,
        "symbol_type": symbol_type,
        "grid_type": grid_type,
        "gamma": gamma,
    }


def _dump_effective_constraints(params: Dict[str, Any], path: str) -> None:
    """
    Write the resolved rendering parameters as a constraints JSON file.

    The output is a valid input for --constraints, minus derived RGB
    values (color fields remain in their original string form when
    possible; here they are written as hex strings).
    """
    if not params.get("effect"):
        raise ValueError("Cannot dump constraints: effect is not set")

    data: Dict[str, Any] = {}

    data["effect"] = params["effect"]

    c1 = params["color1_rgb"]
    c2 = params["color2_rgb"]
    data["color1"] = f"#{c1[0]:02x}{c1[1]:02x}{c1[2]:02x}"
    data["color2"] = f"#{c2[0]:02x}{c2[1]:02x}{c2[2]:02x}"

    data["symbol_type"] = params["symbol_type"]
    data["grid_type"] = params["grid_type"]
    data["symbol_size"] = params["symbol_size"]

    gamma = params.get("gamma", 1.0)
    if gamma != 1.0:
        data["luminance_curve"] = {"gamma": gamma}

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except OSError as e:
        raise ValueError(f"Cannot write constraints file: {e}") from e


def _validate_args_and_paths(args: Namespace) -> str:
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
    args.output = _validate_output_path(args.output)
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    return input_path


def _dispatch_effect(
    args: Namespace,
    input_path: str,
    color1_rgb: Tuple[int, int, int],
    color2_rgb: Tuple[int, int, int],
    custom_palettes: Optional[Dict[str, Tuple[int, int, int]]] = None,
    gamma: float = _GAMMA_DEFAULT,
) -> None:
    """
    Dispatch to the selected effect entry point.

    Each entry point routes to the video or still-image path based on the
    output file extension.
    """
    if getattr(args, "loss_map", None) is not None and args.effect != "halftone":
        raise ValueError("--loss-map requires --effect halftone")

    split_direction = getattr(args, "split_view", None)
    alt_constraints = None
    if getattr(args, "split_alt_constraints", None):
        validate_file_path(args.split_alt_constraints, check_exists=True)
        alt_constraints = _load_and_validate_constraints(args.split_alt_constraints)
    alt_color1_rgb = None
    alt_color2_rgb = None
    alt_kwargs = {}
    if alt_constraints or getattr(args, "split_alt_color1", None) or getattr(args, "split_alt_color2", None) or getattr(args, "split_alt_palette", None):
        alt_color1_rgb, alt_color2_rgb = _resolve_colors(
            _make_alt_args(args), custom_palettes=custom_palettes, constraints=alt_constraints,
        )

    if alt_constraints:
        alt_kwargs = {
            "alt_symbol_type": alt_constraints.get("symbol_type"),
            "alt_symbol_size": alt_constraints.get("symbol_size"),
            "alt_grid_type": alt_constraints.get("grid_type"),
            "alt_gamma": (
                float(alt_constraints["luminance_curve"]["gamma"])
                if alt_constraints.get("luminance_curve") and isinstance(alt_constraints["luminance_curve"], dict)
                and alt_constraints["luminance_curve"].get("gamma") is not None
                else None
            ),
        }

    if args.effect == "duotone":
        apply_duotone(
            input_path,
            args.output,
            color1_rgb,
            color2_rgb,
            no_audio=args.no_audio,
            split_direction=split_direction,
            alt_color1_rgb=alt_color1_rgb,
            alt_color2_rgb=alt_color2_rgb,
            preview_frame=getattr(args, "preview_frame", None),
            preview_output_path=getattr(args, "preview_output", None),
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
            gamma=gamma,
            loss_map_path=(
                _validate_output_path(args.loss_map) if getattr(args, "loss_map", None) else None
            ),
            alt_color1_rgb=alt_color1_rgb,
            alt_color2_rgb=alt_color2_rgb,
            preview_frame=getattr(args, "preview_frame", None),
            preview_output_path=getattr(args, "preview_output", None),
            **alt_kwargs,
        )


def _configure_logging(args: Namespace) -> None:
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


def main() -> int:
    """Main function to process command line arguments and apply video effects."""
    args = parse_arguments()
    _configure_logging(args)

    logger = logging.getLogger(__name__)

    try:
        custom_palettes = None
        if args.palette_file:
            validate_file_path(args.palette_file, check_exists=True)
            custom_palettes = load_palette_file(args.palette_file)

        constraints = None
        if args.constraints:
            validate_file_path(args.constraints, check_exists=True)
            constraints = _load_and_validate_constraints(args.constraints)

        if args.list_palettes:
            print(list_palettes(custom_palettes))
            return 0

        if args.export_palette_preview:
            export_palette_preview(_validate_output_path(args.export_palette_preview), custom_palettes)
            return 0

        params = _resolve_params(args, constraints, custom_palettes)

        if params["effect"] is None:
            raise ValueError(
                "Missing required argument: --effect. "
                "Set it on the command line or in a constraints file."
            )

        args.effect = params["effect"]
        args.symbol_size = params["symbol_size"]
        args.symbol_type = params["symbol_type"]
        args.grid_type = params["grid_type"]

        if args.dump_constraints:
            _dump_effective_constraints(params, _validate_output_path(args.dump_constraints))
            return 0

        input_path = _validate_args_and_paths(args)
        color1_rgb = params["color1_rgb"]
        color2_rgb = params["color2_rgb"]
        _dispatch_effect(
            args, input_path, color1_rgb, color2_rgb,
            custom_palettes=custom_palettes, gamma=params["gamma"],
        )

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
