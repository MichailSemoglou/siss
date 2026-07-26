# Siss

A command-line tool for applying duotone and halftone effects to video and
still-image files. Duotone maps per-pixel luminance to a linear blend between
two user-supplied RGB colors; halftone renders plus, asterisk, slash, or dot
symbols at luminance-proportional sizes over a 3×3-pixel sampled grid, on a
square or hex-offset screen. Accepts hex strings, CSS named colors, RGB triples,
and named two-color palettes.

![GitHub license](https://img.shields.io/github/license/MichailSemoglou/siss)
![Python version](https://img.shields.io/badge/python-3.7%2B-blue)
![PyPI version](https://img.shields.io/pypi/v/siss)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/siss?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=BLUE&left_text=downloads)](https://pepy.tech/projects/siss)
![GitHub issues](https://img.shields.io/github/issues/MichailSemoglou/siss)
![GitHub last commit](https://img.shields.io/github/last-commit/MichailSemoglou/siss)

## Features

- **Duotone** – maps per-pixel luminance to a linear gradient between two RGB colors; `color1` is applied to dark areas, `color2` to light areas
- **Halftone** – renders plus, asterisk, slash, or dot symbols at sizes proportional to local luminance (3×3-pixel sampled average), with independent symbol and background colors, over a square or hex-offset sampling grid
- **Color input** – accepts 3- and 6-digit hex strings (with or without `#`), case-insensitive CSS named colors, RGB integer triples, and named two-color palettes via `--palette`
- **Codec selection** – probes `cv2.VideoWriter_fourcc` candidates per output format and OS at runtime; falls back through a priority list until a working codec is found
- **Audio passthrough** – after rendering, merges the original audio track into the output with `ffmpeg` (no video re-encode); disable with `--no-audio`
- **Output formats** – writes MP4, MOV, AVI, MKV, and WMV videos, plus PNG, JPEG, BMP, TIFF, and WebP still images; the format is inferred from the output file extension
- **Custom palettes** – load your own two-color looks from a JSON file with `--palette-file`; custom names shadow built-in ones

## Installation

### Install from PyPI

```bash
pip install siss
```

### Clone for Development

1. Clone this repository:

   ```bash
   git clone https://github.com/MichailSemoglou/siss.git
   cd siss
   ```

2. Create a virtual environment (recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Install the package so the `siss` command is available:
   ```bash
   pip install .
   # or, for an editable install that picks up source changes:
   pip install -e .
   ```

## Usage

### Basic Usage

```bash
siss input_video.mp4 output_video.mp4 --effect duotone
```

For a source checkout without installing:

```bash
PYTHONPATH=src python3 -m siss.main input_video.mp4 output_video.mp4 --effect duotone
```

The output format is determined by the file extension of the output path. Supported video containers: MP4, MOV, AVI, MKV, WMV. Supported still-image formats: PNG, JPEG, BMP, TIFF, WebP.

### Specifying Colors

Siss accepts colors in any of these forms:

| Form                                         | Example                                   |
| -------------------------------------------- | ----------------------------------------- |
| Hex string (with/without `#`, 3- or 6-digit) | `--color1 "#ff0044"` or `--color1 ff0044` |
| CSS named color                              | `--color1 rebeccapurple`                  |
| RGB triple (original syntax)                 | `--color1 255 0 0`                        |

> **Shell note:** quote hex values that start with `#` to prevent your shell from treating the character as a comment: `"#ff0044"`.

You can also select a complete two-color look with `--palette`:

```bash
siss input_video.mp4 output_duotone.mp4 --effect duotone --palette sunset
```

Browse the built-in palettes:

```bash
siss --list-palettes
```

Individual `--color1` and `--color2` flags override single slots of a selected palette. Precedence: explicit flag > palette > default (red / cyan).

### Duotone Effect

```bash
siss input_video.mp4 output_duotone.mp4 --effect duotone --color1 255 0 0 --color2 0 255 255
```

Applies a duotone effect with red mapped to dark areas and cyan to light areas.

Using a hex color and a CSS name:

```bash
siss input_video.mp4 output_duotone.mp4 --effect duotone --color1 "#3b1f4b" --color2 gold
```

Using a palette:

```bash
siss input_video.mp4 output_duotone.mp4 --effect duotone --palette cyberpunk
```

### Halftone Effect

```bash
siss input_video.mp4 output_halftone.mp4 --effect halftone --symbol_size 12 --symbol_type asterisk --color1 0 0 0 --color2 255 255 255
```

Applies a halftone effect with black asterisks on a white background.

For the classic print-halftone look, use `dot` symbols on a `hex` grid, which staggers alternating rows by half a step to produce the interlocking dot screen of traditional print reproduction:

```bash
siss input_video.mp4 output_halftone.mp4 --effect halftone --symbol_type dot --grid_type hex --color1 0 0 0 --color2 255 255 255
```

### Still Images

This mode accepts still-image input and output paths only; it does not extract a frame from a video file:

```bash
siss input.jpg output.png --effect duotone --palette sunset
```

The input and output formats do not need to match; `siss` reads and writes through OpenCV's `cv2.imread`/`cv2.imwrite` for image paths.

### Codec Compatibility

Codec selection for video output is **automatic** — the tool probes available `cv2.VideoWriter_fourcc` candidates at runtime based on your OS and output container, falling back through a priority list until a working codec is found. No extra flags are needed.

### Available Options

- `--effect` – `duotone` or `halftone` (required)
- `--color1` – first color: hex `#ff0044`, CSS name `rebeccapurple`, or RGB `255 0 0`. Default: red. Dark areas in duotone, symbols in halftone.
- `--color2` – second color, same accepted forms. Default: cyan. Light areas in duotone, background in halftone.
- `--palette` – named two-color palette (overrides the defaults; `--color1` and `--color2` override individual slots)
- `--list-palettes` – print available palettes and exit
- `--symbol_size` – symbol size for halftone (default: `10`)
- `--symbol_type` – halftone symbol shape: `plus`, `asterisk`, `slash`, or `dot` (default: `plus`)
- `--grid_type` – halftone sampling grid: `square` or `hex` (default: `square`); `hex` staggers alternating rows by half a step for a traditional print-halftone dot screen
- `--no-audio` – skip merging the original audio track into the output video (default: merge audio when `ffmpeg` is available)
- `--palette-file` – path to a JSON file of custom palettes; each entry must have `"color1"` and `"color2"` keys in the same formats as `--color1`/`--color2`. Custom names override built-in ones.

## Examples

Blue/yellow duotone:

```bash
siss video.mp4 blue_yellow.mp4 --effect duotone --color1 0 0 255 --color2 255 255 0
```

Halftone with slash symbols:

```bash
siss video.mp4 halftone_slashes.mp4 --effect halftone --symbol_type slash --symbol_size 15
```

Classic print-style halftone dots on a hex-offset grid:

```bash
siss video.mp4 halftone_dots.mp4 --effect halftone --symbol_type dot --grid_type hex --symbol_size 15
```

MOV input and output:

```bash
siss input.mov output.mov --effect duotone --color1 0 0 255 --color2 255 255 0
```

Disable audio passthrough:

```bash
siss input.mp4 output.mp4 --effect halftone --no-audio
```

Load custom palettes from a file:

```bash
siss input.mp4 output.mp4 --effect duotone --palette-file examples/custom-palettes.json --palette brand-warm
```

## Project Structure

- `src/siss/`
  - `main.py` – command-line interface and argument parsing
  - `audio.py` – ffmpeg audio-track passthrough for video output
  - `colors.py` – hex, CSS name, and RGB parsing; curated palette registry; custom palette file loading
  - `duotone.py` – per-frame luminance-to-gradient mapping
  - `halftone.py` – per-frame symbol rendering at luminance-proportional sizes
  - `codec_fix.py` – adaptive `cv2.VideoWriter_fourcc` selection per OS and format
  - `utils/`
    - `video_processing.py` – frame-by-frame video processing, still-image processing, and format/canvas utilities

## Requirements

- Python 3.7+
- OpenCV (`cv2`)
- NumPy
- tqdm
- ffmpeg (optional — for audio passthrough in video output)

## Troubleshooting

### Video Output Issues

If you encounter video output errors:

1. Verify that the required codecs are installed for your operating system.
2. On Windows, try AVI output if MP4 encoding fails.

### Memory Usage

Frames are processed sequentially to keep memory use bounded. For large inputs:

1. Test on a short clip before processing the full video.
2. Reduce the resolution of the input before passing it to `siss`.

## Contributing

To contribute:

1. Fork the repository.
2. Install the development dependencies: optionally `pip install -e .` for an editable install, then `pip install -r requirements-dev.txt`.
3. Run the test suite: `pytest`.
4. Create a feature branch: `git checkout -b feature/short-description`.
5. Commit your changes: `git commit -m 'Add halftone slash rendering'`.
6. Push to the branch: `git push origin feature/short-description`.
7. Open a pull request describing what changed and why.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

MIT. See the [LICENSE](LICENSE) file for terms.
