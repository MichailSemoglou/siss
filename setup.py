from setuptools import setup
from pathlib import Path
import re

# Single source of truth: read version from src/siss/__init__.py
_init = (Path(__file__).parent / "src" / "siss" / "__init__.py").read_text()
__version__ = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", _init).group(1)

# The PyPI long description is maintained in description.md (shipped in the
# sdist via MANIFEST.in). Fail the build loudly if it is missing rather than
# falling back to a second, drifting copy.
long_description = (Path(__file__).parent / "description.md").read_text(encoding="utf-8")

setup(
    name="siss",
    version=__version__,
    description="A command-line utility for applying artistic effects to videos",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Michail Semoglou",
    author_email="m.semoglou@qide.studio",
    url="https://github.com/MichailSemoglou/siss",
    license="MIT",
    packages=["siss", "siss.utils"],
    package_dir={"": "src"},
    install_requires=[
        "opencv-python>=4.5.0",
        "numpy>=1.20.0",
        "tqdm>=4.60.0",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "siss=siss.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video",
        "Topic :: Artistic Software",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="video, duotone, halftone, effect, artistic, video-processing",
    project_urls={
        "Bug Reports": "https://github.com/MichailSemoglou/siss/issues",
        "Source": "https://github.com/MichailSemoglou/siss",
    },
)
