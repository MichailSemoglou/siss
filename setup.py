from setuptools import setup, find_packages

setup(
    name="siss",
    version="0.1.0",
    description="A command-line utility for applying artistic effects to videos",
    author="Michail Semoglou",
    author_email="m.semoglou@tongji.edu.cn",
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
            "siss=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Video",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
    ],
)
