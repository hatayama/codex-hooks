#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT_DIR: Path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from codex_hooks.monitor import main


if __name__ == "__main__":
    main()
