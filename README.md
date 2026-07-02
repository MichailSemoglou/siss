# Siss

A command-line tool for applying duotone and halftone effects to video files.
Duotone maps per-pixel luminance to a linear blend between two user-supplied
RGB colors; halftone renders plus, asterisk, slash, or dot symbols at
luminance-proportional sizes over a 3×3-pixel sampled grid, on a square or
hex-offset screen. Accepts hex strings, CSS named colors, RGB triples, and
named two-color palettes.

![GitHub license](https://img.shields.io/github/license/MichailSemoglou/siss)
![Python version](https://img.shields.io/badge/python-3.7%2B-blue)
![PyPI version](https://img.shields.io/pypi/v/siss)
![PyPI downloads](https://img.shields.io/pypi/dm/siss)
![GitHub issues](https://img.shields.io/github/issues/MichailSemoglou/siss)
![GitHub last commit](https://img.shields.io/github/last-commit/MichailSemoglou/siss)

## Features

- **Duotone** – maps per-pixel luminance to a linear gradient between two RGB colors; `color1` is applied to dark areas, `color2` to light areas
- **Halftone** – renders plus, asterisk, slash, or dot symbols at sizes proportional to local luminance (3×3-pixel sampled average), with independent symbol and background colors, over a square or hex-offset sampling grid
- **Color input** – accepts 3- and 6-digit hex strings (with or without `#`), case-insensitive CSS named colors, RGB integer triples, and named two-color palettes via `--palette`
- **Codec selection** – probes `cv2.VideoWriter_fourcc` candidates per output format and OS at runtime; falls back through a priority list until a working codec is found
- **Output formats** – writes MP4, MOV, AVI, MKV, and WMV; the container is inferred from the output file extension

## Installation

### Option 1: Clone and Install

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

### Option 2: Install from Source

```bash
pip install siss
```

## Usage

### Basic Usage

```bash
siss input_video.mp4 output_video.mp4 --effect duotone
```

For a source checkout without installing:

```bash
python3 src/main.py input_video.mp4 output_video.mp4 --effect duotone
```

The output format is determined by the file extension of the output path. Supported containers: MP4, MOV, AVI, MKV, WMV.

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

### Codec Compatibility

If you encounter codec errors, add `--use-codec-fix`:

```bash
siss input_video.mp4 output_video.mp4 --effect duotone --use-codec-fix
```

`--use-codec-fix` probes `cv2.VideoWriter_fourcc` candidates at startup and selects the first codec that opens successfully for the output container.

### Available Options

- `--effect` – `duotone` or `halftone` (required)
- `--color1` – first color: hex `#ff0044`, CSS name `rebeccapurple`, or RGB `255 0 0`. Default: red. Dark areas in duotone, symbols in halftone.
- `--color2` – second color, same accepted forms. Default: cyan. Light areas in duotone, background in halftone.
- `--palette` – named two-color palette (overrides the defaults; `--color1` and `--color2` override individual slots)
- `--list-palettes` – print available palettes and exit
- `--symbol_size` – symbol size for halftone (default: `10`)
- `--symbol_type` – halftone symbol shape: `plus`, `asterisk`, `slash`, or `dot` (default: `plus`)
- `--grid_type` – halftone sampling grid: `square` or `hex` (default: `square`); `hex` staggers alternating rows by half a step for a traditional print-halftone dot screen
- `--use-codec-fix` – enable adaptive codec selection

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

## Project Structure

- `src/`
  - `main.py` – command-line interface and argument parsing
  - `colors.py` – hex, CSS name, and RGB parsing; curated palette registry
  - `duotone.py` – per-frame luminance-to-gradient mapping
  - `halftone.py` – per-frame symbol rendering at luminance-proportional sizes
  - `codec_fix.py` – adaptive `cv2.VideoWriter_fourcc` selection per OS and format
  - `utils/`
    - `video_processing.py` – frame extraction, writing, and video property utilities

## Requirements

- Python 3.7+
- OpenCV (`cv2`)
- NumPy
- tqdm

## Troubleshooting

### Video Output Issues

If you encounter video output errors:

1. Add `--use-codec-fix` to enable adaptive codec selection.
2. Verify that the required codecs are installed for your operating system.
3. On Windows, try AVI output if MP4 encoding fails.

### Memory Usage

Frames are processed sequentially to keep memory use bounded. For large inputs:

1. Test on a short clip before processing the full video.
2. Reduce the resolution of the input before passing it to `siss`.

## Contributing

To contribute:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/short-description`.
3. Commit your changes: `git commit -m 'Add halftone slash rendering'`.
4. Push to the branch: `git push origin feature/short-description`.
5. Open a pull request describing what changed and why.

## License

MIT. See the [LICENSE](LICENSE) file for terms.
