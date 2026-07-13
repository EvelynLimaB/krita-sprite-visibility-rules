#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${HOME}/.var/app/org.kde.krita/data/krita/pykrita"
ARCHIVE="${ROOT}/dist/sprite_visibility_rules-1.0.0.zip"

command -v flatpak >/dev/null || { echo "flatpak is not installed" >&2; exit 1; }
flatpak info org.kde.krita >/dev/null || { echo "org.kde.krita is not installed" >&2; exit 1; }
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

echo "Installed into ${TARGET}"
echo "Backup: ${BACKUP}"
echo "Restart Krita, enable Sprite Visibility Rules in Python Plugin Manager, restart again, then open Settings > Dockers."
