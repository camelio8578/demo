"""Snapshot saving for scraped pages."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import structlog

log = structlog.get_logger()


class SnapshotSaver:
    def __init__(self, snapshots_dir: str | Path | None = None):
        self.dir = Path(snapshots_dir or os.getenv("SNAPSHOTS_DIR", "./data/snapshots"))
        self.dir.mkdir(parents=True, exist_ok=True)

    def save(self, county: str, html: str, source_name: str = "default") -> Path:
        """Save HTML to disk. Returns path. Always succeeds (logs errors, doesn't raise)."""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        fname = f"{county}_{source_name}_{ts}.html"
        path = self.dir / fname
        try:
            path.write_text(html, encoding="utf-8")
            log.info("snapshot_saved", path=str(path), county=county, bytes=len(html))
        except Exception as exc:
            log.error("snapshot_save_failed", path=str(path), error=str(exc))
        return path
