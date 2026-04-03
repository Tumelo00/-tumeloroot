"""Tests for DeviceProfile."""

import os
import tempfile
import unittest

from tumeloroot.core.device_profile import DeviceProfile


class TestDeviceProfile(unittest.TestCase):

    def test_load_lenovo_k11(self):
        profiles = DeviceProfile.list_available()
        self.assertGreaterEqual(len(profiles), 1)
        p = profiles[0]
        self.assertEqual(p.manufacturer, "Lenovo")
        self.assertEqual(p.codename, "TB330XUP")

    def test_boot_structure(self):
        p = DeviceProfile.list_available()[0]
        self.assertEqual(p.boot_structure.ramdisk_partition, "vendor_boot")
        self.assertEqual(p.boot_structure.kernel_partition, "boot")
        self.assertFalse(p.boot_structure.init_boot_used)
        self.assertTrue(p.boot_structure.ab_device)

    def test_vbmeta_config(self):
        p = DeviceProfile.list_available()[0]
        self.assertEqual(p.vbmeta.flags_offset, 0x78)
        self.assertEqual(p.vbmeta.flags_value, 3)
        self.assertGreater(len(p.vbmeta.partitions), 0)

    def test_validation_pass(self):
        p = DeviceProfile.list_available()[0]
        errors = p.validate()
        self.assertEqual(len(errors), 0)

    def test_validation_fail(self):
        p = DeviceProfile()  # Empty profile
        errors = p.validate()
        self.assertGreater(len(errors), 0)

    def test_display_name(self):
        p = DeviceProfile.list_available()[0]
        self.assertIn("Lenovo", p.display_name)
        self.assertIn("TB330XUP", p.display_name)

    def test_invalid_yaml(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write("invalid: {{{")
            tmp = f.name
        try:
            with self.assertRaises(Exception):
                DeviceProfile.load(tmp)
        finally:
            os.unlink(tmp)


if __name__ == "__main__":
    unittest.main()
