"""dtree-encoding 1.9.0: DTree now lives in Triordinal (package triordinal-dtree).

This package only forwards to ``triordinal.dtree``; the code and all further development
are in https://github.com/EnisOlgac/Triordinal. Please change

    pip install dtree-encoding        ->  pip install triordinal-dtree
    from dtree import DTree           ->  from triordinal.dtree import DTree

The API is the same. The import name ``dtree`` clashes with an unrelated package on PyPI,
and it will not be maintained further.
"""

import warnings

from triordinal.dtree import SINK, SOURCE, DList, DNode, DTree, UMax, UMin, VMax, VMin  # noqa: F401
from triordinal.dtree import __version__ as triordinal_dtree_version  # noqa: F401

warnings.warn(
    "dtree-encoding has moved to Triordinal: pip install triordinal-dtree, then "
    "'from triordinal.dtree import DTree' (same API). The import name 'dtree' is deprecated.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["DTree", "DNode", "DList", "VMin", "VMax", "UMin", "UMax", "SOURCE", "SINK"]
__version__ = "1.9.0"
