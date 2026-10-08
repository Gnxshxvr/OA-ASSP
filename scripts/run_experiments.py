"""Top-level forwarder for running OA-ASSP experiments."""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oa_assp.scripts.run_experiments import main

if __name__ == "__main__":
    sys.exit(main())
