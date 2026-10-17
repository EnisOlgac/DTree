"""Runs the DTree benchmarks from the repository (same as ``python -m dtree.bench``).

    python benchmarks/bench.py [--quick] [--dynamic] [--note "..."] [--no-save] [sizes...]

The benchmark code lives in the package (dtree/bench.py), so users who installed
dtree-encoding can run it as well.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dtree.bench import main  # noqa: E402

if __name__ == "__main__":
    main()
