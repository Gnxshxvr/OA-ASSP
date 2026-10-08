"""Top-level forwarder for running OA-ASSP selection pipeline."""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oa_assp.scripts.run_selector_pipeline import run_pipeline

if __name__ == "__main__":
    run_pipeline()
