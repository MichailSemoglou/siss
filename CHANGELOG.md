# Changelog

All notable changes to the Siss project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.1] - 2026-07-20

### Changed

- Vectorized the halftone renderer. The per-cell Python loops over the sampling grid are replaced by NumPy operations: the luminance grid is computed once from an integral image, symbol sizes derive from it in bulk, and same-sized symbols are drawn with vectorized index operations. Diagonal strokes touching the right or bottom frame edge are still drawn per cell with OpenCV, preserving the clamped-endpoint rasterization of the previous renderer. Output is pixel-identical to 0.5.0; rendering a 1920x1080 frame at the default symbol size drops from about 197 ms to about 9 ms.

### Added

- Solid-frame regression tests for the halftone image path in `tests/test_halftone.py`: a white input renders background only, a black input renders maximum-size symbols, checked for every symbol type and grid type.

### Fixed

- `validate_codec` in `src/codec_fix.py` now releases the probe `VideoWriter` on every exit path; previously it leaked the writer when initialization failed or an exception occurred mid-test.
- Removed an unused `subprocess` import from `src/codec_fix.py`.

## [0.5.0] - 2026-07-12

### Added

- Still-image input and output. Passing an image extension (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`, `.tif`, `.webp`) as the output path dispatches to `cv2.imread`/`cv2.imwrite` and reuses the existing per-frame duotone and halftone closures. Added `apply_duotone_image` and `apply_halftone_image` alongside their video counterparts, plus `process_image` and `is_image_file` helpers in `src/utils/video_processing.py`.

## [0.4.0] - 2026-07-10

### Added

- `requirements-dev.txt` for development-only dependencies (`pytest`, `setuptools`), separated from the runtime `requirements.txt`.
- `pyproject.toml` with pytest configuration (`testpaths`, `addopts`), replacing ad hoc test discovery.
- `tests/test_integration.py`: end-to-end tests that run the real `main()` against synthetic gradient videos and check output dimensions, frame count, and pixel-level duotone and halftone effects.

### Changed

- `apply_duotone` and `apply_halftone` now delegate frame reading, writing, and progress reporting to the shared `process_video_frames` helper in `src/utils/video_processing.py`, removing duplicated capture and writer setup from both modules.
- Codec selection is now always automatic, using `create_video_writer`; there is no longer a manual codec path to opt out of.
- `setup.py` reads `__version__` from `src/__init__.py` instead of hardcoding the version string, making the package `__init__.py` the single source of truth.
- `save_video` in `src/utils/video_processing.py` now writes frames inside a `try/finally` block, guaranteeing `video_writer.release()` and progress bar cleanup even if a write raises an exception.
- Relaxed the per-channel pixel thresholds in the `test_duotone_colors_transform_frame` integration test to allow for lossy-codec and platform variation while still verifying substantially dark and light rows.
- Updated README.md to remove references to the retired `--use-codec-fix` flag.

### Removed

- **Breaking:** the `--use-codec-fix` CLI flag. Codec selection is automatic and no longer configurable from the command line.
- **Breaking:** the `use_codec_fix` parameter from `apply_duotone` and `apply_halftone`. Callers using either function directly must drop the argument.
- `pytest` and `setuptools` from `requirements.txt`; both moved to `requirements-dev.txt`.

### Fixed

- `MANIFEST.in` now includes `src/__init__.py`, so it is present in the sdist. Without it, `setup.py` could not read `__version__` while building the wheel from the sdist, and the PyPI publish step failed.

---

## [0.3.0] - 2026-07-02

### Added

- **Halftone `dot` symbol**: `--symbol_type dot` draws a filled circle (`cv2.circle`) sized by local luminance, matching the classic print-halftone reference point instead of the plus/asterisk/slash glyphs.
- **Halftone `--grid_type` option**: `square` (default, unchanged behavior) or `hex`, which staggers alternating sampling rows by half a step to produce the interlocking dot screen of traditional print halftone reproduction.
- Tests for the new `dot` symbol type and both grid types in `tests/test_halftone.py`; forwarding tests for `--symbol_type dot` and `--grid_type hex` in `tests/test_main.py`.

### Changed

- Bumped version to 0.3.0.
- Updated README.md and description.md to document the `dot` symbol and `hex` grid.

---

## [0.2.1] - 2026-06-30

### Added

- `conftest.py` at the repository root adds `src/` to `sys.path` so test modules import packages by flat name, matching the installed-package layout.
- `tests/test_video_processing.py`: 28 tests covering all six functions in `src/utils/video_processing.py`; 95% line coverage on that module.
- `TestMainVideoEffects` in `tests/test_main.py`: 6 tests for the duotone and halftone branches of `main()`.

### Changed

- Raised `python_requires` to `>=3.7`; removed the Python 3.6 classifier from `setup.py`.
- Rewrote README.md and description.md: specific feature descriptions, named algorithms, correct Python version badge, no hollow descriptors.
- Added `.github/instructions/` to `.gitignore` to keep the VS Code Copilot instruction file local.

### Removed

- `HowToUse.txt`: content superseded by README.md.

### Fixed

- Aligned import style in `tests/test_colors.py`, `tests/test_duotone.py`, and `tests/test_halftone.py` to use flat module names matching the installed-package layout.
- Replaced `except Exception` wrapping over assertions in `tests/test_codec_fix.py` with explicit `skipTest` guards.

---

## [0.2.0] - 2026-06-29

### Added

- **Color input formats**: `--color1` / `--color2` now accept hex strings
  (`#ff0044`), CSS named colors (`rebeccapurple`, `DarkSlateBlue`), and the
  original `R G B` integer triples. The classic syntax remains fully backward
  compatible.
- **Curated palettes**: `--palette <name>` applies a preset two-color
  combination (sunset, mint, cyberpunk, noir, ocean, and more). Run
  `siss --list-palettes` to browse them.
- `--color1` / `--color2` override individual slots of a selected palette.
- New `src/colors.py` module exposing `parse_color`, `get_palette`,
  `list_palettes`, plus the `CSS_NAMED_COLORS` and `PALETTES` data tables.
- Unit tests for color parsing and palettes (`tests/test_colors.py`).

### Changed

- Bumped version to 0.2.0.
- Registered `colors` in `setup.py` so it is shipped on PyPI.

## [0.1.2] - 2025-04-27

### Added

- Example directory with sample images and proper attribution
- Citation file for video sources used in examples

### Changed

- Updated description.md with correct color values used in examples
- More detailed documentation for duotone and halftone effects

### Fixed

- Fixed import paths for better compatibility when installed via pip
- Ensured consistent versioning across all project files

## [0.1.1] - 2025-04-26

### Changed

- Improved PyPI package description
- Added support for more image formats

### Fixed

- Fixed codec compatibility issues on different operating systems

## [0.1.0] - 2025-04-25

### Added

- Initial release
- Duotone effect implementation
- Halftone effect implementation
- Cross-platform codec compatibility
- Command-line interface
