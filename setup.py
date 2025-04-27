from setuptools import setup, find_packages
from pathlib import Path

# Read the long description from the description.md file
this_directory = Path(__file__).parent
long_description = (this_directory / "description.md").read_text()

setup(
    name="siss",
    version="0.1.1",
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
