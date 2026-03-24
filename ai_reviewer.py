#!/usr/bin/env python
"""AI Reviewer - CLI entry point."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cli.main import cli

if __name__ == "__main__":
    cli()
