"""
Unit tests for the colors module (Proposal #2: palette & hex input).
"""
import json
import os
import tempfile
import unittest

from siss.colors import (
    PALETTES,
    export_palette_preview,
    get_palette,
    list_palettes,
    load_palette_file,
    parse_color,
    validate_rgb,
)


class TestParseColor(unittest.TestCase):
    """Tests for the flexible color parser."""

    # --- Hex inputs ----------------------------------------------------------
    def test_hex_with_hash_six_digits(self):
        self.assertEqual(parse_color("#ff0044"), (255, 0, 68))

    def test_hex_without_hash_six_digits(self):
        self.assertEqual(parse_color("ff0044"), (255, 0, 68))

    def test_hex_with_hash_three_digits(self):
        # #f04 -> #ff0044
        self.assertEqual(parse_color("#f04"), (255, 0, 68))

    def test_hex_without_hash_three_digits(self):
        self.assertEqual(parse_color("f04"), (255, 0, 68))

    def test_hex_uppercase(self):
        self.assertEqual(parse_color("#FF00AA"), (255, 0, 170))

    def test_hex_black_and_white(self):
        self.assertEqual(parse_color("#000000"), (0, 0, 0))
        self.assertEqual(parse_color("#ffffff"), (255, 255, 255))

    def test_invalid_hex_letters(self):
        with self.assertRaises(ValueError):
            parse_color("#gg0044")

    def test_invalid_hex_length(self):
        with self.assertRaises(ValueError):
            parse_color("#1234")  # 4 digits is neither 3 nor 6

    # --- CSS named colors ----------------------------------------------------
    def test_css_name_lowercase(self):
        self.assertEqual(parse_color("rebeccapurple"), (102, 51, 153))

    def test_css_name_mixed_case(self):
        self.assertEqual(parse_color("DarkSlateBlue"), (72, 61, 139))

    def test_css_name_uppercase(self):
        self.assertEqual(parse_color("RED"), (255, 0, 0))

    def test_css_name_whitespace(self):
        self.assertEqual(parse_color("  red  "), (255, 0, 0))

    def test_css_name_not_found(self):
        with self.assertRaises(ValueError):
            parse_color("notacolor")

    # --- RGB triples (backward compatibility) --------------------------------
    def test_rgb_list_of_ints(self):
        self.assertEqual(parse_color([255, 0, 0]), (255, 0, 0))

    def test_rgb_tuple_of_ints(self):
        self.assertEqual(parse_color((0, 255, 255)), (0, 255, 255))

    def test_rgb_list_of_strings(self):
        # argparse may hand us string values
        self.assertEqual(parse_color(["255", "0", "0"]), (255, 0, 0))

    def test_rgb_string_space_separated(self):
        self.assertEqual(parse_color("255 0 0"), (255, 0, 0))

    def test_rgb_string_comma_separated(self):
        self.assertEqual(parse_color("255,0,0"), (255, 0, 0))

    def test_rgb_string_comma_space_separated(self):
        self.assertEqual(parse_color("255, 0, 0"), (255, 0, 0))

    def test_rgb_out_of_range(self):
        with self.assertRaises(ValueError):
            parse_color([300, 0, 0])
        with self.assertRaises(ValueError):
            parse_color([-10, 0, 0])

    def test_rgb_wrong_length(self):
        with self.assertRaises(ValueError):
            parse_color([255, 0])
        with self.assertRaises(ValueError):
            parse_color([255, 0, 0, 0])

    # --- Edge cases / disambiguation ----------------------------------------
    def test_empty_string(self):
        with self.assertRaises(ValueError):
            parse_color("")

    def test_unsupported_type(self):
        with self.assertRaises(ValueError):
            parse_color(3.14)
        with self.assertRaises(ValueError):
            parse_color(None)

    def test_bare_hex_token_parsed_as_hex(self):
        # "bad" is not a CSS named color, and all its letters (b, a, d) are
        # valid hex digits of length 3, so it is read as the 3-digit hex
        # #bad -> #bbaadd = (187, 170, 221).
        self.assertEqual(parse_color("bad"), (187, 170, 221))

    def test_hash_takes_priority_over_css_name(self):
        # Even if a token looks name-like, a leading '#' means hex.
        # '#red' is invalid hex, so it should raise rather than silently
        # falling back to the CSS name "red".
        with self.assertRaises(ValueError):
            parse_color("#red")


class TestPalettes(unittest.TestCase):
    """Tests for curated palettes."""

    def test_get_palette_returns_two_rgb_tuples(self):
        c1, c2 = get_palette("sunset")
        self.assertEqual(c1, (59, 31, 75))   # #3b1f4b
        self.assertEqual(c2, (246, 196, 83))  # #f6c453

    def test_get_palette_case_insensitive(self):
        self.assertEqual(get_palette("SUNSET"), get_palette("sunset"))
        self.assertEqual(get_palette("CyberPunk"), get_palette("cyberpunk"))

    def test_get_palette_with_whitespace(self):
        self.assertEqual(get_palette("  mint  "), get_palette("mint"))

    def test_unknown_palette_raises_with_hint(self):
        with self.assertRaises(ValueError) as ctx:
            get_palette("nonexistent")
        # Error message should list available palettes to help discovery.
        self.assertIn("sunset", str(ctx.exception))
        self.assertIn("cyberpunk", str(ctx.exception))

    def test_all_palette_colors_are_valid_hex(self):
        # Every palette entry must parse cleanly into a valid RGB tuple.
        for name, palette in PALETTES.items():
            for slot in ("color1", "color2"):
                rgb = parse_color(palette[slot])
                self.assertEqual(len(rgb), 3, f"{name}.{slot}")
                for channel in rgb:
                    self.assertTrue(
                        0 <= channel <= 255, f"{name}.{slot} out of range"
                    )

    def test_list_palettes_mentions_every_palette(self):
        catalog = list_palettes()
        for name in PALETTES.keys():
            self.assertIn(name, catalog)


class TestLoadPaletteFile(unittest.TestCase):
    """Tests for load_palette_file() and custom palette integration."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, filename, data):
        path = os.path.join(self.tmp.name, filename)
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_loads_valid_palette_file(self):
        path = self._write("p.json", {"brand": {"color1": "#ff0044", "color2": "#0066ff"}})
        palettes = load_palette_file(path)
        self.assertEqual(palettes["brand"], ((255, 0, 68), (0, 102, 255)))

    def test_names_are_lowercased(self):
        path = self._write("p.json", {"MyBrand": {"color1": "#ff0044", "color2": "#0066ff"}})
        palettes = load_palette_file(path)
        self.assertIn("mybrand", palettes)

    def test_multiple_palettes(self):
        path = self._write("p.json", {
            "a": {"color1": "red", "color2": "blue"},
            "b": {"color1": "gold", "color2": "navy"},
        })
        palettes = load_palette_file(path)
        self.assertEqual(len(palettes), 2)
        self.assertEqual(palettes["a"], ((255, 0, 0), (0, 0, 255)))

    def test_missing_color1_raises(self):
        path = self._write("p.json", {"brand": {"color2": "#0066ff"}})
        with self.assertRaises(ValueError) as ctx:
            load_palette_file(path)
        self.assertIn("color1", str(ctx.exception))

    def test_missing_color2_raises(self):
        path = self._write("p.json", {"brand": {"color1": "#ff0044"}})
        with self.assertRaises(ValueError) as ctx:
            load_palette_file(path)
        self.assertIn("color2", str(ctx.exception))

    def test_invalid_color_raises(self):
        path = self._write("p.json", {"brand": {"color1": "notacolor", "color2": "#0066ff"}})
        with self.assertRaises(ValueError):
            load_palette_file(path)

    def test_invalid_json_raises(self):
        path = os.path.join(self.tmp.name, "p.json")
        with open(path, "w") as f:
            f.write("{not valid json")
        with self.assertRaises(ValueError) as ctx:
            load_palette_file(path)
        self.assertIn("Invalid JSON", str(ctx.exception))

    def test_non_object_root_raises(self):
        path = os.path.join(self.tmp.name, "p.json")
        with open(path, "w") as f:
            f.write("[1, 2, 3]")
        with self.assertRaises(ValueError) as ctx:
            load_palette_file(path)
        self.assertIn("JSON object", str(ctx.exception))

    def test_entry_not_a_dict_raises(self):
        path = self._write("p.json", {"brand": "not_an_object"})
        with self.assertRaises(ValueError) as ctx:
            load_palette_file(path)
        self.assertIn("must be an object", str(ctx.exception))

    def test_file_not_found_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_palette_file(os.path.join(self.tmp.name, "nonexistent.json"))

    def test_name_too_long_raises(self):
        long_name = "a" * 65
        path = self._write("p.json", {long_name: {"color1": "#ff0000", "color2": "#0000ff"}})
        with self.assertRaises(ValueError) as ctx:
            load_palette_file(path)
        self.assertIn("65 characters", str(ctx.exception))

    def test_name_at_limit_is_accepted(self):
        exact_name = "b" * 64
        path = self._write("p.json", {exact_name: {"color1": "#ff0000", "color2": "#0000ff"}})
        palettes = load_palette_file(path)
        self.assertIn(exact_name, palettes)


class TestCustomPalettesIntegration(unittest.TestCase):
    """Tests for get_palette() and list_palettes() with custom palettes."""

    def setUp(self):
        self.custom = {
            "brand": ((10, 20, 30), (40, 50, 60)),
            "sunset": ((255, 255, 255), (0, 0, 0)),
        }

    def test_get_palette_returns_custom_when_present(self):
        c1, c2 = get_palette("brand", self.custom)
        self.assertEqual(c1, (10, 20, 30))

    def test_get_palette_custom_overrides_builtin(self):
        c1, c2 = get_palette("sunset", self.custom)
        self.assertEqual(c1, (255, 255, 255))

    def test_get_palette_falls_back_to_builtin(self):
        c1, c2 = get_palette("noir", self.custom)
        self.assertEqual(c1, (0, 0, 0))

    def test_get_palette_unknown_with_custom_loaded_lists_all(self):
        with self.assertRaises(ValueError) as ctx:
            get_palette("nonexistent", self.custom)
        msg = str(ctx.exception)
        self.assertIn("brand", msg)
        self.assertIn("sunset", msg)

    def test_get_palette_accepts_none(self):
        c1, c2 = get_palette("noir", None)
        self.assertEqual(c1, (0, 0, 0))

    def test_list_palettes_includes_custom_names(self):
        catalog = list_palettes(self.custom)
        self.assertIn("brand", catalog)
        self.assertIn("Custom palettes", catalog)

    def test_list_palettes_marks_overrides(self):
        catalog = list_palettes(self.custom)
        self.assertIn("overrides built-in", catalog)

    def test_list_palettes_accepts_none(self):
        catalog = list_palettes(None)
        self.assertIn("sunset", catalog)


class TestValidateRgb(unittest.TestCase):
    """Tests for the shared RGB validator."""

    def test_valid_tuple_returned_as_is(self):
        self.assertEqual(validate_rgb((255, 0, 68)), (255, 0, 68))

    def test_valid_list_returned_as_tuple(self):
        self.assertEqual(validate_rgb([10, 20, 30]), (10, 20, 30))

    def test_wrong_length_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_rgb((1, 2))
        with self.assertRaises(ValueError):
            validate_rgb((1, 2, 3, 4))

    def test_out_of_range_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_rgb((256, 0, 0))
        with self.assertRaises(ValueError):
            validate_rgb((-1, 0, 0))

    def test_non_integer_channel_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_rgb((1.5, 2, 3))
        with self.assertRaises(ValueError):
            validate_rgb(("1", 2, 3))

    def test_boolean_channel_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_rgb((True, 0, 0))
        with self.assertRaises(ValueError):
            validate_rgb((False, 0, 0))

    def test_non_iterable_input_raises_value_error_not_type_error(self):
        with self.assertRaises(ValueError):
            validate_rgb(5)
        with self.assertRaises(ValueError):
            validate_rgb(None)


class TestExportPalettePreview(unittest.TestCase):
    """Tests for the palette preview contact-sheet renderer."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.output_path = os.path.join(self.tmp.name, "preview.png")

    def tearDown(self):
        self.tmp.cleanup()

    def test_preview_renders_png(self):
        export_palette_preview(self.output_path)
        self.assertTrue(os.path.isfile(self.output_path))
        self.assertGreater(os.path.getsize(self.output_path), 0)

    def test_preview_with_no_custom_palettes(self):
        export_palette_preview(self.output_path, custom_palettes=None)
        self.assertTrue(os.path.isfile(self.output_path))

    def test_preview_includes_custom_palettes(self):
        custom = {
            "brand": ((10, 20, 30), (40, 50, 60)),
            "test": ((200, 200, 200), (50, 50, 50)),
        }
        export_palette_preview(self.output_path, custom_palettes=custom)
        self.assertTrue(os.path.isfile(self.output_path))

    def test_preview_skips_builtin_shadowed_by_custom(self):
        custom = {"sunset": ((0, 0, 0), (255, 255, 255))}
        export_palette_preview(self.output_path, custom_palettes=custom)
        self.assertTrue(os.path.isfile(self.output_path))


class TestLoadPaletteFileSizeLimit(unittest.TestCase):
    """Tests for the 1 MiB file-size guard in load_palette_file."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "palettes.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_file_at_limit_is_accepted(self):
        name = "a"
        c1_hex = '"#000"'
        c2_hex = '"#fff"'
        obj = f'{{"{name}":{{"color1":{c1_hex},"color2":{c2_hex}}}}}'
        content = obj.encode()
        padding_len = 1 * 1024 * 1024 - len(content)
        if padding_len < 0:
            self.skipTest("JSON content exceeds size limit; cannot construct boundary test")
        with open(self.path, "wb") as f:
            f.write(content)
            if padding_len > 0:
                f.write(b"\n" + b" " * (padding_len - 1))
        self.assertEqual(os.path.getsize(self.path), 1 * 1024 * 1024)
        result = load_palette_file(self.path)
        self.assertIn(name, result)
        self.assertEqual(result[name], ((0, 0, 0), (255, 255, 255)))

    def test_file_one_byte_over_limit_raises(self):
        with open(self.path, "wb") as f:
            f.write(b" " * (1 * 1024 * 1024 + 1))
        with self.assertRaises(ValueError) as ctx:
            load_palette_file(self.path)
        self.assertIn("1 MiB", str(ctx.exception))

    def test_small_valid_file_is_accepted(self):
        with open(self.path, "w") as f:
            json.dump({"p": {"color1": "#ff0000", "color2": "#0000ff"}}, f)
        result = load_palette_file(self.path)
        self.assertIn("p", result)

    def test_empty_file_is_accepted(self):
        with open(self.path, "w") as f:
            f.write("{}")
        result = load_palette_file(self.path)
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
