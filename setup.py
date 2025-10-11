from setuptools import setup, find_packages
from pathlib import Path

# Try to read the long description from description.md
try:
    this_directory = Path(__file__).parent
    long_description = (this_directory / "description.md").read_text()
except Exception:
    # Fallback description if file is not found
    long_description = """
# Siss

A command-line utility for applying artistic effects to videos.

## Key Features

- **Duotone Effect**: Creates stylish two-color videos, mapping colors to dark and light areas
- **Halftone Effect**: Creates artistic videos using symbol patterns that vary in size based on brightness
- **Cross-platform Compatibility**: Works on Windows, macOS, and Linux with automatic codec detection
- **Progress Tracking**: Shows real-time processing progress with estimated completion time

## Quick Start

After installation, use Siss as a command-line tool:

```bash
siss input_video.mp4 output_video.mp4 --effect duotone
```

For complete documentation, visit the [GitHub repository](https://github.com/MichailSemoglou/siss).
"""

setup(
    name="siss",
    version="0.1.3",
    description="A command-line utility for applying artistic effects to videos",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Michail Semoglou",
    author_email="m.semoglou@qide.studio",
    url="https://github.com/MichailSemoglou/siss",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "opencv-python>=4.5.0",
        "numpy>=1.20.0",
        "tqdm>=4.60.0",
    ],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "siss=src.main:main",
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
        "Programming Language :: Python :: 3.6",
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
