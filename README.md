# Siss

A command-line utility for applying artistic effects to videos.

![GitHub license](https://img.shields.io/github/license/MichailSemoglou/siss)
![Python version](https://img.shields.io/badge/python-3.6%2B-blue)

## Features

- **Duotone Effect**: Creates a video with two selected colors mapped to dark and light areas
- **Halftone Effect**: Creates a video with symbol patterns of varying sizes to represent dark and light areas
- **Cross-platform Compatibility**: Handles codec differences between operating systems
- **Progress Tracking**: Shows real-time progress during video processing

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
python -m src.main input_video.mp4 output_video.mp4 --effect duotone
```

Or if installed using pip:

```bash
siss input_video.mp4 output_video.mp4 --effect duotone
```

The tool supports various video formats including MP4, MOV, AVI, and more. The output format is determined by the file extension you specify for the output file.

### Duotone Effect

```bash
python -m src.main input_video.mp4 output_duotone.mp4 --effect duotone --color1 255 0 0 --color2 0 255 255
```

This applies a duotone effect with red for dark areas and cyan for light areas.

### Halftone Effect

```bash
python -m src.main input_video.mp4 output_halftone.mp4 --effect halftone --symbol_size 12 --symbol_type asterisk --color1 0 0 0 --color2 255 255 255
```

This applies a halftone effect with black asterisks on a white background.

### Codec Compatibility Fix

If you encounter issues with codecs (especially on different operating systems), use the `--use-codec-fix` option:

```bash
python -m src.main input_video.mp4 output_video.mp4 --effect duotone --use-codec-fix
```

This option uses an adaptive approach to find compatible codecs for your specific system.

### Available Options

- `--effect`: Choose between `duotone` or `halftone` (required)
- `--color1`: First color in RGB format (default: 255 0 0, red)
- `--color2`: Second color in RGB format (default: 0 255 255, cyan)
- `--symbol_size`: Size of symbols for halftone effect (default: 10)
- `--symbol_type`: Type of symbol for halftone effect (choices: plus, asterisk, slash, default: plus)
- `--use-codec-fix`: Use adaptive codec selection for cross-platform compatibility

## Examples

### Creating a blue/yellow duotone effect:

```bash
python -m src.main video.mp4 blue_yellow.mp4 --effect duotone --color1 0 0 255 --color2 255 255 0
```

### Creating a halftone effect with slash symbols:

```bash
python -m src.main video.mp4 halftone_slashes.mp4 --effect halftone --symbol_type slash --symbol_size 15
```

### Using MOV files:

```bash
python -m src.main input.mov output.mov --effect duotone --color1 0 0 255 --color2 255 255 0
```

## Project Structure

- `src/`
  - `main.py`: Command-line interface for the tool
  - `duotone.py`: Contains the duotone effect implementation
  - `halftone.py`: Contains the halftone effect implementation
  - `codec_fix.py`: Handles cross-platform codec compatibility
  - `utils/`
    - `video_processing.py`: Utility functions for video handling

## Requirements

- Python 3.6+
- OpenCV (cv2)
- NumPy
- tqdm

## Troubleshooting

### Video Output Issues

If you encounter issues with video output:

1. Try using the `--use-codec-fix` option to automatically find a compatible codec
2. Check that you have the necessary codecs installed for your operating system
3. If creating MP4 files on Windows, try using AVI format instead

### Memory Limitations

For large videos, the tool processes frames sequentially to minimize memory usage. If you still experience memory issues:

1. Try processing a shorter clip first
2. Reduce the resolution of your input video

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
