import logging
import os
import sys
from pathlib import Path


def setup_logging(log_level: str = "info") -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Packaged mode: APP_LOG_DIR is set by Electron sidecar.ts
    log_dir_env = os.environ.get("APP_LOG_DIR", "")
    log_dir = Path(log_dir_env) if log_dir_env else Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)

    file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    file_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(console)
    root.addHandler(file_handler)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
