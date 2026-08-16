"""
Siss - Video Effects Tool package.

A command-line utility for applying artistic effects to videos and still images.
"""

from .metrics import compute_loss_map, compute_metrics, write_benchmark_report

__version__ = '1.1.0'

__all__ = [
    "__version__",
    "compute_loss_map",
    "compute_metrics",
    "write_benchmark_report",
]
