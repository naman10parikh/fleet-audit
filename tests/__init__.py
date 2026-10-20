"""Unit tests. Run from the repository root: python3 -m unittest"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))
os.environ.setdefault("FLEET_AUDIT_RUNLOG", "off")
