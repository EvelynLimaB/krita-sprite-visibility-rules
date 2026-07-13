#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${HOME}/.var/app/org.kde.krita/data/krita/pykrita"

command -v python3 >/dev/null || { echo "python3 is not installed" >&2; exit 1; }
command -v unzip >/dev/null || { echo "unzip is not installed" >&2; exit 1; }
command -v flatpak >/dev/null || { echo "flatpak is not installed" >&2; exit 1; }
flatpak info org.kde.krita >/dev/null || { echo "org.kde.krita is not installed" >&2; exit 1; }

VERSION="$(PLUGIN_ROOT="$ROOT" python3 -c 'import os, sys; sys.path.insert(0, os.environ["PLUGIN_ROOT"]); from sprite_visibility_rules.version import __version__; print(__version__)')"
ARCHIVE="${ROOT}/dist/sprite_visibility_rules-${VERSION}.zip"

python3 "${ROOT}/scripts/build_release.py" >/dev/null
mkdir -p "${TARGET}"
BACKUP="${HOME}/.var/app/org.kde.krita/data/krita/plugin-backups/sprite_visibility_rules-$(date +%Y%m%d-%H%M%S)"
mkdir -p "${BACKUP}"
for item in sprite_visibility_rules sprite_visibility_rules.desktop; do
    if [[ -e "${TARGET}/${item}" ]]; then
        mv "${TARGET}/${item}" "${BACKUP}/"
    fi
done
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
unzip -q "${ARCHIVE}" -d "${TMP}"
cp -a "${TMP}/sprite_visibility_rules" "${TMP}/sprite_visibility_rules.desktop" "${TARGET}/"

echo "Installed Sprite Visibility Rules ${VERSION} into ${TARGET}"
echo "Backup: ${BACKUP}"
echo "Restart Krita, enable Sprite Visibility Rules in Python Plugin Manager, restart again, then open Settings > Dockers."
