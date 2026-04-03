"""Backup Manager - partition backup and restore with SHA-256 verification."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Callable, Optional

from tumeloroot.core.mtk_bridge import MtkBridge

ProgressCallback = Callable[[str, int, int], None]


class BackupManager:
    """Manages partition backups with integrity verification."""

    def __init__(self, backup_root: str, mtk_bridge: MtkBridge):
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
        """Backup all listed partitions to a timestamped directory.

        Args:
            partition_names: List of partition names to backup.
            progress_callback: Called with (partition_name, current_index, total).

        Returns:
            Path to the backup directory, or None on failure.
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_dir = self._root / f"backup_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "timestamp": timestamp,
            "device_info": self._mtk.get_device_info(),
            "partitions": {},
        }

        total = len(partition_names)
        for i, name in enumerate(partition_names):
            if progress_callback:
                progress_callback(name, i, total)

            data = self._mtk.read_partition(name)
            if data is None:
                manifest["partitions"][name] = {"status": "failed"}
                continue

            img_path = backup_dir / f"{name}.img"
            img_path.write_bytes(data)

            manifest["partitions"][name] = {
                "status": "ok",
                "size": len(data),
                "sha256": self._sha256(data),
                "filename": f"{name}.img",
            }

        if progress_callback:
            progress_callback("done", total, total)

        manifest_path = backup_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        return str(backup_dir)

    def verify_backup(self, backup_dir: str) -> tuple[bool, list[str]]:
        """Verify backup integrity using SHA-256 checksums.

        Returns:
            (all_valid, list_of_errors)
        """
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
            if len(data) != info["size"]:
                errors.append(f"{name}: size mismatch ({len(data)} != {info['size']})")
            actual_hash = self._sha256(data)
            if actual_hash != info["sha256"]:
                errors.append(f"{name}: checksum mismatch")

        return len(errors) == 0, errors

    def restore_partition(self, backup_dir: str, partition_name: str) -> bool:
        """Restore a single partition from backup."""
        img_path = Path(backup_dir) / f"{partition_name}.img"
        if not img_path.exists():
            return False
        data = img_path.read_bytes()
        return self._mtk.write_partition(partition_name, data)

    def full_restore(
        self,
        backup_dir: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> bool:
        """Restore all partitions from a backup directory."""
        manifest_path = Path(backup_dir) / "manifest.json"
        if not manifest_path.exists():
            return False

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        partitions = [
            name for name, info in manifest.get("partitions", {}).items()
            if info.get("status") == "ok"
        ]

        total = len(partitions)
        success = True
        for i, name in enumerate(partitions):
            if progress_callback:
                progress_callback(name, i, total)
            if not self.restore_partition(backup_dir, name):
                success = False

        return success

    def list_backups(self) -> list[dict]:
        """List all available backups in the backup root."""
        backups = []
        for entry in sorted(self._root.iterdir(), reverse=True):
            if entry.is_dir() and entry.name.startswith("backup_"):
                manifest_path = entry / "manifest.json"
                if manifest_path.exists():
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    backups.append({
                        "path": str(entry),
                        "timestamp": manifest.get("timestamp", ""),
                        "partitions": list(manifest.get("partitions", {}).keys()),
                    })
        return backups
