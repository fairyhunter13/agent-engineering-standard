#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hooks.core import verification_state_main  # noqa: E402
from policy.shared import STATE_DIR, STATE_FILE, dump_json, load_json  # noqa: E402


def main(argv: list[str]) -> int:
    return verification_state_main(argv, state_dir=STATE_DIR, state_file=STATE_FILE, load_json_fn=load_json, dump_json_fn=dump_json)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
