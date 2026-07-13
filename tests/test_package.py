import configparser
import pathlib
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_desktop_descriptor_matches_module(self):
        config = configparser.ConfigParser()
        config.read(ROOT / "sprite_visibility_rules.desktop", encoding="utf-8")
        entry = config["Desktop Entry"]
        self.assertEqual(entry["X-KDE-Library"], "sprite_visibility_rules")
        self.assertTrue((ROOT / entry["X-KDE-Library"] / "__init__.py").is_file())
        self.assertEqual(entry["ServiceTypes"], "Krita/PythonPlugin")

    def test_manual_exists(self):
        self.assertTrue((ROOT / "sprite_visibility_rules" / "Manual.html").is_file())

    def test_release_zip_is_importer_layout(self):
        archive = ROOT / "dist" / "sprite_visibility_rules-1.0.0.zip"
        self.assertTrue(archive.is_file())
        with zipfile.ZipFile(archive) as zf:
            names = set(zf.namelist())
        self.assertIn("sprite_visibility_rules.desktop", names)
        self.assertIn("sprite_visibility_rules/__init__.py", names)
        self.assertFalse(any(name.startswith("krita-sprite-visibility-rules/") for name in names))


if __name__ == "__main__":
    unittest.main()
