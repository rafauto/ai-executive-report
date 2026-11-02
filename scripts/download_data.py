"""Download the public Olist dataset from Kaggle into data/raw.

Requirements:
    pip install -e ".[data]"
    Kaggle credentials: ~/.kaggle/kaggle.json or the KAGGLE_USERNAME and
    KAGGLE_KEY environment variables (Kaggle > Settings > API > Create New Token).

Manual alternative: download the .zip from
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce and extract the CSVs into data/raw/.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from executive_report.config import OLIST_FILES, RAW_DATA_DIR  # noqa: E402

DATASET = "olistbr/brazilian-ecommerce"


def main() -> int:
    try:
        import kagglehub
    except ImportError:
        print('Install kagglehub first: pip install -e ".[data]"', file=sys.stderr)
        return 1

    print(f"Downloading {DATASET} from Kaggle...")
    cache_dir = Path(kagglehub.dataset_download(DATASET))
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    missing = []
    for filename in OLIST_FILES.values():
        matches = list(cache_dir.rglob(filename))
        if not matches:
            missing.append(filename)
            continue
        shutil.copy2(matches[0], RAW_DATA_DIR / filename)
        print(f"  ✓ {filename}")

    if missing:
        print(f"Files not found in the download: {missing}", file=sys.stderr)
        return 1
    print(f"Done! Data saved to {RAW_DATA_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
