#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hooks.core import pre_tool_use_main  # noqa: E402


def main() -> int:
    return pre_tool_use_main()


if __name__ == "__main__":
    raise SystemExit(main())
