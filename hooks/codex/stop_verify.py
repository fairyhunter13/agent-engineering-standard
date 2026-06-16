#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hooks.core import stop_verify_main  # noqa: E402
from policy.shared import STATE_FILE, load_json  # noqa: E402


def main() -> int:
    return stop_verify_main(agent="codex", state_file=STATE_FILE, load_json_fn=load_json)


if __name__ == "__main__":
    raise SystemExit(main())
