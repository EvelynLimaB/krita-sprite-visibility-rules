#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/home/.var/app/org.kde.krita/data/krita/pykrita"

cat > "$TMP/bin/flatpak" <<'MOCK'
#!/usr/bin/env bash
if [[ "${1:-}" == "info" && "${2:-}" == "org.kde.krita" ]]; then
    exit 0
fi
exit 2
MOCK
chmod +x "$TMP/bin/flatpak"

run_installer() {
    HOME="$TMP/home" PATH="$TMP/bin:$PATH" "$ROOT/scripts/install-flatpak.sh" >/dev/null
}

run_installer
TARGET="$TMP/home/.var/app/org.kde.krita/data/krita/pykrita"
test -f "$TARGET/sprite_visibility_rules.desktop"
test -f "$TARGET/sprite_visibility_rules/__init__.py"

printf 'old marker\n' > "$TARGET/sprite_visibility_rules/old-marker.txt"
run_installer
BACKUP_ROOT="$TMP/home/.var/app/org.kde.krita/data/krita/plugin-backups"
find "$BACKUP_ROOT" -type f -name old-marker.txt -print -quit | grep -q .
test ! -e "$TARGET/sprite_visibility_rules/old-marker.txt"

echo "Flatpak installer mock test passed"
