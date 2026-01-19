"""Backward-compatible shim.

The project has been refactored to `app/services/*`.
This module keeps old imports working.
"""

from .services._legacy import *  # noqa
