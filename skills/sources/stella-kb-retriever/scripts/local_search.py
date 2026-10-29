"""Reuse sibling study-cache without network or model calls."""
import runpy
from pathlib import Path
if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[2] / "study-cache/scripts/study_cache.py"), run_name="__main__")
