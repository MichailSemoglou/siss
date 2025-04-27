# Siss

A command-line utility for applying artistic effects to videos.

## Key Features

- **Duotone Effect**: Creates stylish two-color videos, mapping colors to dark and light areas
- **Halftone Effect**: Creates artistic videos using symbol patterns that vary in size based on brightness
- **Cross-platform Compatibility**: Works on Windows, macOS, and Linux with automatic codec detection
- **Progress Tracking**: Shows real-time processing progress with estimated completion time

## Installation

```bash
pip install siss
```

## Quick Start

After installation, you can use Siss either as a command-line tool:

```bash
siss input_video.mp4 output_video.mp4 --effect duotone
```

## Example Effects

### Duotone Effect

![Duotone Example](https://raw.githubusercontent.com/MichailSemoglou/siss/main/examples/duotone_example.jpg)

```bash
siss input.mp4 output.mp4 --effect duotone --color1 56 12 45 --color2 217 237 3
```

This applies a duotone effect with deep purple for dark areas and bright yellow-green for light areas.

### Halftone Effect

![Halftone Example](https://raw.githubusercontent.com/MichailSemoglou/siss/main/examples/halftone_example.jpg)

```bash
siss input.mp4 output.mp4 --effect halftone --symbol_type asterisk --symbol_size 12
```

This applies a halftone effect with asterisk symbols of varying sizes.

## Documentation

For complete documentation, visit the [GitHub repository](https://github.com/MichailSemoglou/siss).

## Requirements

- Python 3.6+
- OpenCV (cv2)
- NumPy
- tqdm
