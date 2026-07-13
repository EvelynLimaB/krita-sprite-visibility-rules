#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the local V1 release verification suite."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True, env=env)


def main() -> int:
    if shutil.which("ruff"):
        run("ruff", "format", "--check", ".")
        run("ruff", "check", ".")
    else:
        print("- ruff not installed; style checks skipped", file=sys.stderr)

    run(sys.executable, "scripts/build_release.py")
    archive = ROOT / "dist" / "sprite_visibility_rules-1.0.0.zip"
    first_digest = subprocess.check_output(["sha256sum", str(archive)], text=True).split()[0]
    run(sys.executable, "scripts/build_release.py")
    second_digest = subprocess.check_output(["sha256sum", str(archive)], text=True).split()[0]
    if first_digest != second_digest:
        raise SystemExit("Release archive is not reproducible")

    run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v")

    try:
        import PyQt5  # noqa: F401
    except ImportError:
        print("- PyQt5 not installed; offscreen docker smoke test skipped", file=sys.stderr)
    else:
        smoke_env = dict(os.environ)
        smoke_env.update(RUN_QT_SMOKE="1", QT_QPA_PLATFORM="offscreen")
        run(
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_ui_smoke.py",
            "-v",
            env=smoke_env,
        )

    run(sys.executable, "-m", "compileall", "-q", "sprite_visibility_rules", "tests", "scripts")
    run("bash", "-n", "scripts/install-flatpak.sh")
    run("bash", "-n", "scripts/publish-github.sh")
    run("bash", "tests/test_flatpak_installer.sh")

    if shutil.which("unzip"):
        run("unzip", "-tq", str(archive))
    else:
        print("- unzip not installed; external ZIP CRC check skipped", file=sys.stderr)

    digest = subprocess.check_output(["sha256sum", str(archive)], text=True).split()[0]
    (ROOT / "dist" / "SHA256SUMS").write_text(
        f"{digest}  sprite_visibility_rules-1.0.0.zip\n", encoding="utf-8"
    )
    print("Verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
