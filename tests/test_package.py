import configparser
import pathlib
import unittest
import zipfile

from sprite_visibility_rules.version import __version__

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_project_version_matches_plugin_version(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('version = "{}"'.format(__version__), pyproject)

    def test_desktop_descriptor_matches_module(self):
        config = configparser.ConfigParser()
        config.read(ROOT / "sprite_visibility_rules.desktop", encoding="utf-8")
        entry = config["Desktop Entry"]
        self.assertEqual(entry["X-KDE-Library"], "sprite_visibility_rules")
        self.assertTrue((ROOT / entry["X-KDE-Library"] / "__init__.py").is_file())
        self.assertEqual(entry["ServiceTypes"], "Krita/PythonPlugin")

    def test_manual_exists(self):
        self.assertTrue((ROOT / "sprite_visibility_rules" / "Manual.html").is_file())

    def test_publish_helper_uses_python3_compatible_command(self):
        script = (ROOT / "scripts" / "publish-github.sh").read_text(encoding="utf-8")
        self.assertIn('PYTHON="${PYTHON:-python3}"', script)
        self.assertIn('"$PYTHON" scripts/verify_release.py', script)
        self.assertNotIn("\npython scripts/verify_release.py", script)

    def test_release_zip_is_importer_layout(self):
        archive = ROOT / "dist" / "sprite_visibility_rules-{}.zip".format(__version__)
        self.assertTrue(archive.is_file())
        with zipfile.ZipFile(archive) as zf:
            names = set(zf.namelist())
        self.assertIn("sprite_visibility_rules.desktop", names)
        self.assertIn("sprite_visibility_rules/__init__.py", names)
        self.assertFalse(any(name.startswith("krita-sprite-visibility-rules/") for name in names))


if __name__ == "__main__":
    unittest.main()
