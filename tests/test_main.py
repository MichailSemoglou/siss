"""
Unit tests for the CLI argument parsing and color resolution in main.py.

These focus on the pure (non-video) logic:
  - resolve_color_arg(): bridging argparse nargs lists to RGB tuples
  - _resolve_colors(): precedence of flag > palette > default
  - main(): help-style commands and error paths

The video-rendering paths in main() are exercised via the existing
test_duotone / test_halftone suites and manual smoke tests.
"""
import importlib
import os
import unittest
from argparse import Namespace
from unittest import mock

from siss.main import (
    _configure_logging,
    _dispatch_effect,
    _resolve_colors,
    _validate_args_and_paths,
    main,
    resolve_color_arg,
    validate_file_path,
)
from siss.utils.video_processing import is_image_file
from tests.helpers import make_test_video


def _ns(**kwargs):
    """Build a minimal argparse Namespace with defaults matching CLI flags."""
    base = dict(
        input=None,
        output=None,
        effect=None,
        color1=None,
        color2=None,
        palette=None,
        palette_file=None,
        list_palettes=False,
        symbol_size=None,
        symbol_type=None,
        grid_type=None,
        no_audio=False,
        split_view=None,
        constraints=None,
        dump_constraints=None,
        export_palette_preview=None,
        extract_frame=None,
        verbose=0,
        quiet=False,
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


class TestDispatchEffect(unittest.TestCase):
    """Tests for effect dispatch validation."""

    def test_loss_map_requires_halftone(self):
        args = _ns(effect="duotone", output="out.mp4", loss_map="loss.png")
        with self.assertRaises(ValueError) as ctx:
            _dispatch_effect(args, "input.mp4", (255, 0, 0), (0, 255, 255))
        self.assertIn("--loss-map requires --effect halftone", str(ctx.exception))


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

    def test_module_entrypoint_imports(self):
        module = importlib.import_module("siss.__main__")
        self.assertTrue(callable(module.main))

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

    def test_preview_only_inputs_accept_preview_output(self):
        args = _ns(
            input=__file__,
            output=None,
            effect="duotone",
            preview_frame="2",
            preview_output="preview.png",
        )
        input_path = _validate_args_and_paths(args)
        self.assertEqual(input_path, __file__)
        self.assertIsNone(args.output)


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


class TestValidateOutputPath(unittest.TestCase):
    """Tests for _validate_output_path()."""

    def test_relative_path_ok(self):
        from siss.main import _validate_output_path
        self.assertEqual(_validate_output_path("out.mp4"), "out.mp4")

    def test_subdir_ok(self):
        from siss.main import _validate_output_path
        self.assertEqual(_validate_output_path("subdir/out.mp4"), "subdir/out.mp4")

    def test_parent_traversal_rejected(self):
        from siss.main import _validate_output_path
        with self.assertRaises(ValueError):
            _validate_output_path("../etc/malicious.mp4")

    def test_deep_parent_traversal_rejected(self):
        from siss.main import _validate_output_path
        with self.assertRaises(ValueError):
            _validate_output_path("a/../../etc/file")

    def test_empty_path_rejected(self):
        from siss.main import _validate_output_path
        with self.assertRaises(ValueError):
            _validate_output_path("")

    def test_absolute_path_ok(self):
        from siss.main import _validate_output_path
        path = os.path.join(os.getcwd(), "test.mp4")
        self.assertEqual(_validate_output_path(path), path)

    def test_absolute_path_outside_working_tree_accepted(self):
        import tempfile

        from siss.main import _validate_output_path
        path = os.path.join(tempfile.gettempdir(), "test.mp4")
        self.assertEqual(_validate_output_path(path), path)


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

    def test_halftone_square_grid_and_asterisk_symbol_forwarded(self):
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
                    "asterisk",
                    "--grid_type",
                    "square",
                ],
            ):
                main()
        _, kwargs = mock_ht.call_args
        self.assertEqual(kwargs.get("symbol_type"), "asterisk")
        self.assertEqual(kwargs.get("grid_type"), "square")

    def test_halftone_ring_symbol_forwarded(self):
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
                    "ring",
                ],
            ):
                main()
        _, kwargs = mock_ht.call_args
        self.assertEqual(kwargs.get("symbol_type"), "ring")

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

    def test_no_audio_flag_forwarded_to_duotone(self):
        with mock.patch("siss.main.apply_duotone") as mock_dt:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--effect",
                    "duotone",
                    "--no-audio",
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        _, kwargs = mock_dt.call_args
        self.assertTrue(kwargs["no_audio"])

    def test_no_audio_flag_forwarded_to_halftone(self):
        with mock.patch("siss.main.apply_halftone") as mock_ht:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--effect",
                    "halftone",
                    "--no-audio",
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        _, kwargs = mock_ht.call_args
        self.assertTrue(kwargs["no_audio"])


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


class TestMainLogging(unittest.TestCase):
    """Tests for structured logging and --verbose/--quiet flags."""

    def setUp(self):
        import logging
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.tmp.name, "input.mp4")
        self.output_path = os.path.join(self.tmp.name, "output.mp4")
        open(self.input_path, "wb").close()

        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        root.setLevel(logging.WARNING)

    def tearDown(self):
        self.tmp.cleanup()

    def test_configure_logging_default_level(self):
        """Default (no flags) sets WARNING level."""
        import logging

        args = _ns()
        _configure_logging(args)
        self.assertEqual(logging.getLogger().getEffectiveLevel(), logging.WARNING)

    def test_configure_logging_verbose_once(self):
        """-v sets INFO level."""
        import logging

        args = _ns(verbose=1)
        _configure_logging(args)
        self.assertEqual(logging.getLogger().getEffectiveLevel(), logging.INFO)

    def test_configure_logging_verbose_twice(self):
        """-vv sets DEBUG level."""
        import logging

        args = _ns(verbose=2)
        _configure_logging(args)
        self.assertEqual(logging.getLogger().getEffectiveLevel(), logging.DEBUG)

    def test_configure_logging_quiet(self):
        """--quiet sets ERROR level."""
        import logging

        args = _ns(quiet=True)
        _configure_logging(args)
        self.assertEqual(logging.getLogger().getEffectiveLevel(), logging.ERROR)

    def test_quiet_overrides_verbose(self):
        """--quiet -v sets ERROR level regardless of verbosity."""
        import logging

        args = _ns(quiet=True, verbose=2)
        _configure_logging(args)
        self.assertEqual(logging.getLogger().getEffectiveLevel(), logging.ERROR)

    def test_quiet_flag_accepted_in_main(self):
        """--quiet flag produces a successful run."""
        with mock.patch("siss.main.apply_duotone"):
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--effect",
                    "duotone",
                    "--quiet",
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)

    def test_verbose_flag_accepted_in_main(self):
        """--verbose flag produces a successful run."""
        with mock.patch("siss.main.apply_duotone"):
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--effect",
                    "duotone",
                    "-vv",
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)

    def test_error_messages_go_to_logger_not_print(self):
        """FileNotFoundError is logged via logger, not print."""
        with mock.patch(
            "sys.argv",
            ["siss", "/nonexistent", "out.mp4", "--effect", "duotone"],
        ):
            with mock.patch("builtins.print") as mock_print:
                rc = main()
        self.assertEqual(rc, 1)
        stderr_calls = [
            call
            for call in mock_print.call_args_list
            if call[1]
            and call[1].get("file")
            and "stderr" in str(call[1]["file"])
        ]
        self.assertFalse(stderr_calls)

    def test_runtime_error_returns_one(self):
        """RuntimeError from the effect function returns exit code 1."""
        with mock.patch(
            "siss.main.apply_duotone",
            side_effect=RuntimeError("write failure"),
        ):
            with mock.patch(
                "sys.argv",
                ["siss", self.input_path, self.output_path, "--effect", "duotone"],
            ):
                rc = main()
        self.assertEqual(rc, 1)

    def test_unexpected_exception_returns_one(self):
        """A truly unexpected exception (e.g. KeyError) is caught and returns 1."""
        with mock.patch(
            "siss.main.apply_duotone",
            side_effect=KeyError("unknown"),
        ):
            with mock.patch(
                "sys.argv",
                ["siss", self.input_path, self.output_path, "--effect", "duotone"],
            ):
                rc = main()
        self.assertEqual(rc, 1)


class TestMainPalettePreview(unittest.TestCase):
    """Tests for the --export-palette-preview CLI flag."""

    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.preview_path = os.path.join(self.tmp.name, "preview.png")

    def tearDown(self):
        self.tmp.cleanup()

    def test_export_palette_preview_flag_returns_zero(self):
        with mock.patch("sys.argv", ["siss", "--export-palette-preview", self.preview_path]):
            rc = main()
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(self.preview_path))

    def test_export_palette_preview_with_custom_file(self):
        import json

        palette_path = os.path.join(self.tmp.name, "p.json")
        with open(palette_path, "w") as f:
            json.dump({"brand": {"color1": "#ff0000", "color2": "#0000ff"}}, f)

        with mock.patch(
            "sys.argv",
            [
                "siss",
                "--export-palette-preview",
                self.preview_path,
                "--palette-file",
                palette_path,
            ],
        ):
            rc = main()
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(self.preview_path))


class TestMainExtractFrame(unittest.TestCase):
    """Tests for the --extract-frame CLI flag."""

    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.tmp.name, "clip.mp4")
        self.output_path = os.path.join(self.tmp.name, "frame.png")
        make_test_video(self.input_path, frames=5)

    def tearDown(self):
        self.tmp.cleanup()

    def test_extract_frame_writes_image_without_effect(self):
        with mock.patch(
            "sys.argv",
            ["siss", self.input_path, self.output_path, "--extract-frame", "2"],
        ):
            rc = main()
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(self.output_path))

    def test_extract_frame_rejects_effect_combination(self):
        with mock.patch(
            "sys.argv",
            [
                "siss", self.input_path, self.output_path,
                "--extract-frame", "2", "--effect", "duotone",
            ],
        ):
            rc = main()
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(self.output_path))

    def test_extract_frame_rejects_preview_frame_combination(self):
        with mock.patch(
            "sys.argv",
            [
                "siss", self.input_path, self.output_path,
                "--extract-frame", "2", "--preview-frame", "3",
            ],
        ):
            rc = main()
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(self.output_path))

    def test_extract_frame_requires_image_output(self):
        video_out = os.path.join(self.tmp.name, "out.mp4")
        with mock.patch(
            "sys.argv",
            ["siss", self.input_path, video_out, "--extract-frame", "2"],
        ):
            rc = main()
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(video_out))

    def test_extract_frame_missing_output_fails(self):
        with mock.patch(
            "sys.argv",
            ["siss", self.input_path, "--extract-frame", "2"],
        ):
            rc = main()
        self.assertEqual(rc, 1)


class TestMainSplitView(unittest.TestCase):
    """Tests for the --split-view CLI flag."""

    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.tmp.name, "input.png")
        self.output_path = os.path.join(self.tmp.name, "output.png")
        open(self.input_path, "wb").close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_split_view_vertical_forwards_to_duotone(self):
        with mock.patch("siss.main.apply_duotone") as mock_dt:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--effect", "duotone",
                    "--split-view", "vertical",
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        _, kwargs = mock_dt.call_args
        self.assertEqual(kwargs["split_direction"], "vertical")

    def test_split_view_horizontal_forwards_to_halftone(self):
        with mock.patch("siss.main.apply_halftone") as mock_ht:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--effect", "halftone",
                    "--split-view", "horizontal",
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        _, kwargs = mock_ht.call_args
        self.assertEqual(kwargs["split_direction"], "horizontal")


class TestLoadAndValidateConstraints(unittest.TestCase):
    """Tests for _load_and_validate_constraints()."""

    def setUp(self):
        import json
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self._write = lambda name, data: (
            path := os.path.join(self.tmp.name, name),
            json.dump(data, open(path, "w")),
        )[0]

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_minimal_constraints(self):
        path = self._write("c.json", {"effect": "halftone"})
        from siss.main import _load_and_validate_constraints

        result = _load_and_validate_constraints(path)
        self.assertEqual(result, {"effect": "halftone"})

    def test_valid_full_constraints(self):
        path = self._write("c.json", {
            "effect": "halftone",
            "color1": "#ff0044",
            "color2": "gold",
            "symbol_type": "dot",
            "grid_type": "hex",
            "symbol_size": 12,
            "luminance_curve": {"gamma": 0.8},
        })
        from siss.main import _load_and_validate_constraints

        result = _load_and_validate_constraints(path)
        self.assertEqual(result["effect"], "halftone")
        self.assertEqual(result["luminance_curve"]["gamma"], 0.8)

    def test_unknown_key_raises(self):
        path = self._write("c.json", {"effect": "halftone", "unknown_field": 42})
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("Unknown constraint key", str(ctx.exception))
        self.assertIn("unknown_field", str(ctx.exception))

    def test_multiple_unknown_keys_raises(self):
        path = self._write("c.json", {"a": 1, "b": 2, "c": 3})
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        msg = str(ctx.exception)
        self.assertIn("a", msg)
        self.assertIn("b", msg)
        self.assertIn("c", msg)

    def test_non_object_raises(self):
        path = self._write("c.json", [1, 2, 3])
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("JSON object", str(ctx.exception))

    def test_invalid_effect_value_raises(self):
        path = self._write("c.json", {"effect": "blur"})
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("effect", str(ctx.exception))
        self.assertIn("blur", str(ctx.exception))

    def test_invalid_color1_raises(self):
        path = self._write("c.json", {"color1": "not_a_color"})
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError):
            _load_and_validate_constraints(path)

    def test_valid_color1_passes(self):
        path = self._write("c.json", {"color1": "#abcdef"})
        from siss.main import _load_and_validate_constraints

        _load_and_validate_constraints(path)  # should not raise

    def test_parsed_colors_stored_in_constraints(self):
        path = self._write("c.json", {"color1": "#ff0000", "color2": "navy"})
        from siss.main import _load_and_validate_constraints

        result = _load_and_validate_constraints(path)
        self.assertEqual(result["_parsed_color1"], (255, 0, 0))
        self.assertEqual(result["_parsed_color2"], (0, 0, 128))

    def test_invalid_symbol_type_raises(self):
        path = self._write("c.json", {"symbol_type": "triangle"})
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("symbol_type", str(ctx.exception))

    def test_invalid_grid_type_raises(self):
        path = self._write("c.json", {"grid_type": "circular"})
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("grid_type", str(ctx.exception))

    def test_non_integer_symbol_size_raises(self):
        path = self._write("c.json", {"symbol_size": "large"})
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("symbol_size", str(ctx.exception))

    def test_zero_symbol_size_raises(self):
        path = self._write("c.json", {"symbol_size": 0})
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("symbol_size", str(ctx.exception))

    def test_negative_symbol_size_raises(self):
        path = self._write("c.json", {"symbol_size": -5})
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("symbol_size", str(ctx.exception))

    def test_luminance_curve_non_object_raises(self):
        path = self._write("c.json", {"luminance_curve": 1.5})
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("luminance_curve", str(ctx.exception))

    def test_luminance_curve_negative_gamma_raises(self):
        path = self._write("c.json", {"luminance_curve": {"gamma": -0.5}})
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("gamma", str(ctx.exception))

    def test_luminance_curve_zero_gamma_raises(self):
        path = self._write("c.json", {"luminance_curve": {"gamma": 0}})
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("gamma", str(ctx.exception))

    def test_luminance_curve_inf_gamma_raises(self):
        path = os.path.join(self.tmp.name, "inf.json")
        with open(path, "w") as f:
            f.write('{"luminance_curve": {"gamma": Infinity}}')
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("gamma", str(ctx.exception))

    def test_luminance_curve_negative_inf_gamma_raises(self):
        path = os.path.join(self.tmp.name, "ninf.json")
        with open(path, "w") as f:
            f.write('{"luminance_curve": {"gamma": -Infinity}}')
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("gamma", str(ctx.exception))

    def test_luminance_curve_nan_gamma_raises(self):
        path = os.path.join(self.tmp.name, "nan.json")
        with open(path, "w") as f:
            f.write('{"luminance_curve": {"gamma": NaN}}')
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("gamma", str(ctx.exception))

    def test_luminance_curve_boolean_gamma_raises(self):
        path = self._write("c.json", {"luminance_curve": {"gamma": True}})
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("gamma", str(ctx.exception))

    def test_boolean_symbol_size_raises(self):
        path = self._write("c.json", {"symbol_size": True})
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("symbol_size", str(ctx.exception))

    def test_boolean_gamma_raises(self):
        path = self._write("c.json", {"luminance_curve": {"gamma": True}})
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("gamma", str(ctx.exception))

    def test_luminance_curve_extra_keys_ok(self):
        path = self._write("c.json", {"luminance_curve": {"gamma": 1.2, "extra": 3}})
        from siss.main import _load_and_validate_constraints

        _load_and_validate_constraints(path)  # should not raise

    def test_invalid_json_raises(self):
        path = os.path.join(self.tmp.name, "c.json")
        with open(path, "w") as f:
            f.write("{not json")
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("valid JSON", str(ctx.exception))

    def test_nonexistent_file_raises(self):
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError):
            _load_and_validate_constraints(os.path.join(self.tmp.name, "nope.json"))

    def test_file_size_limit_raises(self):
        path = os.path.join(self.tmp.name, "large.json")
        with open(path, "wb") as f:
            f.seek(2 * 1024 * 1024)
            f.write(b"x")
        from siss.main import _load_and_validate_constraints

        with self.assertRaises(ValueError) as ctx:
            _load_and_validate_constraints(path)
        self.assertIn("1 MiB", str(ctx.exception))


class TestResolveParams(unittest.TestCase):
    """Tests for _resolve_params() precedence: CLI > constraints > palette > default."""

    def test_defaults_applied_with_no_inputs(self):
        from siss.main import _resolve_params

        params = _resolve_params(_ns(), None, None)
        self.assertEqual(params["symbol_size"], 10)
        self.assertEqual(params["symbol_type"], "plus")
        self.assertEqual(params["grid_type"], "square")
        self.assertEqual(params["gamma"], 1.0)

    def test_constraints_override_defaults(self):
        from siss.main import _resolve_params

        constraints = {"symbol_size": 15, "symbol_type": "dot"}
        params = _resolve_params(_ns(), constraints, None)
        self.assertEqual(params["symbol_size"], 15)
        self.assertEqual(params["symbol_type"], "dot")

    def test_cli_overrides_constraints(self):
        from siss.main import _resolve_params

        constraints = {"symbol_size": 15, "symbol_type": "dot"}
        params = _resolve_params(
            _ns(symbol_size=25, symbol_type="slash"), constraints, None
        )
        self.assertEqual(params["symbol_size"], 25)
        self.assertEqual(params["symbol_type"], "slash")

    def test_cli_overrides_constraints_for_effect(self):
        from siss.main import _resolve_params

        constraints = {"effect": "halftone"}
        params = _resolve_params(_ns(effect="duotone"), constraints, None)
        self.assertEqual(params["effect"], "duotone")

    def test_constraints_provide_effect(self):
        from siss.main import _resolve_params

        constraints = {"effect": "halftone"}
        params = _resolve_params(_ns(), constraints, None)
        self.assertEqual(params["effect"], "halftone")

    def test_constraints_effect_none_when_not_provided(self):
        from siss.main import _resolve_params

        params = _resolve_params(_ns(), None, None)
        self.assertIsNone(params["effect"])

    def test_constraints_grid_type_defaults(self):
        from siss.main import _resolve_params

        params = _resolve_params(_ns(), None, None)
        self.assertEqual(params["grid_type"], "square")

    def test_grid_type_from_constraints(self):
        from siss.main import _resolve_params

        constraints = {"grid_type": "hex"}
        params = _resolve_params(_ns(), constraints, None)
        self.assertEqual(params["grid_type"], "hex")

    def test_cli_grid_type_overrides_constraints(self):
        from siss.main import _resolve_params

        constraints = {"grid_type": "hex"}
        params = _resolve_params(_ns(grid_type="square"), constraints, None)
        self.assertEqual(params["grid_type"], "square")


class TestResolveColorsConstraints(unittest.TestCase):
    """Tests for _resolve_colors with constraints precedence."""

    def test_constraints_colors_override_defaults(self):
        c1, c2 = _resolve_colors(
            _ns(),
            None,
            {"color1": "#001122", "color2": "#334455"},
        )
        self.assertEqual(c1, (0, 17, 34))
        self.assertEqual(c2, (51, 68, 85))

    def test_constraints_colors_override_palette(self):
        c1, c2 = _resolve_colors(
            _ns(palette="noir"),
            None,
            {"color1": "#ffffff"},
        )
        self.assertEqual(c1, (255, 255, 255))
        self.assertEqual(c2, (229, 229, 229))  # palette's color2 kept

    def test_cli_colors_override_constraints(self):
        c1, c2 = _resolve_colors(
            _ns(color1=["gold"], color2=["navy"]),
            None,
            {"color1": "#ffffff", "color2": "#000000"},
        )
        self.assertEqual(c1, (255, 215, 0))
        self.assertEqual(c2, (0, 0, 128))

    def test_full_precedence_chain(self):
        c1, c2 = _resolve_colors(
            _ns(palette="noir", color1=["gold"]),
            None,
            {"color1": "#ffffff", "color2": "#000000"},
        )
        self.assertEqual(c1, (255, 215, 0))  # CLI overrides all
        self.assertEqual(c2, (0, 0, 0))       # constraints overrides palette

    def test_constraints_color_passes_parse_color_validation(self):
        _resolve_colors(_ns(), None, {"color1": "#aabbcc", "color2": "navy"})  # noqa

    def test_constraints_color_invalid_raises(self):
        with self.assertRaises(ValueError):
            _resolve_colors(
                _ns(),
                None,
                {"color1": [999, 999, 999]},
            )


class TestDumpConstraints(unittest.TestCase):
    """Tests for _dump_effective_constraints()."""

    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "dumped.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_dump_writes_valid_json(self):
        import json

        from siss.main import _dump_effective_constraints

        params = {
            "effect": "halftone",
            "color1_rgb": (255, 0, 68),
            "color2_rgb": (0, 128, 255),
            "symbol_type": "dot",
            "grid_type": "hex",
            "symbol_size": 12,
            "gamma": 1.0,
        }
        _dump_effective_constraints(params, self.path)
        with open(self.path) as f:
            data = json.load(f)
        self.assertEqual(data["effect"], "halftone")
        self.assertEqual(data["color1"], "#ff0044")
        self.assertEqual(data["color2"], "#0080ff")
        self.assertEqual(data["symbol_type"], "dot")
        self.assertEqual(data["symbol_size"], 12)

    def test_dump_omits_luminance_curve_when_gamma_is_one(self):
        import json

        from siss.main import _dump_effective_constraints

        params = {
            "effect": "halftone",
            "color1_rgb": (0, 0, 0),
            "color2_rgb": (255, 255, 255),
            "symbol_type": "plus",
            "grid_type": "square",
            "symbol_size": 10,
            "gamma": 1.0,
        }
        _dump_effective_constraints(params, self.path)
        with open(self.path) as f:
            data = json.load(f)
        self.assertNotIn("luminance_curve", data)

    def test_dump_includes_luminance_curve_when_gamma_not_one(self):
        import json

        from siss.main import _dump_effective_constraints

        params = {
            "effect": "halftone",
            "color1_rgb": (0, 0, 0),
            "color2_rgb": (255, 255, 255),
            "symbol_type": "plus",
            "grid_type": "square",
            "symbol_size": 10,
            "gamma": 0.8,
        }
        _dump_effective_constraints(params, self.path)
        with open(self.path) as f:
            data = json.load(f)
        self.assertEqual(data["luminance_curve"]["gamma"], 0.8)

    def test_dump_is_reloadable_as_constraints(self):
        from siss.main import _dump_effective_constraints, _load_and_validate_constraints

        params = {
            "effect": "halftone",
            "color1_rgb": (255, 0, 68),
            "color2_rgb": (0, 128, 255),
            "symbol_type": "dot",
            "grid_type": "hex",
            "symbol_size": 12,
            "gamma": 1.2,
        }
        _dump_effective_constraints(params, self.path)
        loaded = _load_and_validate_constraints(self.path)
        self.assertEqual(loaded["effect"], "halftone")
        self.assertEqual(loaded["luminance_curve"]["gamma"], 1.2)

    def test_dump_with_none_effect_raises(self):
        from siss.main import _dump_effective_constraints

        params = {
            "effect": None,
            "color1_rgb": (0, 0, 0),
            "color2_rgb": (255, 255, 255),
            "symbol_type": "plus",
            "grid_type": "square",
            "symbol_size": 10,
            "gamma": 1.0,
        }
        with self.assertRaises(ValueError) as ctx:
            _dump_effective_constraints(params, self.path)
        self.assertIn("effect", str(ctx.exception))


class TestMainConstraintsIntegration(unittest.TestCase):
    """Integration tests for --constraints and --dump-constraints in main()."""

    def setUp(self):
        import json
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.tmp.name, "input.mp4")
        self.output_path = os.path.join(self.tmp.name, "output.mp4")
        open(self.input_path, "wb").close()

        self.constraints_path = os.path.join(self.tmp.name, "constraints.json")
        with open(self.constraints_path, "w") as f:
            json.dump(
                {
                    "effect": "halftone",
                    "color1": "#001122",
                    "color2": "#334455",
                    "symbol_type": "dot",
                    "grid_type": "hex",
                    "symbol_size": 8,
                    "luminance_curve": {"gamma": 0.9},
                },
                f,
            )

    def tearDown(self):
        self.tmp.cleanup()

    def test_constraints_run_calls_apply_halftone(self):
        with mock.patch("siss.main.apply_halftone") as mock_ht:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--constraints",
                    self.constraints_path,
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        mock_ht.assert_called_once()
        call_args = mock_ht.call_args
        self.assertEqual(call_args[0][2], 8)  # symbol_size from constraints
        self.assertEqual(call_args[1].get("symbol_type"), "dot")
        self.assertEqual(call_args[1].get("grid_type"), "hex")
        self.assertEqual(call_args[1].get("gamma"), 0.9)

    def test_constraints_with_cli_overrides(self):
        with mock.patch("siss.main.apply_halftone") as mock_ht:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--constraints",
                    self.constraints_path,
                    "--symbol_size",
                    "20",
                    "--symbol_type",
                    "slash",
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        mock_ht.assert_called_once()
        call_args = mock_ht.call_args
        self.assertEqual(call_args[0][2], 20)  # CLI overrides constraints
        self.assertEqual(call_args[1].get("symbol_type"), "slash")

    def test_split_alt_constraints_forward_alt_halftone_kwargs(self):
        with mock.patch("siss.main.apply_halftone") as mock_ht:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--effect",
                    "halftone",
                    "--split-view",
                    "vertical",
                    "--split-alt-constraints",
                    self.constraints_path,
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        mock_ht.assert_called_once()
        call_args = mock_ht.call_args
        self.assertEqual(call_args[1].get("alt_symbol_type"), "dot")
        self.assertEqual(call_args[1].get("alt_symbol_size"), 8)
        self.assertEqual(call_args[1].get("alt_grid_type"), "hex")
        self.assertEqual(call_args[1].get("alt_gamma"), 0.9)

    def test_dump_constraints_writes_and_exits(self):
        import json

        dump_path = os.path.join(self.tmp.name, "dumped.json")
        with mock.patch("siss.main.apply_halftone"):
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
                    "--dump-constraints",
                    dump_path,
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(dump_path))
        with open(dump_path) as f:
            data = json.load(f)
        self.assertEqual(data["effect"], "halftone")
        self.assertEqual(data["symbol_type"], "dot")
        self.assertEqual(data["grid_type"], "hex")

    def test_constraints_missing_file_returns_error(self):
        with mock.patch(
            "sys.argv",
            [
                "siss",
                self.input_path,
                self.output_path,
                "--constraints",
                os.path.join(self.tmp.name, "nope.json"),
            ],
        ):
            rc = main()
        self.assertEqual(rc, 1)

    def test_constraints_invalid_json_returns_error(self):
        bad_path = os.path.join(self.tmp.name, "bad.json")
        with open(bad_path, "w") as f:
            f.write("{not json")
        with mock.patch(
            "sys.argv",
            [
                "siss",
                self.input_path,
                self.output_path,
                "--constraints",
                bad_path,
            ],
        ):
            rc = main()
        self.assertEqual(rc, 1)

    def test_constraints_effect_alone_still_produces_defaults(self):
        import json

        path = os.path.join(self.tmp.name, "effect_only.json")
        with open(path, "w") as f:
            json.dump({"effect": "halftone"}, f)

        with mock.patch("siss.main.apply_halftone") as mock_ht:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--constraints",
                    path,
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        call_args = mock_ht.call_args
        self.assertEqual(call_args[0][2], 10)  # default symbol_size
        self.assertEqual(call_args[1].get("symbol_type"), "plus")
        self.assertEqual(call_args[1].get("gamma"), 1.0)

    def test_constraints_explicit_cli_effect_overrides(self):
        import json

        path = os.path.join(self.tmp.name, "c.json")
        with open(path, "w") as f:
            json.dump({"effect": "halftone"}, f)

        with mock.patch("siss.main.apply_duotone") as mock_dt:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--effect",
                    "duotone",
                    "--constraints",
                    path,
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        mock_dt.assert_called_once()

    def test_constraints_no_effect_without_cli_or_file_raises(self):
        with mock.patch(
            "sys.argv",
            [
                "siss",
                self.input_path,
                self.output_path,
            ],
        ):
            rc = main()
        self.assertEqual(rc, 1)

    def test_loss_map_flag_forwarded_to_halftone(self):
        loss_path = os.path.join(self.tmp.name, "loss.mp4")
        with mock.patch("siss.main.apply_halftone") as mock_ht:
            with mock.patch(
                "sys.argv",
                [
                    "siss",
                    self.input_path,
                    self.output_path,
                    "--effect", "halftone",
                    "--loss-map", loss_path,
                ],
            ):
                rc = main()
        self.assertEqual(rc, 0)
        self.assertEqual(mock_ht.call_args[1].get("loss_map_path"), loss_path)


class TestGammaInHalftone(unittest.TestCase):
    """Tests for luminance-curve gamma in halftone size computation."""

    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.input_path = os.path.join(self.tmp.name, "input.png")
        self.output_path = os.path.join(self.tmp.name, "output.png")

    def tearDown(self):
        self.tmp.cleanup()

    def test_gamma_one_produces_linear_mapping(self):
        import numpy as np  # noqa: I001

        from siss.halftone import _make_halftone_processor

        frame = np.full((200, 200, 3), 128, dtype=np.uint8)
        proc = _make_halftone_processor(
            10, (0, 0, 0), (255, 255, 255), gamma=1.0
        )
        result = proc(frame)
        self.assertEqual(result.shape, (200, 200, 3))

    def test_gamma_two_suppresses_shadow_growth(self):
        import numpy as np

        from siss.halftone import _make_halftone_processor

        frame = np.full((240, 320, 3), 100, dtype=np.uint8)

        proc_lin = _make_halftone_processor(
            12, (0, 0, 0), (255, 255, 255), gamma=1.0
        )
        proc_g2 = _make_halftone_processor(
            12, (0, 0, 0), (255, 255, 255), gamma=2.0
        )

        lin = proc_lin(frame.copy())
        g2 = proc_g2(frame.copy())

        lin_count = np.sum(np.all(lin == (0, 0, 0), axis=-1))
        g2_count = np.sum(np.all(g2 == (0, 0, 0), axis=-1))

        self.assertGreater(lin_count, g2_count)

    def test_gamma_half_amplifies_shadow_growth(self):
        import numpy as np

        from siss.halftone import _make_halftone_processor

        frame = np.full((240, 320, 3), 180, dtype=np.uint8)

        proc_lin = _make_halftone_processor(
            12, (0, 0, 0), (255, 255, 255), gamma=1.0
        )
        proc_half = _make_halftone_processor(
            12, (0, 0, 0), (255, 255, 255), gamma=0.5
        )

        lin = proc_lin(frame.copy())
        half = proc_half(frame.copy())

        lin_count = np.sum(np.all(lin == (0, 0, 0), axis=-1))
        half_count = np.sum(np.all(half == (0, 0, 0), axis=-1))

        self.assertGreater(half_count, lin_count)

    def test_gamma_negative_raises(self):
        from siss.halftone import _make_halftone_processor

        with self.assertRaises(ValueError):
            _make_halftone_processor(
                10, (0, 0, 0), (255, 255, 255), gamma=-1.0
            )

    def test_gamma_zero_raises(self):
        from siss.halftone import _make_halftone_processor

        with self.assertRaises(ValueError):
            _make_halftone_processor(
                10, (0, 0, 0), (255, 255, 255), gamma=0.0
            )

    def test_apply_halftone_forwards_gamma(self):
        with mock.patch("siss.halftone._make_halftone_processor") as mock_make:
            with mock.patch("siss.halftone.process_media"):
                from siss.halftone import apply_halftone

                apply_halftone(
                    self.input_path,
                    self.output_path,
                    10,
                    (0, 0, 0),
                    (255, 255, 255),
                    gamma=0.7,
                )
        mock_make.assert_called_once()
        self.assertEqual(mock_make.call_args[1]["gamma"], 0.7)


if __name__ == "__main__":
    unittest.main()
