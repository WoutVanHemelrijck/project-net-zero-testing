from __future__ import annotations

import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ANN001
    root = Path(session.config.rootpath)
    cache_dirs = ["__pycache__", ".pytest_cache"]

    for folder_name in cache_dirs:
        for directory in root.rglob(folder_name):
            if directory.is_dir():
                shutil.rmtree(directory, ignore_errors=True)