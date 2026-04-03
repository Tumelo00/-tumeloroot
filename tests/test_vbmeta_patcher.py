"""Tests for VBMeta Patcher."""

import unittest

from tumeloroot.core.vbmeta_patcher import (
    is_valid_vbmeta, read_flags, patch_vbmeta, verify_patch,
    AVB_MAGIC, FLAGS_DISABLE_ALL, DEFAULT_FLAGS_OFFSET,
)


class TestVbmetaPatcher(unittest.TestCase):

    def _make_vbmeta(self, flags: int = 0) -> bytes:
        import struct
        data = bytearray(AVB_MAGIC + b"\x00" * 200)
        data[DEFAULT_FLAGS_OFFSET:DEFAULT_FLAGS_OFFSET + 4] = struct.pack(">I", flags)
        return bytes(data)

    def test_is_valid_vbmeta(self):
        self.assertTrue(is_valid_vbmeta(self._make_vbmeta()))
        self.assertFalse(is_valid_vbmeta(b"NOPE"))
        self.assertFalse(is_valid_vbmeta(b"AV"))
        self.assertFalse(is_valid_vbmeta(b""))

    def test_read_flags_default(self):
        self.assertEqual(read_flags(self._make_vbmeta(0)), 0)

    def test_read_flags_disabled(self):
        self.assertEqual(read_flags(self._make_vbmeta(3)), 3)

    def test_read_flags_too_small(self):
        self.assertIsNone(read_flags(b"AVB0"))

    def test_patch_vbmeta(self):
        original = self._make_vbmeta(0)
        patched = patch_vbmeta(original)
        self.assertEqual(read_flags(patched), FLAGS_DISABLE_ALL)

    def test_patch_preserves_magic(self):
        patched = patch_vbmeta(self._make_vbmeta())
        self.assertTrue(patched.startswith(AVB_MAGIC))

    def test_patch_preserves_size(self):
        original = self._make_vbmeta()
        patched = patch_vbmeta(original)
        self.assertEqual(len(patched), len(original))

    def test_patch_custom_flags(self):
        patched = patch_vbmeta(self._make_vbmeta(), flags=2)
        self.assertEqual(read_flags(patched), 2)

    def test_patch_invalid_raises(self):
        with self.assertRaises(ValueError):
            patch_vbmeta(b"NOPE")

    def test_patch_too_small_raises(self):
        with self.assertRaises(ValueError):
            patch_vbmeta(b"AVB0")

    def test_verify_patch_true(self):
        patched = patch_vbmeta(self._make_vbmeta())
        self.assertTrue(verify_patch(patched))

    def test_verify_patch_false(self):
        self.assertFalse(verify_patch(self._make_vbmeta(0)))

    def test_idempotent(self):
        original = self._make_vbmeta()
        patched1 = patch_vbmeta(original)
        patched2 = patch_vbmeta(patched1)
        self.assertEqual(patched1, patched2)


if __name__ == "__main__":
    unittest.main()
