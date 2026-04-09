from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    os.chdir(here)
    sys.path.insert(0, str(here))
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
