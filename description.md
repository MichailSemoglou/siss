# Siss

A command-line tool for applying duotone and halftone effects to video files.
Duotone maps per-pixel luminance to a linear blend between two user-supplied
RGB colors; halftone renders plus, asterisk, slash, or dot symbols at
luminance-proportional sizes, on a square or hex-offset grid. Accepts hex
strings, CSS named colors, RGB triples, and named two-color palettes.

## Features

- **Duotone** – maps per-pixel luminance to a linear gradient between two RGB colors; `color1` is applied to dark areas, `color2` to light areas
- **Halftone** – renders plus, asterisk, slash, or dot symbols at sizes proportional to local luminance, with independent symbol and background colors, over a square or hex-offset sampling grid
- **Color input** – accepts 3- and 6-digit hex strings (with or without `#`), case-insensitive CSS named colors, RGB integer triples, and named two-color palettes via `--palette`
- **Codec selection** – probes `cv2.VideoWriter_fourcc` candidates per output format and OS; falls back through a priority list until a working codec is found

## Installation

```bash
pip install siss
```

## Quick Start

After installation, run `siss` from the command line:

```bash
siss input_video.mp4 output_video.mp4 --effect duotone
```

## Specifying Colors

Colors accept hex strings, CSS names, RGB triples, or curated palettes:

```bash
siss input.mp4 output.mp4 --effect duotone --color1 "#3b1f4b" --color2 gold
siss input.mp4 output.mp4 --effect duotone --palette sunset
siss --list-palettes
```

## Example Effects

### Duotone Effect

![Duotone Example](https://raw.githubusercontent.com/MichailSemoglou/siss/main/examples/duotone_example.jpg)

```bash
siss input.mp4 output.mp4 --effect duotone --color1 56 12 45 --color2 217 237 3
```

Applies a duotone effect with deep purple mapped to dark areas and bright yellow-green to light areas.

### Halftone Effect

![Halftone Example](https://raw.githubusercontent.com/MichailSemoglou/siss/main/examples/halftone_example.jpg)

```bash
siss input.mp4 output.mp4 --effect halftone --symbol_type slash --symbol_size 20 --color1 56 12 45 --color2 217 237 3
```

Applies a halftone effect with slash symbols at luminance-proportional sizes.

## Documentation

See the [GitHub repository](https://github.com/MichailSemoglou/siss) for full documentation.

## Requirements

- Python 3.7+
- OpenCV (`cv2`)
- NumPy
- tqdm
