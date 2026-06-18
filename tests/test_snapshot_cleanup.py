from __future__ import annotations

import os
import time
from pathlib import Path

from hooks.core import cleanup_stale_snapshots, snapshot_meta_dir


def test_cleanup_stale_snapshots_removes_old_files_only(tmp_path: Path) -> None:
    root = snapshot_meta_dir(tmp_path)
    root.mkdir(parents=True)
    old_file = root / "old.json"
    fresh_file = root / "fresh.json"
    old_file.write_text("{}")
    fresh_file.write_text("{}")
    old_mtime = time.time() - 120
    os.utime(old_file, (old_mtime, old_mtime))

    cleanup_stale_snapshots(tmp_path, max_age_seconds=60)

    assert not old_file.exists()
    assert fresh_file.exists()
