import unittest
from pathlib import Path

from daily_ideas.systems import load_devices, load_platform, validate_platform

ROOT = Path(__file__).resolve().parents[1]


class PlatformTests(unittest.TestCase):
    def test_four_role_platform_is_valid(self):
        platform = load_platform(ROOT / "systems" / "platform.json")
        self.assertEqual(4, len(platform.roles))
        self.assertEqual([], validate_platform(platform, ROOT))

    def test_control_loop_is_closed(self):
        platform = load_platform(ROOT / "systems" / "platform.json")
        links = {(link.source, link.target) for link in platform.links}
        self.assertTrue({("observe", "reason"), ("reason", "act"), ("act", "observe")} <= links)

    def test_every_soc_design_is_connected(self):
        devices = load_devices(ROOT / "systems" / "devices.json")
        discovered = {path.name for path in (ROOT / "systems" / "soc-devices").iterdir()
                      if path.is_dir() and (path / "README.md").is_file()}
        self.assertEqual(discovered, {device.id for device in devices})
        self.assertEqual(57, len(devices))
