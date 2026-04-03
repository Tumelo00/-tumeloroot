"""VBMeta partition patcher - disables AVB verification."""

import struct
from typing import Optional

AVB_MAGIC = b"AVB0"
DEFAULT_FLAGS_OFFSET = 0x78
FLAGS_DISABLE_ALL = 3  # VERIFICATION_DISABLED | HASHTREE_DISABLED


def is_valid_vbmeta(data: bytes) -> bool:
    """Check if data starts with the AVB0 magic header."""
    return len(data) >= 4 and data[:4] == AVB_MAGIC


def read_flags(data: bytes, offset: int = DEFAULT_FLAGS_OFFSET) -> Optional[int]:
    """Read the current vbmeta flags value."""
    if len(data) < offset + 4:
        return None
    return struct.unpack(">I", data[offset : offset + 4])[0]


def patch_vbmeta(
    data: bytes, flags: int = FLAGS_DISABLE_ALL, offset: int = DEFAULT_FLAGS_OFFSET
) -> bytes:
    """Patch vbmeta data to set the given flags (disabling verification).

    Args:
        data: Raw vbmeta partition data.
        flags: Flags value to set. Default 3 = disable verification + hashtree.
        offset: Byte offset of the flags field. Default 0x78 (120).

    Returns:
        Patched vbmeta data.

    Raises:
        ValueError: If data is too small or not a valid vbmeta image.
    """
    if not is_valid_vbmeta(data):
        raise ValueError("Not a valid vbmeta image (missing AVB0 magic)")
    if len(data) < offset + 4:
        raise ValueError(f"Data too small ({len(data)} bytes) for offset {offset}")

    patched = bytearray(data)
    patched[offset : offset + 4] = struct.pack(">I", flags)
    return bytes(patched)


def verify_patch(
    data: bytes, expected_flags: int = FLAGS_DISABLE_ALL, offset: int = DEFAULT_FLAGS_OFFSET
) -> bool:
    """Verify that vbmeta data has the expected flags set."""
    current = read_flags(data, offset)
    return current == expected_flags
