from __future__ import annotations

import sys
from pathlib import Path

# Ensure Backend imports like "from routes.api import ..." resolve on Vercel.
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "Backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import app  # noqa: E402
