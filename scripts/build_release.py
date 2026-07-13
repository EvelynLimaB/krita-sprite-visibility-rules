#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a deterministic Krita Python Plugin Importer-compatible ZIP."""

from __future__ import annotations

import compileall
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sprite_visibility_rules.version import __version__  # noqa: E402

DIST = ROOT / "dist"
ARCHIVE = DIST / "sprite_visibility_rules-{}.zip".format(__version__)
# ZIP cannot represent dates before 1980. A fixed release timestamp makes the
# archive byte-for-byte reproducible across checkouts and CI machines.
ZIP_TIMESTAMP = (2026, 7, 13, 0, 0, 0)
MODULE_DIRECTORY = "sprite_visibility_rules/"


def write_directory(zf: zipfile.ZipFile, archive_name: str) -> None:
    """Write an explicit directory entry required by Krita's plugin importer.

    Krita's importer first searches ``ZipFile.namelist()`` for a directory
    named after ``X-KDE-Library`` and only then checks for ``__init__.py``.
    Merely storing files with that path prefix is not enough.
    """

    if not archive_name.endswith("/"):
        archive_name += "/"
    info = zipfile.ZipInfo(archive_name, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = (0o40755 & 0xFFFF) << 16
    info.external_attr |= 0x10  # DOS directory flag for cross-platform readers.
    zf.writestr(info, b"")


def write_deterministic(zf: zipfile.ZipFile, source: Path, archive_name: str) -> None:
    info = zipfile.ZipInfo(archive_name, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (0o100644 & 0xFFFF) << 16
    zf.writestr(info, source.read_bytes())


def main() -> int:
    if not compileall.compile_dir(ROOT / "sprite_visibility_rules", quiet=1):
        raise SystemExit("Python compilation failed")
    DIST.mkdir(exist_ok=True)
    if ARCHIVE.exists():
        ARCHIVE.unlink()
    with zipfile.ZipFile(ARCHIVE, "w") as zf:
        write_deterministic(
            zf,
            ROOT / "sprite_visibility_rules.desktop",
            "sprite_visibility_rules.desktop",
        )
        # Do not remove this entry. Krita's built-in importer requires it to
        # recognize the module; implicit parent directories are insufficient.
        write_directory(zf, MODULE_DIRECTORY)
        for path in sorted((ROOT / "sprite_visibility_rules").rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                write_deterministic(zf, path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(ARCHIVE) as zf:
        bad = zf.testzip()
        if bad:
            raise SystemExit("Corrupt archive member: {}".format(bad))
        names = set(zf.namelist())
    required = {
        "sprite_visibility_rules.desktop",
        MODULE_DIRECTORY,
        "sprite_visibility_rules/__init__.py",
        "sprite_visibility_rules/docker.py",
        "sprite_visibility_rules/Manual.html",
    }
    missing = required - names
    if missing:
        raise SystemExit("Release ZIP missing: {}".format(sorted(missing)))
    print(ARCHIVE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
