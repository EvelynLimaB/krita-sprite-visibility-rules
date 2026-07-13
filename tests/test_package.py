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
        # Krita's built-in importer requires an explicit directory member. An
        # implicit directory created only by file paths is not recognized.
        self.assertIn("sprite_visibility_rules/", names)
        self.assertIn("sprite_visibility_rules/__init__.py", names)
        self.assertFalse(any(name.startswith("krita-sprite-visibility-rules/") for name in names))

    def test_release_zip_matches_krita_importer_module_discovery(self):
        archive = ROOT / "dist" / "sprite_visibility_rules-{}.zip".format(__version__)
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
        module_name = "sprite_visibility_rules"
        module_directory = next(
            (
                name
                for name in names
                if name.endswith("/{}/".format(module_name)) or name == "{}/".format(module_name)
            ),
            None,
        )
        self.assertIsNotNone(module_directory)
        self.assertIn("{}__init__.py".format(module_directory), names)


if __name__ == "__main__":
    unittest.main()
