"""
Unit tests for the CLI argument parsing and color resolution in main.py.

These focus on the pure (non-video) logic:
  - resolve_color_arg(): bridging argparse nargs lists to RGB tuples
  - _resolve_colors(): precedence of flag > palette > default
  - main(): help-style commands and error paths

The video-rendering paths in main() are exercised via the existing
test_duotone / test_halftone suites and manual smoke tests.
"""
import os
import unittest
from argparse import Namespace
from unittest import mock

from siss.main import (
    resolve_color_arg,
    _resolve_colors,
    main,
    validate_file_path,
)
from siss.utils.video_processing import is_image_file


def _ns(**kwargs):
    """Build a minimal argparse Namespace with defaults for color-related args."""
    base = dict(
        input=None,
        output=None,
        effect=None,
        color1=None,
        color2=None,
        palette=None,
        palette_file=None,
        list_palettes=False,
        symbol_size=10,
        symbol_type="plus",
        grid_type="square",
    )
    base.update(kwargs)
    return Namespace(**base)


class TestResolveColorArg(unittest.TestCase):
    """Tests for the per-flag color resolver."""

    def test_none_uses_default(self):
        self.assertEqual(resolve_color_arg(None, (1, 2, 3)), (1, 2, 3))

    def test_single_hex_string(self):
        self.assertEqual(resolve_color_arg(["#ff0044"], (0, 0, 0)), (255, 0, 68))

    def test_single_css_name(self):
        self.assertEqual(resolve_color_arg(["red"], (0, 0, 0)), (255, 0, 0))

    def test_three_ints(self):
        self.assertEqual(resolve_color_arg(["0", "128", "255"], (0, 0, 0)), (0, 128, 255))

    def test_invalid_value_propagates_error(self):
        with self.assertRaises(ValueError):
            resolve_color_arg(["notacolor"], (0, 0, 0))


class TestResolveColors(unittest.TestCase):
    """Tests for the overall color resolution precedence."""

    def test_defaults_when_nothing_specified(self):
        c1, c2 = _resolve_colors(_ns())
        self.assertEqual(c1, (255, 0, 0))   # red
        self.assertEqual(c2, (0, 255, 255))  # cyan

    def test_palette_overrides_defaults(self):
        c1, c2 = _resolve_colors(_ns(palette="noir"))
        self.assertEqual(c1, (0, 0, 0))      # pure black
        self.assertEqual(c2, (229, 229, 229))  # #e5e5e5

    def test_explicit_flag_overrides_palette(self):
        c1, c2 = _resolve_colors(
            _ns(palette="noir", color1=["#ffffff"])
        )
        self.assertEqual(c1, (255, 255, 255))  # overridden to white
        self.assertEqual(c2, (229, 229, 229))  # palette's color2 kept

    def test_both_flags_override_both_palette_slots(self):
        c1, c2 = _resolve_colors(
            _ns(palette="noir", color1=["gold"], color2=["navy"])
        )
        self.assertEqual(c1, (255, 215, 0))    # gold
        self.assertEqual(c2, (0, 0, 128))      # navy

    def test_explicit_flag_overrides_default_without_palette(self):
        c1, _ = _resolve_colors(_ns(color1=["rebeccapurple"]))
        self.assertEqual(c1, (102, 51, 153))

    def test_palette_unknown_raises(self):
        with self.assertRaises(ValueError):
            _resolve_colors(_ns(palette="nonexistent"))


class TestResolveColorsCustomPalettes(unittest.TestCase):
    """Tests for _resolve_colors with custom palettes from --palette-file."""

    def setUp(self):
        self.custom = {
            "brand": ((10, 20, 30), (40, 50, 60)),
            "sunset": ((255, 255, 255), (0, 0, 0)),
        }

    def test_custom_palette_lookup(self):
        c1, c2 = _resolve_colors(_ns(palette="brand"), self.custom)
        self.assertEqual(c1, (10, 20, 30))
        self.assertEqual(c2, (40, 50, 60))

    def test_custom_palette_overrides_builtin(self):
        c1, c2 = _resolve_colors(_ns(palette="sunset"), self.custom)
        self.assertEqual(c1, (255, 255, 255))
        self.assertEqual(c2, (0, 0, 0))

    def test_builtin_palette_still_works_with_custom_loaded(self):
        c1, c2 = _resolve_colors(_ns(palette="noir"), self.custom)
        self.assertEqual(c1, (0, 0, 0))
        self.assertEqual(c2, (229, 229, 229))

    def test_no_custom_palettes_does_not_affect_builtin(self):
        c1, c2 = _resolve_colors(_ns(palette="noir"), None)
        self.assertEqual(c1, (0, 0, 0))
        self.assertEqual(c2, (229, 229, 229))

    def test_explicit_flag_overrides_custom_palette(self):
        c1, c2 = _resolve_colors(
            _ns(palette="brand", color1=["gold"]), self.custom
        )
        self.assertEqual(c1, (255, 215, 0))
        self.assertEqual(c2, (40, 50, 60))


class TestMainEntryPoint(unittest.TestCase):
    """Tests for the main() function's control flow (no video rendering)."""

    def test_list_palettes_prints_and_exits_zero(self):
        with mock.patch("builtins.print") as mock_print:
            with mock.patch("sys.argv", ["siss", "--list-palettes"]):
                rc = main()
        self.assertEqual(rc, 0)
        # The catalog should mention at least one known palette.
        # Combine all print() calls so we don't miss output printed before the last one.
        printed = " ".join(
            str(arg)
            for call in mock_print.call_args_list
            for arg in call[0]
        )
        self.assertIn("sunset", printed)

    def test_missing_required_args_returns_error(self):
        with mock.patch("sys.argv", ["siss", "input.mp4", "output.mp4"]):
            rc = main()
        self.assertEqual(rc, 1)  # missing --effect

    def test_nonexistent_input_returns_error(self):
        with mock.patch(
            "sys.argv",
            ["siss", "/nonexistent/file.mp4", "out.mp4", "--effect", "duotone"],
        ):
            rc = main()
        self.assertEqual(rc, 1)


class TestValidateFilePath(unittest.TestCase):
    """Tests for the file-path validator."""

    def test_empty_path_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_file_path("")

    def test_nonexistent_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            validate_file_path("/nonexistent/file.mp4", check_exists=True)

    def test_existing_file_passes(self):
        # __file__ always exists.
        result = validate_file_path(__file__, check_exists=True)
        self.assertEqual(result, __file__)

    def test_skip_exists_check(self):
        result = validate_file_path("/any/path", check_exists=False)
        self.assertEqual(result, "/any/path")


class TestMainVideoEffects(unittest.TestCase):
    """Tests for the video-rendering paths inside main()."""

    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.tmp.name, "input.mp4")
        self.output_path = os.path.join(self.tmp.name, "output.mp4")

        # A placeholder file is enough: apply_duotone/apply_halftone are
        # fully mocked, so main() only needs the path to pass os.path.isfile().
        open(self.input_path, "wb").close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_duotone_effect_returns_zero(self):
        with mock.patch("siss.main.apply_duotone") as mock_dt:
            with mock.patch(
                "sys.argv",
                ["siss", self.input_path, self.output_path, "--effect", "duotone"],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        mock_dt.assert_called_once()

    def test_halftone_effect_returns_zero(self):
        with mock.patch("siss.main.apply_halftone") as mock_ht:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--effect",
                    "halftone",
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        mock_ht.assert_called_once()

    def test_duotone_color_args_forwarded(self):
        with mock.patch("siss.main.apply_duotone") as mock_dt:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--effect",
                    "duotone",
                    "--color1",
                    "#ff0000",
                    "--color2",
                    "#00ffff",
                ],
            ):
                main()
        _, kwargs = mock_dt.call_args
        # color1_rgb and color2_rgb are positional args
        call_args = mock_dt.call_args[0]
        self.assertEqual(call_args[2], (255, 0, 0))    # color1_rgb
        self.assertEqual(call_args[3], (0, 255, 255))  # color2_rgb

    def test_halftone_symbol_args_forwarded(self):
        with mock.patch("siss.main.apply_halftone") as mock_ht:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--effect",
                    "halftone",
                    "--symbol_size",
                    "15",
                    "--symbol_type",
                    "asterisk",
                ],
            ):
                main()
        call_args = mock_ht.call_args
        # symbol_size is 3rd positional arg (index 2)
        self.assertEqual(call_args[0][2], 15)
        self.assertEqual(call_args[1].get("symbol_type"), "asterisk")

    def test_halftone_dot_symbol_and_grid_type_forwarded(self):
        with mock.patch("siss.main.apply_halftone") as mock_ht:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--effect",
                    "halftone",
                    "--symbol_type",
                    "dot",
                    "--grid_type",
                    "hex",
                ],
            ):
                main()
        _, kwargs = mock_ht.call_args
        self.assertEqual(kwargs.get("symbol_type"), "dot")
        self.assertEqual(kwargs.get("grid_type"), "hex")

    def test_output_directory_created_if_missing(self):
        nested_out = os.path.join(self.tmp.name, "newdir", "out.mp4")
        with mock.patch("siss.main.apply_duotone"):
            with mock.patch(
                "sys.argv",
                ["siss", self.input_path, nested_out, "--effect", "duotone"],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isdir(os.path.join(self.tmp.name, "newdir")))

    def test_unexpected_exception_returns_one(self):
        with mock.patch("siss.main.apply_duotone", side_effect=RuntimeError("boom")):
            with mock.patch(
                "sys.argv",
                ["siss", self.input_path, self.output_path, "--effect", "duotone"],
            ):
                rc = main()
        self.assertEqual(rc, 1)


class TestMainImageEffects(unittest.TestCase):
    """Tests for still-image runs through main().

    The video/still dispatch itself lives in process_media() and is covered
    in test_video_processing.py; here we only check that main() forwards the
    paths to the single per-effect entry point.
    """

    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.tmp.name, "input.png")
        self.output_path = os.path.join(self.tmp.name, "output.png")

        # A placeholder file is enough: the effect entry points are fully
        # mocked, so main() only needs the path to pass os.path.isfile().
        open(self.input_path, "wb").close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_duotone_image_run_calls_apply_duotone(self):
        with mock.patch("siss.main.apply_duotone") as mock_dt:
            with mock.patch(
                "sys.argv",
                ["siss", self.input_path, self.output_path, "--effect", "duotone"],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        mock_dt.assert_called_once()
        call_args = mock_dt.call_args[0]
        self.assertEqual(call_args[0], self.input_path)
        self.assertEqual(call_args[1], self.output_path)

    def test_halftone_image_run_calls_apply_halftone(self):
        with mock.patch("siss.main.apply_halftone") as mock_ht:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--effect",
                    "halftone",
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        mock_ht.assert_called_once()
        call_args = mock_ht.call_args[0]
        self.assertEqual(call_args[0], self.input_path)
        self.assertEqual(call_args[1], self.output_path)

    def test_duotone_video_run_uses_same_entry_point(self):
        output_path = os.path.join(self.tmp.name, "output.mp4")
        with mock.patch("siss.main.apply_duotone") as mock_dt:
            with mock.patch(
                "sys.argv",
                ["siss", self.input_path, output_path, "--effect", "duotone"],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        mock_dt.assert_called_once()


class TestIsImageFile(unittest.TestCase):
    """Tests for the image-extension detector."""

    def test_png_is_image(self):
        self.assertTrue(is_image_file("frame.png"))

    def test_jpeg_is_image(self):
        self.assertTrue(is_image_file("frame.JPEG"))

    def test_mp4_is_not_image(self):
        self.assertFalse(is_image_file("clip.mp4"))


class TestMainPaletteFile(unittest.TestCase):
    """Tests for the --palette-file CLI flag inside main()."""

    def setUp(self):
        import json
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.tmp.name, "input.mp4")
        self.output_path = os.path.join(self.tmp.name, "output.mp4")
        open(self.input_path, "wb").close()

        self.palette_path = os.path.join(self.tmp.name, "p.json")
        with open(self.palette_path, "w") as f:
            json.dump(
                {"brand": {"color1": "#ff0000", "color2": "#00ffff"}}, f
            )

    def tearDown(self):
        self.tmp.cleanup()

    def test_palette_file_used_in_effect_run(self):
        with mock.patch("siss.main.apply_duotone") as mock_dt:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--effect",
                    "duotone",
                    "--palette",
                    "brand",
                    "--palette-file",
                    self.palette_path,
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        call_args = mock_dt.call_args[0]
        self.assertEqual(call_args[2], (255, 0, 0))    # color1 from file
        self.assertEqual(call_args[3], (0, 255, 255))  # color2 from file

    def test_list_palettes_with_palette_file(self):
        with mock.patch("builtins.print") as mock_print:
            with mock.patch(
                "sys.argv",
                ["siss", "--list-palettes", "--palette-file", self.palette_path],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        printed = " ".join(
            str(arg) for call in mock_print.call_args_list for arg in call[0]
        )
        self.assertIn("brand", printed)
        self.assertIn("sunset", printed)

    def test_missing_palette_file_returns_error(self):
        with mock.patch(
            "sys.argv",
            [
                "siss",
                self.input_path,
                self.output_path,
                "--effect",
                "duotone",
                "--palette",
                "brand",
                "--palette-file",
                os.path.join(self.tmp.name, "missing.json"),
            ],
        ):
            rc = main()
        self.assertEqual(rc, 1)

    def test_invalid_palette_file_returns_error(self):
        bad_path = os.path.join(self.tmp.name, "bad.json")
        with open(bad_path, "w") as f:
            f.write("{not json")
        with mock.patch(
            "sys.argv",
            [
                "siss",
                self.input_path,
                self.output_path,
                "--effect",
                "duotone",
                "--palette-file",
                bad_path,
            ],
        ):
            rc = main()
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
