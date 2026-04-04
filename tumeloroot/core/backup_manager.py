"""Backup Manager - partition backup and restore with SHA-256 verification."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Callable, Optional

ProgressCallback = Callable[[str, int, int], None]


class BackupManager:
    """Manages partition backups with integrity verification."""

    def __init__(self, backup_root: str, mtk_bridge):
        self._root = Path(backup_root)
        self._mtk = mtk_bridge
        self._root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def create_backup(
        self,
        partition_names: list[str],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Optional[str]:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_dir = self._root / f"backup_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Single BROM session reads ALL partitions
        ok = self._mtk.backup_all(partition_names, str(backup_dir))

        # Build manifest from whatever was successfully read
        manifest = {
            "timestamp": timestamp,
            "partitions": {},
        }
        for name in partition_names:
            img_path = backup_dir / f"{name}.img"
            if img_path.is_file() and img_path.stat().st_size > 0:
                data = img_path.read_bytes()
                manifest["partitions"][name] = {
                    "status": "ok",
                    "size": len(data),
                    "sha256": self._sha256(data),
                    "filename": f"{name}.img",
                }
            else:
                manifest["partitions"][name] = {"status": "failed"}

        manifest_path = backup_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        if not ok:
            return None
        return str(backup_dir)

    def verify_backup(self, backup_dir: str) -> tuple[bool, list[str]]:
        manifest_path = Path(backup_dir) / "manifest.json"
        if not manifest_path.exists():
            return False, ["manifest.json not found"]

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        errors = []
        for name, info in manifest.get("partitions", {}).items():
            if info.get("status") != "ok":
                continue
            img_path = Path(backup_dir) / info["filename"]
            if not img_path.exists():
                errors.append(f"{name}: file missing")
                continue
            data = img_path.read_bytes()
            if self._sha256(data) != info["sha256"]:
                errors.append(f"{name}: checksum mismatch")
        return len(errors) == 0, errors

    def list_backups(self) -> list[dict]:
        backups = []
        for entry in sorted(self._root.iterdir(), reverse=True):
            if entry.is_dir() and entry.name.startswith("backup_"):
                manifest_path = entry / "manifest.json"
                if manifest_path.exists():
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    backups.append({
                        "path": str(entry),
                        "timestamp": manifest.get("timestamp", ""),
                    })
        return backups
