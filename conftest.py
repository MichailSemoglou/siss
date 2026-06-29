"""
Pytest root configuration.

Adds src/ to sys.path so every test module uses the same flat import
style that the package itself uses internally and that setup.py exposes
to installers (package_dir={"":"src"}):

    from codec_fix import ...
    from utils.video_processing import ...

Only src/ is added; the repo root is intentionally omitted to prevent
the same module from being importable under two names (e.g. both
``colors`` and ``src.colors``), which would split module state.
"""
import os
import sys

_src = os.path.join(os.path.dirname(__file__), "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
