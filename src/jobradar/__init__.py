"""
jobradar — Observability for scheduled & async jobs.
Detects silent failures, anomalies, and cascading issues.
"""

from jobradar.client import configure
from jobradar.observe import ObserveContext, observe, observe_context

__version__ = "0.1.0"

__all__ = [
    "observe",
    "observe_context",
    "ObserveContext",
    "configure",
    "__version__",
]
