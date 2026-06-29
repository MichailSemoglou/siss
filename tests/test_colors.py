"""
Unit tests for the colors module (Proposal #2: palette & hex input).
"""
import unittest
from colors import (
    parse_color,
    get_palette,
    list_palettes,
    PALETTES,
    CSS_NAMED_COLORS,
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


if __name__ == "__main__":
    unittest.main()