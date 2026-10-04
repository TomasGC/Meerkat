import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "scripts"))  # this checkout's shared library
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
