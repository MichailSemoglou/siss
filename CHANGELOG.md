# Changelog

All notable changes to the Siss project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-08-25

### Added

- `--extract-frame` CLI flag saves a single frame from a video input as a still image without applying any effect. Accepts an integer frame index or `first`, `middle`, `last`; the output path must be an image file, and `--effect` is not required.

### Fixed

- `docs/llm-prompt.md` described `symbol_size` as the pixel size of the largest symbol; it actually sets the sampling grid pitch, and the largest symbol radius is half the pitch minus one pixel. The prompt now documents the pitch and tone-level math, the ink-coverage differences between symbol types, and the washed-out interaction between gamma above 1.0 and sizes below 12. The newspaper and dream-wash example grammars use sizes that render as described.

## [1.1.0] - 2026-08-16

### Added

- `--preview-frame` and `--preview-output` CLI flags for processing a single frame from a video input and saving it as a still image for rapid iteration without waiting for a full render.
- Preview-frame support accepts a numeric frame index, a numeric string such as `48`, or the `middle` keyword, and falls back to a grab-loop when frame seeking is unreliable for a given codec.

### Changed

- The preview workflow uses the same duotone and halftone processors as full renders, so designers can inspect one frame quickly before committing to a full video export.

## [1.0.0] - 2026-08-01

### Added

- `--constraints` CLI flag reads a JSON file that locks every rendering parameter (effect, colors, symbol type, symbol size, grid, and luminance-curve gamma). CLI flags override individual slots, so the same file can serve as a reproducible baseline while one parameter is varied. Validation rejects unknown keys and bad values with clear error messages.
- `--dump-constraints` CLI flag writes the effective constraints of any run to a JSON file, capturing the resolved values so a hand-tuned run can be reused as a `--constraints` input
- Luminance-curve gamma (`luminance_curve.gamma` in the constraints file, or passed through the halftone API). The gamma exponent biases the luminance-to-symbol-size mapping: values above 1 suppress symbol growth in dark regions; values below 1 amplify it. The default 1.0 gives a linear mapping identical to previous versions.
- **Halftone `ring` symbol**: `--symbol_type ring` draws a hollow circle (outer radius equal to the computed symbol size, inner radius one pixel less), the outline counterpart to the filled `dot` symbol.
- **Loss-map output** (`--loss-map PATH`): when passed alongside `--effect halftone`, emits a grayscale loss map at the same resolution as the input. Per output cell, the absolute difference between the source luminance and the luminance reproducible under the chosen grammar (symbol-size quantization). Bright marks high divergence, dark marks faithful reproduction. Video output writes a parallel video; still-image output writes a single-channel PNG.
- **Split-view dual styles** (`--split-alt-*` flags): when `--split-view` is active, `--split-alt-color1`, `--split-alt-color2`, `--split-alt-palette`, and `--split-alt-constraints` apply a different visual style to the alternate half of the output, so one side can be noir and the other sunset. Both halves are processed with their own grammars; neither is the raw original. Supports `vertical`, `horizontal`, `vertical-full`, and `horizontal-full` modes.
- Sample constraints file `examples/constraints.json` with a ring-hex halftone configuration at gamma 0.8
- `docs/llm-prompt.md`: a reusable prompt for LLMs (Claude, GPT, Gemini) that describes the constraints schema, parameter semantics, design heuristics, and four worked examples so an LLM can author a visual grammar from a natural-language description
- "Why This Exists" section in the README, positioning Siss as a co-creation instrument where an LLM authors the visual grammar (the constraints file) and deterministic code enforces it
- Over 65 new tests covering constraints validation, precedence resolution, dump format, reloadability, gamma behavior, ring symbol rendering, loss-map computation, and integration through `main()`

### Changed

- `--split-view` expanded to support two modes: `vertical`/`horizontal` stitch half of the original and half of the processed frame into a single output at the original dimensions; `vertical-full`/`horizontal-full` preserve the previous behavior of placing the full original alongside the full processed result at double the width or height. The half-half mode is the new default; the full-canvas mode remains available.
- `--symbol-size`, `--symbol-type`, and `--grid-type` argparse defaults moved from the argument parser to the resolution phase so constraints-file values can override them without breaking CLI precedence
- `_resolve_colors` signature now accepts an optional `constraints` dict
- `_make_halftone_processor` optionally returns a `(rendered, loss_map)` tuple; `process_video_frames` and `process_image` detect tuple returns and write the second element to a loss-map path
- Extracted shared `SYMBOL_TYPES`, `GRID_TYPES`, and `EFFECT_TYPES` constants from three duplicate choice-list sites in `halftone.py` and `main.py` into single-source-of-truth tuples
- Collapsed `TestHalftoneSplitView` and `TestDuotoneSplitView` duplicate test classes into a shared `_SplitViewImageTestMixin` in `tests/helpers.py`
- Deduplicated temp-file cleanup in `merge_audio` by moving the `os.unlink` logic into a single `finally` block gated by a success flag
- `_ns()` test helper base dict expanded to include `no_audio`, `split_view`, `constraints`, `dump_constraints`, and `export_palette_preview` with argparse-correct defaults

### Fixed

- Non-finite gamma values (`Infinity`, `-Infinity`, `NaN`) in constraints files are now properly rejected with a `ValueError` instead of raising an unhandled `NameError`
- Dependency constraints in `setup.py` aligned with `requirements.txt` to address Pillow's authoritative advisory CVE-2025-48379 for the affected range `Pillow>=11.2.0,<11.3.0`, with the issue fixed in `11.3.0`
- Upper bounds added to all runtime and dev dependencies for supply-chain reproducibility
- Output paths are validated against parent-directory traversal (`../` segments)
- Constraints-file loading now enforces a 1 MiB size limit, consistent with palette-file loading
- Success messages now use `logging.info()` instead of `print()`, so `--quiet` silences all output
- Font-loading debug logs no longer include absolute OS filesystem paths
- ffmpeg error detail logged on audio-merge failure strips temporary file paths

## [0.8.0] - 2026-07-28

### Added

- Unit tests for internal core algorithmic functions `_grid_means`, `_draw_symbols`, and `_duotone_frame` in `tests/test_core_algorithms_pytest.py`. Coverage includes all four symbol types (plus, dot, asterisk, slash), known integral-image inputs, and pixel-level assertions for duotone interpolation.
- `--verbose` (`-v`/`-vv`) and `--quiet` (`-q`) CLI flags for controlling log output verbosity.
- Structured logging via Python's `logging` module with ISO-8601 timestamps, severity levels, and module-qualified names. Output goes to stderr; the result-path line stays on stdout for downstream scripts.
- Tests for log-level configuration, `--verbose`/`--quiet` flag acceptance, and exception-handling paths in `tests/test_main.py`.
- `--export-palette-preview` flag that renders an A4-landscape PNG contact sheet of every palette as labeled swatch pairs with HEX and RGB values in a system monospaced font at 12pt.
- `--split-view` flag (`vertical` or `horizontal`) for exporting before/after comparison outputs. Vertical places original left and processed right; horizontal places original above. Works with any input orientation including portrait and 9:16 vertical video.
- Hash-pinned dependency lock files (`requirements.lock`, `requirements-dev.lock`) generated with `uv pip compile --generate-hashes` for reproducible, verifiable installations.
- `pip-audit` step in the CI workflow to flag known vulnerable dependencies on every push and pull request.
- `py.typed` marker (`src/siss/py.typed`) so downstream type-checkers can validate consumer code.
- File-size guard in `load_palette_file()`: palette files larger than 1 MiB are rejected with a `ValueError` before JSON parsing, preventing resource exhaustion from maliciously large inputs.
- Tests for halftone edge-drawer code paths (`_draw_symbols` with asterisk and slash symbols touching frame boundaries, exercising the previously untested `_EDGE_DRAWERS` functions).
- Tests for `_grid_means` near-edge clipping, single-grid-point, and non-default `k` values, verifying integral-image mean computation at frame boundaries.
- Tests for `_draw_symbols` empty-size early-return and multi-size grouping paths.
- End-to-end split-view tests for duotone and halftone on still images (both orientations) and for `process_video_frames` (video split-view path).
- Size-limit boundary tests for `load_palette_file`: exactly at 1 MiB, one byte over, plus valid small and empty files.
- Test for negative `symbol_size` in `_make_halftone_processor`.
- Regression test verifying edge-vs-bulk drawer pixel consistency for interior asterisk and slash symbols, locking the contract between the two rendering paths.
- DEBUG-level logging in codec validation probe failures, font-loading fallback exceptions, and ffprobe probe failures, replacing silent `except Exception`/`except (TimeoutExpired, OSError)` blocks so failures leave diagnostic breadcrumbs.

### Changed

- **Refactor:** split `src/siss/colors.py` (719 lines) into the `src/siss/colors/` package with three single-concern submodules: `_parse.py` (hex/CSS/RGB parsing and validation), `_palettes.py` (curated palettes and JSON palette-file loading), and `_preview.py` (palette contact-sheet renderer with system font discovery). The public API is re-exported unchanged from `colors/__init__.py`; all call sites continue to `import from siss.colors` without modification.
- `apply_duotone_image` and `apply_halftone_image` backward-compat shims now accept and forward `split_direction` and `no_audio`, making them true pass-throughs to `apply_duotone`/`apply_halftone` rather than feature-incomplete wrappers.
- Consolidated duplicate core algorithm test files: `tests/test_core_algorithms.py` (unittest) removed; its coverage was already present in `tests/test_core_algorithms_pytest.py` (pytest).
- `audio.py` and `video_processing.py` now use `logging` instead of `print()` to stderr for warnings and information messages.
- Added `Pillow>=11.0.0` dependency for system font rendering in the palette preview contact sheet.
- **Security:** raised `opencv-python` minimum version from `>=4.5.0` to `>=4.10.0` to exclude versions predating CVE fixes (CVE-2023-2617, CVE-2023-2618).
- **Security:** the `main()` catch-all exception handler now emits the full traceback only when log level is `DEBUG` (`-vv`); at default verbosity, it logs a user-friendly message without leaking file paths or stack frames.
- **Security:** ffmpeg error output embedded in audio-merge warning messages is truncated to 200 characters, preventing long stderr strings with absolute paths from appearing in logs.
- `tqdm` progress bar is automatically disabled when `--quiet` is active (root logger at ERROR or above).
- `main()` exception handler now distinguishes `FileNotFoundError`, `ValueError`, and `RuntimeError` from unexpected exceptions; all are logged via `logging` instead of `print()` to stderr.
- Indentation bug in `process_video_frames` fixed: `out` and `progress_bar` are now assigned outside the guard clause, not unreachable inside it.
- `_draw_symbols` guards against an empty `sizes` array, returning early instead of iterating zero symbols.

### Fixed

- Inner closures `_duotone_frame` and `_halftone_frame` in the processor factories now carry type annotations on their `frame` parameters and return types.
- `_make_halftone_processor` had a structural bug where `_halftone_frame` was defined at module scope instead of inside the closure; the `return _halftone_frame` statement was unreachable and `apply_halftone` received `None`. Restored correct indentation.

## [0.7.2] - 2026-07-27

### Added

- CI workflow (`.github/workflows/ci.yml`): runs ruff, mypy, and pytest on push and PR across Python 3.9–3.13.
- `--no-audio` CLI integration tests in `tests/test_main.py` (forwarding coverage through `main()`).
- `TestSafeInt` in `tests/test_video_processing.py`: 6 edge-case tests for non-finite and negative values.

### Changed

- **Breaking:** `symbol_type`, `grid_type`, and `no_audio` are now keyword-only parameters in `apply_duotone`, `apply_halftone`, and `apply_halftone_image`. Positional pass-through sites in tests are updated.
- Raise `python_requires` to `>=3.9`; ruff `target-version` to `py39`; drop Python 3.7 and 3.8 classifiers from `setup.py`.
- Extracted `_validate_args_and_paths()` and `_dispatch_effect()` from `main()`; `main()` is now ~35 lines.
- `main()` unexpected-error handler prints the full traceback alongside the one-line message.
- `merge_audio` in `src/siss/audio.py` appends ffmpeg stderr to the warning on `CalledProcessError`.
- `_has_audio_stream` in `src/siss/audio.py` checks `returncode == 0` before testing stdout contents.
- `apply_duotone_image` and `apply_halftone_image` shims now accept and forward `no_audio`.

### Fixed

- `setup.py` version regex now guards against `None` match with a clear `RuntimeError`.
- Unused `mock_stderr` variable removed from `tests/test_audio.py`.
- Import ordering in all source and test files aligned with ruff `I` rule.
- `tests/test_audio.py` docstring updated to note that `--no-audio` CLI tests live in `test_main.py`.

## [0.7.1] - 2026-07-27

### Changed

- The duotone processor now blends the two colors in a single vectorized operation (`src/siss/duotone.py`). The per-channel Python loop is replaced by a NumPy broadcast, and the float-to-uint8 cast uses `np.round` instead of truncation, removing a systematic dark bias of up to 1 LSB per channel.
- `--symbol-size`, `--symbol-type`, and `--grid-type` are now the primary CLI flags for the halftone effect (`src/siss/main.py`). The previous underscore variants (`--symbol_size` and so on) remain as hidden aliases, so existing scripts and muscle memory are not broken.

### Fixed

- The audio merge step in `src/siss/audio.py` now creates the temporary file next to the output path rather than in the system temp directory. On macOS and other platforms where a user-chosen output resides on a different volume from `/tmp`, `os.replace` no longer fails with a cross-device link error and the rendered audio is not lost.
- `process_video_frames` in `src/siss/utils/video_processing.py` raises `ValueError` before writer construction when the input video reports degenerate dimensions (`width <= 0` or `height <= 0`) or a non-positive frame count. A `(0, 0)` writer is no longer silently accepted.
- Each processed frame is checked against the writer's configured dimensions in `process_video_frames`. When OpenCV yields a frame whose shape diverges from the reported properties (observed with certain transcoders and rotated metadata), the frame is resized to match before writing rather than producing a corrupt packet.
- The halftone edge predicate for `asterisk` and `slash` symbols in `src/siss/halftone.py` now covers all four sides of the frame. Symbols whose strokes overflow the top or left edge are routed through the same clamped `cv2.line` drawer as bottom and right edges, producing symmetric results instead of silently dropping out-of-bounds pixels.

## [0.7.0] - 2026-07-26

### Added

- Audio passthrough for video output. OpenCV `VideoWriter` writes silent files; after rendering, `merge_audio` in the new `src/siss/audio.py` copies the original audio track into the output with `ffmpeg` (`-c:a copy -c:v copy`, no re-encode). The merge happens automatically for video output and is skipped when `ffmpeg` is not on PATH (warning to stderr) or when the source has no audio stream.
- `--no-audio` CLI flag to skip the audio merge. Forwarded through `apply_duotone`, `apply_halftone`, and `process_media`; still-image paths ignore it.
- Unit tests for the audio module in `tests/test_audio.py` (18 tests). Covers `_has_audio_stream`, `merge_audio`, process-media dispatch, and effect-function forwarding.
- `ruff` and `mypy` configurations in `pyproject.toml`. All 9 source files pass both tools with no issues.

### Changed

- `process_video_frames` restructured: `out` and `progress_bar` are initialized to `None` before a single `try/finally` block, removing the nested structure and the `if 'out' in locals()` guard.
- `validate_codec` simplified: uses `mkstemp` instead of `NamedTemporaryFile` with `delete=False`, removing the overlapping context-manager and manual-cleanup paths. Behavior is unchanged.
- `_parse_hex` no longer re-validates hex digits; the two callers guarantee valid input through `_looks_like_hex` or the `#`-prefix guard. Behavior is unchanged.
- Halftone grid-sizing constants are documented inline in `src/siss/halftone.py`.

### Fixed

- `ColorLike` type alias in `src/siss/colors.py` no longer advertises `int`, matching the actual behavior of `parse_color`, which rejects bare integers.

## [0.6.0] - 2026-07-24

### Changed

- Restructured the source tree as a proper `siss` package. Modules moved from flat files under `src/` to `src/siss/`, internal imports are now relative, and `setup.py` installs `packages=["siss", "siss.utils"]` with the console-script entry point `siss=siss.main:main`. The generic top-level module names (`main`, `duotone`, `utils`, and others) are no longer installed, removing the risk of conflicts with other packages.
- Tests now import the package as `siss.*`. The per-file `sys.path` manipulation in `tests/` is removed; `conftest.py` is the single place that puts `src/` on the path for a source checkout.
- `MANIFEST.in` now includes `src/siss/__init__.py`, the file `setup.py` reads `__version__` from.
- Unified the video and still-image processing paths. `process_media()` in `src/siss/utils/video_processing.py` dispatches on the output extension, `apply_duotone()` and `apply_halftone()` handle both media types through one entry point, and `main()` no longer repeats the dispatch per effect. `apply_duotone_image()` and `apply_halftone_image()` remain as aliases for backward compatibility.
- RGB channel validation is shared through `validate_rgb()` in `src/siss/colors.py`; `parse_color` and both effect processors use it. Out-of-range colors still raise `ValueError`.
- Codec selection in `src/siss/codec_fix.py` is now a single default map with per-OS overrides, and `get_working_codec` validates each candidate codec at most once per call. Selected codecs are unchanged.
- `setup.py` reads the PyPI long description from `description.md` directly; the embedded fallback copy is removed.
- Test scaffolding is shared through `tests/helpers.py` instead of per-file gradient video and image builders.

### Removed

- **Breaking:** the unused helpers `extract_frames()`, `save_video()`, and `release_resources()` from `src/siss/utils/video_processing.py`. None had production callers; the first two were exercised only by their own tests, which are removed with them. Code importing these helpers must keep its own copies.
- Unused imports: `numpy` from `src/siss/utils/video_processing.py` and `sys` from `tests/test_video_processing.py`.

### Fixed

- `validate_codec()` and `get_working_codec()` in `src/siss/codec_fix.py` now probe with the actual requested output extension (`.avi`, `.mov`, `.mkv`, `.wmv`) instead of a hardcoded `.mp4`, so codec validation reflects the real target container.
- `validate_rgb()` in `src/siss/colors.py` now rejects non-integer and boolean channels, and raises `ValueError` (instead of a leaked `TypeError`) for non-iterable input.

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
